from __future__ import absolute_import
import os
from time import sleep

import tools.user_params
from HealthCheckCommon.operations import DataCollector
from flows_of_sys_operations.FileTracker.DiffParser import DiffParser
from flows_of_sys_operations.FileTracker.FileTrackerBase import FileTrackerBase
from flows_of_sys_operations.FileTracker.FileTrackerPaths import FileTrackerPaths
from tools.Exceptions import UnExpectedSystemOutput
from tools.global_enums import Objectives
import tools.sys_parameters as gs
from flows_of_sys_operations.FileTracker import FileTrackerLogging as file_tracker_logger


class K8sResourceDataCollector(DataCollector):
    objective_hosts = [Objectives.ONE_MASTER]
    hosts_cached_pool = {}

    def collect_data(self, resource_name, resource_type, resource_namespace):
        find_resource = self._is_resource_exist(resource_name, resource_type, resource_namespace)

        if not find_resource:
            return False, None

        try:
            resource_yaml_content = self._get_resource_yaml(resource_name, resource_type, resource_namespace)
        except UnExpectedSystemOutput:
            # sleep to not run k8s when it's busy from the previous k8s command,
            # this is only a try to fix:
            # runtime: unexpected return pc for runtime.systemstack_switch called from 0xc000493200
            # if you find this issue after this change pls try another solution.
            sleep(1)
            resource_yaml_content = self._get_resource_yaml(resource_name, resource_type, resource_namespace)

        return True, resource_yaml_content

    def _get_resource_yaml(self, resource_name, resource_type, resource_namespace):
        return self.get_output_from_run_cmd(
            "sudo bash -c 'nice -n 4 sudo kubectl get {resource_type} {resource_name} -n {namespace} -o yaml'".format(
                resource_name=resource_name, resource_type=resource_type, namespace=resource_namespace))

    def _is_resource_exist(self, resource_name, resource_type, resource_namespace):
        cmd = "sudo kubectl get {resource_type} -n {namespace} --output jsonpath='{{.items[*].metadata.name}}'".format(
            resource_type=resource_type, namespace=resource_namespace)
        resources = self.get_output_from_run_cmd(cmd, hosts_cached_pool=K8sResourceDataCollector.hosts_cached_pool).split()

        return resource_name in resources


class IsValidChange(DataCollector):
    objective_hosts = [Objectives.ONE_MASTER]

    def collect_data(self, resource_name, resource_type, namespace):
        return_code, out, err = self.run_cmd(
            "sudo kubectl get pods -n {namespace} | grep {resource_name} | grep CrashLoopBackOff".format(
                namespace=namespace, resource_name=resource_name))
        if return_code == 0:
            if out:
                if tools.user_params.debug:
                    file_tracker_logger.log(
                        self, "Ignore changes in {} '{}' in namespace {}, "
                              "due to at least one pod that is in a 'CrashLoopBackOff' state".format(resource_type,
                                                                                                     resource_name,
                                                                                                     namespace))
                return False
        return True


class DynamicDiffsCollector(FileTrackerBase):
    objective_hosts = [Objectives.ONE_MANAGER, Objectives.DEPLOYER]

    def set_document(self):
        self._unique_operation_name = "collect_diffs_in_dynamic_resources"
        self._title = "Collecting diffs in dynamic resources"
        self._failed_msg = "Collecting diffs in dynamic resources failed"
        self._run_in_parallel = False
        self._prerequisite_unique_operation_name = "file_tracker_pre_running"

    def is_prerequisite_fulfilled(self):
        return len(gs.get_host_executor_factory().get_host_executors_by_roles(Objectives.MASTERS)) > 0

    def run_file_tracker_operator(self):
        if not self.verify_free_disk_space():
            return False
        changes_list = []
        self.create_ice_dir()
        self.create_file_tracker_dir()
        self._create_dynamic_snapshots_dir()
        try:
            self._create_tmp_yaml_dir()
            dynamic_resources_dict = self.get_tracked_items_dict(FileTrackerPaths.DYNAMIC_RESOURCES_JSON)
            assert type(dynamic_resources_dict) is dict, "Assertion Error: 'dynamic_resources_dict' is not a dictionary format"

            for resource_name, resource_details_dict in list(dynamic_resources_dict.items()):
                assert type(resource_details_dict) is dict, "Assertion Error: 'resource_details_dict' is not a dictionary format"
                self._collect_data_for_resource_name(resource_name, resource_details_dict, changes_list)
            if len(changes_list) > 0:
                if FileTrackerBase.data_store.get(self.get_host_name()):
                    FileTrackerBase.data_store[self.get_host_name()].extend(changes_list)
                else:
                    FileTrackerBase.data_store[self.get_host_name()] = changes_list
        finally:
            K8sResourceDataCollector.hosts_cached_pool = {}
            self._delete_tmp_yaml_dir()
        return True

    def _collect_data_for_resource_name(self, resource_name, resource_details_dict, changes_list):
        for resource_type, resource_namespace in list(resource_details_dict.items()):
            resource_name_in_snapshots = "{}_{}_{}".format(resource_name, resource_type, resource_namespace)
            dynamic_snapshot_path = os.path.join(FileTrackerPaths.DYNAMIC_SNAPSHOTS_DIRECTORY,
                                                 resource_name_in_snapshots)

            find_snapshot = self.file_utils.find_file_in_dir(FileTrackerPaths.DYNAMIC_SNAPSHOTS_DIRECTORY,
                                                             resource_name_in_snapshots)
            find_resource, resource_yaml = self.run_data_collector_on_one_master(K8sResourceDataCollector,
                                                                                 resource_name=resource_name,
                                                                                 resource_type=resource_type,
                                                                                 resource_namespace=resource_namespace)
            if find_snapshot:
                if find_resource:
                    tmp_yaml_path = "{tmp_yaml_dir}{resource_name}_tmp.yaml".format(
                        tmp_yaml_dir=FileTrackerPaths.TMP_YAML_DIR, resource_name=resource_name)
                    self._create_tmp_yaml_for_resource(resource_name, resource_type, resource_yaml, tmp_yaml_path)
                    if not self.file_utils.is_file_exist(tmp_yaml_path):
                        return
                    diff_output, return_code, err, cmd = self._compare_tmp_yaml_to_snapshot(tmp_yaml_path,
                                                                                            dynamic_snapshot_path)
                    self._handle_diff_output_states(diff_output, return_code, err, cmd, resource_type,
                                                    resource_namespace, resource_name, changes_list, tmp_yaml_path)
                    self._delete_tmp_yaml_file(tmp_yaml_path)
                else:
                    timestamp, diff_output = self._handle_deleted_resource(dynamic_snapshot_path, resource_name,
                                                                           resource_type)
                    self._add_changes_to_list(resource_name, resource_type, resource_namespace, timestamp, diff_output,
                                              changes_list,
                                              is_resource_exist=False)
            else:
                if find_resource:
                    file_tracker_logger.log(self, "There is no snapshot yet for {} {}".format(resource_type,
                                                                                              resource_name))
                    self.create_new_dynamic_snapshot(resource_name, resource_type, resource_yaml,
                                                     dynamic_snapshot_path, add_log_message=True)
                else:
                    if tools.user_params.debug:
                        file_tracker_logger.log(self, "No such {} '{}' in namespace {}".format(resource_type, resource_name,
                                                                                               resource_namespace))

    def _create_dynamic_snapshots_dir(self):
        is_snapshots_dir_exist = self.file_utils.is_dir_exist(FileTrackerPaths.DYNAMIC_SNAPSHOTS_DIRECTORY)
        self.get_output_from_run_cmd("sudo mkdir -p {}".format(FileTrackerPaths.DYNAMIC_SNAPSHOTS_DIRECTORY))
        self.file_utils.change_file_owner(self._host_executor.user_name, FileTrackerPaths.DYNAMIC_SNAPSHOTS_DIRECTORY)
        if self.parse_to_int(self.file_utils.get_file_permission_id(FileTrackerPaths.DYNAMIC_SNAPSHOTS_DIRECTORY)) == int(self.file_utils.OPENED_PERMISSIONS):
            self.file_utils.change_file_permissions(permissions='775', file_path=FileTrackerPaths.DYNAMIC_SNAPSHOTS_DIRECTORY)
        if not is_snapshots_dir_exist:
            file_tracker_logger.log(self, "{} was not exist. The dynamic snapshots directory was created".format(
                FileTrackerPaths.DYNAMIC_SNAPSHOTS_DIRECTORY))

    def _handle_diff_output_states(self, diff_output, return_code, err, cmd, resource_type, namespace, resource_name,
                                   changes_list, tmp_yaml_path):
        if return_code > 1 or "command not found" in err:  # return_code > 1 means that the diff command was not successful
            raise UnExpectedSystemOutput(ip=self._host_executor.ip, cmd=cmd, output=diff_output + err)
        else:
            if return_code == 1:  # return_code = 1 means that differences were found
                if self._is_valid_change(resource_name, resource_type, namespace):
                    diff_output = DiffParser().parse_output(diff_output)
                    timestamp = self._get_estimated_last_modify_timestamp_range()
                    self._add_changes_to_list(resource_name, resource_type, namespace, timestamp, diff_output, changes_list)

    def _add_changes_to_list(self, resource_name, resource_type, namespace, timestamp_range, changes, changes_list,
                             is_resource_exist=True):
        changes_by_lines = changes.split('\n')
        resource_diffs_dict = {'resource name': resource_name, 'resource type': resource_type, 'namespace': namespace,
                               'estimated modify timestamp': timestamp_range,
                               'changes': changes_by_lines, 'is resource exist': is_resource_exist}
        changes_list.append(resource_diffs_dict)
        file_tracker_logger.log(self,
                                "Changes were found in {} '{}' in namespace {}".format(resource_type, resource_name,
                                                                                       namespace))

    def _handle_deleted_resource(self, dynamic_snapshot_path, resource_name, resource_type):
        timestamp = self.get_output_from_run_cmd("date +'{}'".format(self.DATE_FORMAT)).replace('\n', '')
        last_snapshot_timestamp = self._get_last_file_change_timestamp(dynamic_snapshot_path)
        diff_output = "The {} '{}' was deleted.\nLast snapshot was taken on {}".format(resource_type, resource_name,
                                                                                       last_snapshot_timestamp)
        return timestamp, diff_output

    def _create_tmp_yaml_for_resource(self, resource_name, resource_type, resource_yaml, tmp_yaml_path):
        self.create_new_dynamic_snapshot(resource_name, resource_type, resource_yaml, tmp_yaml_path,
                                         add_log_message=False)

    def _compare_tmp_yaml_to_snapshot(self, tmp_yaml_path, dynamic_snapshot_path):
        diff_cmd = "sudo diff {dynamic_snapshot_path} {tmp_yaml_path}".format(
            tmp_yaml_path=tmp_yaml_path, dynamic_snapshot_path=dynamic_snapshot_path)
        return_code, diff_output, err = self.run_cmd(diff_cmd)
        return diff_output, return_code, err, diff_cmd

    def _delete_tmp_yaml_file(self, tmp_yaml_path):
        self.get_output_from_run_cmd("sudo rm -f {tmp_yaml_path}".format(tmp_yaml_path=tmp_yaml_path))

    def _create_tmp_yaml_dir(self):
        self._create_tmp_dir(FileTrackerPaths.TMP_YAML_DIR)
            
    def _delete_tmp_yaml_dir(self):
        is_tmp_yaml_dir_exist = self.file_utils.is_dir_exist(FileTrackerPaths.TMP_YAML_DIR)
        if is_tmp_yaml_dir_exist:
            self.get_output_from_run_cmd("sudo rm -rf {}".format(FileTrackerPaths.TMP_YAML_DIR))

    def _is_valid_change(self, resource_name, resource_type, namespace):
        return self.run_data_collector_on_one_master(IsValidChange, resource_name=resource_name,
                                                     resource_type=resource_type, namespace=namespace)
