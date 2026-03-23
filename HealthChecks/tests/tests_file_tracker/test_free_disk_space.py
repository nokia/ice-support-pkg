from __future__ import absolute_import
import os

from flows_of_sys_operations.FileTracker.FileTrackerPaths import FileTrackerPaths
from tests.tests_file_tracker.FileTrackerBaseTest import FileTrackerBaseTest
from tools.global_enums import Severity


class TestFreeDiskSpace(FileTrackerBaseTest):
    config_json_path = 'tests/tests_file_tracker/configurations_jsons/test_configurations_verify_disk_space.json'


    def set_document(self):
        self._unique_operation_name = "test_free_disk_space"
        self._title = "Verify free disk space"
        self._failed_msg = "Expected to have the following error message in the log: 'There is not enough available disk space for the file tracker running.'"
        self._severity = Severity.ERROR

    def run_test(self):
        self.run_file_tracker()

    def test_assert(self):
        is_msg_in_log = False
        if self.file_utils.is_file_exist(FileTrackerPaths.FILE_TRACKER_LOG_PATH):
            is_msg_in_log = self.run_cmd_return_is_successful(
                "grep 'There is not enough available disk space for the file tracker running.' {}".format(
                    FileTrackerPaths.FILE_TRACKER_LOG_PATH))
        assert is_msg_in_log, "File Tracker Test Failed - log doesn't contain the relevant error message"
