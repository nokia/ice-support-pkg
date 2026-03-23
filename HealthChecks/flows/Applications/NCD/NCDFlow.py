from __future__ import absolute_import
from flows.Applications.NCD.NcdPreChecks import *
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
from tools.global_enums import *


class NCDFlow(BaseValidationFlow):

    def _get_list_of_validator_class(self, version, deployment_type):
        check_list_class = [
                            pre_installed_applications_check,
                            ncom_access,
                            fqdn_resolve
                            # is_sc_rwx
                            ]
        return check_list_class


    def command_name(self):
        return "ncd"

    def deployment_type_list(self):
        return [Deployment_type.NCS_OVER_BM]

    def is_default(self):
        return False