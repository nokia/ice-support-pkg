from __future__ import absolute_import
import os
from datetime import datetime
from tools.python_versioning_alignment import is_python_2
import ipaddress
import socket
import tools.sys_parameters as gs
import copy
from tools.global_enums import *
import six


class GetInfo:

    @staticmethod
    def get_ntp_list():
        ntp_ip_address = []

        uc_data = gs.get_base_conf()
        if 'ntp_servers' not in list(uc_data['CBIS']['common'].keys()) or not uc_data['CBIS']['common']['ntp_servers']:
            return False, "NTP server list is empty or NTP server not found in user_config."

        ntp_ip = uc_data['CBIS']['common']['ntp_servers']

        for ip in ntp_ip:
            # If NTP value doesnt have : in value, then its either hostname or v4:
            # If its a hostname, we get the ip - then get the version.
            if ':' not in ip:
                ip = socket.gethostbyname(ip)  # todo - is this realy needed ?
                ver = ipaddress.ip_address(ip.decode('UTF-8')) if is_python_2() else ipaddress.ip_address(ip)
                # Else its an IPv6 IP and we get the version to pass along:
            else:
                ver = ipaddress.IPv6Address(six.text_type(ip)) if is_python_2() else ipaddress.ip_address(ip)
            ip_ver = (ip, ver)
            ntp_ip_address.append(ip_ver)
        return ntp_ip_address

    @staticmethod
    def get_setup_host_list():
        '''return the host list (not includes HYP and UC)'''
        to_return = {}
        host_executors_dict = gs.get_host_executor_factory().get_all_host_executors()
        for host_name in host_executors_dict:
            ip = host_executors_dict[host_name].ip
            roles = copy.deepcopy(host_executors_dict[host_name].roles)

            for role in roles:
                if role not in {Objectives.UC, Objectives.HYP, Objectives.MANAGERS, Objectives.ONE_MANAGER}:
                    host_details = {"ip": ip, "roles": roles}
                    to_return[host_name] = host_details
                    break

        return to_return

    @staticmethod
    def get_system_available_roles():
        to_return = set()
        host_executors_dict = gs.get_host_executor_factory().get_all_host_executors()
        for host_name in host_executors_dict:
            roles_set = set(host_executors_dict[host_name].roles)
            to_return = to_return | roles_set

        return to_return

    @staticmethod
    def get_ice_version():
        path = '../../ice_version'
        version = 'testing'
        if os.path.isfile(path):
            with open(path) as f:
                version = f.read().strip()
        return version

    @staticmethod
    def get_ice_version_date():
        path = '../../ice_version_date'
        version_date = datetime.today().strftime("%d-%m-%Y")
        if os.path.isfile(path):
            with open(path) as f:
                version_date = f.read().strip()
        return version_date