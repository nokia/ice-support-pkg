from __future__ import absolute_import
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
from flows.OpenStack.Vms.VmsInfoInformators import *


class VmsInfoFlow(BaseValidationFlow):
    flow_name = "vms"

    def _get_list_of_validator_class(self, version, deployment_type):
        check_list_class = [
            # VmsVirshXML,
            VmsDomInfo,
            VmsVcpuInfo,
            DomMemstatInfo,
            ComputeRouteInfo,
            VirshNetInfo,
            DomIfAddressInfo,
            # OvsInfo,
            VmsDiagnostics,
            VmsPortsList,
            DomIfListInfo,
            VmsStorageInfo,
            # PCIInfo,
            IpLinkInfo,
            BridgesInfo,
            VmShowInfo,
            VmFlavor,
            VmImage,
            ComputeHypervisorInfo,
            NovaComputeService,
        ]

        return check_list_class

    def command_name(self):
        return VmsInfoFlow.flow_name

    def deployment_type_list(self):
        return [Deployment_type.CBIS]

    def is_default(self):
        return False
