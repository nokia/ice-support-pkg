from __future__ import absolute_import
from tools import paths
from tools.Exceptions import UnExpectedSystemTimeOut
from tools.ExecutionModule.HostExecutorsFactory.BaseHostExecutorsFactory import BaseHostExecutorFactory
from tools.ExecutionModule.execution_helper import ExecutionHelper
from tools.global_enums import *
from tools import global_logging


class CbisHostExecutorFactory(BaseHostExecutorFactory):
    SSH_USER = "cbis-admin"
    SSH_KEY = "/home/stack/.ssh/id_rsa"
    SINGLE_ROLES_TO_ADD = {Objectives.CONTROLLERS: Objectives.ONE_CONTROLLER,
                           Objectives.STORAGE: Objectives.ONE_STORAGE}

    def __init__(self):
        BaseHostExecutorFactory.__init__(self)
        self.hosts_str = None
        self.uc_host_name = ExecutionHelper.get_local_host_name().split('.')[0]
        self._set_roles()

    def _is_all_roles_where_set_correctly(self):
        factory_roles = list(self._roles.keys())
        global_enums_roles = Objectives.get_available_types(Deployment_type.CBIS)
        intersection = PythonUtils.list_intersection(factory_roles, global_enums_roles)
        return len(intersection) == len(factory_roles)

    def _set_roles(self):
        # TODO: map between role and detection function, assert roles valid
        self._roles = {
            Objectives.COMPUTES: 'Compute',
            Objectives.STORAGE: 'CephStorage',
            Objectives.CONTROLLERS: 'Control',
            Objectives.DPDK_COMPUTES: 'DpdkCompute',
            Objectives.SRIOV_COMPUTES: 'Sriov',
            Objectives.HYP: 'hypervisor',
            Objectives.MONITOR: 'Monitoring',
            Objectives.AVRS_COMPUTES: 'AvrsCompute'
        }

    def parse_ansible_inventory(self, inventory_path):
        result_dict = {}
        inventory_groups = self._find_inventory_groups(inventory_path)
        for role in self._roles:
            role_name = self._roles[role]
            group = inventory_groups.get(role_name)
            if group:
                result_dict[role] = {}
                key_file = group.get("vars", {}).get('ansible_ssh_private_key_file')
                user_name = group.get("vars", {}).get('ansible_user')
                hosts = group.get("hosts", {})
                for host, host_data in list(hosts.items()):
                    host_name = str(host)
                    host_vars = {
                        'user_name': host_data.get('ansible_user') or user_name,
                        'ip': host_data.get('ansible_ssh_host') or host_name,
                        'key_file': key_file,
                        'roles': [role]
                    }
                    if role == Objectives.HYP:
                        host_name = 'hypervisor'
                    else:
                        host_vars['roles'].append(Objectives.ALL_HOSTS)
                    result_dict[role][host_name] = host_vars

        return result_dict

    # for cbis 18, there is an ansible bug which includes
    #    computes as hci even the architecture is non-hci
    def filter_storage_role_non_hci(self):
        storage_nodes = self.get_host_executors_by_roles([Objectives.STORAGE])
        hci_nodes = [compute for compute in storage_nodes if Objectives.COMPUTES in storage_nodes[compute].roles]
        is_non_hci = len(hci_nodes) != len(storage_nodes)
        if is_non_hci:
            for host_name in hci_nodes:
                self._host_executors_dict[host_name].roles.remove(Objectives.STORAGE)

    def add_undercloud_host_executor(self):
        self._add_host_executor([Objectives.UC, Objectives.ALL_HOSTS],
                                self.uc_host_name, 'localhost', 'stack', is_local=False,
                                key_file=ExecutionHelper.get_path_to_pkey_from_container_to_host())

    def add_ovs_compute_role(self):
        computes = self.get_host_executors_by_roles(roles=[Objectives.COMPUTES])
        for compute in computes:
            if 'ovs' in compute.lower():
                self._host_executors_dict[compute].add_role(Objectives.OVS_COMPUTES)

    def _build_host_executors_dict(self, inventory_path, *args):
        if not inventory_path:
            if self._build_host_executors_dict_by_command(args[0]):
                return
            global_logging.log_and_print("Failed to run openstack commands to find servers list.\n"
                                         "Use by default the hosts file from: {}\n"
                                         "If you want another hosts file, pls provide full path to the hosts "
                                         "inventory file by flag:\n"
                                         "--path-to-cbis-hosts-file <path>".format(paths.CBIS_HOSTS_FILE))
            inventory_path = paths.CBIS_HOSTS_FILE

        self._build_host_executors_dict_from_inventory_path(inventory_path)

    def _build_host_executors_dict_from_inventory_path(self, inventory_path):
        roles_host_dict = self.parse_ansible_inventory(inventory_path)
        for role in roles_host_dict:
            for host_name in roles_host_dict[role]:
                host_vars = roles_host_dict[role][host_name]
                self._add_host_executor(
                    host_vars['roles'],
                    host_name,
                    host_vars['ip'],
                    host_vars['user_name'],
                    key_file=host_vars['key_file']
                )
        self.add_ovs_compute_role()
        self.add_undercloud_host_executor()
        self.filter_storage_role_non_hci()

    def _build_host_executors_dict_by_command(self, base_conf):
        self.add_undercloud_host_executor()
        _, uc_host_executor = self.get_host_executor_by_host_name(self.uc_host_name)
        uc_host_executor.connect_ssh_client()
        nova_list = self._get_server_list(uc_host_executor)

        if nova_list is None:
            return False
        ironic_list = self._get_baremetal_nodes(uc_host_executor)

        if ironic_list is None:
            return False
        roles_per_hg = self._get_roles_per_host_group(base_conf)

        for ironic_host in ironic_list:
            nova_match_host_list = list([host for host in nova_list if host["ID"] == ironic_host["Instance UUID"]])

            if not len(nova_match_host_list):
                global_logging.log_and_print("No match nova host for ironic host: {}".format(ironic_host))
                continue
            nova_host = nova_match_host_list[0]
            host_group = nova_host["Flavor"]
            roles = self._convert_roles(roles_per_hg[host_group])
            roles.append(Objectives.ALL_HOSTS)

            if ironic_host["Maintenance"]:
                roles = [Objectives.MAINTENANCE]

            self._add_host_executor(
                roles,
                nova_host["Name"],
                self._get_ip_from_server_network(nova_host["Networks"]),
                self.SSH_USER,
                key_file=self.SSH_KEY
            )
        self._add_hypervisor_host_executor()
        self.add_ovs_compute_role()
        self.filter_storage_role_non_hci()

        return True

    def get_base_hosts(self):
        return [Objectives.HYP, Objectives.UC]

    def _convert_roles(self, roles_list):
        res = []

        for role in roles_list:
            res.append(list(self._roles.keys())[list(self._roles.values()).index(role)])

        return res

    def _add_hypervisor_host_executor(self):
        self._add_host_executor(
            [Objectives.HYP],
            "hypervisor",
            "172.31.7.254",
            self.SSH_USER,
            key_file=self.SSH_KEY
        )

    def _get_baremetal_nodes(self, uc_host_executor):
        host_operator = ExecutionHelper.get_hosting_operator(False)
        cmd = ("source {}; openstack baremetal node list -c 'Instance UUID' -c Maintenance -f json --quote none".format(
            host_operator.system_utils.get_stackrc_file_path()))

        try:
            exit_code, server_list, err = uc_host_executor.execute_cmd(cmd, timeout=30)
        except UnExpectedSystemTimeOut:
            return None

        if exit_code != 0:
            return None

        res = json.loads(server_list)

        for line in res:
            if "Instance UUID" not in list(line.keys()) or "Maintenance" not in list(line.keys()):
                return None

        return res

    def _get_server_list(self, uc_host_executor):
        host_operator = ExecutionHelper.get_hosting_operator(False)
        stackrc_path = host_operator.system_utils.get_stackrc_file_path()
        cmd = "source {}; openstack server list -c ID -c Name -c Networks -c Flavor -f json --quote none".format(stackrc_path)

        try:
            exit_code, server_list, err = uc_host_executor.execute_cmd(cmd, timeout=30)
            if exit_code != 0:
                cmd = "metalsmith -f json list | jq -r '[.[] | {Name:.hostname, ID:.node.instance_id, Networks:.ip_addresses.ctlplane, Flavor:.node.properties.host_group}]'"
                exit_code, server_list, err = uc_host_executor.execute_cmd(cmd, timeout=30)
        except UnExpectedSystemTimeOut:
            return None

        if exit_code != 0:
            return None

        res = json.loads(server_list)

        for line in res:
            if "Name" not in list(line.keys()) or "Networks" not in list(line.keys()) or "Flavor" not in list(line.keys()):
                return None

        return res

    def _get_ip_from_server_network(self, server_network):
        if '=' in server_network:
            return server_network.split("=")[1]
        else:
            return server_network[0]

    def _get_roles_per_host_group(self, uc_data):
        roles_per_host_group = {}
        host_groups = set(uc_data.get('CBIS').get('host_group_config').keys())

        for host_group in host_groups:
            roles_list = uc_data.get('CBIS').get('host_group_config').get(host_group).get('role')

            if roles_list is None:
                continue

            # Add CephStorage role only if enable_ceph_storage is true
            self._fix_roles_list(host_group, roles_list, uc_data)
            roles_per_host_group.update({host_group: roles_list})

        return roles_per_host_group

    def _fix_roles_list(self, host_group, roles_list, uc_data):
        if 'CephStorage' in roles_list:
            storage_config = uc_data.get('CBIS').get('host_group_config').get(host_group).get('storage_config')
            if storage_config is None:
                enable_ceph_storage = None
            else:
                enable_ceph_storage = storage_config.get('enable_ceph_storage')

            if not enable_ceph_storage and not host_group == 'Storage':
                roles_list.remove('CephStorage')
        # Use base compute role for all-in-one computes
        if 'AioDpdkCompute' in roles_list:
            roles_list.remove('AioDpdkCompute')
            roles_list.append('DpdkCompute')
        if 'AioSriovCompute' in roles_list:
            roles_list.remove('AioSriovCompute')
            roles_list.append('Sriov')

    def _find_inventory_groups(self, inventory_path):
        with open(inventory_path) as f:
            file_content = f.read()

        # Create dict like: {'Sriov': 'overcloud-sriovperformancecompute-cbis22-0 ansible_ssh_host=172.31.1.45\n\n',
        # 'Sriov:vars': 'ansible_user=cbis-admin\nansible_ssh_private_key_file=/home/stack/.ssh/id_rsa\n\n' ...}
        role_data_dict = dict(re.findall(r"\[(.*)\]\n([0-9a-zA-Z.=\-_/\s]+\n*)*",
                                         file_content,  re.MULTILINE & re.DOTALL))
        res = {}
        for role, role_data in list(role_data_dict.items()):
            if role.endswith(":vars"):
                res[role[:-5]] = res.get(role[:-5], {})
                res[role[:-5]]["vars"] = self._get_vars_data(role_data)
            else:
                res[role] = res.get(role, {})
                res[role]["hosts"] = self._get_hosts_data(role_data)

        return res

    def _get_vars_data(self, role_data):
        return self._get_dict_from_assignment_str(role_data)

    def _get_hosts_data(self, role_data):
        res = {}

        for line in role_data.splitlines():
            if line:
                split_line = line.split()
                assert len(split_line) >= 2
                res[split_line[0]] = self._get_dict_from_assignment_str(line[len(split_line[0]):])

        return res

    def _get_dict_from_assignment_str(self, assignment_str):
        return dict(re.findall("(.*)=(.*)", assignment_str.replace(" ", "\n")))
