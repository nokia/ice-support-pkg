from __future__ import absolute_import
from flows.K8s.k8s_components.k8s_components_validator import *
from flows.K8s.k8s_components.k8s_sanity_checks import *
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
from tools import sys_parameters
from tools.global_enums import *


class K8sFlow(BaseValidationFlow):

    def _get_list_of_validator_class(self, version, deployment_type):

        check_list_class = [
            NodeAreReadyValidetor,
            ValidateNamespaceStatus,
            TotalNumberOfPodsPerCluster,
            NumberOfPodsPerNode,
            TotalNumberOfContainersPerCluster,
            AllPodsReadyAndRunning,
            SystemPodsReadyAndRunning,
            ContainersNcmsPodsReadyAndRunning,
            CheckCloudUserPermissions,
            # AllNodesHaveRoutesToAPIServer,
            CheckMaridbRunningPodCount,
            CheckMaridbMysqldbStatus,
            CheckHarborRegistryDiskUsage,
            AllNodesHaveRoutesToAPIServer,
            CheckRedisClusterStatus,
            RootCertificateExpiryValidator,
            VerifyOrphanedPods,
            CheckRedisHAStatus,
            ValidatePodsRestartedDueToOutofMemory,
            CburLatestBackupsSucceeded,
            CheckCburBackendConfigFile,
            CheckCburBackupDiskUsage,
            CheckWhetherCbisDirsExistsUnderRootDir,
            ValidateCAIssuer,
            VerifyKubectlCommand,
            CheckAllowedDisruptionsInPodDisruptionBudget,
            VerifyMissingContainerImages,
            CheckWhetherYumRepoExists,
            CheckBCMTRegistry,
            VerifyDeploymentAndStatefulsetResilient,
            ValidateAllDaemonsetsScheduled,
            CheckK8sPendingJobsCount,
            ValidateGaleraDiskUsage,
            ValidateHarborCburRegistryBackupWithPvc
            #RedhatEfiGrubConfigExistenceValidator
        ]

        if deployment_type == Deployment_type.NCS_OVER_BM:
            check_list_class.append(CheckPerconaXtradbIsSynced)
            check_list_class.append(HarborCertVipValidation)

        if version < Version.V20_FP2:
            # not relevant since fix was applied ncosfm-1076
            check_list_class.append(AllPodsHasLimits)

        if version in [Version.V20] and deployment_type == Deployment_type.NCS_OVER_BM:
            check_list_class = check_list_class + [ValidateHasAllBasicDaemonsets
                                                   # list_Of_btel_components_installed,
                                                   # is_btel_pods_terminated_with_OOMKILLED
                                                   ]

        if version < Version.V22:
            check_list_class.append(EtcdDefragmentationCheckInWorkersEdges)
            check_list_class.append(EtcdDefragmentationCheckInController)

        if version == Version.V22:
            check_list_class.append(HarborTlsCheck)

        if version >= Version.V22_12 and deployment_type == Deployment_type.NCS_OVER_BM:
            check_list_class.append(ValidateCsiCephRbdConfigFile)

        if version >= Version.V22:
            check_list_class.append(PodmanVolumesValidation)
            check_list_class.append(PodmanNumLockValidation)
            check_list_class.append(ValidateLockForPodmanVolumes)

        if version < Version.V23_10:
           check_list_class.append(CheckWhereaboutsCleanerPodIsFrozen)

        if version <= Version.V23_10:
            check_list_class.append(VerifyCkeyServiceConnectivity)

        if Version.V22 <= version < Version.V23_10:
            if version == Version.V22_12:
                if len(sys_parameters.get_hotfix_list()) == 0:
                    check_list_class.append(EtcdDefragCronjobValidation)
            else:
                check_list_class.append(EtcdDefragCronjobValidation)

        if version < Version.V24_7:
            check_list_class = check_list_class + [CheckMariaDbAdminPodLogs,
                                                   CheckMaridbAdminDbConnection,
                                                   CheckKeystoreFileMaridb,
                                                   CheckLoginConfFileMaridb]

        if Version.V22 <= version < Version.V24_7:
            check_list_class.append(ServiceTokenValidityCheck)

        if version >= Version.V24_7:
            check_list_class = check_list_class + [CheckMyConfFileMaridb]

        if version < Version.V25_11:
            check_list_class.append(ValidatePvSizeAgainstHelmChart)

        return check_list_class

    def command_name(self):
        return "test_k8s_basics"

    def deployment_type_list(self):
        return [Deployment_type.NCS_OVER_OPENSTACK, Deployment_type.NCS_OVER_BM, Deployment_type.NCS_OVER_VSPHERE]
