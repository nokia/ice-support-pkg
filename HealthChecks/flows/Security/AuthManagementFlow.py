from __future__ import absolute_import
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
from flows.Security.AuthManagement.AuthManagementValidations import *
from tools.global_enums import *


class AuthManagementFlow(BaseValidationFlow):

    def _get_list_of_validator_class(self, version, deployment_type):
        check_list_class = [
            KeycloakLoginErrorsCheck,
            VerifyCbisAdminKeyHost
        ]

        return check_list_class

    def command_name(self):
        return "auth"

    def deployment_type_list(self):
        return [Deployment_type.NCS_OVER_BM,Deployment_type.NCS_OVER_OPENSTACK,Deployment_type.NCS_OVER_VSPHERE]
