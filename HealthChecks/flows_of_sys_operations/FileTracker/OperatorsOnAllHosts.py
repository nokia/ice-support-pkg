from __future__ import absolute_import
import os

import tools.user_params
from flows_of_sys_operations.FileTracker.DiffParser import DiffParser
from flows_of_sys_operations.FileTracker.FileTrackerBase import FileTrackerBase
from flows_of_sys_operations.FileTracker.FileTrackerPaths import FileTrackerPaths
from flows_of_sys_operations.FileTracker.dynamic_diffs_collector import K8sResourceDataCollector
from tools.Exceptions import UnExpectedSystemOutput
from tools.global_enums import Objectives
import tools.sys_parameters as gs
from flows_of_sys_operations.FileTracker import FileTrackerLogging as file_tracker_logger


class SnapshotsUpdater(FileTrackerBase):
    objective_hosts = [Objectives.ALL_HOSTS, Objectives.HYP, Objectives.ALL_NODES, Objectives.MANAGERS,
                       Objectives.MONITOR, Objectives.DEPLOYER]

    def set_document(self):
        self._unique_operation_name = "update_snapshots"
        self._title = "Updating snapshots for configurations with changes"
        self._failed_msg = "Updating snapshots for configurations with changes failed"
        self._run_in_parallel = True
        self._prerequisite_unique_operation_name = "write_all_changes_to_json_file"

    def run_file_tracker_operator(self):
        try:
            host_name = self.get_host_name()
            if host_name not in list(FileTrackerBase.data_store.keys()):
                return True
            changes_list = FileTrackerBase.data_store[host_name]
            folders_changes = set()

            for change in changes_list:
                if change:
                    if 'full path' in list(change.keys()):
                        self._update_snapshot_for_file(change)
                    elif 'resource name' in list(change.keys()):
                        self._update_snapshot_for_resource(change)
                    elif 'added / deleted' in list(change.keys()):
                        folders_changes.add(change['folder path'])
                    elif 'command' in list(change.keys()):
                        self._update_snapshot_for_command(change)
                    else:
                        e = KeyError("The change must have 'file name' or 'resource name' or 'added / deleted' or "
                                     "'command' key")
                        self.update_log_on_failure(e.__str__().replace('\n', ' '))
                        raise e
            self._update_snapshots_for_folders(folders_changes)

            if not tools.user_params.debug:
                file_tracker_logger.log(self,
                                        "New snapshots were taken for all the configurations that were changed on this host")
            return True
        except Exception as e:
            self.update_log_on_failure(e.__str__().replace('\n', ' '))
            self._create_lock_file()
            self.update_log_on_failure(
                "The running on this host has stopped due to an error during updating snapshots.\n********************* File Tracker is locked for the next runs *********************",
                False)
            return False

    def _create_lock_file(self):
        cmd = "sudo touch {}".format(FileTrackerPaths.FILE_TRACKER_LOCKER)
        roles = [Objectives.UC, Objectives.ONE_MANAGER, Objectives.DEPLOYER]

        out = gs.get_host_executor_factory().execute_cmd_by_roles(roles, cmd, 10)
        host_name = list(out.keys())[0]
        if out[host_name]['exit_code'] == 0:
            return True
        raise UnExpectedSystemOutput(ip=self._host_executor.ip, cmd=cmd,
                                     output=out[host_name]['out'] + out[host_name]['err'])

    def _update_snapshot_for_file(self, change):
        full_path = change['full path']
        file_name_in_snapshots = self.get_snapshot_name_by_path(full_path)
        if 'Input/output error' in change['changes'][0]:
            self._update_file_snapshot_name(file_name_in_snapshots, change['modify timestamp'],
                                            FileTrackerPaths.SNAPSHOTS_DIRECTORY, 'unreadable')
        elif change['is file exist'] is False:
            self._update_file_snapshot_name(file_name_in_snapshots, change['modify timestamp'],
                                            FileTrackerPaths.SNAPSHOTS_DIRECTORY, 'deleted')
        elif self.file_utils.is_file_exist(full_path):
            self.create_new_snapshot(file_name_in_snapshots, full_path, is_first_snapshot=False)

    def _update_snapshot_for_resource(self, change):
        resource_name = change['resource name']
        resource_type = change['resource type']
        resource_namespace = change['namespace']
        resource_name_in_snapshots = "{}_{}_{}".format(resource_name, resource_type, resource_namespace)
        if change['is resource exist'] is False:
            self._update_file_snapshot_name(resource_name_in_snapshots, change['estimated modify timestamp'],
                                            FileTrackerPaths.DYNAMIC_SNAPSHOTS_DIRECTORY, 'deleted')
        else:
            file_path = os.path.join(FileTrackerPaths.DYNAMIC_SNAPSHOTS_DIRECTORY, resource_name_in_snapshots)
            find_resource, resource_yaml = self.run_data_collector_on_one_master(K8sResourceDataCollector,
                                                                                 resource_name=resource_name,
                                                                                 resource_type=resource_type,
                                                                                 resource_namespace=resource_namespace)
            self.create_new_dynamic_snapshot(resource_name, resource_type, resource_yaml, file_path)

    def _update_snapshots_for_folders(self, folders_changes):
        for folder_path in folders_changes:
            snapshot_file_name = self.get_snapshot_name_for_folder(folder_path)
            folder_exist = True if self.file_utils.is_dir_exist(folder_path) else False

            self.create_snapshot_for_folder(
                folder_path, os.path.join(FileTrackerPaths.FOLDERS_SNAPSHOTS_DIRECTORY, snapshot_file_name),
                is_first_snapshot=False,
                is_folder_exist=folder_exist)

    def _update_snapshot_for_command(self, change):
        cmd = change['command']
        cmd_name_in_snapshots = self.get_snapshot_name_by_cmd(cmd)
        snapshot_file_path = os.path.join(FileTrackerPaths.COMMANDS_SNAPSHOTS_DIRECTORY, cmd_name_in_snapshots)
        self.save_cmd_out_into_file(cmd, snapshot_file_path)
        cmd_to_log = "command '{}'".format(cmd)
        self.log_new_snapshot(cmd_to_log, is_first_snapshot=False,
                              snapshots_dir=FileTrackerPaths.COMMANDS_SNAPSHOTS_DIRECTORY)

    def _update_file_snapshot_name(self, file_name_in_snapshots, timestamp, snapshots_dir_path, keyword):
        converted_timestamp = timestamp.replace(" ", "_")
        snapshot_path = snapshots_dir_path + file_name_in_snapshots
        self.get_output_from_run_cmd(
            "nice -n 4 sudo mv {} {}_{}_{}".format(snapshot_path, snapshot_path, keyword, converted_timestamp))


class DiffsCollector(FileTrackerBase):
    objective_hosts = [Objectives.ALL_HOSTS, Objectives.HYP, Objectives.ALL_NODES, Objectives.MANAGERS,
                       Objectives.DEPLOYER]
    host_roles = None

    def set_document(self):
        self._unique_operation_name = "collect_diffs"
        self._title = "Collecting diffs in configuration files"
        self._failed_msg = "Collecting diffs in files failed"
        self._run_in_parallel = True
        self._prerequisite_unique_operation_name = "file_tracker_pre_running"
        self._ignore_changes_in_permissions = False

    def run_file_tracker_operator(self):
        if not self.verify_free_disk_space():
            return False
        changes_list = []
        self.host_roles = self.get_host_roles()
        self.create_ice_dir()
        self.create_file_tracker_dir()
        self.create_snapshots_dir(FileTrackerPaths.SNAPSHOTS_DIRECTORY)

        conf_files_dict = self.get_tracked_items_dict(FileTrackerPaths.CONF_FILES_JSON)
        assert type(conf_files_dict) is dict, "Not a dictionary format"

        for file_name, file_name_paths_dict in list(conf_files_dict.items()):
            assert type(file_name_paths_dict) is dict, "Not a dictionary format"
            for dir_path, file_hosts in list(file_name_paths_dict.items()):
                assert dir_path[-1] == '/', "Add / at the end of the path:{}".format(dir_path)
                self._collect_data_for_file_path(dir_path, file_name, file_hosts, changes_list)
        if len(changes_list) > 0:
            changes_list = self.sort_change_list_by_modify_timestamp(changes_list=changes_list)
            FileTrackerBase.data_store[self.get_host_name()] = changes_list
        return True

    def _collect_data_for_file_path(self, dir_path, file_name, file_hosts, changes_list):
        full_path = dir_path + file_name
        file_name_in_snapshots = self.get_snapshot_name_by_path(full_path)

        if self.is_relevant_for_current_host(file_hosts):
            if not self.file_utils.is_dir_exist(dir_path):
                if tools.user_params.debug:
                    file_tracker_logger.log(self, "The directory path {} does not exist".format(dir_path))
                return
            find_snapshot = self.file_utils.find_file_in_dir(FileTrackerPaths.SNAPSHOTS_DIRECTORY,
                                                             file_name_in_snapshots)
            if find_snapshot:
                find_conf_file = self.file_utils.find_file_in_dir(dir_path, file_name)
                if find_conf_file:
                    if not self.file_utils.is_file_readable(full_path):
                        self._handle_unreadable_conf_file(full_path, file_name, changes_list)
                    else:
                        diff_output, return_code, err, cmd = self._compare_conf_file_to_snapshot(full_path,
                                                                                                 file_name_in_snapshots)
                        diff_permissions_output = self._compare_files_permissions(full_path, file_name_in_snapshots)
                        if self._is_ignore_changes_in_permissions_from_diff(file_name_in_snapshots,
                                                                            diff_permissions_output):
                            diff_permissions_output = ""
                            self.create_new_snapshot(file_name_in_snapshots, full_path, is_first_snapshot=False)
                        self._handle_diff_output_states(diff_output, diff_permissions_output, return_code, err, cmd,
                                                        full_path,
                                                        file_name,
                                                        changes_list)
                else:
                    timestamp, diff_output = self._handle_deleted_conf_file(find_snapshot.replace('\n', ''), full_path)
                    self._add_changes_to_list(full_path, file_name, timestamp, diff_output, changes_list,
                                              is_file_exist=False)
            else:
                find_conf_file = self.file_utils.find_file_in_dir(dir_path, file_name)
                if find_conf_file and self.file_utils.is_file_readable(full_path):
                    file_tracker_logger.log(self, "There is no snapshot yet for {}".format(full_path))
                    self.create_new_snapshot(file_name_in_snapshots, full_path)
                elif not find_conf_file:
                    if tools.user_params.debug:
                        file_tracker_logger.log(self, "No such file in path: {}".format(full_path))

    def _compare_conf_file_to_snapshot(self, full_path, file_name):
        diff_cmd = "sudo diff {snapshots_dir_path}{file_name} {full_path}".format(full_path=full_path,
                                                                                  file_name=file_name,
                                                                                  snapshots_dir_path=FileTrackerPaths.SNAPSHOTS_DIRECTORY)
        return_code, diff_output, err = self.run_cmd(diff_cmd)
        return diff_output, return_code, err, diff_cmd

    def _handle_diff_output_states(self, diff_output, diff_permissions_output, return_code, err, cmd, full_path,
                                   file_name,
                                   changes_list):
        if return_code > 1 or "command not found" in err:  # return_code > 1 means that the diff command was not successful
            raise UnExpectedSystemOutput(ip=self._host_executor.ip, cmd=cmd, output=diff_output + err)
        else:
            is_change_found = False
            total_changes = diff_permissions_output
            if return_code == 1:  # return_code = 1 means that differences were found
                diff_output = DiffParser().parse_output(diff_output)
                total_changes = diff_permissions_output + diff_output
                is_change_found = True
            if is_change_found or total_changes != "":
                timestamp = self._get_last_file_change_timestamp(full_path)
                self._add_changes_to_list(full_path, file_name, timestamp, total_changes, changes_list)

    def _add_changes_to_list(self, full_path, file_name, timestamp, changes, changes_list, is_file_exist=True):
        changes_by_lines = changes.split('\n')
        conf_file_diffs_dict = {'file name': file_name, 'full path': full_path, 'modify timestamp': timestamp,
                                'changes': changes_by_lines, 'is file exist': is_file_exist}
        changes_list.append(conf_file_diffs_dict)
        file_tracker_logger.log(self, "Changes were found in {}".format(full_path))

    def _is_ignore_changes_in_permissions_from_diff(self, file_name_in_snapshots, diff_permissions_output):
        if diff_permissions_output != "":
            if FileTrackerBase.IGNORE_CHANGES_IN_PERMISSIONS and self._check_if_snapshot_permissions_are_wrongly_too_open(
                    file_name_in_snapshots):
                return True
        return False

    def _compare_files_permissions(self, conf_file_path, snapshot_file_name):
        permissions_output = ""
        permissions_changed = False
        snapshot_file_path = FileTrackerPaths.SNAPSHOTS_DIRECTORY + snapshot_file_name
        conf_file_permissions_dict = self.file_utils.get_file_permissions_dict(conf_file_path)
        snapshot_permissions_dict = self.file_utils.get_file_permissions_dict(snapshot_file_path)
        compare_keys_list = [key for key in list(snapshot_permissions_dict.keys()) if 'id' in key]
        for key in compare_keys_list:
            if int(conf_file_permissions_dict[key]) != int(snapshot_permissions_dict[key]):
                permissions_changed = True
        if permissions_changed:
            conf_file_permission_str = "{} {} | User: {} {} | Group: {} {}".format(
                *list(conf_file_permissions_dict.values()))
            snapshot_permission_str = "{} {} | User: {} {} | Group: {} {}".format(
                *list(snapshot_permissions_dict.values()))
            permissions_output = "********************************\nFile's permissions have changed:\nOld Permissions: {}\nNew Permissions: {}\n********************************\n".format(
                snapshot_permission_str, conf_file_permission_str)
        return permissions_output

    def _check_if_snapshot_permissions_are_wrongly_too_open(self, file_name_in_snapshots):
        snapshot_permissions = self.file_utils.get_file_permission_id(
            FileTrackerPaths.SNAPSHOTS_DIRECTORY + file_name_in_snapshots)
        if int(snapshot_permissions) == int(self.file_utils.OPENED_PERMISSIONS):
            return True
        else:
            return False

    def _handle_unreadable_conf_file(self, full_path, file_name, changes_list):
        unreadable_file_change = "The file is not readable due to an Input/output error"
        timestamp = self._get_last_file_change_timestamp(full_path)
        self._add_changes_to_list(full_path, file_name, timestamp, unreadable_file_change, changes_list)
        if tools.user_params.debug:
            file_tracker_logger.log(self, "Cannot check the file {} due to an Input/output error".format(full_path))


class FoldersDiffsCollector(FileTrackerBase):
    objective_hosts = [Objectives.ALL_NODES, Objectives.MANAGERS, Objectives.DEPLOYER, Objectives.ALL_HOSTS,
                       Objectives.UC, Objectives.HYP]

    def set_document(self):
        self._unique_operation_name = "collect_diffs_for_folders"
        self._title = "Collecting diffs in folders"
        self._failed_msg = "Collecting diffs in folders failed"
        self._run_in_parallel = True
        self._prerequisite_unique_operation_name = "file_tracker_pre_running"
        self._ignore_changes_in_permissions = False

    def run_file_tracker_operator(self):
        if not self.verify_free_disk_space():
            return False

        self.create_ice_dir()
        self.create_file_tracker_dir()
        self.create_snapshots_dir(FileTrackerPaths.FOLDERS_SNAPSHOTS_DIRECTORY)
        tracked_folders_dict = self.get_tracked_items_dict(FileTrackerPaths.TRACKED_FOLDERS_JSON)
        changes_list = []

        for folder_path, hosts in list(tracked_folders_dict.items()):
            if self.is_relevant_for_current_host(hosts):
                folder_content = set(self.file_utils.get_dir_content(folder_path))
                snapshot_file_name = self.get_snapshot_name_for_folder(folder_path)
                find_snapshot = self.file_utils.find_file_in_dir(FileTrackerPaths.FOLDERS_SNAPSHOTS_DIRECTORY,
                                                                 snapshot_file_name)
                is_folder_exist = self.file_utils.is_dir_exist(folder_path)

                if find_snapshot:
                    snapshot_content = set(self.file_utils.read_file(os.path.join(
                        FileTrackerPaths.FOLDERS_SNAPSHOTS_DIRECTORY, snapshot_file_name)).split())
                    new_files = folder_content - snapshot_content
                    deleted_files = snapshot_content - folder_content
                    self._update_change("Added", folder_path, new_files, find_snapshot, changes_list)
                    self._update_change("Deleted", folder_path, deleted_files, find_snapshot, changes_list)
                    if new_files or deleted_files:
                        file_tracker_logger.log(self, "Changes were found in folder {}".format(folder_path))

                elif is_folder_exist:
                    self.create_snapshot_for_folder(
                        folder_path, os.path.join(FileTrackerPaths.FOLDERS_SNAPSHOTS_DIRECTORY, snapshot_file_name),
                        is_first_snapshot=True)

        if len(changes_list) > 0:
            FileTrackerBase.data_store[self.get_host_name()] = FileTrackerBase.data_store.get(self.get_host_name(), []) \
                                                               + changes_list

        return True

    def _update_change(self, change, folder_path, files_names_list, find_snapshot, changes_list):
        for f in files_names_list:
            if change == "Added":
                timestamp = self._get_last_file_change_timestamp(os.path.join(folder_path, f))
            else:
                timestamp, change = self._handle_deleted_conf_file(find_snapshot.replace('\n', ''),
                                                                   os.path.join(folder_path, f))
            changes_list.append({
                "modify timestamp": timestamp,
                "folder path": folder_path,
                "file name": f,
                "added / deleted": change
            })
