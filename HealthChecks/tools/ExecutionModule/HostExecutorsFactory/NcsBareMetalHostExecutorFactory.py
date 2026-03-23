from __future__ import absolute_import
import json

from tools.ExecutionModule.HostExecutorsFactory.BaseHostExecutorsFactory import BaseHostExecutorFactory
from tools.ExecutionModule.HostExecutorsFactory.ncs_host_executor_factory import NcsHostExecutorFactory
from tools.ExecutionModule.execution_helper import ExecutionHelper
from tools.global_enums import Objectives


class NcsBareMetalHostExecutorFactory(NcsHostExecutorFactory):
    SINGLE_ROLES_TO_ADD = {
        Objectives.MASTERS: Objectives.ONE_MASTER,
        Objectives.MANAGERS: Objectives.ONE_MANAGER,
        Objectives.STORAGE: Objectives.ONE_STORAGE
    }

    def __init__(self):
        BaseHostExecutorFactory.__init__(self)
        self._local_host_name = ExecutionHelper.get_local_host_name()
        self._set_roles()

    def _set_roles(self):
        self._roles = {
            Objectives.MASTERS: "Master",
            Objectives.EDGES: "Edge",
            Objectives.WORKERS: "Worker",
            Objectives.MANAGERS: 'Manage',
            Objectives.STORAGE: "Storage",
            Objectives.MONITOR: 'Monitor'
        }

    def get_hosts_roles_dict(self, post_conf_dict):
        hosts_roles_dict = {}
        for role, ncs_role_name in list(self._roles.items()):
            # conf_roles_children = post_conf_dict[ncs_role_name]['children']
            conf_roles_children = post_conf_dict.get(ncs_role_name, {}).get('children', {})
            for child_role in conf_roles_children:
                hosts_list = post_conf_dict[child_role]['hosts']
                for host_name in hosts_list:
                    if not hosts_roles_dict.get(host_name):
                        hosts_roles_dict[host_name] = []
                    hosts_roles_dict[host_name].append(role)
        for host_name in hosts_roles_dict:
            if not (len(hosts_roles_dict[host_name]) == 1 and Objectives.MANAGERS in hosts_roles_dict[host_name]):
                hosts_roles_dict[host_name].append(Objectives.ALL_NODES)
        return hosts_roles_dict

    def _build_host_executors_dict(self, inventory_path, *args):
        with open(inventory_path) as f:
            post_conf_dict = json.load(f)
        hosts_roles_dict = self.get_hosts_roles_dict(post_conf_dict)
        hosts_dict = post_conf_dict['_meta']['hostvars']
        for host_name, info_dict in list(hosts_dict.items()):
            is_local = False

            self._add_host_executor(
                hosts_roles_dict[host_name],
                host_name,
                info_dict['ansible_host'],
                info_dict['sudo_user'],
                is_local=is_local,
                key_file=info_dict['ansible_ssh_private_key_file']
            )

    def get_base_hosts(self):
        return [list(self.get_host_executors_by_roles(roles=[Objectives.ONE_MANAGER]).keys())[0]]