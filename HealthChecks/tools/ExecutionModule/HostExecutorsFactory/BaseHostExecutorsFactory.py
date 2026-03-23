from __future__ import absolute_import
from HealthCheckCommon.parallel_runner import ParallelRunner
from tools.ExecutionModule.HostExecutorsFactory.HostExecutor import HostExecutor
from tools.Exceptions import NoSuitableHostWasFoundForRoles, UnExpectedSystemOutput
import tools.global_logging as log
from tools.ExecutionModule.execution_helper import ExecutionHelper
from tools.global_enums import Objectives


class BaseHostExecutorFactory(object):
    SINGLE_ROLES_TO_ADD = {}
    RETRY_CONNECTION_COUNT = 3

    def __init__(self):
        self._host_executors_dict = {}
        self._local_host_name = None

    def build_host_executors_dict(self, inventory_path, base_conf):
        try:
            log.log('inventory location: {}'.format(inventory_path))
            self._build_host_executors_dict(inventory_path, base_conf)
            self.connect_all_host_executors_with_retry()
            self.add_single_role_from_objective()
            if ExecutionHelper.is_run_inside_container():
                self.add_ice_container_host_executor()

        except KeyError as e:
            return False, 'Inventory file {} :\nKey {} is missing'.format(inventory_path, str(e))
        return True, ""

    def _build_host_executors_dict(self, inventory_path, *args):
        raise NotImplementedError

    # add documentation
    # unit test this
    def _add_host_executor(self, objective_roles, host_name, ip, user_name, is_local=False,
                           password=None, key_file=None, pkey_string=None):
        if host_name in self._host_executors_dict:
            self._host_executors_dict[host_name].add_roles(objective_roles)
        else:
            self._host_executors_dict[host_name] = HostExecutor(
                ip, host_name, user_name, objective_roles,
                is_local=is_local, password=password,
                key_file=key_file, pkey_string=pkey_string)

    def get_host_executors_by_roles(self, roles=None):
        result_dict = {}
        for host_name in self._host_executors_dict:
            for role in self._host_executors_dict[host_name].roles:
                if role in roles:
                    result_dict[host_name] = self._host_executors_dict[host_name]
                    break
        return result_dict

    def add_single_role_from_objective(self):
        for role_of_many, role_of_single in list(self.SINGLE_ROLES_TO_ADD.items()):
            hosts_by_role = self.get_host_executors_by_roles(roles=[role_of_many])
            connected_hosts_by_role = [host for host in hosts_by_role
                                       if self._host_executors_dict[host].is_connected]
            if not len(connected_hosts_by_role):
                log.log_and_print("*****************************************")
                log.log_and_print("*** NO connected {} were found ***".format(role_of_many))
                log.log_and_print("*****************************************")
                log.log("Not connected {}: \n{}".format(role_of_many, '\n'.join(hosts_by_role)))
            else:
                selected_single = self.select_single_host(connected_hosts_by_role, role_of_single)
                self._host_executors_dict[selected_single].add_role(role_of_single)

    def select_single_host(self, connected_hosts_by_role, role_of_single):
        selected_single = sorted(connected_hosts_by_role)[0]

        for host in connected_hosts_by_role:
            if ExecutionHelper.is_run_inside_container():
                if self._local_host_name and \
                        self._host_executors_dict[host].host_name == self._local_host_name:
                    selected_single = host
            elif self._host_executors_dict[host].is_local:
                selected_single = host

        return self.improve_single_host_selection(connected_hosts_by_role, role_of_single, selected_single)

    def improve_single_host_selection(self, connected_hosts_by_role, role_of_single, selected_single):
        return selected_single

    def get_host_executors_by_ip_or_hostname(self, ip_host_names_list=None):
        is_hosts_list_valid, invalid_hosts = self.check_if_host_list_exists(ip_host_names_list)
        assert is_hosts_list_valid, "Hosts {} does not exist in the system".format(str(invalid_hosts))
        result_dict = {}
        for host_name in self._host_executors_dict:
            if host_name in ip_host_names_list or self._host_executors_dict[host_name].ip in ip_host_names_list:
                result_dict[host_name] = self._host_executors_dict[host_name]
        return result_dict

    def get_all_host_executors(self):
        return self._host_executors_dict

    def check_if_host_list_exists(self, ip_host_names_list):
        result_dict = {host: False for host in ip_host_names_list}
        for host_name in self._host_executors_dict:
            if host_name in ip_host_names_list:
                result_dict[host_name] = True
            if self._host_executors_dict[host_name].ip in ip_host_names_list:
                result_dict[self._host_executors_dict[host_name].ip] = True
        missing_hosts = [host for host in result_dict if result_dict[host] is False]
        if len(missing_hosts) == 0:
            return True, None
        else:
            return False, missing_hosts

    def get_roles_map_dict(self):
        roles_map_dict = {}
        for host_name in self._host_executors_dict:
            not_connected_str = " - Not Connected" if not self._host_executors_dict[host_name].is_connected else ""
            host_executor = self._host_executors_dict[host_name]
            for role in host_executor.roles:
                if role not in roles_map_dict:
                    roles_map_dict[role] = []
                roles_map_dict[role].append(host_name + " at " + host_executor.ip + not_connected_str)
        return roles_map_dict

    def get_host_executor_by_host_name(self, host_name):
        host_executor = None
        original_host_name = None
        for host_executor_host_name in self._host_executors_dict:
            if host_executor_host_name.lower() == host_name.lower():
                host_executor = self._host_executors_dict[host_executor_host_name]
                original_host_name = host_executor_host_name
                break
        return original_host_name, host_executor

    def run_command_on_first_host_from_selected_roles(self, cmd, roles, timeout=60):
        host_executors_dict = self.get_host_executors_by_roles(roles=roles)
        if not len(host_executors_dict):
            raise NoSuitableHostWasFoundForRoles(roles)
        host_executor = list(host_executors_dict.values())[0]
        exit_code, out, err = host_executor.execute_cmd(cmd, timeout=timeout)
        if exit_code:
            raise UnExpectedSystemOutput(host_executor.host_name, cmd, err)
        return out

    def get_connected_host_executors_by_roles(self, roles):
        connected_host_executors_dict = {}
        host_executors_dict = self.get_host_executors_by_roles(roles=roles)
        for host_name in host_executors_dict:
            host_executor = host_executors_dict[host_name]
            if host_executor.is_connected:
                connected_host_executors_dict[host_name] = host_executor
        return connected_host_executors_dict

    def execute_cmd_by_roles(self, roles, cmd, timeout=60):
        result_dict = {}
        host_executors_dict = self.get_connected_host_executors_by_roles(roles)
        for host_name in host_executors_dict:
            host_executor = host_executors_dict[host_name]
            exit_code, out, err = host_executor.execute_cmd(cmd, timeout=timeout)
            result_dict[host_name] = {
                "out": out,
                "err": err,
                "exit_code": exit_code,
                "ip": host_executor.ip,
                "roles": host_executor.roles
            }
        if len(result_dict) == 0:
            raise NoSuitableHostWasFoundForRoles(roles)

        return result_dict

    def get_base_hosts(self):
        raise NotImplementedError

    def get_relevant_hosts_list(self, host_list):
        res = []
        for host_name in self._host_executors_dict:
            if self._host_executors_dict[host_name].ip in host_list or host_name in host_list:
                res.append(host_name)
        return res

    def reconnect_host_by_password(self, host_name, user_name, password):
        assert host_name in self._host_executors_dict
        assert not self._host_executors_dict[host_name].is_connected
        return self._host_executors_dict[host_name].reconnect_by_password(user_name, password)

    def add_ice_container_host_executor(self):
        assert ExecutionHelper.is_run_inside_container(), "Please add ice container host executor only if you run inside container"
        self._add_host_executor([Objectives.ICE_CONTAINER], 'ice_container', 'localhost', 'root', is_local=True)

    @staticmethod
    def run_connect_ssh_client(host_executor):
        host_executor.connect_ssh_client()

    def connect_list_of_host_executors(self, host_executors):
        ParallelRunner.run_target_in_parallel(host_executors, BaseHostExecutorFactory.run_connect_ssh_client)

    def connect_all_host_executors_with_retry(self):
        hosts_to_connect = list(self._host_executors_dict.values())
        retry = 0

        while hosts_to_connect and retry < BaseHostExecutorFactory.RETRY_CONNECTION_COUNT:
            retry += 1
            self.connect_list_of_host_executors(hosts_to_connect)

            hosts_to_connect = list([host for host in hosts_to_connect if host.is_connected is False])

            if hosts_to_connect:
                log.log_and_print(
                    "Failed to connect to hosts: {}".format(", ".join([host.host_name for host in hosts_to_connect])))

                if retry < BaseHostExecutorFactory.RETRY_CONNECTION_COUNT:
                    log.log_and_print("Retry connection to failed hosts")

        log.log_and_print(
            "Connection to hosts complete, Starting health check for the connected hosts")
