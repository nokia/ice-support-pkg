from __future__ import absolute_import
from tools.UI.HTMLBuilder import HTMLBuilder


class Unit:
    KB = "KB"
    BYTES = "BYTES"
    GB = 'GB'
    MB = 'MB'


class Domain:
    MEMORY = 'Memory'
    STORAGE = 'Storage'
    CPU = 'cpu'
    DETAILS = 'Details'
    NETWORK = 'Network'


class VIEWS:
    SIMPLE_TABLE = 'simple_table'
    DETAILS_TABLE = 'details_table'


view_dict = {
    "info_vms_diagnostics_info": {
        "domain": Domain.MEMORY,
        "name": "memory",
        "view": VIEWS.DETAILS_TABLE,
        "per_vm": True,
        "fields": {
            "memory": {
                "unit": Unit.KB,
                "explanation": "all memory"
            },
            "memory-available": {
                "unit": Unit.KB,
                "explanation": "the memory that is free to use"
            },
            "memory-actual": {
                "unit": Unit.KB,
                "explanation": "all the physical memory"
            },
            "memory-usable": {
                "unit": Unit.KB,
                "explanation": "sable memory is a calculated amount of the total physical memory minus \"hardware "
                               "reserved\" memory "
            },
            "memory-swap_in": {
                "unit": Unit.KB,
                "explanation": "Swap-in is a method of removing a program from a hard disk and putting it back into the "
                               "main memory or RAM. "
            },
            "memory-swap_out": {
                "unit": Unit.KB,
                "explanation": "Swap-out is a method of removing a process from RAM and adding it to the hard disk"
            },
            "memory-rss": {
                "unit": Unit.KB,
                "explanation": "how much memory the process uses"
            },
            "memory-unused": {
                "unit": Unit.KB,
                "explanation": "un-used memory"
            }
            #   https://scoutapm.com/blog/understanding-page-faults-and-memory-swap-in-outs-when-should-you-worry
        }

    },
    "info_domiflist_info": {
        "domain": Domain.NETWORK,
        "name": "vms interfaces",
        "view": VIEWS.SIMPLE_TABLE,
        "per_vm": True,
        "fields": {
            # "statistics": {
            #     "rx_packets": {
            #         "unit": Unit.NO_UNIT,
            #         "explanation": "a total number of packets received"
            #     },
            #     "rx_bytes": {
            #         "unit": Unit.BYTES,
            #         "explanation": "the volume of data, in bytes, received by the interface"
            #     },
            #     "rx_drop": {
            #         "unit": Unit.NO_UNIT,
            #         "explanation": "number of dropped packets"
            #     },
            #     "rx_errs": {
            #         "unit": Unit.NO_UNIT,
            #         "explanation": "CRC failures on receipt of a frame. The root cause of this could be a bad cable, "
            #                        "or a bad interface on either the machine or the switch "
            #     },
            #     "tx_packets": {
            #         "unit": Unit.NO_UNIT,
            #         "explanation": "a total number of packets transmitted"
            #     },
            #     "tx_bytes": {
            #         "unit": Unit.BYTES,
            #         "explanation": "the volume of data, in bytes, transmitted by the interface"
            #     },
            #     "tx_drop": {
            #         "unit": Unit.NO_UNIT,
            #         "explanation": "number of transmitted dropped packets"
            #     },
            #     "tx_errs": {
            #         "unit": Unit.NO_UNIT,
            #         "explanation": "CRC failures on receipt of a transmitted frame. The root cause of this could be a bad "
            #                        "cable, or a bad interface on either the machine or the switch"
            #     },
            #
            # },
            "Interface": {
                "explanation": "the tap device of the vm"
            },
            "Source": {
                "explanation": "The bridge device the tap is connected to"
            },
            "Model": {
                "explanation": "the way the network devices is connected"
            },
            "MAC": {
                "explanation": "the mac address of the interface"
            }
        }
    },
    "info_compute_virsh_networks": {
        "domain": Domain.NETWORK,
        "name": "compute virsh dhcp network",
        "view": VIEWS.SIMPLE_TABLE,
        "per_vm": False,
        "fields": {
            "Name": {
                "explanation": "The network name"
            },
            "Bridge": {
                "explanation": "The network bridge name"
            },
            "state": {
                "explanation": "The state of the bridge(active/inactive)"
            },
            "Persistent": {
                "explanation": "If the network persistent over reboots and shutdown"
            },
            "Autostart": {
                "explanation": "If the network automatically starts reboots and shutdown"
            },
        }
    },
    "info_compute_brctl_show": {
        "domain": Domain.NETWORK,
        "name": "compute bridges",
        "view": VIEWS.SIMPLE_TABLE,
        "per_vm": False,
        "fields": {
            "name": {
                "explanation": "The network bridge name"
            },
            "interfaces": {
                "explanation": "The bridge and tap"
            },
            "id": {
                "explanation": "The id of the bridge"
            }
        }
    },
    "info_dommemstat_info": {
        "domain": Domain.MEMORY,
        "name": "memory statistics",
        "view": VIEWS.DETAILS_TABLE,
        "per_vm": True,
        "fields": {
            "actual": {
                "unit": Unit.KB,
                "explanation": "all the physical memory"
            },
            "rss": {
                "unit": Unit.KB,
                "explanation": "how much memory the process uses"
            },
        }
    },
    "info_vms_storage": {
        "domain": Domain.STORAGE,
        "name": "vms storage disks (volumes)",
        "view": VIEWS.SIMPLE_TABLE,
        "per_vm": True,
        "fields": {
            "disk_name": {
                "explanation": "The vm disk name"
            },
            "volume_id": {
                "explanation": "The id of the disk volume"
            },
            "Allocation": {
                "unit": Unit.KB,
                "explanation": "The size of the partitioned disk"
            },
            "volume_pool_name": {
                "explanation": "The pool name of the disk volume"
            },
            "Physical": {
                "unit": Unit.KB,
                "explanation": "The physical size of the disk"
            },
            "Capacity": {
                "unit": Unit.KB,
                "explanation": "The capacity of the disk"
            },
        }
    },
    "info_vms_show_info": {
        "domain": Domain.DETAILS,
        "name": "vm information",
        "view": VIEWS.DETAILS_TABLE,
        "per_vm": True,
        "fields": {
            "vm_name": {
                "explanation": "The vm disk name"
            },
            "availability_zone": {
                "explanation": "The vm availability zone"
            },
            "image_name": {
                "explanation": "The image name of the vm"
            },
            "image_id": {
                "explanation": "The image id of the vm"
            },
            "flavor_name": {
                "explanation": "The flavor name of the vm"
            },
            "flavor_id": {
                "explanation": "The flavor id of the vm"
            },
            "virsh_name": {
                "explanation": "The virsh instance name of the vm"
            },
            "networks": {
                "explanation": "the network list"
            },
            "security_groups": {
                "explanation": "The security groups"
            },
            "volumes_attached": {
                "explanation": "The volumes attached to the vm"
            },
            "created": {
                "explanation": "The date of the vm creation"
            },
            "properties": {
                "explanation": "The vm properties"
            },
            "vm_status": {
                "explanation": "The activation status of the vm"
            },
            "ipv4": {
                "explanation": ""
            },
            "ipv6": {
                "explanation": ""
            },
            "power_state": {
                "explanation": "The power state of the vm"
            },
            "project_id": {
                "explanation": "The id of the vm project"
            },
        }
    },
    "info_vms_flavor_info": {
        "domain": Domain.DETAILS,
        "name": "vm flavor information",
        "view": VIEWS.DETAILS_TABLE,
        "per_vm": True,
        "fields": {
            "name": {
                "explanation": "The flavor name"
            },
            "ram": {
                "explanation": "The ram of the flavor",
                "unit": Unit.KB
            },
            "OS-FLV-DISABLED:disabled": {
            },
            "vcpus": {
                "explanation": "Number of cpu in the flavor"
            },
            "flavor": {
                "explanation": "The flavor name of the vm"
            },
            "access_project_ids": {
                "explanation": "the projects ids that has access to the flavor"
            },
            "os-flavor-access:is_public": {
                "explanation": "If the flavor is public"
            },
            "rxtx_factor": {
                "explanation": ""
            },
            "OS-FLV-EXT-DATA:ephemeral": {
                "explanation": ""
            },
            "disk": {
                "explanation": ""
            },
            "properties": {
                "explanation": ""
            },
            "swap": {
                "explanation": ""
            },

        }
    },
    "info_vms_image_info": {
        "domain": Domain.DETAILS,
        "name": "vm image information",
        "view": VIEWS.DETAILS_TABLE,
        "per_vm": True,
        "fields": {
            "name": {
                "explanation": "The image name"
            },
            "id": {
                "explanation": "The image id"
            },
            "file": {
                "explanation": "The file of the image",
            },
            "container_format": {
                "explanation": "if the image is wrapped in a container (e.g. qcow) or bare",
            },
            "owner": {
                "explanation": "The id of the image owner"
            },
            "virtual_size": {
                "explanation": ""
            },
            "created_at": {
                "explanation": ""
            },
            "size": {
                "explanation": "",
                "unit": Unit.KB
            },
            "properties": {
                "explanation": ""
            },
            "schema": {
                "explanation": ""
            },
            "checksum": {
                "explanation": ""
            },
            "tags": {
                "explanation": ""
            },
            "disk_format": {
                "explanation": ""
            },
            "visibility": {
                "explanation": ""
            },
            "protected": {
                "explanation": ""
            },
            "min_ram": {
                "explanation": ""
            },
            "updated_at": {
                "explanation": ""
            },

        }
    },
    "info_compute_hypervisor_details": {
        "domain": Domain.DETAILS,
        "name": "compute hypervisor information (resources etc)",
        "view": VIEWS.DETAILS_TABLE,
        "per_vm": False,
        "fields": {
            "id": {
                "explanation": "id of the hypervisor"
            },
            "host_time": {
                "explanation": "the host ttime"
            },
            "uptime": {
                "explanation": "The time the host is up",
            },
            "local_gb_used": {
                "explanation": "",
                "unit": Unit.GB
            },
            "memory_mb_used": {
                "explanation": "",
                "unit": Unit.MB
            },
            "state": {
                "explanation": ""
            },
            "status": {
                "explanation": ""
            },
            "aggregates": {
                "explanation": ""
            },
            "host_ip": {
                "explanation": ""
            },
            "disk_available_least": {
                "explanation": ""
            },
            "local_gb": {
                "explanation": "",
                "unit": Unit.GB
            },
            "free_ram_mb": {
                "explanation": "",
                "unit": Unit.MB
            },
            "vcpus_used": {
                "explanation": ""
            },
            "memory_mb": {
                "explanation": "",
                "unit": Unit.MB
            },
            "vcpus": {
                "explanation": "number of vcpus"
            },
            "running_vms": {
                "explanation": ""
            },
            "service_id": {
                "explanation": ""
            },
            "service_host": {
                "explanation": ""
            },

        }
    },
    "info_vms_ports": {
        "domain": Domain.NETWORK,
        "name": "vm ports",
        "view": VIEWS.SIMPLE_TABLE,
        "per_vm": True,
        "fields": {
            "id": {
                "explanation": "The id of the port"
            },
            "fixed_ips": {
                "explanation": ""
            },
            "port_security_enabled": {
                "explanation": ""
            },
            "mac_address": {
                "explanation": ""
            },
            "status": {
                "explanation": "The activation status of the port"
            },
            "binding_vif_type": {
                "explanation": ""
            },
            "ip_address": {
                "explanation": ""
            },
            "device_id": {
                "explanation": ""
            }
        }
    },
    "info_compute_route": {
        "domain": Domain.NETWORK,
        "name": "the compute route command",
        "view": VIEWS.SIMPLE_TABLE,
        "per_vm": False,
        "fields": {
            "Iface": {
                "explanation": "Interface to which packets for this route will be sent"
            },
            "Destination": {
                "explanation": "The destination network or destination host"
            },
            "Genmask": {
                "explanation": "The netmask for the destination net; '255.255.255.255' for a host destination and '0.0.0.0' for the default route"
            },
            "Flags": {
                "explanation": """
                        U (route is up)
                        H (target is a host)
                        G (use gateway)
                        R (reinstate route for dynamic routing)
                        D (dynamically installed by daemon or redirect)
                        M (modified from routing daemon or redirect)
                        A (installed by addrconf)
                        C (cache entry)
                        !  (reject route)
                """
            },
            "Gateway": {
                "explanation": "The gateway address or '*' if none set."
            },
        }
    },
    "info_compute_ip_link_show": {
        "domain": Domain.NETWORK,
        "name": "compute network interfaces",
        "view": VIEWS.SIMPLE_TABLE,
        "per_vm": False,
        "fields": {
            "name": {
                "explanation": "link name"
            },
            "mtu": {
                "explanation": "Maximum Transmission Unit"
            },
            "status": {
                "explanation": ""
            },
            "qlen": {
                "explanation": "transmit queue length of the device"
            },
            "link/ether": {
                "explanation": ""
            },
            "master": {
                "explanation": ""
            },
            "mode": {
                "explanation": ""
            },
            "brd": {
                "explanation": ""
            },
            "state": {
                "explanation": ""
            },
        }
    },
    "info_vcpu_info": {
        "domain": Domain.CPU,
        "name": "vm vcpu information",
        "view": VIEWS.SIMPLE_TABLE,
        "per_vm": True,
        "fields": {
            "VCPU": {
                "explanation": ""
            },
            "CPU": {
                "explanation": "The number of the real CPU"
            },
            "State": {
                "explanation": ""
            },
            "CPU time": {
                "explanation": ""
            },
        }
    },
    "info_dom_info": {
        "domain": Domain.MEMORY,
        "name": "vm memory info",
        "view": VIEWS.DETAILS_TABLE,
        "per_vm": True,
        "fields": {
            "Max memory": {
                "explanation": ""
            },
            "Used memory": {
                "explanation": "The number of the real CPU"
            },
        }
    },
}


class VmsProcessResultDict:
    def __init__(self, result_dict, include_help_text=True):
        self.result_dict = result_dict['details']
        self.include_help_text = include_help_text
        self._processed_dict = {}

    def get_dict_as_simple_table(self, data, display_name, fields_data):
        headers_list = []
        for header in fields_data:
            if self.include_help_text:
                help_text = fields_data[header].get('explanation', "")
                headers_list.append([header, help_text])
            else:
                headers_list.append(header)
        result_dict = {
            'name': display_name,
            'view': VIEWS.SIMPLE_TABLE,
            'fields': [],
            'header': headers_list
        }
        for row in data:

            columns = []
            for field_name in fields_data:
                text = str(row.get(field_name, "")) + fields_data[field_name].get('unit', "")

                columns.append(text)
            result_dict['fields'].append(columns)
        return result_dict

    def get_dict_as_details_table(self, data, display_name, fields_data):
        result_dict = {
            'name': display_name,
            'view': VIEWS.DETAILS_TABLE,
            'fields': [],
            'header': ['Name', 'Value']
        }
        for field_name in fields_data:

            field_data = fields_data[field_name]
            if not data.get(field_name):
                continue
            help_text = field_data.get('explanation', "")
            value = str(data.get(field_name, "")) + field_data.get('unit', "")
            if self.include_help_text:
                result_dict['fields'].append([[field_name, help_text], value])
            else:
                result_dict['fields'].append([field_name, value])
        return result_dict

    def get_view_details(self, data, view_data):
        view = view_data['view']
        if view == VIEWS.SIMPLE_TABLE:
            return self.get_dict_as_simple_table(data, view_data['name'], view_data['fields'])
        elif view == VIEWS.DETAILS_TABLE:
            return self.get_dict_as_details_table(data, view_data['name'], view_data['fields'])
        return None

    def get_vm_name_id_dict(self, result_dict):
        res_dict = {}
        result_dict = result_dict['details']
        for host_name in result_dict:
            if result_dict[host_name].get('info_vms_show_info'):
                vms_info = result_dict[host_name]['info_vms_show_info']["system_info"]
                for vm_id in vms_info:
                    if vms_info[vm_id]['result'] != '---':
                        res_dict[vm_id] = vms_info[vm_id]['result']['vm_name']
        return res_dict

    def process_result(self):
        for host_name in self.result_dict:
            self._processed_dict[host_name] = {
                'vms_info': {},
                'host_info': {}
            }
            for info_name in self.result_dict[host_name]:
                view_data = view_dict.get(info_name)
                if view_data:
                    data = self.result_dict[host_name][info_name]['system_info']
                    if view_data['per_vm'] is True:
                        for vm_id in data:
                            if data[vm_id]['result'] == '---':
                                continue
                            if not self._processed_dict[host_name]['vms_info'].get(vm_id):
                                self._processed_dict[host_name]['vms_info'][vm_id] = {}
                            if not self._processed_dict[host_name]['vms_info'][vm_id].get(view_data['domain']):
                                self._processed_dict[host_name]['vms_info'][vm_id][view_data['domain']] = {}
                            self._processed_dict[host_name]['vms_info'][vm_id][view_data['domain']][
                                info_name] = self.get_view_details(
                                data[vm_id]['result'], view_data)
                    else:
                        if not self._processed_dict[host_name]['host_info'].get(view_data['domain']):
                            self._processed_dict[host_name]['host_info'][view_data['domain']] = {}
                        self._processed_dict[host_name]['host_info'][view_data['domain']][
                            info_name] = self.get_view_details(data, view_data)

    def get_processed_dict(self):
        if not self._processed_dict:
            self.process_result()
        return self._processed_dict
