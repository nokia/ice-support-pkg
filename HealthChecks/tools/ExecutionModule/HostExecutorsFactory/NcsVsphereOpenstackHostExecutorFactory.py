from __future__ import absolute_import
from tools.ExecutionModule.HostExecutorsFactory.BaseHostExecutorsFactory import BaseHostExecutorFactory
from tools.ExecutionModule.HostExecutorsFactory.ncs_host_executor_factory import NcsHostExecutorFactory
from tools.ExecutionModule.execution_helper import ExecutionHelper
from tools.global_enums import Objectives


class NcsVsphereOpenstackHostExecutorFactory(NcsHostExecutorFactory):
    SINGLE_ROLES_TO_ADD = {Objectives.MASTERS: Objectives.ONE_MASTER,
                           Objectives.STORAGE: Objectives.ONE_STORAGE}

    def __init__(self):
        BaseHostExecutorFactory.__init__(self)
        self._set_roles()

    def _set_roles(self):
        self._roles = {
            Objectives.MASTERS: "control",
            Objectives.EDGES: "edge",
            Objectives.WORKERS: "worker",
            Objectives.STORAGE: "storage",
        }

    def _build_host_executors_dict(self, inventory_path, *args):
        inventory_dict = ExecutionHelper.get_local_operator().get_dict_from_file(inventory_path)

        if "role_all" in list(inventory_dict.keys()):
            self._build_host_executors_dict_from_ui_inventory(inventory_dict)
        else:
            self._build_host_executors_dict_from_default_inventory(inventory_dict)

        host_username = ExecutionHelper.get_host_username()
        self._add_host_executor([Objectives.DEPLOYER], 'deployer', 'localhost', host_username, is_local=False,
                                key_file=ExecutionHelper.get_path_to_pkey_from_container_to_host())

    def _build_host_executors_dict_from_default_inventory(self, inventory_dict):
        ssh_private_key_str = inventory_dict['ssh_private_key']

        for role_name, role_in_inventory in list(self._roles.items()):
            if role_name != Objectives.STORAGE or role_in_inventory in list(inventory_dict.keys()):
                role_hosts = inventory_dict[role_in_inventory]
                for host_name in role_hosts:
                    host_info = role_hosts[host_name]
                    ip = host_info['internal_oam_ip']
                    user_name = host_info['ssh_user']
                    self._add_host_executor(
                        [Objectives.ALL_NODES, role_name], host_name, ip, user_name, pkey_string=ssh_private_key_str)

    def _build_host_executors_dict_from_ui_inventory(self, inventory_dict):
        for role in self._roles:
            role_hosts = inventory_dict["role_" + self._roles[role]]["hosts"]

            for host_name, host_info in list(role_hosts.items()):
                ip = host_info['private_oam_ipv4']
                user_name = host_info['ansible_ssh_user']
                ssh_private_key_str = host_info['ssh_private_key']

                self._add_host_executor(
                    [Objectives.ALL_NODES, role], host_name, ip, user_name, pkey_string=ssh_private_key_str)

    def get_base_hosts(self):
        return [list(self.get_host_executors_by_roles(roles=[Objectives.ONE_MANAGER]).keys())[0]]
