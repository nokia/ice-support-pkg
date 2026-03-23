from __future__ import absolute_import
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
from flows.Network.network_validations import *


class network_flows_ncs(BaseValidationFlow):

    def _get_list_of_validator_class(self, version, deployment_type):

        check_list_class = [  # is_all_intefaces_up,
            # NetworkBondCheckRequired, - anhance to ncs
            # NetworkBondCheckHealth,
            # NetworkBondCheckSysconfig,
            NetworkInterfaceAddresses,
            NetworkInterfaceMTU,
            are_host_connected,
            # DuplicateIP,
            OverlayNetworkCheck,
            # IptablesSizeUniformComputes, IptablesSizeUniformControllers, IptablesSizeUniformStorage,
            CalicoNodeStatus,
            CalicoIpamStatus,
            VerifyIpsetListBcmtwhitelist,
            VerifyIptablesServiceStop,
            NoDynamicAddressInIptables,
            WhereaboutsDuplicateIPAddresses,
            WhereaboutsMissingPodrefs,
            WhereaboutsMissingAllocations,
            WhereaboutsExistingAllocations,
            VerifySysctlParameters,
            ValidateBFDSessionStateUpDown,
           # CalicoIpamBlockStatus, #commentout false positive (see ICET-2394)
            VerifyNextHopGroupNodeSelectors,
            CheckIptablesForManuallyAddedRules,
            VerifyBFDSessionOutput,
            NetworkInterfaceLinks,
            CalicoIpamBlockPrefix,
            VerifyMellanoxVFNumber,
            VerifyIstioPluginFileExists,
            SysctlVlanForwarding,
            ValidateStaleStaticRouteConfig,
            ValidateStaleNextHops
        ]

        if deployment_type == Deployment_type.NCS_OVER_BM:
            check_list_class.extend([HostIPMI])
            if version < Version.V22:
                check_list_class.extend([InternalServiceNetworkCheck])

            if Version.V22_7 <= version < Version.V25:
                check_list_class.append(ValidateCorrectNetconfig)

        if deployment_type == Deployment_type.NCS_OVER_OPENSTACK:
            check_list_class.extend([VerifyEgressGateway, VerifyAllowedAddressPair])

        if version >= Version.V22:
            check_list_class.extend([ValidateCoreDNSReverseLookupIPV6, ValidateStaleEgressGatewayNode])

        if version <= Version.V24_7:
            check_list_class.extend([
                NetworkBondCheck
            ])

        if version >= Version.V22_7:
            check_list_class.extend([
                ValidateSelinuxContextDirIstio
            ])

        if version < Version.V24_11:
            check_list_class.extend([
                VerifyCalicoConflistExistsNonEmpty
            ])

        if deployment_type == Deployment_type.NCS_OVER_OPENSTACK and version == Version.V22:
            check_list_class.append(VerifyUnmanagedDeviceList)
        return check_list_class

    def command_name(self):
        return "network_validations_ncs"

    def deployment_type_list(self):
        return [Deployment_type.NCS_OVER_BM, Deployment_type.NCS_OVER_VSPHERE, Deployment_type.NCS_OVER_OPENSTACK]
