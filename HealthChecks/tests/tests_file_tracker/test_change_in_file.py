from __future__ import absolute_import
from __future__ import print_function
import os

from tests.tests_file_tracker.FileTrackerBaseTest import FileTrackerBaseTest
from tools.global_enums import Severity, Objectives
import tools.sys_parameters as gs


class TestChangeInFile(FileTrackerBaseTest):

    expected_output = []
    role = ''
    conf_file_path = ''
    config_json_path = 'tests/tests_file_tracker/configurations_jsons/test_configurations.json'

    def set_document(self):
        self._unique_operation_name = "test_change_in_file_{}".format(self.role)
        self._title = "Change in file"
        self._failed_msg = "expected change in file"
        self._severity = Severity.ERROR

    def set_up(self):
        FileTrackerBaseTest.set_up(self)
        self.copy_conf_files_dir()
        print ("Copy conf files done")
        self.run_file_tracker()
        print ("First File Tracker run done")

    def run_test(self):
        self.make_change_in_conf_file()
        self.run_file_tracker()

    def test_assert(self):
        current_diff_file = self.convert_current_diff_file_to_list()
        assert current_diff_file, "File Tracker Test Failed - diff.json file is empty"
        fields_to_compare = ["full path", "changes"]
        self.compare_diff_outputs(fields_to_compare, self.expected_output, current_diff_file[-1])

    def make_change_in_conf_file(self):
        cmd = "echo '### test line' >> {}".format(self.conf_file_path)
        gs.get_host_executor_factory().execute_cmd_by_roles([self.role], cmd)
        print("Make a change in {} done".format(self.conf_file_path))

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


class TestChangeInFileOnUC(TestChangeInFile):

    expected_output = [
        {
            "full path": "/usr/share/ice/file_tracker_test/configuration_files/user_config.yaml",
            "file name": "user_config.yaml",
            "changes": [
                "",
                "Line 565 was added:",
                "New Line: ### test line",
                "",
                ""
            ],
            "is file exist": True,
            "modify timestamp": "2022-02-16 18:15:17"
        }
    ]

    role = Objectives.UC
    conf_file_path = "/usr/share/ice/file_tracker_test/configuration_files/user_config.yaml"

    def set_document(self):
        TestChangeInFile.set_document(self)
        self._title = "Change in file on UC"

    def copy_conf_files_dir(self):
        self._create_file_tracker_test_dir([Objectives.UC])
        source_path = "{}/ice/lib/HealthChecks/tests/tests_file_tracker/configuration_files/".format(self.home_dir)
        dest_path = "/usr/share/ice/file_tracker_test/configuration_files/"
        self.run_cmd("sudo cp -rp {source_path} {dest_path}".format(source_path=source_path, dest_path=dest_path))


class TestChangeInFileOnControllers(TestChangeInFile):

    expected_output = [
        {
            "full path": "/usr/share/ice/file_tracker_test/configuration_files/resolv.conf",
            "file name": "resolv.conf",
            "changes": [
                "",
                "Line 3 was changed:",
                "Old Line: nameserver 135.248.16.241",
                "\\ No newline at end of file",
                "---",
                "New Line: nameserver 135.248.16.241### test line",
                "",
                ""
            ],
            "is file exist": True,
            "modify timestamp": "2022-10-13 15:23:22"
        }
    ]

    role = Objectives.CONTROLLERS
    conf_file_path = "/usr/share/ice/file_tracker_test/configuration_files/resolv.conf"

    def set_document(self):
        TestChangeInFile.set_document(self)
        self._title = "Change in file on controllers"

    def copy_conf_files_dir(self):
        self._create_file_tracker_test_dir([Objectives.CONTROLLERS])
        hosts_dict = gs.get_host_executor_factory()._host_executors_dict
        for host_name in hosts_dict:
            if self.role in hosts_dict[host_name].roles:
                self._copy_conf_files_dir_from_localhost_to_host_roles([Objectives.CONTROLLERS], hosts_dict[host_name].ip)


class TestChangeInFileOnHYP(TestChangeInFile):

    expected_output = [
        {
            "full path": "/usr/share/ice/file_tracker_test/configuration_files/user_config.yaml",
            "file name": "user_config.yaml",
            "changes": [
                "",
                "Line 565 was added:",
                "New Line: ### test line",
                "",
                ""
            ],
            "is file exist": True,
            "modify timestamp": "2022-10-23 08:47:40"
        }
    ]

    role = Objectives.HYP
    conf_file_path = "/usr/share/ice/file_tracker_test/configuration_files/user_config.yaml"

    def set_document(self):
        TestChangeInFile.set_document(self)
        self._title = "Change in file on hypervisor"

    def copy_conf_files_dir(self):
        self._create_file_tracker_test_dir([Objectives.HYP])

        source_path = "{}/ice/lib/HealthChecks/tests/tests_file_tracker/configuration_files/".format(self.home_dir)
        dest_path = "/usr/share/ice/file_tracker_test/configuration_files/"

        gs.get_host_executor_factory().run_command_on_first_host_from_selected_roles("sudo scp -rp stack@uc:{source_path} {dest_path}".format(source_path=source_path, dest_path=dest_path), [Objectives.HYP])