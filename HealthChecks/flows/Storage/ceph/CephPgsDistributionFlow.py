from __future__ import absolute_import
from flows.Storage.ceph.CephPgsDistribution import *
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
from tools.global_enums import *


class CephPgsDistributionFlow(BaseValidationFlow):
    def _get_list_of_validator_class(self, version, deployment_type):
        check_list_class = [CephPgsDistribution]
        return check_list_class

    def command_name(self):
        return "ceph_pgs_distribution"

    def deployment_type_list(self):
        return [Deployment_type.CBIS, Deployment_type.NCS_OVER_BM]

    def is_default(self):
        return False
