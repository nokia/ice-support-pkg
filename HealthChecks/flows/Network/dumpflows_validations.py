from __future__ import absolute_import
import xml.etree.ElementTree as ET
from itertools import chain

from HealthCheckCommon.operations import *
from HealthCheckCommon.validator import InformatorValidator
from HealthCheckCommon.table_system_info import TableSystemInfo
from flows.OpenStack.openstack_utils_data_collector import OpenstackUtilsDataCollector
from flows.Network.dump_flows_info import DumpFlowsInfoOperator
from tools.lazy_global_data_loader import *


class FlowsDataCollector(DataCollector, DumpFlowsInfoOperator):
    objective_hosts = [Objectives.CONTROLLERS, Objectives.COMPUTES]

    def get_table20_flows(self):
        output = self.exec_dumpflow('br-tun', 20)
        rules = []
        rex = re.compile(r'.*priority=(\d+),.*dl_dst=(\S+).*load:(0x[a-zA-Z0-9]+).*output:(\d+)')
        for line in output.splitlines():
            if rex.match(line):
                priority, mac, vlan, output = rex.match(line).groups()
                rules.append({'priority': priority, 'mac': mac, 'vlan': vlan, 'output': output})
        return rules

    def get_arp(self):
        output = self.exec_dumpflow('br-tun', 21)
        arp = []
        rex = re.compile(r'.*arp_tpa=(\S+).*mod_dl_src:(\S+),')
        for line in output.splitlines():
            if rex.match(line):
                ip, mac = rex.match(line).groups()
                arp.append((mac, ip))
        return arp

    def collect_data(self):
        flows = []
        if not self.is_br_tun_bridge_exist():
            return []
        arp_table = self.get_arp()
        interfaces = self.get_interfaces()
        for flow in self.get_table20_flows():
            output = flow['output']
            mac = flow['mac']
            vlan = self.convert_hex_to_decimal(flow['vlan'])
            matching_interfaces = [x for x in interfaces if str(x['ofport']) == output]
            if len(matching_interfaces) == 0:
                port_name = None
                local_ip = None
                remote_ip = None
            else:
                remote_ip = matching_interfaces[0]['options']['remote_ip']
                local_ip = matching_interfaces[0]['options']['local_ip']
                port_name = matching_interfaces[0]['name']

            # Get ARP IP - return the first match. While there can be multiple
            # IPs mapped to the same MAC address, we don't expect to see this
            # in a CBIS environment
            arp_ip = None
            for m, ip in arp_table:
                if m == mac:
                    arp_ip = ip
                    break
            flows.append(
                {'mac': mac, 'ip': arp_ip, 'vlan': vlan, 'remote_ip': remote_ip, 'local_ip': local_ip, 'output': output,
                 'port_name': port_name})

        # Remove duplicate flows - some flows have the same mac, vlan, output
        # but have different priority/actions
        flows = [dict(t) for t in {tuple(sorted(d.items())) for d in flows}]
        return flows


class UnicastDumpFlows(DumpFlowsInfoOperator, InformatorValidator):
    objective_hosts = [Objectives.UC]
    hypervisors = None
    mac_addresses = None
    flows = None
    counter = None
    states_flows_dict = None

    def set_document(self):
        self._unique_operation_name = "unicast_dump_flows"
        self._title = "unicast dump flows"
        self._system_info = ""
        self._table_system_info = TableSystemInfo(table=[], remarks="")
        self._failed_msg = ""
        self._is_clean_cmd_info = True
        self._title_of_info = "unicast dump flows"
        self._is_pure_info = True
        self._severity = Severity.NA
        self._implication_tags = [ImplicationTag.RISK_GARBAGE_CLEANING_RECOMMENDED]
        self._table_system_info.set_expected_column_values(column_index=2, valid_value=[States.VALID],
                                                           invalid_value=[States.INVALID], unknown_value=[States.UNKNOWN])

    def get_macaddrs_dict(self):
        macadress = {}
        hosts_dict = {host.lower(): ip_address for ip_address, host in list(self.get_host_name_by_ip_dict().items())}
        agents_vms = self.run_data_collector(VmsDataCollector)
        agents_vms.update(self.run_data_collector(AgentsDataCollector))
        for host_name in list(agents_vms.keys()):
            try:
                macadress[hosts_dict[host_name.lower()]] = agents_vms[host_name]
            except KeyError as e:
                raise UnExpectedSystemOutput(ip=host_name, cmd="", output=hosts_dict,
                                             message='Key {} is missing'.format(str(e)))
        return macadress

    def is_validation_passed(self):
        self.failed_hosts = []
        self.no_flows = []
        self.states_list = States.get_states_list()
        self.states_list.remove(States.INFO)
        self.get_flows_results()
        if self._table_system_info.table:
            self._system_info = self.get_flow_summary()
        self._system_info += self._failed_msg
        if self.no_flows:
            no_flow_msg = 'No flows found on {}\n'.format(', '.join(self.no_flows))
            if self._system_info == '':
                self._system_info = no_flow_msg
            else:
                self._table_system_info.remarks = no_flow_msg
        if self.counter[States.INVALID] > 0:
            self._failed_msg += "Some of the flows failed\n"
        self._system_info = self._system_info.rstrip('\n')
        if self._severity != Severity.NA:
            return False
        return True

    def handle_invalid_state(self, host, flow, matched_macs, name, hypervisor):
        msg = None
        if flow['port_name'] is None:
            if host == hypervisor:
                msg = 'switch port {0} does not exist. {1} running on this hypervisor'.format(flow['output'], name)
            elif name is None:
                msg = 'switch port {0} does not exist. {1} is unknown'.format(flow['output'], flow['mac'])
            else:
                msg = 'switch port {0} does not exist. {1} maps to {2}'.format(flow['output'], flow['mac'], name)
        elif len(matched_macs) < 1:
            msg = 'unknown mac address {0}'.format(flow['mac'])
        elif hypervisor is None:
            if self._severity != Severity.WARNING:
                self._severity = Severity.NOTIFICATION
            msg = 'tunnel destination unknown'
            return msg
        elif not name:
            if len(matched_macs) > 1:
                msg = '{0} maps to {1}'.format(flow['mac'], matched_macs)
            else:
                tunnel_ip = list(matched_macs)[0]
                tunnel_hypervisor = self.hypervisors[tunnel_ip]
                tunnel_vm = matched_macs[tunnel_ip]
                msg = '{0} assigned to {1} located on {2} ({3})'.format(flow['mac'], tunnel_vm, tunnel_hypervisor,
                                                                        tunnel_ip)
        if msg:
            self._severity = Severity.WARNING
        return msg

    def handle_unknown_state(self, flow, host, name):
        hypervisor = self.hypervisors.get(flow['remote_ip'], None)
        if host == hypervisor:
            return '{0} running on this hypervisor ({1})'.format(name, hypervisor)

    def handle_valid_state(self, name):
        return name

    def run_data_collector(self, data_collector_class, **kwargs):
        data_collected = FlowsOperator.run_data_collector(self, data_collector_class, **kwargs)
        data_collected_without_None_valuse = {}
        for host_name, data in list(data_collected.items()):
            if data is None:
                if host_name not in self.failed_hosts:
                    host_name_msg = host_name
                    if self.is_not_connected_host(host_name):
                        host_name_msg += " - Not Connected"
                    self._failed_msg += "Failed to collect data for {} (details in the .json file)\n".format(
                        host_name_msg)
                    self.failed_hosts.append(host_name)
                    self._severity = Severity.WARNING
            else:
                data_collected_without_None_valuse[host_name] = data
        return data_collected_without_None_valuse

    def get_flows_results(self):
        self.states_flows_dict = dict()
        self.hypervisors = self.get_host_name_by_ip_dict()
        self.mac_addresses = self.get_macaddrs_dict()
        flows = self.run_data_collector(FlowsDataCollector)
        self.counter = {state: 0 for state in self.states_list}
        for host, host_flows in list(flows.items()):
            if not host_flows and host not in self.failed_hosts:
                self.no_flows.append(host)
                continue
            for flow in host_flows:
                matched_macs = {ip: self.mac_addresses[ip][flow['mac']] for ip in self.mac_addresses if
                                flow['mac'] in self.mac_addresses[ip]}
                name = self.mac_addresses.get(flow.get('remote_ip', ''), {}).get(flow.get('mac', ''), None)
                hypervisor = self.hypervisors.get(flow.get('remote_ip', ''), None)
                if hypervisor is not None:
                    dst = '{0} ({1})'.format(flow['remote_ip'], hypervisor)
                else:
                    dst = 'port.{0}'.format(flow['port_name'] if flow['port_name'] else flow['output'])
                msg = self.handle_invalid_state(host, flow, matched_macs, name, hypervisor)
                if msg:
                    state = States.INVALID
                else:
                    msg = self.handle_unknown_state(flow, host, name)
                    if msg:
                        state = States.UNKNOWN
                    else:
                        msg = self.handle_valid_state(name)
                        state = States.VALID
                self.counter[state] += 1
                flow = '{0} -> {1}'.format(flow['mac'], dst)
                self.states_flows_dict.setdefault(state, []).append([host, flow, state, msg])
        self._table_system_info.table = [item for state in self.states_list for item in
                                   self.states_flows_dict.get(state, [])]

    def get_flow_summary(self):
        return "Flows: {}\n".format(
            ', '.join('{}: {}'.format(state, self.counter[state]) for state in self.states_list))


class AgentsDataCollector(DataCollector):
    objective_hosts = [Objectives.CONTROLLERS]

    def exec_ip_netns_list(self):
        args = 'sudo ip netns list'
        return self.get_output_from_run_cmd(args)

    def exec_ip_link(self, namespace):
        args = 'sudo ip -n {namespace} -br link'.format(namespace=namespace)
        return self.get_output_from_run_cmd(args)

    def collect_data(self):
        addrs = {}
        out = self.exec_ip_netns_list()
        namespaces = [x.split()[0] for x in out.splitlines() if x.startswith('qdhcp') or x.startswith('qrouter')]

        for namespace in namespaces:
            out = self.exec_ip_link(namespace)
            for line in out.splitlines():
                if any(line.startswith(x) for x in ['tap', 'qr', 'ha', 'qa', 'gq']):
                    addrs[line.split()[2]] = namespace
        return addrs


class VmsDataCollector(DataCollector):
    objective_hosts = [Objectives.COMPUTES]

    def exec_virsh_list(self):
        args = 'sudo virsh list --all --uuid'
        return self.get_output_from_run_cmd(args)

    def exec_virsh_dumpxml(self, uuid):
        args = 'sudo virsh dumpxml ' + uuid
        return self.get_output_from_run_cmd(args)

    def collect_data(self):
        namespace_version = '1.0' if gs.get_version() < Version.V25 else '1.1'
        addrs = {}
        for uuid in self.exec_virsh_list().strip().splitlines():
            xml = self.exec_virsh_dumpxml(uuid)
            root = ET.fromstring(xml)
            namespaces = {'nova': 'http://openstack.org/xmlns/libvirt/nova/{}'.format(namespace_version)}
            name = root.find('metadata')[0].find('nova:name', namespaces).text
            for e in root.find('devices').iter('interface'):
                mac = e.find('mac').get('address')
                addrs[mac] = name
        return addrs


class MulticastDumpFlows(DumpFlowsInfoOperator, InformatorValidator):
    objective_hosts = {Deployment_type.CBIS: [Objectives.CONTROLLERS, Objectives.COMPUTES]}

    def is_prerequisite_fulfilled(self):
        return self.is_br_tun_bridge_exist()

    def set_document(self):
        self._system_info = ""
        self._failed_msg = ""
        self._title_of_info = "multicast dump flows"
        self._is_pure_info = True
        self._unique_operation_name = "multicast_dump_flows"
        self._title = "multicast dump flows"
        self._implication_tags = [ImplicationTag.RISK_GARBAGE_CLEANING_RECOMMENDED]
        self._is_clean_cmd_info = True
        self._severity = Severity.ERROR

    def get_table22_flows(self):
        output = self.exec_dumpflow('br-tun', 22)
        rules = []
        rex = re.compile(r'.*priority=(\d+),.*load:(0x[a-zA-Z0-9]+)')
        for line in output.splitlines():
            if rex.match(line):
                priority, tunnel_id = rex.match(line).groups()
                rules.append({'priority': priority, 'tunnel_id': tunnel_id,
                              'output': (re.findall(r'output:(\d+)', line))})
        return rules

    def get_multicast_flows(self):
        flows = []
        interfaces = self.get_interfaces()
        for flow in self.get_table22_flows():
            output = flow['output']
            vlan = self.convert_hex_to_decimal(flow['tunnel_id'])
            # Find the matching interface
            remote_ip_list = []
            local_ip_list = []
            port_name_list = []
            is_match_found = False
            for output_item in output:
                matching_interfaces = [x for x in interfaces if str(x['ofport']) == output_item]
                if len(matching_interfaces) != 0:
                    is_match_found = True
                    remote_ip_list.append(matching_interfaces[0]['options']['remote_ip'])
                    local_ip_list.append(matching_interfaces[0]['options']['local_ip'])
                    port_name_list.append(matching_interfaces[0]['name'])
            if is_match_found:
                flows.append(OrderedDict([('tunnel_id', vlan), ('remote_ip_list', remote_ip_list), ('output', output),
                                          ('local_ip_list', local_ip_list), ('port_name_list', port_name_list)]))
        return flows

    @lazy_global_data_loader
    def get_hosts_for_segmentation_dict_from_mariadb(self):
        dhcp_agents_list = self.get_first_value_from_data_collector(OpenstackUtilsDataCollector, mysql_command="use ovs_neutron; select distinct(ml2_vxlan_endpoints.ip_address), networksegments.segmentation_id from  ml2_vxlan_endpoints, networksegments, agents,networkdhcpagentbindings where networksegments.network_type=\"vxlan\" and ml2_vxlan_endpoints.host=agents.host and  networksegments.network_id=networkdhcpagentbindings.network_id and  agents.id=dhcp_agent_id;")
        routers_agents_list = self.get_first_value_from_data_collector(OpenstackUtilsDataCollector, mysql_command="use ovs_neutron; select distinct(ml2_vxlan_endpoints.ip_address), networksegments.segmentation_id from  ml2_vxlan_endpoints, agents, networksegments, ports, ha_router_agent_port_bindings where ml2_vxlan_endpoints.host=agents.host  and networksegments.network_type=\"vxlan\" and  ha_router_agent_port_bindings.l3_agent_id=agents.id and ports.id=ha_router_agent_port_bindings.port_id and ha_router_agent_port_bindings.state=\"active\";")
        ovs_agents_list = self.get_first_value_from_data_collector(OpenstackUtilsDataCollector, mysql_command="use ovs_neutron; select distinct(ml2_vxlan_endpoints.ip_address), networksegments.segmentation_id from  ml2_vxlan_endpoints, networksegments, nova.instances inst, ports where networksegments.network_type=\"vxlan\" and inst.uuid = ports.device_id and ml2_vxlan_endpoints.host=inst.host and networksegments.network_id=ports.network_id;")
        host_segmentation_list = dhcp_agents_list + routers_agents_list + ovs_agents_list
        hosts_for_segmentation_dict = {}
        try:
            for item in host_segmentation_list:
                segmentation_id_int = self.parse_to_int(item['segmentation_id'])
                if segmentation_id_int not in hosts_for_segmentation_dict:
                    hosts_for_segmentation_dict[segmentation_id_int] = []
                hosts_for_segmentation_dict[segmentation_id_int].extend([item['ip_address']])
            return {key: list(set(value)) for key, value in list(hosts_for_segmentation_dict.items())}
        except KeyError as e:
            raise UnExpectedSystemOutput(ip=Objectives.ONE_CONTROLLER, cmd="MariaDB command",
                                         output=host_segmentation_list,
                                         message='Key {} is missing'.format(str(e)))

    def is_validation_passed(self):
        host_name_by_ip_dict = self.get_host_name_by_ip_dict()
        host_name_by_ip_connected_msg_dict = self.get_host_name_by_ip_connected_msg_dict(host_name_by_ip_dict)
        hosts_for_segmentation_dict = self.get_hosts_for_segmentation_dict_from_mariadb()
        flows_list = self.get_multicast_flows()
        unrecognized_ips = self.handle_unrecognized_ips(hosts_for_segmentation_dict, flows_list, host_name_by_ip_dict)
        tunnels_without_flows = []
        if flows_list:
            host_ip = flows_list[0]['local_ip_list'][0]
            tunnels_without_flows = [key for key, value in list(hosts_for_segmentation_dict.items()) if host_ip in value]
        for flow in flows_list:
            if hosts_for_segmentation_dict.get(flow['tunnel_id']) is None:
                flow_str = ", ".join("{}: {}".format(k, v) for k, v in flow.items())
                self._system_info += "Invalid flow: {}\ntunnel_id: {} not exist.\n".format(flow_str, flow['tunnel_id'])
                continue
            if flow['tunnel_id'] in tunnels_without_flows:
                tunnels_without_flows.remove(flow['tunnel_id'])
            sorted_remote_ip_list = PythonUtils.words_in_A_missing_from_B(sorted(flow['remote_ip_list']),
                                                                          unrecognized_ips)
            sorted_tunnel_hosts = PythonUtils.words_in_A_missing_from_B(
                sorted(hosts_for_segmentation_dict[flow['tunnel_id']]), unrecognized_ips)

            try:
                self.handle_redundant_outputting(sorted_tunnel_hosts, sorted_remote_ip_list, host_ip, flow['tunnel_id'],host_name_by_ip_connected_msg_dict)
                self.handle_missing_outputting(sorted_tunnel_hosts, sorted_remote_ip_list, host_ip, host_name_by_ip_connected_msg_dict, flow['tunnel_id'])
            except IPHostMappingNotFoundError as e:
                raise UnExpectedSystemOutput("", "", "", message=e.message)

        if tunnels_without_flows:
            self._system_info += "There are no multicast flows with tunnel_ids: {} on this host.\n".format(
                str(tunnels_without_flows))
        if not self._system_info:
            self._system_info = "Multicast traffic OK"
        self._system_info = self._system_info.rstrip('\n')
        return True

    def get_host_name_by_ip_connected_msg_dict(self, host_name_by_ip_dict):
        host_name_by_ip_connected_msg_dict = host_name_by_ip_dict.copy()
        for ip, host_name in list(host_name_by_ip_dict.items()):
            if self.is_not_connected_host(host_name):
                host_name_by_ip_connected_msg_dict[ip] = "{} - Not Connected".format(host_name)
        return host_name_by_ip_connected_msg_dict

    def handle_redundant_outputting(self, sorted_tunnel_hosts, sorted_remote_ip_list, host_ip, flow_tunnel_id,
                                    host_name_by_ip_connected_msg_dict):
        redundant_outputting = PythonUtils.words_in_A_missing_from_B(A_list=sorted_remote_ip_list,
                                                                     B_list=sorted_tunnel_hosts)
        if host_ip not in sorted_tunnel_hosts:
            redundant_outputting.append(host_ip)
        if host_ip in sorted_remote_ip_list:
            self._system_info += "Multicast traffic via tunnel_id: {} running on this hypervisor.\n".format(
                flow_tunnel_id)
        if redundant_outputting:
            redundant_outputting_hosts_ips_list = self.build_ip_hostname_list(redundant_outputting, host_name_by_ip_connected_msg_dict)
            self._system_info += 'Multicast traffic via tunnel_id: {} cannot reach: {}.\n'.format(
                flow_tunnel_id, str(redundant_outputting_hosts_ips_list))

    def handle_missing_outputting(self, sorted_tunnel_hosts, sorted_remote_ip_list, host_ip,
                                  host_name_by_ip_connected_msg_dict,
                                  flow_tunnel_id):
        missing_outputting = PythonUtils.words_in_A_missing_from_B(A_list=sorted_tunnel_hosts,
                                                                   B_list=sorted_remote_ip_list)
        if host_ip in missing_outputting:
            missing_outputting.remove(host_ip)
        if missing_outputting:

            missing_outputting_hosts_ips_list = self.build_ip_hostname_list(missing_outputting, host_name_by_ip_connected_msg_dict)
            self._system_info += "Multicast traffic via tunnel_id: {} is not outputting to: {}.\n".format(flow_tunnel_id,
                                                                                                         str(missing_outputting_hosts_ips_list))
    @staticmethod
    def build_ip_hostname_list(ip_list, host_name_by_ip_connected_msg_dict):
        result = []
        for ip in ip_list:
            host_name = host_name_by_ip_connected_msg_dict.get(ip)
            if host_name is None:
                raise IPHostMappingNotFoundError(ip)
            result.append("{} ({})".format(ip, host_name))
        return result

    def handle_unrecognized_ips(self, hosts_for_segmentation_dict, flows_list, host_name_by_ip_dict):
        missing_ips_flows_remote_ips = set()
        missing_ips_tunnel_hosts = set()
        if hosts_for_segmentation_dict:
            hosts_for_segmentation_ips_set = set(list(chain.from_iterable(list(hosts_for_segmentation_dict.values()))))
            missing_ips_tunnel_hosts = set(hosts_for_segmentation_ips_set).difference(set(host_name_by_ip_dict))
            if missing_ips_tunnel_hosts:
                self._system_info += "Unrecognized tunnel ips: {}.\n".format(list(missing_ips_tunnel_hosts))
        if flows_list:
            remote_ip_set = set(list(chain.from_iterable([flow['remote_ip_list'] for flow in flows_list])))
            missing_ips_flows_remote_ips = set(remote_ip_set).difference(set(host_name_by_ip_dict))
            if missing_ips_flows_remote_ips:
                self._system_info += "Unrecognized flow remote ips: {}.\n".format(list(missing_ips_flows_remote_ips))
        return list(set(list(missing_ips_tunnel_hosts) + list(missing_ips_flows_remote_ips)))

class ValidateUnicastFlows(UnicastDumpFlows):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "validate_unicast_flows"
        self._title = "Validate Unicast Flows"
        self._failed_msg = "Missing VXLAN tunnel\n"
        self._is_pure_info = False
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        is_passed = True

        self.failed_hosts = []
        self.no_flows = []
        self.states_list = States.get_states_list()

        self.get_flows_results()

        if self._table_system_info.table:
            self._system_info = self.get_flow_summary()

        invalid_count = self.counter.get(States.INVALID, 0)
        unknown_count = self.counter.get(States.UNKNOWN, 0)

        if invalid_count > 0 or unknown_count > 0:
            is_passed = False
            problematic_hosts = set()

            for state in [States.INVALID, States.UNKNOWN]:
                for row in self.states_flows_dict.get(state, []):
                    problematic_hosts.add(row[0])

            if problematic_hosts:
                sorted_hosts = sorted(list(problematic_hosts))
                self._failed_msg += "Issues detected on the following hosts (Invalid/Unknown flows): {}\n".format(", ".join(sorted_hosts)                )
                self._failed_msg += "\nRestart ovs agent container on these nodes"

        return is_passed

class ValidateMulticastFlows(MulticastDumpFlows):
    objective_hosts = {Deployment_type.CBIS: [Objectives.CONTROLLERS, Objectives.COMPUTES]}

    def set_document(self):
        self._unique_operation_name = "validate_multicast_flows"
        self._title = "Validate Multicast Flows"
        self._failed_msg = ""
        self._is_pure_info = False
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        super(ValidateMulticastFlows, self).is_validation_passed()

        if "Multicast traffic OK" in self._system_info:
            return True

        self._failed_msg = self._system_info
        self._failed_msg += "\nRestart ovs agent container on these nodes"
        return False