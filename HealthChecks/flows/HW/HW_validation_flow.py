from __future__ import absolute_import
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
from flows.HW import HW_info
from flows.HW import HW_validations
from flows.HW import SMART
from flows.HW import VCPU
from tools.global_enums import Deployment_type, Version


class HWValidationFlow(BaseValidationFlow):

    def _get_list_of_validator_class(self, version, deployment_type):
        check_list_class = [
            HW_validations.CheckDiskUsage,
            HW_validations.CheckDiskUsageOnCriticalObjectives,
            HW_validations.BasicFreeMemoryValidation,
            HW_validations.BasicFreeMemoryValidationOnCriticalObjectives,
            HW_validations.CpuUsageValidation,
            HW_validations.TempValidation,
            # cpu_speed_validation,
            VCPU.ValidateCBISIsolationFileExist,
            # IsCpuTestPassed,
            HW_validations.ValidateRaidModeSettings,
            HW_validations.HwSysClockCompare,
            HW_validations.ValidateOsDiskOnSDA
        ]

        if deployment_type in [Deployment_type.CBIS, Deployment_type.NCS_OVER_BM]:
            check_list_class.extend([
                HW_info.UnifyHWCheck_on_computes,
                # HW_info.UnifyHWCheck_on_storage,
                # HW_info.UnifyHWCheck_on_ncs_workers,
                # HW_info.UnifyHWCheck_on_ncs_edges
            ])

        if deployment_type in [Deployment_type.CBIS, Deployment_type.NCS_OVER_BM]:
            check_list_class.extend([SMART.IsSmartEnabled, SMART.IsSmartTestPassed])

        if version >= Version.V19 and deployment_type == Deployment_type.CBIS:
            check_list_class.extend([VCPU.validate_cpu_isolation_scheme, VCPU.validate_cpu_pinning_config,
                                     VCPU.has_host_isolated_scheme, VCPU.validate_no_overlap])

        if version < Version.V22 and deployment_type == Deployment_type.CBIS:
            check_list_class.extend([HW_validations.CPUfreqScalingGovernorValidation])

        if version >= Version.V22 and deployment_type == Deployment_type.CBIS:
            check_list_class.extend([HW_validations.ValidateDiskSpace])

        if version >= Version.V23_10 and deployment_type == Deployment_type.NCS_OVER_BM:
            check_list_class.extend([HW_validations.ValidateDiskSpace])

        return check_list_class

    def command_name(self):
        return "test_HW"

    def deployment_type_list(self):
        return [Deployment_type.CBIS, Deployment_type.NCS_OVER_BM, Deployment_type.NCS_OVER_OPENSTACK]

    def get_flow_order(self):
        return -2  # Run on the beginning for user experience only
