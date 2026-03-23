from __future__ import absolute_import
from tools.lazy_global_data_loader import *
import tools.sys_parameters as gs
from tools.global_enums import Objectives, Version, Deployment_type
from tools.Exceptions import UnExpectedSystemOutput
import re
from tools.python_utils import PythonUtils
from tools.ExecutionModule.execution_helper import ExecutionHelper


class VmsInfo:
    @staticmethod
    def get_placement_db():
        return "placement" if gs.get_version() >= Version.V22 else "nova_api"

    @staticmethod
    def convert_network_string_to_dict(s):
        result = {}
        if not s:
            return result
        network_lines = s.split(";")
        for line in network_lines:
            if not bool(re.match(r".+=.+", line)):
                raise UnExpectedSystemOutput(
                    "uc", 'openstack server list', "unexpected networks format-{}".format(line))
            network_name, network_ip = line.split('=')
            result[network_name] = network_ip
        return result

    @staticmethod
    def convert_cbis_18_vm_from_list_to_dict(vm_properties_list):
        """
        in cbis 18 the json output is not a dict, Its formatted like:
        [
        {
            "Field":"field_name",
            "Value":"field_val"
        },
        ...
        ]
        This function changes it to :
        {
            "field_name":"field_val",
            ...
        }
        :param vm_properties_list: list
        :return:
        key-value dictionary
        """
        assert type(vm_properties_list) is list
        result_dict = {}
        for item in vm_properties_list:
            assert "Value" in item and "Field" in item
            k, v = item["Field"], item["Value"]
            result_dict[k] = v

        return result_dict

    @staticmethod
    def get_vms_basic_details():
        """
        :return:
        {
            "vm_id_1111":{
                "vm_name": "name",
                "vm_status":status,
                "networks":{
                    "net_name":"ip"
                }
            }
        }
        """
        result_dict = {}
        cmd = "openstack server list --all-projects"
        vms_dict = VmsInfo.get_openstack_command_output(cmd)
        for vm in vms_dict:
            vm_id = vm["ID"]
            result_dict[vm_id] = {
                "vm_name": vm["Name"],
                "vm_status": vm["Status"],
                "networks": VmsInfo.convert_network_string_to_dict(vm["Networks"])
            }

        return result_dict

    @staticmethod
    def extract_name_id_from_openstack_info(info_text):
        if not info_text:
            return None, None
        # Pattern to match text and ID inside parentheses
        pattern = r"^(.*?)\s*\(([^)]+)\)$"
        match = re.match(pattern, info_text.strip())
        if match:
            name = match.group(1).strip()
            id_value = match.group(2).strip()
            return name, id_value
        else:
            # If pattern doesn't match, return the original text for 'name' and None for 'id'
            return info_text.strip(), None

    @staticmethod
    # CBIS Version <25 , 'flavor_info' was in String but in version 25, 'flavor_info' is in Dict format
    # both conditions returns "original_name" of the flavor and return type <class 'str'>
    def extract_flavor_name_from_flavor_info(flavor_info):
        if type(flavor_info) == dict:
            return flavor_info.get("original_name", None)
        else:
            matches = re.findall(r'\w+=".+?"', flavor_info.replace("'", '"'))
            matches_no_double_quotes = [m.replace('"', '') for m in matches]
            matches = [m.split('=', 1) for m in matches_no_double_quotes]
            flavor_dict = dict(matches)
            return flavor_dict.get("original_name", None)  # used .get() to avoid KeyError

    @staticmethod
    def get_vm_details(vm_id):
        """
        :param vm_id: str
        :return:
        {
            'image': 'image',
            'created': 'created',
            'properties': 'properties',
            'project_id': 'project_id',
            'ipv4': 'accessIPv4',
            'ipv6': 'accessIPv6',
            'virsh_name': 'OS-EXT-SRV-ATTR:instance_name',
            'flavor': 'flavor',
            'security_groups': 'security_groups',
            'volumes_attached': 'volumes_attached',
            'power_state': 'OS-EXT-STS:power_state',
            'availability_zone': 'OS-EXT-AZ:availability_zone',
            'host': 'OS-EXT-SRV-ATTR:host'
        }
        """
        result_dict = {}
        required_fields = {
            'image': ['image'],
            'created': ['created'],
            'properties': ['properties'],
            'project_id': ['project_id'],
            'ipv4': ['accessIPv4'],
            'ipv6': ['accessIPv6'],
            'virsh_name': ['OS-EXT-SRV-ATTR:instance_name'],
            'vm_name': ['OS-EXT-SRV-ATTR:hostname'],
            'flavor': ['flavor'],
            'security_groups': ['security_groups'],
            'volumes_attached': ['volumes_attached', 'os-extended-volumes:volumes_attached'],
            'power_state': ['OS-EXT-STS:power_state'],
            'availability_zone': ['OS-EXT-AZ:availability_zone'],
            'host': ['OS-EXT-SRV-ATTR:host'],
            'image_name': 'img',
            'image_id': 'id',
            'flavor_name': 'flavor name',
            'flavor_id': 'flavor_id'
        }

        cmd = " openstack server show {} ".format(vm_id)
        vm_dict = VmsInfo.get_openstack_command_output(cmd, handle_cbis_18_out=True)
        for field_name in required_fields:
            field_openstack_names = required_fields[field_name]
            for field_openstack_name in field_openstack_names:
                val = vm_dict.get(field_openstack_name)
                if val:
                    result_dict[field_name] = val
                    break
        result_dict['host'] = result_dict.get('host', '').replace(".localdomain", "")
        original_host_name, compute_host_executor = gs.get_host_executor_factory().get_host_executor_by_host_name(
            result_dict['host'])
        result_dict['host'] = original_host_name
        if gs.get_version() >= Version.V22:
            flavor_name = VmsInfo.extract_flavor_name_from_flavor_info(result_dict.get('flavor'))
            flavor_id = ''
        else:
            flavor_name, flavor_id = VmsInfo.extract_name_id_from_openstack_info(result_dict.get('flavor'))
        image_name, image_id = VmsInfo.extract_name_id_from_openstack_info(result_dict.get('image'))
        result_dict['image_name'] = image_name
        result_dict['image_id'] = image_id
        result_dict['flavor_name'] = flavor_name
        result_dict['flavor_id'] = flavor_id
        return result_dict

    @staticmethod
    def get_openstack_command_output(
            cmd, is_overcloud=True, is_json=True, handle_cbis_18_out=False, host=Objectives.UC):
        json_str = ' -f json ' if is_json else ''
        cmd = "{cmd} {json_str}".format(
            cmd=cmd,
            json_str=json_str
        )
        out = VmsInfo.run_command_on_selected_host(cmd, is_overcloud=is_overcloud, host_obj=host)
        if not is_json:
            return out
        res = PythonUtils.get_dict_from_string(out, 'json')
        if gs.get_version() < Version.V19 and handle_cbis_18_out:
            return VmsInfo.convert_cbis_18_vm_from_list_to_dict(res)
        return res

    @staticmethod
    def run_command_on_selected_host(cmd, is_overcloud=True, host_obj=Objectives.UC):
        host_operator = ExecutionHelper.get_hosting_operator(False)
        is_system_armed = host_operator.system_utils.is_system_armed()
        if host_obj == Objectives.UC:
            home_path = "/home/stack"
            suffix = "_locked" if is_system_armed else ""
        else:
            home_path = "/home/cbis-admin"
            suffix = ""

        rc_filename = "overcloudrc" if is_overcloud else "stackrc"
        rc_file_path = ". {}/{}{};".format(home_path, rc_filename, suffix)

        cmd_str = "{} {}".format(rc_file_path, cmd)
        out = gs.get_host_executor_factory().run_command_on_first_host_from_selected_roles(cmd_str,
                                                                                           roles=[host_obj])
        return out

    @staticmethod
    @lazy_global_data_loader
    def get_vms_dict():
        """
        :return:
        dictionary:
        {
            "host_name":{
                "vm_id":{
                    "virsh_name": "virsh name",
                    "vm_name": "vm_name",
                    "vm_status": "ACTIVE/ERROR...",
                    "availability_zone":"zone",
                    "created":"date___",
                    "flavor":"flavor",
                    "image":"image_name",
                    "ipv4":"ipv4_address",
                    "ipv6":"ipv6_address",
                    "networks":{
                        "network_name":"network_ip"
                    },
                    "power_state":Running",
                    "project_id":"id",
                    "volumes_attached":"ssss",
                    "vm_status":"ACTIVE",
                    "security_groups":"dddd",
                    "properties":""
                }
            }
        }
        """
        result_dict = {}
        vms_basic_dict = VmsInfo.get_vms_basic_details()
        for vm_id in vms_basic_dict:
            vm_dict = vms_basic_dict[vm_id]
            details = VmsInfo.get_vm_details(vm_id)
            vm_dict.update(details)
            host_name = vm_dict['host']
            if not result_dict.get(host_name):
                result_dict[host_name] = {}
            result_dict[host_name][vm_id] = vm_dict
        return result_dict
