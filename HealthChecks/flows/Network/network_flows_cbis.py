from __future__ import absolute_import
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
from flows.Network.network_validations import *


class network_flows_cbis(BaseValidationFlow):

    def _get_list_of_validator_class(self, version, deployment_type):
        check_list_class = [
                            are_host_connected,
                            NetworkInterfaceLinks,
                            NetworkInterfaceAddresses,
                            NetworkInterfaceMTU,
                            IsNuageVersionUniform,
                            NetworkBondCheck,  # todo - enhance to ncs
                            #DuplicateIP,
                            HostIPMI,
                            ValidateUcControlPlaneIpEtcHosts,
                            VerifyRouterIPActiveStatus
                            # iptables_size_uniform_computes,iptables_size_uniform_controllers,iptables_size_uniform_storage
                            ]
        return check_list_class

    def command_name(self):
        return "network_validations_cbis"

    def deployment_type_list(self):
        return [Deployment_type.CBIS]
