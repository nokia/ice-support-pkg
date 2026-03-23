from __future__ import absolute_import
from datetime import datetime
import tools.sys_parameters as gs
from tools.ExecutionModule.execution_helper import ExecutionHelper
from tools.global_enums import Objectives
import os
from tools.global_enums import Deployment_type
from tools.sys_toolkit import HTMLPrint
import json
import tools.global_logging as log


class SummaryFilesOperations:
    def __init__(self, prefix='HealthChecksSummary', out_path=None, cluster_name=""):
        if cluster_name != "" and cluster_name is not None:
            prefix = "{}_{}".format(cluster_name, prefix)
        self.creation_date = datetime.now().strftime("%Y-%m-%d_%H-%M")
        self.file_prefix = "{}_{}".format(prefix, self.creation_date)
        if not out_path:
            self.local_files_dir = self._set_local_files_dir()
        else:
            self.local_files_dir = out_path

        self.create_local_health_check_file_dir()

    def _set_hv_files_dir(self, hv_host_executor):
        if hv_host_executor.user_name == 'root':
            return '/root/HealthCheckFiles'
        else:
            return '/home/{}/HealthCheckFiles'.format(hv_host_executor.user_name)

    def _set_local_files_dir(self):
        if ExecutionHelper.is_run_inside_container():
            path = os.environ["OUT_FILES_DIR"]
        else:
            path = os.path.join(os.path.expanduser("~"), "HealthCheckFiles")
        return path

    def get_supported_formats(self):
        return ['html', 'json', 'log']

    def get_out_file_path(self, parent_dir, file_format):
        return "{}/{}.{}".format(parent_dir, self.file_prefix, file_format)

    def create_local_health_check_file_dir(self):
        local_operator = ExecutionHelper.get_local_operator(False)
        if not local_operator.file_utils.is_file_exist(self.local_files_dir):
            local_operator.get_output_from_run_cmd("sudo mkdir {}".format(self.local_files_dir))
        local_operator.get_output_from_run_cmd("sudo chmod 777 {}".format(self.local_files_dir))

    def copy_files_to_hv(self, hv_host_executor, hv_files_dir):
        assert hv_host_executor.is_connected

        source_dest_dict = {}
        for postfix in self.get_supported_formats():
            source_path = self.get_out_file_path(self.local_files_dir, postfix)
            dest_path = self.get_out_file_path(hv_files_dir, postfix)
            source_dest_dict[source_path] = dest_path

        gs.get_host_executor_factory().run_command_on_first_host_from_selected_roles(
            'mkdir -p {}'.format(hv_files_dir), [Objectives.HYP])
        for source_path, dest_path in list(source_dest_dict.items()):
            cmd = 'scp -q -o "StrictHostKeyChecking no" stack@uc:{uc_path} {hv_path}'.format(
                uc_path=source_path, hv_path=dest_path)
            gs.get_host_executor_factory().run_command_on_first_host_from_selected_roles(cmd, [Objectives.HYP])
        log.log_and_print(
            "\nFiles were copied successfully to Hypervisor:\n{}".format('\n'.join(list(source_dest_dict.values()))))

    def create_tar_file_on_hv(self, hv_host_executor, hv_files_dir):
        assert hv_host_executor.is_connected
        tar_full_path = self.get_out_file_path(hv_files_dir, 'tar.gz')
        source_pattern = self.get_out_file_path(hv_files_dir, '*')
        tar_cmd = 'tar -zcvf {dest} {source}'.format(dest=tar_full_path, source=source_pattern)
        gs.get_host_executor_factory().run_command_on_first_host_from_selected_roles(tar_cmd, [Objectives.HYP])
        log.log_and_print("\nA tar file was created on HV: \n{}".format(tar_full_path))

    def perform_hv_operations(self, deployment_type):
        assert deployment_type == Deployment_type.CBIS
        hv_host_executor_dict = gs.get_host_executor_factory().get_host_executors_by_roles(roles=[Objectives.HYP])
        assert len(hv_host_executor_dict)
        hv_host_executor = list(hv_host_executor_dict.values())[0]
        hv_files_dir = self._set_hv_files_dir(hv_host_executor)
        if not hv_host_executor.is_connected:
            return False, "Could not copy files to HV- HV is not connected!"
        try:
            self.copy_files_to_hv(hv_host_executor, hv_files_dir)
            self.create_tar_file_on_hv(hv_host_executor, hv_files_dir)
            return True, ""
        except Exception as e:
            return False, str(e)

    def create_out_files(self, deployment_type, version, sub_version, build, bcmt_build, hotfix_list, roles_map, ice_version,
                         ice_version_date, result_dict, creation_date, cluster_name):
        html_path = self.get_out_file_path(self.local_files_dir, 'html')
        json_path = self.get_out_file_path(self.local_files_dir, 'json')
        log_path = self.get_out_file_path(self.local_files_dir, 'log')
        
        HTMLPrint.create_validation_summary_html(
            result_dict, html_path, version, sub_version, build, bcmt_build, deployment_type, hotfix_list, roles_map, ice_version,
            ice_version_date, creation_date, cluster_name)

        with open(json_path, 'w') as outfile:
            json.dump(result_dict, outfile, indent=4)
        host_name = ExecutionHelper.get_local_host_name()
        if deployment_type == Deployment_type.CBIS:
            host_name = host_name.split('.')[0]
        log.log_and_print("Out Files were created on {}: \n{}\n{}\n{}\n".format(host_name, log_path, html_path, json_path))
        log.log_and_print("-------------------------------------------------------------------------------------------------------------------------------\n")

    def get_logger_path(self):
        return self.get_out_file_path(self.local_files_dir, 'log')

    def run(self, deployment_type, version, sub_version, build, bcmt_build, hotfix_list, roles_map,
            ice_version, ice_version_date, result_dict, cluster_name):
        self.create_out_files(deployment_type, version, sub_version, build, bcmt_build, hotfix_list, roles_map, ice_version,
                              ice_version_date, result_dict, self.creation_date, cluster_name)
        if deployment_type == Deployment_type.CBIS:
            is_ok, msg = self.perform_hv_operations(deployment_type)
            if not is_ok:
                return False, msg
        return True, ""

