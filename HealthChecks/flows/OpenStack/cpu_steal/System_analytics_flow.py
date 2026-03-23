from __future__ import absolute_import
from flows.OpenStack.cpu_steal.cpu_steal import *
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
from tools.global_enums import *


class System_analytics_flow(BaseValidationFlow):

    def _get_list_of_validator_class(self, version, deployment_type):
        # if version in [Version.V19,Version.V19A]: those checks are general and should work on all Cbis versions
        check_list_class = [CPU_steal_validation]
        return check_list_class


    def command_name(self):
        return "run_sys_analytics"

    def is_default(self):
        return False

    def deployment_type_list(self):
        return [Deployment_type.CBIS]
