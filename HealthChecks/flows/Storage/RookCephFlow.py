from __future__ import absolute_import
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
from flows.Storage.ceph.RookCeph import *
from tools.global_enums import *


class RookCephFlow(BaseValidationFlow):
    def _get_list_of_validator_class(self, version, deployment_type):
        check_list_class = []

        if version >= Version.V24_7:
            check_list_class.extend([
                VerifyRookCephHealth
            ])
        return check_list_class

    def command_name(self):
        return "test_rook_ceph"

    def deployment_type_list(self):
        return [Deployment_type.NCS_OVER_OPENSTACK]


