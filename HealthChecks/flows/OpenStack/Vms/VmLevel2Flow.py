from __future__ import absolute_import
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
from flows.OpenStack.Vms.VmsInfoInformators import VmsDetailsLevel2
from tools.global_enums import Deployment_type


class VmsInfoFlow2(BaseValidationFlow):
    def _get_list_of_validator_class(self, version, deployment_type):
        check_list_class = [VmsDetailsLevel2]
        return check_list_class

    def command_name(self):
        return "vms2"

    def deployment_type_list(self):
        return [Deployment_type.CBIS]

    def is_default(self):
        return False

    def get_flow_order(self):
        return 1

    def get_dependencies(self):
        return ["vms"]
