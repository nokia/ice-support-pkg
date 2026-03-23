from __future__ import absolute_import
import json
import re
from HealthCheckCommon.secret_filter import SecretFilter
from tools.python_versioning_alignment import get_full_trace
import tools.user_params
from HealthCheckCommon.operations import SystemOperator
from flows_of_sys_operations.FileTracker import FileTrackerLogging as file_tracker_logger
from flows_of_sys_operations.FileTracker.FileTrackerPaths import FileTrackerPaths, FileTrackerPathsInitiator
from tools.Exceptions import UnExpectedSystemOutput
from tools.global_enums import Objectives
from tools.date_and_time_utils import parse

from tools.lazy_global_data_loader import lazy_global_data_loader
from tools.system_commands import SystemCommands


class FileTrackerBase(SystemOperator):
    data_store = {}
    is_log_with_failure = False
    IGNORE_CHANGES_IN_PERMISSIONS = False
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S %Z"
    last_run_timestamp = ""

    def convert_to_json(self, all_changes_list):
        try:
            return json.dumps(all_changes_list, indent=5)
        except:
            raise ValueError("The value is not in appropriate format")

    def preserve_and_copy(self, file_name, full_path, snapshots_dir):
        self.get_output_from_run_cmd(
            "nice -n 4 sudo cp --preserve=mode,ownership {full_path} {snapshots_dir_path}{file_name}".format(
                file_name=file_name, full_path=full_path,
                snapshots_dir_path=snapshots_dir))

    def create_new_snapshot(self, file_name, full_path, is_first_snapshot=True,
                            snapshots_dir=None):
        if snapshots_dir is None:
            snapshots_dir = FileTrackerPaths.SNAPSHOTS_DIRECTORY
        self.preserve_and_copy(file_name, full_path, snapshots_dir)
        self.log_new_snapshot(full_path, is_first_snapshot, snapshots_dir)

    def log_new_snapshot(self, full_path, is_first_snapshot, snapshots_dir):
        if tools.user_params.debug or is_first_snapshot:
            file_tracker_logger.log(self, "A new snapshot for {} was created in {}".format(
                full_path, snapshots_dir))

    def create_snapshot_for_folder(self, folder_path, snapshot_path, is_first_snapshot, is_folder_exist=True):
        if is_folder_exist:
            cmd = "sudo bash -c 'ls {} > {}'".format(folder_path, snapshot_path)
        else:
            cmd = "sudo bash -c 'echo > {}'".format(snapshot_path)
        self.get_output_from_run_cmd(cmd)
        self.log_new_snapshot(folder_path, is_first_snapshot,
                              snapshots_dir=FileTrackerPaths.FOLDERS_SNAPSHOTS_DIRECTORY)

    def create_new_dynamic_snapshot(self, resource_name, resource_type, resource_yaml_content, file_path,
                                    add_log_message=None):
        if add_log_message is None:
            add_log_message = tools.user_params.debug
        extracted_spec_yaml = self._extract_spec_section_from_yaml(resource_yaml_content)
        if not extracted_spec_yaml:
            file_tracker_logger.log(self, "Expected to have 'spec' section in the '{}' {}'s yaml".format(resource_name,
                                                                                                         resource_type))
            return

        self.file_utils.write_content_to_file(file_path, extracted_spec_yaml)
        if add_log_message:
            file_tracker_logger.log(self, "A new snapshot for {} was created in {}".format(
                resource_name, FileTrackerPaths.DYNAMIC_SNAPSHOTS_DIRECTORY))

    def update_log_on_failure(self, msg="The running has stopped due to some errors.", is_running_failed=True):
        FileTrackerBase.is_log_with_failure = True
        msg = SecretFilter.filter_string_array(msg)
        for line_msg in msg.split('\n'):
            file_tracker_logger.log(self, text=line_msg, error=True)
        if is_running_failed:
            file_tracker_logger.log(self, "{} Failed".format(self._title), error=True)

    def verify_free_disk_space(self):
        available_disk_space_size = self.system_utils.get_available_disk_space_size()
        if available_disk_space_size < FileTrackerPaths.DISK_SPACE_THRESHOLD:

            if self.file_utils.is_file_exist_on_host_roles(FileTrackerPaths.FILE_TRACKER_LOG_PATH,
                                                           [Objectives.UC, Objectives.ONE_MANAGER, Objectives.DEPLOYER]
                                                           ):
                failed_msg = "There is not enough available disk space for the file tracker running. \nRequired disk space: {}K\nAvailable disk space: {}K.".format(
                    FileTrackerPaths.DISK_SPACE_THRESHOLD, available_disk_space_size)
                self.update_log_on_failure(failed_msg, True)
            return False
        return True

    def run_file_tracker_operator(self):
        raise NotImplementedError

    def run_system_operation(self):
        FileTrackerPathsInitiator()

        try:
            return self.run_file_tracker_operator()
        except:
            full_trace = get_full_trace()
            if file_tracker_logger.logger:
                self.update_log_on_failure(full_trace.replace('\n', ' '))
            raise

    def _get_last_file_change_timestamp(self, path):
        last_change_time = self.file_utils.get_last_change_time(path)
        last_change_time_in_format = self._get_timestamp_in_format(last_change_time)
        return last_change_time_in_format

    def _handle_deleted_conf_file(self, snapshot_path, full_path):
        timestamp = self._get_now_timestamp()
        last_snapshot_timestamp = self._get_last_file_change_timestamp(snapshot_path)
        diff_output = "The file {} was deleted from this directory.\nLast snapshot was taken on {}".format(
            full_path, last_snapshot_timestamp)
        return timestamp, diff_output

    def _get_now_timestamp(self):
        return self.get_output_from_run_cmd("date +'{}'".format(self.DATE_FORMAT)).replace('\n', '')

    def _get_timestamp_in_format(self, timestamp):
        timestamp_in_format = self.get_output_from_run_cmd(
            "date -d '{}' +'{}'".format(timestamp, self.DATE_FORMAT)).replace('\n', '')
        return timestamp_in_format

    def sort_change_list_by_modify_timestamp(self, changes_list):
        sort_key = "modify timestamp"
        for dict_item in changes_list:
            assert sort_key in list(dict_item.keys()), "Not all the dictionaries in the list contain the sort key '{}'".format(
                sort_key)
        return sorted(changes_list, key=lambda x: parse(x[sort_key]))

    def convert_json_to_dict(self, json_path):
        with open(json_path) as json_file:
            operation_details_dict = json.load(json_file)
        return operation_details_dict

    def create_ice_dir(self):
        self.get_output_from_run_cmd(SystemCommands.get_create_ice_dir_cmd())

    def get_tracked_items_dict(self, tracked_items_json_path):
        items_dict = self.convert_json_to_dict(tracked_items_json_path)
        if "configuration" in tracked_items_json_path:
            if FileTrackerPaths.CONF_FILES_PER_DEPLOYMENT:
                items_dict.update(self.convert_json_to_dict(FileTrackerPaths.CONF_FILES_PER_DEPLOYMENT))
        elif "dynamic" in tracked_items_json_path:
            items_dict.update(self.convert_json_to_dict(FileTrackerPaths.DYNAMIC_RESOURCES_PER_DEPLOYMENT))
        return items_dict

    def create_file_tracker_dir(self, shared_folder=False):
        if shared_folder:
            dir_path = FileTrackerPaths.MAIN_FILE_TRACKER_DIR_PATH
        else:
            dir_path = FileTrackerPaths.FILE_TRACKER_DIR_PATH_ON_HOST

        self.get_output_from_run_cmd("sudo mkdir -p {}".format(dir_path))
        if self.parse_to_int(self.file_utils.get_file_permission_id(dir_path)) == int(self.file_utils.OPENED_PERMISSIONS):
            self.file_utils.change_file_permissions(permissions='775', file_path=dir_path)
        self.file_utils.change_file_owner(owner=self._host_executor.user_name, file_path=dir_path)

    def is_relevant_for_current_host(self, hosts_list_str):
        hosts_list = set(eval(hosts_list_str))
        intersection_hosts = set(self.get_host_roles()).intersection(hosts_list)

        return len(intersection_hosts) > 0

    def get_snapshot_name_by_path(self, full_path):
        return full_path.replace("/", "_")[1:]

    def get_snapshot_name_by_cmd(self, cmd):
        return cmd.replace(" ", "_").replace("|", "")

    def get_snapshot_name_for_folder(self, folder_path):
        return self.get_snapshot_name_by_path(folder_path)[:-1]

    def create_snapshots_dir(self, snapshot_dir_path):
        is_snapshots_dir_exist = self.file_utils.is_dir_exist(snapshot_dir_path)
        self.get_output_from_run_cmd("sudo mkdir -p {}".format(snapshot_dir_path))
        if self.parse_to_int(self.file_utils.get_file_permission_id(snapshot_dir_path)) == int(self.file_utils.OPENED_PERMISSIONS):
            self.file_utils.change_file_permissions(permissions='775', file_path=snapshot_dir_path)
        if not is_snapshots_dir_exist:
            file_tracker_logger.log(self, "{} was not exist. The snapshots directory was created".format(
                snapshot_dir_path))

    def run_data_collector_on_one_master(self, data_collector_class, **kwargs):
        assert data_collector_class.objective_hosts == [Objectives.ONE_MASTER]
        res = self.run_data_collector(data_collector_class, **kwargs)

        if len(list(res.items())) == 0:
            raise UnExpectedSystemOutput("1 master", "", "Can't run, no connected master")

        assert len(list(res.items())) == 1, "This method run only on 1 host"

        res = list(res.values())[0]
        if res is None:
            raise UnExpectedSystemOutput("one master", "",
                                         "exception was raised from data collector: {}".format(
                                             data_collector_class.__name__))

        return res

    def _extract_spec_section_from_yaml(self, yaml_content):
        # ^spec:: Matches the literal string "spec:" at the beginning of a line.
        # (.*?): Matches any sequence of characters (.) and captures it. The *? modifier makes the * (zero or more)
        #   quantifier non-greedy, which means it will match as few characters as possible.
        # (?=^\S|\Z): A positive lookahead assertion (?= ... ) that specifies a condition that must be satisfied for
        #   a match to occur. It checks two conditions:
        # ^\S: This part matches the beginning of a line (^) followed by a non-whitespace character (\S). This condition
        #   ensures that the match stops just before the next line that starts with a non-whitespace character.
        # |\Z: The | character represents an OR condition. \Z matches the end of the string. This condition ensures
        #   that if there are no more lines in the string, the match will stop at the end of the string.
        spec_match = re.search(r"^spec:(.*?)(?=^\S|\Z)", yaml_content, re.DOTALL | re.MULTILINE)
        if spec_match:
            return "spec:" + spec_match.group(1)
        else:
            return None

    def _get_estimated_last_modify_timestamp_range(self):
        current_datetime_str = self.get_output_from_run_cmd("date +'{}'".format(self.DATE_FORMAT)).replace('\n', '')

        if not self.last_run_timestamp:
            estimated_modify_timestamp_range = "Before {}".format(current_datetime_str)
        else:
            estimated_modify_timestamp_range = "Between {from_timestamp} and {to_timestamp}".format(
                from_timestamp=self.last_run_timestamp, to_timestamp=current_datetime_str)

        return estimated_modify_timestamp_range

    def _create_tmp_dir(self, tmp_dir_path):
        is_tmp_dir_exist = self.file_utils.is_dir_exist(tmp_dir_path)
        if not is_tmp_dir_exist:
            self.get_output_from_run_cmd("sudo mkdir -p {}".format(tmp_dir_path))
            self.file_utils.change_file_owner(self._host_executor.user_name, tmp_dir_path)
        if self.parse_to_int(self.file_utils.get_file_permission_id(tmp_dir_path)) == int(self.file_utils.OPENED_PERMISSIONS):
            self.file_utils.change_file_permissions(permissions='775', file_path=tmp_dir_path)

    def save_cmd_out_into_file(self, cmd, file_path):
        self._verify_cmd_is_valid(cmd)
        if self.file_utils.is_file_exist(file_path):
            self.file_utils.change_file_permissions(self.file_utils.R_W_PERMISSIONS, file_path)
        try:
            full_cmd = "sudo bash -c '{cmd} > {file_path}'".format(cmd=cmd, file_path=file_path)
            self.get_output_from_run_cmd(full_cmd)
        finally:
            self.file_utils.change_file_permissions(self.file_utils.CLOSED_PERMISSIONS, file_path)

    def _verify_cmd_is_valid(self, cmd):
        self.get_output_from_run_cmd(cmd)