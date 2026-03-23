from __future__ import absolute_import
from HealthCheckCommon.validator import InformatorValidator
from flows.OpenStack.Vms.VmsInfo import VmsInfo
from HealthCheckCommon.operations import *
import re
from tools.python_utils import PythonUtils


class PerVmInformator(InformatorValidator):
    objective_hosts = [Objectives.COMPUTES]

    def _set_info_name(self):
        raise NotImplementedError

    def set_document(self):
        self._is_pure_info = True
        self._unique_operation_name = self._set_info_name()
        self._title_of_info = self._set_info_name().replace("_", " ")
        self._system_info = ""


    def get_info_for_vm(self, vm_id, vm_properties_dict):
        raise NotImplementedError

    def get_system_info(self):
        result_dict = {}
        host_vms = VmsInfo.get_vms_dict().get(self.get_host_name(), {})
        for vm_id in host_vms:
            res = {
                'result': '---',
                'exception': '---'
            }
            try:
                res['result'] = self.get_info_for_vm(vm_id, host_vms[vm_id])
            except Exception as e:
                res['exception'] = str(e)
            result_dict[vm_id] = res
        return result_dict


class VmsVirshXML(PerVmInformator):
    def _set_info_name(self):
        return "virsh_xml"

    def get_info_for_vm(self, vm_id, vm_properties_dict):
        vm_instance_name = re.sub("instance|inst", '', vm_properties_dict['virsh_name'])
        cmd = "sudo find /etc/libvirt/qemu/ -name \"inst*{}.xml\"".format(vm_instance_name)
        exit_code, path, err = self.run_cmd(cmd)
        return self.get_dict_from_file(path, file_format='xml')


class VmsDomInfo(PerVmInformator):
    def _set_info_name(self):
        return "dom_info"

    def get_info_for_vm(self, vm_id, vm_properties_dict):
        cmd = "sudo virsh dominfo {uuid}".format(uuid=vm_id)
        return self.get_dict_from_command_output(cmd, out_format='yaml')


class VmsVcpuInfo(PerVmInformator):
    info_name = "vcpu_info"

    def _set_info_name(self):
        return VmsVcpuInfo.info_name

    def get_info_for_vm(self, vm_id, vm_properties_dict):
        res = []
        cmd = "sudo virsh vcpuinfo {uuid}".format(uuid=vm_id)
        out = self.get_output_from_run_cmd(cmd)
        out_sections = out.split('\n\n')
        for section in out_sections:
            d = PythonUtils.get_dict_from_string(section, 'yaml')
            if d:
                res.append(d)
        return res


class ComputeRouteInfo(InformatorValidator):
    objective_hosts = [Objectives.COMPUTES]

    def set_document(self):
        self._is_pure_info = True
        self._unique_operation_name = 'compute_route'
        self._title_of_info = 'Get compute route'
        self._system_info = ""


    def get_system_info(self):
        return self.get_dict_from_command_output('sudo route', out_format='linux_table', header_line=1)


class ComputeHypervisorInfo(InformatorValidator):
    objective_hosts = [Objectives.COMPUTES]

    def set_document(self):
        self._is_pure_info = True
        self._unique_operation_name = 'compute_hypervisor_details'
        self._title_of_info = 'Get compute hypervisor details'
        self._system_info = ""


    def get_system_info(self):
        cmd = 'openstack hypervisor show {}.localdomain'.format(self.get_host_name().lower())
        return VmsInfo.get_openstack_command_output(cmd, handle_cbis_18_out=True)


class DomMemstatInfo(PerVmInformator):
    def _set_info_name(self):
        return "dommemstat_info"

    def get_info_for_vm(self, vm_id, vm_properties_dict):
        cmd = "sudo virsh dommemstat {uuid}".format(uuid=vm_id)
        return self.get_dict_from_command_output(cmd, 'space')


class DomIfListInfo(PerVmInformator):
    def _set_info_name(self):
        return "domiflist_info"

    def get_info_for_vm(self, vm_id, vm_properties_dict):
        result_list = []
        cmd = "sudo virsh domiflist {uuid}".format(uuid=vm_id)
        interfaces_dict = self.get_dict_from_command_output(cmd, 'linux_table')
        for interface in interfaces_dict:
            interface_name = interface['Interface']
            cmd = 'sudo virsh domifstat {vm_id} {interface_name}'.format(
                vm_id=vm_id, interface_name=interface_name
            )
            out = self.get_output_from_run_cmd(cmd)
            out = re.sub(r'{}\s*'.format(interface_name), "", out)
            statistics_dict = PythonUtils.get_dict_from_space_separated_file(out)
            res = interface
            res['statistics'] = statistics_dict
            result_list.append(res)
        return result_list


class DomIfAddressInfo(PerVmInformator):
    def _set_info_name(self):
        return "domifaddress_info"

    def get_info_for_vm(self, vm_id, vm_properties_dict):
        cmd = " sudo virsh domifaddr --full --domain {uuid}".format(uuid=vm_id)
        headers = [
            'Name', 'MAC address', 'Protocol', 'Address'
        ]
        return self.get_dict_from_command_output(cmd, 'linux_table', custom_header=headers)


class VmsDiagnostics(PerVmInformator):
    def _set_info_name(self):
        return "vms_diagnostics_info"

    def get_info_for_vm(self, vm_id, vm_properties_dict):
        cmd = "openstack server show  --diagnostics {uuid} ".format(uuid=vm_id)
        return VmsInfo.get_openstack_command_output(cmd, handle_cbis_18_out=True)


class VmFlavor(PerVmInformator):
    def _set_info_name(self):
        return "vms_flavor_info"

    def get_info_for_vm(self, vm_id, vm_properties_dict):
        flavor_name = vm_properties_dict['flavor_name']
        cmd = "openstack flavor show {} ".format(flavor_name)
        return VmsInfo.get_openstack_command_output(cmd, handle_cbis_18_out=True)


class VmImage(PerVmInformator):
    def _set_info_name(self):
        return "vms_image_info"

    def get_info_for_vm(self, vm_id, vm_properties_dict):
        flavor_id = vm_properties_dict['image_id']
        cmd = "openstack image show {uuid} ".format(uuid=flavor_id)
        return VmsInfo.get_openstack_command_output(cmd, handle_cbis_18_out=True)


class VmsPortsList(PerVmInformator):
    def _set_info_name(self):
        return "vms_ports"

    def get_info_for_vm(self, vm_id, vm_properties_dict):
        port_res_list = []
        cmd = "nova interface-list {uuid}".format(uuid=vm_id)
        out = VmsInfo.run_command_on_selected_host(cmd)
        ports_list = PythonUtils.get_dict_from_string(out, 'linux_table', custom_delimiter='|')
        for port_dict in ports_list:
            port_id = port_dict['Port ID']
            port_show_cmd = 'source {stackrc}; openstack port show {port_id}'.format(stackrc=self.system_utils.get_stackrc_file_path(), port_id=port_id)
            res = VmsInfo.get_openstack_command_output(port_show_cmd, handle_cbis_18_out=True)
            res['ip_address'] = port_dict['IP addresses']
            port_res_list.append(res)
        return port_res_list


class VmsStorageInfo(PerVmInformator):
    def _set_info_name(self):
        return "vms_storage"

    def get_info_for_vm(self, vm_id, vm_properties_dict):
        res_list = []
        cmd = "sudo virsh domblklist {uuid}".format(uuid=vm_id)
        disks_dict = self.get_dict_from_command_output(cmd, 'linux_table')
        for disk in disks_dict:
            disk_name = disk['Target']
            disk_volume_pool_name, disk_volume_id = disk['Source'].split('/')
            get_disk_info_cmd = "sudo virsh domblkinfo {vm_id} {disk_name}".format(
                vm_id=vm_id, disk_name=disk_name
            )
            res = self.get_dict_from_command_output(get_disk_info_cmd, 'yaml')
            res['disk_name'] = disk_name
            res['volume_pool_name'] = disk_volume_pool_name
            res['volume_id'] = disk_volume_id
            res_list.append(res)
        return res_list


class VmShowInfo(PerVmInformator):
    def _set_info_name(self):
        return "vms_show_info"

    def get_info_for_vm(self, vm_id, vm_properties_dict):
        return vm_properties_dict


class VirshNetInfo(InformatorValidator):
    objective_hosts = [Objectives.COMPUTES]

    def set_document(self):
        self._is_pure_info = True
        self._unique_operation_name = 'compute_virsh_networks'
        self._title_of_info = 'Get compute virsh networks'
        self._system_info = ""


    def get_system_info(self):
        res_list = []
        cmd = "sudo virsh net-list --all"
        network_list = self.get_dict_from_command_output(cmd, 'linux_table')
        for network in network_list:
            res = {}
            network_name = network['Name']
            network_details_cmd = 'sudo virsh net-info --network {network_name}'.format(
                network_name=network_name)
            res = self.get_dict_from_command_output(network_details_cmd, 'yaml')
            res['state'] = network['State']
            net_dhcp_headers = [
                'Expiry Time', 'MAC address', 'Protocol', 'IP address', 'Hostname', 'Client ID or DUID'
            ]
            cmd = 'sudo virsh net-dhcp-leases {network}'.format(network=network_name)
            res['dhcp_info'] = self.get_dict_from_command_output(
                cmd, 'linux_table', custom_header=net_dhcp_headers)
            res_list.append(res)
        return res_list


class PCIInfo(InformatorValidator):
    objective_hosts = [Objectives.COMPUTES]

    def set_document(self):
        self._is_pure_info = True
        self._unique_operation_name = 'compute_PCIs'
        self._title_of_info = 'Get compute PCIs list and details'
        self._system_info = ""

    def get_system_info(self):
        res_dict = {}
        cmd = "sudo virsh nodedev-list --cap pci"
        pci_list = self.get_output_from_run_cmd(cmd).splitlines()
        for pci in pci_list:
            if not pci:
                continue
            pci_details_cmd = 'sudo virsh nodedev-dumpxml {pci}'.format(pci=pci)
            res_dict[pci] = self.get_dict_from_command_output(pci_details_cmd, 'xml')
        return res_dict


class OvsInfo(InformatorValidator):
    objective_hosts = [Objectives.COMPUTES]

    def set_document(self):
        self._is_pure_info = True
        self._unique_operation_name = 'compute_ovs_show'
        self._title_of_info = 'Get compute ovs details'
        self._system_info = ""

    def get_system_info(self):
        cmd = "sudo ovs-vsctl show"
        out = self.get_output_from_run_cmd(cmd)
        return PythonUtils.ovs_vsctl_parse(s=out)


class IpLinkInfo(InformatorValidator):
    objective_hosts = [Objectives.COMPUTES]

    def set_document(self):
        self._is_pure_info = True
        self._unique_operation_name = 'compute_ip_link_show'
        self._title_of_info = 'Get compute ip link details'
        self._system_info = ""


    def get_system_info(self):
        cmd = "sudo ip link show"
        out = self.get_output_from_run_cmd(cmd)
        return PythonUtils.parse_ip_link(s=out)


class BridgesInfo(InformatorValidator):
    objective_hosts = [Objectives.COMPUTES]

    def set_document(self):
        self._is_pure_info = True
        self._unique_operation_name = 'compute_brctl_show'
        self._title_of_info = 'Get compute bridges details'
        self._system_info = ""


    def get_system_info(self):
        cmd = "sudo brctl show"
        out = self.get_output_from_run_cmd(cmd)
        return PythonUtils.parse_brctl_show(s=out)


class VmsDetailsLevel2(InformatorValidator):
    objective_hosts = [Objectives.COMPUTES]

    def set_document(self):
        self._is_pure_info = True
        self._unique_operation_name = "virsh_info_level_2"
        self._title_of_info = "Get host vms virsh info level 2"
        self._system_info = ""


    def get_system_info(self):
        return self.get_dependency_flow_result('vms')

class NovaComputeService(InformatorValidator):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._is_pure_info = True
        self._unique_operation_name = 'nova_compute_service_list'
        self._title_of_info = 'Get compute service list'
        self._system_info = ""

    def get_system_info(self):
        cmd = "source /home/stack/overcloudrc; openstack compute service list --long -c 'Binary' -c 'Status' -c 'Host' -c 'Disabled Reason'"
        return VmsInfo.get_openstack_command_output(cmd, handle_cbis_18_out=True)


# ps aux | grep dnsmasq | grep -v grep #check the process
#
# dnsmasq --test
