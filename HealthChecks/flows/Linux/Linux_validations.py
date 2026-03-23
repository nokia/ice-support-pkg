from __future__ import absolute_import
import six

from tools import adapter
from HealthCheckCommon.operations import *
import re
import yaml

from HealthCheckCommon.validator import Validator
from tools.ConfigStore import ConfigStore
from tools.python_versioning_alignment import to_unicode
from flows.Linux.Services_requirements_list import ServicesRequirements
from tools.Conversion import Conversion
from tools.python_utils import PythonUtils
import tools.sys_parameters as sys_parameters
import tools.global_logging as gl
from datetime import datetime, timedelta
import time
from six.moves import range


#Slab memory leak initiated due to nested namespace cleanup, please reboot the server when possible

class NestedNamespaceMemoryLeak(Validator):
    objective_hosts = [Objectives.ALL_NODES, Objectives.ALL_HOSTS, Objectives.HYP, Objectives.DEPLOYER,Objectives.MAINTENANCE]

    def set_document(self):
        self._unique_operation_name = "nested_namespace_memory_leak"
        self._title = "Look for slab memory leak initiated due to nested namespace cleanup"
        self._failed_msg = " 'Memory leak initiated due to nested namespace cleanup was detected"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.SYMPTOM, ImplicationTag.RISK_RESOURCE_CLEANING_RECOMMENDED]

    def is_validation_passed(self):
        ret, out, err = self.run_cmd("dmesg  |grep -c unregister_netdevice", add_bash_timeout=True)
        if ret == 1:
            return True
        else:
            return False


class SystemdServicesStatus(Validator):
    '''go over all the service in the systemctl and look for failers
    if we are on the UC - (almost) all failers are critical
    if we are on OVS - we check if this service is in the list of critical servises
    if so - we check if it was changed by knowe docker - if not - it is cretical failer)
    '''
    objective_hosts = [Objectives.ALL_HOSTS, Objectives.ALL_NODES]

    def set_document(self):
        self._unique_operation_name = "systmed_services_health_check"
        self._title = "Verify systemd services are in running state"
        self._failed_msg = "TBD"
        self._severity = Severity.NOTIFICATION
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]


    HARMLESS_LIST = ["NetworkManager-wait-online",
                     "dhcp-interface",
                     "Resets System Activity Logs",
                     "alarm-manager",
                     "sysstat"]

    def _get_service_names(self, line):
        line.strip()
        words = line.split()

        # replaceing the Non-ASCII character "\xe2\x97\x8f" with ""
        # the dot in '*NetworkManager-wait-online.service' is read as \xe2\x97\x8f
        pretty_words = [word.strip() for word in words if not (six.text_type(word.strip()) == u'\u25cf')]
        one_failed_services_full = " ".join(pretty_words)
        if one_failed_services_full:
            one_failed_services = pretty_words[0]
        else:
            one_failed_services = None
        return one_failed_services, one_failed_services_full

    def _find_in_services_requirment(self, one_failed_services):

        myServicesRequirements = ServicesRequirements()
        critical_services_map = myServicesRequirements.get_services_requirements()

        for service in critical_services_map:
            service_name = critical_services_map[service]['service_name']

            if not service_name is None:

                if service_name == one_failed_services or \
                        service_name + ".service" == one_failed_services or \
                        "/" + service_name == one_failed_services:
                    return True, service_name, critical_services_map[service]["roles"]

        return False, None, None

    def _should_run_on_this_host(self, roles):
        list_intersection = PythonUtils.list_intersection(self.get_host_roles(), roles)
        return len(list_intersection) > 0

    def _is_in_harmless_list(self, one_failed_services):
        for services in self.HARMLESS_LIST:
            if services in one_failed_services:
                return True
        return False

    def _check_if_container_is_running(self, container_name):
        docker_or_podman = adapter.docker_or_podman()
        docker_ps_cmd = "sudo {docker_or_podman} ps -a --format 'table {{{{.Names}}}} {{{{.Status}}}}'".format(docker_or_podman=docker_or_podman)
        return_code, out, err = self.run_cmd("{} | grep -i Up ".format(docker_ps_cmd), timeout=30)
        if container_name in out:
            return True
        return False

    def is_validation_passed(self):
        critical_failed_services = []
        warning_failed_services = []
        notifacation_failed_services = []

        return_code, out, err = self.run_cmd("systemctl list-units | grep failed", timeout=60)

        if self.get_host_roles() == Objectives.UC:
            self._severity = Severity.CRITICAL

        if return_code > 0:
            return True
        if out:

            lines = out.split("\n")
            for line in lines:

                one_failed_services, one_failed_services_full = self._get_service_names(line)

                if one_failed_services and not self._is_in_harmless_list(one_failed_services):
                    # check if this is on the service_of_risk_list
                    is_found, container_name, roles = self._find_in_services_requirment(one_failed_services)
                    if is_found:
                        if not self._should_run_on_this_host(roles):
                            notifacation_failed_services.append(one_failed_services_full)
                        elif container_name:
                            if self._check_if_container_is_running(container_name):
                                notifacation_failed_services.append(one_failed_services_full)
                            else:
                                critical_failed_services.append(one_failed_services_full)
                        else:
                            critical_failed_services.append(one_failed_services_full)
                    else:
                        warning_failed_services.append(one_failed_services_full)

                    self._failed_msg = 'The following services are at failed state:\n critical: {}\n warning: {}\n notification: {} '.format \
                        (critical_failed_services, warning_failed_services, notifacation_failed_services)

        if len(warning_failed_services) > 0:
            self._severity = Severity.WARNING
        if len(critical_failed_services):
            self._severity = Severity.CRITICAL

        if len(critical_failed_services) > 0 or len(warning_failed_services) or len(notifacation_failed_services):
            return False
        else:
            return True


# -----------------------------------------------------------------------------------------------------------------------
class is_host_reachable(Validator):
    objective_hosts = [Objectives.ALL_NODES, Objectives.ALL_HOSTS, Objectives.MAINTENANCE]

    def set_document(self):
        self._unique_operation_name = "is_host_reachable"
        self._title = "Verify can run simple command (echo) on host"
        self._failed_msg = "host {} not reachable".format(self.get_host_ip())
        self._severity = Severity.ERROR

        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        ok = self.run_cmd_return_is_successful("echo 'regards to host'")
        return ok

class VerifyDuNotHang(Validator):
    objective_hosts = [Objectives.ALL_NODES, Objectives.ALL_HOSTS, Objectives.HYP, Objectives.DEPLOYER,Objectives.MAINTENANCE]

    def set_document(self):
        self._unique_operation_name = "verify_du_not_hang"
        self._title = "Verify 'du' not hang"
        self._failed_msg = "'du' commands hang"
        self._severity = Severity.ERROR

        self._implication_tags = [ImplicationTag.SYMPTOM]

    def is_validation_passed(self):
        try:
            self.run_cmd("sudo du > /dev/null", add_bash_timeout=True)
        except UnExpectedSystemTimeOut:
            return False
        return True

# -----------------------------------------------------------------------------------------------------------------------
class CheckDnsResolutionNcs(Validator):
    #objective_hosts = [Objectives.MASTERS]
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.MASTERS],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.MASTERS],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.MASTERS]
    }

    def set_document(self):
        self._unique_operation_name = "is_dns_valid_on_all_hosts_NCS"
        self._title = "Verify dns is valid in NCS"
        self._failed_msg = "DNS at {} not valid".format(self.get_host_ip())
        self._severity = Severity.ERROR

        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        # in this case if no dns this will fial with time out

        return_code, out, err = self.run_cmd("nslookup bcmt-registry -timeout=1", timeout=60)
        if out and "Server:" in out:
            cmd = "nslookup bcmt-registry | grep -i 'Address' | head -1"
            cmd_output = self.get_output_from_run_cmd(cmd)
            split_err_msg = "The output should contain '{}'."
            if ":" not in cmd_output:
                raise UnExpectedSystemOutput(ip=self.get_host_ip(), cmd=cmd, output=cmd_output,
                                             message=split_err_msg.format(':'))
            array = cmd_output.split(":", 1)
            ip_port = array[1].strip()
            if "#" not in ip_port:
                raise UnExpectedSystemOutput(ip=self.get_host_ip(), cmd=cmd, output=cmd_output,
                                             message=split_err_msg.format('#'))
            array = ip_port.split("#")
            dns_ip = array[0]
            dns_port = array[1]
            nameservers_list = []
            rsolv_conf_dns_count = 0
            coredns_dns_flag = 0
            return_code, out, err = self.run_cmd("sudo cat /etc/resolv.conf", timeout=60)
            if return_code == 0:
                content_resolv_conf = out.splitlines()
                for line in content_resolv_conf:
                    if line.startswith("nameserver"):
                        nameserver_ip = line.split()[1].strip()
                        if nameserver_ip.endswith('.'):
                            nameserver_ip = nameserver_ip[:-1]
                        nameservers_list.append(nameserver_ip)

                for nameserver_ip in nameservers_list:
                    if nameserver_ip == dns_ip:
                        rsolv_conf_dns_count = rsolv_conf_dns_count + 1

                if rsolv_conf_dns_count > 0:
                    for nameserver_ip in nameservers_list:
                        nameserver_ip_pattern = nameserver_ip
                        if PythonUtils.is_ipv6(nameserver_ip):
                            nameserver_ip_pattern = '\\[{}\\]'.format(nameserver_ip)
                        cmd = "sudo ss -tulpn | grep '{}:{}' | grep -i 'coredns' | wc -l".format(
                            nameserver_ip_pattern, dns_port)
                        cmd_output = self.get_output_from_run_cmd(cmd).strip()
                        if int(cmd_output) > 0:
                            coredns_dns_flag = coredns_dns_flag + 1

                    if coredns_dns_flag > 0:
                        return True
                    else:
                        return False
                else:
                    return False
        return False


class CheckDnsResolutionCbis(Validator):
    objective_hosts = [Objectives.CONTROLLERS]

    def set_document(self):
        self._unique_operation_name = "is_dns_valid_on_all_hosts_CBIS"
        self._title = "Verify dns is valid in CBIS"
        self._failed_msg = "dns at {} not valid".format(self.get_host_ip())
        self._severity = Severity.ERROR

        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        status = False
        fqdn_list = ['www.google.com', 'google.com']
        for fqdn in fqdn_list:
            exit_code, out, err = self.run_cmd("sudo dig {} +nocomments  +noadditional +noanswer".format(fqdn))
            if 'no servers could be reached' in out:
                continue
            matched = re.search(r".*SERVER*", out)
            if (matched):
                status = True
                break
        return status


# -----------------------------------------------------------------------------------------------------------------------
class TooManyOpenFilesCheck(Validator):
    objective_hosts = [Objectives.ALL_HOSTS, Objectives.ALL_NODES, Objectives.MAINTENANCE]

    def set_document(self):
        self._unique_operation_name = "too_many_open_files_per_proc"
        self._title = "Validate the opened file descriptors are not exceeded the limit per proc"
        self._failed_msg = "TBD"
        self._severity = Severity.WARNING

        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.RISK_GARBAGE_CLEANING_RECOMMENDED, ImplicationTag.APPLICATION_DOMAIN]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        check_error_in_log_cmd = "sudo grep -n -E 'Too many open files' /var/log/messages"
        exit_code, out, err = self.run_cmd(check_error_in_log_cmd)
        is_a_real_error = False
        for line in out.splitlines():
            if 'grep' not in line:
                is_a_real_error = True
                break

        if is_a_real_error:
            # going over all the processes only if evidence to Too many open file run this for every proc
            open_files_limit_per_process_cmd = "ulimit -n"
            exit_code, out, err = self.run_cmd(open_files_limit_per_process_cmd)
            opened_files_limit = int(out)
            get_exceeded_processes_cmd = \
                "sudo find /proc/ | grep -E \"/proc/[0-9]+/fd/\" " \
                "| sed 's/\\/fd\\/.*/\\/fd\\//g' | sort | uniq -c | sort -n -r -k1 "
            exit_code, out, err = self.run_cmd(get_exceeded_processes_cmd)
            if not out:
                raise UnExpectedSystemOutput(self.get_host_name(), get_exceeded_processes_cmd, "", "empty output")
            result = []
            processes_fd_lines = out.splitlines()
            for line in processes_fd_lines:
                fd_count_str, pid = re.findall("\\d+", line)
                fd_count = int(fd_count_str)
                if fd_count > opened_files_limit:
                    check_specific_process_limit_cmd = 'sudo prlimit -p {} --nofile -o HARD --noheadings'.format(pid)
                    out = self.get_output_from_run_cmd(check_specific_process_limit_cmd)
                    specific_limit = int(out)
                    if fd_count > specific_limit:
                        self._severity = Severity.ERROR
                        cmd_get_name = "grep Name /proc/{}/status".format(pid)
                        exit_code, out, err = self.run_cmd(cmd_get_name)
                        if exit_code == 0 and out:
                            name = out.split()[1]
                        else:
                            name = "NA"
                        result.append("proc name '{}' pid {} has {} open files. limit is {}".format(name, pid,
                                                                                                    fd_count_str,
                                                                                                    specific_limit))
                else:
                    # output is sorted by the count, so if the count is less than limit,
                    # the next counts are smaller so no need to check them
                    break
            if len(result):
                exceeded_processes_str = yaml.safe_dump(result, default_flow_style=False)
                self._failed_msg = "following processes opened files limit was exceeded:\n {}".format(
                    exceeded_processes_str)
                return False
            else:
                return True

        return True


class RpmdbVerify(Validator):
    #depricated
    objective_hosts = [Objectives.ALL_HOSTS, Objectives.ALL_NODES]

    def set_document(self):
        self._unique_operation_name = "rpmdb_verify"
        self._title = "Verify rpmdb"
        self._failed_msg = "rpmdb verification failed"
        self._msg = "RPM Database failed validation. Package installation and rpm related healthchecks may fail."
        self._severity = Severity.WARNING

        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        return self.run_cmd_return_is_successful("/usr/lib/rpm/rpmdb_verify /var/lib/rpm/Packages")


class SelinuxMode(Validator):
    objective_hosts = [Objectives.ALL_HOSTS, Objectives.ALL_NODES]

    def set_document(self):
        self._unique_operation_name = "selinux_mode"
        self._title = "selinux enforcing mode"
        self._msg = "In production environments, It is highly recommended that Selinux is set to enforce mode .\n" \
                    "In non-production environments, selinux MAY BE set to permissive for testing.\n" \
                    "selinux MUST NOT be disabled. Systems with selinux disabled are not secure!"
        self._failed_msg = "selinux is not set to enforcing"
        self._severity = Severity.WARNING

        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]
        self._blocking_tags = []

    def is_validation_passed(self):
        cmd = 'sudo /usr/sbin/getenforce'
        stdout = self.get_output_from_run_cmd(cmd)
        mode = stdout.strip().lower()

        if mode == 'enforcing':
            return True
        elif mode == 'permissive':
            self._severity = Severity.ERROR
            self._failed_msg = 'selinux in permissive mode'
            return False
        elif mode == 'disabled':
            self._severity = Severity.CRITICAL
            self._failed_msg = 'selinux is disabled'
            return False
        else:
            raise UnExpectedSystemOutput(self.get_host_name(), cmd, "selinux mode unknown {}".format(mode))


class TooManyProcessesCheck(Validator):
    objective_hosts = [Objectives.ALL_HOSTS, Objectives.ALL_NODES, Objectives.MAINTENANCE]

    def set_document(self):
        self._unique_operation_name = "too_many_processes_per_user"
        self._title = "Validate actual amount of processes haven't exceeded the limit per user"
        self._failed_msg = ""
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.RISK_GARBAGE_CLEANING_RECOMMENDED]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        max_proc_per_user = self.get_config_max_proc()
        actual_proc_per_user = self.get_actual_max_proc()
        proc_status = self.validate_max_proc_per_user(actual_proc_per_user, max_proc_per_user)
        if proc_status["over_max_result"]:
            self._severity = Severity.ERROR
            exceeded_processes_str = yaml.safe_dump(proc_status["over_max_result"], default_flow_style=False)
            self._failed_msg = "Following users had exceeded the limit of max" + \
                               " allowed processes:\n {}".format(exceeded_processes_str)
        if proc_status["close_max_result"]:
            self._severity = Severity.WARNING
            exceeded_processes_str = yaml.safe_dump(proc_status["close_max_result"], default_flow_style=False)
            self._failed_msg += "Following users had reached more than 90% of max" + \
                                " allowed processes:\n {}".format(exceeded_processes_str)
        if proc_status["over_max_result"] or proc_status["close_max_result"]:
            return False
        return True

    def get_config_max_proc(self):
        configured_max_proc_per_user_cmd = "cat /etc/security/limits.d/20-nproc.conf | grep nproc"
        out = self.get_output_from_run_cmd(configured_max_proc_per_user_cmd)
        max_proc_per_user = {}
        for line in out.splitlines():
            if len(line.split()) < 4:
                raise UnExpectedSystemOutput(self.get_host_ip(), configured_max_proc_per_user_cmd, out, "Expected to have atleast 4 columns on command output")
            user = line.split()[0]
            nproc_limit = line.split()[3]
            max_proc_per_user[user] = nproc_limit
        return max_proc_per_user

    def get_actual_max_proc(self):
        actual_max_proc_per_user_dict = {}
        actual_max_proc_per_user_cmd = "ps auxwwwm | awk ' { print $1 }' | sort | uniq -c |sort -n -r"
        out = self.get_output_from_run_cmd(actual_max_proc_per_user_cmd)
        for line in out.splitlines():
            actual_max_proc = line.split()[0]
            user = line.split()[1]
            if not actual_max_proc.isdigit():
                raise UnExpectedSystemOutput(self.get_host_ip(), actual_max_proc_per_user_cmd, out,
                                             "Amount of processes for user '{}' should be an integer value, while it's actually {}".format(user, actual_max_proc))
            actual_max_proc_per_user_dict[user] = actual_max_proc
        return actual_max_proc_per_user_dict

    def validate_max_proc_per_user(self, actual_proc, max_config_proc):
        proc_status = {}
        proc_status["over_max_result"] = []
        proc_status["close_max_result"] = []
        for user in actual_proc:
            if user not in max_config_proc:
                limit_max_proc = max_config_proc['*']
            else:
                limit_max_proc = max_config_proc[user]
            if limit_max_proc == 'unlimited':
                continue
            if int(actual_proc[user]) > int(limit_max_proc):
                proc_status["over_max_result"].append("User '{}' actual uses {} processes. Limit is {}".format(
                    user, actual_proc[user], limit_max_proc))
            percent_in_use = float(actual_proc[user]) / float(limit_max_proc) * 100
            if percent_in_use > 90:
                proc_status["close_max_result"].append("User '{}' actual uses {} processes. Limit is {}".format(
                    user, actual_proc[user], limit_max_proc))
        return proc_status


class Filesystem_is_not_btrfs(Validator):
    objective_hosts = [Objectives.HYP]

    def set_document(self):
        self._unique_operation_name = "filesystem_not_btrfs"
        self._title = "Verify filesystem in hypervisor is not btrfs"
        self._failed_msg = "In case of full disk, df command does not show correct information."
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]

    def is_validation_passed(self):
        list_block = self.get_output_from_run_cmd("lsblk -f | grep -w /")
        return not "btrfs" in list_block


class SystemCheckDentryCache(Validator):
    '''
    There are 3 kinds of directory entries (dentry) in the cache: used, unused and negative.
    Used dentries are never dropped. Unused and negative dentries are reclaimed when system
    runs low on memory. Unused dentries are limited be the inode number, however negative
    dentries can grow unlimited. This is our problem, we need to check it does not grow too
    big.
    Version <= Version.V19A: Based on field experience 20% total does not cause an issue, so setting failed
    condition to 50G and 80G.
    Version > Version.V19A: Red Hat recommendation is  to limit _negative dentries_ to 0.1-10% of total system
    memory
    '''
    objective_hosts = [Objectives.CONTROLLERS]

    def set_document(self):
        self._unique_operation_name = "check_dentry_cache"
        self._title = "Check Dentry Cache"
        self._failed_msg = "Dentry cache too large. May impact system performance and/or stability"
        self._severity = Severity.NOTIFICATION
        self._implication_tags = [ImplicationTag.PERFORMANCE]

    def is_validation_passed(self):
        self.add_to_validation_log("begin dentry cache check")
        state = self.get_output_from_run_cmd("cat /proc/sys/fs/dentry-state")
        self.add_to_validation_log("Dentry state found: {}".format(state))
        total_system_memory = self.get_output_from_run_cmd("cat /proc/meminfo | grep MemTotal")
        self.add_to_validation_log("Total memory found: {}".format(total_system_memory))
        total_system_memory_bytes = self.parse_to_int(
            PythonUtils.get_the_n_th_field(total_system_memory, 2)) * Conversion.KIBI_BYTE
        result = None
        if gs.get_version() <= Version.V19A:
            result = self.validate_lower_kernel_version(total_system_memory_bytes, state)
        else:
            result = self.validate_new_kernel_version(total_system_memory_bytes, state)
        self.add_to_validation_log("finish dentry cache check")
        return result

    def validate_lower_kernel_version(self, total_system_memory_bytes, state):
        kernel_dentry_line = self.get_output_from_run_cmd("sudo cat /proc/slabinfo | grep dentry")
        dentry_num_objs = self.parse_to_int(PythonUtils.get_the_n_th_field(kernel_dentry_line, 3))
        dentry_obj_size_bytes = self.parse_to_int(PythonUtils.get_the_n_th_field(kernel_dentry_line, 4))

        dentry_cache_size_bytes = dentry_obj_size_bytes * dentry_num_objs
        dentry_cache_size_output = Conversion.convert_bytes_to_output_text(dentry_cache_size_bytes)
        self.add_to_validation_log("In this version only the total DEntry cache size " +
                                   "can be checked. Found bytes size: {}".format(dentry_cache_size_bytes))

        unused = int(state.split()[1])
        unused_size_bytes = unused * dentry_obj_size_bytes
        unused_size_gigas = unused_size_bytes / Conversion.GIBI_BYTE     # 1024**3
        dentry_cache_percent = (dentry_cache_size_bytes * 100) / float(total_system_memory_bytes)
        self._details = "Total dentry cache size is {}. It should be less than 10% of total system memory.".format(
            dentry_cache_size_output)
        if unused_size_gigas >= 50:
            self._severity = Severity.WARNING
        self.add_to_validation_log("Total DEntry cache size is expected to be below 20%. Calculated: {0:.3g}%".format(
            dentry_cache_percent))
        return dentry_cache_percent < 20

    def validate_new_kernel_version(self, total_system_memory_bytes, state):
        dentry_negative_size = self.parse_to_int(PythonUtils.get_the_n_th_field(state, 5))
        dentry_negative_size_output = Conversion.convert_bytes_to_output_text(dentry_negative_size)
        self.add_to_validation_log("Negtive dentry cache size is expected to be less than 10%. Found size: {}.".format(
            dentry_negative_size))
        self._details = "Total dentry negative cache size is {}. It should be less than 10% of total system memory.".\
            format(dentry_negative_size_output)
        # Red Hat suggestion is to limit DEntry cache at 10%. This is our new fail condition.
        dentry_cache_percent = (dentry_negative_size * 100) / float(total_system_memory_bytes)
        if dentry_cache_percent > 10:
            self._severity = Severity.WARNING
        if dentry_cache_percent > 20:
            self._severity = Severity.ERROR
        elif dentry_cache_percent > 30:
            self._severity = Severity.CRITICAL
        self.add_to_validation_log("Negative DEntry cache size is expected to be" +
                                   " below 10%. Calculated: {0:.3g}%".format(dentry_cache_percent))
        return dentry_cache_percent < 11


class verify_vm_drop_cache(Validator):
    '''
        This validation is not in use anymore , however we are keeping this code here for future enhancement if required.
        related JIRA : ICET-1447 , ICET-1745
        '''
    objective_hosts = [Objectives.COMPUTES, Objectives.STORAGE]

    def set_document(self):
        self._unique_operation_name = "verify_vm_drop_cache"
        self._title = "Verify VM drop Cache set on CBIS Compute and Storage nodes"
        self._failed_msg = "VM drop cache is set on this node, Please set it to default value '0'"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]

    def is_validation_passed(self):
        cmd = "sudo cat /proc/sys/vm/drop_caches"
        out = self.get_int_output_from_run_cmd(cmd)
        if (int(out)) == 0:
            return True
        else:
            return False



class Mellanox_driver_version_validation(Validator):
    objective_hosts = {Deployment_type.CBIS: [Objectives.HYP, Objectives.ALL_HOSTS, Objectives.MAINTENANCE],
                       Deployment_type.NCS_OVER_BM: [Objectives.ALL_NODES]}

    def set_document(self):
        self._unique_operation_name = "Mellanox_driver_version_validation"
        self._title = "Verify mellanox driver version is not 5.4-1.0.3"
        self._failed_msg = "Found Mellanox problematic driver version 5.4-1.0.3 "
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]

    def is_validation_passed(self):
        lspci_cmd = "sudo /sbin/lspci | egrep -i 'ethernet|infiniband' | grep -iv 'virtual function'"
        lspci_out = self.get_output_from_run_cmd(lspci_cmd)
        if 'Mellanox' in lspci_out:
            pci_ids = [line.split(" ")[0].strip()
                    for line in lspci_out.strip().split("\n") if 'Mellanox' in line]
            get_nics_cmd = "sudo ls -l /sys/class/net/* |egrep -v 'br|vlan|vxlan|lo|^q|ovs|tap|openvswitch|veth|tun|bridge|bond|docker'"
            get_nics_cmd_out = self.get_output_from_run_cmd(get_nics_cmd)
            nics = get_nics_cmd_out.strip().split('\n')
            phy_nics_list = []
            for pci_id in pci_ids:
                for nic in nics:
                    if pci_id in nic:
                        phy_nics_list.append(nic)
            phy_nics = [phy_nic.split("/")[-1] for phy_nic in phy_nics_list]
            mlx_list = []
            for phy_nic in phy_nics:
                driver_info = 'sudo ethtool -i {0} '.format(phy_nic)
                nic_driver_ver = self.get_output_from_run_cmd(driver_info)
                if ('mlx5_core' in nic_driver_ver) and ('5.4-1.0.3' in nic_driver_ver):
                    mlx_list.append(phy_nic)
            if len(mlx_list) == 0:
                return True
            else:
                self._failed_msg += "for the following NIC's: {} - TCPDUMP command create network hung in the node.".format(mlx_list)
                return False
        else:
            self.add_to_validation_log("No Mellanox supported interface found")
            return True

class Hugepage(Validator):
    def is_hugepage_enabled(self, host_grp):
        is_enabled = dict()
        if sys_parameters.get_deployment_type() == Deployment_type.NCS_OVER_BM:
            conf_dict = ConfigStore.get_ncs_bm_conf()
            list_of_host_grp = list(conf_dict["host_group_config"].keys())
            for host_group in list_of_host_grp:
                if host_group.lower() == host_grp:
                    host_group = "{}".format(host_group)
                    try:
                        res = conf_dict["host_group_config"][host_group]["enable_hugepages"]
                        is_enabled[host_grp] = res
                        return True, is_enabled
                    except KeyError:
                        gl.log_and_print("{}:Key not found".format(host_group))
                        return False, is_enabled
            return False, is_enabled


class ValidateKernelParamsOverwritten(Hugepage):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.WORKERS, Objectives.EDGES]
    }

    def set_document(self):
        self._unique_operation_name = "kernel_parameter_overwritten_validation"
        self._title = "Check if kernel parameters are missing/overwritten"
        self._failed_msg = "Kernel parameters are missing/overwritten\n"
        self._severity = Severity.CRITICAL
        self._details = ""
        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.ACTIVE_PROBLEM]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        host_grp = self.get_host_name().split("-")[-2]
        output, is_enabled = self.is_hugepage_enabled(host_grp)
        if output is True and is_enabled[host_grp] is True:
            cmdline_cmd = self.get_output_from_run_cmd("sudo cat /proc/cmdline").strip()
            validate_res = None
            list_to_validate = ["default_hugepagesz", "hugepagesz", "intel_iommu=on"]
            for value in list_to_validate:
                if value in cmdline_cmd:
                    validate_res = True
                else:
                    validate_res = False
                    break
            hugepagesize_total = self.get_output_from_run_cmd("grep -i 'HugePages_Total' /proc/meminfo").strip()
            hugepagesize_total = re.split(r" {1,}", hugepagesize_total)
            if int(hugepagesize_total[1]) > 0 and validate_res is True:
                return True
            else:
                self._details = "Kernel parameters are missing/overwritten:\n{cmdline_cmd}\nHugepagesize:{hugepagesize}" \
                    .format(cmdline_cmd=cmdline_cmd, hugepagesize=hugepagesize_total[1])
                return False
        if output is True and is_enabled[host_grp] is False:
            self._details = "Huge pages are not used"
            return True

        self._details = "Host group:{host_group} not found".format(host_group=host_grp)
        return False


class NoZombiesAllowed(Validator):
    objective_hosts = {
    Deployment_type.NCS_OVER_BM: [Objectives.MASTERS, Objectives.WORKERS],
    Deployment_type.NCS_OVER_OPENSTACK: [Objectives.MASTERS, Objectives.WORKERS],
    Deployment_type.NCS_OVER_VSPHERE: [Objectives.MASTERS, Objectives.WORKERS],
    Deployment_type.CBIS: [Objectives.CONTROLLERS, Objectives.COMPUTES,Objectives.MAINTENANCE]
    }

    def set_document(self):
        self._unique_operation_name = "zombies_do_not_exist"
        self._title = "validate that there is no zombie processes"
        self._failed_msg = "Zombie processes were found"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.SYMPTOM]

    def is_validation_passed(self):
        cmd = "top -bn 1 | grep Tasks:"
        out = self.get_output_from_run_cmd(cmd)
        tasks_split = out.split()
        if tasks_split[-1] != "zombie":
            raise UnExpectedSystemOutput(ip=self.get_host_name(), cmd=cmd, output=out, message="Output of top command should print zombie on the last parameter in Tasks line")
        else:
            zombie_count = int(tasks_split[-2])
            if zombie_count > 100:
                self._failed_msg = "Found {} Zombie processes".format(zombie_count)
                return False
            else:
                return True

#################################
# Below VerifyMountCephFsShareServiceDisabled validation is deprecated.
# CephFS is no longer utilized on CBIs (19A and 20).
# It is our choice - if we don't use this internal mount point we can disable it . This is really not needed.
# Reference - https://jiradc2.ext.net.nokia.com/browse/CBIS-16781
################################
class VerifyMountCephFsShareServiceDisabled(Validator):
    objective_hosts = [Objectives.CONTROLLERS, Objectives.COMPUTES, Objectives.STORAGE]

    def set_document(self):
        self._unique_operation_name = "verify_mount_cephfs_share_service_disabled"
        self._title = "Validate systemctl CephFS service disabled"
        self._failed_msg = "systemctl CephFS service not disabled"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.SYMPTOM]

    def is_validation_passed(self):
        # Validate mount_cephfs_share service is disabled in all overcloud nodes.
        return_code, output, err = self.run_cmd("systemctl is-enabled mount_cephfs_share.service")
        # If mount_cephfs_share service file itself not present,validation is passed.
        if "No such file or directory" in err:
            return True
        return output.strip() == "disabled"


class AuditdBacklogLimit(Validator):
    objective_hosts = [Objectives.ALL_HOSTS, Objectives.HYP, Objectives.ALL_NODES]

    BACKLOG = 'backlog'
    BACKLOG_LIMIT = 'backlog_limit'
    LOST = 'lost'

    def set_document(self):
        self._unique_operation_name = "auditd_backlog_limit"
        self._title = "Check auditd backlog limit usage"
        self._msg = "Depending on system configuration auditd can trigger system outages.\n" \
                    "To prevent this, it is recommended to monitor the backlog buffer utilization"
        self._failed_msg = "auditd backlog risk\n"
        self._severity = Severity.WARNING

        self._implication_tags = [ImplicationTag.SYMPTOM]
        self._blocking_tags = []

    def _measure_auditd_stats_n_times(self, cmd, n=10, wait_seconds=0.25):
        stream = ''
        for i in range(n):
            stream += self.get_output_from_run_cmd(cmd)
            time.sleep(wait_seconds)
            # to be more consistent with sampling period across different systems
        return stream

    def _parse_auditd_data(self, stdout):
        stdout_dict = {AuditdBacklogLimit.BACKLOG: 0, AuditdBacklogLimit.BACKLOG_LIMIT: -1, AuditdBacklogLimit.LOST: 0}
        previous_lost = None
        for x in stdout:
            values = x.split()
            values[1] = self.parse_to_int(values[1])
            if (AuditdBacklogLimit.BACKLOG == values[0] or AuditdBacklogLimit.BACKLOG_LIMIT == values[0]) and \
                    values[1] > stdout_dict[values[0]]:
                # backlog or backlog_limit
                stdout_dict[values[0]] = values[1]
            elif AuditdBacklogLimit.LOST == values[0]:
                # lost
                if previous_lost is not None:     # when previous_lost is defined, use it
                    stdout_dict[values[0]] += (values[1] - previous_lost)
                previous_lost = values[1]

        return stdout_dict

    def is_validation_passed(self):

        cmd1 = 'sudo /usr/sbin/auditctl -s'
        n, wait_seconds = 10, 0.25
        stream1 = self._measure_auditd_stats_n_times(cmd=cmd1, n=n, wait_seconds=wait_seconds)

        stdout = [x for x in stream1.splitlines() if x]
        cost, return_flag = 0.8, True
        stdout_dict = self._parse_auditd_data(stdout=stdout)

        # if no info of backlog_limit in command, raise exception:
        if stdout_dict[AuditdBacklogLimit.BACKLOG_LIMIT] == -1:
            raise UnExpectedSystemOutput(ip=self.get_host_ip(), cmd=cmd1, output=stream1,
                                         message="Command output from '{}' didn't include backlog/lost info".format(
                                             cmd1))

        # check for backlog utilization and lost message count:
        if stdout_dict[AuditdBacklogLimit.BACKLOG] >= cost * stdout_dict[AuditdBacklogLimit.BACKLOG_LIMIT]:
            self._failed_msg += "\nAuditd backlog utilization is {:.1f}% >= {:.1f}%: {}={}, {}={}".format(
                100.0 * stdout_dict[AuditdBacklogLimit.BACKLOG] / stdout_dict[AuditdBacklogLimit.BACKLOG_LIMIT],
                100.0 * cost,
                AuditdBacklogLimit.BACKLOG, stdout_dict[AuditdBacklogLimit.BACKLOG],
                AuditdBacklogLimit.BACKLOG_LIMIT, stdout_dict[AuditdBacklogLimit.BACKLOG_LIMIT])
            return_flag = False
        if stdout_dict[AuditdBacklogLimit.LOST] > 0:
            self._failed_msg += "\nAuditd lost messages increasing a total of " + \
                                "{} messages in the sampled period (~{:.1f} sec)".format(
                                    stdout_dict[AuditdBacklogLimit.LOST], n * wait_seconds)
            return_flag = False

        return return_flag

class KernelVersionValidation(Validator):
    objective_hosts = {Deployment_type.CBIS: [Objectives.HYP, Objectives.ALL_HOSTS, Objectives.MAINTENANCE],
                       Deployment_type.NCS_OVER_BM: [Objectives.ALL_NODES]}
    MIN_VALID_KERNEL_VERSION = 372
    MIN_NOT_VALID_VERSION = 240
    MAIN_VERSION_OF_ISSUE = "4.18.0"

    def set_document(self):
        self._unique_operation_name = "Kernel_version_validation"
        self._title = "Verify that Kernel version is higher or equal to 372."
        self._failed_msg = "Kernel version is lower than expected. "
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION, ImplicationTag.ACTIVE_PROBLEM]

    def is_kernel_version_valid(self, lskernel_version):
        '''
        4.18.0-240 is not OK (22PP0/1)
        4.18.0-348 is not OK (22.7)
        4.18.0-372 is OK (WA applied)
        '''

        lskernel_version_parse = lskernel_version.split("-")

        if lskernel_version_parse[0] != self.MAIN_VERSION_OF_ISSUE:
            return True, ''

        lskernel_version_parse = lskernel_version_parse[1].split(".")
        lskernel_version_parse = lskernel_version_parse[0]
        if to_unicode(lskernel_version_parse).isnumeric():
            is_valid_version = int(lskernel_version_parse) >= self.MIN_VALID_KERNEL_VERSION \
                               or int(lskernel_version_parse) < self.MIN_NOT_VALID_VERSION

            return (is_valid_version, lskernel_version_parse)
        else:
            raise UnExpectedSystemOutput(self.get_host_name(), self.lskernel_version_cmd, "Output value is not in the expected format (int). Value: {0}".format(lskernel_version))

    def is_validation_passed(self):
        self.lskernel_version_cmd = "sudo uname -r"
        lskernel_version = self.get_output_from_run_cmd(self.lskernel_version_cmd)
        is_valid_version, lskernel_version_parse = self.is_kernel_version_valid(lskernel_version)
        if is_valid_version:
            return True
        self._failed_msg += "Expected minimum version is {0}, found {1}. Check with 'uname -r'.".format(self.MIN_VALID_KERNEL_VERSION, lskernel_version_parse)
        return False

class VerifyNginxWorkerConnection(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.MANAGERS]
    }

    def set_document(self):
        self._unique_operation_name = "verify_nginx_worker_connections"
        self._title = "Verify nginx worker connections"
        self._failed_msg = "Nginx worker connections is below optimal value"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.SYMPTOM]

    def is_validation_passed(self):
        cmd_1 = "sudo grep worker_connections /data0/podman/storage/volumes/nginx_etc_vol/_data/nginx.conf"
        output = self.get_output_from_run_cmd(cmd_1).strip().split()
        if len(output) > 1:
            worker_connections = output[1].rstrip(';')
            if int(worker_connections) < 20:
                return False
            return True
        else:
            raise UnExpectedSystemOutput(ip=self.get_host_ip(), cmd=cmd_1, output=output,
                                         message="Expected to have worker_connections parameter with value")


#########################################################
#   ICET-1845 | /data0 - validate file system is rw (read-write)
#   DATE :  05-09-2023
#   Author : SOUVIK DAS
#########################################################

class Data0FileSystemReadWriteCheck(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.MASTERS, Objectives.WORKERS, Objectives.EDGES,Objectives.MANAGERS],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.MASTERS, Objectives.WORKERS, Objectives.EDGES],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.MASTERS, Objectives.WORKERS, Objectives.EDGES]
    }

    def set_document(self):
        self._unique_operation_name = "Data0_FileSystem_ReadWrite_Check"
        self._title = "Data0 FileSystem ReadWrite Check"
        self._failed_msg = "/DATA0 filesystem is not set to READ-WRITE (RW)"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.SYMPTOM, ImplicationTag.APPLICATION_DOMAIN]

    def is_validation_passed(self):
        cmd = "sudo mount -l | grep /dev/ | grep '/data0'"
        return_code, output, err = self.run_cmd(cmd)
        if return_code:
            raise UnExpectedSystemOutput ( ip=self.get_host_name(), cmd=cmd, output=output, message="/data0 does not exist !! ERROR !!")

        mount_output_entries = output.strip().splitlines()
        flag = 0
        for mount_point in mount_output_entries:
            output_split_array = mount_point.strip().split()
            if len(output_split_array)<6:
                raise UnExpectedSystemOutput ( ip=self.get_host_name(), cmd=cmd, output=output, message="/data0 entry is not proper!! ERROR !!")
            else:
                directory_permission_data = output_split_array[5].split(",")
                permission = directory_permission_data[0].replace("(", "")
                if permission == "rw":
                    pass
                else:
                    self._failed_msg = self._failed_msg + "\n" + str(mount_point)
                    flag = flag + 1

        if flag ==0:
            return True
        else:
            return False

#############################################################
##      https://jiradc2.ext.net.nokia.com/browse/ICET-1594
##      Author : Nandagopal Rajangam
##      Date : 05-Sep-2023
##      Validation of cbis-admin password expiry
##      Code reused from CBIS validation
###############################################################

class CheckPasswordExpiryNcs(Validator):
    def get_objective_names(self):
        assert False

    def set_document(self):
        self._unique_operation_name = None
        self._title = "Verify if Password expires for {}".format(self.get_objective_names())
        self._failed_msg = "Password expires for {} - Please change the 'age'\n".format(self.get_objective_names())
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.RISK_BAD_CONFIGURATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_nonexpired_in_two_week(self, account, date):
        if "never" in date:
            self._details += "Password of {} not expired".format(account)
            return True
        date_expire = datetime.strptime(date[-12:], "%b %d, %Y")
        today_plus_14 = datetime.today() + timedelta(days=14)
        if date_expire > today_plus_14:
            self._details += "Password of {} not expired".format(account)
            return True
        else:
            if date_expire <= datetime.today():
                self._implication_tags.append(ImplicationTag.ACTIVE_PROBLEM)
                self._failed_msg += "Password of {} had expired {} days ago".format(account, abs(date_expire - datetime.today()).days)
            else:
                self._failed_msg += "Password of {} will be expired in {} days".format(account, (date_expire - datetime.today()).days)
        return False

    def is_validation_passed(self):
        flg_valid = True
        for account in self.get_objective_names():
            cmd1 = "sudo chage -l {} | grep 'Password expires'".format(account)
            out1 = self.get_output_from_run_cmd(cmd1).strip()
            flg_valid = flg_valid and self.is_nonexpired_in_two_week(account, out1)

        return flg_valid


class CheckPasswordExpiryForNCSBareMetal(CheckPasswordExpiryNcs):
    objective_hosts = [Objectives.MASTERS, Objectives.WORKERS, Objectives.STORAGE, Objectives.EDGES]

    def get_objective_names(self):
        return ["cbis-admin"]

    def set_document(self):
        CheckPasswordExpiryNcs.set_document(self)
        self._unique_operation_name = "check_password_expiry_for_Ncs_BareMetal"

class GetAlarmManagerStatusfromManagers(DataCollector):
    objective_hosts = [Objectives.MANAGERS]

    def collect_data(self):
        cmd = 'systemctl is-active --quiet alarm-manager && echo "active" || echo "failed"'
        out = self.get_output_from_run_cmd(cmd).strip()
        vm_array = out.splitlines()
        return vm_array


class check_systemd_alarm_manager_service(Validator):
    objective_hosts = [Objectives.ONE_MANAGER]

    def set_document(self):
        self._unique_operation_name = "check_systemd_alarm_manager_service"
        self._title = "Check Alarm Manager Service"
        self._failed_msg = "ERROR!! CALM Alarm Manager should be running on One Node with MANAGER Role"
        self._severity = Severity.NOTIFICATION
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        data = self.run_data_collector(GetAlarmManagerStatusfromManagers)
        error_string = ""
        for key,value in list(data.items()):
            error_string = error_string + " On Node : " + str(key) + " Alarm Manager service status is : " + str(value) + "\n"

        active_items = [key for key, value in list(data.items()) if value == [u'active']]
        if len(active_items) == 1:
            return True
        elif len(active_items) < 1:
            self._failed_msg = self._failed_msg + "\n" + "But here CALM Alarm Manager Service is not running in any of the Node" + "\n" + str(error_string)
            return False
        else:
            self._failed_msg = self._failed_msg + "\n" + "But here CALM Alarm Manager running on Multiple nodes on this cluster" + "\n" + str(error_string)
            return False

#############################################################
##      https://jiradc2.ext.net.nokia.com/browse/ICET-2222
##      Author :  SOUVIK DAS
##      Date : 16-Feb-2024
##      Check /etc/fstab if /root/backup is on NFS
###############################################################

class VerifyEtcFstabDirectoryForNFS(Validator):
    objective_hosts = [Objectives.MANAGERS, Objectives.MASTERS]

    def set_document(self):
        self._unique_operation_name = "Verify_Etc_Fstab_Directory_For_NFS"
        self._title = "Verify /etc/fstab Directory For NFS"
        self._failed_msg = "ERROR !! /root/backup entry exists in /etc/fstab\n"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]
        self._blocking_tags = [BlockingTag.UPGRADE]

    def is_validation_passed(self):
        cmd = "sudo cat /etc/fstab"
        """
        SAMPLE OUTPUT >>>>>
        # cat /etc/fstab
        LABEL=img-rootfs / xfs defaults 0 1
        /dev/mapper/vg_root-_data0 /data0 xfs prjquota 0 0
        # 10.88.73.50:/bigpool/nfs-szalon/backup /root/backup nfs defaults 0 0
        """
        exit_code, out, err = self.run_cmd(cmd)
        if exit_code == 0:
            pattern = re.compile(r'.*(/root/backup).*')
            root_backup_entries = pattern.findall(out)
            if root_backup_entries:
                self._failed_msg = self._failed_msg + "\n" + out
                return False
            else:
                return True
        else:
            self._failed_msg = "sudo cat /etc/fstab Command Failed !!!"
            return False

class YumlockFileCheck(Validator):
    objective_hosts = {Deployment_type.CBIS:[Objectives.ALL_HOSTS],
                       Deployment_type.NCS_OVER_BM: [Objectives.ALL_NODES]
                       }

    def set_document(self):
        self._unique_operation_name = "verify_yum_lockfile_is_held_by_another_process"
        self._title = "verify yum lockfile is not held by another process"
        self._failed_msg = "yum lockfile is not held by another process"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.UPGRADE, BlockingTag.SCALE]

    def is_validation_passed(self):
        # Verify yum.pid file exists or not.
        #todo move to file utils
        return_code, output, err = self.run_cmd("ls /var/run/yum.pid")
        if return_code == 2:
            return True
        else:
            self._failed_msg = self._failed_msg + "/var/run/yum.pid file exists, yum process may be in hung status"
        return False


class CheckCronJobDuplicates(Validator):
    objective_hosts = [Objectives.UC, Objectives.MASTERS]
    USERS_TO_CHECK = ['root']

    def set_document(self):
        self._unique_operation_name = "check_cron_job_duplicates"
        self._title = "Check cron job duplicates"
        self._failed_msg = "Cron job duplicates found, the following appeared multiple times:\n"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.NOTE, ImplicationTag.PERFORMANCE]

    def is_validation_passed(self):
        is_passed = True
        for user in self._get_users_to_check():
            cmd = "sudo crontab -u {} -l".format(user)
            return_code, output, err = self.run_cmd(cmd)
            if return_code == 1 and "no crontab for" in err:
                continue
            if return_code != 0:
                raise UnExpectedSystemOutput(self.get_host_ip(), cmd, output, message="error: {}".format(err))

            lines = [line.strip() for line in output.splitlines()]
            jobs = [line for line in lines if line and not line.startswith('#')]
            jobs_counter_dict = {}
            for job in jobs:
                jobs_counter_dict[job] = jobs_counter_dict.get(job, 0) + 1
                if jobs_counter_dict[job] == 2:
                    self._failed_msg+= "user {}: {}\n".format(user, job)
                    is_passed = False
        return is_passed

    def _get_users_to_check(self):
        cmd = "whoami"
        out = self.get_output_from_run_cmd(cmd).strip()
        return set(self.USERS_TO_CHECK + [out])

class ValidateProcFsNfsdAbsenceInUcVm(Validator):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "check_proc_fs_nfsd_absence"
        self._title = "Validate /proc/fs/nfsd is not present in UC VM"
        self._failed_msg = "/proc/fs/nfsd exists on the UC VM This could be a remnant from the CBIS22 to CBIS24 upgrade process performed with leapp."
        self._severity = Severity.CRITICAL
        self._blocking_tags = [BlockingTag.UPGRADE]
        self._implication_tags = [ImplicationTag.PRE_OPERATION]

    def is_validation_passed(self):

        check_mount_cmd  = "mount | grep '/proc/fs/nfsd'"

        return_code, output, err  = self.run_cmd(check_mount_cmd)

        if return_code == 1 and output == "":
            # '/proc/fs/nfsd' is not mounted
            return True
        elif return_code == 0:
            return False
        else:
            raise UnExpectedSystemOutput(self.get_host_ip(), check_mount_cmd, output)


class GetPipVersionFromHosts(DataCollector):
    objective_hosts = [Objectives.MASTERS]

    def collect_data(self):
        cmd = 'sudo pip3 --version'
        out = self.get_output_from_run_cmd(cmd).strip().split()
        return out[1]


class ValidatePipVersionConsistency(Validator):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._unique_operation_name = "validate_pip_version_consistency"
        self._title = "Validate pip version consistency among masters"
        self._failed_msg = ""
        self._severity = Severity.CRITICAL
        self._blocking_tags = [BlockingTag.UPGRADE]
        self._implication_tags = [ImplicationTag.PRE_OPERATION]

    def is_validation_passed(self):
        out = self.run_data_collector(GetPipVersionFromHosts)
        versions_set = set(out.values())
        if None in versions_set:
            self._failed_msg = "Validation failed one or more nodes don't have pip3 installed, pip versions {}".format(dict(out))
            return False
        if len(versions_set) > 1:
            self._failed_msg = "Validation failed different versions of pip found {}".format(dict(out))
            return False
        return True


class IPv6VersionCheckerDataCollector(DataCollector):
    objective_hosts = [Objectives.UC]

    def collect_data(self):
        file_path = "user_config.yaml"
        if not self.file_utils.is_file_exist(file_path):
            raise UnExpectedSystemOutput(self.get_host_ip(), "",
                                         "", "Failed to find {}".format(file_path))
        else:
            cmd = 'sudo cat {} | grep -i stack'.format(file_path)
            out = self.get_output_from_run_cmd(cmd).strip()
            if "IPv4/IPv6 dual stack" in out:
                return True
            return False

class ValidateGatewayBrPublic(Validator):
    objective_hosts = {Deployment_type.CBIS:[Objectives.HYP]}

    def set_document(self):
        self._unique_operation_name = "validate_gateway_brpublic"
        self._title = "Validate IPv4 and IPv6 Default Routes in br-public Network Manager Connection"
        self._failed_msg = "TBD"
        self._severity = Severity.CRITICAL
        self._blocking_tags = [BlockingTag.UPGRADE]
        self._implication_tags = [ImplicationTag.PRE_OPERATION]

    def is_validation_passed(self):

        if gs.get_version() < Version.V24:
            route_br_public_file_path ="/etc/sysconfig/network-scripts/route-br-public"
            if not self.file_utils.is_file_exist(route_br_public_file_path):
                raise UnExpectedSystemOutput(self.get_host_ip(), "",
                                             "", "Failed to find {}".format(route_br_public_file_path))
            check_gateway_cmd = "sudo cat {}".format(route_br_public_file_path)
            output = self.get_output_from_run_cmd(check_gateway_cmd)
            if output is None or not output.strip():
                raise UnExpectedSystemOutput ( ip=self.get_host_ip(), cmd=check_gateway_cmd, output=output, message="Legacy route file route-br-public not found")
            elif "default via" not in output.strip():
                self._failed_msg = "Default gateway is not defined in route-br-public"
                return False
        else:
            br_public_connection_path  ="/etc/NetworkManager/system-connections/br-public.nmconnection"
            if not self.file_utils.is_file_exist(br_public_connection_path):
                raise UnExpectedSystemOutput(self.get_host_ip(), "",
                                             "", "Failed to find {}".format(br_public_connection_path))

            check_gateway_cmd = "sudo cat {} | grep -i route".format(br_public_connection_path)
            output = self.get_output_from_run_cmd(check_gateway_cmd)
            if output is None or not output.strip():
                raise UnExpectedSystemOutput(ip=self.get_host_ip(), cmd=check_gateway_cmd, output=output,
                                             message="br-public NetworkManager connection file missing or no routes defined")

            has_ipv4 = any("0.0.0.0/0" in line for line in output.splitlines())
            has_ipv6 = any("::/0" in line for line in output.splitlines())
            ipv6_enabled = list(self.run_data_collector(IPv6VersionCheckerDataCollector).values())[0]

            if not has_ipv4:
                self._failed_msg = "IPv4 default route is not defined in br-public Network Manager connection"
                return False
            elif ipv6_enabled and not has_ipv6:
                self._failed_msg = "IPv6 default route is not defined while IPv6 is enabled"
                return False
        return True

class ValidateCbisPodsLogRotated(Validator):
    objective_hosts = {Deployment_type.CBIS: [Objectives.HYP],
                       Deployment_type.NCS_OVER_BM: [Objectives.MANAGERS]}

    def set_document(self):
        self._unique_operation_name = "validate_cbis_pods_log_rotated"
        self._title = "Validate /var/log/cbis_pods.log is rotated"
        self._failed_msg = "/var/log/cbis_pods.log is not rotated"
        self._severity = Severity.NOTIFICATION
        self._implication_tags = [ImplicationTag.NOTE]

    def is_validation_passed(self):
        is_passed = True
        file_path = "/var/log/cbis_pods.log"

        if self.file_utils.is_file_exist(file_path):
            file_path2 = "/etc/logrotate.d/cbis_pods"

            if not self.file_utils.is_file_exist(file_path2):
                cmd = "sudo ls -lh /var/log/cbis_pods.log"
                out = self.get_output_from_run_cmd(cmd, add_bash_timeout=True)
                size = out.split()[4]
                self._failed_msg += ", current size: {} and increasing continuously".format(size)
                is_passed = False
        return is_passed

class ValidateSysLogRotated(Validator):
    objective_hosts = [Objectives.ALL_NODES]

    def set_document(self):
        self._unique_operation_name = "validate_syslog_rotated"
        self._title = "Validate /etc/logrotate.d/syslog is exists"
        self._failed_msg = "/etc/logrotate.d/syslog is not exists"
        self._severity = Severity.NOTIFICATION
        self._implication_tags = [ImplicationTag.NOTE]

    def is_validation_passed(self):
        is_passed = True
        file_path = "/etc/logrotate.d/syslog"

        if not self.file_utils.is_file_exist(file_path):
                cmd = "ls -lh /var/log/messages"
                out = self.get_output_from_run_cmd(cmd, add_bash_timeout=True)
                size = out.split()[4]
                self._failed_msg += ", current size: {} and increasing continuously".format(size)
                is_passed = False
        return is_passed


# Part 1 , validation for checking critical fstab mounts i.e., /data0 and /data0/etcd
class FstabValidator(Validator):
    objective_hosts = {Deployment_type.NCS_OVER_OPENSTACK: [Objectives.MASTERS],
                      Deployment_type.NCS_OVER_BM: [Objectives.MASTERS]}

    def set_document(self):
        self._unique_operation_name = "validate_critical_fstab_mounts"
        self._title = "Verify Mount Points in /etc/fstab"
        self._failed_msg = "Missing or incorrect entries found for mount paths in /etc/fstab."
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        file_path = "/etc/fstab"
        if not self.file_utils.is_file_exist(file_path):
            self._failed_msg = "{} is not found".format(file_path)
            return False

        content = self.get_output_from_run_cmd("cat /etc/fstab", add_bash_timeout=True)
        lines = content.splitlines()

        has_data0 = False
        has_etcd = False

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                mountpoint = parts[1]
                if mountpoint == "/data0":
                    has_data0 = True
                if mountpoint == "/data0/etcd":
                    has_etcd = True

        if has_data0 and has_etcd:
            return True

        missing = []
        if not has_data0:
            missing.append("'/data0'")
        if not has_etcd:
            missing.append("'/data0/etcd'")

        self._failed_msg += "\nMissing entries in /etc/fstab: " + ", ".join(missing)
        return False


# Part 2 , validation for checking disk mounts & file system integrity in NCS
class DiskMountValidator(Validator):
    objective_hosts = {Deployment_type.NCS_OVER_OPENSTACK: [Objectives.MASTERS],
                       Deployment_type.NCS_OVER_BM: [Objectives.MASTERS]}

    def set_document(self):
        self._unique_operation_name = "validate_mount_disk"
        self._title = "Validate Disk Mounts and Filesystem Integrity in NCS"
        self._failed_msg = (
            "One or more critical application mount points (e.g., /data0 or /data0/etcd) are missing, "
            "or the underlying file system is corrupted (missing UUID).")
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        out = self.get_output_from_run_cmd("lsblk -p -P -o NAME,MOUNTPOINT,UUID", add_bash_timeout=True)
        '''
        sample o/p of above lsblk cmd
        NAME="/dev/mapper/vg_root-_data0" MOUNTPOINT="/data0" UUID="4f236d7d-1177-4c16-96a1-290b54a07226"
        '''
        if not out:
            self._failed_msg += "Failed to run 'lsblk' command."
            return False

        found_mounts = {
            "/data0": None,
            "/data0/etcd": None
        }

        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue

            device_attributes = {}
            for token in line.split():
                if "=" in token:
                    key, value_with_quotes = token.split("=", 1)
                    cleaned_value = value_with_quotes.strip('"')
                    device_attributes[key] = cleaned_value
            '''
            dict
            {'NAME': '/dev/mapper/vg_root-_data0', 'MOUNTPOINT': '/data0', 'UUID': '...'}
            '''
            mp = device_attributes.get("MOUNTPOINT", "")
            # code iterates over all lines ( /dev/sda, /dev/sda1, etc...).
            # It only proceeds if mp is exactly /data0 or /data0/etcd
            '''
            /data0 -> {'NAME': '/dev/mapper/vg_root-_data0', 'MOUNTPOINT': '/data0', 'UUID': '0290c496-777c-48b6-a77a-d60a1252b4eb'}
            /data0/etcd -> {'NAME': '/dev/mapper/vg_etcd-_etcd', 'MOUNTPOINT': '/data0/etcd', 'UUID': '5cf1c3cc-8b00-416dacfc-1a557dbf9606'}
            '''
            if mp in found_mounts:
                found_mounts[mp] = device_attributes
        is_ok = True
        for mount_path, device_data in found_mounts.items():
            if device_data:
                # if the mount point exists.. checking for UUID.
                if not device_data.get("UUID"):
                    # If UUID is missing, possibly a filesystem error
                    self._failed_msg += "\nUUID missing for mounted path {} (Filesystem integrity issue). ".format(
                        mount_path)
                    is_ok = False
            else:
                # if the required mount point was not found in lsblk output.
                self._failed_msg += "\nMount point {} missing. ".format(mount_path)
                is_ok = False
        return is_ok


class VerifyNoEmptyFilesInConfigDirs(Validator):
    objective_hosts = [Objectives.ALL_NODES]

    def set_document(self):
        self._unique_operation_name = "verify_no_empty_files_in_config_dirs"
        self._title = "Verify no 0-byte files exist in critical configuration directories"
        self._failed_msg = "The following files have 0 bytes size: "
        self._severity = Severity.NOTIFICATION
        self._implication_tags = [ImplicationTag.NOTE]

    def is_validation_passed(self):
        # Add more directories here as needed
        target_directories = [
            '/etc/cni/net.d/',
            '/etc/kubernetes/cni/net.d/',
            '/etc/selinux/targeted/policy/',
            '/etc/selinux/'
        ]

        found_empty_files = []

        for directory in target_directories:
            # Added '|| true' to safely handle if the directory is actually missing
            check_dir_cmd = "sudo test -d {} && echo 'exists' || true".format(directory)
            dir_check_out = self.get_output_from_run_cmd(check_dir_cmd)

            if 'exists' in dir_check_out:
                # Find 0-byte files
                find_cmd = "sudo find {} -maxdepth 1 -type f -size 0".format(directory)
                out = self.get_output_from_run_cmd(find_cmd)

                if out:
                    for line in out.strip().splitlines():
                        found_empty_files.append(line)

        if found_empty_files:
            self._failed_msg += "\n" + "\n".join(found_empty_files)
            return False

        return True


class VerifySecureBootStatus(Validator):
  
    objective_hosts = [Objectives.ALL_NODES, Objectives.ALL_HOSTS, Objectives.HYP, Objectives.DEPLOYER, Objectives.MANAGERS]

    SECURE_BOOT_FILE_PATH = "/sys/firmware/efi/efivars/SecureBoot-*"

    def set_document(self):
        self._unique_operation_name = "verify_secure_boot_status"
        self._title = "Verify Secure Boot is enabled"
        self._failed_msg = "Secure Boot is not enabled or not available"
        self._severity = Severity.NOTIFICATION
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]

    def is_prerequisite_fulfilled(self):
        # Check if the SecureBoot file exists (UEFI mode)
        # If not, system is probably using Legacy BIOS mode - skip validation
        check_file_cmd = "ls {} 2>/dev/null".format(self.SECURE_BOOT_FILE_PATH)
        ret, out, err = self.run_cmd(check_file_cmd)
        return ret == 0 and bool(out.strip())

    def is_validation_passed(self):
        # Read the SecureBoot status
        cmd = "cat {} 2>/dev/null | od -An -t u1 | tail -c 2".format(self.SECURE_BOOT_FILE_PATH)
        ret, out, err = self.run_cmd(cmd)

        out_stripped = out.strip() if out else ""

        # Case 1: Output is "1" - Secure Boot enabled
        if out_stripped == "1":
            return True

        # Case 2: Output is "0" - Secure Boot disabled
        if out_stripped == "0":
            self._failed_msg = "Secure Boot is DISABLED. Consider enabling it for enhanced security."
            self._msg = "Status code: 2 (DISABLED)"
            return False

        # Case 3: Empty output - file exists but couldn't read value
        if not out_stripped:
            self._failed_msg = "Secure Boot status not available (EFI variables not accessible)"
            self._severity = Severity.NOTIFICATION
            self._msg = "Status code: 3 (NOT_AVAILABLE)"
            return False

        # Case 4: Any other output - unexpected
        self._failed_msg = "Unexpected Secure Boot status value: '{}'. Manual investigation required.".format(
            out_stripped)
        self._msg = "Status code: 4 (UNEXPECTED)"
        return False