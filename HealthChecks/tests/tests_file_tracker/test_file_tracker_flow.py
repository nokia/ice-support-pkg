from __future__ import absolute_import
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
from tests.tests_file_tracker.test_change_in_file import *
from tests.tests_file_tracker.test_deleted_conf_file import *
from tests.tests_file_tracker.test_free_disk_space import *
from tools.global_enums import *


class TestFileTrackerFlow(BaseValidationFlow):

    def _get_list_of_validator_class(self, version, deployment_type):
        check_list_class = [
                            TestFreeDiskSpace,
                            TestChangeInFileOnUC,
                            TestChangeInFileOnControllers,
                            TestChangeInFileOnHYP,
                            TestDeletedConfFileOnUC,
                            TestDeletedConfFileOnControllers
        ]
        return check_list_class

    def command_name(self):
        return "test_file_tracker"

    def deployment_type_list(self):
        return [Deployment_type.CBIS]
