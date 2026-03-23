from __future__ import absolute_import
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
from flows.Storage.ceph.Ceph import *
from tools.global_enums import *


class Ceph_base_host_validation_flow(BaseValidationFlow):
    def _get_list_of_validator_class(self, version, deployment_type):
        # if version in [Version.V19,Version.V19A]: those checks are general and should work on all Cbis versions
        check_list_class = [
                            OsdHostsVsCephHosts,
                            CephHasConfFile,
                            CephHasOnlyOneConfFile,
                            CephOsdTreeWorks,
                            IsCephHealthOk,
                            MonitorsCount,
                            IsOSDsUp,
                            IsOSDsWeightOK,
                            IsCephOSDsNearFull,
                            ValidateCephTempFilesCount,
                            CheckVarLibCephDir,
                            CheckVarLibCephDirOwner,
                            IsOsdAuthSameAsOsdTree,
                            CheckOsdPGLogTuning,
                            IsCephEncryption,
                            OsdJournalError,
                            CheckCephfsShareExist,
                            CephCheckPGsPerOSD
                            # ValidateCephBlockDBSize
                            ]

        if version < Version.V24_11:
            check_list_class.extend([
                MonitorsHealth,
                AreInstalledOSDsMatchCephConfigOnNCS,
                CheckMultipleMondirs,
                CephConfCrushLocationExists,
            ])

        if version >= Version.V24_11:
            check_list_class.extend([
                MonitorsHealthCephAdm
            ])

        if version >= Version.V19:
            check_list_class.extend(
                [
                    CephMgrStandbyCheck,
                    CheckPoolSize,
                    CheckMonCount,
                    CheckMgrCount,
                    CheckMdsCount,
                    CheckMinOsdNodes,
                    VerifyOsdOpNumThreadsPerShardSSD,
                    CephSlowRequests,
                    AreAllOSDsRunningOnNCS,
                    ValidateCephRbdKeyringConfigOnNCS,
                    ValidateCephFsKeyringConfigOnNCS

                ]
            )

        # on CBIS V.22, osd is mounted to 'tmpfs' and not to related osd folder
        if version >= Version.V19 and version < Version.V22:
            check_list_class.append(IsOsdDiskConfApplied)

        if version >= Version.V19 and version < Version.V24_11:
            check_list_class.extend([
                IsCephConfExist,
                CephConfServiceNameValid,
                IsOsdSystemctlValid,
                CephOsdMemoryAllocation,
                CephMultipoolSameNodeMemberCheck
            ])

        #if version >= Version.V20:
            #check_list_class.append(CheckAdminCount)

        if version < Version.V24:
            check_list_class.append(IsOsdInContainerSameAsInConf)

        if Deployment_type.is_cbis(Deployment_type) or (Deployment_type.is_ncs(deployment_type) and version < Version.V24_7):
            check_list_class.append(CephCpuQuotaCheck)

        if version <= Version.V23_10 and deployment_type == Deployment_type.NCS_OVER_BM:
            check_list_class.append(IOErrorCephFSMount)

        if version >= Version.V24_11:
            check_list_class.append(CheckCephServiceStatus)

        if deployment_type == Deployment_type.NCS_OVER_BM:
            check_list_class.append(VerifyLostVolumesCephK8sPV)

        return check_list_class

    def command_name(self):
        return "test_ceph"

    def deployment_type_list(self):
        return [Deployment_type.CBIS, Deployment_type.NCS_OVER_BM]