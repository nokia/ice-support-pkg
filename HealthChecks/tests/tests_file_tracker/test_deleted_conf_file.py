from __future__ import absolute_import
from __future__ import print_function
import os

from flows_of_sys_operations.FileTracker.FileTrackerPaths import FileTrackerPaths
from tests.tests_file_tracker.FileTrackerBaseTest import FileTrackerBaseTest
from tools.global_enums import Severity, Objectives
import tools.sys_parameters as gs


class TestDeletedConfFile(FileTrackerBaseTest):

    expected_output = []
    role = ''
    conf_file_path = ''
    config_json_path = 'tests/tests_file_tracker/configurations_jsons/test_configurations.json'

    def set_document(self):
        self._unique_operation_name = "test_deleted_conf_file_{}".format(self.role)
        self._title = "Deleted configuration file"
        self._failed_msg = "expected change in results json of deleted conf file"
        self._severity = Severity.ERROR

    def set_up(self):
        FileTrackerBaseTest.set_up(self)
        self.copy_conf_files_dir()
        print ("Copy conf files done")
        self.run_file_tracker()

    def run_test(self):
        self.delete_conf_file()
        self.run_file_tracker()

    def test_assert(self):
        current_diff_file = self.convert_current_diff_file_to_list()
        assert current_diff_file, "File Tracker Test Failed - diff.json file is empty"
        fields_to_compare = ["full path", "is file exist"]
        self.compare_diff_outputs(fields_to_compare, self.expected_output, current_diff_file[-1])

    def delete_conf_file(self):
        cmd = "sudo mv '{}' '{}_backup'".format(self.conf_file_path, self.conf_file_path)
        gs.get_host_executor_factory().execute_cmd_by_roles([self.role], cmd)
        print("Delete file {} done".format(self.conf_file_path))

    def copy_conf_files_dir(self):
        pass

    def compare_diff_outputs(self, fields_to_compare, expected_output, current_diff_file):
        hosts_dict = gs.get_host_executor_factory()._host_executors_dict
        for host_name in hosts_dict:
            if self.role in hosts_dict[host_name].roles:
                for field in fields_to_compare:
                    print("Field '{}' is the same in both results files:".format(field))
                    print(expected_output[0][field] == current_diff_file[host_name][0][field])
                    assert expected_output[0][field] == current_diff_file[host_name][0][field], "File Tracker Test Failed - field '{}' is different between the files".format(field)


class TestDeletedConfFileOnUC(TestDeletedConfFile):

    expected_output = [
        {
            "full path": "/usr/share/ice/file_tracker_test/configuration_files/user_config.yaml",
            "file name": "user_config.yaml",
            "changes": [
                "The file /usr/share/ice/file_tracker_test/configuration_files/user_config.yaml was deleted from this directory.\nLast snapshot was taken on 2022-10-26 14:55:58 UTC"
            ],
            "is file exist": False,
            "modify timestamp": "2022-02-16 18:15:17"
        }
    ]

    role = Objectives.UC
    conf_file_path = "/usr/share/ice/file_tracker_test/configuration_files/user_config.yaml"

    def set_document(self):
        TestDeletedConfFile.set_document(self)
        self._title = "Deleted configuration file on undercloud"

    def copy_conf_files_dir(self):
        self._create_file_tracker_test_dir([Objectives.UC])
        source_path = "{}/ice/lib/HealthChecks/tests/tests_file_tracker/configuration_files/".format(self.home_dir)
        dest_path = "/usr/share/ice/file_tracker_test/configuration_files/"
        self.run_cmd("sudo cp -rp {source_path} {dest_path}".format(source_path=source_path, dest_path=dest_path))


class TestDeletedConfFileOnControllers(TestDeletedConfFile):

    expected_output = [
        {
            "full path": "/usr/share/ice/file_tracker_test/configuration_files/resolv.conf",
            "file name": "resolv.conf",
            "changes": [
                "The file /usr/share/ice/file_tracker_test/configuration_files/resolv.conf was deleted from this directory.\nLast snapshot was taken on 2022-10-26 14:55:58 UTC"
            ],
            "is file exist": False,
            "modify timestamp": "2022-02-16 18:15:17"
        }
    ]

    role = Objectives.CONTROLLERS
    conf_file_path = "/usr/share/ice/file_tracker_test/configuration_files/resolv.conf"

    def set_document(self):
        TestDeletedConfFile.set_document(self)
        self._title = "Deleted configuration file on controllers"

    def copy_conf_files_dir(self):
        self._create_file_tracker_test_dir([Objectives.CONTROLLERS])
        hosts_dict = gs.get_host_executor_factory()._host_executors_dict
        for host_name in hosts_dict:
            if self.role in hosts_dict[host_name].roles:
                self._copy_conf_files_dir_from_localhost_to_host_roles([Objectives.CONTROLLERS], hosts_dict[host_name].ip)