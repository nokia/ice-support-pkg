from __future__ import absolute_import
from tools import adapter
from HealthCheckCommon.operations import *
import re

from HealthCheckCommon.validator import Validator
from tools.Exceptions import *
from tools.ConfigStore import ConfigStore
from six.moves import map
from six.moves import range


class CPU_affinity_base(Validator):
    objective_hosts = [Objectives.COMPUTES, Objectives.EDGES, Objectives.WORKERS]

    def get_host_type(self):
        roles = self.get_host_roles()
        compute = None

        if Objectives.OVS_COMPUTES in roles:
            compute = "OvsCompute"
        elif Objectives.SRIOV_COMPUTES in roles:
            compute = "SriovPerformanceCompute"
        elif 'DpdkCompute' in roles:
            compute = "DpdkPerformanceCompute"
        elif Objectives.AVRS_COMPUTES in roles:
            compute = "AvrsCompute"
        elif Objectives.EDGES in roles:
            compute = "EdgeBM"
        elif Objectives.WORKERS in roles:
            compute = "WorkerBM"
        return compute

    def is_compute_type(self, list_of_user_conf_roles):

        for role in list_of_user_conf_roles:
            if 'Compute' in role or 'compute' in role:
                return True

        return False

    def is_isolation_scheme_type_is_uniform_in_user_conf(self):
        'check if in user config all the isolation_scheme_type is the same, return true/false and the first scame found '
        if Deployment_type.is_cbis(gs.get_deployment_type()):
            hosts = ConfigStore.get_cbis_user_config()['CBIS']['host_group_config']
        else:
            hosts = ConfigStore.get_cbis_user_config()['host_group_config']

        isolation_scheme_type_set = set()

        computes_role_found = 0
        for host_name in hosts:
            host = hosts[host_name]
            if self.is_compute_type(host.get('role', "")):
                computes_role_found = computes_role_found + 1
                isolation_scheme_type = host.get('cpu_isolation_scheme')
                if not isolation_scheme_type is None:
                    isolation_scheme_type_set.add(isolation_scheme_type)

        if len(isolation_scheme_type_set) == 1:
            return True, isolation_scheme_type_set.pop()

        if len(isolation_scheme_type_set) > 1:
            return False, isolation_scheme_type_set.pop()

        # else
        raise UnExpectedSystemOutput("user_config.yaml issue",
                                     "test if all cpu_isolation_scheme is the same in all computes",
                                     "no cpu_isolation_scheme was found. found -{}- computes".format(
                                         computes_role_found),
                                     "issue in is_isolation_scheme_type_is_uniform_in_user_conf")

    def get_cpu_isolation_scheme(self):
        # compute_type = self.get_compute_type()
        # isolation_scheme_type = ConfigStore.get_cbis_user_config()['CBIS']['host_group_config'][compute_type]['cpu_isolation_scheme']

        # if the cpu_isolation_scheme is the same for all computes roles, I don't maind what is this compute type:
        flg_uniform, isolation_scheme_type = self.is_isolation_scheme_type_is_uniform_in_user_conf()
        if flg_uniform:
            return isolation_scheme_type

        # else
        compute_type = self.get_host_type()
        if Deployment_type.is_cbis(gs.get_deployment_type()):
            host_group_config = ConfigStore.get_cbis_user_config()['CBIS']['host_group_config']
        else:
            host_group_config = ConfigStore.get_cbis_user_config()['host_group_config']
        if host_group_config.get(compute_type):
            isolation_scheme_type = host_group_config[compute_type][
                'cpu_isolation_scheme']
            return isolation_scheme_type

        self._failed_msg = "we do not support this validations for cases where the compute types are not standard and isolation_scheme_type is not the same on all computes types, please perform these tests manually"
        raise NotApplicable("NotApplicable: " + self._failed_msg)

    def get_grub_isolcpu(self):
        out = self.get_output_from_run_cmd("sudo cat /proc/cmdline")
        grub_isolcpus = out.split("isolcpus=")[1].split(" ")[0].split(",")
        return self._separate_the_range(grub_isolcpus)

    def get_systemd_cpu_affinity(self):
        cmd = "sudo cat /etc/systemd/system.conf"
        out = self.get_output_from_run_cmd(cmd)

        cpu_regex = r'^CPUAffinity=([\d\s]+)$'
        matches = re.findall(cpu_regex, out, flags=re.MULTILINE)

        if len(matches) > 1:
            raise UnExpectedSystemOutput(self.get_host_ip(), cmd, out, "Expected at most 1 line that define the cpu "
                                                                       "affinity list.")
        cpu_list = matches[0].split() if len(matches) == 1 else []
        cpu_affinity = list(map(int, cpu_list))  # remove the character 'u' in a list

        return cpu_affinity

    def verify_cpu_isolation_scheme(self):
        isolation_scheme = int(self.get_cpu_isolation_scheme())
        if isolation_scheme == 0:
            if len(self.get_grub_isolcpu()) == 0:
                return False
            return True
        elif isolation_scheme == 1:
            if len(self.get_systemd_cpu_affinity()) == 0:
                return False
            return True

    def get_host_isolated_scheme(self):
        isolation_scheme = int(self.get_cpu_isolation_scheme())
        if isolation_scheme == 0:
            host_isolated_cpus = self.get_grub_isolcpu()
            return host_isolated_cpus
        elif isolation_scheme == 1:
            host_isolated_cpus = self.get_systemd_cpu_affinity()
            return host_isolated_cpus
        else:
            self._failed_msg = "Can't define host isolated CPU's"
            return False

    def _hyphen_separated_sequence(self, range_list):
        # print a hyphen-separated sorted number from list ["2-8",10-14] like ["2,3,4,5,6,7,8","10,11,12,13,14"]
        lst = []
        flat_list = []
        for x in range_list:
            first_num = int(x.split("-")[0])
            last_num = int(x.split("-")[1])
            r_list = list(range(first_num, last_num))
            lst.append(r_list)
            # create one list from several lists
            flat_list = [item for sublist in lst for item in sublist]
        return flat_list

    def _separate_the_range(self, range_list):
        lst_with_dash = []
        pure_comma_lst = []
        for x in range_list:
            if "-" in x:
                lst_with_dash.append(x)
            else:
                pure_comma_lst.append(int(x))
        dashed_lst = self._hyphen_separated_sequence(lst_with_dash)
        return pure_comma_lst + dashed_lst

    def get_nova_conf_vcpu_pin_set(self):
        res, out, err = self.run_cmd(
            'sudo grep "^vcpu_pin_set" /var/lib/config-data/puppet-generated/nova_libvirt/etc/nova/nova.conf')

        if res != 0:
            return None

        nova_conf_vcpu_pin = out.split("vcpu_pin_set = ")[1].split(",")
        return self._separate_the_range(nova_conf_vcpu_pin)

    def get_docker_vcpu_pin_set(self, nova_container):
        docker_or_podman = adapter.docker_or_podman()
        res, out, err = self.run_cmd(
            'sudo {docker_or_podman} exec $(sudo {docker_or_podman} ps -f name={nova_container} -q) grep "^vcpu_pin_set" /etc/nova/nova.conf'.
            format(docker_or_podman=docker_or_podman, nova_container=nova_container), add_bash_timeout=True)

        if res != 0:
            return None

        docker_vcpu_pin = out.split("vcpu_pin_set = ")[1].split(",")
        return self._separate_the_range(docker_vcpu_pin)

    def _is_foreign_groups(self, list_a, list_b):
        for x in list_a:
            if x in list_b:
                return False
        return True


class validate_cpu_isolation_scheme(CPU_affinity_base):

    def set_document(self):
        self._unique_operation_name = "verify_cpu_isolation_scheme"
        self._title = "Validate CPU isolation scheme in use"
        self._failed_msg = "CPU isolation scheme is not in use"
        self._severity = Severity.ERROR

        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION, ImplicationTag.PERFORMANCE]

    def is_validation_passed(self):
        return self.verify_cpu_isolation_scheme()


class validate_cpu_pinning_config(CPU_affinity_base):

    def set_document(self):
        self._unique_operation_name = "validate_cpu_pinning_config"
        self._title = "Check if the nova.conf CPU's properly defined"
        self._failed_msg = ""
        self._severity = Severity.ERROR

        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION, ImplicationTag.PERFORMANCE]

    def verify_cpu_pinning_config(self):
        nova_conf_vcpu_pin_set = self.get_nova_conf_vcpu_pin_set()
        if not nova_conf_vcpu_pin_set:
            self._failed_msg = "The vcpu pining isn't set in /var/lib/config-data/puppet-generated/nova_libvirt/etc/nova/nova.conf config"
            return False

        nova_container = 'nova_virtqemud' if gs.get_version() >= Version.V25 else 'nova_libvirt'
        docker_vcpu_pin_set = self.get_docker_vcpu_pin_set(nova_container)

        if not docker_vcpu_pin_set:
            self._failed_msg = "The vcpu pining isn't set in the docker '{}' container".format(nova_container)
            return False

        if nova_conf_vcpu_pin_set != docker_vcpu_pin_set:
            self._failed_msg = "There is mismatch  between the docker '{}' container and nova.conf file".format(nova_container)
            return False

        return True

    def is_validation_passed(self):
        return self.verify_cpu_pinning_config()


class has_host_isolated_scheme(CPU_affinity_base):
    def set_document(self):
        self._unique_operation_name = "has_host_isolated_scheme"
        self._title = "validate host isolated scheme is defined"
        self._failed_msg = "isolated scheme is not defined"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION, ImplicationTag.PERFORMANCE]

    def is_validation_passed(self):
        if not self.get_host_isolated_scheme():
            return False
        return True


class validate_no_overlap(CPU_affinity_base):

    def is_prerequisite_fulfilled(self):
        if not self.get_nova_conf_vcpu_pin_set():
            return False

        if not self.get_host_isolated_scheme():
            return False

        return True

    def set_document(self):
        self._unique_operation_name = "check_cpu_isolation_and_vcpu_pinning"
        self._title = "Check if hypervisor isolated CPU not overlaped by Nova allowed CPU's"
        self._failed_msg = "There is overlap between nova and isolated CPU's"
        self._severity = Severity.ERROR

        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION, ImplicationTag.PERFORMANCE]

    def diff_between_cpu_pining_to_isolation_cpu(self):
        hypervisor_cpus = self.get_nova_conf_vcpu_pin_set()
        isolated_cpus = self.get_host_isolated_scheme()
        self._failed_msg = "There is overlap between nova and isolated CPU's - isolated_cpus:{} : hypervisor_cpus:{}".format(
            isolated_cpus, hypervisor_cpus)
        return self._is_foreign_groups(hypervisor_cpus, isolated_cpus)

    def is_validation_passed(self):
        return self.diff_between_cpu_pining_to_isolation_cpu()


class ValidateCBISIsolationFileExist(Validator):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.COMPUTES]
    }

    def set_document(self):
        self._unique_operation_name = "verify_cbis_isolation_file"
        self._title = "Validate cbis cpu_isolation file exists"
        self._failed_msg = "cbis cpu_isolation file does not exist."
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION, ImplicationTag.PERFORMANCE]

    def is_validation_passed(self):
        '''
            Validates the existence of the CPU isolation file based on host roles and version.
        '''
        file_path_base = "/usr/share/cbis/data/cbis.cpu_isolation"
        file_path_dpdk = "/usr/share/cbis/data/cbis.dpdk_cpu_isolation"
        missing_paths = []
        file_to_check = file_path_base
        if Objectives.DPDK_COMPUTES in self.get_host_roles() and gs.get_version() >= Version.V25:
            file_to_check = file_path_dpdk

        if not self.file_utils.is_file_exist(file_to_check):
            missing_paths.append(file_to_check)

        if missing_paths:
            self._failed_msg += "Missing file path in your cluster: {}".format(file_to_check)
            return False

        return True
