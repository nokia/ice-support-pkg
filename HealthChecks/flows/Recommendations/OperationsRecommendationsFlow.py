from __future__ import absolute_import
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
from flows.Recommendations.OperationsRecommendationsValidations import *
from tools.global_enums import *
import sys


class OperationsRecommendationsFlow(BaseValidationFlow):
    def _get_list_of_validator_class(self, version, deployment_type):
        check_list_class = [
                            ScaleBlocker,
                            UpgradeBlocker,
                            MigrationBlocker,
                            CertRenewalBlocker
                            ]
        return check_list_class

    def command_name(self):
        return "operations_recommendations"

    def deployment_type_list(self):
        return [Deployment_type.CBIS, Deployment_type.NCS_OVER_BM, Deployment_type.NCS_OVER_OPENSTACK,
                Deployment_type.NCS_OVER_VSPHERE]

    def get_flow_order(self):
        return sys.float_info.max

