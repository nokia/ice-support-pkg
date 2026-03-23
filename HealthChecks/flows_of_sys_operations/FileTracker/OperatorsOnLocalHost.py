from __future__ import absolute_import
import gzip
import os.path

from HealthCheckCommon.operations import DataCollector
from flows.Chain_of_events.operation_timing_info import Operation_timing_info
from flows_of_sys_operations.FileTracker.FileTrackerBase import FileTrackerBase
from flows_of_sys_operations.FileTracker.FileTrackerPaths import FileTrackerPaths
from tools import paths
from tools.Exceptions import NoSuitableHostWasFoundForRoles
from flows_of_sys_operations.FileTracker import FileTrackerLogging as file_tracker_logger
from tools.Info import *
from datetime import datetime, timedelta
import tools.sys_parameters as gs
from tools.system_commands import SystemCommands
from six.moves import range


class FTLogChangeTime(DataCollector):
    objective_hosts = [Objectives.MANAGERS]

    def collect_data(self, **kwargs):
        old_log_path = "/usr/share/ice/file_tracker/file_tracker.log"

        if self.file_utils.is_file_exist(old_log_path):
            return self.file_utils.get_last_change_int_time(old_log_path)

        return -1


class CopyFTItemsToManagersShared(DataCollector):
    def collect_data(self, **kwargs):
        log_folder = os.path.dirname(FileTrackerPaths.FILE_TRACKER_LOG_PATH)
        self.file_utils.copy_file("/usr/share/ice/file_tracker/file_tracker.log*", log_folder)
        self.file_utils.remove_file("/usr/share/ice/file_tracker/file_tracker.log*")

        if self.file_utils.is_file_exist("/usr/share/ice/file_tracker/diff.json"):
            diff_folder = os.path.dirname(FileTrackerPaths.DIFFERENCES_SUMMARY_FILE)
            self.file_utils.copy_file("/usr/share/ice/file_tracker/diff.json*", diff_folder)
            self.file_utils.remove_file("/usr/share/ice/file_tracker/diff.json*")

        if self.file_utils.is_file_exist("/usr/share/ice/file_tracker/file_tracker_locker"):
            self.file_utils.copy_file("/usr/share/ice/file_tracker/file_tracker_locker",
                                      FileTrackerPaths.FILE_TRACKER_LOCKER)
            self.file_utils.remove_file("/usr/share/ice/file_tracker/file_tracker_locker")


class FileTrackerStarter(FileTrackerBase):

    objective_hosts = [Objectives.UC, Objectives.ONE_MANAGER, Objectives.DEPLOYER]

    def set_document(self):
        self._unique_operation_name = "file_tracker_pre_running"
        self._title = "File Tracker pre-running"
        self._failed_msg = "File Tracker pre-running failed"
        self._run_in_parallel = False
        self._prerequisite_unique_operation_name = ""
        self.last_file_tracker_run_datetime_in_utc = None

    def run_file_tracker_operator(self):
        FileTrackerBase.is_log_with_failure = False
        FileTrackerBase.data_store = {}
        self.create_ice_dir()
        self.create_file_tracker_dir()
        self.create_file_tracker_dir(shared_folder=True)
        ice_shared_folder = os.path.abspath(os.path.join(FileTrackerPaths.MAIN_FILE_TRACKER_DIR_PATH, os.pardir))
        self.file_utils.change_file_owner(self._host_executor.user_name, ice_shared_folder)

        if gs.get_deployment_type() == Deployment_type.NCS_OVER_BM:
            if not self.file_utils.is_file_exist(FileTrackerPaths.FILE_TRACKER_LOG_PATH):
                last_updated_host = self._get_last_updated_manager()

                if last_updated_host:
                    self._upgrade_ice_ft_cnb(last_updated_host)

        if self.is_file_tracker_locked():
            return False

        if self.file_utils.is_file_exist(FileTrackerPaths.FILE_TRACKER_LOG_PATH):
            last_run_int_timestamp = self._get_last_run_int_timestamp()
            self.last_file_tracker_run_datetime_in_utc = self._get_last_run_datetime_in_utc(last_run_int_timestamp)
            if gs.get_cluster_name():  # We expect to have cluster name in NCS, and not in CBIS
                FileTrackerBase.last_run_timestamp = self._get_last_run_timestamp_by_cluster_name(gs.get_cluster_name())
            else:
                FileTrackerBase.last_run_timestamp = self._convert_timestamp_from_int_to_str(last_run_int_timestamp)

        file_tracker_logger.init(FileTrackerPaths.FILE_TRACKER_LOG_PATH)
        if gs.get_cluster_name():
            file_tracker_logger.log(self,
                                    "********************************************** Start running File Tracker on cluster {} **********************************************".format(gs.get_cluster_name()))
        else:
            file_tracker_logger.log(self,
                                    "********************************************** Start running File Tracker **********************************************")
        if not self.verify_free_disk_space():
            return False
        self.copy_conf_files_json()
        self.copy_tracked_folders_json()

        if Deployment_type.is_ncs(gs.get_deployment_type()):
            self.copy_dynamic_resources_json()

        if gs.get_version() >= Version.V24_11:
            self.copy_tracked_commands_json()

        if gs.get_deployment_type() == Deployment_type.CBIS:
            self.check_compatibility_to_snapshots_permissions_fix()
            self.log_restore_uc_from_backup_case()

        return True

    def is_file_tracker_locked(self):
        return self.file_utils.is_file_exist(FileTrackerPaths.FILE_TRACKER_LOCKER)

    def copy_conf_files_json(self):
        self._copy_tracked_items_json("tracked_configuration_files.json", FileTrackerPaths.CONF_FILES_JSON)

        # Remove files from prev ice version (file name was changed)
        self.file_utils.remove_file_if_exist(os.path.join(FileTrackerPaths.FILE_TRACKER_DIR_PATH_ON_HOST,
                                                          "ncs_tracked_configuration_files.json"))
        self.file_utils.remove_file_if_exist(os.path.join(FileTrackerPaths.FILE_TRACKER_DIR_PATH_ON_HOST,
                                                          "cbis_tracked_configuration_files.json"))

    def copy_dynamic_resources_json(self):
        self._copy_tracked_items_json("tracked_dynamic_resources.json", FileTrackerPaths.DYNAMIC_RESOURCES_JSON)

    def copy_tracked_folders_json(self):
        self._copy_tracked_items_json("tracked_folders.json", FileTrackerPaths.TRACKED_FOLDERS_JSON)

    def copy_tracked_commands_json(self):
        self._copy_tracked_items_json("tracked_commands.json", FileTrackerPaths.TRACKED_COMMANDS_JSON)

    def _copy_tracked_items_json(self, file_name, tracked_items_json_path):
        tracked_items_json = self.get_tracked_items_dict(tracked_items_json_path)

        file_path_dest = os.path.join(FileTrackerPaths.MAIN_FILE_TRACKER_DIR_PATH, file_name)

        if self.file_utils.is_file_exist(file_path_dest):
            self.file_utils.change_file_owner(owner=self._host_executor.user_name, file_path=file_path_dest)

        with open(file_path_dest, 'w') as f:
            json.dump(tracked_items_json, f, indent=2)

    def _update_current_ice_version(self):
        current_version = GetInfo.get_ice_version()

        with open(FileTrackerPaths.CURRENT_ICE_VERSION_FILE, "w") as f:
            f.write(current_version)

    def check_compatibility_to_snapshots_permissions_fix(self):
        if not os.path.exists(FileTrackerPaths.CURRENT_ICE_VERSION_FILE):
            return_code, last_ice_version, err = self.run_cmd("cat {}".format(FileTrackerPaths.LAST_ICE_VERSION_PATH))
            if return_code != 0:
                last_ice_version = '1.3-b219'  # default value for ice version in case there is no backup folder (first version with file tracker)
            last_build_number = int(last_ice_version.split('b')[1])
            if last_build_number < 243 and gs.get_deployment_type() == Deployment_type.CBIS:  # build 243 is the first build with the check of changes in permissions, and taking the correct permissions of the snapshots
                FileTrackerBase.IGNORE_CHANGES_IN_PERMISSIONS = True
        self._update_current_ice_version()

    def log_restore_uc_from_backup_case(self):
        operation_timing = Operation_timing_info(self)
        res = None
        try:
            res = operation_timing.get_operations_datetime()
        except NoSuitableHostWasFoundForRoles:
            pass
        if res and res.get('undercloud_restore') != None:
            last_uc_restore = res['undercloud_restore'][-1]["start_time"]
            uc_restore_date_format = "%Y-%m-%d %H:%M:%S"
            last_uc_restore_datetime = datetime.strptime(last_uc_restore, uc_restore_date_format)
            if self.last_file_tracker_run_datetime_in_utc is not None:
                if last_uc_restore_datetime >= self.last_file_tracker_run_datetime_in_utc:
                    file_tracker_logger.log(self,
                                        "Restore undercloud from backup operation was performed on {}".format(last_uc_restore))

    def _get_last_run_int_timestamp(self):
        return self.file_utils.get_last_change_int_time(FileTrackerPaths.FILE_TRACKER_LOG_PATH)

    def _convert_timestamp_from_int_to_str(self, int_timestamp, is_utc=False):
        if is_utc:
            str_timestamp = self.get_output_from_run_cmd("date --utc --date=@{} +'{}'".format(int_timestamp, self.DATE_FORMAT)).replace('\n', '')
        else:
            str_timestamp = self.get_output_from_run_cmd("date --date=@{} +'{}'".format(int_timestamp, self.DATE_FORMAT)).replace('\n', '')
        return str_timestamp

    def _get_last_run_datetime_in_utc(self, last_run_int_timestamp):
        last_file_tracker_run_str = self._convert_timestamp_from_int_to_str(last_run_int_timestamp, is_utc=True)
        last_file_tracker_run_datetime = datetime.strptime(last_file_tracker_run_str, self.DATE_FORMAT)
        return last_file_tracker_run_datetime

    def _get_last_run_timestamp_by_cluster_name(self, cluster_name):
        last_cluster_line_in_log = self.get_output_from_run_cmd("grep 'on cluster {}' {} | tail -1".format(cluster_name, FileTrackerPaths.FILE_TRACKER_LOG_PATH))
        last_cluster_run_timestamp = last_cluster_line_in_log.split(',')[0]
        local_timezone = self.get_output_from_run_cmd("date +'%Z'").replace('\n', '')
        full_last_cluster_run_timestamp = "{} {}".format(last_cluster_run_timestamp, local_timezone)
        return full_last_cluster_run_timestamp

    def _upgrade_ice_ft_cnb(self, last_updated_host):
        self.run_data_collector_on_specific_hosts(CopyFTItemsToManagersShared, hosts_names_list=[last_updated_host])

    def _get_last_updated_manager(self):
        log_change_times = self.run_data_collector(FTLogChangeTime)
        last_updated_host = max(list(log_change_times.keys()), key=lambda host: log_change_times[host])

        if log_change_times[last_updated_host] < 0:
            return None

        return last_updated_host


class DiffsWriter(FileTrackerBase):
    objective_hosts = [Objectives.UC, Objectives.ONE_MANAGER, Objectives.DEPLOYER]
    FILE_SIZE_THRESHOLD = 1048576 * 10  # We assume 1048576*10 bytes (10M) available disk space is enough for the diff.json file

    def set_document(self):
        self._unique_operation_name = "write_all_changes_to_json_file"
        self._title = "Writing all changes to diff.json file"
        self._failed_msg = "Writing all changes to diff.json file failed"
        self._run_in_parallel = False
        self._prerequisite_unique_operation_name = "file_tracker_pre_running"

    def run_file_tracker_operator(self):
        all_changes_list = []
        if self.file_utils.is_file_exist(FileTrackerPaths.DIFFERENCES_SUMMARY_FILE):
            self.set_diff_permissions(FileTrackerPaths.DIFFERENCES_SUMMARY_FILE)
            all_changes_list = self.convert_current_diff_file_to_list()
            is_security_info_found = self.remove_security_info(json_file=all_changes_list)
            if is_security_info_found:
                origin_changes_json = self.convert_to_json(all_changes_list)
                self.write_in_file(file_path=FileTrackerPaths.DIFFERENCES_SUMMARY_FILE, text=origin_changes_json)
        if len(FileTrackerBase.data_store) > 0:
            self.remove_security_info(json_file=[FileTrackerBase.data_store])
            all_changes_json_obj = self.convert_to_json([FileTrackerBase.data_store])
            if not self.check_new_diff_size(all_changes_json_obj):
                return False
            if self.file_utils.is_file_exist(FileTrackerPaths.DIFFERENCES_SUMMARY_FILE) and self.is_current_file_size_large(FileTrackerPaths.DIFFERENCES_SUMMARY_FILE):
                self.rotate_file(file_name=FileTrackerPaths.DIFFERENCES_SUMMARY_FILE)
            else:
                all_changes_list.append(FileTrackerBase.data_store)
                all_changes_json_obj = self.convert_to_json(all_changes_list)
            if not self.file_utils.is_file_exist(FileTrackerPaths.DIFFERENCES_SUMMARY_FILE):
                self.create_diff_file()
            self.write_in_file(file_path=FileTrackerPaths.DIFFERENCES_SUMMARY_FILE, text=all_changes_json_obj)
            file_tracker_logger.log(self,
                                    "All changes that were found have been written to {}".format(
                                        FileTrackerPaths.DIFFERENCES_SUMMARY_FILE))
        return True

    def check_new_diff_size(self, all_changes_json):
        file_size = len(all_changes_json.encode("utf-8"))
        if file_size > self.FILE_SIZE_THRESHOLD:
            failed_msg = "The size of of changes found in this run is too big. The new data have not written to the file. File size: {} bytes. File size limitation: {} bytes.".format(
                file_size, self.FILE_SIZE_THRESHOLD)
            self.update_log_on_failure(failed_msg, True)
            return False
        return True

    def convert_current_diff_file_to_list(self):
        with self.file_utils.with_file_permissions(FileTrackerPaths.DIFFERENCES_SUMMARY_FILE, "444"):
            with open(FileTrackerPaths.DIFFERENCES_SUMMARY_FILE, 'r') as f:
                current_diff_file_to_list = json.load(f)
        return current_diff_file_to_list

    def is_current_file_size_large(self, file_path):
        file_size = self.file_utils.get_file_size(file_path)
        if file_size > self.FILE_SIZE_THRESHOLD:
            return True
        return False

    def rotate_file(self, file_name, backup_count=10):
        if backup_count > 0:
            self.roll_backup_files(backup_count, file_name)
        new_backup_file = file_name + ".1"
        if os.path.exists(file_name):
            os.rename(file_name, new_backup_file)
            self.do_archive(new_backup_file)

    def do_archive(self, new_backup_file):
        try:
            self.file_utils.change_file_permissions(permissions=self.file_utils.R_W_PERMISSIONS, file_path=new_backup_file)
            with open(new_backup_file, 'rb') as f:
                new_backup_file_gz = new_backup_file + '.gz'
                with gzip.open(new_backup_file_gz, 'wb') as comp_file:
                    comp_file.writelines(f)
            os.remove(new_backup_file)
        finally:
            self.set_diff_permissions(new_backup_file_gz)

    def roll_backup_files(self, backup_count, file_name):
        for i in range(backup_count - 1, 0, -1):
            pre_zip_file = "%s.%d.gz" % (file_name, i)
            last_zip_file = "%s.%d.gz" % (file_name, i + 1)
            if os.path.exists(pre_zip_file):
                if os.path.exists(last_zip_file):
                    os.remove(last_zip_file)
                os.rename(pre_zip_file, last_zip_file)

    def create_diff_file(self):
        self.get_output_from_run_cmd("sudo touch {}".format(FileTrackerPaths.DIFFERENCES_SUMMARY_FILE))
        self.set_diff_permissions(FileTrackerPaths.DIFFERENCES_SUMMARY_FILE)

    def remove_security_info(self, json_file):
        #TODO - marge with the Health check securty cover code (ICET-1315)
        SECURITY_STRING_LIST = ["password", "pass", "pas", "ssh-rsa", "ssh", "rsa", "key", "dsa", "ecdsa", "pwd_value",
                                "pwd", "token", "secret", "certificate"]
        placeholder = "*****"
        is_security_info_found = False
        for index in range(len(json_file)):
            for host in json_file[index]:
                for change in json_file[index][host]:
                    if change.get('changes'):
                        for line_index in range(len(change['changes'])):
                            line = change['changes'][line_index]
                            for security_string in SECURITY_STRING_LIST:
                                index_security_string = line.lower().find(security_string)
                                if index_security_string != -1:
                                    start_security_string = index_security_string+len(security_string)
                                    start_security_string = self.get_start_security_string(line, start_security_string)
                                    if start_security_string != len(line) and line[start_security_string:] != placeholder:
                                        is_security_info_found = True
                                        line = line[0:start_security_string] + placeholder
                                        change['changes'][line_index] = line
        return is_security_info_found

    def get_start_security_string(self, line, start_security_string):
        for char in [':', ' ', '-', '=', '"']:
            if start_security_string == len(line):
                break
            if line[start_security_string] == char:
                start_security_string = start_security_string + 1
        return start_security_string

    def write_in_file(self, file_path, text):
        try:
            self.file_utils.change_file_permissions(permissions=self.file_utils.R_W_PERMISSIONS, file_path=file_path)
            with open(file_path, 'w') as f:
                f.write(text)
        finally:
            self.set_diff_permissions(FileTrackerPaths.DIFFERENCES_SUMMARY_FILE)

    def set_diff_permissions(self, file_path):
        self.file_utils.change_file_permissions(permissions=self.file_utils.CLOSED_PERMISSIONS, file_path=file_path)
        self.file_utils.change_file_owner(owner='root', file_path=file_path)


class FileTrackerFinisher(FileTrackerBase):
    objective_hosts = [Objectives.UC, Objectives.ONE_MANAGER, Objectives.DEPLOYER]

    def set_document(self):
        self._unique_operation_name = "file_tracker_post_running"
        self._title = "File Tracker post-running"
        self._failed_msg = "File Tracker post-running failed"
        self._run_in_parallel = False
        self._prerequisite_unique_operation_name = "file_tracker_pre_running"

    def run_file_tracker_operator(self):
        if gs.get_cluster_name():
            file_tracker_logger.log(self,
                                    "********************************************** File Tracker running finished on cluster {} **********************************************".format(gs.get_cluster_name()))
        else:
            file_tracker_logger.log(self,
                                "********************************************** File Tracker running finished **********************************************")

        return True

class SaveEncryptionKey(FileTrackerBase):

    objective_hosts = [Objectives.UC, Objectives.ONE_MANAGER, Objectives.DEPLOYER]

    def set_document(self):
        self._unique_operation_name = "save_encryption_key"
        self._title = "save encryption key for file_tracker.log"
        self._failed_msg = "saving encryption key for file_tracker.log failed"
        self._run_in_parallel = False
        self._prerequisite_unique_operation_name = ""

    def run_file_tracker_operator(self):
        if FileTrackerBase.is_log_with_failure:
            SystemCommands.save_key_to_keys_file(FileTrackerPaths.MAIN_FILE_TRACKER_DIR_PATH,
                                                 file_tracker_logger.get_first_log_time())
        self.clean_old_lines(os.path.join(FileTrackerPaths.MAIN_FILE_TRACKER_DIR_PATH, paths.ENCRYPTION_OUT_FILES_KEYS_FILE))
        return True

    def is_valid_date(self, date_str):
        """Checks if the date string follows the correct format."""
        DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{6}")
        return bool(DATE_REGEX.match(date_str))

    def clean_old_lines(self, file_path, days_threshold=100):
        KEY_DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
        cutoff_date = datetime.today() - timedelta(days=days_threshold)
        updated_lines = []

        if self.file_utils.is_file_exist(file_path):
            with open(file_path, "r") as f:
                for line in f:
                    parts = line.split(None, 2)
                    if len(parts) < 2 or not self.is_valid_date(parts[0] + " " + parts[1]):
                        updated_lines.append(line)
                        continue

                    line_date = datetime.strptime(parts[0] + " " + parts[1], KEY_DATE_FORMAT)
                    if line_date >= cutoff_date:
                        updated_lines.append(line)

            with open(file_path, "w") as f:
                f.writelines(updated_lines)

