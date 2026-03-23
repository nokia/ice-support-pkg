from __future__ import absolute_import
from HealthCheckCommon.base_SystemOperator_flow import BaseSystemOperatorFlow
from flows_of_sys_operations.test.test_operations import *
from tools.global_enums import *


class BaseSystemOperatorTestFlow(BaseSystemOperatorFlow):

    def _get_list_of_validator_class(self, version, deployment_type):
        check_list_class = [
            TestFileCreatAtHost,
            TestCopyFileToUC,
            TestFailedCommand
        ]

        return check_list_class

    @staticmethod
    def command_name():
        return "test_scp"

    def deployment_type_list(self):
        return [Deployment_type.CBIS, Deployment_type.NCS_OVER_BM]
