from __future__ import absolute_import
from HealthCheckCommon.operations import *
from tools.global_enums import Version
from tools.lazy_global_data_loader import *
import tools.sys_parameters as sys_param


class DumpFlowsInfoOperator(FlowsOperator):

    def ovs_json_to_dict(self, data):
        results = []
        for row in data['data']:
            d = {}
            for counter, item in enumerate(row):
                name = data['headings'][counter]
                if not isinstance(item, list):
                    d[name] = item
                elif item[0] == 'map':
                    d[name] = {}
                    for key, value in item[1]:
                        d[name][key] = value
                elif item[0] == 'set':
                    d[name] = item[1]
                elif item[0] == 'uuid':
                    d[name] = item[1]
                else:
                    d[name] = {item[0]: item[1]}
            results.append(d)
        return results

    def exec_dumpflow(self, switch, table=None):
        args = 'sudo ovs-ofctl --read-only --no-stats --no-names dump-flows {}'.format(switch)
        if gs.get_version() == Version.V18_5:
            args = 'sudo ovs-ofctl dump-flows --read-only {}'.format(switch)
        args += ' table={}'.format(table)
        return self.get_output_from_run_cmd(args)

    def is_br_tun_bridge_exist(self):
        return_code, out, err = self.run_cmd('sudo ovs-vsctl list-ports br-tun')
        if "ovs-vsctl: no bridge named br-tun" in err:
            return False
        return True

    def exec_ovs_vsctl_list_ports(self, bridge):
        args = 'sudo ovs-vsctl list-ports {}'.format(bridge)
        return self.get_output_from_run_cmd(args)

    def exec_ovs_vsctl_list(self, table, name=None):
        args = 'sudo ovs-vsctl -f json list {}'.format(table)
        if name:
            args += [name]
        return self.get_output_from_run_cmd(args)

    def get_interfaces(self):
        '''Returns list of ovs interfaces for a given bridge'''
        ports = self.exec_ovs_vsctl_list_ports('br-tun').splitlines()
        interfaces = self.ovs_json_to_dict(json.loads(self.exec_ovs_vsctl_list('interface')))
        return [x for x in interfaces if x['name'] in ports]

    def convert_hex_to_decimal(self, hex_str):
        return int(hex_str, 16)

    @lazy_global_data_loader
    def get_host_name_by_ip_dict(self):
        result_dict = dict()
        host_name_by_ip_dict = dict()
        network_prefix = ".".join(gs.get_base_conf()['CBIS']['subnets']['tenant']['network_address'].split(".")[0:3])
        available_roles = list(sys_param.get_host_executor_factory().get_roles_map_dict().keys())
        if [x for x in [Objectives.COMPUTES, Objectives.CONTROLLERS] if x in available_roles]:
            result_dict = self.run_cmd_by_roles(cmd="sudo ifconfig | grep {}".format(network_prefix),
                                                roles=[Objectives.CONTROLLERS, Objectives.COMPUTES])
        for host_name in list(result_dict.keys()):
            if result_dict[host_name]["out"]:
                host_ip = network_prefix + result_dict[host_name]["out"].split(network_prefix)[1].split()[0]
                host_name_by_ip_dict[host_ip] = host_name
        return host_name_by_ip_dict

    def is_not_connected_host(self, host_name):
        host_executors = sys_param.get_host_executor_factory().get_all_host_executors()
        not_connected_hosts_list = [host for host in host_executors if not host_executors[host].is_connected]
        if host_name in not_connected_hosts_list:
            return True
        return False
