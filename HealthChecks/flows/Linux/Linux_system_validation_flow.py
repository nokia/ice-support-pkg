from __future__ import absolute_import
from flows.Linux.Linux_validations import *
from flows.Linux.sync_validations import *
from HealthCheckCommon.base_validation_flow import BaseValidationFlow

from tools.global_enums import *


class Linux_system_checks_flow(BaseValidationFlow):

    def _get_list_of_validator_class(self, version, deployment_type):
        # if version in [Version.V19,Version.V19A]: those checks are general and should work on all Cbis versions

        check_list_class = [
                             SystemdServicesStatus,
                             is_host_reachable,
                             CheckDnsResolutionNcs,
                             clock_clock_synchronized,
                             TooManyOpenFilesCheck,
                             TooManyProcessesCheck,
                             # RpmdbVerify,
                             SelinuxMode,
                             Filesystem_is_not_btrfs,
                             Mellanox_driver_version_validation,
                             NoZombiesAllowed,
                             AuditdBacklogLimit,
                             KernelVersionValidation,
                             Data0FileSystemReadWriteCheck,
                             VerifyDuNotHang,
                             check_systemd_alarm_manager_service,
                             NestedNamespaceMemoryLeak,
                             YumlockFileCheck,
                             CheckCronJobDuplicates,
                             FstabValidator,
                             DiskMountValidator,
                             VerifyNoEmptyFilesInConfigDirs,
                             VerifySecureBootStatus
                             ]

        if deployment_type == Deployment_type.NCS_OVER_BM:
            check_list_class.append(CheckPasswordExpiryForNCSBareMetal)

        #if version >= Version.V19:
        #    check_list_class.append(SystemCheckDentryCache)

        if version >= Version.V19:
            check_list_class.append(SystemCheckDentryCache)

        if version > Version.V19A:
            check_list_class.append(ntp_offset_checker)

        if deployment_type == Deployment_type.CBIS:
            check_list_class = check_list_class+ [ValidateNtpIp, CheckDnsResolutionCbis, ValidateGatewayBrPublic]

            if version <= Version.V20:
                check_list_class.append(ntpdate_checker)  # no ntpq in cbis 21
            else:
                check_list_class.append(validate_no_ntp_in_cbis_21)

            if version == Version.V22 or version == Version.V24:
                check_list_class.append(ValidateProcFsNfsdAbsenceInUcVm)

        if version >= Version.V20_FP2 and deployment_type == Deployment_type.NCS_OVER_BM:
            check_list_class.append(ValidateKernelParamsOverwritten)

        # if version >= Version.V19 and deployment_type == Deployment_type.CBIS:
        #    check_list_class.append(VerifyMountCephFsShareServiceDisabled)

        if version >= Version.V22 and deployment_type == Deployment_type.NCS_OVER_BM:
            check_list_class.append(VerifyNginxWorkerConnection)

        if version >= Version.V22 and version < Version.V23 and deployment_type == Deployment_type.NCS_OVER_BM:
            check_list_class.append(VerifyEtcFstabDirectoryForNFS)

        if version >= Version.V22 and deployment_type in [Deployment_type.NCS_OVER_BM, Deployment_type.NCS_OVER_VSPHERE, Deployment_type.NCS_OVER_OPENSTACK]:
            check_list_class.append(ValidatePipVersionConsistency)

        if deployment_type in [Deployment_type.NCS_OVER_BM, Deployment_type.CBIS]:
            check_list_class.append(ValidateCbisPodsLogRotated)

        if version >= Version.V25_7 and deployment_type  in [Deployment_type.NCS_OVER_BM, Deployment_type.NCS_OVER_OPENSTACK]:
            check_list_class.append(ValidateSysLogRotated)

        return check_list_class

    def command_name(self):
        return "test_linux_system"

    def deployment_type_list(self):
        return [Deployment_type.CBIS,
                Deployment_type.NCS_OVER_BM,
                Deployment_type.NCS_OVER_OPENSTACK,
                Deployment_type.NCS_OVER_VSPHERE]
