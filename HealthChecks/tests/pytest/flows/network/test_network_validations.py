from __future__ import absolute_import
import pytest
import warnings
import copy
from ipaddress import IPv4Address, IPv6Address
from tests.pytest.tools.versions_alignment import Mock
from flows.Network.network_validations import are_host_connected, NetworkInterfaceLinks, NetworkInterfaceAddresses, \
    WhereaboutsConfiguration, WhereaboutsDuplicateIPAddresses, WhereaboutsMissingPodrefs, \
    WhereaboutsMissingAllocations, WhereaboutsExistingAllocations, NoDynamicAddressInIptables, \
    GetMultusNodes, CalicoIpamBlockStatus, ValidateUcControlPlaneIpEtcHosts, CheckIptablesForManuallyAddedRules, \
    ValidateSelinuxContextDirIstio, VerifyMellanoxVFNumber, ValidateCorrectNetconfig, ValidateStaleStaticRouteConfig, \
    ValidateStaleNextHops, GetIPDetailsFromControllers, VerifyRouterIPActiveStatus
from flows.Etcd.etcd_validations import CalicoKubernetesAlignNodes
from tests.pytest.pytest_tools.operator.test_data_collector import DataCollectorTestBase, DataCollectorScenarioParams
from tests.pytest.pytest_tools.operator.test_operator import CmdOutput
from tests.pytest.pytest_tools.operator.test_validation_base import ValidationTestBase, ValidationScenarioParams
from tools.global_enums import Version, Deployment_type, Objectives
from six.moves import range


class TestAreHostConnected(ValidationTestBase):
    tested_type = are_host_connected

    get_host_executor_factory_mock = Mock()
    get_host_executor_factory_mock.return_value.get_all_host_executors = Mock(return_value={
        "workerbm-1": Mock(is_connected=True)})

    scenario_passed = [
        ValidationScenarioParams("all hosts are connected",
                                 library_mocks_dict={
                                     "sys_param.get_host_executor_factory": get_host_executor_factory_mock})
    ]

    get_host_executor_factory_mock_failed_1_host = Mock()
    get_host_executor_factory_mock_failed_1_host.return_value.get_all_host_executors = Mock(return_value={
        "workerbm-1": Mock(is_connected=True), "workerbm-2": Mock(is_connected=False)})

    get_host_executor_factory_mock_failed_2_host = Mock()
    get_host_executor_factory_mock_failed_2_host.return_value.get_all_host_executors = Mock(return_value={
        "workerbm-1": Mock(is_connected=False), "workerbm-2": Mock(is_connected=False)})

    scenario_failed = [
        ValidationScenarioParams("1 host not connected",
                                 library_mocks_dict={
                                     "sys_param.get_host_executor_factory":
                                         get_host_executor_factory_mock_failed_1_host}),
        ValidationScenarioParams("all host not connected",
                                 library_mocks_dict={
                                     "sys_param.get_host_executor_factory":
                                         get_host_executor_factory_mock_failed_2_host})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    def test_has_confluence(self, tested_object):
        # Override the func since this val doesn't have a confluence.
        # pls do not copy it! it's only for old validations that do not have a confluence page.
        warnings.warn("No confluence page")


class TestNetworkInterfaceLinks(ValidationTestBase):
    tested_type = NetworkInterfaceLinks

    cmd1 = "sudo cat /etc/os-net-config/config.json"

    out_format1 = """
    {{"network_config": [{{
            "members": [{{
                    "bonding_options": "mode=active-backup miimon=100",
                    "members": [{{
                            "mtu": 8000,
                            "name": {},
                            "primary": "true",
                            "type": "interface",
                            "use_dhcp": false
                        }}, {{
                            "mtu": 9000,
                            "name": {},
                            "type": "interface",
                            "use_dhcp": false
                        }}
                    ],
                    "mtu": 9000,
                    "name": {},
                    "type": "linux_bond"
                }}
            ],
            "mtu": 9000,
            "name": {},
            "type": "interface",
            "use_dhcp": false
        }}, {{
            "addresses": [{{
                    "ip_netmask": "172.17.1.13/24"
                }}
            ],
            "device": "infra-bond",
            "mtu": 9000,
            "type": "vlan",
            "use_dhcp": false,
            "vlan_id": {}
        }}
    ]}}
    """

    cmd2 = "sudo /sbin/ip -o link"

    out2 = """1: ens5f0: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN mode DEFAULT group default
    2: ens25f0: <BROADCAST,MULTICAST> mtu 1500 qdisc noop state DOWN mode DEFAULT group default 
    3: vlan103@infra-bond: <BROADCAST,MULTICAST,SLAVE,UP,LOWER_UP> mtu 9000 qdisc mq master infra-bond state UP 
    4: ens25f1: <BROADCAST,MULTICAST,SLAVE,UP,LOWER_UP> mtu 9000 qdisc mq master infra-bond state UP mode DEFAULT
    5: tenant-bond: <BROADCAST,MULTICAST,SLAVE,UP,LOWER_UP> mtu 9000 qdisc mq master tenant-bond state UP mode DEFAULT
    6: br-ex: <BROADCAST,MULTICAST,SLAVE,UP,LOWER_UP> mtu 9000 qdisc mq master tenant-bond state UP mode DEFAULT """

    cmd4 = "cat /sys/class/net/{}/operstate"

    cmd_input_output_dict_passed_scenario = {
        cmd1: CmdOutput(out=out_format1.format('"ens25f0"', '"ens25f1"', '"br-ex"', '"tenant-bond"', 103)),
        cmd2: CmdOutput(out=out2)
    }

    for i, interface in enumerate(["ens25f0", "vlan103", "ens25f1", "tenant-bond"]):
        cmd_input_output_dict_passed_scenario[cmd4.format(interface)] = CmdOutput("up")

    scenario_passed = [
        ValidationScenarioParams("all good", cmd_input_output_dict=cmd_input_output_dict_passed_scenario,
                                 version=Version.V24,
                                 library_mocks_dict={"gs.get_deployment_type": Mock(return_value=Deployment_type.CBIS)}
                                 )
    ]

    scenario_cmds_interface_not_active = copy.deepcopy(cmd_input_output_dict_passed_scenario)
    scenario_cmds_interface_not_active.update({cmd1: CmdOutput(out=out_format1.format(
        '"ens25f0"', '"ens25f1"', '"br-ex"', '"name-not-in-active"', 103))})

    scenario_cmds_state_down = copy.deepcopy(cmd_input_output_dict_passed_scenario)
    scenario_cmds_state_down.update({cmd4.format("vlan103"): CmdOutput(out="down")})

    scenario_cmds_all_bad = copy.deepcopy(cmd_input_output_dict_passed_scenario)
    scenario_cmds_all_bad.update({
        cmd1: CmdOutput(out=out_format1.format('"ens25f0"', '"ens25f1"', '"br-ex"', '"name-not-in-active"', 103)),
        cmd4.format("vlan103"): CmdOutput(out="down")
    })

    scenario_failed = [
        ValidationScenarioParams("interface not active", scenario_cmds_interface_not_active,
                                 version=Version.V24,
                                 library_mocks_dict={"gs.get_deployment_type": Mock(return_value=Deployment_type.CBIS)}),
        ValidationScenarioParams("state down", scenario_cmds_state_down,
                                 version=Version.V24,
                                 library_mocks_dict={"gs.get_deployment_type": Mock(return_value=Deployment_type.CBIS)}),
        ValidationScenarioParams("all bad", scenario_cmds_all_bad,
                                 version=Version.V24,
                                 library_mocks_dict={"gs.get_deployment_type": Mock(return_value=Deployment_type.CBIS)}),
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    def _init_mocks(self, tested_object):
        tested_object.file_utils.is_file_exist = Mock(side_effect=[False, True])


class TestNetworkInterfaceAddresses(ValidationTestBase):
    tested_type = NetworkInterfaceAddresses

    cmd1 = "sudo cat /etc/os-net-config/config.json"

    out_format1 = """
    {{"network_config": [{{
            "mtu": 9000,
            "name": "ens25f0",
            "type": "interface",
            "use_dhcp": false
        }}, {{
            "addresses": [{{
                    "ip_netmask": "{}"
                }}
            ],
            "mtu": 9000,
            "name": {},
            "type": "interface",
            "use_dhcp": false
        }}, {{
            "addresses": [{{
                    "ip_netmask": "{}"
                }}
            ],
            "device": "infra-bond",
            "mtu": 9000,
            "type": "{type_}",
            "use_dhcp": false,
            "vlan_id": {}
        }}
    ]}}
    """

    cmd2 = "sudo /sbin/ip -o addr"

    out2 = """2: eth0    inet6 fe80::5054:ff:fe35:96e5/64 scope link \       valid_lft forever preferred_lft forever
    3: eth1    inet 100.73.246.5/26 brd 100.73.246.63 scope global noprefixroute eth1\       valid_lft forever preferred
    3: eth1    inet6 fe80::5054:ff:feee:3cd8/64 scope link \       valid_lft forever preferred_lft forever
    7: br-ctlplane    inet 172.31.0.1/21 brd 172.31.7.255 scope global br-ctlplane\       valid_lft forever preferred
    7: br-ctlplane    inet6 fe80::5054:ff:fe35:96e5/64 scope link \  valid_lft forever preferred_lft forever
    8: vlan94    inet 100.73.246.19/26 brd 100.73.246.63 scope global vlan94\ valid_lft forever preferred_lft forever
    8: vlan94    inet 100.73.246.10/32 brd 100.73.246.63 scope global vlan94\ valid_lft forever preferred_lft forever"""

    scenario_passed = [
        ValidationScenarioParams("passed", {cmd1: CmdOutput(out_format1.format("100.73.246.5/26", '"eth1"',
                                                                               "100.73.246.19/26", 94, type_="vlan")),
                                            cmd2: CmdOutput(out2)},
                                 version=Version.V24,
                                 library_mocks_dict={"gs.get_deployment_type": Mock(return_value=Deployment_type.CBIS)})
    ]

    scenario_failed = [
        ValidationScenarioParams("interface does not exist in active addresses",
                                 {cmd1: CmdOutput(out_format1.format("100.73.246.5/26", '"eth2"', "100.73.246.19/26",
                                                                     94, type_="vlan")),
                                  cmd2: CmdOutput(out2)},
                                 version=Version.V24,
                                 library_mocks_dict={"gs.get_deployment_type": Mock(return_value=Deployment_type.CBIS)}),
        ValidationScenarioParams("interface exist, address is different",
                                 {cmd1: CmdOutput(out_format1.format("100.73.246.5/26", '"eth1"',
                                                                     "100.73.246.19/24", 94, type_="vlan")),
                                  cmd2: CmdOutput(out2)},
                                 version=Version.V24,
                                 library_mocks_dict={"gs.get_deployment_type": Mock(return_value=Deployment_type.CBIS)})
    ]

    scenario_unexpected_system_output = [
        ValidationScenarioParams("type not vlan and no name",
                                 {cmd1: CmdOutput(out_format1.format("100.73.246.5/26", '"eth1"',
                                                                     "100.73.246.19/26", 94, type_="interface")),
                                  cmd2: CmdOutput(out2)},
                                 version=Version.V24,
                                 library_mocks_dict={"gs.get_deployment_type": Mock(return_value=Deployment_type.CBIS)})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_unexpected_system_output(self, scenario_params, tested_object)

    def _init_mocks(self, tested_object):
        tested_object.file_utils.is_file_exist = Mock(side_effect=[False, True])


class TestWhereaboutsConfiguration(ValidationTestBase):
    tested_type = WhereaboutsConfiguration

    def test_has_confluence(self, tested_object):
        # Override the func since this val doesn't have a confluence.
        # pls do not copy it! it's only for old validations that do not have a confluence page.
        warnings.warn("No confluence page")

    @pytest.fixture
    def gather_net_attach_def_configs(self, tested_object):
        cmd_out = """net-attach-def01<split>namespace01<split>{
                        "cniVersion": "0.3.1",
                        "type": "ipvlan",
                        "master": "vlan95",
                        "mode": "l2",
                        "ipam": {
                            "type": "whereabouts",
                            "range": "10.10.10.0/24",
                            "range_start": "10.10.10.40",
                            "range_end": "10.10.10.70"
                        }
                     }<split>net-attach-def02<split>namespace01<split>{
                         "cniVersion": "0.3.1",
                         "type": "ipvlan",
                         "master": "vlan95",
                         "mode": "l2",
                         "ipam": {
                             "type": "whereabouts",
                             "range": "fe80:caa5::/112",
                             "range_start": "fe80:caa5::9",
                             "range_end": "fe80:caa5::25"
                         }
                     }<split>net-attach-def03<split>namespace01<split>{
                         "cniVersion": "0.3.1",
                         "type": "ipvlan",
                         "master": "vlan95",
                         "mode": "l2",
                         "ipam": {
                             "type": "static",
                             "addresses": [
                                 {
                                     "address": "10.100.10.20/24"
                                 }
                             ]
                         }
                     }<split>net-attach-def04<split>namespace02<split>{
                         "cniVersion": "0.3.1",
                         "name": "net-attach-def04",
                         "plugins": [
                             {
                                 "type": "sriov",
                                 "spoofchk": "off",
                                 "trust": "on",
                                 "ipam": {}
                             },
                             {
                                 "type": "tuning",
                                 "promisc": true,
                                 "allmulti": true
                             }
                         ]
                     }<split>net-attach-def05<split>namespace03<split>{
                         "cniVersion": "0.3.0",
                         "name": "different-name-for-testing",
                         "type": "ipvlan",
                         "master": "vlan95",
                         "ipam": {
                             "type": "whereabouts",
                             "range": "55.55.59.50/24",
                             "range_start": "55.55.59.25",
                             "range_end": "55.55.59.198",
                             "exclude": [
                                 "55.55.59.100/30",
                                 "55.55.59.120/30"
                             ]
                         }
                     }<split>net-attach-def06<split>namespace03<split>{
                         "cniVersion": "0.3.0",
                         "plugins": [{
                             "type": "macvlan",
                             "master": "vlan95",
                             "ipam": {
                                 "type": "whereabouts",
                                 "range": "55.55.60.50/24",
                                 "range_start": "55.55.60.25",
                                 "range_end": "55.55.60.30"
                             }
                         },
                         {
                             "type":"tuning",
                             "mac": "c2:11:22:33:44:55",
                             "mtu": 1454
                         }]
                     }<split>"""
        tested_object.get_whereabouts_cmd_output = Mock(return_value=cmd_out)
        return tested_object.gather_net_attach_def_configs()

    def test_gather_net_attach_def_configs(self, tested_object, gather_net_attach_def_configs):
        expected_res = [{'config': {u'master': u'vlan95', u'cniVersion': u'0.3.1', u'type': u'ipvlan', u'mode': u'l2',
                                    u'ipam': {u'range_end': u'10.10.10.70', u'range_start': u'10.10.10.40',
                                              u'range': u'10.10.10.0/24', u'type': u'whereabouts'}},
                         'namespace': 'namespace01', 'name': 'net-attach-def01'},
                        {'config': {u'master': u'vlan95', u'cniVersion': u'0.3.1', u'type': u'ipvlan', u'mode': u'l2',
                                    u'ipam': {u'range_end': u'fe80:caa5::25', u'range_start': u'fe80:caa5::9',
                                              u'range': u'fe80:caa5::/112', u'type': u'whereabouts'}},
                         'namespace': 'namespace01', 'name': 'net-attach-def02'},
                        {'config': {u'master': u'vlan95', u'cniVersion': u'0.3.1', u'type': u'ipvlan', u'mode': u'l2',
                                    u'ipam': {u'type': u'static', u'addresses': [{u'address': u'10.100.10.20/24'}]}},
                         'namespace': 'namespace01', 'name': 'net-attach-def03'},
                        {'config': {u'cniVersion': u'0.3.1', u'name': u'net-attach-def04', u'plugins': [
                            {u'ipam': {}, u'trust': u'on', u'type': u'sriov', u'spoofchk': u'off'},
                            {u'allmulti': True, u'promisc': True, u'type': u'tuning'}]},
                         'namespace': 'namespace02', 'name': 'net-attach-def04'},
                        {'config': {u'master': u'vlan95', u'cniVersion': u'0.3.0', u'type': u'ipvlan',
                                    u'name': u'different-name-for-testing', u'ipam':
                                        {u'range_end': u'55.55.59.198', u'range_start': u'55.55.59.25',
                                         u'range': u'55.55.59.50/24', u'type': u'whereabouts',
                                         u'exclude': [u'55.55.59.100/30', u'55.55.59.120/30']}},
                         'namespace': 'namespace03', 'name': 'net-attach-def05'},
                        {'config': {u'cniVersion': u'0.3.0', u'plugins': [
                            {u'master': u'vlan95', u'type': u'macvlan', u'ipam':
                                {u'range_end': u'55.55.60.30', u'range_start': u'55.55.60.25',
                                 u'range': u'55.55.60.50/24', u'type': u'whereabouts'}},
                            {u'mac': u'c2:11:22:33:44:55', u'type': u'tuning', u'mtu': 1454}]},
                         'namespace': 'namespace03', 'name': 'net-attach-def06'}]
        assert gather_net_attach_def_configs == expected_res

    @pytest.fixture
    def gather_pod_configs(self, tested_object):
        cmd_out = """pod01<split>namespace04<split>[{
                         "name": "calico-network",
                         "ips": [
                             "10.10.153.1"
                         ],
                         "default": true,
                         "dns": {}
                     }]<split>pod02<split>namespace04<split>[{
                         "name": "calico-network",
                         "ips": [
                             "10.10.153.53"
                         ],
                         "default": true,
                         "dns": {}
                     }]<split>pod03<split>namespace01<split>[{
                         "name": "calico-network",
                         "ips": [
                             "10.10.153.61"
                         ],
                         "default": true,
                         "dns": {}
                     },{
                         "name": "net-attach-def02",
                         "interface": "net1",
                         "ips": [
                             "fe80:caa5::f"
                         ],
                         "mac": "b8:83:03:8e:0e:f0",
                         "dns": {}
                     }]<split>pod04<split>namespace01<split>[{
                         "name": "calico-network",
                         "ips": [
                             "10.10.153.28"
                         ],
                         "default": true,
                         "dns": {}
                     },{
                         "name": "net-attach-def02",
                         "interface": "net1",
                         "ips": [
                             "fe80:caa5::11"
                         ],
                         "mac": "b8:83:03:8e:0e:f0",
                         "dns": {}
                     }]<split>pod05<split>namespace01<split>[{
                         "name": "calico-network",
                         "ips": [
                             "10.10.153.18"
                         ],
                         "default": true,
                         "dns": {}
                     },{
                         "name": "net-attach-def02",
                         "interface": "net1",
                         "ips": [
                             "fe80:caa5::a"
                         ],
                         "mac": "b8:83:03:8e:0e:f0",
                         "dns": {}
                     }]<split>pod06<split>namespace01<split>[{
                         "name": "calico-network",
                         "ips": [
                             "10.10.153.50"
                         ],
                         "default": true,
                         "dns": {}
                     },{
                         "name": "namespace01/net-attach-def01",
                         "interface": "net1",
                         "ips": [
                             "10.10.10.41"
                         ],
                         "mac": "b8:83:03:8e:0e:f0",
                         "dns": {}
                     }]<split>pod07<split>namespace01<split>[{
                         "name": "calico-network",
                         "ips": [
                             "10.10.153.31"
                         ],
                         "default": true,
                         "dns": {}
                     },{
                         "name": "namespace01/net-attach-def01",
                         "interface": "net1",
                         "ips": [
                             "10.10.10.49"
                         ],
                         "mac": "b8:83:03:8e:0e:f0",
                         "dns": {}
                     }]<split>pod08<split>namespace01<split>[{
                         "name": "calico-network",
                         "ips": [
                             "10.10.153.32"
                         ],
                         "default": true,
                         "dns": {}
                     },{
                         "name": "namespace01/net-attach-def01",
                         "interface": "net1",
                         "ips": [
                             "10.10.10.48"
                         ],
                         "mac": "b8:83:03:8e:0e:f0",
                         "dns": {}
                     }]<split>pod09<split>namespace03<split>[{
                        "name": "calico-network",
                        "ips": [
                            "10.10.218.79"
                        ],
                        "default": true,
                        "dns": {}
                     },{
                         "name": "different-name-for-testing",
                         "interface": "net1",
                         "ips": [
                             "55.55.59.26"
                         ],
                         "mac": "b8:83:03:8e:5e:90",
                         "dns": {}
                     }]<split>pod10<split>namespace03<split>[{
                         "name": "calico-network",
                         "ips": [
                             "10.10.218.117"
                         ],
                         "default": true,
                         "dns": {}
                     },{
                         "name": "different-name-for-testing",
                         "interface": "net1",
                         "ips": [
                             "55.55.59.25"
                         ],
                         "mac": "b8:83:03:8e:5e:90",
                         "dns": {}
                     }]<split>pod11<split>namespace03<split>[{
                         "name": "calico-network",
                         "ips": [
                             "10.10.153.2"
                         ],
                         "default": true,
                         "dns": {}
                     },{
                         "name": "different-name-for-testing",
                         "interface": "net1",
                         "ips": [
                             "55.55.59.27"
                         ],
                         "mac": "b8:83:03:8e:0e:f0",
                         "dns": {}
                     }]<split>"""
        tested_object.get_whereabouts_cmd_output = Mock(return_value=cmd_out)
        return tested_object.gather_pod_configs()

    def test_gather_pod_configs(self, tested_object, gather_pod_configs):
        expected_res = [{'namespace': 'namespace04', 'name': 'pod01', 'network': [
                            {u'default': True, u'ips': [u'10.10.153.1'], u'name': u'calico-network', u'dns': {}}]},
                        {'namespace': 'namespace04', 'name': 'pod02', 'network': [
                            {u'default': True, u'ips': [u'10.10.153.53'], u'name': u'calico-network', u'dns': {}}]},
                        {'namespace': 'namespace01', 'name': 'pod03', 'network': [
                            {u'default': True, u'ips': [u'10.10.153.61'], u'name': u'calico-network', u'dns': {}},
                            {u'interface': u'net1', u'ips': [u'fe80:caa5::f'], u'mac': u'b8:83:03:8e:0e:f0',
                             u'name': u'net-attach-def02', u'dns': {}}]},
                        {'namespace': 'namespace01', 'name': 'pod04', 'network': [
                            {u'default': True, u'ips': [u'10.10.153.28'], u'name': u'calico-network', u'dns': {}},
                            {u'interface': u'net1', u'ips': [u'fe80:caa5::11'], u'mac': u'b8:83:03:8e:0e:f0',
                             u'name': u'net-attach-def02', u'dns': {}}]},
                        {'namespace': 'namespace01', 'name': 'pod05', 'network': [
                            {u'default': True, u'ips': [u'10.10.153.18'], u'name': u'calico-network', u'dns': {}},
                            {u'interface': u'net1', u'ips': [u'fe80:caa5::a'], u'mac': u'b8:83:03:8e:0e:f0',
                             u'name': u'net-attach-def02', u'dns': {}}]},
                        {'namespace': 'namespace01', 'name': 'pod06', 'network': [
                            {u'default': True, u'ips': [u'10.10.153.50'], u'name': u'calico-network', u'dns': {}},
                            {u'interface': u'net1', u'ips': [u'10.10.10.41'], u'mac': u'b8:83:03:8e:0e:f0',
                             u'name': u'namespace01/net-attach-def01', u'dns': {}}]},
                        {'namespace': 'namespace01', 'name': 'pod07', 'network': [
                            {u'default': True, u'ips': [u'10.10.153.31'], u'name': u'calico-network', u'dns': {}},
                            {u'interface': u'net1', u'ips': [u'10.10.10.49'], u'mac': u'b8:83:03:8e:0e:f0',
                             u'name': u'namespace01/net-attach-def01', u'dns': {}}]},
                        {'namespace': 'namespace01', 'name': 'pod08', 'network': [
                            {u'default': True, u'ips': [u'10.10.153.32'], u'name': u'calico-network', u'dns': {}},
                            {u'interface': u'net1', u'ips': [u'10.10.10.48'], u'mac': u'b8:83:03:8e:0e:f0',
                             u'name': u'namespace01/net-attach-def01', u'dns': {}}]},
                        {'namespace': 'namespace03', 'name': 'pod09', 'network': [
                            {u'default': True, u'ips': [u'10.10.218.79'], u'name': u'calico-network', u'dns': {}},
                            {u'interface': u'net1', u'ips': [u'55.55.59.26'], u'mac': u'b8:83:03:8e:5e:90',
                             u'name': u'different-name-for-testing', u'dns': {}}]},
                        {'namespace': 'namespace03', 'name': 'pod10', 'network': [
                            {u'default': True, u'ips': [u'10.10.218.117'], u'name': u'calico-network', u'dns': {}},
                            {u'interface': u'net1', u'ips': [u'55.55.59.25'], u'mac': u'b8:83:03:8e:5e:90',
                             u'name': u'different-name-for-testing', u'dns': {}}]},
                        {'namespace': 'namespace03', 'name': 'pod11', 'network': [
                            {u'default': True, u'ips': [u'10.10.153.2'], u'name': u'calico-network', u'dns': {}},
                            {u'interface': u'net1', u'ips': [u'55.55.59.27'], u'mac': u'b8:83:03:8e:0e:f0',
                             u'name': u'different-name-for-testing', u'dns': {}}]}]
        assert gather_pod_configs == expected_res

    @pytest.fixture
    def gather_ippool_configs(self, tested_object):
        cmd_out = """10.10.10.0-24<split>kube-system<split>{
                         "allocations": {
                             "41": {
                                 "id": "9bc50c11210e9bfaa8fae799628a020816d4b858a1262560d222e8e8ae35e70d",
                                 "podref": "namespace01/pod06"
                             },
                             "48": {
                                 "id": "e69576b3d774d289d3552cb6d8142afd6ea243a8d8466b910d2847677a7a4ca7",
                                 "podref": "namespace01/pod08"
                             },
                             "49": {
                                 "id": "73c353ce50de516f414ead0204bac1266aa7f6cc47a9e42d16031f58fd73d141",
                                 "podref": "namespace01/pod07"
                             }
                         },
                         "range": "10.10.10.0/24"
                     }<split>fe80-caa5---112<split>kube-system<split>{
                         "allocations": {
                             "10": {
                                 "id": "ad6b8ef6a97624dafe4716df1c5803b980b5d46870badbf1648c81095f89f7f3",
                                 "podref": "namespace01/pod05"
                             },
                             "15": {
                                 "id": "7b3089df5cc57d8c4a63447cc9c8a66f17a4f5c80612f573d428cd80547febbe",
                                 "podref": "namespace01/pod03"
                             },
                             "17": {
                                 "id": "79cbf173f9d9fba852ce943d727e7cf6d2f951adffd71365a9ed707fc8f59bf4",
                                 "podref": "namespace01/pod04"
                             }
                         },
                         "range": "fe80:caa5::/112"
                     }<split>55.55.59.0-24<split>kube-system<split>{
                         "allocations": {
                             "25": {
                                 "id": "a1e7b6f78a114a246113e87acab163f3d7f660db57ee70400b5068a4d9170f33",
                                 "podref": "namespace03/pod10"
                             },
                             "26": {
                                 "id": "6fff11345af9e035f7ee6adeb2f198efab89fc875c4ba1606b4bdd71a6a97f79",
                                 "podref": "namespace03/pod09"
                             },
                             "27": {
                                 "id": "c9e962c55cc485d00d540e68fa01acf6902a0f7b175b544563f3c9285140697c",
                                 "podref": "namespace03/pod11"
                             }
                         },
                         "range": "55.55.59.0/24"
                     }<split>"""
        tested_object.get_whereabouts_cmd_output = Mock(return_value=cmd_out)
        return tested_object.gather_ippool_configs()

    def test_gather_ippool_configs(self, tested_object, gather_ippool_configs):
        expected_res = [{'namespace': 'kube-system', 'name': '10.10.10.0-24', 'spec': {
                            u'range': u'10.10.10.0/24', u'allocations': {
                                u'49': {u'podref': u'namespace01/pod07',
                                        u'id': u'73c353ce50de516f414ead0204bac1266aa7f6cc47a9e42d16031f58fd73d141'},
                                u'48': {u'podref': u'namespace01/pod08',
                                        u'id': u'e69576b3d774d289d3552cb6d8142afd6ea243a8d8466b910d2847677a7a4ca7'},
                                u'41': {u'podref': u'namespace01/pod06',
                                        u'id': u'9bc50c11210e9bfaa8fae799628a020816d4b858a1262560d222e8e8ae35e70d'}}}},
                        {'namespace': 'kube-system', 'name': 'fe80-caa5---112', 'spec': {
                            u'range': u'fe80:caa5::/112', u'allocations': {
                                u'10': {u'podref': u'namespace01/pod05',
                                        u'id': u'ad6b8ef6a97624dafe4716df1c5803b980b5d46870badbf1648c81095f89f7f3'},
                                u'15': {u'podref': u'namespace01/pod03',
                                        u'id': u'7b3089df5cc57d8c4a63447cc9c8a66f17a4f5c80612f573d428cd80547febbe'},
                                u'17': {u'podref': u'namespace01/pod04',
                                        u'id': u'79cbf173f9d9fba852ce943d727e7cf6d2f951adffd71365a9ed707fc8f59bf4'}}}},
                        {'namespace': 'kube-system', 'name': '55.55.59.0-24', 'spec': {
                            u'range': u'55.55.59.0/24', u'allocations': {
                                u'25': {u'podref': u'namespace03/pod10',
                                        u'id': u'a1e7b6f78a114a246113e87acab163f3d7f660db57ee70400b5068a4d9170f33'},
                                u'26': {u'podref': u'namespace03/pod09',
                                        u'id': u'6fff11345af9e035f7ee6adeb2f198efab89fc875c4ba1606b4bdd71a6a97f79'},
                                u'27': {u'podref': u'namespace03/pod11',
                                        u'id': u'c9e962c55cc485d00d540e68fa01acf6902a0f7b175b544563f3c9285140697c'}}}}]
        assert gather_ippool_configs == expected_res

    @pytest.fixture
    def get_net_attach_def_whereabouts_list(self, tested_object, gather_net_attach_def_configs):
        tested_object.gather_net_attach_def_configs = Mock(return_value=gather_net_attach_def_configs)
        return tested_object.get_net_attach_def_whereabouts_list()

    def test_get_net_attach_def_whereabouts_list(self, tested_object, get_net_attach_def_whereabouts_list):
        expected_res = [{'namespace': 'namespace01', 'name': 'net-attach-def01'},
                        {'namespace': 'namespace01', 'name': 'net-attach-def02'},
                        {'namespace': 'namespace03', 'name': 'net-attach-def05'},
                        {'namespace': 'namespace03', 'name': 'different-name-for-testing'},
                        {'namespace': 'namespace03', 'name': 'net-attach-def06'}]
        assert get_net_attach_def_whereabouts_list == expected_res

    @pytest.fixture
    def get_pod_whereabouts_ip_list(self, tested_object, gather_net_attach_def_configs, gather_pod_configs):
        tested_object.gather_pod_configs = Mock(return_value=gather_pod_configs)
        tested_object.gather_net_attach_def_configs = Mock(return_value=gather_net_attach_def_configs)
        return tested_object.get_pod_whereabouts_ip_list()

    def test_get_pod_whereabouts_ip_list(self, tested_object, get_pod_whereabouts_ip_list):
        expected_res = [{'ips': [u'fe80:caa5::f'], 'namespace': 'namespace01', 'name': 'pod03'},
                        {'ips': [u'fe80:caa5::11'], 'namespace': 'namespace01', 'name': 'pod04'},
                        {'ips': [u'fe80:caa5::a'], 'namespace': 'namespace01', 'name': 'pod05'},
                        {'ips': [u'10.10.10.41'], 'namespace': 'namespace01', 'name': 'pod06'},
                        {'ips': [u'10.10.10.49'], 'namespace': 'namespace01', 'name': 'pod07'},
                        {'ips': [u'10.10.10.48'], 'namespace': 'namespace01', 'name': 'pod08'},
                        {'ips': [u'55.55.59.26'], 'namespace': 'namespace03', 'name': 'pod09'},
                        {'ips': [u'55.55.59.25'], 'namespace': 'namespace03', 'name': 'pod10'},
                        {'ips': [u'55.55.59.27'], 'namespace': 'namespace03', 'name': 'pod11'}]
        assert get_pod_whereabouts_ip_list == expected_res

    @pytest.fixture
    def get_ippool_allocation_list(self, tested_object, gather_ippool_configs):
        tested_object.gather_ippool_configs = Mock(return_value=gather_ippool_configs)
        return tested_object.get_ippool_allocation_list()

    def test_get_ippool_allocation_list(self, tested_object, get_ippool_allocation_list):
        expected_res = [{'range': u'10.10.10.0/24', 'name': '10.10.10.0-24', 'allocation_data': {
                            u'podref': u'namespace01/pod07',
                            u'id': u'73c353ce50de516f414ead0204bac1266aa7f6cc47a9e42d16031f58fd73d141'},
                         'allocation_number': u'49'},
                        {'range': u'10.10.10.0/24', 'name': '10.10.10.0-24', 'allocation_data': {
                            u'podref': u'namespace01/pod08',
                            u'id': u'e69576b3d774d289d3552cb6d8142afd6ea243a8d8466b910d2847677a7a4ca7'},
                         'allocation_number': u'48'},
                        {'range': u'10.10.10.0/24', 'name': '10.10.10.0-24', 'allocation_data': {
                            u'podref': u'namespace01/pod06',
                            u'id': u'9bc50c11210e9bfaa8fae799628a020816d4b858a1262560d222e8e8ae35e70d'},
                         'allocation_number': u'41'},
                        {'range': u'fe80:caa5::/112', 'name': 'fe80-caa5---112', 'allocation_data': {
                            u'podref': u'namespace01/pod05',
                            u'id': u'ad6b8ef6a97624dafe4716df1c5803b980b5d46870badbf1648c81095f89f7f3'},
                         'allocation_number': u'10'},
                        {'range': u'fe80:caa5::/112', 'name': 'fe80-caa5---112', 'allocation_data': {
                            u'podref': u'namespace01/pod03',
                            u'id': u'7b3089df5cc57d8c4a63447cc9c8a66f17a4f5c80612f573d428cd80547febbe'},
                         'allocation_number': u'15'},
                        {'range': u'fe80:caa5::/112', 'name': 'fe80-caa5---112', 'allocation_data': {
                            u'podref': u'namespace01/pod04',
                            u'id': u'79cbf173f9d9fba852ce943d727e7cf6d2f951adffd71365a9ed707fc8f59bf4'},
                         'allocation_number': u'17'},
                        {'range': u'55.55.59.0/24', 'name': '55.55.59.0-24', 'allocation_data': {
                            u'podref': u'namespace03/pod10',
                            u'id': u'a1e7b6f78a114a246113e87acab163f3d7f660db57ee70400b5068a4d9170f33'},
                         'allocation_number': u'25'},
                        {'range': u'55.55.59.0/24', 'name': '55.55.59.0-24', 'allocation_data': {
                            u'podref': u'namespace03/pod09',
                            u'id': u'6fff11345af9e035f7ee6adeb2f198efab89fc875c4ba1606b4bdd71a6a97f79'},
                         'allocation_number': u'26'},
                        {'range': u'55.55.59.0/24', 'name': '55.55.59.0-24', 'allocation_data': {
                            u'podref': u'namespace03/pod11',
                            u'id': u'c9e962c55cc485d00d540e68fa01acf6902a0f7b175b544563f3c9285140697c'},
                         'allocation_number': u'27'}]
        for item in get_ippool_allocation_list:
            assert item in expected_res

    class TestWhereaboutsDuplicateIPAddresses(ValidationTestBase):
        tested_type = WhereaboutsDuplicateIPAddresses

        check_duplicate_ips_results_without_duplicates = []
        check_duplicate_ips_results_with_duplicate_ips = \
            ['--> Pod namespace01/pod03 has a duplicate IP 172.30.77.1',
             '--> Pod namespace01/pod05 has a duplicate IP 172.30.77.1',
             '--> Pod namespace01/pod07 has a duplicate IP 172.30.77.1',
             '--> Pod namespace03/pod09 has a duplicate IP 172.30.77.1',
             '--> Pod namespace03/pod11 has a duplicate IP 172.30.77.1']

        @pytest.mark.parametrize("duplicate_ip, expected_res", [
            ([u'172.30.77.1'], check_duplicate_ips_results_with_duplicate_ips),
            (False, check_duplicate_ips_results_without_duplicates)])
        def test_check_duplicate_ips(self, tested_object, duplicate_ip, get_pod_whereabouts_ip_list, expected_res):
            if duplicate_ip:
                for x in range(0, len(get_pod_whereabouts_ip_list), 2):
                    get_pod_whereabouts_ip_list[x]['ips'] = duplicate_ip
            tested_object.get_pod_whereabouts_ip_list = Mock(return_value=get_pod_whereabouts_ip_list)
            assert tested_object.check_duplicate_ips() == expected_res

        scenario_passed = [
            ValidationScenarioParams(scenario_title="No duplicate IP's",
                                     tested_object_mock_dict={"check_duplicate_ips": Mock(
                                         return_value=check_duplicate_ips_results_without_duplicates)})]

        scenario_failed = [
            ValidationScenarioParams(scenario_title="Yes duplicate IP's",
                                     tested_object_mock_dict={"check_duplicate_ips": Mock(
                                         return_value=check_duplicate_ips_results_with_duplicate_ips)})]

        @pytest.mark.parametrize("scenario_params", scenario_passed)
        def test_scenario_passed(self, scenario_params, tested_object):
            ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

        @pytest.mark.parametrize("scenario_params", scenario_failed)
        def test_scenario_failed(self, scenario_params, tested_object):
            ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    class TestWhereaboutsMissingPodrefs(ValidationTestBase):
        tested_type = WhereaboutsMissingPodrefs

        get_missing_podref_ip_list_results_without_missing_podrefs = []
        get_missing_podref_ip_list_results_with_missing_podrefs = \
            [IPv4Address(u'10.10.10.49'), IPv4Address(u'10.10.10.41'), IPv6Address(u'fe80:caa5::f'),
             IPv4Address(u'55.55.59.25'), IPv4Address(u'55.55.59.27')]

        @pytest.mark.parametrize("is_missing_podrefs, expected_res", [
            (True, get_missing_podref_ip_list_results_with_missing_podrefs),
            (False, get_missing_podref_ip_list_results_without_missing_podrefs)])
        def test_get_missing_podref_ip_list(self, tested_object, is_missing_podrefs, get_ippool_allocation_list,
                                            expected_res):
            if is_missing_podrefs:
                for x in range(0, len(get_ippool_allocation_list), 2):
                    del get_ippool_allocation_list[x]['allocation_data']['podref']
            tested_object.get_ippool_allocation_list = Mock(return_value=get_ippool_allocation_list)
            res = tested_object.get_missing_podref_ip_list()

            for ip in expected_res:
                assert ip in res

        check_missing_podrefs_results_without_missing_podrefs = []
        check_missing_podrefs_results_with_missing_podrefs = \
            ['--> Pod namespace01/pod07 has a missing podref for IP 10.10.10.49',
             '--> Pod namespace01/pod06 has a missing podref for IP 10.10.10.41',
             '--> Pod namespace01/pod03 has a missing podref for IP fe80:caa5::f',
             '--> Pod namespace03/pod10 has a missing podref for IP 55.55.59.25',
             '--> Pod namespace03/pod11 has a missing podref for IP 55.55.59.27']

        @pytest.mark.parametrize("is_missing_podrefs, get_missing_podref_ip_list_results, expected_res", [
            (True, get_missing_podref_ip_list_results_with_missing_podrefs,
             check_missing_podrefs_results_with_missing_podrefs),
            (False, get_missing_podref_ip_list_results_without_missing_podrefs,
             check_missing_podrefs_results_without_missing_podrefs)])
        def test_check_missing_podrefs(self, tested_object, is_missing_podrefs, get_missing_podref_ip_list_results,
                                       get_pod_whereabouts_ip_list, expected_res):
            tested_object.get_missing_podref_ip_list = Mock(return_value=get_missing_podref_ip_list_results)
            tested_object.get_pod_whereabouts_ip_list = Mock(return_value=get_pod_whereabouts_ip_list)
            assert tested_object.check_missing_podrefs() == expected_res

        scenario_passed = [
            ValidationScenarioParams(scenario_title="No missing podrefs",
                                     tested_object_mock_dict={"check_missing_podrefs": Mock(
                                         return_value=check_missing_podrefs_results_without_missing_podrefs)})]

        scenario_failed = [
            ValidationScenarioParams(scenario_title="Yes missing podrefs",
                                     tested_object_mock_dict={"check_missing_podrefs": Mock(
                                         return_value=check_missing_podrefs_results_with_missing_podrefs)})]

        @pytest.mark.parametrize("scenario_params", scenario_passed)
        def test_scenario_passed(self, scenario_params, tested_object):
            ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

        @pytest.mark.parametrize("scenario_params", scenario_failed)
        def test_scenario_failed(self, scenario_params, tested_object):
            ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    class TestWhereaboutsMissingAllocations(ValidationTestBase):
        tested_type = WhereaboutsMissingAllocations

        @pytest.fixture
        def get_allocated_ip_list(self, tested_object, gather_ippool_configs):
            tested_object.gather_ippool_configs = Mock(return_value=gather_ippool_configs)
            return tested_object.get_allocated_ip_list()

        def test_get_allocated_ip_list(self, tested_object, get_allocated_ip_list):
            expected_res = [IPv4Address(u'10.10.10.49'), IPv4Address(u'10.10.10.48'), IPv4Address(u'10.10.10.41'),
                            IPv6Address(u'fe80:caa5::a'), IPv6Address(u'fe80:caa5::f'), IPv6Address(u'fe80:caa5::11'),
                            IPv4Address(u'55.55.59.25'), IPv4Address(u'55.55.59.26'), IPv4Address(u'55.55.59.27')]

            for ip in expected_res:
                assert ip in get_allocated_ip_list

        get_missing_ip_allocation_pod_list_results_without_missing_allocations = []
        get_missing_ip_allocation_pod_list_results_with_missing_allocations = \
            [{'ips': [u'fe80:caa5::f'], 'name': 'pod03', 'namespace': 'namespace01'},
             {'ips': [u'10.10.10.41'], 'name': 'pod06', 'namespace': 'namespace01'},
             {'ips': [u'10.10.10.49'], 'name': 'pod07', 'namespace': 'namespace01'},
             {'ips': [u'55.55.59.25'], 'name': 'pod10', 'namespace': 'namespace03'},
             {'ips': [u'55.55.59.27'], 'name': 'pod11', 'namespace': 'namespace03'}]

        @pytest.mark.parametrize("is_missing_allocation, expected_res",
                                 [(True, get_missing_ip_allocation_pod_list_results_with_missing_allocations),
                                  (False, get_missing_ip_allocation_pod_list_results_without_missing_allocations)])
        def test_get_missing_ip_allocation_pod_list(self, tested_object, is_missing_allocation, get_allocated_ip_list,
                                                    get_pod_whereabouts_ip_list, expected_res):
            if is_missing_allocation:
                del get_allocated_ip_list[::2]
            tested_object.get_allocated_ip_list = Mock(return_value=get_allocated_ip_list)
            tested_object.get_pod_whereabouts_ip_list = Mock(return_value=get_pod_whereabouts_ip_list)
            assert tested_object.get_missing_ip_allocation_pod_list() == expected_res

        check_missing_ippool_allocations_results_without_missing_allocations = []
        check_missing_ippool_allocations_results_with_missing_allocations = [
            '--> Pod namespace01/pod03 has a missing IP allocation for IP fe80:caa5::f',
            '--> Pod namespace01/pod06 has a missing IP allocation for IP 10.10.10.41',
            '--> Pod namespace01/pod07 has a missing IP allocation for IP 10.10.10.49',
            '--> Pod namespace03/pod10 has a missing IP allocation for IP 55.55.59.25',
            '--> Pod namespace03/pod11 has a missing IP allocation for IP 55.55.59.27']

        @pytest.mark.parametrize("is_missing_allocations, get_missing_ip_allocation_pod_list_results, expected_res",
                                 [(True, get_missing_ip_allocation_pod_list_results_with_missing_allocations,
                                   check_missing_ippool_allocations_results_with_missing_allocations),
                                  (False, get_missing_ip_allocation_pod_list_results_without_missing_allocations,
                                   check_missing_ippool_allocations_results_without_missing_allocations)])
        def test_check_missing_ippool_allocations(self, tested_object, is_missing_allocations,
                                                  get_missing_ip_allocation_pod_list_results, expected_res):
            tested_object.get_missing_ip_allocation_pod_list = \
                Mock(return_value=get_missing_ip_allocation_pod_list_results)
            assert tested_object.check_missing_ippool_allocations() == expected_res

        scenario_passed = [
            ValidationScenarioParams(
                scenario_title="No missing ippool allocations",
                tested_object_mock_dict={"check_missing_ippool_allocations": Mock(
                    return_value=check_missing_ippool_allocations_results_without_missing_allocations)})]

        scenario_failed = [
            ValidationScenarioParams(
                scenario_title="Yes missing ippool allocations",
                tested_object_mock_dict={"check_missing_ippool_allocations": Mock(
                    return_value=check_missing_ippool_allocations_results_with_missing_allocations)})]

        @pytest.mark.parametrize("scenario_params", scenario_passed)
        def test_scenario_passed(self, scenario_params, tested_object):
            ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

        @pytest.mark.parametrize("scenario_params", scenario_failed)
        def test_scenario_failed(self, scenario_params, tested_object):
            ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    class TestWhereaboutsExistingAllocations(ValidationTestBase):
        tested_type = WhereaboutsExistingAllocations

        verify_existing_ip_allocations_without_incorrect_allocations = []
        verify_existing_ip_allocations_with_incorrect_allocations = \
            ['--> Allocation in ippool 10.10.10.0-24 with allocation number 49 does not match the pod listed in its '
             'podref: namespace01/wrong-pod-name',
             '--> Allocation in ippool 10.10.10.0-24 with allocation number 41 does not match the pod listed in its '
             'podref: namespace01/wrong-pod-name',
             '--> Allocation in ippool fe80-caa5---112 with allocation number 7 does not match the pod listed in its '
             'podref: namespace01/pod03',
             '--> Allocation in ippool 55.55.59.0-24 with allocation number 7 does not match the pod listed in its '
             'podref: namespace03/pod10',
             '--> Allocation in ippool 55.55.59.0-24 with allocation number 7 does not match the pod listed in its '
             'podref: namespace03/pod11']

        @pytest.mark.parametrize("has_incorrect_allocation, expected_res",
                                 [(True, verify_existing_ip_allocations_with_incorrect_allocations),
                                  (False, verify_existing_ip_allocations_without_incorrect_allocations)])
        def test_verify_existing_ip_allocations(self, tested_object, has_incorrect_allocation,
                                                get_pod_whereabouts_ip_list, get_ippool_allocation_list, expected_res):
            if has_incorrect_allocation:
                incorrect_podref = u'namespace01/wrong-pod-name'
                for x in range(0, 3, 2):
                    get_ippool_allocation_list[x]['allocation_data']['podref'] = incorrect_podref
                incorrect_allocation_number = u'7'
                for x in range(4, len(get_ippool_allocation_list), 2):
                    get_ippool_allocation_list[x]['allocation_number'] = incorrect_allocation_number
            tested_object.get_pod_whereabouts_ip_list = Mock(return_value=get_pod_whereabouts_ip_list)
            tested_object.get_ippool_allocation_list = Mock(return_value=get_ippool_allocation_list)

            for line in tested_object.verify_existing_ip_allocations():
                assert line in expected_res

        scenario_passed = [
            ValidationScenarioParams(
                scenario_title="No incorrect ippool allocations",
                tested_object_mock_dict={"verify_existing_ip_allocations": Mock(
                    return_value=verify_existing_ip_allocations_without_incorrect_allocations)})]

        scenario_failed = [
            ValidationScenarioParams(
                scenario_title="Yes incorrect ippool allocations",
                tested_object_mock_dict={"verify_existing_ip_allocations": Mock(
                        return_value=verify_existing_ip_allocations_with_incorrect_allocations)})]

        @pytest.mark.parametrize("scenario_params", scenario_passed)
        def test_scenario_passed(self, scenario_params, tested_object):
            ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

        @pytest.mark.parametrize("scenario_params", scenario_failed)
        def test_scenario_failed(self, scenario_params, tested_object):
            ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestNoDynamicAddressInIptables(ValidationTestBase):
    tested_type = NoDynamicAddressInIptables

    scenario_passed = [
        ValidationScenarioParams(scenario_title="No iptables files exist",
                                 additional_parameters_dict={"file_exist": [False, False],  "cmd_out": 'NA'}),
        ValidationScenarioParams(scenario_title="Iptables file 1 exists and there are no dynamic IP rules detected",
                                 additional_parameters_dict={"file_exist": [True, False],
                                                             "cmd_out": [(1, 'output_NA', 'error_NA'),
                                                                         (1, 'output_NA', 'error_NA')]}),
        ValidationScenarioParams(scenario_title="Iptables file 2 exists and there are no dynamic IP rules detected",
                                 additional_parameters_dict={"file_exist": [False, True],
                                                             "cmd_out": [(1, 'output_NA', 'error_NA'),
                                                                         (1, 'output_NA', 'error_NA')]})]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="Iptables file 1 exists and there are are dynamic IP rules detected",
                                 additional_parameters_dict={"file_exist": [True, False],
                                                             "cmd_out": [(0, 'output_NA', 'error_NA'),
                                                                         (1, 'output_NA', 'error_NA')]}),
        ValidationScenarioParams(scenario_title="Iptables file 2 exists and there are are dynamic IP rules detected",
                                 additional_parameters_dict={"file_exist": [False, True],
                                                             "cmd_out": [(1, 'output_NA', 'error_NA'),
                                                                         (0, 'output_NA', 'error_NA')]})]

    def _init_mocks(self, tested_object):
        tested_object.file_utils.is_file_exist = Mock()
        tested_object.file_utils.is_file_exist.side_effect = self.additional_parameters_dict['file_exist']
        tested_object.run_cmd = Mock()
        tested_object.run_cmd.side_effect = self.additional_parameters_dict['cmd_out']

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestGetMultusNodes(DataCollectorTestBase):
    tested_type = GetMultusNodes

    multus_nodes_raw = """fi803-bm-edgebm-0     Ready   <none>   11d   v1.19.5
                          fi803-bm-edgebm-1     Ready   <none>   11d   v1.19.5
                          fi803-bm-edgebm-2     Ready   <none>   11d   v1.19.5
                          fi803-bm-workerbm-0   Ready   <none>   11d   v1.19.5
                          fi803-bm-workerbm-1   Ready   <none>   11d   v1.19.5
                          fi803-bm-workerbm-2   Ready   <none>   11d   v1.19.5"""

    multus_nodes = ['fi803-bm-edgebm-0', 'fi803-bm-edgebm-1', 'fi803-bm-edgebm-2', 'fi803-bm-workerbm-0',
                    'fi803-bm-workerbm-1', 'fi803-bm-workerbm-2']

    scenarios = [
        DataCollectorScenarioParams(
            "with multus nodes",
            {"sudo /usr/local/bin/kubectl get nodes -l=ncs.nokia.com/multus_node=true --no-headers": CmdOutput(
                multus_nodes_raw)},
            scenario_res=multus_nodes
        ),
        DataCollectorScenarioParams(
            "no multus nodes",
            {"sudo /usr/local/bin/kubectl get nodes -l=ncs.nokia.com/multus_node=true --no-headers": CmdOutput("")},
            scenario_res=[]
        )
    ]

    @pytest.mark.parametrize("scenario_params", scenarios)
    def test_collect_data(self, scenario_params, tested_object):
        DataCollectorTestBase.test_collect_data(self, scenario_params, tested_object)


class TestCalicoIpamBlockStatus(ValidationTestBase):
    tested_type = CalicoIpamBlockStatus

    cmd = 'sudo /usr/local/sbin/calicoctl ipam show --show-blocks'
    out_good = """
    +----------+-------------------+-----------+------------+-----------+.
        | GROUPING |       CIDR        | IPS TOTAL | IPS IN USE | IPS FREE  |.
        +----------+-------------------+-----------+------------+-----------+.
        | IP Pool  | 192.168.70.0/24   |       256 | 68 (27%)   | 188 (73%) |.
        | Block    | 192.168.70.0/26   |        64 | 19 (30%)   | 45 (70%)  |.
        | Block    | 192.168.70.128/26 |        64 | 16 (25%)   | 48 (75%)  |.
        | Block    | 192.168.70.192/26 |        64 | 9 (14%)    | 55 (86%)  |.
        | Block    | 192.168.70.64/26  |        64 | 24 (38%)   | 40 (62%)  |.
        +----------+-------------------+-----------+------------+-----------+.    
    """

    out_bad = """
    +----------+-------------------+-----------+------------+-----------+.
        | GROUPING |       CIDR        | IPS TOTAL | IPS IN USE | IPS FREE  |.
        +----------+-------------------+-----------+------------+-----------+.
        | IP Pool  | 192.168.70.0/24   |       256 | 68 (27%)   | 188 (73%) |.
        | Block    | 192.168.70.0/26   |        64 | 52 (81%)   | 12 (19%)  |.
        | Block    | 192.168.70.128/26 |        64 | 16 (25%)   | 48 (75%)  |.
        | Block    | 192.168.70.192/26 |        64 | 9 (14%)    | 55 (86%)  |.
        | Block    | 192.168.70.64/26  |        64 | 24 (38%)   | 40 (62%)  |.
        +----------+-------------------+-----------+------------+-----------+.    
    """


    scenario_passed = [
        ValidationScenarioParams("no failures",
                                 cmd_input_output_dict={
                                     cmd: CmdOutput(out_good)
                                 })
    ]

    scenario_failed = [
        ValidationScenarioParams("failures",
                                 cmd_input_output_dict={
                                     cmd: CmdOutput(out_bad)
                                 })
    ]

    @ pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

class TestCalicoKubernetesAlignNodes(ValidationTestBase):
    tested_type = CalicoKubernetesAlignNodes

    validation_cmd = 'sudo ETCDCTL_API=3 bash -c "etcdctl get /calico/resources/v3/projectcalico.org/nodes/ --prefix \
--keys-only --endpoints=$(sudo cat /etc/etcd/etcd_endpoints.yml|cut -d\' \' -f2|tr -d \'"\') --cacert=/etc/etcd/ssl/ca.pem --cert=/etc/etcd/ssl/etcd-client.pem \
--key=/etc/etcd/ssl/etcd-client-key.pem| awk NF"'
    validation_cmd2 = "sudo kubectl get nodes"

    out = """
/calico/resources/v3/projectcalico.org/nodes/fin-767-edgebm-{}
/calico/resources/v3/projectcalico.org/nodes/fin-767-edgebm-{}
/calico/resources/v3/projectcalico.org/nodes/fin-767-edgebm-{}
"""

    out2 = """
NAME                  STATUS   ROLES    AGE    VERSION
fin-767-edgebm-{}      Ready    <none>   162d   v1.21.12
fin-767-edgebm-{}      Ready    <none>   162d   v1.21.12
fin-767-edgebm-{}      Ready    <none>   162d   v1.21.12
"""

    scenario_passed = [
        ValidationScenarioParams(scenario_title="Same output, same order",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out.format('0', '1', '2')),
                                                        validation_cmd2: CmdOutput(out2.format('0', '1', '2'))}),

        ValidationScenarioParams(scenario_title="Same output, different order",
                        cmd_input_output_dict={validation_cmd: CmdOutput(out.format('0', '1', '2')),
                                               validation_cmd2: CmdOutput(out2.format('1', '2', '0'))})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="Different output",
                             cmd_input_output_dict={validation_cmd: CmdOutput(out.format('0', '1', '2')),
                                                    validation_cmd2: CmdOutput(out2.format('1', '5', '2'))})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    def test_has_confluence(self, tested_object):
        # Override the func since this val doesn't have a confluence.
        # pls do not copy it! it's only for old validations that do not have a confluence page.
        warnings.warn("No confluence page")


class TestValidateUcControlPlaneIpEtcHosts(ValidationTestBase):
    tested_type = ValidateUcControlPlaneIpEtcHosts

    scenario_passed = [
        ValidationScenarioParams(scenario_title="Correct - IPv4 - Correct IP",
                                 tested_object_mock_dict={
                                     "_get_etc_hosts_entries": Mock(return_value=[
                                         "172.31.0.1 undercloud.ctlplane.localdomain undercloud.ctlplane"]),
                                     "_get_control_plane_ip": Mock(return_value="172.31.0.1"),
                                 }),
        ValidationScenarioParams(scenario_title="Correct - IPv4 - 2 entries",
                                 tested_object_mock_dict={
                                     "_get_etc_hosts_entries": Mock(return_value=[
                                         "172.31.0.1 undercloud.ctlplane.localdomain undercloud.ctlplane",
                                         "172.31.0.1 undercloud.ctlplane.localdomain undercloud.ctlplane"]),
                                     "_get_control_plane_ip": Mock(return_value="172.31.0.1"),
                                 }),
        ValidationScenarioParams(scenario_title="Correct - No entries",
                                 tested_object_mock_dict={
                                     "_get_etc_hosts_entries": Mock(return_value=[]),
                                     "_get_control_plane_ip": Mock(return_value="172.31.0.1"),
                                 }),
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="Incorrect - IPv4 - 127.0.0.1",
                                 tested_object_mock_dict={
                                     "_get_etc_hosts_entries": Mock(return_value=[
                                         "127.0.0.1 undercloud.ctlplane.localdomain undercloud.ctlplane"]),
                                     "_get_control_plane_ip": Mock(return_value="172.31.0.1"),
                                 }),
        ValidationScenarioParams(scenario_title="Incorrect - IPv4 - 1.1.1.1",
                                 tested_object_mock_dict={
                                     "_get_etc_hosts_entries": Mock(return_value=[
                                         "1.1.1.1 undercloud.ctlplane.localdomain undercloud.ctlplane"]),
                                     "_get_control_plane_ip": Mock(return_value="172.31.0.1"),
                                 }),
        ValidationScenarioParams(scenario_title="Incorrect - IPv4 - 2 entries - 1.1.1.1",
                                 tested_object_mock_dict={
                                     "_get_etc_hosts_entries": Mock(return_value=[
                                         "172.31.0.1 undercloud.ctlplane.localdomain undercloud.ctlplane",
                                         "1.1.1.1    undercloud.ctlplane.localdomain undercloud.ctlplane"]),
                                     "_get_control_plane_ip": Mock(return_value="172.31.0.1"),
                                 }),
        ValidationScenarioParams(scenario_title="Incorrect - IPv6 - ::1",
                                 tested_object_mock_dict={
                                     "_get_etc_hosts_entries": Mock(return_value=[
                                         "::1 undercloud.ctlplane.localdomain undercloud.ctlplane"]),
                                     "_get_control_plane_ip": Mock(return_value="172.31.0.1"),
                                 }),
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestCheckIptablesForManuallyAddedRules(ValidationTestBase):
    tested_type = CheckIptablesForManuallyAddedRules

    ncs_cnb_get_deployment_type_mock = Mock()
    ncs_cnb_get_deployment_type_mock.return_value = Deployment_type.NCS_OVER_BM
    ncs_cna_get_deployment_type_mock = Mock()
    ncs_cna_get_deployment_type_mock.return_value = Deployment_type.NCS_OVER_OPENSTACK
    control_node_get_host_roles_mock = Mock()
    control_node_get_host_roles_mock.return_value = [Objectives.MASTERS]
    edge_node_get_host_roles_mock = Mock()
    edge_node_get_host_roles_mock.return_value = [Objectives.EDGES]

    cnb_control_node_cmd = (tested_type.base_command + tested_type.cnb_base_add + tested_type.cnb_control_add +
                            tested_type.default_aim_ports_control_add)
    cna_edge_node_cmd = tested_type.base_command + tested_type.default_aim_ports_add

    cnb_control_node_pass_out = ('-A INPUT -m state --state RELATED,ESTABLISHED -j ACCEPT\n-A INPUT -m conntrack '
                                 '--ctstate INVALID -j DROP\n-A FORWARD -o br-d7eafa45d288 -m conntrack --ctstate '
                                 'RELATED,ESTABLISHED -j ACCEPT\n-A FORWARD -i br-d7eafa45d288 ! -o br-d7eafa45d288 -j '
                                 'ACCEPT\n-A FORWARD -i br-d7eafa45d288 -o br-d7eafa45d288 -j ACCEPT\n-A POSTROUTING '
                                 '-o br-d7eafa45d288 -m addrtype --src-type LOCAL -j MASQUERADE\n-A POSTROUTING -s '
                                 '172.18.0.0/16 ! -o br-d7eafa45d288 -j MASQUERADE\n')

    cna_edge_node_pass_out = ('-A POSTROUTING -o vlan105 -j SNAT --to-source 10.11.172.40\n-A POSTROUTING -o vlan105 '
                              '-j SNAT --to-source 10.11.172.58\n-A POSTROUTING -o vlan105 -j SNAT --to-source '
                              '10.11.172.57\n-A POSTROUTING -o vlan105 -j SNAT --to-source 10.11.172.56\n-A '
                              'POSTROUTING -o vlan105 -j SNAT --to-source 10.11.172.60\n-A POSTROUTING -o vlan105 -j '
                              'SNAT --to-source 10.11.172.62\n')

    cnb_control_node_fail_out = '-A POSTROUTING -o vlan105 -j SNAT --to-source 10.11.172.40\n'

    cna_edge_node_fail_out = '-A INPUT -p tcp -m tcp --dport 55555 -j ACCEPT\n'

    scenario_passed = [
        ValidationScenarioParams(scenario_title="CNB control node - cmd has output but is correctly filtered out",
                                 cmd_input_output_dict={cnb_control_node_cmd: CmdOutput(cnb_control_node_pass_out)},
                                 library_mocks_dict={"sys_param.get_deployment_type": ncs_cnb_get_deployment_type_mock},
                                 tested_object_mock_dict={"get_host_roles": control_node_get_host_roles_mock}),
        ValidationScenarioParams(scenario_title="CNB control node - cmd has no output, automatic pass",
                                 cmd_input_output_dict={cnb_control_node_cmd: CmdOutput('')},
                                 library_mocks_dict={"sys_param.get_deployment_type": ncs_cnb_get_deployment_type_mock},
                                 tested_object_mock_dict={"get_host_roles": control_node_get_host_roles_mock}),
        ValidationScenarioParams(scenario_title="CNA edge node - cmd has output but is correctly filtered out",
                                 cmd_input_output_dict={cna_edge_node_cmd: CmdOutput(cna_edge_node_pass_out)},
                                 library_mocks_dict={"sys_param.get_deployment_type": ncs_cna_get_deployment_type_mock},
                                 tested_object_mock_dict={"get_host_roles": edge_node_get_host_roles_mock})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="CNB control node - manually added snat rule",
                                 cmd_input_output_dict={cnb_control_node_cmd: CmdOutput(cnb_control_node_fail_out)},
                                 library_mocks_dict={"sys_param.get_deployment_type": ncs_cnb_get_deployment_type_mock},
                                 tested_object_mock_dict={"get_host_roles": control_node_get_host_roles_mock}),
        ValidationScenarioParams(scenario_title="CNA edge node - manually added open port",
                                 cmd_input_output_dict={cna_edge_node_cmd: CmdOutput(cna_edge_node_fail_out)},
                                 library_mocks_dict={"sys_param.get_deployment_type": ncs_cna_get_deployment_type_mock},
                                 tested_object_mock_dict={"get_host_roles": edge_node_get_host_roles_mock})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestValidateSelinuxContextDirIstio(ValidationTestBase):
    tested_type = ValidateSelinuxContextDirIstio

    version_mocks = [Mock(), Mock()]
    version_mocks[0].return_value, version_mocks[1].return_value = Version.V22_12, Version.V23_10

    scenario_passed = [
        ValidationScenarioParams(scenario_title="Correct - usr_t type",
                                 library_mocks_dict={"sys_parameters.get_version": version_mocks[0]},
                                 tested_object_mock_dict={
                                     "_is_istio_used": Mock(return_value=True),
                                     "_get_selinux_context_line": Mock(return_value= "unconfined_u:object_r:usr_t:s0   bin"),
                                     "_filter_allow_rule": Mock(return_value=[])
                                 },
                                 additional_parameters_dict={'operating_system': 'Red Hat Enterprise Linux 8.8 (Ootpa)'}),
        ValidationScenarioParams(scenario_title="Correct - bin_t type with correct permission",
                                 library_mocks_dict={"sys_parameters.get_version": version_mocks[0]},
                                 tested_object_mock_dict={
                                     "_is_istio_used": Mock(return_value=True),
                                     "_get_selinux_context_line": Mock(return_value="unconfined_u:object_r:bin_t:s0   bin"),
                                     "_filter_allow_rule":
                                         Mock(return_value=
                                              ["(allow container_t bin_t (file (create rename setattr unlink write)))"])
                                 },
                                 additional_parameters_dict={'operating_system': 'CentOS Linux 7 (Core)'}),
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="Incorrect - bin_t type with incorrect permission",
                                 library_mocks_dict={"sys_parameters.get_version": version_mocks[1]},
                                 tested_object_mock_dict={
                                     "_is_istio_used": Mock(return_value=True),
                                     "_get_selinux_context_line":
                                         Mock(return_value="unconfined_u:object_r:bin_t:s0   bin"),
                                     "_filter_allow_rule": Mock(return_value=[]),
                                 },
                                 additional_parameters_dict={'operating_system': 'CentOS Linux 7 (Core)'})
    ]

    scenario_prerequisite_not_fulfilled = [
        ValidationScenarioParams(scenario_title="Prerequisite not fulfilled",
                                 library_mocks_dict={"_is_istio_used": Mock(return_value=False)},
                                 additional_parameters_dict={'operating_system': 'CentOS Linux 7 (Core)'})
    ]

    scenario_unexpected_system_output = [
        ValidationScenarioParams(scenario_title="Unexpected system output - wrong ls of selinux conext",
                                 tested_object_mock_dict={
                                     "_is_istio_used": Mock(return_value=True),
                                     "_get_selinux_context_line": Mock(return_value="bin"),
                                 },
                                 additional_parameters_dict={'operating_system': 'CentOS Linux 7 (Core)'}),
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    def _init_mocks(self, tested_object):
        tested_object.system_utils.get_operating_system_type = Mock()
        tested_object.system_utils.get_operating_system_type.return_value = self.additional_parameters_dict['operating_system']

    @pytest.mark.parametrize("scenario_params", scenario_prerequisite_not_fulfilled)
    def test_prerequisite_not_fulfilled(self, scenario_params, tested_object):
        ValidationTestBase.test_prerequisite_not_fulfilled(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_unexpected_system_output(self, scenario_params, tested_object)


class TestVerifyMellanoxVFNumber(ValidationTestBase):
    tested_type = VerifyMellanoxVFNumber
    get_base_conf_mock = {
        'hosts': {
            'sriov-enabled-workerbm-0': {
                'hieradata': {
                    'my_host_group': {
                        'cbis::my_host_group::interface_mapping::caas_sriov_mapping': [
                            {
                                "num_of_vfs": 10,
                                "port": "ens3f0"
                            },
                            {
                                "num_of_vfs": 10,
                                "port": "ens3f1"
                            }
                        ]
                    }
                }
            },
            'sriov-disabled-workerbm-0': {
                'hieradata': {
                    'my_host_group': {
                        'cbis::my_host_group::interface_mapping::caas_sriov_mapping': [
                            {
                                "num_of_vfs": 0,
                                "port": "ens3f0"
                            },
                            {
                                "num_of_vfs": 0,
                                "port": "ens3f1"
                            }
                        ]
                    }
                }
            }
        }
    }
    lspci_out_without_mellanox = """
    02:00.0 Ethernet controller: Broadcom Inc. and subsidiaries NetXtreme BCM5719 Gigabit Ethernet PCIe (rev 01)
    02:00.1 Ethernet controller: Broadcom Inc. and subsidiaries NetXtreme BCM5719 Gigabit Ethernet PCIe (rev 01)
    02:00.2 Ethernet controller: Broadcom Inc. and subsidiaries NetXtreme BCM5719 Gigabit Ethernet PCIe (rev 01)
    02:00.3 Ethernet controller: Broadcom Inc. and subsidiaries NetXtreme BCM5719 Gigabit Ethernet PCIe (rev 01)
    """
    lspci_out_with_mellanox = lspci_out_without_mellanox + """
    12:00.0 Ethernet controller: Mellanox Technologies MT27800 Family [ConnectX-5]
    12:00.1 Ethernet controller: Mellanox Technologies MT27800 Family [ConnectX-5]
    d8:00.0 Ethernet controller: Mellanox Technologies MT27800 Family [ConnectX-5]
    d8:00.1 Ethernet controller: Mellanox Technologies MT27800 Family [ConnectX-5]
    """

    scenario_passed = [
        ValidationScenarioParams(scenario_title="No Mellanox NIC",
                                 cmd_input_output_dict={
                                     '/sbin/lspci | grep Ethernet': CmdOutput(lspci_out_without_mellanox),
                                     '/usr/bin/hostname': CmdOutput('sriov-enabled-workerbm-0'),
                                     '/usr/bin/cat /sys/class/net/ens3f0/device/sriov_totalvfs': CmdOutput('10'),
                                     '/usr/bin/cat /sys/class/net/ens3f1/device/sriov_totalvfs': CmdOutput('10'),
                                     '/usr/bin/cat /sys/class/net/ens3f0/device/sriov_numvfs': CmdOutput('10'),
                                     '/usr/bin/cat /sys/class/net/ens3f1/device/sriov_numvfs': CmdOutput('10')},
                                 library_mocks_dict={"sys_param.get_base_conf": Mock(return_value=get_base_conf_mock)}),
        ValidationScenarioParams(scenario_title="SRIOV is not enabled",
                                 cmd_input_output_dict={
                                     '/sbin/lspci | grep Ethernet': CmdOutput(lspci_out_with_mellanox),
                                     '/usr/bin/hostname': CmdOutput('sriov-disabled-workerbm-0'),
                                     '/usr/bin/cat /sys/class/net/ens3f0/device/sriov_totalvfs': CmdOutput('0'),
                                     '/usr/bin/cat /sys/class/net/ens3f1/device/sriov_totalvfs': CmdOutput('0'),
                                     '/usr/bin/cat /sys/class/net/ens3f0/device/sriov_numvfs': CmdOutput('0'),
                                     '/usr/bin/cat /sys/class/net/ens3f1/device/sriov_numvfs': CmdOutput('0')},
                                 library_mocks_dict={"sys_param.get_base_conf": Mock(return_value=get_base_conf_mock)}),
        ValidationScenarioParams(scenario_title="sriov_totalvfs equals vfs configured at hostgroup level",
                                 cmd_input_output_dict={
                                     '/sbin/lspci | grep Ethernet': CmdOutput(lspci_out_with_mellanox),
                                     '/usr/bin/hostname': CmdOutput('sriov-enabled-workerbm-0'),
                                     '/usr/bin/cat /sys/class/net/ens3f0/device/sriov_totalvfs': CmdOutput('10'),
                                     '/usr/bin/cat /sys/class/net/ens3f1/device/sriov_totalvfs': CmdOutput('10'),
                                     '/usr/bin/cat /sys/class/net/ens3f0/device/sriov_numvfs': CmdOutput('10'),
                                     '/usr/bin/cat /sys/class/net/ens3f1/device/sriov_numvfs': CmdOutput('10')},
                                 library_mocks_dict={"sys_param.get_base_conf": Mock(return_value=get_base_conf_mock)})
    ]
    scenario_failed = [
        ValidationScenarioParams(scenario_title="sriov_totalvfs are less than hostgroup config and 0 are active",
                                 cmd_input_output_dict={
                                     '/sbin/lspci | grep Ethernet': CmdOutput(lspci_out_with_mellanox),
                                     '/usr/bin/hostname': CmdOutput('sriov-enabled-workerbm-0'),
                                     '/usr/bin/cat /sys/class/net/ens3f0/device/sriov_totalvfs': CmdOutput('8'),
                                     '/usr/bin/cat /sys/class/net/ens3f1/device/sriov_totalvfs': CmdOutput('8'),
                                     '/usr/bin/cat /sys/class/net/ens3f0/device/sriov_numvfs': CmdOutput('0'),
                                     '/usr/bin/cat /sys/class/net/ens3f1/device/sriov_numvfs': CmdOutput('0')},
                                 library_mocks_dict={"sys_param.get_base_conf": Mock(return_value=get_base_conf_mock)}),
        ValidationScenarioParams(scenario_title="sriov_totalvfs are more than hostgroup config",
                                 cmd_input_output_dict={
                                     '/sbin/lspci | grep Ethernet': CmdOutput(lspci_out_with_mellanox),
                                     '/usr/bin/hostname': CmdOutput('sriov-enabled-workerbm-0'),
                                     '/usr/bin/cat /sys/class/net/ens3f0/device/sriov_totalvfs': CmdOutput('15'),
                                     '/usr/bin/cat /sys/class/net/ens3f1/device/sriov_totalvfs': CmdOutput('15'),
                                     '/usr/bin/cat /sys/class/net/ens3f0/device/sriov_numvfs': CmdOutput('10'),
                                     '/usr/bin/cat /sys/class/net/ens3f1/device/sriov_numvfs': CmdOutput('10')},
                                 library_mocks_dict={"sys_param.get_base_conf": Mock(return_value=get_base_conf_mock)})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestValidateCorrectNetconfig(ValidationTestBase):
    tested_type = ValidateCorrectNetconfig

    cmd = "sudo os-net-config --noop --detailed-exit-codes -c /etc/os-net-config/config.json 2>/dev/null"

    out_failed = """File: /etc/sysconfig/network-scripts/ifcfg-vlan97

# This file is autogenerated by os-net-config
DEVICE=vlan97
ONBOOT=yes
HOTPLUG=no
NM_CONTROLLED=no
PEERDNS=no
VLAN=yes
PHYSDEV=infra-bond
MTU=9000
BOOTPROTO=static
IPADDR=172.17.3.68
NETMASK=255.255.255.192

----
File: /etc/sysconfig/network-scripts/ifcfg-vlan96

# This file is autogenerated by os-net-config
DEVICE=vlan96
ONBOOT=yes
HOTPLUG=no
NM_CONTROLLED=no
PEERDNS=no
VLAN=yes
PHYSDEV=infra-bond
MTU=9000
BOOTPROTO=static
IPADDR=172.17.5.68
NETMASK=255.255.255.192

----
File: /etc/sysconfig/network-scripts/ifcfg-vlan94

# This file is autogenerated by os-net-config
DEVICE=vlan94
ONBOOT=yes
HOTPLUG=no
NM_CONTROLLED=no
PEERDNS=no
VLAN=yes
PHYSDEV=infra-bond
MTU=9000
BOOTPROTO=static
IPADDR=100.78.69.13
NETMASK=255.255.255.240

"""
    scenario_passed = [
        ValidationScenarioParams("exit code 0", cmd_input_output_dict={cmd: CmdOutput("")})
    ]

    scenario_failed = [
        ValidationScenarioParams("exit code 2", cmd_input_output_dict={cmd: CmdOutput(out_failed, 2)},
                                 failed_msg="Bad configuration for files: /etc/sysconfig/network-scripts/ifcfg-vlan97\n"
                                            "/etc/sysconfig/network-scripts/ifcfg-vlan96\n"
                                            "/etc/sysconfig/network-scripts/ifcfg-vlan94\n"
                                            "Please do not run Post Install Changes for Ingress Networks")
    ]

    scenario_unexpected_system_output = [
        ValidationScenarioParams("exit code 3", cmd_input_output_dict={cmd: CmdOutput("", 3)}),
        ValidationScenarioParams("exit code 2, no file in out", cmd_input_output_dict={cmd: CmdOutput("", 2)})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_unexpected_system_output(self, scenario_params, tested_object)

class TestValidateStaleStaticRouteConfig(ValidationTestBase):
    tested_type = ValidateStaleStaticRouteConfig

    validation_cmd = "sudo /usr/local/bin/kubectl get staticrouteconfigs --no-headers -A -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,NODE:.spec.node"

    pass_out = """default   defroute-0        fi845a-fi845a-workerbm-0
             default   test-defroute-0   fi845a-fi845a-workerbm-0"""

    empty_out = ""

    fail_out = """default   defroute-0        fi845a-fi845a-workerbm-2
                 default   test-defroute-0   fi845a-fi845a-workerbm-2"""

    mock_node_list = ["fi845a-fi845a-workerbm-0","fi845a-fi845a-workerbm-1"]


    scenario_passed = [ValidationScenarioParams(scenario_title="no stale resource found",
                                                cmd_input_output_dict={validation_cmd: CmdOutput(pass_out)},
                                                tested_object_mock_dict={
                                                    "get_nodes_only": Mock(return_value=mock_node_list)}),
                       ValidationScenarioParams(scenario_title="empty response",
                                                cmd_input_output_dict={validation_cmd: CmdOutput(empty_out)},
                                                tested_object_mock_dict={
                                                    "get_nodes_only": Mock(return_value=mock_node_list)}),
                       ]

    scenario_failed = [ValidationScenarioParams(scenario_title="stale resource found",
                                                cmd_input_output_dict={validation_cmd: CmdOutput(fail_out)},
                                                tested_object_mock_dict={"get_nodes_only": Mock(return_value=mock_node_list)})
                       ]


    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

class TestValidateStaleNextHops(ValidationTestBase):
    tested_type = ValidateStaleNextHops

    validation_cmd = "sudo /usr/local/bin/kubectl get nexthops.ncm.nokia.com --no-headers -A -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,NODE:.spec.node"

    pass_out = """default   defroute-0        fi845a-fi845a-workerbm-0
             default   test-defroute-0   fi845a-fi845a-workerbm-0"""

    empty_out = ""

    fail_out = """default   defroute-0        fi845a-fi845a-workerbm-2
                 default   test-defroute-0   fi845a-fi845a-workerbm-2"""

    mock_node_list = ["fi845a-fi845a-workerbm-0","fi845a-fi845a-workerbm-1"]


    scenario_passed = [ValidationScenarioParams(scenario_title="no stale resource found",
                                                cmd_input_output_dict={validation_cmd: CmdOutput(pass_out)},
                                                tested_object_mock_dict={
                                                    "get_nodes_only": Mock(return_value=mock_node_list)}),
                       ValidationScenarioParams(scenario_title="empty response",
                                                cmd_input_output_dict={validation_cmd: CmdOutput(empty_out)},
                                                tested_object_mock_dict={
                                                    "get_nodes_only": Mock(return_value=mock_node_list)}),
                       ]

    scenario_failed = [ValidationScenarioParams(scenario_title="stale resource found",
                                                cmd_input_output_dict={validation_cmd: CmdOutput(fail_out)},
                                                tested_object_mock_dict={"get_nodes_only": Mock(return_value=mock_node_list)})
                       ]


    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

class TestGetIPDetailsFromControllers(DataCollectorTestBase):
    tested_type = GetIPDetailsFromControllers
    cmd = "sudo ip netns exec qrouter-be6a6d3f-bfdc-4157-89ee-3bb0b5abb4e9aaa hostname -I"
    out = "{'169.254.195.72', '169.254.193.84 169.254.0.11', '169.254.195.233'}"
    scenarios = [
        DataCollectorScenarioParams("get router virtualip in controllers", {cmd: CmdOutput(out)},
                                    scenario_res=out)
    ]

    @pytest.mark.parametrize("scenario_params", scenarios)
    def test_collect_data(self, scenario_params, tested_object):
        DataCollectorTestBase.test_collect_data(self, scenario_params, tested_object, router_id = "be6a6d3f-bfdc-4157-89ee-3bb0b5abb4e9aaa")

class TestVerifyRouterIPActiveStatus(ValidationTestBase):
    tested_type = VerifyRouterIPActiveStatus

    validation_cmd = "source {}; openstack router list  --column ID -f value".format('/home/stack/overcloudrc_locked')
    validation_out = 'be6a6d3f-bfdc-4157-89ee-3bb0b5abb4e9aaa'

    def _init_mocks(self, tested_object):
        tested_object.system_utils.get_overcloudrc_file_path = Mock()
        tested_object.system_utils.get_overcloudrc_file_path.return_value = '/home/stack/overcloudrc_locked'

    scenario_passed = [
        ValidationScenarioParams(scenario_title="virtual router active on one controller",
                                 cmd_input_output_dict={
                                     validation_cmd: CmdOutput(validation_out)},
                                 data_collector_dict={
                                     GetIPDetailsFromControllers: {"overcloud-controller-fi862-0": "169.254.195.233",
                                                                   "overcloud-controller-fi862-1": "169.254.193.84 169.254.0.11",
                                                                   "overcloud-controller-fi862-2": "169.254.195.72"}
                                 })
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="virtual router exist on more than one controller",
                                 cmd_input_output_dict={
                                     validation_cmd: CmdOutput(validation_out)},
                                 data_collector_dict={
                                     GetIPDetailsFromControllers: {"overcloud-controller-fi862-0": "169.254.195.233",
                                                                   "overcloud-controller-fi862-1": "169.254.193.84 169.254.0.11",
                                                                   "overcloud-controller-fi862-2": "169.254.195.72 169.254.0.11"}
                                 })
    ]

    scenario_unexpected_system_output=[
        ValidationScenarioParams(scenario_title="data collector raised internal exception",
                                 cmd_input_output_dict={
                                     validation_cmd: CmdOutput(validation_out)},
                                 data_collector_dict={
                                     GetIPDetailsFromControllers: {"overcloud-controller-fi862-0": None,
                                                                   "overcloud-controller-fi862-1": "169.254.193.84 169.254.0.11",
                                                                   "overcloud-controller-fi862-2": "169.254.195.72"}
                                 })
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_unexpected_system_output(self, scenario_params, tested_object)