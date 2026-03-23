from __future__ import absolute_import
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
from HealthCheckCommon.operations import *


class BaseSystemOperatorFlow(BaseValidationFlow):

    def _invoke_checks(self, validators_list, printer):
        ParallelRunner.run_SystemOperator_on_all_host(validators_list, printer)

    @staticmethod
    def add_flow_arguments(flow_parser):
        pass

    @staticmethod
    def init_args(args):
        pass

    @staticmethod
    def command_name():
        assert True, "Please implement command_name"
