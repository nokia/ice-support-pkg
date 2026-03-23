from __future__ import absolute_import
from __future__ import print_function
import os

import tools.user_params
from HealthCheckCommon.operations import *
from HealthCheckCommon.validator import Validator
from flows_of_sys_operations.FileTracker.FileTrackerPaths import FileTrackerPaths, FileTrackerPathsInitiator
from tools.global_enums import *


class FileTrackerBaseTest(Validator):

    objective_hosts = {
        Deployment_type.CBIS: [Objectives.UC]
    }

    config_json_path = ''
    home_dir = os.environ['HOME']

    def set_document(self):
        raise NotImplementedError

    def is_validation_passed(self):
        self.set_up()
        self.run_test()
        self.test_assert()
        self.cleanup()

        return True

    def set_up(self):
        print("************** Start test " + self._title + "*************")
        tools.user_params.config_json_path = self.config_json_path
        FileTrackerPathsInitiator()
        self._delete_file_tracker_test_dir()
        assert not self.run_cmd_return_is_successful("cd /usr/share/ice/file_tracker_test/"), "'file_tracker_test' directory already exists"
        print("Set up stage is done")

    def run_test(self):
        pass

    def test_assert(self):
        pass

    def cleanup(self):
        print ("Start cleanup after test")
        self._delete_file_tracker_test_dir()
        print("************** Test " + self._title + " finished *************")

    def run_file_tracker(self):
        self.run_cmd(
            "cd {home_dir}; cd; source ./icerc; ice filetracker runOnce --config-json-path '{path}'".format(home_dir=self.home_dir, path=self.config_json_path), timeout=600)

    def convert_current_diff_file_to_list(self):
        current_diff_file_to_list = []
        cmd = "sudo cat {}".format(FileTrackerPaths.DIFFERENCES_SUMMARY_FILE)
        return_code, current_diff_file, err = self.run_cmd(cmd)
        if return_code == 0:
            if current_diff_file:
                try:
                    current_diff_file_to_list = json.loads(current_diff_file)
                except:
                    raise ValueError("The value is not in JSON format")
        return current_diff_file_to_list

    def _create_file_tracker_test_dir(self, roles_list):
        # CAUTION: Similar functionality might exist elsewhere, requiring synchronization to maintain consistency across the codebase.
        mkdir_cmd = "sudo mkdir /usr/share/ice/file_tracker_test/"
        if Objectives.UC in roles_list or Objectives.ONE_MANAGER in roles_list:
            self.run_cmd(mkdir_cmd)
        else:
            gs.get_host_executor_factory().execute_cmd_by_roles(roles_list, mkdir_cmd)

    def _delete_file_tracker_test_dir(self):
        #TODO - add check if the dir exists, and remove it only if it does
        rm_cmd = "sudo rm -rf /usr/share/ice/file_tracker_test/"
        #TODO - apply this command on NCS hosts also
        gs.get_host_executor_factory().execute_cmd_by_roles([Objectives.CONTROLLERS, Objectives.HYP, Objectives.COMPUTES, Objectives.STORAGE, Objectives.MONITOR], rm_cmd)
        self.run_cmd(rm_cmd)
        print ("Deleted file tracker test directory on all hosts")

    def _copy_conf_files_dir_from_localhost_to_host_roles(self, roles_list, host_ip):
        source_path = "{}/ice/lib/HealthChecks/tests/tests_file_tracker/configuration_files/".format(self.home_dir)
        temp_dest_path = "/tmp/configuration_files/"
        dest_path = "/usr/share/ice/file_tracker_test/configuration_files/"
        self.run_cmd("scp -rp {source_path} cbis-admin@{host_ip}:{dest_path}".format(source_path=source_path, host_ip=host_ip, dest_path=temp_dest_path))
        mv_cmd = "sudo mv {source_path} {dest_path}".format(source_path=temp_dest_path, dest_path=dest_path)
        gs.get_host_executor_factory().execute_cmd_by_roles(roles_list, mv_cmd)




