from __future__ import absolute_import
import re

from flows.Blueprint.BlueprintDataCollectorsCommon import *


class NICBlueprintDataCollector(BlueprintDataCollector):

    ids = None

    def get_system_ids(self):
        return set(self.get_nic_ports_ids_dict().keys())

    def get_nic_ports_ids_dict(self):
        nic_ports_ids = {}
        interfaces_list = self.get_output_from_run_cmd(
            r"sudo lspci | grep -i 'ethernet\|infiniband' | grep -vi 'virtual'",
            hosts_cached_pool=BlueprintDataCollector.cached_data_pool).splitlines()
        for interface in interfaces_list:
            port_id = interface.split(' ')[0]
            nic_id = port_id.split('.')[0]
            ports_ids_list = nic_ports_ids.get(nic_id, [])
            ports_ids_list.append(port_id)
            nic_ports_ids[nic_id] = ports_ids_list
        return nic_ports_ids

    def get_nic_ports_names_dict(self):
        nic_ports_names_dict = {}

        for nic_id, ports_ids in list(self.get_nic_ports_ids_dict().items()):
            nic_ports_names_dict[nic_id] = []
            for port_id in ports_ids:
                ls_hw_info = self.get_lshw_info_by_port(port_id)
                port_name = ls_hw_info.get("logicalname", "----")
                nic_ports_names_dict[nic_id].append(port_name)

        return nic_ports_names_dict

    def get_lshw_info_by_port(self, port_id):
        net_items = self.get_lshw_json(["network"])

        for net_item in net_items:
            if port_id in net_item.get("businfo", ""):
                return net_item

        return None

    def get_nics_values_dict(self, field):
        nics_values_dict = {}
        for nic_id, ports_ids in list(self.get_nic_ports_ids_dict().items()):
            ls_hw_info = self.get_lshw_info_by_port(ports_ids[0])
            nics_values_dict[nic_id] = ls_hw_info.get(field, "----")

        return nics_values_dict

    def get_nics_values_dict_by_ports(self, cmd, func_to_split=None):
        nics_values_dict = {}
        for nic_id, nic_ports in list(self.get_nic_ports_names_dict().items()):
            nics_values_list = []
            for port in nic_ports:
                full_cmd = cmd.format(port_name=port)
                out = self.get_output_from_run_cmd(full_cmd, hosts_cached_pool=BlueprintDataCollector.cached_data_pool)
                if not func_to_split:
                    nic_value = self.split_result_from_output(full_cmd, out)[0]
                else:
                    nic_value = func_to_split(full_cmd, out)
                nics_values_list.append(nic_value)
            if len(set(nics_values_list)) > 1:
                raise NonIdenticalValues(self.get_host_ip(), cmd, nics_values_list,
                                             "Expected the same value for all ports in NIC")
            objective_value = nics_values_list[0]
            nics_values_dict[nic_id] = objective_value
        return nics_values_dict

    def get_blueprint_objective_key_name(self):
        return "Network Interface"

    def collect_blueprint_data(self, **kwargs):
        pass


class NICPortsAmount(NICBlueprintDataCollector):

    def get_blueprint_objective_key_name(self):
        return "Network Interface@ports_amount"

    def collect_blueprint_data(self, **kwargs):
        res = {}
        for nic_id, ports_ids in list(self.get_nic_ports_ids_dict().items()):
            res[nic_id] = len(ports_ids)
        return res


class NICVendor(NICBlueprintDataCollector):

    def get_blueprint_objective_key_name(self):
        return "Network Interface@vendor"

    def collect_blueprint_data(self, **kwargs):
        return self.get_nics_values_dict("vendor")


class NICModel(NICBlueprintDataCollector):

    def get_blueprint_objective_key_name(self):
        return "Network Interface@model"

    def collect_blueprint_data(self, **kwargs):
        return self.get_nics_values_dict("product")


class NICPortsNames(NICBlueprintDataCollector):

    def get_blueprint_objective_key_name(self):
        return "Network Interface@ports_names"

    def collect_blueprint_data(self, **kwargs):
        return self.get_nic_ports_names_dict()


class NICSpeed(NICBlueprintDataCollector):

    def get_blueprint_objective_key_name(self):
        return "Network Interface@speed_in_mb"

    def collect_blueprint_data(self, **kwargs):
        cmd = "sudo ethtool {port_name}"
        speed_dict_in_mb_s = self.get_nics_values_dict_by_ports(cmd, func_to_split=NICSpeed._get_speed_from_out)
        for nic_id, speed_in_mb_s in list(speed_dict_in_mb_s.items()):
            if speed_in_mb_s == '':
                raise ValueError("NIC {}: Expected speed with Mb/s".format(nic_id))
            try:
                int_speed_in_mb_s = int(speed_in_mb_s)
            except:
                raise ValueError("NIC {}: Expected integer speed, found '{}'".format(nic_id, speed_in_mb_s))
            speed_dict_in_mb_s[nic_id] = int_speed_in_mb_s
        return speed_dict_in_mb_s

    @staticmethod
    def _get_speed_from_out(cmd, out):
        out = out.replace("\t", "        ")
        nic_data_dict = PythonUtils.get_dict_from_string(out, 'yaml')

        if len(nic_data_dict) < 1:
            raise UnExpectedSystemOutput("", cmd, out, "Expected to have nic name and then it's data.")
        supported_speeds = nic_data_dict[list(nic_data_dict.keys())[0]].get("Supported link modes")

        if not supported_speeds:
            raise UnExpectedSystemOutput("", cmd, out, "Expected to have Supported link modes in out")

        return NICSpeed._get_max_available_speed(cmd, supported_speeds)

    @staticmethod
    def _get_max_available_speed(cmd, speed_out):
        speed_numbers = re.findall(r"\d+", speed_out)

        if len(speed_out) < 1:
            raise UnExpectedSystemOutput("", cmd, speed_out, "Expected to have numbers in out.")

        return max([int(speed) for speed in speed_numbers])


class NICVersion(NICBlueprintDataCollector):

    def get_blueprint_objective_key_name(self):
        return "Network Interface@version"

    def collect_blueprint_data(self, **kwargs):
        cmd = "sudo ethtool -i {port_name} | grep version:"
        return self.get_nics_values_dict_by_ports(cmd)


class NICFirmware(NICBlueprintDataCollector):

    def get_blueprint_objective_key_name(self):
        return "Network Interface@firmware"

    def collect_blueprint_data(self, **kwargs):
        cmd = "sudo ethtool -i {port_name} | grep firmware-version:"
        return self.get_nics_values_dict_by_ports(cmd)


class NICDriver(NICBlueprintDataCollector):

    def get_blueprint_objective_key_name(self):
        return "Network Interface@driver"

    def collect_blueprint_data(self, **kwargs):
        cmd = "sudo ethtool -i {port_name} | grep driver:"
        return self.get_nics_values_dict_by_ports(cmd)


class NICBufferCollector(NICBlueprintDataCollector):

    def get_blueprint_objective_key_name(self):
        return "Network Interface@buffer_size"

    def collect_blueprint_data(self, **kwargs):
        nic_port_name = self.get_nic_ports_names_dict()
        res = {}
        for nic_id, port_names in list(nic_port_name.items()):
            res[nic_id] = []
            for port_name in port_names:
                cmd = "sudo ethtool --show-ring {port_name}".format(port_name=port_name)
                '''
                Sample Output
                [cbis-admin@fc27-bmcluster-storagebm-0 ~]$ ethtool --show-ring ens5f0
                 Ring parameters for ens5f0:
                 Pre-set maximums:
                 RX:            8192
                 RX Mini:       n/a
                 RX Jumbo:      n/a
                 TX:            8192
                 Current hardware settings:
                 RX:            2048
                 RX Mini:       n/a
                 RX Jumbo:      n/a
                 TX:            2048
                '''
                out = self.get_output_from_run_cmd(cmd)

                if "Current hardware settings" not in out:
                    raise UnExpectedSystemOutput(self.get_host_ip(),
                                                 cmd, out,
                                                 "Expected to have 'Current hardware settings' in out")
                current_hardware = out.split("Current hardware settings")[1]
                pattern_rx = r"RX:\s+(\d+)"
                pattern_tx = r"TX:\s+(\d+)"
                rx_match = re.search(pattern_rx, current_hardware)
                tx_match = re.search(pattern_tx, current_hardware)

                if not rx_match or not tx_match:
                    raise UnExpectedSystemOutput(self.get_host_ip(),
                                                 cmd, out, "expected to have a correct pattern {}{}".format(pattern_rx,
                                                                                                            pattern_tx))
                rx_value = int(rx_match.group(1))
                tx_value = int(tx_match.group(1))
                res[nic_id].append("{port_name}: RX: {rx_value}, TX: {tx_value}".format(port_name=port_name,
                                                                                        rx_value=rx_value,
                                                                                        tx_value=tx_value))
        return res
