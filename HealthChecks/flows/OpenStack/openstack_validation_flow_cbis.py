from __future__ import absolute_import
from flows.OpenStack.Ironic_validations import *
from flows.OpenStack.validation_based_openstack import *
from flows.OpenStack.openstack_validations import *
from flows.OpenStack.swift_service_validator import *
from flows.OpenStack.Password_expiry_check import *
from flows.OpenStack.LargeSetup_validator import *
from flows.OpenStack.HypervisorValidation import *
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
from tools.global_enums import *

class OpenStack_system_checks_flow_cbis(BaseValidationFlow):

    def _get_list_of_validator_class(self, version, deployment_type):

        check_list_class = [
                            IronicNodeActiveValidator,
                            check_neutron_agents,
                            CheckSrvDirOwner,
                            ValidateSrvFolderSpace,
                            CheckPasswordExpiryForStack,
                            CheckPasswordExpiryForOpenStack,
                            CompareCorosyncNodeList,
                            ValidateHttpdServiceUC,
                            SpaceNotInAvailabilityZone,
                            JsonFileIsValid,
                            check_project_non_ascii_chars,
                            checkOvercloudrc,
                            CheckTenantPasswordExpiry,
                            VerifyClustercheckContainerPort,
                            VerifyPassthroughWhitelistInNovaConf
                            ]
        if version >= Version.V22_FP1:
            check_list_class.append(TripleOVolumeTypeValidation)
        if version <= Version.V19:
            check_list_class.append(CheckMariadbConnectTimeout)
            check_list_class.append(CheckKeystoneRequest)
        if version >= Version.V19:
            check_list_class.append(HypervisorFreeDiskSpaceCheck)
            check_list_class.append(computes_memory_check)  # todo make work on 18.5
            check_list_class.append(HasNovaConf)
            check_list_class.append(check_for_stale_allocations_in_novadb)
            check_list_class.append(PassthroughWhitelistInNova)
            check_list_class.append(RabbitMQPasswordNeutronValidation)
        if version >= Version.V22:
            #check_list_class.append(validate_metadata_RPC_Api_workers_parameter)
            check_list_class.append(validateRPCApiCPUparameter)
        if version < Version.V22:
            check_list_class.append(VerifyCbisManagerDockerLayers)
        if version >= Version.V24:
            check_list_class.append(CheckCbisManagerNginxPodUserPasswordExpiry)
        if version < Version.V25:
            check_list_class.extend([CheckSwiftDirectorySrv,
                                     SwiftServiceValidator,
                                     CheckSwiftFilesOvercloud])

        return check_list_class

    def command_name(self):
        return "openStack_cbis"

    def deployment_type_list(self):
        return [Deployment_type.CBIS]
