from __future__ import absolute_import
from flows_of_sys_operations.FileTracker.DiffParser import DiffParser
from flows_of_sys_operations.FileTracker.FileTrackerBase import FileTrackerBase
from flows_of_sys_operations.FileTracker.FileTrackerPaths import FileTrackerPaths
from tools.Exceptions import UnExpectedSystemOutput
from tools.global_enums import Objectives, Deployment_type
from flows_of_sys_operations.FileTracker import FileTrackerLogging as file_tracker_logger


class CommandsDiffsCollector(FileTrackerBase):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.ALL_HOSTS, Objectives.HYP],
        Deployment_type.NCS_OVER_BM: [Objectives.ALL_NODES, Objectives.MANAGERS]
    }

    def set_document(self):
        self._unique_operation_name = "collect_diffs_for_commands_outputs"
        self._title = "Collecting diffs in commands outputs"
        self._failed_msg = "Collecting diffs in commands outputs failed"
        self._run_in_parallel = True
        self._prerequisite_unique_operation_name = "file_tracker_pre_running"
        self._ignore_changes_in_permissions = False

    def run_file_tracker_operator(self):
        if not self.verify_free_disk_space():
            return False

        self.create_snapshots_dir(FileTrackerPaths.COMMANDS_SNAPSHOTS_DIRECTORY)
        tracked_commands_dict = self.get_tracked_items_dict(FileTrackerPaths.TRACKED_COMMANDS_JSON)
        assert type(
            tracked_commands_dict) is dict, "Assertion Error: 'tracked_commands_dict' is not in a dictionary format"
        changes_list = []

        try:
            self._create_tmp_cmd_out_dir()

            for cmd, hosts in list(tracked_commands_dict.items()):
                if self.is_relevant_for_current_host(hosts):
                    self._collect_data_for_cmd(cmd, changes_list)
                if len(changes_list) > 0:
                    if FileTrackerBase.data_store.get(self.get_host_name()):
                        FileTrackerBase.data_store[self.get_host_name()].extend(changes_list)
                    else:
                        FileTrackerBase.data_store[self.get_host_name()] = changes_list
        finally:
            self._delete_tmp_cmd_out_dir()

        return True

    def _collect_data_for_cmd(self, cmd, changes_list):
        cmd_snapshot_file_name = self.get_snapshot_name_by_cmd(cmd)
        tmp_cmd_out_file_path = "{tmp_cmd_out_dir}{cmd_name}_tmp".format(
            tmp_cmd_out_dir=FileTrackerPaths.TMP_CMD_OUT_DIR,
            cmd_name=cmd_snapshot_file_name)
        self.save_cmd_out_into_file(cmd, tmp_cmd_out_file_path)
        find_snapshot = self.file_utils.find_file_in_dir(FileTrackerPaths.COMMANDS_SNAPSHOTS_DIRECTORY,
                                                         cmd_snapshot_file_name)
        if find_snapshot:
            diff_output, return_code, err, diff_cmd = self._compare_cmd_out_file_to_snapshot(tmp_cmd_out_file_path,
                                                                                             cmd_snapshot_file_name)
            self._handle_diff_output_states(diff_output, return_code, err, diff_cmd, changes_list, cmd)
        else:
            file_tracker_logger.log(self, "There is no snapshot yet for the command '{}'".format(cmd))
            self.create_command_snapshot(cmd_snapshot_file_name, tmp_cmd_out_file_path, cmd, FileTrackerPaths.COMMANDS_SNAPSHOTS_DIRECTORY)
        self._delete_tmp_cmd_out_file(tmp_cmd_out_file_path)

    def _compare_cmd_out_file_to_snapshot(self, current_tmp_file, snapshot_file_name):
        diff_cmd = "sudo diff {snapshots_dir_path}{snapshot_file_name} {current_tmp_file_path}".format(
            current_tmp_file_path=current_tmp_file,
            snapshot_file_name=snapshot_file_name,
            snapshots_dir_path=FileTrackerPaths.COMMANDS_SNAPSHOTS_DIRECTORY)
        return_code, diff_output, err = self.run_cmd(diff_cmd)
        return diff_output, return_code, err, diff_cmd

    def create_command_snapshot(self, file_name, full_path, cmd, snapshots_dir, is_first_snapshot=True):
        self.preserve_and_copy(file_name, full_path, snapshots_dir)
        cmd_to_log = "command '{}'".format(cmd)
        self.log_new_snapshot(cmd_to_log, is_first_snapshot=is_first_snapshot, snapshots_dir=snapshots_dir)

    def _delete_tmp_cmd_out_dir(self):
        is_tmp_cmd_out_dir_exist = self.file_utils.is_dir_exist(FileTrackerPaths.TMP_CMD_OUT_DIR)
        if is_tmp_cmd_out_dir_exist:
            self.get_output_from_run_cmd("sudo rm -rf {}".format(FileTrackerPaths.TMP_CMD_OUT_DIR))

    def _delete_tmp_cmd_out_file(self, tmp_cmd_out_file_path):
        self.get_output_from_run_cmd(
            "sudo rm -f {tmp_cmd_out_file_path}".format(tmp_cmd_out_file_path=tmp_cmd_out_file_path))

    def _create_tmp_cmd_out_dir(self):
        self._create_tmp_dir(FileTrackerPaths.TMP_CMD_OUT_DIR)

    def _handle_diff_output_states(self, diff_output, return_code, err, diff_cmd, changes_list, cmd):
        if return_code > 1 or "command not found" in err:  # return_code > 1 means that the diff command was not successful
            raise UnExpectedSystemOutput(ip=self._host_executor.ip, cmd=diff_cmd, output=diff_output + err)
        else:
            if return_code == 1:  # return_code = 1 means that differences were found
                diff_output = DiffParser().parse_output(diff_output)
                timestamp = self._get_estimated_last_modify_timestamp_range()
                self._add_changes_to_list(cmd, timestamp, diff_output, changes_list)

    def _add_changes_to_list(self, cmd, timestamp_range, changes, changes_list):
        changes_by_lines = changes.split('\n')
        command_diffs_dict = {'command': cmd,
                              'estimated modify timestamp': timestamp_range,
                              'changes': changes_by_lines}
        changes_list.append(command_diffs_dict)
        file_tracker_logger.log(self, "Changes were found in the output of the command: '{}'".format(cmd))