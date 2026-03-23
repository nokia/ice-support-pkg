from __future__ import absolute_import
from flows.Cbis.cbis_system_checks.system_basic_checks import *
from flows.Cbis.cbis_system_checks.RPM_Validation import *
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
from flows.Cbis.cbis_system_checks.zombie_nodes_validation import *
from tools.global_enums import *


class cbis_system_checks_flow(BaseValidationFlow):
    def _get_list_of_validator_class(self, version, deployment_type):
        # if version in [Version.V19,Version.V19A]: those checks are general and should work on all Cbis versions

        check_list_class = [
            CheckStackStatus,
            ClusterResourcesStatus,
            CheckSuccessFlgExist,
            CheckNetworkAgentHostnameMismatch,
            # FileTrackerCheck,
            OvercloudBackupCheck,
            #RPMInstalledDatesCheck,
            #overcloud_rpm_list_check,
            # operations_time,  - need to delete as it duplicated
            validate_three_controllers,
            CheckZombieNodes,
            RabbitMQCheckOnUC,
            RabbitMQCheckOnControllers,
            RabbitMQQueueNotHuge,
            MYSQLCheck,
            security_hardening_info,
            UCBackupCheck,
            RabbitMQDirectoryNotLarge,
            MySQLDirectoryNotLarge,
            VerifyUnercloudHostname,
            VerifyMACandBondAddress,
            CheckOvercloudrcPasswdOnCbisCluster,
            ValidateBMCPasswordValidAndSync,
            ValidateARPResponder,
            RabbitMQErrorLogValidation,
            RabbitMQMessagesLogValidation
            # ,UniformBaremetalPropertiesValidation
        ]

        if Version.V22 <= version <= Version.V22_FP1:
            check_list_class.append(VerifySymlinkForCACert)

        if version >= Version.V22_FP1:
            check_list_class.append(VerifyOldRPMs)
            check_list_class.append(CinderDefaultVolumeType)

        if version < Version.V22:
            check_list_class.append(RabbitMQQueueCheck)

        if version <= Version.V19:
            check_list_class.append(ValidationReadPermissions)

        if version >= Version.V19:
            check_list_class = check_list_class + [
                                                   check_galera_is_synced_docker,
                                                   check_haproxy,
                                                   check_haproxy_config_valid,
                                                   CbisSystemCheckGnocchiCeilometerDocker
            ]
            # check_list_class.append(uc_rpm_list_check)

        if version in [Version.V18_5, Version.V18]:
            check_list_class.append(check_galera_is_synced)
            check_list_class.append(CbisSystemCheckGnocchiCeilometer)

        if version >= Version.V18_5:
            check_list_class.append(CheckMaxProcessesForKeystone)

        if Version.V22 <= version <= Version.V24_11:
            check_list_class.append(VerifyDefaultLibvirtNetwork)

        if version < Version.V25:
            check_list_class.append(CheckDeploymentServerBlacklist)
            check_list_class.append(RedisMasterRoleAvailability)
            check_list_class.append(ZaqarTimeoutValidation)

        if version >= Version.V20:
            check_list_class.append(RabbitMQConnectionPoolLimitCheck)

        return check_list_class


    def command_name(self):
        return "test_cbis_system"

    def deployment_type_list(self):
        return [Deployment_type.CBIS]
