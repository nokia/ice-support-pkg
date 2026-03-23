from __future__ import absolute_import

import ipaddress
from HealthCheckCommon.operations import *
from HealthCheckCommon.validator import Validator, InformatorValidator
from tools.python_utils import PythonUtils
from HealthCheckCommon.UnifySystemParameterCheck import UnifySystemParameterCheck
import tools.sys_parameters as sys_param
from tools.global_enums import Version
from tools.ConfigStore import ConfigStore
from tools.lazy_global_data_loader import *
from tools import user_params
import copy
import tools.DynamicPaths as DynamicPaths
import tools.sys_parameters as sys_parameters
from flows.Blueprint.CsfAddOnBlueprintDataCollectors import IstioVersion
from datetime import datetime
from flows.K8s.k8s_components.k8s_sanity_checks import K8sValidation
from six.moves import map
from six.moves import range
from six.moves import zip

class HostIPMI(InformatorValidator):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.CONTROLLERS, Objectives.STORAGE, Objectives.COMPUTES],
        Deployment_type.NCS_OVER_BM: [Objectives.ALL_NODES],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ALL_NODES],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ALL_NODES]
    }

    def set_document(self):
        self._unique_operation_name = 'host_ipmi_info'
        self._title = 'Host IPMI address'
        self._is_pure_info = True
        self._is_highlighted_info = True
        self._title_of_info = 'Host IPMI address'

    def get_system_info(self):
        info_table = self.get_dict_from_command_output('sudo ipmitool lan print', 'space', custom_delimiter=':')
        return info_table.get('IP Address')


class are_host_connected(Validator):
    objective_hosts = [Objectives.UC, Objectives.ONE_MASTER]

    def set_document(self):
        self._unique_operation_name = "are_all_hosts_connected"
        self._title = "Verify that all the hosts in the system are connected"
        self._failed_msg = "TBD"
        self._severity = Severity.ERROR

        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        host_executors = sys_param.get_host_executor_factory().get_all_host_executors()
        not_connected = [host for host in host_executors if not host_executors[host].is_connected]
        if len(not_connected):
            self._failed_msg = "Following hosts are not connected:\n{}".format("\n".join(not_connected))
            return False
        return True


class NetworkNetConf(Validator):
    def read_os_net_config(self):
        NET_CONFIG="/etc/os-net-config/config.{}"
        if self.file_utils.is_file_exist(NET_CONFIG.format("yaml")):
            output = self.get_output_from_run_cmd("sudo cat " + NET_CONFIG.format("yaml"))
            return PythonUtils.yaml_safe_load(output, file_path=NET_CONFIG.format("yaml"))['network_config']
        if self.file_utils.is_file_exist(NET_CONFIG.format("json")):
            output = self.get_output_from_run_cmd("sudo cat " + NET_CONFIG.format("json"))
            try:
                return json.loads(output)['network_config']
            except ValueError:
                raise UnExpectedSystemOutput(self.get_host_ip(), "sudo cat " + NET_CONFIG.format("json"),
                                             "issue with reading JSON out")
        else:
            raise UnExpectedSystemOutput(ip=self.get_host_ip(),
                                         cmd="",
                                         output="",
                                         message="nether {} or {} found".format(NET_CONFIG.format("json"),
                                                                                NET_CONFIG.format("yaml")))

    def ip_addr_map(self):
        map = dict()
        ip_out = self.get_output_from_run_cmd("sudo /sbin/ip -o addr")
        for line in ip_out.splitlines():
            slice = line.split()
            index = slice[0]
            interface = slice[1]
            inet = slice[2]
            address = slice[3]

            if inet in ['inet', 'inet6']:
                if interface in map:
                    map[interface].append(address)
                else:
                    map[interface] = [address]

        return map

    def ip_link_map(self):
        map = dict()
        ip_out = self.get_output_from_run_cmd("sudo /sbin/ip -o link")
        for line in ip_out.splitlines():
            index, interface, data = line.split(': ', 2)
            interface = interface.split('@', 1)[0]
            slice = data.split()
            flags = slice[0]
            mtu = slice[2]

            map[interface] = {'flags': flags, 'mtu': mtu}
        return map

    def is_ipv6(self):
        assert Deployment_type.is_ncs(gs.get_deployment_type()), 'IPv6 verification is only supported for NCS for now'
        if gs.get_deployment_type() == Deployment_type.NCS_OVER_BM:
            conf_info_path = DynamicPaths.ncs_bm_post_config_path
        else:
            conf_info_path = DynamicPaths.bcmt_conf_path
        conf_info = gs.get_base_conf()
        network_type = PythonUtils.get_value_from_nested_dict(conf_info, 'network_stack')
        if len(set(network_type)) > 1:
            err_msg = "Having different values for 'network_stack' at {}"
            raise NotApplicable(err_msg.format(conf_info_path))
        elif len(network_type) == 0:
            err_msg = "Failed to find 'network_stack' at {}"
            raise NotApplicable(err_msg.format(conf_info_path))
        if network_type[0] in ['ipv6_only', 'ipv4_dualstack']:
            return True
        else:
            return False


class NetworkInterfaceAddresses(NetworkNetConf):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.ALL_HOSTS],
        Deployment_type.NCS_OVER_BM: [Objectives.ALL_NODES]
    }

    def set_document(self):
        self._unique_operation_name = "network_interface_addresses"
        self._title = "Verify Interface Addresses"
        self._failed_msg = "Addresses missing from interfaces"
        self._severity = Severity.ERROR

        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        net_config = self.read_os_net_config()
        results = [item for item in net_config if 'addresses' in item]

        config_interfaces = {}
        for item in results:
            if 'name' in item:
                interface_name = item['name']
            elif item['type'] == 'vlan':
                interface_name = 'vlan{}'.format(item['vlan_id'])
            else:
                raise UnExpectedSystemOutput(self.get_host_ip(), "sudo cat /etc/os-net-config/config.json",
                                             net_config, "Expected to have name or type vlan for every item")

            # TODO: Support IPv6 - Need to find a cluster with IPv6
            ipv4 = [x['ip_netmask'] for x in item['addresses'] if 'ip_netmask' in x]
            config_interfaces[interface_name] = ipv4

        active_addrs = self.ip_addr_map()

        failures = []

        for interface, addresses in list(config_interfaces.items()):
            # Check if the Interface Exists
            if interface not in active_addrs:
                failures.append('{} interface does not exist on the system'.format(interface))
                continue

            # Check if address is configured on the interface
            for address in addresses:
                if address not in active_addrs[interface]:
                    failures.append('{} not assigned to {}'.format(address, interface))

        if failures:
            self._failed_msg = '\n'.join(failures)
            return False

        return True


class NetworkInterfaceLinks(NetworkNetConf):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.ALL_HOSTS],
        Deployment_type.NCS_OVER_BM: [Objectives.ALL_NODES]
    }

    def set_document(self):
        self._unique_operation_name = "network_interface_links"
        self._title = "Verify Interface Links"
        self._failed_msg = "interfaces are down"
        self._severity = Severity.ERROR

        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        net_config = self.read_os_net_config()
        active_links = self.ip_link_map()

        def find_members(data):
            results = []
            for item in data:
                if 'members' in item:
                    results.extend(find_members(item['members']))
                if any(x in item['type'] for x in ['interface', 'sriov_pf']):
                    results.append(item['name'])
            return results

        # Find all interfaces, excluding bridges
        interfaces = []
        for item in net_config:
            if 'members' in item:
                interfaces.extend(find_members(item['members']))
            if item['type'] == 'ovs_patch_port':
                pass
            elif 'name' in item and not item['name'].startswith('br'):
                interfaces.append(item['name'])
            elif item['type'] == 'vlan':
                interfaces.append('vlan{}'.format(item['vlan_id']))
        interfaces = list(set(interfaces))

        # Check Interface state (up/down)
        failures = []
        for interface in interfaces:
            if interface not in active_links:
                failures.append('{} does not exist on the system'.format(interface))
                continue

            state = self.get_output_from_run_cmd("cat /sys/class/net/{}/operstate".format(interface)).strip()
            if state != 'up':
                failures.append('{} interface is {}'.format(interface, state))
                continue

        if failures:
            self._failed_msg = '\n'.join(failures)
            return False

        return True


class NetworkInterfaceMTU(NetworkNetConf):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.ALL_HOSTS],
        Deployment_type.NCS_OVER_BM: [Objectives.ALL_NODES]
    }

    def set_document(self):
        self._unique_operation_name = "network_interface_mtu"
        self._title = "Verify Interface MTUs"
        self._failed_msg = "interfaces MTUs are not aligned"
        self._severity = Severity.ERROR

        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        if Deployment_type.is_cbis(gs.get_deployment_type()) and gs.get_version() == Version.V24:
            self._severity = Severity.NOTIFICATION
        net_config = self.read_os_net_config()
        active_links = self.ip_link_map()

        def find_members(data):
            results = {}
            for item in data:
                if 'members' in item:
                    results.update(find_members(item['members']))
                if any(x in item['type'] for x in ['interface', 'sriov_pf']):
                    results[item['name']] = item['mtu']
            return results

        # Find all interfaces, excluding bridges
        interfaces = {}
        for item in net_config:
            if 'members' in item:
                interfaces.update(find_members(item['members']))
            if 'mtu' in item:
                if item['type'] == 'vlan':
                    name = 'vlan{}'.format(item['vlan_id'])
                else:
                    name = item['name']
                interfaces[name] = item['mtu']

        # Check Interface state (up/down)
        failures = []
        for interface, mtu in list(interfaces.items()):
            if interface not in active_links:
                failures.append('{} does not exist on the system'.format(interface))
                continue

            device_mtu = self.get_output_from_run_cmd("cat /sys/class/net/{}/mtu".format(interface)).strip()
            if mtu != int(device_mtu):
                failures.append('{} mtu set to {}, should be {}'.format(interface, device_mtu, mtu))
                continue

        if failures:
            self._failed_msg = '\n'.join(failures)
            return False

        return True


class NetworkBondCheck(NetworkNetConf):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.COMPUTES, Objectives.STORAGE, Objectives.CONTROLLERS],
        Deployment_type.NCS_OVER_BM: [Objectives.MASTERS, Objectives.WORKERS, Objectives.EDGES]
    }
    LACP_ACTIVE_ACTIVE_LINK_MODE = '802.3ad 4' # LACP Active-Active Link Aggregation Mode

    def set_document(self):
        self._unique_operation_name = "network_bond_check"
        self._title = "Verify Network Bonds"
        self._failed_msg = "network bonds are unhealthy"
        self._severity = Severity.ERROR

        self._implication_tags = [ImplicationTag.RISK_NO_HIGH_AVAILABILITY]

    def get_config_bonds(self):
        net_config = self.read_os_net_config()

        linux_bonds = []
        ovs_bonds = []

        # Find Linux Bonds
        for item in net_config:
            if item['type'] == 'linux_bond':
                linux_bonds.append(item)
            elif item['type'] == 'ovs_bridge':
                if 'member' not in item:
                    continue
                for member in item['members']:
                    if member['type'] == 'linux_bond':
                        linux_bonds.append(member)

        # Find OVS Bonds
        for item in net_config:
            if item['type'] == 'ovs_bridge':
                if 'member' not in item:
                    continue
                for member in item['members']:
                    if member['type'] == "ovs_bond":
                        ovs_bonds.append(member)

        return (linux_bonds, ovs_bonds)

    def linux_bond(self, bond):
        name = bond['name']
        slaves = [m['name'] for m in bond['members'] if any(x in m['type'] for x in ['interface', 'sriov_pf'])]

        if len(slaves) < 1:
            return "{}: slaves not found in configuration".format(name)

        # Check for bond existance
        rc, _, _ = self.run_cmd("test -e /sys/class/net/{}".format(name))
        if rc != 0:
            return "{} does not exist".format(name)

        # Check bond state
        state = self.get_output_from_run_cmd("cat /sys/class/net/{}/operstate".format(name)).strip()
        if state != "up":
            return "{} is {}".format(name, state)

        # check member state for LACP Active-Active
        mode = self.get_output_from_run_cmd("cat /sys/class/net/{}/bonding/mode".format(name)).strip()
        if mode == NetworkBondCheck.LACP_ACTIVE_ACTIVE_LINK_MODE:
            member_state = self.get_output_from_run_cmd("cat /proc/net/bonding/{} | grep 'Churn State'".format(name)).strip()
            if "churned" or "monitoring" in member_state:
                return "{} is unhealthy".format(name)

        active_slaves = self.get_output_from_run_cmd("cat /sys/class/net/{}/bonding/slaves".format(name))
        active_slaves = active_slaves.strip().split()
        if set(slaves) != set(active_slaves):
            return "{} using {}; should use {}".format(name, ', '.join(active_slaves), ', '.join(slaves))

        slave_state = {}
        for slave in slaves:
            slave_state[slave] = self.get_output_from_run_cmd(
                "cat /sys/class/net/{}/lower_{}/operstate".format(name, slave)).strip()

        if any(v != 'up' for k, v in list(slave_state.items())):
            return "{} is unhealthy: {}".format(name, slave_state)

    def ovs_bond(self, bond):
        name = bond['name']
        slaves = [m['name'] for m in bond['members'] if any(x in m['type'] for x in ['interface', 'sriov_pf'])]

        if len(slaves) < 1:
            return "{}: slaves not found in configuration".format(name)

        rc, out, err = self.run_cmd("sudo ovs-appctl bond/show {}".format(name))

        if rc != 0:
            return "{} does not exist or Open vSwitch is down".format(name)

        slave_state = {}
        for line in out.splitlines():
            if line.startswith('slave'):
                # state will be: [enabled, disabled]
                slave, state = line.replace('slave ', '').split(':')
                slave = slave.strip()
                state = state.strip()
                slave_state[slave] = state

        active_slaves = list(slave_state.keys())
        if set(slaves) != set(active_slaves):
            return "{} using {}; should use {}".format(name, ', '.join(active_slaves), ', '.join(slaves))

        if any(v != 'enabled' for k, v in list(slave_state.items())):
            return "{} is unhealthy: {}".format(name, slave_state)

    def is_validation_passed(self):
        linux_bonds, ovs_bonds = self.get_config_bonds()
        failures = []
        for bond in linux_bonds:
            r = self.linux_bond(bond)
            if r:
                failures.append(r)

        for bond in ovs_bonds:
            r = self.ovs_bond(bond)
            if r:
                failures.append(r)

        if failures:
            self._failed_msg = '\n'.join(failures)
            return False

        return True


################ SOUVIK CODE BEGINS ###################

######################################################
## network_validations      bm-20-555,bm-20-803,bm-21-allinone,vsphere,openstack
## bm-20-555,vsphere,openstack
#######################################################

class ValidationNetworkMaskCheck(Validator):

    # objective_hosts = [Objectives.ONE_MANAGER]

    def get_parameter_from_conf(self):
        raise NotImplementedError

    def set_unique_operation_name(self):
        raise NotImplementedError

    def set_title(self):
        raise NotImplementedError

    def set_failed_msg(self):
        raise NotImplementedError

    def set_document(self):
        self._unique_operation_name = self.set_unique_operation_name()
        self._title = self.set_title()
        self._failed_msg = self.set_failed_msg()
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):

        ### COMMON Code for both of the Validations ..
        #### OverlayNetwork MASK Check and InternalServiceNetwork Mask

        NCS_version_MAJOR = sys_param.get_version()
        NCS_version_MINOR = sys_param.get_sub_version()

        # From FP3 release onward this check will be added in Product itself
        # Till FP2 it has to be added as separate checks
        # But we enabled the Checks for all NCS versions irrespectively 
        # Reference : ICE-2584
        # NCS Version/sub-version details: https://confluence.ext.net.nokia.com/display/CBCS/NCS20FP2SU1+patch+procedure+-+target+version

        ### self.get_parameter_from_conf() function 
        ### Is created in respective Classes with specific process

        # print("Version NCS20FP2 ... Lets process")
        cidr_block1 = self.get_parameter_from_conf()
        x = cidr_block1.split('/')
        mask = x[1]

        ## CoreDns module could only handle netmasks which are times of 8
        ## So need to check MASK is Divisible by 8 or not

        if int(mask) % 8 != 0:
            self._failed_msg += "\nCurrent network mask is '{}' - it should be divided by 8 for CoreDns".format(mask)
            return False
        else:
            return True


#########################################################

class OverlayNetworkCheck(ValidationNetworkMaskCheck):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MANAGER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.DEPLOYER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.DEPLOYER],
    }

    def set_unique_operation_name(self):
        return "OverlayNetworkCheck"

    def set_title(self):
        return "OverlayNetworkCheck"

    def set_failed_msg(self):
        return "OverlayNetworkCheck Wrong!!"

    def get_parameter_from_conf(self):
        # If CN-B Then Follow this Block
        if sys_param.get_deployment_type() == Deployment_type.NCS_OVER_BM:
            conf_dict = ConfigStore.get_ncs_bm_conf()
            cidr_block = conf_dict["cluster_deployment"]["cluster_config"]["overlay_network"]

        # If CN-A Then Follow this Block
        else:
            conf_dict = ConfigStore.get_ncs_cna_conf()
            if conf_dict is None:
                conf_dict = ConfigStore.get_ncs_cna_user_conf()
                cidr_block = conf_dict["Clusters"]["cluster-01"]["overlay_network"]
            else:
                cidr_block = conf_dict["cluster_config"]["overlay_network"]

        return cidr_block


#######################################################

class InternalServiceNetworkCheck(ValidationNetworkMaskCheck):
    objective_hosts = [Objectives.ONE_MANAGER]

    def set_unique_operation_name(self):
        return "InternalServiceNetworkCheck"

    def set_title(self):
        return "Verify Internal Service Network Mask"

    def set_failed_msg(self):
        return "Internal Service Network Mask on configuration file at 'subnets' >> 'tenant' >> 'network_address' is worng"

    def get_parameter_from_conf(self):
        ## Only for CN-B .. Not for CN-A
        conf_dict = ConfigStore.get_ncs_bm_conf()
        cidr_block = conf_dict["subnets"]["tenant"]["network_address"]
        # print("InternalServiceNetwork Network is :   " + cidr_block)
        return cidr_block


############### SOUVIK CODE ENDS #############################

class NuageVersionDataCollector(DataCollector):
    objective_hosts = [Objectives.COMPUTES]

    def collect_data(self):
        # output:
        # ovs-vsctl (Open vSwitch) 20.10.6-359-nuage-6wind
        cmd = 'sudo ovs-vsctl --version'
        out = self.get_output_from_run_cmd(cmd)
        nuage_ml2 = ConfigStore.get_cbis_user_config()['CBIS']['openstack_deployment'].get("nuage_ml2")
        if 'nuage' not in out:
            if str(nuage_ml2) == "True":
                return 'Nuage ML2 is implemented'
            return 'Nuage is not implemented'
        version_line = out.splitlines()[0]
        version_prefix_found = re.findall(r'\d+.\d+.\d+-\d+', version_line)
        if not version_prefix_found:
            raise UnExpectedSystemOutput(self.get_host_ip(), cmd, out)
        version_prefix = version_prefix_found[0]
        return version_prefix


class IsNuageVersionUniform(InformatorValidator):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "is_nuage_version_uniform"
        self._title = "Verify Nuage version is uniform on all hosts"
        self._failed_msg = "TBD"
        self._severity = Severity.CRITICAL
        self._info = ""
        self._is_highlighted_info = True
        self._title_of_info = "Nuage Version"
        self._is_pure_info = False
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        cbis_version = gs.get_version()
        if cbis_version < Version.V20:
            # from cbis 20 nuage is not on the controllers
            NuageVersionDataCollector.objective_hosts.append(Objectives.CONTROLLERS)
        res = self.run_data_collector(NuageVersionDataCollector)
        version_to_hosts_dict = PythonUtils.reverse_dict(res)

        if len(version_to_hosts_dict) == 0:
            return True
        
        if len(version_to_hosts_dict) == 1:
            self._system_info = list(version_to_hosts_dict.keys())[0]
            return True
        self._system_info = PythonUtils.key_to_list2str("list of the host of each version:", version_to_hosts_dict)
        self._failed_msg = 'Nuage version is not uniform in all hosts:\n{}'.format(self._system_info)
        return False


class CheckIptablesSizeUniform(UnifySystemParameterCheck):
    def set_document(self):
        self._unique_operation_name = "is_iptables_rules_are_uniform"
        self._title = "Validate that iptables rules are uniform"
        self._failed_msg = "not finished"
        self._severity = Severity.CRITICAL
        self._info = ""
        self._title_of_info = "ip table size"
        self._is_pure_info = False
        self._implication_tags = [ImplicationTag.SYMPTOM]

    def _set_system_parameter_name(self):
        return "iptables rules size"

    def _is_check_relevant(self, parameter_host_dict):
        return True

    def _process_parameter_from_command_output(self, out, err, exit_code, host_name):
        return out

    def _user_set_info(self, is_check_relevant, parameter_host_dict):
        if len(parameter_host_dict) == 1:
            return list(parameter_host_dict.keys())[0]
        return PythonUtils.key_to_list2str("list of the host of each iptable size:", parameter_host_dict)

    def _set_command_to_execute_on_each_host(self):
        return "sudo sudo iptables -L INPUT |wc -l"


class IptablesSizeUniformComputes(CheckIptablesSizeUniform):
    def _set_target_roles(self):
        return [Objectives.COMPUTES]

    def set_document(self):
        self._unique_operation_name = "is_iptables_rules_are_uniform_computes"
        self._title = "Validate that iptables rules are uniform computes"
        self._failed_msg = "not finished"
        self._severity = Severity.CRITICAL
        self._info = ""
        self._title_of_info = "ip table size"
        self._is_pure_info = False
        self._implication_tags = [ImplicationTag.SYMPTOM]


class IptablesSizeUniformStorage(CheckIptablesSizeUniform):
    def _set_target_roles(self):
        return [Objectives.STORAGE]

    def set_document(self):
        self._unique_operation_name = "is_iptables_rules_are_uniform_storage"
        self._title = "Validate that iptables rules are uniform: storage"
        self._failed_msg = "not finished"
        self._severity = Severity.CRITICAL
        self._info = ""
        self._title_of_info = "ip table size"
        self._is_pure_info = False
        self._implication_tags = [ImplicationTag.SYMPTOM]


class IptablesSizeUniformControllers(CheckIptablesSizeUniform):
    def _set_target_roles(self):
        return [Objectives.CONTROLLERS]

    def set_document(self):
        self._unique_operation_name = "is_iptables_rules_are_uniform_controllers"
        self._title = "Validate that iptables rules are uniform: controllers"
        self._failed_msg = "not finished"
        self._severity = Severity.CRITICAL
        self._info = ""
        self._title_of_info = "ip table size"
        self._is_pure_info = False
        self._implication_tags = [ImplicationTag.SYMPTOM]


class DuplicateIP(Validator):
    CMD_ARPING = "sudo arping -c 1 -d -r {}"
    CMD_GET_IP_STRING = "sudo ip -4 addr | grep inet"
    objective_hosts = [Objectives.ONE_MASTER, Objectives.ONE_CONTROLLER]

    def set_document(self):
        self._unique_operation_name = "duplicate_ip"
        self._title = "Check for duplicate IP"
        self._failed_msg = ""
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.RISK_GARBAGE_CLEANING_RECOMMENDED, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def arping(self, ip_address):
        '''Returns a list of mac addressess which replied to
        'arp who has' ip_address request or returns an empty
        list if there is no reply.
        arguments:
        ip_address -- string, containing a valid ipv4 address
        '''
        mac_addresses = []
        return_code, out, err = self.run_cmd(DuplicateIP.CMD_ARPING.format(ip_address), timeout=10)
        if return_code == 1:
            lines = out.decode("UTF-8").split('\n')
            for line in lines:
                if len(line) > 0:
                    mac_addresses.append(line)
        return mac_addresses

    def get_duplicates(self, ipv4_network):
        """Returns a dict of ip address as key and a list of
        corresponding mac addresses as value.

        arguments:
        ipv4_network -- object, ipaddress.IPv4Network 
        """
        duplicates = {}
        for ip in ipv4_network:
            macs = self.arping(ip)
            if len(macs) > 0:
                duplicates[ip] = macs
        return duplicates

    def is_validation_passed(self):
        duplicate_ips = {}
        out = self.get_output_from_run_cmd(self.CMD_GET_IP_STRING, timeout=10)
        cidr_list = PythonUtils.get_cidr_from_string(out.encode('UTF-8'))
        for cidr in cidr_list:
            network = ipaddress.IPv4Network(cidr.decode('UTF-8'), False)
            if not network.is_loopback:
                duplicate_ips.update(self.get_duplicates(network))
        if len(duplicate_ips) > 0:
            self._failed_msg = "Following ips are used multiple times: {}".format(duplicate_ips)
            return False
        else:
            return True


#########################################################
### ICET-1080: Checks for Calicoctl | IPSET LIST | iptables service ######
### SOUVIK CODE BEGINS ####
########## CHECK 1 : CALICOCTL NODE STATUS Checking #######
########## CHECK 2 : CALICOCTL IPAM SHOW Checking ######
########## BUg fix : ICET-2858_calico_node_status_all_nodes
######### https://jiradc2.ext.net.nokia.com/browse/ICET-2858

class CalicoNodeStatus(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.MASTERS, Objectives.WORKERS, Objectives.EDGES],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.MASTERS, Objectives.WORKERS, Objectives.EDGES],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.MASTERS, Objectives.WORKERS, Objectives.EDGES],
    }

    def set_document(self):
        self._unique_operation_name = "calico_node_status"
        self._title = "Validate CALICO CNI NODE STATUS"
        self._failed_msg = "Error in CALICOCTL Node Status"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.APPLICATION_DOMAIN]

    def is_validation_passed(self):
        return_code, out, err = self.run_cmd("sudo /usr/local/sbin/calicoctl node status")
        if return_code == 0:
            calicoctl_node_status = [y for y in (x.strip() for x in out.splitlines()) if ("|" in y) and ("PEER ADDRESS" not in y)]
        else:
            calicoctl_node_status = [str(err)]
            self._failed_msg += "\n\n" + str(err)

        status = True

        for data in calicoctl_node_status:
            if not ("Established" in data):
                status = False

        if not status:
            self._failed_msg += "\n\n" + out
        return status
			
##############  CODE ENDS   #############################

class CalicoIpamStatus(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER],
    }

    def set_document(self):
        self._unique_operation_name = "calico_ipam_status"
        self._title = "Validate CALICO CNI IPAM STATUS"
        self._failed_msg = "WARNING in CALICOCTL IPAM Status, more than 80% IPs used"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.RISK_RESOURCE_CLEANING_RECOMMENDED]

    def is_validation_passed(self):

        stream1 = self.get_output_from_run_cmd("sudo /usr/local/sbin/calicoctl ipam show")

        array1 = [y for y in (x.strip() for x in stream1.splitlines()) if y]
        calico_ipam_show = []
        j = 0

        for i in range(3, (len(array1) - 1)):
            calico_ipam_show.append(array1[i])

        for j in range(0, len(calico_ipam_show)):
            a = calico_ipam_show[j].split("|")
            ips_used_str = str(a[4].strip())
            b1 = ips_used_str.split("(")
            b2 = b1[1].strip()
            b3 = b2.split("%")
            b4 = b3[0].strip()
            ips_used_percentage = b4
            # print ("USED IPS:" +str(ips_used_percentage))

            if (int(ips_used_percentage) < 80):
                # print ("ALL GOOD !!!")
                return True
            else:
                # print ("WARNING !!! more than 80 percent used")
                return False


########## CHECK 3 : IPSET LIST checks ######
########## DUAL STACK ipv6 Improvement #################
#####   https://jiradc2.ext.net.nokia.com/browse/ICET-2721
####    SOUVIK DAS | 27-01-2025
##########################################################

class VerifyIpsetListBcmtwhitelist(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.MASTERS],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.MASTERS],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.MASTERS],
    }

    def set_document(self):
        self._unique_operation_name = "verify_ipset_list_bcmtwhitelist"
        self._title = "Validate IPSET LIST AND BCMTWHITELIST"
        self._failed_msg = "NODE MISSING IN BCMTWHITELIST | Missing IPs are : "
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def check_ips_in_ipset_list(self, ip, missing_ips_ipset):
        cmd_to_run = "sudo /usr/sbin/ipset list | grep " + ip + " | wc -l"
        streamz = self.get_output_from_run_cmd(cmd_to_run)
        if (int(streamz) == 0):
            missing_ips_ipset.append(ip)
        return missing_ips_ipset

    def validate_missing_ips_ipset(self, ip_list):
        missing_ips_ipset = []
        if len(ip_list) > 0:
            for ip in ip_list:
                if (ip != "<none>" and ip != "DATA"):
                    if "," in ip:
                        dual_ipv6_ipv4_ips = ip.split(",")
                        for ipv4_ipv6 in dual_ipv6_ipv4_ips:
                            missing_ips_ipset = self.check_ips_in_ipset_list(ipv4_ipv6, missing_ips_ipset)
                    else:
                        missing_ips_ipset = self.check_ips_in_ipset_list(ip.strip(), missing_ips_ipset)

        return missing_ips_ipset

    def is_validation_passed(self):
        external_ips_out = self.get_output_from_run_cmd(
            "sudo /usr/local/bin/kubectl get nodes -o wide -o=custom-columns='DATA:.status.addresses[?(@.type==\"ExternalIP\")].address'")

        internal_ips_out = self.get_output_from_run_cmd(
            "sudo /usr/local/bin/kubectl get nodes -o wide -o=custom-columns='DATA:.status.addresses[?(@.type==\"InternalIP\")].address'")

        InternalIPs = [internal_ip.strip() for internal_ip in internal_ips_out.splitlines() if internal_ip.strip()]
        ExternalIPs = [external_ip.strip() for external_ip in external_ips_out.splitlines() if external_ip.strip()]

        dual_ipv6_ipv4_ips = []
        dual_ipv6_ipv4_ips_external = self.validate_missing_ips_ipset(ExternalIPs)
        dual_ipv6_ipv4_ips_internal = self.validate_missing_ips_ipset(InternalIPs)

        dual_ipv6_ipv4_ips = dual_ipv6_ipv4_ips_external + dual_ipv6_ipv4_ips_internal

        if (len(dual_ipv6_ipv4_ips) > 0):
            for i in dual_ipv6_ipv4_ips:
                self._failed_msg = self._failed_msg + "\n" + str(i)
            return False
        else:
            return True

########## CHECK 4 : IPTABLE SERVICE STOP check ######

class VerifyIptablesServiceStop(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ALL_NODES],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ALL_NODES],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ALL_NODES],
    }

    def set_document(self):
        self._unique_operation_name = "verify_iptables_service_stop"
        self._title = "Validate SYSTEMCTL IPTABLES SERVICE STOPPED"
        self._failed_msg = "SYSTEMCTL IPTABLES SERVICE RUNNING"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]

    def is_validation_passed(self):
        exit_code, out, err = self.run_cmd("sudo /usr/bin/systemctl status iptables")

        if " Active: active (running)" in out:
            self._severity = Severity.CRITICAL
            return False

        if "Active: active (exited)" or " Active: inactive (dead)" in out:
            return True

        self._failed_msg = "systemctl iptable isn't in proper state. status is:\n{}\n{}".format(
            out, err)
        return False


########## CHECK 5 : calico.conflist exists or empty checking ######
########## Bug fix : https://jiradc2.ext.net.nokia.com/browse/ICET-2258
########## Bug Fix :   https://jiradc2.ext.net.nokia.com/browse/ICET-2866 | ISTIO modifies MULTUS conf file name | NCS 22 Above

class VerifyCalicoConflistExistsNonEmpty(ValidationNetworkMaskCheck):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.MASTERS, Objectives.WORKERS, Objectives.EDGES],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.MASTERS, Objectives.WORKERS, Objectives.EDGES],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.MASTERS, Objectives.WORKERS, Objectives.EDGES],
    }

    def set_document(self):
        self._unique_operation_name = "verify_calico_conflist_exists_nonempty"
        self._title = "Validate CALICO and MULTUS Conf File"
        self._failed_msg = "ERROR!!\n"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION, ImplicationTag.APPLICATION_DOMAIN]

    def validate_multus_enabled_or_not(self):
        multus_enabled_flag = False
        # If CN-B Then Follow this Block
        if sys_param.get_deployment_type() == Deployment_type.NCS_OVER_BM:
            conf_dict = ConfigStore.get_ncs_bm_conf()
            multus_enabled_flag = conf_dict["cluster_deployment"]["cluster_config"]["k8s_use_multus"]

        # If CN-A Then Follow this Block
        else:
            conf_dict = ConfigStore.get_ncs_cna_conf()
            if conf_dict is None:
                raise UnExpectedSystemOutput(self.get_host_ip(), "", "File {} doesn't exists".
                                             format(user_params.initialization_factory.environment_info.base_conf))
            else:
                multus_enabled_flag = conf_dict["cluster_config"]["k8s_use_multus"]
        return multus_enabled_flag

    def check_file_status(self, filename):
        if self.file_utils.is_file_exist(filename):
            if not self.file_utils.is_file_empty(filename):
                return True
            else:
                self._failed_msg += filename +" file is empty\n"
        else:
            self._failed_msg += filename + " file is missing\n"
        return False

    def is_validation_passed(self):

        FILENAME_NCS20 = "/etc/cni/net.d/10-calico.conflist"
        FILENAME_NCS22A = "/etc/kubernetes/cni/net.d/10-calico.conflist"
        FILENAME_NCS22A_MULTUS_CALICO_COMBINED = ["/etc/kubernetes/cni/net.d/00-multus.conf","/etc/kubernetes/cni/net.d/00-multus.conflist"]

        ## If ISTIO Installed then ISTIO renames default Multus file.
        ## sudo kubectl logs -n istio-system cist-istio-istiocni-istio-cni-node-XXXXX |grep multus
        ## Renaming /host/etc/cni/net.d/00-multus.conf extension to .conflist
        ## install Created CNI config /host/etc/cni/net.d/00-multus.conflist 

        return_value = True
        NCS_version_MAJOR = sys_param.get_version()

        ### This code block for NCS versions less than 22
        if NCS_version_MAJOR < Version.V22:
            return_value = self.check_file_status(FILENAME_NCS20)
            return return_value
        else:
            ### NCS version is 22 or more
            ### First validate MULTUS enabled or not in cluster.
            ### /etc/kubernetes/cni/net.d/10-calico.conflist is NOT present on Setups where MULTUS is enabled. Only on MASTERS this file will be present, WORKER, EDGES it will not be there. 
            ###  If only one ALL-IN-ONE nodes there then all are edge, worker and master so then calico wont be in MASTER too then we need to search for :  "/etc/kubernetes/cni/net.d/00-multus.conf"  file

            multus_enabled_flag = self.validate_multus_enabled_or_not()
            
            ### When MULTUS is enabled on NCS22 and Above Clusters
            if multus_enabled_flag == True:
                ###     FOR MASTER NODES
                if Objectives.MASTERS in self.get_host_roles():
                    calico_conflist_file_exists = self.check_file_status(FILENAME_NCS22A)
                    if calico_conflist_file_exists:
                        return True
                    ## If 10-calico.conflist file not present on masters
                    else:
                        for multus_file in FILENAME_NCS22A_MULTUS_CALICO_COMBINED:
                            is_multus_conf_file_exists = self.check_file_status(multus_file)
                            if is_multus_conf_file_exists:
                                return True
                        return False
                ###  FOR NON-MASTER NODES
                else:
                    for multus_file in FILENAME_NCS22A_MULTUS_CALICO_COMBINED:
                            is_multus_conf_file_exists = self.check_file_status(multus_file)
                            if is_multus_conf_file_exists:
                                return True
                    return False
            ### When MULTUS is NOT enabled on NCS22 and Above Clusters
            else:
                return self.check_file_status(FILENAME_NCS22A)

class GetMultusNodes(DataCollector):
    objective_hosts = [Objectives.ONE_MASTER]

    def collect_data(self, **kwargs):
        output = self.get_output_from_run_cmd(
            "sudo /usr/local/bin/kubectl get nodes -l=ncs.nokia.com/multus_node=true --no-headers")
        multus_nodes = []

        for line in output.splitlines():
            multus_node = line.split()[0]
            multus_nodes.append(multus_node)

        return multus_nodes


########### EGRESS GATEWAY CODE #########

class CheckEgressGateway(Validator):

    def get_parameter_from_conf(self):
        conf_dict = ConfigStore.get_ncs_cna_conf()
        if conf_dict:
            os_auth_url = conf_dict["openstack"]["OS_AUTH_URL"]
        else:
            conf_dict = ConfigStore.get_ncs_cna_user_conf()
            os_auth_url = conf_dict["Openstack"]["OS_AUTH_URL"]
        url_ip_port = os_auth_url.strip().split(":")
        url_ip = url_ip_port[1]
        ips = url_ip.split('/')
        ip = ips[2]
        return ip

    def get_egress_name_and_namespace(self):
        stream = self.get_output_from_run_cmd("sudo /usr/local/bin/kubectl get egressgateway -A --no-headers").strip()

        egressgateway_list = []
        egressgateway_namespace_list = []

        for line in stream.splitlines():
            egressgateway = line.split()[1]
            egressgateway_namespace = line.split()[0]
            egressgateway_list.append(egressgateway)
            egressgateway_namespace_list.append(egressgateway_namespace)

        return egressgateway_list, egressgateway_namespace_list

    def get_egress_node_selectors_list(self, egressgateway_list, egressgateway_namespace_list):

        egress_node_selectors_list = []

        if len(egressgateway_list) > 0:
            for i in range(0, len(egressgateway_list)):

                egress_namespace_name = egressgateway_namespace_list[i]
                egress_name = egressgateway_list[i]

                cmd = "sudo /usr/local/bin/kubectl get egressgateway {} -n {} -o jsonpath='{{.spec.nodeSelector}}'".format(
                    egress_name, egress_namespace_name)

                egress_node_selector_name = self.get_output_from_run_cmd(cmd)

                egress_node_selector_name = str(egress_node_selector_name)
                special_chars = "\\{}\""
                for char in special_chars:
                    egress_node_selector_name = egress_node_selector_name.replace(char, '')

                egress_selector_array = egress_node_selector_name.strip().split(":")

                egress_node_selector_name = egress_selector_array[0] + "=" + egress_selector_array[1]

                cmd = "sudo /usr/local/bin/kubectl get nodes -l={} --no-headers".format(egress_node_selector_name)

                egres_nodes = (self.get_output_from_run_cmd(cmd)).strip()
                egress_from_nodes_list = []

                for line in egres_nodes.splitlines():
                    server_name = line.split()[0]
                    egress_from_nodes_list.append(server_name)

                strValue = ""
                for i in egress_from_nodes_list:
                    strValue = strValue + str(i).strip() + ":"

                last_char_index = strValue.rfind(":")
                strValue2 = strValue[:last_char_index] + "" + strValue[last_char_index + 1:]

                egress_node_selectors_list.append(strValue2)

        return egress_node_selectors_list

    def get_nexthops(self,egress_name, egress_namespace_name):
        #### Check for NEXTHOPS
        nexthops_list_string = ""
        cmd = "sudo /usr/local/bin/kubectl get egressgateway {} -n {} -o jsonpath='{{.spec.nodeEgressGatewayTemplate.nextHops}}'".format(egress_name, egress_namespace_name)
        out = self.get_output_from_run_cmd(cmd).strip()
        splitted_array = out.split(",")
        for i in splitted_array:
            processed_string = PythonUtils.replace_special_chars(i)
            nexthops_list_string = nexthops_list_string + "|" + processed_string
        return nexthops_list_string

    def get_nexthopgroup_list(self, egressgateway_list, egressgateway_namespace_list):
        nexthopgroup_list = []
        nexthops_list = []
        nexthop_egress_dict = {}
        SAFTY_THRESHOLD = 50

        if len(egressgateway_list) > SAFTY_THRESHOLD:
            raise UnExpectedSystemOutput(self.get_host_name(), "", "", "egressgateway_list too big size is {}, threshold is {}".format(len(egressgateway_list), SAFTY_THRESHOLD))

        if len(egressgateway_list) > 0:
            for i in range(0, len(egressgateway_list)):
                egress_name = egressgateway_list[i]
                egress_namespace_name = egressgateway_namespace_list[i]

                cmd = "sudo /usr/local/bin/kubectl get egressgateway {} -n {} -o jsonpath='{{.spec.nodeEgressGatewayTemplate.nextHopGroup}}'".format(egress_name, egress_namespace_name)

                nexthopgroup_name = self.get_output_from_run_cmd(cmd).strip()

                if not nexthopgroup_name:
                    nexthop = self.get_nexthops(egress_name, egress_namespace_name)
                    nexthops_list.append(nexthop)
                    temp_array = []
                    temp_array.append (nexthop)
                    nexthops_ips_list = self.get_nextHop_ips(temp_array)
                    nexthop_egress_dict [egressgateway_list[i]] = nexthops_ips_list
                else:
                    nexthopgroup_list.append(nexthopgroup_name)

        return nexthopgroup_list, nexthops_list , nexthop_egress_dict

    def get_egress_node_ip(self, nexthopgroup_list):
        nexthopgroup_namespace_list = []
        egress_gw_SNATinterface_list = []
        egress_gw_node_list = []
        egress_gw_IP_list = []
        neXtHop_EgressNode_dict = {}

        if len(nexthopgroup_list) > 0:
            for i in range(0, len(nexthopgroup_list)):
                cmd = "sudo /usr/local/bin/kubectl get nexthopgroup -A | grep -w {}".format(nexthopgroup_list[i])

                cmd_output = self.get_output_from_run_cmd(cmd).strip()

                for line in cmd_output.splitlines():
                    nexthopgroup_namespace_name = line.split()[0]
                    nexthopgroup_namespace_list.append(nexthopgroup_namespace_name)

        if nexthopgroup_list:
            for i in range(0, len(nexthopgroup_list)):
                namespace_name = nexthopgroup_namespace_list[i]
                hopgroup_name = nexthopgroup_list[i]

                cmd = "sudo /usr/local/bin/kubectl get nexthopgroup {} -n {} -o jsonpath='{{.status.nodes[*].nodeName}}'".format(
                    hopgroup_name, namespace_name)

                egress_gw_node_names = self.get_output_from_run_cmd(cmd)
                egress_gw_node_list.append(egress_gw_node_names)

                cmd = "sudo /usr/local/bin/kubectl get nexthopgroup {} -n {} -o jsonpath='{{.status.nodes[*].address}}'".format(
                    hopgroup_name, namespace_name)

                egress_gw_IPaddress = self.get_output_from_run_cmd(cmd)
                for ip in (egress_gw_IPaddress.split(" ")):
                    egress_gw_IP_list.append(ip)
                
                ips = egress_gw_IPaddress.split()
                neXtHop_EgressNode_dict[hopgroup_name] = ips

                cmd = "sudo /usr/local/bin/kubectl get nexthopgroup {} -n {} -o jsonpath='{{.spec.nextHopTemplate.bidirectionalForwardingDetectionInterface}}'".format(
                    hopgroup_name, namespace_name)

                egress_gw_SNATinterface_name = self.get_output_from_run_cmd(cmd)

                egress_gw_SNATinterface_list.append(egress_gw_SNATinterface_name)

        return egress_gw_node_list, egress_gw_IP_list, neXtHop_EgressNode_dict

    def get_egressGateway_from_NodeEgress_list(self,nodeegressgateway_list):
        egressgateway_list = []
        for egress in nodeegressgateway_list:
            char_to_find = '-'
            last_position = egress.rfind(char_to_find)
            egress_gateway_name = str(egress[0:int(last_position)])
            egressgateway_list.append(egress_gateway_name)
        return egressgateway_list

    def get_nextHop_ips (self, nexthops_list):
        nexthops_ips_list = []  
        if len(nexthops_list)!=0:
            for each_nexthop in nexthops_list:
                split_array = each_nexthop.split("|")
                split_array = split_array[1:]
                for i in split_array:
                    nexthops_ips_list.append (i)
        return nexthops_ips_list


class VerifyEgressGateway(CheckEgressGateway):
    objective_hosts = {
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.MASTERS, Objectives.WORKERS, Objectives.EDGES]
    }

    def set_document(self):
        self._unique_operation_name = "verify_egress_gateway"
        self._title = "verify egress gateway"
        self._failed_msg = "ERROR!! EGRESS CONFIGURATION WRONG\n"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        if sys_param.get_deployment_type() == Deployment_type.NCS_OVER_OPENSTACK:
            self.HORIZON_IP = self.get_parameter_from_conf()

        node_hostname = self.get_output_from_run_cmd("sudo /usr/bin/hostname")

        egressgateway_list, egressgateway_namespace_list = self.get_egress_name_and_namespace()

        egress_node_selectors_list = self.get_egress_node_selectors_list(egressgateway_list, egressgateway_namespace_list)

        if egress_node_selectors_list:
            for i in range(0, len(egress_node_selectors_list)):
                nodes = egress_node_selectors_list[i].split(":")

                for node in nodes:
                    if (node == node_hostname.strip()):
                        #### First Check CURL To Opestack Horoizon IP
                        curl_command = "curl -ks https://{} --connect-timeout 10".format(self.HORIZON_IP)
                        curl_return_code, curl_output, curl_err = self.run_cmd(curl_command)
                        if curl_return_code == 0:
                            return True ## IF CURL Success then All good
                        else:
                            self._failed_msg += "CURL FAILED:\n{}\n".format(curl_err)
                            """
                            IF CURL Fails then check PING, to see connectivity itself fails or not
                            -c = number of echo request = 10
                            -w = Timeout time 10 seconds
                            """
                            ping_cmd = "sudo /bin/ping -c10 -w10 {} | grep received".format(self.HORIZON_IP)
                            ping_return_code, ping_output, ping_err = self.run_cmd(ping_cmd)
                            if ping_return_code == 0:     ### If PING comamnd runs properly
                                split_ping_output = ping_output.split(",")
                                array_val1 = split_ping_output[1]
                                array_val2 = array_val1.split(" ")
                                ping_received = array_val2[1]
                                if int(ping_received.strip()) != 0:
                                    return True     ## If PING Packets received then Success
                                else:
                                    ### If PING comamnd NO packet received it's a FAILURE
                                    self._failed_msg += "NO PING Response received:\n{}\n".format(ping_output)
                                    return False
                            else:   ### If PING comamnd fails it's a FAILURE
                                self._failed_msg += "PING error:\n{}".format(ping_err)
                                return False
        return True


class VerifyAllowedAddressPair(VerifyEgressGateway):
    objective_hosts = {
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
    }

    def set_document(self):
        self._unique_operation_name = "verify_allowed_address_Pair"
        self._title = "verify allowed_address_Pair"
        self._failed_msg = "ERROR!!ALLOWED_ADDRESS_PAIRS CONFIGURATION WRONG\n"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION, ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        flag = 0
        egress_gw_IP_list_final = []
        egressgateway_list, egressgateway_namespace_list = self.get_egress_name_and_namespace()

        nexthopgroup_list, nexthops_list, nexthop_egress_dict = self.get_nexthopgroup_list(egressgateway_list, egressgateway_namespace_list)
        egress_gw_node_list, egress_gw_IP_list, neXtHop_EgressNode_dict = self.get_egress_node_ip(nexthopgroup_list)
        nexthops_ips_list = []

        if len(nexthops_list)!=0:
            nexthops_ips_list = self.get_nextHop_ips(nexthops_list)
            merged_egress_gw_ip_list = egress_gw_IP_list + nexthops_ips_list
            [egress_gw_IP_list_final.append(x) for x in merged_egress_gw_ip_list if x not in egress_gw_IP_list_final]
        else:
            egress_gw_IP_list_final = egress_gw_IP_list

        cmd = "sudo /usr/local/bin/kubectl get pod -n ncms | grep -i 'bcmt-api' | grep -i 'Running'"
        bcmt_api_pod_output = self.get_output_from_run_cmd(cmd).strip()
        bcmt_api_pod_array = bcmt_api_pod_output.split()
        bcmt_api_pod = bcmt_api_pod_array[0].strip()

        for j in range(len(egress_gw_IP_list_final)):
            ip_to_find = egress_gw_IP_list_final[j]
            main_command = "sudo /usr/local/bin/kubectl exec -n ncms {}".format(bcmt_api_pod)
            openstack_command = " port list"
            command_to_be_run = self.get_openstack_api_command(main_command, openstack_command)
            command_output = self.get_output_from_run_cmd(command_to_be_run).strip()

            matching_line = next((line for line in command_output.splitlines() if ip_to_find in line), "")

            if matching_line:
                api_port = matching_line.split("|")
                output_openstack_api_port = api_port[1].strip() if len(api_port) > 1 else None

                if output_openstack_api_port:
                    openstack_command = " port show {} -f json".format(output_openstack_api_port)
                    command_to_be_run = self.get_openstack_api_command(main_command, openstack_command)
                    output_openstack_port_show = self.get_dict_from_command_output(command_to_be_run, 'json', custom_delimiter=':')
                    allowed_address_pairs = output_openstack_port_show.get('allowed_address_pairs')
                    address_pair_found = re.search("0.0.0.0/0", str(allowed_address_pairs))

                    if not address_pair_found:
                        flag += 1
                        self._failed_msg = self._failed_msg + "\nCheck node IP : " + egress_gw_IP_list_final[j]
                else:
                    flag += 1
                    self._failed_msg = self._failed_msg + "\nPort ID missing for node IP: " + ip_to_find
            else:
                flag += 1
                self._failed_msg = self._failed_msg + "\nPort not found for node IP: " + ip_to_find

        if flag > 0:
            return False

        return True

######## VerifyAllowedAddressPair  CODE ENDS #############

class NoDynamicAddressInIptables(Validator):
    objective_hosts = [Objectives.MASTERS]

    def set_document(self):
        self._title = "Validate that there is no dynamic IP configuration set in iptables file"
        self._failed_msg = "Dynamic IP configuration is set in: "
        self._severity = Severity.ERROR
        self._unique_operation_name = "validate_no_dynamic_ip_set_in_iptables"
        self._implication_tags=[ImplicationTag.RISK_BAD_CONFIGURATION]

    def is_validation_passed(self):
        iptables_paths = ["/etc/sysconfig/iptables", "/etc/sysconfig/iptables.d/iptables"]
        valid_kube_components = ['kube-controllers', 'kube-scheduler']
        status = True
        for iptables_file in iptables_paths:
            if self.file_utils.is_file_exist(iptables_file):
                iptables_file_status = True
                return_code_calico, cali_out, err = self.run_cmd('sudo grep -i cali {}'.format(iptables_file))
                if return_code_calico == 0:
                    iptables_file_status = False
                return_code_kube, kube_out, err = self.run_cmd('sudo grep -i kube {}'.format(iptables_file))
                if return_code_kube == 0:
                    for line in kube_out.splitlines():
                        if not any(component in line for component in valid_kube_components):
                            iptables_file_status = False
                if iptables_file_status == False:
                    self._failed_msg += " {} ".format(iptables_file)
                    status = False
        return status


class WhereaboutsConfiguration(Validator):
    objective_hosts = 'NA'

    def set_document(self):
        self._title = 'Whereabouts Validations Base Class'
        self._failed_msg = 'NA'
        self._severity = Severity.NA
        self._unique_operation_name = 'Whereabouts Validations Base Class'
        self._implication_tags = 'NA'

    def get_whereabouts_cmd_output(self, cmd, timeout=30, message='', hosts_cached_pool=None,
                                   get_not_ascii=False, add_bash_timeout=False):
        return_code, out, err = self.run_cmd(cmd, timeout, hosts_cached_pool,
                                             get_not_ascii, add_bash_timeout)

        if return_code != 0:    # jsonpath range being used, no need to check for 'No resources found' case
            return ''
        return out

    def gather_net_attach_def_configs(self):
        cmd = "sudo /usr/local/bin/kubectl get net-attach-def -A -o=jsonpath='{range .items[*]}{.metadata.name}" \
              "<split>{.metadata.namespace}<split>{.spec.config}<split>{end}'"
        cmd_out = self.get_whereabouts_cmd_output(cmd)
        temp_net_attach_def_configs = cmd_out.split('<split>')
        del temp_net_attach_def_configs[-1]
        temp_net_attach_def_configs = [temp_net_attach_def_configs[i:i + 3]
                                       for i in range(0, len(temp_net_attach_def_configs), 3)]
        net_attach_def_configs = []
        for net_attach_def in temp_net_attach_def_configs:
            net_attach_def_configs.append({'name': net_attach_def[0], 'namespace': net_attach_def[1],
                                           'config': json.loads(net_attach_def[2])})
        return net_attach_def_configs

    # caching here because kubectl get pod command can take a long time in large clusters with many pods
    @lazy_global_data_loader
    def gather_pod_configs(self):
        cmd = "sudo /usr/local/bin/kubectl get pod -A -o=jsonpath='{range .items" \
              "[?(@.metadata.annotations.k8s\\.v1\\.cni\\.cncf\\.io/network-status)]}{.metadata.name}<split>" \
              "{.metadata.namespace}<split>{.metadata.annotations.k8s\\.v1\\.cni\\.cncf\\.io/network-status}<split>" \
              "{end}'"
        cmd_out = self.get_whereabouts_cmd_output(cmd)
        temp_pod_configs = cmd_out.split('<split>')
        second_temp_pod_configs = []
        for item in temp_pod_configs:
            second_temp_pod_configs.append(item.replace('\n', ''))
        del second_temp_pod_configs[-1]
        second_temp_pod_configs = [second_temp_pod_configs[i:i + 3] for i in range(0, len(second_temp_pod_configs), 3)]
        pod_configs = []
        for pod in second_temp_pod_configs:
            pod_configs.append({'name': pod[0], 'namespace': pod[1], 'network': json.loads(pod[2])})
        return pod_configs

    def gather_ippool_configs(self):
        cmd = "sudo /usr/local/bin/kubectl get ippools -A -o=jsonpath='{range .items[*]}{.metadata.name}<split>" \
              "{.metadata.namespace}<split>{.spec}<split>{end}'"
        cmd_out = self.get_whereabouts_cmd_output(cmd)
        temp_ippool_configs = cmd_out.split('<split>')
        del temp_ippool_configs[-1]
        temp_ippool_configs = [temp_ippool_configs[i:i + 3] for i in range(0, len(temp_ippool_configs), 3)]
        ippool_configs = []
        for ippool in temp_ippool_configs:
            ippool_configs.append({'name': ippool[0], 'namespace': ippool[1], 'spec': json.loads(ippool[2])})
        return ippool_configs

    def get_net_attach_def_whereabouts_list(self):
        net_attach_def_configs = self.gather_net_attach_def_configs()
        temp_net_attach_def_whereabouts_list = []
        for net_attach_def in net_attach_def_configs:
            if 'ipam' in net_attach_def['config'] and 'type' in net_attach_def['config']['ipam'] and 'whereabouts' in \
                    net_attach_def['config']['ipam']['type']:
                temp_net_attach_def_whereabouts_list.append({'name': net_attach_def['name'],
                                                             'namespace': net_attach_def['namespace']})
                # This append uses the name inside the network attachment definition config to add to the list. This is
                # important because sometimes the names of the network attachment definition is different from the name
                # inside the network attachment definition config
                if 'name' in net_attach_def['config']:
                    temp_net_attach_def_whereabouts_list.append({'name': json.dumps(net_attach_def['config']['name'])
                                                                .strip('"'), 'namespace': net_attach_def['namespace']})
            # This part is to catch if whereabouts is configured inside plugins
            if 'plugins' in net_attach_def['config']:
                for plugin in net_attach_def['config']['plugins']:
                    if 'ipam' in plugin and 'type' in plugin['ipam'] and 'whereabouts' in plugin['ipam']['type']:
                        temp_net_attach_def_whereabouts_list.append({'name': net_attach_def['name'],
                                                                     'namespace': net_attach_def['namespace']})
                        if 'name' in net_attach_def['config']:
                            temp_net_attach_def_whereabouts_list.append(
                                {'name': json.dumps(net_attach_def['config']['name']).strip('"'),
                                 'namespace': net_attach_def['namespace']})
        net_attach_def_whereabouts_list = self.remove_duplicate_list_items(temp_net_attach_def_whereabouts_list)
        return net_attach_def_whereabouts_list

    def get_pod_whereabouts_ip_list(self):
        pod_configs = self.gather_pod_configs()
        net_attach_def_whereabouts_list = self.get_net_attach_def_whereabouts_list()
        pod_whereabouts_ip_list = []
        for pod in pod_configs:
            for pod_network in pod['network']:
                for net_attach_def in net_attach_def_whereabouts_list:
                    if pod_network['name'] == net_attach_def['name'] and \
                            pod['namespace'] == net_attach_def['namespace']:
                        pod_whereabouts_ip_list.append({'name': pod['name'], 'namespace': pod['namespace'],
                                                        'ips': pod_network['ips']})
                    # This below if statement catches net-attach-def names that have the namespace/name format that
                    # NCS22 uses. Prior to NCS22 it just used name and not namespace in pod network-status annotations.
                    if pod_network['name'] == net_attach_def['namespace'] + '/' + net_attach_def['name']:
                        pod_whereabouts_ip_list.append({'name': pod['name'], 'namespace': pod['namespace'],
                                                        'ips': pod_network['ips']})
        return pod_whereabouts_ip_list

    def get_ippool_allocation_list(self):
        ippool_configs = self.gather_ippool_configs()
        ippool_allocation_list = []
        for ippool in ippool_configs:
            allocations = ippool['spec']['allocations']
            for allocation_number, allocation_data in list(allocations.items()):
                ippool_allocation_list.append({'name': ippool['name'], 'range': ippool['spec']['range'],
                                               'allocation_number': allocation_number,
                                               'allocation_data': allocation_data})
        return ippool_allocation_list

    @staticmethod
    def remove_duplicate_list_items(list_to_remove_duplicates):
        list_without_duplicates = []
        for list_item in list_to_remove_duplicates:
            if list_item not in list_without_duplicates:
                list_without_duplicates.append(list_item)

        return list_without_duplicates


class WhereaboutsDuplicateIPAddresses(WhereaboutsConfiguration):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._title = 'Validate that there are no duplicate whereabouts IP addresses.'
        self._failed_msg = 'TBD'
        self._severity = Severity.ERROR
        self._unique_operation_name = 'duplicate_whereabouts_IP_addresses'
        self._implication_tags = [ImplicationTag.RISK_GARBAGE_CLEANING_RECOMMENDED, ImplicationTag.APPLICATION_DOMAIN]

    def check_duplicate_ips(self):
        pod_whereabouts_ip_list = self.get_pod_whereabouts_ip_list()
        active_ip_list = []
        for pod in pod_whereabouts_ip_list:
            active_ip_list.extend(pod['ips'])
        duplicate_ip_list = [ip for i, ip in enumerate(active_ip_list) if ip in active_ip_list[:i]]
        temp_duplicate_ip_pod_list = []
        for duplicate_ip in duplicate_ip_list:
            for pod in pod_whereabouts_ip_list:
                if duplicate_ip in pod['ips']:
                    temp_duplicate_ip_pod_list.append({'name': pod['name'], 'namespace': pod['namespace'],
                                                       'ip': duplicate_ip})
        duplicate_ip_pod_list = self.remove_duplicate_list_items(temp_duplicate_ip_pod_list)
        results = []
        for pod in duplicate_ip_pod_list:
            results.append('--> Pod {namespace}/{name} has a duplicate IP {ip}'.format(namespace=pod['namespace'],
                                                                                       name=pod['name'],
                                                                                       ip=pod['ip']))
        return results

    def is_validation_passed(self):
        results = self.check_duplicate_ips()
        if results:
            self._failed_msg = 'Duplicate whereabouts IP addresses have been detected: \n {}'\
                .format('\n '.join(results))
            return False
        else:
            return True


class WhereaboutsMissingPodrefs(WhereaboutsConfiguration):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._title = 'Validate that there are no missing whereabouts podrefs in ippool allocations.'
        self._failed_msg = 'TBD'
        self._severity = Severity.ERROR
        self._unique_operation_name = 'missing_whereabouts_podrefs'
        self._implication_tags = [ImplicationTag.RISK_GARBAGE_CLEANING_RECOMMENDED]

    def get_missing_podref_ip_list(self):
        ippool_allocation_list = self.get_ippool_allocation_list()
        missing_podref_allocation_list = []
        for allocation in ippool_allocation_list:
            if 'podref' not in allocation['allocation_data']:
                missing_podref_allocation_list.append(allocation)
        missing_podref_ip_list = []
        for allocation in missing_podref_allocation_list:
            network = ipaddress.ip_network(allocation['range'], strict=False)
            missing_podref_ip_list.append(network[0] + int(allocation['allocation_number']))
        return missing_podref_ip_list

    def check_missing_podrefs(self):
        missing_podref_ip_list = self.get_missing_podref_ip_list()
        pod_whereabouts_ip_list = self.get_pod_whereabouts_ip_list()
        results = []
        for ip_missing_podref in missing_podref_ip_list:
            for pod in pod_whereabouts_ip_list:
                for pod_ip in pod['ips']:
                    if ip_missing_podref == ipaddress.ip_address(pod_ip):
                        results.append('--> Pod {pod_namespace}/{pod_name} has a missing podref for IP {pod_ip}'
                                       .format(pod_name=pod['name'],
                                               pod_namespace=pod['namespace'],
                                               pod_ip=pod_ip))
        return results

    def is_validation_passed(self):
        results = self.check_missing_podrefs()
        if results:
            self._failed_msg = 'Missing whereabouts podrefs in ippool allocations have been detected: \n {}'\
                .format('\n '.join(results))
            return False
        else:
            return True


class WhereaboutsMissingAllocations(WhereaboutsConfiguration):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._title = 'Validate that there are no missing whereabouts ippool allocations.'
        self._failed_msg = 'TBD'
        self._severity = Severity.ERROR
        self._unique_operation_name = 'missing_whereabouts_allocations'
        self._implication_tags = [ImplicationTag.RISK_GARBAGE_CLEANING_RECOMMENDED, ImplicationTag.APPLICATION_DOMAIN]

    def get_allocated_ip_list(self):
        ippool_configs = self.gather_ippool_configs()
        allocated_ip_list = []
        for ippool in ippool_configs:
            network = ipaddress.ip_network(ippool['spec']['range'], strict=False)
            for allocation in ippool['spec']['allocations']:
                allocated_ip_list.append(network[0] + int(allocation))
        return allocated_ip_list

    def get_missing_ip_allocation_pod_list(self):
        allocated_ip_list = self.get_allocated_ip_list()
        temp_missing_ip_allocation_pod_list = copy.deepcopy(self.get_pod_whereabouts_ip_list())
        for ippool_ip in allocated_ip_list:
            for pod in temp_missing_ip_allocation_pod_list:
                for pod_ip in pod['ips']:
                    if ipaddress.ip_address(pod_ip) == ippool_ip:
                        pod['ips'].remove(pod_ip)
        missing_ip_allocation_pod_list = []
        for pod in temp_missing_ip_allocation_pod_list:
            if pod['ips']:
                missing_ip_allocation_pod_list.append(pod)
        return missing_ip_allocation_pod_list

    def check_missing_ippool_allocations(self):
        missing_ip_allocation_pod_list = self.get_missing_ip_allocation_pod_list()
        results = []
        for pod in missing_ip_allocation_pod_list:
            if pod['ips']:
                for pod_ip in pod['ips']:
                    results.append('--> Pod {pod_namespace}/{pod_name} has a missing IP allocation for IP {pod_ip}'
                                   .format(pod_name=pod['name'],
                                           pod_namespace=pod['namespace'],
                                           pod_ip=json.dumps(pod_ip).strip('"')))
        return results

    def is_validation_passed(self):
        results = self.check_missing_ippool_allocations()
        if results:
            self._failed_msg = 'Missing whereabouts ippool allocations have been detected: \n {}'\
                .format('\n '.join(results))
            return False
        else:
            return True


class WhereaboutsExistingAllocations(WhereaboutsConfiguration):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._title = 'Validate that all whereabouts ippool allocations match their corresponding pod and pod IP.'
        self._failed_msg = 'TBD'
        self._severity = Severity.ERROR
        self._unique_operation_name = 'verify_existing_whereabouts_allocations'
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION, ImplicationTag.APPLICATION_DOMAIN]

    def verify_existing_ip_allocations(self):
        pod_whereabouts_ip_list = self.get_pod_whereabouts_ip_list()
        incorrect_ippool_allocation_list = self.get_ippool_allocation_list()
        for pod in pod_whereabouts_ip_list:
            for ip in pod['ips']:
                pod_ip = ipaddress.ip_address(ip)
                for allocation in incorrect_ippool_allocation_list:
                    allocation_ip = ipaddress.ip_network(allocation['range'], strict=False)[0] + \
                                    int(allocation['allocation_number'])
                    if pod_ip == allocation_ip:
                        if 'podref' in allocation['allocation_data']:
                            podref = json.dumps(allocation['allocation_data']['podref']).replace('"', '').split('/')
                            if podref[0] == pod['namespace'] and podref[1] == pod['name']:
                                incorrect_ippool_allocation_list.remove(allocation)
        results = []
        if incorrect_ippool_allocation_list:
            for allocation in incorrect_ippool_allocation_list:
                if 'podref' in allocation['allocation_data']:
                    results.append('--> Allocation in ippool {ippools_name} with allocation number {allocation_number} '
                                   'does not match the pod listed in its podref: {podref}'
                                   .format(ippools_name=allocation['name'],
                                           allocation_number=allocation['allocation_number'],
                                           podref=allocation['allocation_data']['podref']))
        return results

    def is_validation_passed(self):
        results = self.verify_existing_ip_allocations()
        if results:
            self._failed_msg = 'There is a problem with the following ippool allocations. These allocations do not ' \
                               'match their corresponding pod name and pod IP based on the allocation podrefs: \n {}'\
                .format('\n '.join(results))
            return False
        else:
            return True


#############################################################
##      https://jiradc2.ext.net.nokia.com/browse/ICET-1818
##      Author :  SOUVIK DAS
##      Date : 08-Aug-2023
##      Validate no overlapping nodes selectors in NexthopGroups
###############################################################

class VerifyNextHopGroupNodeSelectors(VerifyEgressGateway):
    objective_hosts = {
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER],
    }

    def set_document(self):
        self._unique_operation_name = "Verify_NextHopGroup_NodeSelectors"
        self._title = "Verify NodeSelectors NextHopGroup"
        self._failed_msg = "ERROR!! Some Edge Nodes are part of Multiple NextHopGroups->"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION, ImplicationTag.ACTIVE_PROBLEM]

    def get_repeating_edge_nodes(self,edge_nodes):
        _size = len(edge_nodes)
        repeating_edge_nodes_array = []
        for i in range(_size):
            k = i + 1
            for j in range(k, _size):
                if edge_nodes[i] == edge_nodes[j] and edge_nodes[i] not in repeating_edge_nodes_array:
                    repeating_edge_nodes_array.append(edge_nodes[i])
        return repeating_edge_nodes_array
    
    def is_validation_passed(self):
        egressgateway_list, egressgateway_namespace_list = self.get_egress_name_and_namespace()

        nexthopgroup_list, nexthops_list, nexthop_egress_dict = self.get_nexthopgroup_list(egressgateway_list, egressgateway_namespace_list)
        nexthops_ips_list = []
        nexthops_ips_list = self.get_nextHop_ips(nexthops_list)

        egress_gw_node_list, egress_gw_IP_list, neXtHopgroup_EgressNode_dict = self.get_egress_node_ip(nexthopgroup_list)
        Splitted_edge_nodes = []

        for egress_gw_node in egress_gw_IP_list:
            if len(egress_gw_node.split()) == 1:
                Splitted_edge_nodes.append(egress_gw_node)
            elif len(egress_gw_node.split()) > 1:
                egress_nodes = egress_gw_node.split()
                for node in egress_nodes:
                    Splitted_edge_nodes.append(node)

        repeating_edge_nodes_from_nexthops_nextHoproups = []

        all_edges_merged_nexthop_nexthopgroup = Splitted_edge_nodes + nexthops_ips_list

        if (len(all_edges_merged_nexthop_nexthopgroup))>1:
            repeating_edge_nodes_from_nexthops_nextHoproups = self.get_repeating_edge_nodes(all_edges_merged_nexthop_nexthopgroup)

        flag = 0
        if (repeating_edge_nodes_from_nexthops_nextHoproups):
            flag = flag +1
            self._failed_msg = self._failed_msg + "\n"

            for key, value in list(neXtHopgroup_EgressNode_dict.items()):
                for node in repeating_edge_nodes_from_nexthops_nextHoproups:
                    if (type(value) is list):
                        for item in value:
                            if node == item:
                                string = "NextHopGroup: " + str(key) + " is applied on node : " + str(item)
                                self._failed_msg = self._failed_msg + "\n" + string
                    else:
                        if node == value:
                            string = "NextHopGroup: " + str(key) + " is applied on node : " + str(value)
                            self._failed_msg = self._failed_msg + "\n" + string

            for key, value in list(nexthop_egress_dict.items()):
                for node in repeating_edge_nodes_from_nexthops_nextHoproups:
                    for item in value:
                        if node == item:
                            string = "Egressgateway with NEXTHOP " + str(key) + " is applied on node : " + str(node) + " | Other hops are :  " + str(value)
                            self._failed_msg = self._failed_msg + "\n" + string
        
        if flag == 0:
            return True
        else:
            return False


#############################################################
##      https://jiradc2.ext.net.nokia.com/browse/ICET-856
##      https://jiradc2.ext.net.nokia.com/browse/ICET-2134
##      Author :  NANDAGOPAL and SOUVIK DAS
##      Date : 15-01-2024
##      SYSCTL validation
###############################################################

class SysctlParameterDataCollector(DataCollector):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER]
    }

    def get_node_selector_values(self, line):
        whole_line = line.split()
        sysctl_name = whole_line[0].strip()
        pattern = r'map\[(.+)\]'
        match = re.search(pattern, line)
        if match:
            key = match.group(1)
            key_value_pair = key
        else:
            key = whole_line[1].strip()
            if key == "<none>" or key == "map[]":
                key_sysctl = "<none>"
                value_sysctl = "<none>"
                key_value_pair = key_sysctl + " " + value_sysctl
        return sysctl_name, key_value_pair

    def get_key_value_arrays(self, output_from_ocmmand):
        sysctl_name_array = []
        key_value_pair_array = []
        output_lines_array = output_from_ocmmand.strip().splitlines()
        for line in output_lines_array:
            sysctl_name, key_value_pair = self.get_node_selector_values(line)
            sysctl_name_array.append(sysctl_name)
            key_value_pair_array.append(key_value_pair)
        return sysctl_name_array, key_value_pair_array

    def collect_data(self):
        return_code, out, err = self.run_cmd("sudo /usr/local/bin/kubectl get sysctl -A -o=custom-columns='NAME:.metadata.name,SELECTOR:.spec.nodeSelector' | grep -v 'SELECTOR'", timeout=10)
        """
        Example:
        Suppose we have 1 systctl resource in NCS k8s cluster.

        Command :  kubectl get sysctl -A
        Outout:
        NAMESPACE   NAME         AGE
        default     sysctl-cmm   38m
 
        Command : sudo /usr/local/bin/kubectl get sysctl -A -o=custom-columns='NAME:.metadata.name,SELECTOR:.spec.nodeSelector' | grep -v 'SELECTOR'"

        Outout:
        sysctl-cmm   map[is_edge:true]
        """
        if return_code != 0:
            sysctl_name_array = []
            node_list_from_each_selectors = []
            sysctl_rules_list = []
        else:
            sysctl_name_array, key_value_pair_array = self.get_key_value_arrays(out)
            node_list_from_each_selectors = []
            node_list_temp = []
            for i in range(0, len(key_value_pair_array)):
                nodes_for_each_sysctl = ""
                if key_value_pair_array[i] != "<none> <none>":
                    node_selector_array = key_value_pair_array[i].split()
                    for node_selector in node_selector_array:
                        key = node_selector.split(":")[0].strip()
                        value = node_selector.split(":")[1].strip()
                        command_to_be_run="sudo /usr/local/bin/kubectl get nodes -l=" + key + "=" + value + " --no-headers"
                        out=self.get_output_from_run_cmd(command_to_be_run).strip()
                        node_list_temp = PythonUtils.get_node_list_from_selectors(out)
                        nodes_for_each_sysctl = nodes_for_each_sysctl + node_list_temp
                else:
                    command_to_be_run="sudo /usr/local/bin/kubectl get nodes --no-headers"
                    out=self.get_output_from_run_cmd(command_to_be_run).strip()
                    node_list_temp = PythonUtils.get_node_list_from_selectors(out)
                    nodes_for_each_sysctl = nodes_for_each_sysctl + node_list_temp

                node_list_from_each_selectors.append(nodes_for_each_sysctl)

            # get the sysctl Rules ..
            stream=self.get_output_from_run_cmd("sudo /usr/local/bin/kubectl get sysctl -A -o jsonpath='{.items[*].spec.sysctlRules}'")

            """
            Example:
            Suppose we have 1 systctl resource in NCS k8s cluster.

            Command :  kubectl get sysctl -A
            Outout:
            NAMESPACE   NAME         AGE
            default     sysctl-cmm   38m

            And The rules in the above SYSTCTL Resource is:

            spec:
                sysctlRules:
                - "net.core.rmem_max=4194304"
                - "net.core.wmem_max=4194304"
                - "kernel.sched_rt_runtime_us=-1"
                - "kernel.core_pattern=/var/crash/core.%p" 
 
            Command : sudo /usr/local/bin/kubectl get sysctl -A -o jsonpath='{.items[*].spec.sysctlRules}'
        
            Outout:
        
            ["net.core.rmem_max=4194304","net.core.wmem_max=4194304","kernel.sched_rt_runtime_us=-1","kernel.core_pattern=/var/crash/core.%p"]

            """
            sysctl_rules_list = stream.strip().split("]")

        return {"sysctl_name_array": sysctl_name_array, "node_list_from_each_selectors": node_list_from_each_selectors,
                "sysctl_rules_list": sysctl_rules_list}

class VerifySysctlParameters(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.MASTERS,Objectives.WORKERS,Objectives.EDGES],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.MASTERS,Objectives.WORKERS,Objectives.EDGES],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.MASTERS,Objectives.WORKERS,Objectives.EDGES]
    }
    def set_document(self):
        self._unique_operation_name = "verify_sysctl_parameters_configured_properely"
        self._title = "Validate Sysctl Parameter"
        self._failed_msg = "ERROR!! Missing sysctl parameter on kernel level"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]

    def replce_replace_chars(self, string):
        special_chars = "\\{}\"[]\'"
        modified = string
        for char in special_chars:
            modified = modified.replace(char,'')
        return modified

    def is_validation_passed(self):
        node_hostname=self.get_host_name()
        sysctl_dict = self.get_first_value_from_data_collector(SysctlParameterDataCollector)

        Error_flag = 0 ## Intially ALL GOOD so 0.. if WRONG then only flag=1
        
        if int(len(sysctl_dict["sysctl_name_array"])) > 0:
            for i in range(0, len(sysctl_dict["node_list_from_each_selectors"])):
                temp_nodes = str(sysctl_dict["node_list_from_each_selectors"][i]).split("|")
                for j in range (1, len(temp_nodes)):
                    modified_node = self.replce_replace_chars(str(temp_nodes[j]))
                    if (str(modified_node).strip() == node_hostname.strip()):
                        temp1=sysctl_dict["sysctl_rules_list"][i].split(",")

                        for z in range (0,len(temp1)):                        
                            temp2=str(temp1[z]).split("=")

                            final1 = self.replce_replace_chars(str(temp2[0]))
                            final2 = self.replce_replace_chars(str(temp2[1]))
                        
                            command_to_be_run="sudo /sbin/sysctl -a | grep -w '" + final1.strip() + " = " +  final2.strip() + "'" + " | wc -l"
                            sysctl_exists=self.get_output_from_run_cmd(command_to_be_run)
                            if (int(sysctl_exists.strip()) >0):
                                pass
                            else:
                                cmd = "sudo /sbin/sysctl " +  final1
                                sysctl_value = self.get_output_from_run_cmd (cmd).strip()
                                a = sysctl_value.split("=")
                                a1 = a[0].strip()
                                a2 = (a[1].strip()).split()
                                a3 = "$".join(a2)
                                b = a1 + "=" + a3
                                c = (final1.strip() + "=" + final2.strip()).strip()
                                d = c.split()
                                e = "$".join(d)
                                if b == e:
                                    pass
                                else:
                                    Error_flag = Error_flag + 1       ##BAD
                                    self._failed_msg = self._failed_msg + "\n\n" + "Sysctl Resource :  " + str(sysctl_dict["sysctl_name_array"][i]) + "\nNodes : " + str(sysctl_dict["node_list_from_each_selectors"][i]) + "\nIn k8s Syscltl resource config rules is :   " + final1 + "=" + final2 + "\nIn Host OS sysctl entry is :  " + sysctl_value
                    else:
                        pass
        
            if (int(Error_flag)==0):
                return True
            else:
                return False
        else:
            return True

########### SYSCTL Validation Code Ends #################

#############################################################
##      https://jiradc2.ext.net.nokia.com/browse/ICET-1927
##      Author :  SOUVIK DAS
##      Date : 10-Nov-2023
##      HealthCheck to warn BFD "Up to Down" events to prevent 
##      Egress and NextHopGroup instability issues in cluster
###############################################################

class ValidateBFDSessionStateUpDown(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "Validate_BFD_Session_State_Up_Down"
        self._title = "Validate BFD Session State Up Down"
        self._failed_msg = "ERROR!! BFD changed state from Up to Down"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]

    def is_validation_passed(self):
        cmd = "sudo kubectl get po -l app=ip-man -n ncms -o custom-columns=\":metadata.name,:status.phase\" --no-headers"
        exit_code, out, err = self.run_cmd(cmd)
        if not out or exit_code !=0:
            self._failed_msg = "No ip-man pods are running. System is in WRONG State"
            return False
        else:
            pod_status_array = out.strip().splitlines()
            if len(pod_status_array) != 0:
                flag = 0
                ip_man_pod_notRunning = 0
                for pod_and_status in pod_status_array:
                    output_split_array = pod_and_status.strip().split()
                    if output_split_array[1] == "Running":
                        running_pod = output_split_array[0].strip()
                        cmd_constant = "changed state from Up to Down"
                        cmd_to_be_used = "sudo kubectl logs -n ncms {} --since 48h|grep -i '{}'".format(running_pod,cmd_constant)
                        cmd = cmd_to_be_used + " | wc -l"
                        exit_code, out, err = self.run_cmd(cmd)
                        if exit_code != 0:
                            raise UnExpectedSystemOutput(self.get_host_name(), cmd, "", "Unable to get ip-man pod logs")
                        if int(out) != 0:
                            flag = flag + 1
                            cmd = cmd_to_be_used
                            out = self.get_output_from_run_cmd(cmd)
                            error_line = out.splitlines()[0]
                            self._failed_msg = self._failed_msg + "\nPOD -> " + running_pod + " |  Error Log = " + error_line
                    else:
                        ip_man_pod_notRunning = ip_man_pod_notRunning + 1
            else:
                self._failed_msg = "No ip-man pods are there in system. System is in WRONG State"
                return False
        
        if int(ip_man_pod_notRunning) != 0 and int(ip_man_pod_notRunning) == len(pod_status_array):
            self._failed_msg = "IP-MAN pods are there in system but NOT in Running state. System is in INCORRECT State"
            return False
        elif int(ip_man_pod_notRunning) != 0 and int(ip_man_pod_notRunning) != len(pod_status_array):
            self._failed_msg = self._failed_msg + "\n" + "Not all IP-MAN pods are in Running state. Check System Health"
        
        if flag == 0:
            return True
        else:
            return False

class CalicoIpamBlockStatus(Validator):
    # commentout du to false positive see ICET-2394
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER],
    }
    THRESHOLD_IN_PERCENTAGES = 80

    def set_document(self):
        self._unique_operation_name = "calico_ipam_block_filled"
        self._title = "Validate CALICO IP blocked allocated Is 80% filled"
        self._failed_msg = "Warning in calicoctl IPAM\n"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.RISK_RESOURCE_CLEANING_RECOMMENDED, ImplicationTag.APPLICATION_DOMAIN]

    def is_validation_passed(self):
        cmd = "sudo /usr/local/sbin/calicoctl ipam show --show-blocks"
        block_output = self.get_output_from_run_cmd(cmd)
        block_array = []
        ip_prefix = []
        block_usage = []
        for line in block_output.splitlines():
            if "Block" in line:
                block_array.append(line)
            if "IP Pool" in line:
                ip_prefix.append(line)
        #ip_prefix_text1 = str(ip_prefix).split("|")[2]
        #ip_prefix_text2 = ip_prefix_text1.split("/")[1]
        for pool in block_array:
            cells = pool.split("|")
            if len(cells) < 5:
                raise UnExpectedSystemOutput(ip=self._host_executor.ip,
                                             cmd=cmd,
                                             output=block_output,
                                             message='Invalid output, Please check manually')
            cell_of_intrest = cells[4]
            if "(" in cell_of_intrest and ")" in cell_of_intrest and "%" in cell_of_intrest:
                pass
            else:
                raise UnExpectedSystemOutput(ip=self._host_executor.ip,
                                             cmd=cmd,
                                             output=block_output,
                                             message='Invalid output, Please check manually')
            tall_value = cell_of_intrest.split("(")[1].split(")")[0].strip("%")
            if not tall_value.isnumeric():
                raise UnExpectedSystemOutput(ip=self._host_executor.ip,
                                                 cmd=cmd,
                                                 output=block_output,
                                                 message='Invalid output, Please check manually')
            tall_int_value = int(tall_value)
            if tall_int_value > CalicoIpamBlockStatus.THRESHOLD_IN_PERCENTAGES:
                block_usage.append(tall_int_value)
        if len(block_usage) > 0:
            self._failed_msg += "Following blocks have more than {}% IP usage, please clear unused IPS:\nCIDR: {}\n\ncalicoctl ipam table:\n{}".format(
                CalicoIpamBlockStatus.THRESHOLD_IN_PERCENTAGES,
                block_usage,
            block_output)

            return False
        return True


class CalicoIpamBlockPrefix(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER],
    }
    THRESHOLD_VALUE = 16

    def set_document(self):
        self._unique_operation_name = "calico_ipam_block_prefix_is_higher_than_16"
        self._title = "Validate CALICO IPAM block prefix for IPv4 is not higher than /16 subnet"
        self._failed_msg = "Small IP Block available for pod IP allocation, please see the pods requirements.\n"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]

    def is_validation_passed(self):
        cmd = "sudo /usr/local/sbin/calicoctl ipam show --show-blocks"
        block_output = self.get_output_from_run_cmd(cmd)
        ip_prefix = ""
        num_of_pools = 0
        for line in block_output.splitlines():
            if "IP Pool" in line:
                ip_with_subnet = line.split("|")[2]
                if ':' in ip_with_subnet:
                    continue
                num_of_pools = num_of_pools + 1
                ip_prefix = line

        if num_of_pools > 1:
            raise UnExpectedSystemOutput(self.get_host_ip(), cmd, block_output, "In NCS we support only single pool of IPv4")

        if len(ip_prefix.split("|")) < 3:
            raise UnExpectedSystemOutput(self.get_host_ip(), cmd, block_output, "Expected out put with '|' ")

        ip_with_subnet = ip_prefix.split("|")[2]
        if len(ip_with_subnet.split("/")) <2 :
                raise UnExpectedSystemOutput(self.get_host_ip(), cmd, block_output, "Expected out put with '/' ")
        subnet = ip_with_subnet.split("/")[1].strip()
        if not (subnet.isnumeric()):
            raise UnExpectedSystemOutput(self.get_host_ip(), cmd, block_output, "Expected numeric value in ip pool")

        if float(subnet) > self.THRESHOLD_VALUE:
            self._failed_msg  += "The following pool has subnet {} while it should be is smaller than {}:\n{}".\
                format(subnet, self.THRESHOLD_VALUE, ip_prefix)
            return False
        return True


#############################################################
##      https://jiradc2.ext.net.nokia.com/browse/ICET-2128
##      Author :  SOUVIK DAS
##      Date : 09-Jan-2024
##      Check if NCS CoreDNS can do IPv6 reverse lookups or not
###############################################################

class ValidateCoreDNSReverseLookupIPV6(NetworkNetConf):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "Validate_CoreDNS_Reverse_Lookup_IPV6"
        self._title = "Validate CoreDNS Reverse Lookup for IPV6"
        self._failed_msg = "ERROR!! CoreDNS Reverse Lookup for IPV6 Failed"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.SYMPTOM]

    def is_prerequisite_fulfilled(self):
        return self.is_ipv6()

    def is_validation_passed(self):
        ####################################################
        ### Sample Output can be : nslookup bcmt-api.ncms.svc
        ### Name:   bcmt-api.ncms.svc.cluster.local
        ### Address: 10.254.0.99
        ### Name:   bcmt-api.ncms.svc.cluster.local
        ### Address: fd01:abcd::9305
        ####################################################
        cmd = "sudo /bin/nslookup bcmt-api.ncms.svc"
        exit_code, out, err = self.run_cmd(cmd)

        ## IF NSLOOKUP Failed so Validation itself Failed
        if not out or exit_code !=0:
            self._failed_msg = " | nslookup bcmt-api.ncms.svc failed | "
            return False
        else:
            ipv4_ipv6_addresses = []
            ## ELSE NSLOOKUP Command fine. so Validation will Continue to
            ## Check FQDN Addresses and IP Address for bcmt-api.ncms.svc

            ## Get the IP Addresses (IPv4 or IPv6 Whatever) in array : ipv4_ipv6_addresses

            # Define the regex pattern to match IP addresses after "Name" line
            ip_pattern = re.compile(r'Name:[^\n]+(?:\n\s*Address: (\S+))+')

            # Find all matches in the output
            ipv4_ipv6_addresses = ip_pattern.findall(out)
            flag = 0
            failed_commands = []
            failed_commands_outputs = []
            #ipv4_ipv6_addresses Array Sample  = ["10.254.0.99","fd01:abcd::9305"]

            ## For each IP Addresses Check REVERSE DNS LOOKUP
            for address in ipv4_ipv6_addresses:
                cmd = "sudo /bin/nslookup {}".format(address).strip()
                exit_code, out, err = self.run_cmd(cmd)

                ## If NSLOOKUP Failed then RETURN CODE will be Non Zero in linux
                ## echo $?
                ## For each IP Addresses failure
                ## Get the Failed Command and output in an array
                if not out or exit_code !=0:
                    flag = flag + 1
                    failed_commands.append(cmd)
                    failed_commands_outputs.append(out)
                else:
                    pass
            ##  For each Failure we will print in Failed_MESSAGE
            if flag !=0:
                if len(failed_commands_outputs) !=0:
                    for i in range (0,len(failed_commands)):
                        self._failed_msg = self._failed_msg + "\n\n" + str(failed_commands[i]) + "\n\n" + str(failed_commands_outputs[i])
                else:
                    pass
                return False
            else:
                return True
            
#############################################################
##      https://jiradc2.ext.net.nokia.com/browse/ICET-2061
##      Author :  SOUVIK DAS
##      Date : 05-Feb-2024
##      Check for stale NodeEgressGateway resources
###############################################################

class ValidateStaleEgressGatewayNode(CheckEgressGateway):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "Validate_Stale_Egress_Gateway_Node"
        self._title = "Validate Stale EgressGateway Node"
        self._failed_msg = "ERROR!! Stale Nodes exist in EgressGateway Nodes"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.SYMPTOM]

    def is_validation_passed(self):
        cmd = "sudo /usr/local/bin/kubectl get nodeegressgateways.ncm.nokia.com --no-headers -A -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,NODE:.spec.node"

        """ SAMPLE OUTPUT
        default   egressgateway1-0   radegast-wrk-01
        default   egressgateway2-0   radegast-wrk-02
        default   egressgateway3-0   radegast-wrk-01
        default   egressgateway3-1   radegast-wrk-02
        default   egressgateway3-2   radegast-wrk-03
        default   egressgateway4-0   radegast-wrk-03
        """
        exit_code, out, err = self.run_cmd(cmd)

        if exit_code == 0:
            if out:
                rows = out.strip().split('\n')
                # Split each row into columns
                table_data = [row.split() for row in rows]

                # Transpose the table_data to get columns
                columns = list(zip(*table_data))

                # Split the columns into two separate arrays
                egress_gateway_namespace_list = list(columns[0])
                nodeegressgateway_list = list(columns[1])
                nodeegressgateway_node_list = list(columns[2])

                egressgateway_list = self.get_egressGateway_from_NodeEgress_list(nodeegressgateway_list)
            else:
                ### There is no NodeEgress Resources . Its OK
                return True
        else:
            self._failed_msg = "ERROR!! Could not run Kubectl nodeegressgateways command"
            return False

        cmd = "sudo /usr/local/bin/kubectl get node --no-headers -o custom-columns='NODE_NAME:.metadata.name'"

        """
        SAMPLE OUTPUT:
        radegast-ctrl-01
        radegast-ctrl-02
        radegast-ctrl-03
        radegast-edg-01
        radegast-edg-02
        radegast-wrk-01
        radegast-wrk-02
        ##### SUPPOSE radegast-wrk-03 Node REMOVED
        """
        exit_code, out, err = self.run_cmd(cmd)
        k8s_node_list = out.splitlines()
        failed_msg = ""
        if exit_code == 0:
            if len(k8s_node_list) !=0 :
                for i in range(0,len(nodeegressgateway_node_list)):
                    node = nodeegressgateway_node_list[i].strip()
                    flag = 0
                    for k8s_node in k8s_node_list:
                        if node == k8s_node.strip():
                            flag = 1
                        else:
                            pass

                    if flag == 0:
                        failed_msg = failed_msg + "\n" + "Stale Egress Gateway : '" + str(egressgateway_list[i]) + "' under namesapce : '" + str(egress_gateway_namespace_list[i]) + "' having stale Node (In k8s cluster Node does not exist) : '" + str(node) + "'"
            else:
                self._failed_msg = "ERROR!! K8S NODES NOT FOUND !!"
                return False
        else:
            self._failed_msg = "ERROR!! Could not run Kubectl command. K8S NODES NOT FOUND !!"
            return False

        if failed_msg !="":
            self._failed_msg = self._failed_msg + failed_msg
            return False
        else:
            return True


class ValidateUcControlPlaneIpEtcHosts(Validator):
    objective_hosts = [Objectives.UC]

    HOSTS_CMD = 'grep undercloud.ctlplane /etc/hosts'
    IP_CMD = '/sbin/ip a | grep br-ctlplane$'

    def set_document(self):
        self._unique_operation_name = "validate_ctlplane_ip_on_ucvm_etc_hosts"
        self._title = "Validation of correct ctlplane IP on /etc/hosts on UC VM"
        self._msg = "When the 'undercloud.ctlplane.localdomain undercloud.ctlplane' entry in /etc/hosts does not " \
                    "match the control plane IP of UC VM this can cause mysql bind issues affecting undercloud " \
                    "operations. \nNote that this is most likely an environmental issue when it occurs."
        self._failed_msg = "Control plane IP is not included in undercloud.ctlplane.localdomain undercloud.ctlplane " \
                           "on /etc/hosts on the UC VM."
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def _get_etc_hosts_entries(self):
        _, out, _ = self.run_cmd(self.HOSTS_CMD)
        out = out.splitlines()
        return out

    def _get_control_plane_ip(self):
        out = self.get_output_from_run_cmd(self.IP_CMD).splitlines()[0]     # excepts if no match for br-ctlplane IP

        ip_row_tokens = out.replace('/', ' ').split()
        if len(ip_row_tokens) < 2:
            raise UnExpectedSystemOutput(self.get_host_ip(), cmd=self.IP_CMD, output=out,
                                         message="Control plane IP could not be obtained.")

        return ip_row_tokens[1]

    def is_validation_passed(self):
        etc_hosts_entries = self._get_etc_hosts_entries()
        control_plane_ip = self._get_control_plane_ip()
        return_value = True

        for entry in etc_hosts_entries:
            if control_plane_ip not in entry:
                return_value = False
                self._failed_msg += ("\n    UC control plane IP '{}' is not on entry '{}'"
                                     .format(control_plane_ip, entry))
        return return_value


class ValidateCorrectNetconfig(Validator):
    objective_hosts = {Deployment_type.NCS_OVER_BM: [Objectives.ALL_NODES]}

    def is_prerequisite_fulfilled(self):
        if gs.is_ncs_central() and Objectives.MANAGERS in self._host_executor.roles:
            return False
        return True

    def set_document(self):
        self._unique_operation_name = "validate_correct_netconfig"
        self._title = "Validation of correct netconfig"
        self._failed_msg = ""
        self._severity = Severity.NOTIFICATION
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        cmd = "sudo os-net-config --noop --detailed-exit-codes -c /etc/os-net-config/config.json 2>/dev/null"
        return_code, out, err = self.run_cmd(cmd, timeout=60)

        if return_code == 0:
            return True

        if return_code != 2:
            raise UnExpectedSystemOutput(self.get_host_ip(), cmd, out + err, "Expected to get exit code 0 for success, "
                                                                             "2 for not success, got: {}".format(
                return_code))

        bad_files = re.findall(r"File: (.*)", out)

        if not bad_files:
            raise UnExpectedSystemOutput(self.get_host_ip(), cmd, out + err, "Expected to get the bad files in out.")

        self._failed_msg = "Bad configuration for files: {}\n" \
                           "Please do not run Post Install Changes for Ingress Networks".format("\n".join(bad_files))

        return False



class CheckIptablesForManuallyAddedRules(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.MASTERS, Objectives.WORKERS, Objectives.EDGES],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.MASTERS, Objectives.WORKERS, Objectives.EDGES]
    }

    base_command = ("sudo iptables-save | grep -Ev 'cali|CNI|NETAVARK|KUBE|docker|DOCKER|IP-MAN|BCMT|zabbix|Zabbix|:INPUT"
                    "|:FORWARD|:OUTPUT|:PREROUTING|:POSTROUTING|COMMIT|#|\\*filter|\\*nat|\\*mangle|\\*raw|\\*security|"
                    "drop_optional_ip_headers|\\-i lo|u32|bpf|NodeLocal DNS Cache")

    # spaces intentionally left before/after ports less than or equal to 6553 to prevent partial port matches
    # some port matches contain commas due to multiple ports declared in iptables rules
    # IMPORTANT - if ports/phrases are ever added here, make sure to also add to validation's Confluence page
    cna_control_add = "| 5000 | 2380 | 2379 "
    cnb_base_add = "|cbis-INPUT|8787|7300|6800|6789| 3300 | 3300,| 1701 | 123 "
    cnb_control_add = ("|Alarm manager trap|Dashboards access|Elasticsearch communication|Grafana Port|IndexSearch "
                       "communication|Kibana access|vmauth port|61400|61399|38765|26379|20048|13808|7000| 6385 | 6379 |"
                       " 6379,| 5601 | 5000 | 2380 | 2379 | 2049 |,2049,| 1995 | 623 | 546 | 547 | 443 | 443,| 162 |"
                       " 111 | 111,| 80 |,80 | 22 | 9443 ")

    # AIM: Application & Infrastructure Monitoring
    # https://nokia.sharepoint.com/sites/test-automation-tools-team
    default_aim_ports_add = "|11235|11234'"
    default_aim_ports_control_add = "|27017|26543|14369|13456|11235|11234|9990| 6543 '"

    def set_document(self):
        self._unique_operation_name = "check_iptables_for_manually_added_rules"
        self._title = "Check Iptables for Manually Added Rules"
        self._failed_msg = "Manually added and/or non-default active iptables rules detected:"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]

    def filter_out_known_iptables_ports_and_phrases(self, deployment_type, host_roles):
        if deployment_type == Deployment_type.NCS_OVER_BM:
            if Objectives.MASTERS in host_roles:
                final_command = (self.base_command + self.cnb_base_add + self.cnb_control_add +
                                 self.default_aim_ports_control_add)
            else:
                final_command = self.base_command + self.cnb_base_add + self.default_aim_ports_add
        else:
            if Objectives.MASTERS in host_roles:
                final_command = self.base_command + self.cna_control_add + self.default_aim_ports_control_add
            else:
                final_command = self.base_command + self.default_aim_ports_add
        rc, out, err = self.run_cmd(final_command)
        return out

    def filter_out_known_complex_iptables_rules(self, iptables_results, host_roles):
        cnb_master_ncs20_regex = ['-A INPUT -m state --state RELATED,ESTABLISHED -j ACCEPT',
                                  '-A INPUT -m conntrack --ctstate INVALID -j DROP',
                                  '-A FORWARD -o .* -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT',
                                  '-A FORWARD -i .* ! -o .* -j ACCEPT',
                                  '-A FORWARD -i .* -o .* -j ACCEPT',
                                  '-A POSTROUTING -o .* -m addrtype --src-type LOCAL -j MASQUERADE',
                                  '-A POSTROUTING -s .* ! -o .* -j MASQUERADE']

        ncs_cli_keepalived_snat_regex = '-A POSTROUTING -o .* -j SNAT --to-source .*'

        iptables_results = iptables_results.splitlines()
        if Objectives.MASTERS in host_roles:
            for regex_rule in cnb_master_ncs20_regex:
                iptables_results = [result for result in iptables_results if not re.match(regex_rule, result)]
        elif Objectives.EDGES in host_roles:
            iptables_results = [result for result in iptables_results if not re.match(ncs_cli_keepalived_snat_regex,
                                                                                      result)]
        return iptables_results

    def is_validation_passed(self):
        deployment_type = sys_param.get_deployment_type()
        host_roles = self.get_host_roles()
        iptables_results = self.filter_out_known_iptables_ports_and_phrases(deployment_type, host_roles)
        if not iptables_results:
            return True
        iptables_results = self.filter_out_known_complex_iptables_rules(iptables_results, host_roles)
        if iptables_results:
            self._failed_msg += '\n{}'.format('\n'.join(iptables_results))
            return False
        else:
            return True


class ValidateSelinuxContextDirIstio(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.MASTERS, Objectives.WORKERS, Objectives.EDGES],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.MASTERS, Objectives.WORKERS, Objectives.EDGES]
    }

    CHECK_DIR_CONTEXT_CMD = "sudo ls {} /opt/cni | grep bin"
    CHECK_CON_CMD = "sudo bzcat #PATH# | grep 'allow.*#TYPE#.*file.*rename'"
    CONTEXT_PATH = "#DIR#selinux/targeted/active/modules/400/bcmt_istio/cil"

    def set_document(self):
        self._unique_operation_name = "validate_selinux_context_dir_istio"
        self._title = "Validation of correct SELinux context being used for /opt/cni/bin directory when using istio"
        self._msg = ""
        self._failed_msg = "Wrong SELinux context for /opt/cni/bin directory."
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_prerequisite_fulfilled(self):
        """Only test when using istio"""
        return _is_istio_used(self)


    def _get_context_type_from_ls(self, ls_output, cmd=""):
        """
        Receives an entry like this and obtains the selinux context type from it:
        unconfined_u:object_r:usr_t:s0 bin
        Context type is: usr_t in this example
        """

        try:
            context_type = ls_output.split()[0].split(':')[2]
        except IndexError:
            raise UnExpectedSystemOutput(ip=self._host_executor.ip, cmd=cmd, output=ls_output,
                                         message='Getting selinux context type for /opt/cni/bin failed')
        return context_type

    @staticmethod
    def _get_context_dir_based_on_version():
        ncs_version = sys_parameters.get_version()

        if ncs_version >= Version.V23_10:
            return "/var/lib/"      # 23.10, 24.7
        elif Version.V22_12 >= ncs_version >= Version.V22_7:
            return "/etc/"          # 22.7, 22.12

    def _get_selinux_context_line(self):
        return self.get_output_from_run_cmd(self.CHECK_DIR_CONTEXT_CMD).splitlines()[0]

    def _filter_allow_rule(self, context_dir, context_type):
        check_context_cmd = self.CHECK_CON_CMD.replace("#PATH#", context_dir).replace("#TYPE#", context_type)
        rc, out, _ = self.run_cmd(check_context_cmd)
        if rc != 0:
            return []
        return out.splitlines()

    def is_validation_passed(self):
        if 'centos' in self.system_utils.get_operating_system_type().lower():
            self.CHECK_DIR_CONTEXT_CMD = self.CHECK_DIR_CONTEXT_CMD.format('--scontext')
        else:
            self.CHECK_DIR_CONTEXT_CMD = self.CHECK_DIR_CONTEXT_CMD.format('--context')
        context_out = self._get_selinux_context_line()
        context_type = self._get_context_type_from_ls(context_out, self.CHECK_DIR_CONTEXT_CMD)

        if context_type != "usr_t":
            context_dir = self._get_context_dir_based_on_version()
            context_dir = self.CONTEXT_PATH.replace("#DIR#", context_dir)
            matching_rules = self._filter_allow_rule(context_dir, context_type)
            if len(matching_rules) == 0:
                self._failed_msg = "\nContext type: '{}' does not have the file rename permission on '{}'".format(
                    context_type, context_dir)
                return False
        return True


class VerifyUnmanagedDeviceList(Validator):
    objective_hosts = [Objectives.ALL_NODES]

    def set_document(self):
        self._unique_operation_name = "verify_network_manager_unmanaged_devices"
        self._title = "Verify NetworkManager unmanaged devices"
        self._failed_msg = ""
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]
        self._is_clean_cmd_info = True

    def is_validation_passed(self):
        unmanaged_devices_conf_file = "/etc/NetworkManager/conf.d/calico.conf"
        """
        SAMPLE OUTPUT >>>>>
        [keyfile]
        unmanaged-devices=interface-name:cali*;interface-name:tunl*;interface-name:vxlan.calico
        """
        if not self.file_utils.is_file_exist(unmanaged_devices_conf_file):
            msg = "Failed to find {}".format(unmanaged_devices_conf_file)
            raise UnExpectedSystemOutput(self.get_host_ip(), "",
                                         "", msg)
        cmd = "sudo cat {}".format(unmanaged_devices_conf_file)
        out = self.get_output_from_run_cmd(cmd).strip().split('\n')
        output = out[1].strip().split(';')
        flg_is_bad_interfaces_found = False
        if 'interface-name:*' in output:
            self._failed_msg += "'interface-name:*' present in unmanaged devices list"
            flg_is_bad_interfaces_found = True
        return not flg_is_bad_interfaces_found


#https://jiradc2.ext.net.nokia.com/browse/ICET-1875
class VerifyBFDSessionOutput(CheckEgressGateway):
    objective_hosts = {
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "verify_bfd_session_age"
        self._title = "Verify the age of BFD sessions in 'bcmt-ip-man-agent' pods"
        self._failed_msg = "Error!! BFD Session is Wrong!!\n"
        self._severity = Severity.NOTIFICATION
        self._implication_tags = [ImplicationTag.NOTE]

    def get_bfd_session_output(self, pod_list):
        pods_with_since = {}
        for pod_name in pod_list:
            since_values = []
            # Get the BFD session output from "bcmt-ip-man-agent" PODs running in the EDGE nodes
            exit_code, out, err = self.run_cmd(
                "sudo /usr/local/bin/kubectl exec -n ncms {} -- birdcl -s /var/run/ip-man/bird/bird.ctl show bfd sessions".format(pod_name))
            if exit_code == 0:
                if 'SINCE' in out.upper():
                    pods_with_since[pod_name] = []
                    lines = (out.strip()).splitlines()
                    total_since_length = len(lines)
                    for index, line in enumerate(lines):
                        if "SINCE" in (line.upper()):
                            ## Take the cell number dynamically
                            since_line_bfd_index = index + 1
                            break
                    for j in range(since_line_bfd_index, total_since_length):
                        since_value = lines[j].split()[3]
                        since_values.append(since_value)
                    pods_with_since[pod_name] = since_values
        return pods_with_since

    def validate_time(self, since_time, today_time):
        today_date = str(today_time).strip().split()[0]
        since_date_time = today_date + " " + since_time
        # Convert since_value string representation to datetime objects
        since_value_in_datetime = datetime.strptime(since_date_time, "%Y-%m-%d %H:%M:%S.%f")
        time_difference = today_time - since_value_in_datetime
        if time_difference.days >= 0:
            # Time difference will be in TIME format so Splitting the time difference into hours, minutes, and seconds
            hours, minutes, seconds = list(map(float, str(time_difference).split(':')))
            # Convert hours, minutes, and seconds into seconds
            total_seconds = hours * 3600 + minutes * 60 + seconds
            # Check if the time difference is less than 1 hour , Severity will be ERROR
            if total_seconds < 3600:
                self._severity = Severity.ERROR
                return False

            # Check if the time difference is greater than 1 hour but less than 24 hours , Severity will be Warning
            elif 3600 < total_seconds < 24 * 3600:
                if self._severity != Severity.WARNING and self._severity != Severity.ERROR:
                    self._severity = Severity.WARNING
                return False
        return True

    def validate_date_time(self, pods_with_since_dict):
        status = True
        today_time = datetime.now()
        for pod_name, since_values in list(pods_with_since_dict.items()):
            if not since_values:
                status = False
                self._failed_msg += "\nPod '{}': BFD session is there but NO SINCE Value is present!! - WRONG Configuration!! ".format(pod_name)
            else:
                for since_value in since_values:
                    time_regex = r'(\d{2}):(\d{2}):(\d{2}\.\d{3})'
                    date_regex = r'(\d{4})-(\d{2})-(\d{2})'

                    if re.match(date_regex, since_value):
                        continue
                    elif re.match(time_regex, since_value):
                        time_status = self.validate_time(since_value, today_time)
                        if time_status is False:
                            status = False
                            if pod_name not in self._failed_msg:
                                self._failed_msg += "\nPod '{}': BFD Sessions are running less than 24 hours".format(pod_name)
                    else:
                        status = False
                        self._failed_msg += "\nPod '{}': Invalid Since format - Since value is '{}', expected to be in format '{}' or '{}'".format(pod_name, since_value, time_regex, date_regex)
        return status

    def is_prerequisite_fulfilled(self):
        return self.get_relevant_egress_gw_node_list()

    def get_relevant_egress_gw_node_list(self):
        egressgateway_list, egressgateway_namespace_list = self.get_egress_name_and_namespace()
        nexthopgroup_list, nexthops_list, nexthop_egress_dict = self.get_nexthopgroup_list(egressgateway_list,
                                                                                           egressgateway_namespace_list)
        relevant_egress_gw_node_list, egress_gw_ip_list, next_hop_egress_node_dict = self.get_egress_node_ip(nexthopgroup_list)
        return relevant_egress_gw_node_list

    def is_validation_passed(self):
        relevant_egress_gw_node_list = self.get_relevant_egress_gw_node_list()
        final_edge_list= []
        for edge_entries in relevant_egress_gw_node_list:
            splitted_edge_entries = edge_entries.split()
            for edge_node_name in splitted_edge_entries:
                if edge_node_name not in final_edge_list:
                    final_edge_list.append(edge_node_name)
        edges_node_list = "|".join(final_edge_list)
        edges_node_list = "'" + edges_node_list + "'"
        cmd = "sudo /usr/local/bin/kubectl get po -o wide -l bcmt-ip-man=agent -n ncms | grep 'Running' | grep -E " + edges_node_list
        exit_code, out, err = self.run_cmd(cmd.strip())
        if exit_code == 0:
            pod_list = []
            for line in out.splitlines():
                pods_name = line.split()[0]
                pod_list.append(pods_name)

            pods_with_since_dict = self.get_bfd_session_output(pod_list)
            if pods_with_since_dict:
                return self.validate_date_time(pods_with_since_dict)

            return True
        else:
            self._failed_msg = "Error !! Either bcmt-ip-man-agent pods are not running or KUBECTL Command failed to execute !!"
            return False



def _is_istio_used(self):
    _, istio_version_res = self.run_data_collector(IstioVersion)
    if len(list(istio_version_res.values())) >= 1 and len(list(list(istio_version_res.values())[0].values())) >= 1:
        istio_version = list(list(istio_version_res.values())[0].values())[0]  # for first node (master), first and only id
    else:
        raise UnExpectedSystemOutput(ip=self._host_executor.ip, cmd='', output='',
                                         message='Failed to obtain istio version from data collector\n')

    if '---' not in istio_version:  # if not '----', then valid version, it is installed!
        return True
    return False


def _is_istio_cni_node_present(self):
    ncs_version = Version.get_version_name(sys_parameters.get_version())
    if ncs_version < Version.V22:
        helmre = self.get_output_from_run_cmd('sudo helm list --output json')
    else:
        helmre = self.get_output_from_run_cmd('sudo helm list --output json -A')
    helm_releases_unicode = json.loads(helmre)
    flag = False
    for release in helm_releases_unicode:
        if 'istio-cni-node' in release['name']:
            flag = True
    return flag



class VerifyIstioPluginFileExists(Validator):
    objective_hosts = [Objectives.MASTERS,Objectives.EDGES,Objectives.WORKERS]

    def is_prerequisite_fulfilled(self):
        return _is_istio_used(self) and _is_istio_cni_node_present(self)
    def set_document(self):
        self._unique_operation_name = "verify_istio_plugin_file_exists"
        self._title = "Verify If Istio Plugin File Exists"
        self._failed_msg = ""
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.APPLICATION_DOMAIN]


    def is_validation_passed(self):
        filepath = "/opt/cni/bin/istio-cni"
        if not self.file_utils.is_file_exist(filepath):
            return False
        return True

class VerifyMellanoxVFNumber(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.WORKERS, Objectives.EDGES]
    }

    def _init_instance_variables(self):
        self.sriov_config_from_cluster_config = self.get_sriov_config_from_cluster_config()
        self.sriov_config_from_server = self.get_sriov_config_from_server()

    def set_document(self):
        self._unique_operation_name = "verify_mellanox_vf_number"
        self._title = "Verify Mellanox VF Number"
        self._failed_msg = "The number of SRIOV virtual functions does not match the hostgroup configuration:"
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.APPLICATION_DOMAIN,
                                  ImplicationTag.RISK_BAD_CONFIGURATION]
        self._severity = Severity.CRITICAL

    def get_sriov_config_from_cluster_config(self):
        cluster_config = sys_param.get_base_conf()
        hostname = self.get_output_from_run_cmd('/usr/bin/hostname').replace('\n', '')
        sriov_key = 'cbis::my_host_group::interface_mapping::caas_sriov_mapping'
        try:
            sriov_config_from_cluster_config = cluster_config['hosts'][hostname]['hieradata']['my_host_group'][sriov_key]
            return sriov_config_from_cluster_config
        except KeyError as e:
            error_msg = "Config Entry Key Error: {}".format(str(e))
            raise UnExpectedSystemOutput(self.get_host_ip(), cmd="", output="", message=error_msg)

    def get_sriov_config_from_server(self):
        sriov_config_from_server = []
        for port in self.sriov_config_from_cluster_config:
            sriov_config_from_server.append({'port': port['port']})
        for port in sriov_config_from_server:
            cmd = '/usr/bin/cat /sys/class/net/{}/device/sriov_totalvfs'.format(port['port'])
            return_code, out, err = self.run_cmd(cmd)
            if not return_code:
                port['total_num_of_vfs'] = int(out)
            else:
                port['total_num_of_vfs'] = 0
            cmd = '/usr/bin/cat /sys/class/net/{}/device/sriov_numvfs'.format(port['port'])
            return_code, out, err = self.run_cmd(cmd)
            if not return_code:
                port['active_num_of_vfs'] = int(out)
            else:
                port['active_num_of_vfs'] = 0
        return sriov_config_from_server

    def is_nic_mellanox(self):
        cmd = "/sbin/lspci | grep Ethernet"
        lspci_out = self.get_output_from_run_cmd(cmd)
        if 'Mellanox' in lspci_out:
            return True
        else:
            return False

    def is_sriov_enabled(self):
        for port in self.sriov_config_from_cluster_config:
            if port['num_of_vfs']:
                return True
            else:
                return False

    def are_vf_numbers_inconsistent(self):
        are_inconsistent = False
        for cluster_config_port in self.sriov_config_from_cluster_config:
            for server_port in self.sriov_config_from_server:
                if cluster_config_port['port'] == server_port['port']:
                    if cluster_config_port['num_of_vfs'] != server_port['total_num_of_vfs']:
                        cluster_config_port['wrong_total_num_of_vfs'] = server_port['total_num_of_vfs']
                        are_inconsistent = True
        return are_inconsistent

    def is_validation_passed(self):
        self._init_instance_variables()
        if not self.is_nic_mellanox() or not self.is_sriov_enabled() or not self.are_vf_numbers_inconsistent():
            return True
        for port in self.sriov_config_from_cluster_config:
            if 'wrong_total_num_of_vfs' in port and port['wrong_total_num_of_vfs']:
                self._failed_msg += ('\nPort {} has wrong number of total vfs. Current total: {}. Hostgroup total: {}'
                                     .format(port['port'], port['wrong_total_num_of_vfs'], port['num_of_vfs']))
        is_implication_tags_change = False

        for port in self.sriov_config_from_server:
            if port['total_num_of_vfs'] != 0 and port['active_num_of_vfs'] == 0:
                self._failed_msg += ('\nPort {} has 0 active vfs!'.format(port['port']))
            elif port['total_num_of_vfs'] != 0 and port['active_num_of_vfs'] != 0:
                self._severity = Severity.WARNING

                if not is_implication_tags_change:
                    is_implication_tags_change = True
                    self._implication_tags.remove(ImplicationTag.ACTIVE_PROBLEM)
                    self._implication_tags.remove(ImplicationTag.APPLICATION_DOMAIN)
        return False


class SysctlVlanForwarding(Validator):
    objective_hosts = {Deployment_type.NCS_OVER_BM: [Objectives.EDGES]}

    def set_document(self):
        self._unique_operation_name = "sysctl_vlan_forwarding_parameter_validation"
        self._title = "Verify sysctl Vlan forwarding parameter"
        self._failed_msg = "Vlan forwarding entries on sysctl should be set with default value '1'.\n" \
                           "The following vlan forwarding entries have a different value:\n"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION , ImplicationTag.APPLICATION_DOMAIN]

    def is_validation_passed(self):
        problematic_vlan_forwarding = []
        #Using grep in cmd instead of grep function , because of -E option.
        cmd = "sudo sysctl -a |grep -E 'net.ipv4.conf.vlan[0-9]+.forwarding'"
        exit_code, out, err = self.run_cmd(cmd)
        out = out.strip().split("\n")
        if exit_code == 0 and out:
            for line in out:
                result = line.split('=')
                if len(result) != 2:
                    raise UnExpectedSystemOutput(self.get_host_ip(), cmd, out, message="Expected entry in following format:\n"
                                                                                       "net.ipv4.conf.vlan96.forwarding = 0")
                if int(result[1]) != 1:
                    problematic_vlan_forwarding.append(line)
        if problematic_vlan_forwarding:
            self._failed_msg += "{}".format("\n".join(problematic_vlan_forwarding))
            return False
        #If empty response, exit_code is 1 so we are returning True as response is empty and nothing to validate.
        return True


class VerifyStaleResource(CheckEgressGateway, K8sValidation):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER]
    }

    def stale_resource_list(self, resource):
        cmd = "sudo /usr/local/bin/kubectl get {} --no-headers -A -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,NODE:.spec.node".format(resource)
        stale_resources = []
        exit_code, out, err = self.run_cmd(cmd)
        if exit_code == 0:
            if out:
                out = out.splitlines()
                formatted_out = []
                # converting output to below format:
                # [[u'default', u'defaultroute-0', u'fi845a-fi845a-edgebm-0'],[u'default', u'defroute-0', u'fi845a-fi845a-edgebm-0']]
                for line in out:
                    formatted_out.append(line.split())
                nodes_list = self.get_nodes_only()
                for line in formatted_out:
                    if line[2] not in nodes_list:
                        stale_resources.append(line)
                return stale_resources
        return stale_resources


class ValidateStaleStaticRouteConfig(VerifyStaleResource):
    def set_document(self):
        self._unique_operation_name = "validate_stale_static_route_config"
        self._title = "Validate Stale Static Route Config"
        self._failed_msg = "Below stale staticrouteconfigs resources are present in cluster:"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.SYMPTOM, ImplicationTag.RISK_GARBAGE_CLEANING_RECOMMENDED]

    def is_validation_passed(self):
        output = self.stale_resource_list(resource='staticrouteconfigs')
        if len(output) > 0:
            self._failed_msg += "\n{}".format('\n'.join('-'.join(line) for line in output))
            return False
        return True


class ValidateStaleNextHops(VerifyStaleResource):
    def set_document(self):
        self._unique_operation_name = "validate_stale_next_hops"
        self._title = "Validate Stale Next Hops"
        self._failed_msg = "Below stale nexthops.ncm.nokia.com resources are present in cluster:"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.SYMPTOM, ImplicationTag.RISK_GARBAGE_CLEANING_RECOMMENDED]

    def is_validation_passed(self):
        output = self.stale_resource_list(resource='nexthops.ncm.nokia.com')
        if len(output) > 0:
            self._failed_msg += "\n{}".format('\n'.join('-'.join(line) for line in output))
            return False
        return True

class GetIPDetailsFromControllers(DataCollector):
    objective_hosts = [Objectives.CONTROLLERS]

    def collect_data(self, router_id):
        cmd = "sudo ip netns exec qrouter-{} hostname -I".format(router_id)
        router_ip = self.get_output_from_run_cmd(cmd, timeout=60, add_bash_timeout=True)
        router_ip = router_ip.splitlines()[0]
        return router_ip

class VerifyRouterIPActiveStatus(Validator):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "verify_router_ip_active_status"
        self._title = "Check router IP active status in controllers"
        self._failed_msg = "Mentioned Virtual router IP is active on more than one controller:"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM ,ImplicationTag.APPLICATION_DOMAIN]

    def is_validation_passed(self):
        router_list_cmd = "source {}; openstack router list  --column ID -f value".format(self.system_utils.get_overcloudrc_file_path())
        router_list = self.get_output_from_run_cmd(router_list_cmd)
        router_list = router_list.splitlines()
        if router_list:
            duplication_ip_list = []
            for router in router_list:
                router_ip_details_in_dict = self.run_data_collector(GetIPDetailsFromControllers, router_id=router)
                #we get get_ip_details_from_dict out like this [u'169.254.193.164 ', u'169.254.194.53 ', u'169.254.194.122 169.254.0.14 ']
                get_ip_details_from_dict = list(router_ip_details_in_dict.values())
                if None in get_ip_details_from_dict:
                    raise UnExpectedSystemOutput(self.get_host_ip(), "", "", "data collector returned None value")
                #we convert it to [u'169.254.194.122 169.254.0.14 ', u'169.254.193.164 ', u'169.254.194.53 ']
                split_ip_to_list = [ip.strip() for value in get_ip_details_from_dict for ip in value.split()]
                if len(split_ip_to_list) != len(set(split_ip_to_list)):
                    for ip in set(split_ip_to_list):
                        if split_ip_to_list.count(ip) > 1:
                            duplication_ip_list.append(ip)
            if len(duplication_ip_list) > 0:
                self._failed_msg += " {}".format(" ".join(duplication_ip_list))
                return False
        return True

