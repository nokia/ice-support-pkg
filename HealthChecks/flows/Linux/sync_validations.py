from __future__ import absolute_import
from HealthCheckCommon.operations import *
import socket

from HealthCheckCommon.validator import Validator
from tools.Info import GetInfo
import tools.sys_parameters as sys_param
import re
import ipaddress

class clock_clock_synchronized(Validator):
    objective_hosts = [Objectives.ALL_HOSTS, Objectives.ALL_NODES]

    def set_document(self):
        self._unique_operation_name = "is_clock_synchronized"
        self._title = "Verify clock synchronized"
        self._failed_msg = "test not completed:"
        self._severity = Severity.CRITICAL

        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PRE_OPERATION, ImplicationTag.APPLICATION_DOMAIN]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        if gs.get_version() >= Version.V23:
            return self.validate_synchronized_by_timedatectl()
        return_code, out, err = self.run_cmd("ntpstat ; echo $?", timeout=15)
        if out:
            time_offset = re.findall(r"\d*\sms", out)
            time_offset = time_offset[0] if len(time_offset) else None
            if time_offset is None and 'unsynchronised' in out:
                self._failed_msg = "Host {} is unsynchronised with NTP".format(self.get_host_ip())
                return False
            out_lines = re.split("[\n\r]", out)
            out_lines = list([_f for _f in out_lines if _f])
            res = out_lines[-1]
            is_sync = True if res == '0' else False
            self._failed_msg = "Host synchronized offset of {} at {} ".format(time_offset, self.get_host_ip())
            return is_sync
        raise SystemError

    def validate_synchronized_by_timedatectl(self):
        timedatectl_dict = self.get_dict_from_command_output('timedatectl', 'space', custom_delimiter=':')
        failed_fields_dict = {}
        expected_dict = {"System clock synchronized": "yes"}
        if gs.get_deployment_type() in [Deployment_type.CBIS, Deployment_type.NCS_OVER_BM]:
            expected_dict["NTP service"] = "active"
        for field in list(expected_dict.keys()):
            try:
                if timedatectl_dict[field] != expected_dict[field]:
                    failed_fields_dict[field] = timedatectl_dict[field]
            except KeyError as e:
                raise UnExpectedSystemOutput(ip=self.get_host_ip(), cmd="", output=str(e),
                                             message="No field '{}' in the command output of 'timedatectl'".format(field))
        if failed_fields_dict:
            self._failed_msg = "NTP wrong values:{} at {} ".format(failed_fields_dict, self.get_host_ip())
            return False
        return True

class ValidateNtpIp(Validator):
    objective_hosts = [Objectives.UC]  # todo at this moment - only cbis

    def set_document(self):
        self._unique_operation_name = "is_NTP_ip_valid"
        self._title = "Verify NTP IP is valid"
        self._failed_msg = "test not completed:"
        self._severity = Severity.CRITICAL

        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        ips = GetInfo().get_ntp_list()
        for ip, ver in ips:
            if isinstance(ver, ipaddress.IPv6Address):
                # if ver.version == 6:
                try:
                    socket.inet_pton(socket.AF_INET6, ip)
                except socket.error:
                    self._failed_msg = ("The address {} is not a valid IPv6 address".format(ip))
                    return False
                return True
            # Else the version is Ipv4, and either an ip or a hostname:
            elif isinstance(ver, ipaddress.IPv4Address):
                ip = socket.gethostbyname(ip)
                try:
                    socket.inet_pton(socket.AF_INET, ip)
                except socket.error:
                    self._failed_msg = ("The address {} is not a valid IPv4 address".format(ip))
                    return False
                return True
            else:
                raise UnExpectedSystemOutput("uc", "get the ntp from conf", str(ver), "ver is no IPV4 and not IPV6")


class ntpdate_checker(Validator):
    objective_hosts = [Objectives.UC, Objectives.CONTROLLERS]

    def set_document(self):
        self._unique_operation_name = "is_ntp_valid"
        self._title = "Verify NTP"
        self._failed_msg = "test not completed:"
        self._severity = Severity.CRITICAL

        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        # ips = GetInfo.get_ntp_list()
        # for ip, var in ips:
        # line = "sudo /usr/sbin/ntpdate -q %s < /dev/null" % ip
        # this 1) change the system
        #    2)can not run parraloztion
        line = 'sudo ntpq -c rv'
        out = self.get_output_from_run_cmd(line, 5)

        if not "leap_none" in out:
            self._failed_msg = (
                "NTP Synchronization failed. please use 'sudo /usr/sbin/ntpdate' to update the dates , "
                "please contact your systems administrator if filed")
            return False
        return True


class validate_no_ntp_in_cbis_21(Validator):
    objective_hosts = [Objectives.ALL_HOSTS]

    def set_document(self):
        self._unique_operation_name = "chronyc_run"
        self._title = "make sure in cbis 21 and on we have chronyc and not NTP"
        self._failed_msg = "test not completed:"
        self._severity = Severity.ERROR

        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        if sys_param.get_version() < Version.V22:
            return True

        out = self.get_output_from_run_cmd("systemctl --type=service --state=running")
        if "ntpd" in out:
            self._failed_msg = "we do not expect ntpd in this cbis version"
            return False

        if not "chronyd" in out:
            self._failed_msg = "chronyd expect in this cbis version"
            return False
        return True


class ntp_offset_checker(Validator):
    objective_hosts = [Objectives.ALL_HOSTS]

    def set_document(self):
        self._unique_operation_name = "ntp_offset_checker"
        self._title = "Verify NTP/chronyc offset for CEPH"
        self._failed_msg = "test not completed:"
        self._severity = Severity.CRITICAL

        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def _is_offset_valid(self, offset):
        if abs(float(offset)) > 50:
            self._failed_msg = ("NTP offset = {0:.0f} is exceeded 50 milliseconds".format(offset))
            return False
        return True

    def is_validation_passed(self):
        cmd = "systemctl --type=service --state=running"
        out = self.get_output_from_run_cmd(cmd)

        if "ntpd" in out:
            ntp_lines = self.get_output_from_run_cmd('sudo ntpq -nc peers').splitlines()
            active_ntp_lines = ntp_lines[2:]

            if len(active_ntp_lines) > 1:
                active_ntp_lines = list([l for l in ntp_lines if l.startswith("*")])

            if not active_ntp_lines:
                self._failed_msg = "please check NTP service is running"
                return False

            active_ntp_line = active_ntp_lines[0]
            offset = float(PythonUtils.get_the_n_th_field(active_ntp_line, 9))
            return self._is_offset_valid(offset)
        elif "chronyd" in out:
            offset = self.run_and_get_the_nth_field("sudo chronyc tracking |grep 'Last'", 4)
            offset = (float(offset) * 1000)  # convert to ms
            return self._is_offset_valid(offset)

        raise UnExpectedSystemOutput(self.get_host_ip(), cmd, out, "Expected to have 'ntpd' or 'chronyd' in out.")
