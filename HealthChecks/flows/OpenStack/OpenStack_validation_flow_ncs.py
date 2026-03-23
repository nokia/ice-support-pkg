from __future__ import absolute_import
from flows.OpenStack.Ironic_validations import *

from HealthCheckCommon.base_validation_flow import BaseValidationFlow

from tools.global_enums import *

class OpenStack_system_checks_flow_ncs(BaseValidationFlow):

    def _get_list_of_validator_class(self, version, deployment_type):

        check_list_class = []
        if version >= Version.V22_7 and deployment_type == Deployment_type.NCS_OVER_BM:
            check_list_class.append(IronicNodeActiveValidator)
        return check_list_class

    def command_name(self):
        return "openStack_ncs"

    def deployment_type_list(self):
        return [Deployment_type.NCS_OVER_BM]
