from __future__ import absolute_import
import copy
import os

import pytest

from HealthCheckCommon.table_system_info import TableSystemInfo
from tests.pytest.tools.versions_alignment import Mock
import tools.global_logging as log
from flows.Network.dumpflows_validations import MulticastDumpFlows, UnicastDumpFlows, FlowsDataCollector, \
    AgentsDataCollector, VmsDataCollector
from flows.OpenStack.openstack_utils_data_collector import OpenstackUtilsDataCollector
from tests.pytest.pytest_tools.operator.test_data_collector import DataCollectorScenarioParams, DataCollectorTestBase
from tests.pytest.pytest_tools.operator.test_informator_validator import InformatorValidatorTestBase, \
    InformatorValidatorScenarioParams
from tests.pytest.pytest_tools.operator.test_operator import CmdOutput
from tools import sys_parameters
from tools.global_enums import Version


def get_data_from_file(file_name):
    current_dir_path = os.path.dirname(os.path.abspath(__file__))
    host_name_by_ip_path = os.path.join(current_dir_path, 'inputs', file_name)
    with open(host_name_by_ip_path, 'r') as f:
        return f.read()


base_mariadb_cmd = "sudo mysql -u root -e '{}'"
host_name_by_ip_cmd = "use ovs_neutron; select ip_address, host from  ml2_vxlan_endpoints"
ovs_agents_cmd = "use ovs_neutron; select distinct(ml2_vxlan_endpoints.ip_address)," \
                 " networksegments.segmentation_id from  ml2_vxlan_endpoints, " \
                 "networksegments, nova.instances inst, ports where networksegments.network_type=\"vxlan\" " \
                 "and inst.uuid = ports.device_id and ml2_vxlan_endpoints.host=inst.host" \
                 " and networksegments.network_id=ports.network_id;"
dhcp_agents_cmd = "use ovs_neutron; select distinct(ml2_vxlan_endpoints.ip_address), " \
                  "networksegments.segmentation_id from  ml2_vxlan_endpoints, " \
                  "networksegments, agents,networkdhcpagentbindings where networksegments.network_type=\"vxlan\" " \
                  "and ml2_vxlan_endpoints.host=agents.host and  networksegments.network_id=networkdhcpagentbindings." \
                  "network_id and  agents.id=dhcp_agent_id;"
routers_agents_cmd = "use ovs_neutron; select distinct(ml2_vxlan_endpoints.ip_address), " \
                     "networksegments.segmentation_id from  ml2_vxlan_endpoints, agents, " \
                     "networksegments, ports, ha_router_agent_port_bindings where " \
                     "ml2_vxlan_endpoints.host=agents.host  and networksegments.network_type=\"vxlan\" " \
                     "and  ha_router_agent_port_bindings.l3_agent_id=" \
                     "agents.id and ports.id=ha_router_agent_port_bindings." \
                     "port_id and ha_router_agent_port_bindings.state=\"active\";"
host_name_by_ip_file = get_data_from_file('host_name_by_ip.txt')


def run_data_collector_side_effects(data_collector_class, **kwargs):
    if kwargs['mysql_command'] == dhcp_agents_cmd:
        return {"overcloud-controller-pl-8004-i14-0": [{"ip_address": "172.17.2.13", "segmentation_id": "12"},
                                                       {"ip_address": "172.17.2.15", "segmentation_id": "12"},
                                                       {"ip_address": "172.17.2.21", "segmentation_id": "98"},
                                                       {"ip_address": "172.17.2.13", "segmentation_id": "98"}]}
    if kwargs['mysql_command'] == routers_agents_cmd:
        return {"overcloud-controller-pl-8004-i14-0": [{"ip_address": "172.17.2.21", "segmentation_id": "12"},
                                                       {"ip_address": "172.17.2.15", "segmentation_id": "98"}]}
    if kwargs['mysql_command'] == ovs_agents_cmd:
        return {"overcloud-controller-pl-8004-i14-0": [{"ip_address": "172.17.2.11", "segmentation_id": "12"},
                                                       {"ip_address": "172.17.2.17", "segmentation_id": "12"}]}


def run_data_collector_failed_redundant_outputting_side_effects(data_collector_class, **kwargs):
    if kwargs['mysql_command'] == dhcp_agents_cmd:
        return {"overcloud-controller-pl-8004-i14-0": [{"ip_address": "172.17.2.13", "segmentation_id": "12"},
                                                       {"ip_address": "172.17.2.15", "segmentation_id": "12"},
                                                       {"ip_address": "172.17.2.21", "segmentation_id": "98"},
                                                       {"ip_address": "172.17.2.13", "segmentation_id": "98"}]}
    if kwargs['mysql_command'] == routers_agents_cmd:
        return {"overcloud-controller-pl-8004-i14-0": [{"ip_address": "172.17.2.21", "segmentation_id": "12"},
                                                       {"ip_address": "172.17.2.15", "segmentation_id": "98"}]}
    if kwargs['mysql_command'] == ovs_agents_cmd:
        return {"overcloud-controller-pl-8004-i14-0": [{"ip_address": "172.17.2.11", "segmentation_id": "12"}]}


def run_data_collector_failed_tunnel_not_exist_side_effects(data_collector_class, **kwargs):
    if kwargs['mysql_command'] == dhcp_agents_cmd:
        return {"overcloud-controller-pl-8004-i14-0": []}
    if kwargs['mysql_command'] == routers_agents_cmd:
        return {"overcloud-controller-pl-8004-i14-0": []}
    if kwargs['mysql_command'] == ovs_agents_cmd:
        return {"overcloud-controller-pl-8004-i14-0": [{"ip_address": "172.17.2.11", "segmentation_id": "12"},
                                                       {"ip_address": "172.17.2.17", "segmentation_id": "12"}]}


def _run_data_collector_failed_collect_agents_data_side_effects(tested_object, data_collector_class, **kwargs):
    data_collector_dict = {
        FlowsDataCollector: {"overcloud-controller-191-0": []},
        VmsDataCollector: {"overcloud-ovscompute-191-0": {}},
        AgentsDataCollector: {"overcloud-controller-191-0": None}
    }
    return data_collector_dict[data_collector_class]


def get_passed_dict():
    ovs_vsctl_interface_file = get_data_from_file('ovs-vsctl_interface.txt')
    ports = """patch-int
vxlan-ac11020b
vxlan-ac11020d
vxlan-ac11020f
vxlan-ac110211"""
    table_22 = """ cookie=0x3491e5c468a22c3c, table=22, priority=1,dl_vlan=58 actions=strip_vlan,load:0x62->\
    NXM_NX_TUN_ID[],output:2,output:3
cookie=0x3491e5c468a22c3c, table=22, priority=1,dl_vlan=74 actions=strip_vlan,load:0xc->NXM_NX_TUN_ID[]\
,output:16,output:17,output:2,output:3
cookie=0x3491e5c468a22c3c, table=22, priority=0 actions=drop"""
    return {
        "sudo /bin/hiera -c /etc/puppet/hiera.yaml mysql::server::root_password": {
            "overcloud-controller-pl-8004-i14-0": CmdOutput('nil')},
        base_mariadb_cmd.format(host_name_by_ip_cmd): {
            "overcloud-controller-pl-8004-i14-0": CmdOutput(host_name_by_ip_file)},
        "sudo ifconfig | grep 172.17.2": {"overcloud-controller-pl-8004-i14-0": CmdOutput(
            "inet 172.17.2.21  netmask 255.255.255.0  broadcast 172.17.2.255\\n"),
            "overcloud-dpdkperformancecompute-cbis22-0": CmdOutput(
                "inet 172.17.2.147  netmask 255.255.255.0  broadcast 172.17.2.255\\n"),
            "overcloud-controller-pl-8004-i14-1": CmdOutput(
                "inet 172.17.2.13  netmask 255.255.255.0  broadcast 172.17.2.255\\n"),
            "overcloud-controller-pl-8004-i14-2": CmdOutput(
                "inet 172.17.2.15  netmask 255.255.255.0  broadcast 172.17.2.255\\n"),
            "overcloud-ovscompute-pl-8004-i14-0": CmdOutput(
                "inet 172.17.2.11  netmask 255.255.255.0  broadcast 172.17.2.255\\n"),
            "overcloud-ovscompute-pl-8004-i14-1": CmdOutput(
                "inet 172.17.2.17  netmask 255.255.255.0  broadcast 172.17.2.255\\n")},
        "sudo ovs-vsctl list-ports br-tun": CmdOutput(ports),
        "sudo ovs-vsctl -f json list interface": CmdOutput(ovs_vsctl_interface_file),
        "sudo ovs-ofctl --read-only --no-stats --no-names dump-flows br-tun table=22": CmdOutput(table_22)}


def get_dict_failed_missing_outputting(cmd_input_output_dict):
    table_22_missing_outputting = """ cookie=0x3491e5c468a22c3c, table=22, priority=1,dl_vlan=58 actions=strip_vlan\
    ,load:0x62->NXM_NX_TUN_ID[],output:2,output:3
cookie=0x3491e5c468a22c3c, table=22, priority=1,dl_vlan=74 actions=strip_vlan,load:0xc->NXM_NX_TUN_ID[],output:16\
,output:2,output:3
cookie=0x3491e5c468a22c3c, table=22, priority=0 actions=drop
"""
    cmd_input_output_dict["sudo ovs-ofctl --read-only --no-stats --no-names dump-flows br-tun table=22"] = CmdOutput(
        table_22_missing_outputting)
    return cmd_input_output_dict

def get_dict_failed_unrecognized_tunnel_ips(cmd_input_output_dict):
    cmd_input_output_dict["sudo ifconfig | grep 172.17.2"].pop("overcloud-ovscompute-pl-8004-i14-0")
    return cmd_input_output_dict


def get_dict_failed_unrecognized_remote_ips(cmd_input_output_dict):
    cmd_input_output_dict["sudo ifconfig | grep 172.17.2"].pop("overcloud-ovscompute-pl-8004-i14-1")
    return cmd_input_output_dict

def get_dict_failed_unrecognized_ips(cmd_input_output_dict):
    cmd_input_output_dict["sudo ifconfig | grep 172.17.2"].pop("overcloud-controller-pl-8004-i14-1")
    return cmd_input_output_dict


def get_dict_failed_no_flows_with_tunnel(cmd_input_output_dict):
    table_22_no_flows_with_tunnel = """ cookie=0x3491e5c468a22c3c, table=22, priority=1,dl_vlan=58 actions=strip_vlan,\
    load:0x62->NXM_NX_TUN_ID[],output:2,output:3
cookie=0x3491e5c468a22c3c, table=22, priority=0 actions=drop
"""
    cmd_input_output_dict["sudo ovs-ofctl --read-only --no-stats --no-names dump-flows br-tun table=22"] = CmdOutput(
        table_22_no_flows_with_tunnel)
    return cmd_input_output_dict


def get_dict_failed_running_on_hyp(cmd_input_output_dict):
    ovs_vsctl_interface_running_on_hyp_invalid_file = get_data_from_file(
        'ovs-vsctl_interface_running_on_hyp_invalid.txt')
    cmd_input_output_dict["sudo ovs-vsctl -f json list interface"] = CmdOutput(
        ovs_vsctl_interface_running_on_hyp_invalid_file)
    return cmd_input_output_dict


def get_dict_passed_v_18(cmd_input_output_dict):
    dict_copy = copy.deepcopy(cmd_input_output_dict)
    for key, value in list(dict_copy.items()):
        cmd_input_output_dict[
            key.replace('--read-only --no-stats --no-names dump-flows', 'dump-flows --read-only')] = value
    return cmd_input_output_dict


class TestVmsDataCollector(DataCollectorTestBase):
    tested_type = VmsDataCollector

    scenarios = [
        DataCollectorScenarioParams(
            scenario_title="basic scenario",
            cmd_input_output_dict={
                "sudo virsh list --all --uuid": CmdOutput(out="5ec12353-4717-4328-8469-0a0c506302a9"),
                "sudo virsh dumpxml 5ec12353-4717-4328-8469-0a0c506302a9": CmdOutput(
                    get_data_from_file('virsh_dumpxml_by_id_passed.out'))
            },
            version=Version.V20,
            scenario_res={"fa:16:3e:81:ed:52": "aim-2-network",
                          "fa:16:3e:91:11:54": "aim-2-network"}
        )
    ]

    @pytest.mark.parametrize("scenario_params", scenarios)
    def test_collect_data(self, scenario_params, tested_object):
        DataCollectorTestBase.test_collect_data(self, scenario_params, tested_object)


class TestAgentsDataCollector(DataCollectorTestBase):
    tested_type = AgentsDataCollector

    scenarios = [
        DataCollectorScenarioParams(
            scenario_title="basic scenario",
            cmd_input_output_dict={
                "sudo ip netns list": CmdOutput(out="qdhcp-11dc2712-93eb-4b97-9783-0b2a1bb7765d (id: 3)"),
                "sudo ip -n qdhcp-11dc2712-93eb-4b97-9783-0b2a1bb7765d -br link": CmdOutput(
                    get_data_from_file('ip_namespace_br_link_passed.out'))
            },
            scenario_res={"fa:16:3e:f2:cd:46": "qdhcp-11dc2712-93eb-4b97-9783-0b2a1bb7765d"}
        )
    ]

    @pytest.mark.parametrize("scenario_params", scenarios)
    def test_collect_data(self, scenario_params, tested_object):
        DataCollectorTestBase.test_collect_data(self, scenario_params, tested_object)


class TestFlowsDataCollector(DataCollectorTestBase):
    tested_type = FlowsDataCollector
    br_tun_out = """patch-int
vxlan-ac11020f
vxlan-ac110213
vxlan-ac110215
vxlan-ac110222
vxlan-ac110223
"""

    table_20_out = "cookie=0xd55448b81cb172a9, table=20, priority=2,dl_vlan=22,dl_dst=fa:16:3e:f5:8b:02 actions=strip_vlan,load:0x29->NXM_NX_TUN_ID[],output:3"
    scenarios = [
        DataCollectorScenarioParams(
            version=Version.V19A,
            scenario_title="basic scenario",
            cmd_input_output_dict={
                "sudo ovs-ofctl --read-only --no-stats --no-names dump-flows br-tun table=20": CmdOutput(
                    out=table_20_out),
                "sudo ovs-vsctl list-ports br-tun": CmdOutput(out=br_tun_out),
                "sudo ovs-ofctl --read-only --no-stats --no-names dump-flows br-tun table=21": CmdOutput(
                    out=get_data_from_file("table_21_passed.out")),
                "sudo ip -n qdhcp-11dc2712-93eb-4b97-9783-0b2a1bb7765d -br link": CmdOutput(
                    get_data_from_file('ip_namespace_br_link_passed.out')),
                "sudo ovs-vsctl -f json list interface": CmdOutput(
                    get_data_from_file('ovs_vsctl_list_interface_compute_passed.out'))
            },
            scenario_res=[
                {'mac': "fa:16:3e:f5:8b:02", 'ip': "45.45.45.3", 'vlan': 41, 'remote_ip': "172.17.2.28",
                 'local_ip': "172.17.2.12", 'output': "3",
                 'port_name': "vxlan-ac11020f"}]
        ),
        DataCollectorScenarioParams(
            version=Version.V18_5,
            scenario_title="version 18.5",
            cmd_input_output_dict={
                "sudo ovs-ofctl dump-flows --read-only br-tun table=20": CmdOutput(out=table_20_out),
                "sudo ovs-vsctl list-ports br-tun": CmdOutput(out=br_tun_out),
                "sudo ovs-ofctl dump-flows --read-only br-tun table=21": CmdOutput(
                    out=get_data_from_file("table_21_passed.out")),
                "sudo ip -n qdhcp-11dc2712-93eb-4b97-9783-0b2a1bb7765d -br link": CmdOutput(
                    get_data_from_file('ip_namespace_br_link_passed.out')),
                "sudo ovs-vsctl -f json list interface": CmdOutput(
                    get_data_from_file('ovs_vsctl_list_interface_compute_passed.out'))
            },
            scenario_res=[
                {'mac': "fa:16:3e:f5:8b:02", 'ip': "45.45.45.3", 'vlan': 41, 'remote_ip': "172.17.2.28",
                 'local_ip': "172.17.2.12", 'output': "3",
                 'port_name': "vxlan-ac11020f"}]
        )
    ]

    @pytest.mark.parametrize("scenario_params", scenarios)
    def test_collect_data(self, scenario_params, tested_object):
        DataCollectorTestBase.test_collect_data(self, scenario_params, tested_object)


class DumpFlowsTestBase(InformatorValidatorTestBase):

    def _init_mocks(self, tested_object):
        sys_parameters.get_base_conf = Mock()
        sys_parameters.get_base_conf.return_value = self.additional_parameters_dict['base_conf']
        sys_parameters.get_host_executor_factory.return_value.get_roles_map_dict = Mock()
        sys_parameters.get_host_executor_factory.return_value.get_roles_map_dict.return_value = \
            self.additional_parameters_dict['roles_map_dict']
        tested_object.is_not_connected_host = Mock()
        tested_object._host_executor.host_name = self.additional_parameters_dict['host_name']
        if self.additional_parameters_dict.get("test_hosts", None):
            sys_parameters.get_host_executor_factory.return_value.get_all_host_executors = Mock()
            hosts_dict = {}
            for host, is_connected in list(self.additional_parameters_dict["test_hosts"].items()):
                host_executor = Mock()
                host_executor.is_connected = is_connected
                hosts_dict[host] = host_executor
            sys_parameters.get_host_executor_factory.return_value.get_all_host_executors.return_value = hosts_dict
        else:
            tested_object.is_not_connected_host.return_value = False


class TestUnicastDumpFlows(DumpFlowsTestBase):
    base_conf = {
        "CBIS": {"subnets": {"tenant": {"network_address": "172.17.2.0/24"}}}
    }
    roles_map_dict = {'OvsCompute': ['overcloud-ovscompute-191-0 at 172.31.0.14'],
                      'hypervisor': ['hypervisor at 172.31.7.254'],
                      'undercloud': ['undercloud at localhost'],
                      'controllers': ['overcloud-controller-191-0 at 172.31.0.24'],
                      'computes': ['overcloud-ovscompute-191-0 at 172.31.0.14'],
                      'one_controller': ['overcloud-controller-191-0 at 172.31.0.24'],
                      'storages': ['overcloud-ovscompute-191-0 at 172.31.0.14'],
                      'all-hosts': ['overcloud-ovscompute-191-0 at 172.31.0.14',
                                    'overcloud-controller-191-0 at 172.31.0.24',
                                    'undercloud at localhost']}
    roles_map_dict_multiple_host = {'OvsCompute': ['overcloud-ovscompute-191-0 at 172.31.0.14'],
                                    'SriovCompute': ['overcloud-sriovperformancecompute-191-0 at 172.31.0.27'],
                                    'hypervisor': ['hypervisor at 172.31.7.254'],
                                    'undercloud': ['undercloud at localhost'],
                                    'controllers': ['overcloud-controller-191-0 at 172.31.0.24'],
                                    'computes': ['overcloud-ovscompute-191-0 at 172.31.0.14',
                                                 'overcloud-sriovperformancecompute-191-0 at 172.31.0.27'],
                                    'one_controller': ['overcloud-controller-191-0 at 172.31.0.24'],
                                    'storages': ['overcloud-ovscompute-191-0 at 172.31.0.14',
                                                 'overcloud-sriovperformancecompute-191-0 at 172.31.0.27'],
                                    'all-hosts': ['overcloud-ovscompute-191-0 at 172.31.0.14',
                                                  'overcloud-sriovperformancecompute-191-0 at 172.31.0.27'
                                                  'overcloud-controller-191-0 at 172.31.0.24',
                                                  'undercloud at localhost']}
    additional_parameters_dict = {"host_name": 'overcloud-controller-191-0',
                                  "base_conf": base_conf,
                                  "roles_map_dict": roles_map_dict
                                  }
    additional_parameters_dict_compute = {"host_name": 'overcloud-ovscompute-191-0',
                                          "base_conf": base_conf,
                                          "roles_map_dict": roles_map_dict
                                          }
    additional_parameters_dict_multiple_host = {"host_name": 'overcloud-controller-191-0',
                                                "base_conf": base_conf,
                                                "roles_map_dict": roles_map_dict_multiple_host
                                                }
    tested_type = UnicastDumpFlows
    out = "kubernetes   ClusterIP   10.254.0.1   <none>   443/TCP   37d"
    cmd = "sudo kubectl get svc kubernetes --no-headers"
    dict_out = {"sudo ifconfig | grep 172.17.2": {"overcloud-controller-191-0": CmdOutput(
        "inet 172.17.2.14  netmask 255.255.255.0  broadcast 172.17.2.255\\n"),
        "overcloud-ovscompute-191-0": CmdOutput(
            "inet 172.17.2.28  netmask 255.255.255.0  broadcast 172.17.2.255\\n")}}
    dict_out_multiple_host = {"sudo ifconfig | grep 172.17.2": {"overcloud-controller-191-0": CmdOutput(
        "inet 172.17.2.14  netmask 255.255.255.0  broadcast 172.17.2.255\\n"),
        "overcloud-ovscompute-191-0": CmdOutput(
            "inet 172.17.2.28  netmask 255.255.255.0  broadcast 172.17.2.255\\n"),
        "overcloud-sriovperformancecompute-191-0": CmdOutput(
            "inet 172.17.2.21  netmask 255.255.255.0  broadcast 172.17.2.255\\n")}}
    scenario_passed = [
        InformatorValidatorScenarioParams(
            scenario_title="scenario_controller_invalid_switch_port_not_exist_mac_is_unknown",
            expected_system_info="Flows: INVALID: 1, UNKNOWN: 0, VALID: 0\n",
            table_system_info=TableSystemInfo(table=[['overcloud-controller-191-0', 'fa:16:3e:f2:cd:46 -> port.2', 'INVALID',
                                                      'switch port 2 does not exist. fa:16:3e:f2:cd:46 is unknown']]),
            cmd_input_output_dict=dict_out,
            data_collector_dict={
                FlowsDataCollector: {"overcloud-controller-191-0": [
                    {'mac': "fa:16:3e:f2:cd:46", 'ip': "100.1.1.1", 'vlan': 41, 'remote_ip': "172.17.2.14",
                     'local_ip': "172.17.2.12", 'output': "2",
                     'port_name': "2"}]},
                AgentsDataCollector: {
                    "overcloud-controller-191-0": {"fa:16:3e:f2:cd:46": "qdhcp-11dc2712-93eb-4b97-9783-0b2a1bb7765d"}},
                VmsDataCollector: {"overcloud-ovscompute-191-0": {}}
            },
            version=Version.V19A,
            additional_parameters_dict=additional_parameters_dict),
        InformatorValidatorScenarioParams(
            scenario_title="scenario_controller_unknown_running_on_this_hypervisor",
            expected_system_info="Flows: INVALID: 0, UNKNOWN: 1, VALID: 0\n",
            table_system_info=TableSystemInfo(table=[
                ['overcloud-controller-191-0', 'fa:16:3e:f2:cd:46 -> 172.17.2.14 (overcloud-controller-191-0)',
                 'UNKNOWN',
                 'qdhcp-11dc2712-93eb-4b97-9783-0b2a1bb7765d running on this hypervisor (overcloud-controller-191-0)']]),
            cmd_input_output_dict=dict_out,
            data_collector_dict={
                FlowsDataCollector: {"overcloud-controller-191-0": [
                    {'mac': "fa:16:3e:f2:cd:46", 'ip': "100.1.1.1", 'vlan': 41, 'remote_ip': "172.17.2.14",
                     'local_ip': "172.17.2.12", 'output': "2",
                     'port_name': "2"}]},
                AgentsDataCollector: {
                    "overcloud-controller-191-0": {"fa:16:3e:f2:cd:46": "qdhcp-11dc2712-93eb-4b97-9783-0b2a1bb7765d"}},
                VmsDataCollector: {"overcloud-ovscompute-191-0": {}}
            },
            version=Version.V19A,
            additional_parameters_dict=additional_parameters_dict),
        InformatorValidatorScenarioParams(
            scenario_title="scenario_valid",
            expected_system_info="Flows: INVALID: 0, UNKNOWN: 0, VALID: 2\n",
            table_system_info=TableSystemInfo(table=[
                ['overcloud-ovscompute-191-0', 'fa:16:3e:f2:cd:46 -> 172.17.2.14 (overcloud-controller-191-0)', 'VALID',
                 'qdhcp-11dc2712-93eb-4b97-9783-0b2a1bb7765d'],
                ['overcloud-controller-191-0', 'fa:16:3e:91:11:54 -> 172.17.2.28 (overcloud-ovscompute-191-0)', 'VALID',
                 'aim-2-network']]),
            cmd_input_output_dict=dict_out,
            data_collector_dict={
                FlowsDataCollector: {"overcloud-controller-191-0": [
                    {'mac': "fa:16:3e:91:11:54", 'ip': "100.1.1.1", 'vlan': 41, 'remote_ip': "172.17.2.28",
                     'local_ip': "172.17.2.12", 'output': "3",
                     'port_name': "2"}],
                    "overcloud-ovscompute-191-0": [
                        {'mac': "fa:16:3e:f2:cd:46", 'ip': "100.1.1.1", 'vlan': 41, 'remote_ip': "172.17.2.14",
                         'local_ip': "172.17.2.12", 'output': "3",
                         'port_name': "2"}]
                },
                AgentsDataCollector: {
                    "overcloud-controller-191-0": {"fa:16:3e:f2:cd:46": "qdhcp-11dc2712-93eb-4b97-9783-0b2a1bb7765d"}},
                VmsDataCollector: {"overcloud-ovscompute-191-0": {"fa:16:3e:81:ed:52": "aim-2-network",
                                                                  "fa:16:3e:91:11:54": "aim-2-network"}}
            },
            version=Version.V19A,
            additional_parameters_dict=additional_parameters_dict_multiple_host),
        InformatorValidatorScenarioParams(
            scenario_title="scenario_compute_unknown_running_on_this_hypervisor",
            expected_system_info="Flows: INVALID: 0, UNKNOWN: 1, VALID: 0\n",
            table_system_info=TableSystemInfo(table=[
                ['overcloud-ovscompute-191-0', 'fa:16:3e:91:11:54 -> 172.17.2.28 (overcloud-ovscompute-191-0)',
                 'UNKNOWN', 'aim-2-network running on this hypervisor (overcloud-ovscompute-191-0)']]),
            cmd_input_output_dict=dict_out,
            data_collector_dict={
                FlowsDataCollector: {
                    "overcloud-ovscompute-191-0": [
                        {'mac': "fa:16:3e:91:11:54", 'ip': "100.1.1.1", 'vlan': 41, 'remote_ip': "172.17.2.28",
                         'local_ip': "172.17.2.12", 'output': "3",
                         'port_name': "2"}]
                },
                AgentsDataCollector: {
                    "overcloud-controller-191-0": {}},
                VmsDataCollector: {"overcloud-ovscompute-191-0": {"fa:16:3e:81:ed:52": "aim-2-network",
                                                                  "fa:16:3e:91:11:54": "aim-2-network"}}
            },
            version=Version.V19A,
            additional_parameters_dict=additional_parameters_dict_compute)]
    scenario_failed_collect_flows_data_collector = {
        "environment_info": {
            "lab_name": "one_controller",
            "deployment_type": "Deployment_type.CBIS",
            "host_name": "overcloud-controller-191-0"
        },
        "inputs": {
            "sudo /bin/hiera -c /etc/puppet/hiera.yaml mysql::server::root_password": "echo xxx",
            "sudo mysql -u root -pxxx -e 'use ovs_neutron; select ip_address, host from  ml2_vxlan_endpoints'": "cat tests/validation_tests/inputs/dump_flows_paths/host_name_by_ip_mysql_passed.out",
            "sudo ovs-vsctl list-ports br-tun": "echo \"patch-int\nvxlan-ac11020f\nvxlan-ac110213\nvxlan-ac110215\nvxlan-ac110222\nvxlan-ac110223\n\"",
            "sudo ovs-vsctl -f json list interface": "cat tests/validation_tests/inputs/dump_flows_paths/ovs_vsctl_list_interface_passed.out",
            "sudo ovs-ofctl --read-only --no-stats --no-names dump-flows br-tun table=20": "bash -c 'exit 1'",
            "sudo ip netns list": "echo 'qdhcp-11dc2712-93eb-4b97-9783-0b2a1bb7765d (id: 3)'",
            "sudo ip -n qdhcp-11dc2712-93eb-4b97-9783-0b2a1bb7765d -br link": "cat tests/validation_tests/inputs/dump_flows_paths/ip_namespace_br_link_passed.out",
            "sudo virsh list --all --uuid": "echo \n",
            "sudo ovs-ofctl --read-only --no-stats --no-names dump-flows br-tun table=21": "cat tests/validation_tests/inputs/dump_flows_paths/table_21_passed.out"
        },
        "expected_out": {
            "pass": "false",
            "table_system_info": "[]",
            "system_info": "",
            "failed_msg": "Failed to collect data for overcloud-controller-191-0 (details in the .json file)\n\n\nHashtags:\n#system_at_risk\n#hidden_issue\n",
            "is_expected_prerequisite_fulfill": "true",
            "is_expected_exception": "false"
        }
    }
    scenario_failed = [
        InformatorValidatorScenarioParams(
            scenario_title="scenario_controller_invalid_unknown_mac_address",
            failed_msg="Some of the flows failed\n",
            expected_system_info="Flows: INVALID: 1, UNKNOWN: 0, VALID: 0\n",
            table_system_info=TableSystemInfo(table=[
                ['overcloud-controller-191-0', 'fa:16:3e:f5:8b:02 -> 172.17.2.28 (overcloud-ovscompute-191-0)',
                 'INVALID',
                 'unknown mac address fa:16:3e:f5:8b:02']]),
            cmd_input_output_dict=dict_out,
            data_collector_dict={
                FlowsDataCollector: {"overcloud-controller-191-0": [
                    {'mac': "fa:16:3e:f5:8b:02", 'ip': "100.1.1.1", 'vlan': 41, 'remote_ip': "172.17.2.28",
                     'local_ip': "172.17.2.12", 'output': "3",
                     'port_name': "2"}]},
                AgentsDataCollector: {
                    "overcloud-controller-191-0": {"fa:16:3e:f2:cd:46": "qdhcp-11dc2712-93eb-4b97-9783-0b2a1bb7765d"}},
                VmsDataCollector: {"overcloud-ovscompute-191-0": {}}
            },
            version=Version.V19A,
            additional_parameters_dict=additional_parameters_dict),
        InformatorValidatorScenarioParams(
            scenario_title="scenario_controller_invalid_tunnel_destination_unknown",
            failed_msg="Some of the flows failed\n",
            expected_system_info="Flows: INVALID: 1, UNKNOWN: 0, VALID: 0\n",
            table_system_info=TableSystemInfo(table=[['overcloud-controller-191-0', 'fa:16:3e:f2:cd:46 -> port.vxlan-ac11020f', 'INVALID',
                                'tunnel destination unknown']]),
            cmd_input_output_dict=dict_out,
            data_collector_dict={
                FlowsDataCollector: {"overcloud-controller-191-0": [
                    {'mac': "fa:16:3e:f2:cd:46", 'ip': "100.1.1.1", 'vlan': 41, 'remote_ip': "172.17.2.27",
                     'local_ip': "172.17.2.12", 'output': "3",
                     'port_name': "vxlan-ac11020f"}]},
                AgentsDataCollector: {
                    "overcloud-controller-191-0": {"fa:16:3e:f2:cd:46": "qdhcp-11dc2712-93eb-4b97-9783-0b2a1bb7765d"}},
                VmsDataCollector: {"overcloud-ovscompute-191-0": {}}
            },
            version=Version.V19A,
            additional_parameters_dict=additional_parameters_dict),
        InformatorValidatorScenarioParams(
            scenario_title="scenario_failed_collect_agents_data_collector",
            failed_msg="Failed to collect data for overcloud-controller-191-0 (details in the .json file)\n",
            expected_system_info="No flows found on overcloud-controller-191-0\n",
            table_system_info=TableSystemInfo(table=[]),
            cmd_input_output_dict=dict_out,
            version=Version.V19A,
            additional_parameters_dict=additional_parameters_dict_compute),
        InformatorValidatorScenarioParams(
            scenario_title="scenario_controller_invalid_tunnel_destination_unknown",
            failed_msg="Some of the flows failed\n",
            expected_system_info="Flows: INVALID: 1, UNKNOWN: 0, VALID: 0\n",
            table_system_info=TableSystemInfo(table=[
                ['overcloud-ovscompute-191-0', 'fa:16:3e:91:11:54 -> 172.17.2.28 (overcloud-ovscompute-191-0)',
                 'INVALID', 'unknown mac address fa:16:3e:91:11:54']]),
            cmd_input_output_dict=dict_out,
            data_collector_dict={
                FlowsDataCollector: {"overcloud-controller-191-0": [
                    {'mac': "fa:16:3e:f2:cd:46", 'ip': "100.1.1.1", 'vlan': 41, 'remote_ip': "172.17.2.28",
                     'local_ip': "172.17.2.12", 'output': "3",
                     'port_name': "2"}]},
                AgentsDataCollector: {
                    "overcloud-controller-191-0": {}},
                VmsDataCollector: {"overcloud-ovscompute-191-0": {}}
            },
            version=Version.V19A,
            additional_parameters_dict=additional_parameters_dict_compute),
        InformatorValidatorScenarioParams(
            scenario_title="scenario_compute_invalid",
            failed_msg="Some of the flows failed\n",
            expected_system_info="Flows: INVALID: 1, UNKNOWN: 0, VALID: 0\n",
            table_system_info=TableSystemInfo(table=[
                ['overcloud-ovscompute-191-0', 'fa:16:3e:91:11:54 -> 172.17.2.14 (overcloud-controller-191-0)',
                 'INVALID',
                 'fa:16:3e:91:11:54 assigned to aim-2-network located on overcloud-ovscompute-191-0 (172.17.2.28)']]),
            cmd_input_output_dict=dict_out,
            data_collector_dict={
                FlowsDataCollector: {"overcloud-controller-191-0": [
                    {'mac': "fa:16:3e:f2:cd:46", 'ip': "100.1.1.1", 'vlan': 41, 'remote_ip': "172.17.2.14",
                     'local_ip': "172.17.2.12", 'output': "3",
                     'port_name': "2"}]},
                AgentsDataCollector: {
                    "overcloud-controller-191-0": {}},
                VmsDataCollector: {"overcloud-ovscompute-191-0": {"fa:16:3e:81:ed:52": "aim-2-network",
                                                                  "fa:16:3e:91:11:54": "aim-2-network"}}
            },
            version=Version.V19A,
            additional_parameters_dict=additional_parameters_dict_compute),
        InformatorValidatorScenarioParams(
            scenario_title="scenario_controller_invalid",
            failed_msg="Some of the flows failed\n",
            expected_system_info="Flows: INVALID: 1, UNKNOWN: 0, VALID: 0\n",
            table_system_info=TableSystemInfo(table=[
                ['overcloud-controller-191-0', 'fa:16:3e:f2:cd:46 -> 172.17.2.28 (overcloud-ovscompute-191-0)',
                 'INVALID',
                 'fa:16:3e:f2:cd:46 assigned to qdhcp-11dc2712-93eb-4b97-9783-0b2a1bb7765d located on overcloud-controller-191-0 (172.17.2.14)']]),
            cmd_input_output_dict=dict_out,
            data_collector_dict={
                FlowsDataCollector: {"overcloud-controller-191-0": [
                    {'mac': "fa:16:3e:f2:cd:46", 'ip': "100.1.1.1", 'vlan': 41, 'remote_ip': "172.17.2.28",
                     'local_ip': "172.17.2.12", 'output': "3",
                     'port_name': "2"}]},
                AgentsDataCollector: {
                    "overcloud-controller-191-0": {"fa:16:3e:f2:cd:46": "qdhcp-11dc2712-93eb-4b97-9783-0b2a1bb7765d"}},
                VmsDataCollector: {"overcloud-ovscompute-191-0": {}}
            },
            version=Version.V19A,
            additional_parameters_dict=additional_parameters_dict),
        InformatorValidatorScenarioParams(
            scenario_title="scenario_compute_invalid_unknown_mac_address",
            failed_msg="Some of the flows failed\n",
            expected_system_info="Flows: INVALID: 1, UNKNOWN: 0, VALID: 0\n",
            table_system_info=TableSystemInfo(table=[
                ['overcloud-ovscompute-191-0', 'fa:16:3e:91:11:54 -> 172.17.2.28 (overcloud-ovscompute-191-0)',
                 'INVALID', 'unknown mac address fa:16:3e:91:11:54']]),
            cmd_input_output_dict=dict_out,
            data_collector_dict={
                FlowsDataCollector: {"overcloud-controller-191-0": [
                    {'mac': "fa:16:3e:91:11:54", 'ip': "100.1.1.1", 'vlan': 41, 'remote_ip': "172.17.2.28",
                     'local_ip': "172.17.2.12", 'output': "3",
                     'port_name': "2"}]},
                AgentsDataCollector: {
                    "overcloud-controller-191-0": {}},
                VmsDataCollector: {"overcloud-ovscompute-191-0": {}}
            },
            version=Version.V19A,
            additional_parameters_dict=additional_parameters_dict_compute),
        InformatorValidatorScenarioParams(
            scenario_title="scenario_invalid_duplicate",
            failed_msg="Some of the flows failed\n",
            expected_system_info="Flows: INVALID: 1, UNKNOWN: 0, VALID: 0\n",
            table_system_info=TableSystemInfo(table=[
                ['overcloud-controller-191-0', 'fa:16:3e:f2:cd:46 -> 172.17.2.28 (overcloud-ovscompute-191-0)',
                 'INVALID',
                 "fa:16:3e:f2:cd:46 maps to {'172.17.2.21': 'aim-2-network', '172.17.2.14': 'qdhcp-11dc2712-93eb-4b97-9783-0b2a1bb7765d'}"]]),
            cmd_input_output_dict=dict_out_multiple_host,
            data_collector_dict={
                FlowsDataCollector: {"overcloud-controller-191-0": [
                    {'mac': "fa:16:3e:f2:cd:46", 'ip': "100.1.1.1", 'vlan': 41, 'remote_ip': "172.17.2.28",
                     'local_ip': "172.17.2.12", 'output': "3",
                     'port_name': "3"}]},
                AgentsDataCollector: {
                    "overcloud-controller-191-0": {"fa:16:3e:f2:cd:46": "qdhcp-11dc2712-93eb-4b97-9783-0b2a1bb7765d"}},
                VmsDataCollector: {"overcloud-ovscompute-191-0": {"fa:16:3e:81:ed:52": "aim-2-network",
                                                                  "fa:16:3e:91:11:54": "aim-2-network"},
                                   "overcloud-sriovperformancecompute-191-0": {"fa:16:3e:81:ed:52": "aim-2-network",
                                                                               "fa:16:3e:f2:cd:46": "aim-2-network"}}
            },
            version=Version.V19A,
            additional_parameters_dict=additional_parameters_dict),
        InformatorValidatorScenarioParams(
            scenario_title="scenario_compute_invalid_switch_port_not_exist_mac_is_unknown",
            failed_msg="Some of the flows failed\n",
            expected_system_info="Flows: INVALID: 1, UNKNOWN: 0, VALID: 0\n",
            table_system_info=TableSystemInfo(table=[['overcloud-ovscompute-191-0', 'fa:16:3e:f2:cd:46 -> port.2', 'INVALID',
                                'switch port 2 does not exist. fa:16:3e:f2:cd:46 is unknown']]),
            cmd_input_output_dict=dict_out,
            data_collector_dict={
                FlowsDataCollector: {"overcloud-controller-191-0": [
                    {'mac': "fa:16:3e:f2:cd:46", 'ip': "100.1.1.1", 'vlan': 41, 'remote_ip': "172.17.2.14",
                     'local_ip': "172.17.2.12", 'output': "2",
                     'port_name': "2"}]},
                AgentsDataCollector: {
                    "overcloud-controller-191-0": {}},
                VmsDataCollector: {"overcloud-ovscompute-191-0": {"fa:16:3e:81:ed:52": "aim-2-network",
                                                                  "fa:16:3e:91:11:54": "aim-2-network"}}
            },
            version=Version.V19A,
            additional_parameters_dict=additional_parameters_dict_compute),
        InformatorValidatorScenarioParams(
            scenario_title="scenario_compute_invalid_tunnel_destination_unknown",
            failed_msg="Some of the flows failed\n",
            expected_system_info="Flows: INVALID: 1, UNKNOWN: 0, VALID: 0\n",
            table_system_info=TableSystemInfo(table=[['overcloud-ovscompute-191-0', 'fa:16:3e:91:11:54 -> port.vxlan-ac11020f', 'INVALID',
                                'tunnel destination unknown']]),
            cmd_input_output_dict=dict_out,
            data_collector_dict={
                FlowsDataCollector: {"overcloud-controller-191-0": [
                    {'mac': "fa:16:3e:91:11:54", 'ip': "100.1.1.1", 'vlan': 41, 'remote_ip': "172.17.2.15",
                     'local_ip': "172.17.2.12", 'output': "3",
                     'port_name': "vxlan-ac11020f"}]},
                AgentsDataCollector: {
                    "overcloud-controller-191-0": {}},
                VmsDataCollector: {"overcloud-ovscompute-191-0": {"fa:16:3e:81:ed:52": "aim-2-network",
                                                                  "fa:16:3e:91:11:54": "aim-2-network"}}
            },
            version=Version.V19A,
            additional_parameters_dict=additional_parameters_dict_compute)
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        InformatorValidatorTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        origin_scenario_params = copy.copy(scenario_params)
        if scenario_params.scenario_title == "scenario_failed_collect_agents_data_collector":
            scenario_params.tested_object_mock_dict = {
                "run_data_collector": Mock(side_effect=tested_object.run_data_collector)}
            scenario_params.library_mocks_dict = {
                "FlowsOperator.run_data_collector": Mock(
                    side_effect=_run_data_collector_failed_collect_agents_data_side_effects)
            }
        else:
            scenario_params = origin_scenario_params
        InformatorValidatorTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestMulticastDumpFlows(DumpFlowsTestBase):
    dpdk_host = "overcloud-dpdkperformancecompute-cbis22-0 at 172.31.3.162"
    base_conf = {
        "CBIS": {"subnets": {"tenant": {"network_address": "172.17.2.0/24"}}}
    }
    roles_map_dict = {'OvsCompute': ['overcloud-ovscompute-pl-8004-i14-0 at 172.31.0.27',
                                     'overcloud-ovscompute-pl-8004-i14-1 at 172.31.0.5'],
                      'hypervisor': ['hypervisor at 172.31.7.254'],
                      'undercloud': ['undercloud at localhost'],
                      'controllers': ['overcloud-controller-pl-8004-i14-0 at 172.31.0.32',
                                      'overcloud-controller-pl-8004-i14-1 at 172.31.0.10',
                                      'overcloud-controller-pl-8004-i14-2 at 172.31.0.25'],
                      'computes': ['overcloud-ovscompute-pl-8004-i14-0 at 172.31.0.27',
                                   'overcloud-ovscompute-pl-8004-i14-1 at 172.31.0.5'],
                      'one_controller': ['overcloud-controller-pl-8004-i14-0'],
                      'storages': ['overcloud-ovscompute-pl-8004-i14-0 at 172.31.0.27',
                                   'overcloud-ovscompute-pl-8004-i14-1 at 172.31.0.5'],
                      'all-hosts': ['overcloud-ovscompute-pl-8004-i14-0 at 172.31.0.27',
                                    'overcloud-ovscompute-pl-8004-i14-1 at 172.31.0.5',
                                    'overcloud-controller-pl-8004-i14-0 at 172.31.0.32',
                                    'overcloud-controller-pl-8004-i14-1 at 172.31.0.10',
                                    'overcloud-controller-pl-8004-i14-2 at 172.31.0.25',
                                    'undercloud at localhost']}
    additional_parameters_dict = {"host_name": 'overcloud-controller-pl-8004-i14-0',
                                  "base_conf": base_conf,
                                  "roles_map_dict": roles_map_dict
                                  }
    roles_map_dict_with_dpdk = roles_map_dict.copy()
    roles_map_dict_with_dpdk["DpdkCompute"] = [dpdk_host]
    roles_map_dict_with_dpdk["all-hosts"].append(dpdk_host)
    roles_map_dict_with_dpdk["computes"].append(dpdk_host)
    additional_parameters_dict_dpdk = additional_parameters_dict.copy()
    additional_parameters_dict_not_connected = additional_parameters_dict.copy()
    additional_parameters_dict_dpdk["roles_map_dict"] = roles_map_dict_with_dpdk
    additional_parameters_dict_not_connected["test_hosts"] = {"overcloud-ovscompute-pl-8004-i14-0": True,
                                                              "overcloud-ovscompute-pl-8004-i14-1": True,
                                                              "overcloud-controller-pl-8004-i14-0": True,
                                                              "overcloud-controller-pl-8004-i14-1": True,
                                                              "overcloud-controller-pl-8004-i14-2": False}
    tested_type = MulticastDumpFlows
    scenarios = [
        InformatorValidatorScenarioParams("passed version=20",
                                          expected_system_info='Multicast traffic OK',
                                          cmd_input_output_dict=get_passed_dict(),
                                          tested_object_mock_dict={
                                              "run_data_collector": Mock(side_effect=run_data_collector_side_effects)
                                          },
                                          version=Version.V20,
                                          additional_parameters_dict=additional_parameters_dict),
        InformatorValidatorScenarioParams("passed dpdk",
                                          expected_system_info='Multicast traffic OK',
                                          cmd_input_output_dict=get_passed_dict(),
                                          tested_object_mock_dict={
                                              "run_data_collector": Mock(side_effect=run_data_collector_side_effects)
                                          },
                                          version=Version.V20,
                                          additional_parameters_dict=additional_parameters_dict_dpdk),
        InformatorValidatorScenarioParams("passed version=18",
                                          expected_system_info='Multicast traffic OK',
                                          cmd_input_output_dict=get_dict_passed_v_18(get_passed_dict()),
                                          tested_object_mock_dict={
                                              "run_data_collector": Mock(side_effect=run_data_collector_side_effects)
                                          },
                                          version=Version.V18,
                                          additional_parameters_dict=additional_parameters_dict),
        InformatorValidatorScenarioParams("passed not connected",
                                          expected_system_info='Multicast traffic OK',
                                          cmd_input_output_dict=get_passed_dict(),
                                          tested_object_mock_dict={
                                              "run_data_collector": Mock(side_effect=run_data_collector_side_effects)
                                          },
                                          version=Version.V20,
                                          additional_parameters_dict=additional_parameters_dict_not_connected),
        InformatorValidatorScenarioParams("failed unrecognized tunnel ips & remote ips",
                                          expected_system_info="Unrecognized tunnel ips: ['172.17.2.13'].\nUnrecognized flow remote ips: [u'172.17.2.13'].",
                                          cmd_input_output_dict=get_dict_failed_unrecognized_ips(get_passed_dict()),
                                          tested_object_mock_dict={
                                              "run_data_collector": Mock(side_effect=run_data_collector_side_effects)
                                          },
                                          version=Version.V20,
                                          additional_parameters_dict=additional_parameters_dict),
        InformatorValidatorScenarioParams("failed unrecognized tunnel ips",
                                          expected_system_info="Unrecognized tunnel ips: ['172.17.2.11'].",
                                          cmd_input_output_dict=get_dict_failed_unrecognized_tunnel_ips(
                                              get_dict_failed_missing_outputting(get_passed_dict())),
                                          tested_object_mock_dict={
                                              "run_data_collector": Mock(side_effect=run_data_collector_side_effects)
                                          },
                                          version=Version.V20,
                                          additional_parameters_dict=additional_parameters_dict),
        InformatorValidatorScenarioParams("failed unrecognized remote ips",
                                          expected_system_info="Unrecognized flow remote ips: [u'172.17.2.17'].",
                                          cmd_input_output_dict=get_dict_failed_unrecognized_remote_ips(get_passed_dict()),
                                          version=Version.V20,
                                          additional_parameters_dict=additional_parameters_dict,
                                          tested_object_mock_dict={
                                              "run_data_collector": Mock(
                                                  side_effect=run_data_collector_failed_redundant_outputting_side_effects)
                                          }),
        InformatorValidatorScenarioParams("failed missing_outputting",
                                          expected_system_info="Multicast traffic via tunnel_id: 12 is not outputting "
                                                               "to: ['172.17.2.11 (overcloud-ovscompute-pl-8004-i14-0)'"
                                                               "].",
                                          cmd_input_output_dict=get_dict_failed_missing_outputting(get_passed_dict()),
                                          tested_object_mock_dict={
                                              "run_data_collector": Mock(side_effect=run_data_collector_side_effects)
                                          },
                                          version=Version.V20,
                                          additional_parameters_dict=additional_parameters_dict),
        InformatorValidatorScenarioParams("failed redundant outputting",
                                          expected_system_info="Multicast traffic via tunnel_id: 12 cannot reach: "
                                                               "['172.17.2.17 (overcloud-ovscompute-pl-8004-i14-1)']"
                                                               ".",
                                          cmd_input_output_dict=get_passed_dict(),
                                          version=Version.V20,
                                          additional_parameters_dict=additional_parameters_dict,
                                          tested_object_mock_dict={
                                              "run_data_collector": Mock(
                                                  side_effect=run_data_collector_failed_redundant_outputting_side_effects)
                                          }),
        InformatorValidatorScenarioParams("failed tunnel not exist",
                                          expected_system_info="Invalid flow: tunnel_id: 98, remote_ip_list: ['172.17.2.15', '172.17.2.13'], "
                                                               "output: ['2', '3'], local_ip_list: "
                                                               "['172.17.2.21', '172.17.2.21'], "
                                                               "port_name_list: "
                                                               "['vxlan-ac11020f', 'vxlan-ac11020d']\ntunnel_id: 98"
                                                               " not exist.\nMulticast traffic via tunnel_id: 12 cannot"
                                                               " reach: ['172.17.2.13 (overcloud-controller-pl-"
                                                               "8004-i14-1)', '172.17.2.15 (overcloud-controller-pl"
                                                               "-8004-i14-2)', '172.17.2.21 (overcloud-controller-pl-8"
                                                               "004-i14-0)'].",
                                          cmd_input_output_dict=get_passed_dict(),
                                          tested_object_mock_dict={
                                              "run_data_collector": Mock(
                                                  side_effect=run_data_collector_failed_tunnel_not_exist_side_effects)
                                          },
                                          version=Version.V20,
                                          additional_parameters_dict=additional_parameters_dict),
        InformatorValidatorScenarioParams("no flows with tunnel + tunnel cannot reach hyp",
                                          expected_system_info='There are no multicast flows with tunnel_ids: [12] '
                                                               'on this host.',
                                          cmd_input_output_dict=get_dict_failed_no_flows_with_tunnel(get_passed_dict()),
                                          tested_object_mock_dict={
                                              "run_data_collector": Mock(side_effect=run_data_collector_side_effects)
                                          },
                                          version=Version.V20,
                                          additional_parameters_dict=additional_parameters_dict),
        InformatorValidatorScenarioParams("multicast traffic running on this hypervisor + missing outputting",
                                          expected_system_info="Multicast traffic via tunnel_id: 12 running on this "
                                                               "hypervisor.\nMulticast traffic via tunnel_id: 12 is "
                                                               "not outputting to: ['172.17.2.17 "
                                                               "(overcloud-ovscompute-pl-8004-i14-1)'].",
                                          cmd_input_output_dict=get_dict_failed_running_on_hyp(get_passed_dict()),
                                          tested_object_mock_dict={
                                              "run_data_collector": Mock(side_effect=run_data_collector_side_effects)
                                          },
                                          version=Version.V20,
                                          additional_parameters_dict=additional_parameters_dict
                                          )
    ]

    scenario_no_suitable_host = [
        InformatorValidatorScenarioParams(
            scenario_title="no suitable host scenario",
            tested_object_mock_dict={"get_host_name_by_ip_dict": Mock(return_value={}),
                                     "get_host_name_by_ip_connected_msg_dict": Mock(return_value={})},
            additional_parameters_dict=additional_parameters_dict,
            data_collector_dict={OpenstackUtilsDataCollector: {}}, expected_system_info="")]

    @pytest.mark.parametrize("scenario_params", scenarios)
    def test_scenario_passed(self, scenario_params, tested_object):
        InformatorValidatorTestBase.test_is_validation_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_no_suitable_host)
    def test_scenario_no_suitable_host(self, scenario_params, tested_object):
        log.init()
        InformatorValidatorTestBase.test_scenario_no_suitable_host(self, scenario_params, tested_object)