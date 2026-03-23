from __future__ import absolute_import
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
from flows.Monitoring.elk_validations import *
from tools.global_enums import Deployment_type


class ElkFlows(BaseValidationFlow):

    def _get_list_of_validator_class(self, version, deployment_type):
        check_list_class = [
                            ValidateElkDeployedInLargeSystems,
                            CheckElkFsAccessibleOrNot,
                            ElkDaysRetentionConsistency,
                            IsElkDaysRetentionCorrect,
                            CheckElkPodsCrashWithNoUpAndRunningPrivateAddr,
                            CheckElkPodsCrashedWithLowMemoryHeapSize,
                            ]
        if version in [Version.V22, Version.V22_FP1, Version.V22_7,
                       Version.V22_12] and deployment_type == Deployment_type.NCS_OVER_BM:
            check_list_class.append(ValidateElkCuratorCronTimeIsOffset)
        return check_list_class

    def command_name(self):
        return "elk"

    def deployment_type_list(self):
        return [Deployment_type.CBIS, Deployment_type.NCS_OVER_BM, Deployment_type.NCS_OVER_OPENSTACK, Deployment_type.NCS_OVER_VSPHERE]
