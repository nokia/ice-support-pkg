from __future__ import absolute_import
from flows.System.containers.container_validations import *
from HealthCheckCommon.base_validation_flow import BaseValidationFlow

from tools.global_enums import *


class ContainersFlow(BaseValidationFlow):

    def _get_list_of_validator_class(self, version, deployment_type):

        check_list_class = []

        if version >= Version.V19:
            check_list_class.append(ValidateDockersHealth)
            check_list_class.append(ValidateDockersNotExited)
            check_list_class.append(ValidateCbisManagerNginxHealth)
            check_list_class.append(ValidateCbisConductorHealth)

        return check_list_class

    def command_name(self):
        return "test_containers"

    def deployment_type_list(self):
        return [Deployment_type.CBIS,
                Deployment_type.NCS_OVER_BM,
                Deployment_type.NCS_OVER_OPENSTACK,
                Deployment_type.NCS_OVER_VSPHERE]
