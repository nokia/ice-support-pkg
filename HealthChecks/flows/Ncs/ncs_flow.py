from __future__ import absolute_import
from flows.Ncs.ncs_validations import *
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
from tools.global_enums import *
import tools.sys_parameters as gs


class NcsFlow(BaseValidationFlow):
    def _get_list_of_validator_class(self, version, deployment_type):
        check_list_class = [
            CheckManagerContainers,
            SecurityPatchValidation,
            RedisActiveOperationsCheck,
            CheckLDAPConnectivity,
            CheckWebsocketProcessCount,
            CheckRedundantDirectivesInResolvConf,
            IrqServiceValidator,
            BcmtVrrpSecurityGroupValidation,
            ValidateHelmStatus,
            CheckNodeRebootRequired
        ]

        if deployment_type == Deployment_type.NCS_OVER_BM:
            if gs.is_ncs_central():
                if gs.is_more_than_one_cluster():
                    check_list_class.append(CheckManagerPort)
                    if version >= Version.V22:
                        check_list_class.append(RedisPasswordSyncCheck)
                        check_list_class.append(CheckSymLink)
            else:
                check_list_class.append(CheckManagerPort)
                if version >= Version.V22:
                    check_list_class.append(RedisPasswordSyncCheck)

        if version >= Version.V23:
            check_list_class.append(CheckCertificateCommonName)
            check_list_class.append(VerifySecretCertETCDCert)
            check_list_class.append(CertificateVerifyCA)

        if version < Version.V24_7:
            check_list_class.append(CheckResourceLimitsOfBcmtCitmIngress)

        if version == Version.V22_7:
            check_list_class.append(PreUpgradeNotification)

        if version >= Version.V22_12 and deployment_type == Deployment_type.NCS_OVER_BM:
            check_list_class.append(ValidateTunedProfile)
        if version >= Version.V22_12 and deployment_type == Deployment_type.NCS_OVER_OPENSTACK:
            check_list_class.append(BcmtImageMatchingNCSVersion)
        if version >= Version.V23_10 and deployment_type == Deployment_type.NCS_OVER_BM:
            check_list_class.append(GenOpensslCnfFileExists)
        if version >= Version.V25_7 and deployment_type == Deployment_type.NCS_OVER_BM:
            check_list_class.append(ValidateLogrotateTimerEnabledActive)
        if version >= Version.V22_7:
            check_list_class.append(CheckCburPvCount)
        return check_list_class

    def command_name(self):
        return "ncs_flows"

    def deployment_type_list(self):
        return [Deployment_type.NCS_OVER_BM, Deployment_type.NCS_OVER_OPENSTACK, Deployment_type.NCS_OVER_VSPHERE]
