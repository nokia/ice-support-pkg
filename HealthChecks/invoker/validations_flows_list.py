from __future__ import absolute_import
# return the list of flowes in that can be ran
# (this was part of the invoker)
from flows.Etcd.etcd_flow import EtcdFlow
from flows.System.System_info_flow import SystemInfoChecksFlow
from flows.ICE.ICEInternalFlow import ICEInternalFlow
from flows.K8s.k8s_components.K8s_flow import K8sFlow
from flows.Cbis.user_config_validator.CBIS_user_config_validation_flow import CBIS_user_config_validation_flow
from flows.Network.network_traffic_flows import NetworkTrafficFlows
from flows.OpenStack.Vms.openstack_resource.openstack_resource_flow import OpenstackResource
from flows.Recommendations.OperationsRecommendationsFlow import OperationsRecommendationsFlow
from flows.Storage.Ceph_base_host_validation_flow import Ceph_base_host_validation_flow
from flows.Storage.CephFSIDFlow import CephFSIDFlow
from flows.Storage.RookCephFlow import RookCephFlow
from flows.Cbis.cbis_system_checks.basic_system_validation_flow import cbis_system_checks_flow
from flows.Storage.ceph.CephPgsDistributionFlow import CephPgsDistributionFlow
from flows.Cbis.scale_in_out_log_errors.scale_error_from_log_flow import scaleIsErrorInLogFlow
from flows.Cbis.system_log_checkes.system_error_from_log_flow import SystemErrorInLogFlow
from flows.Chain_of_events.chain_of_events_flows import ChainOfEventsFlow
from flows.OpenStack.cpu_steal.System_analytics_flow import System_analytics_flow
from flows.Network.network_flows_cbis import network_flows_cbis
from flows.Network.network_flows_ncs import network_flows_ncs
from flows.Security.certificate_flow import certificate_flow
from flows.Security.AuthManagementFlow import AuthManagementFlow
from flows.Linux.Linux_system_validation_flow import Linux_system_checks_flow
from flows.HW.HW_validation_flow import HWValidationFlow
from flows.OpenStack.openstack_validation_flow_cbis import OpenStack_system_checks_flow_cbis
from flows.OpenStack.OpenStack_validation_flow_ncs import OpenStack_system_checks_flow_ncs
from flows.OpenStack.Vms.VmsInfoFlow import VmsInfoFlow
from flows.Applications.NCD.NCDFlow import NCDFlow
from flows.Monitoring.btel_flows_ncs import btel_flows_ncs
from flows.Monitoring.zabbix_flows import ZabbixFlows
from flows.Monitoring.victoriaMetrics_flows import VictoriaMetricsFlows
from flows.Monitoring.elk_flows import ElkFlows
from flows.Storage.GlusterFsFlow import GlusterFsFlow
from flows.Blueprint.BlueprintValidationFlow import BlueprintValidationFlow
from flows.Ncs.ncs_flow import NcsFlow
from flows.K8s.k8s_components.k8s_vsphere_flows import K8sVsphereFlow
from flows.System.containers.container_flow import ContainersFlow

class ValidationFlowList:

    @staticmethod
    def get_list_of_flows():
        return [
            SystemInfoChecksFlow,
            HWValidationFlow,
            certificate_flow,
            cbis_system_checks_flow,
            CBIS_user_config_validation_flow,
            CephFSIDFlow,
            Ceph_base_host_validation_flow,
            RookCephFlow,
            CephPgsDistributionFlow,
            K8sFlow,
            EtcdFlow,
            network_flows_cbis,
            network_flows_ncs,
            scaleIsErrorInLogFlow,
            SystemErrorInLogFlow,
            System_analytics_flow,
            Linux_system_checks_flow,
            OpenStack_system_checks_flow_cbis,
            OpenStack_system_checks_flow_ncs,
            AuthManagementFlow,
            VmsInfoFlow,
            OpenstackResource,
            # VmsInfoFlow2,
            NCDFlow,
            btel_flows_ncs,
            ZabbixFlows,
            VictoriaMetricsFlows,
            ElkFlows,
            GlusterFsFlow,
            ChainOfEventsFlow,
            BlueprintValidationFlow,
            OperationsRecommendationsFlow,
            NcsFlow,
            K8sVsphereFlow,
            NetworkTrafficFlows,
            ICEInternalFlow,
            ContainersFlow
        ]
