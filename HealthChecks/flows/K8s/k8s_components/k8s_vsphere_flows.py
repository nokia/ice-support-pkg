from __future__ import absolute_import
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
from flows.K8s.k8s_components.k8s_vsphere_validation import *
from tools.global_enums import *


class K8sVsphereFlow(BaseValidationFlow):
    def _get_list_of_validator_class(self, version, deployment_type):
        check_list_class = [
            ValidateProviderId
        ]
        return check_list_class

    def command_name(self):
        return "k8s_vsphere_flow_validations"

    def deployment_type_list(self):
        return [Deployment_type.NCS_OVER_VSPHERE]
