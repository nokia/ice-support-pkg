from __future__ import absolute_import
from flows.System.System_info_validations import *
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
from tools.global_enums import *

class SystemInfoChecksFlow(BaseValidationFlow):

    def _get_list_of_validator_class(self, version, deployment_type):

        check_list_class = [
                            LatestHotfixCheck
                            ]

        return check_list_class

    def command_name(self):
        return "system_info"

    def deployment_type_list(self):
        return [Deployment_type.CBIS, Deployment_type.NCS_OVER_BM, Deployment_type.NCS_OVER_OPENSTACK, Deployment_type.NCS_OVER_VSPHERE]

    def get_flow_order(self):
        return -3  # Run on the beginning for user experience only
