from __future__ import absolute_import
import os

from HealthCheckCommon.operations import *
from pkg_resources import parse_version  # to compare different version numbers

from HealthCheckCommon.validator import Validator, InformatorValidator
from tools.Info import GetInfo
from tools.python_versioning_alignment import get_full_trace, to_unicode
import datetime

from tools import paths
from tools.ExecutionModule.execution_helper import ExecutionHelper

try:
    # zabbixAPI is not installed on all versions.
    # we do not want the code to break on it
    # but not used for cbis 18
    from pyzabbix import ZabbixAPI
except:
    pass

import tools.sys_parameters as sys_parameters

ZABBIX_PORT = "10050"
class CheckWhetherZabbixAgentFirewallWorkingAsExpected(Validator):
    objective_hosts = [Objectives.ALL_NODES]

    def set_document(self):
        self._unique_operation_name = "CheckWhetherZabbixAgentFirewallWorkingAsExpected"
        self._title = "Check whether zabbix agent firewall working as expected"
        self._failed_msg = "Please check the zabbix agent firewall"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        cmd = "sudo iptables -L -n  |  grep " + ZABBIX_PORT
        return_code, out, err = self.run_cmd(cmd)
        if out:
            return True
        else:
            return False


class ZabbixDetailsFromSystemDataCollector(DataCollector):
    objective_hosts = [Objectives.ONE_CONTROLLER]

    def collect_data(self):
        virtual_ip_cmd = 'sudo hiera public_virtual_ip'
        username_cmd = 'sudo hiera -c /usr/share/cbis/data/cbis_hiera.yaml cbis::openstack_deployment::zabbix_username'
        password_cmd = 'sudo hiera -c /usr/share/cbis/data/cbis_hiera.yaml cbis::openstack_deployment::zabbix_password'
        hiera_tls_cmd = 'sudo hiera  tripleo::haproxy::service_certificate'

        stdout = self.get_output_from_run_cmd(virtual_ip_cmd)
        virtual_ip = stdout.replace("\n", "").replace("\r", "")

        stdout = self.get_output_from_run_cmd(hiera_tls_cmd)
        hiera_tls = stdout.replace("\n", "").replace("\r", "")

        stdout = self.get_output_from_run_cmd(username_cmd)
        username = stdout.replace("\n", "").replace("\r", "")

        password = self._get_zabbix_password(password_cmd)

        return {"virtual_ip": virtual_ip, "hiera_tls": hiera_tls, "username": username, "password": password}

    def _get_zabbix_password(self, password_cmd):
        stdout = self.get_output_from_run_cmd(password_cmd)
        if "ANSIBLE_VAULT" in stdout:
            stdout = self.system_utils.decrypt_password(stdout)

        password = stdout.replace("\n", "").replace("\r", "")
        return password


# grep all the zabbix alarms that are still on in the last week
# different implementation to different Zabbix versions
class CheckZabbixAlarms(InformatorValidator):

    def set_document(self):
        self._unique_operation_name = ""
        self._title = "Verify Zabbix has no alarms currently"
        self._title_of_info = "Zabbix alarms:"
        self._failed_msg = "Zabbix alarms:"
        self._severity = Severity.ERROR
        self._is_pure_info = False
        self._is_clean_cmd_info = True
        self._implication_tags = [ImplicationTag.SYMPTOM]


    def create_client(self, ip, z_user, z_pass, hiera_tls, port_str='', session_verify=True, set_ca=True):
        z_url_prefix = 'https'
        if hiera_tls == 'nil':
            z_url_prefix = 'http'
        z_ip = ip
        if ':' in z_ip:  # Is ipv6
            z_ip = '[' + z_ip + ']'
        z_url = z_url_prefix + '://' + z_ip + port_str + '/zabbix/'
        if set_ca:
            if ExecutionHelper.is_run_inside_container():
                os.environ['REQUESTS_CA_BUNDLE'] = paths.MOUNTED_CA_CERT_PATH_IN_CONTAINER

        try:
            if session_verify:
                client = ZabbixAPI(z_url)
            else:
                version = sys_parameters.get_version()
                if version >= Version.V25 and Deployment_type.is_cbis(sys_parameters.get_deployment_type()):
                    client = ZabbixAPI(z_url, detect_version=True)
                else:
                    client = ZabbixAPI(z_url, detect_version=False)
                # pyzabbix version 1.0.0 is used at least from 1.3-b380 onwards
                # From pyzabbix 1.0.0 release there is a new feature for auto-detecting Zabbix API version by default,
                # this can cause the ZabbixAPI instance creation to fail when using SSL and ZabbixAPI.session.verify =
                # False, to avoid this it is needed to add the detect_version=False parameter, but this is only
                # available from 1.0.0 onwards.
            client.session.verify = session_verify
            client.login(z_user, z_pass)
        except Exception as e:
            raise UnExpectedSystemOutput(ip=self.get_host_ip(), cmd="create Zabbix client from python code", output='',
                                         message='Creating Zabbix client - Failed, Exiting\n{}'.format(e))
        return client

    def _get_zapi(self):
        raise NotImplementedError

    def _get_zabbix_credentials(self):
        raise NotImplementedError

    def is_validation_passed(self):

        try:
            zapi = self._get_zapi()
            historical_info = self.get_historical_info(zapi)

            self._system_info = ""
            api_version = zapi.apiinfo.version()

            if parse_version(api_version) >= parse_version('4.0.0'):
                flg_ok = self.get_current_zabbix_alarms_from_problems(zapi)
            else:
                flg_ok = self.get_current_zabbix_alarms_from_triggers(zapi)

        except Exception as e:
            full_trace = get_full_trace()
            raise UnExpectedSystemOutput(ip=self.get_host_ip(),
                                         cmd="",
                                         output=e.__str__() + " " + full_trace,
                                         message="problem in getting data from Zabbix")

        self._system_info = self._system_info + "*** Past 7 days Zabbix alarms {}".format(historical_info)
        return flg_ok

    def get_current_zabbix_alarms_from_problems(self, zapi):
        msg_str = ""
        flg_ok = True
        prob = zapi.problem.get()
        for p in prob:
            subject = p['name']
            alrtTime = datetime.datetime.fromtimestamp(float(p['clock'])).strftime('%Y-%m-%d %H:%M:%S')
            self._failed_msg += "\n" + ("{0} - {1}".format(alrtTime, subject))
            msg_str += "\n" + ("{0} - {1}".format(alrtTime, subject))
            flg_ok = False

        self._system_info = "*** Current Zabbix alarms: " + msg_str + "\n\n"
        return flg_ok

    def get_current_zabbix_alarms_from_triggers(self, zapi):
        msg_str = ""
        flg_ok = True
        triggers = zapi.trigger.get(only_true=1,
                                    skipDependent=1,
                                    monitored=1,
                                    active=1,
                                    output='extend',
                                    expandDescription=1,
                                    selectHosts=['host'],
                                    withLastEventUnacknowledged=1
                                    )

        for t in triggers:
            if int(t['value']) == 1:
                tTime = datetime.datetime.fromtimestamp(float(t['lastchange'])).strftime('%Y-%m-%d %H:%M:%S')
                self._failed_msg += "\n" + ("{0} - {1} - {2}".format(
                    tTime,
                    t['hosts'][0]['host'],
                    t['description'])
                )
                msg_str += "\n" + ("{0} - {1} - {2}".format(tTime, t['hosts'][0]['host'], t['description']))
                flg_ok = False
        self._system_info = "*** Current Zabbix alarms: " + msg_str + "\n\n"
        return flg_ok

    def get_historical_info(self, zapi):
        out = self.get_output_from_run_cmd('echo $(( $(date +%s) - 604800 ))')
        time = int(out)
        events = zapi.event.get(time_from=time, selectHosts=['host'])
        eventids = []
        for event in events:
            eventid = event['eventid']
            eventids.append(eventid)
        alrts = zapi.alert.get(eventids=eventids)
        history_info = ""

        for alrt in alrts:
            subject = alrt['subject'] if alrt['subject'] != "PROBLEM" and alrt['subject'] != "OK" else None
            if not subject:
                continue
            alrtTime = datetime.datetime.fromtimestamp(float(alrt['clock'])).strftime('%Y-%m-%d %H:%M:%S')
            history_info += "\n" + ("{0} - {1} - {2}".format(
                alrtTime,
                alrt['eventid'],
                subject)
            )
        return history_info


class CheckZabbixAlarmsCbis(CheckZabbixAlarms):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        super(CheckZabbixAlarmsCbis, self).set_document()
        self._unique_operation_name = "is_zabbix_has_alarms_cbis"
        self._implication_tags = [ImplicationTag.SYMPTOM]

    def _get_zabbix_credentials(self):
        return self.get_first_value_from_data_collector(ZabbixDetailsFromSystemDataCollector)

    def _create_client_cbis(self, public_ip, z_user, z_pass, hiera_tls):
        return self.create_client(public_ip, z_user, z_pass, hiera_tls, session_verify=False, set_ca=False)

    def _get_zapi(self):
        zabbix_details_dict = self._get_zabbix_credentials()
        zapi = self._create_client_cbis(zabbix_details_dict['virtual_ip'], zabbix_details_dict['username'],
                                        zabbix_details_dict['password'], zabbix_details_dict['hiera_tls'])
        return zapi


class CheckZabbixAlarmsNcs(CheckZabbixAlarms):
    objective_hosts = {Deployment_type.NCS_OVER_BM: [Objectives.ONE_MANAGER]}   # Zabbix only on CN-B

    # older versions:
    ZABBIX_BM_FILE = "/usr/share/cbis/overcloud/postdeploy/scripts/zabbix-config-baremetal.conf"

    # newer versions:
    CMD_IP = 'sudo /bin/hiera -c /usr/share/cbis/data/cbis_hiera.yaml controller_virtual_ip'
    CMD_USER = 'sudo /bin/hiera -c /usr/share/cbis/data/cbis_hiera.yaml cbis::openstack_deployment::zabbix_username'
    CMD_PASS = 'sudo /bin/hiera -c /usr/share/cbis/data/cbis_hiera.yaml cbis::openstack_deployment::zabbix_password'
    CMD_PUB_IP = 'sudo /bin/hiera -c /usr/share/cbis/data/cbis_hiera.yaml tripleo::haproxy::public_virtual_ip'

    def set_document(self):
        super(CheckZabbixAlarmsNcs, self).set_document()
        self._unique_operation_name = "is_zabbix_has_alarms_ncs"
        self._implication_tags = [ImplicationTag.SYMPTOM]

    def _get_zabbix_credentials_from_file(self):
        '''
        File has format:
        {'zabbix_config': {'zabbix_username': 'cbis-admin', 'zabbix_password': 'xxx', 'public_virtual_ip': 'x.x.x.x',
        'internal_virtual_ip': 'y.y.y.y', 'cluster_name': 'name'}}
        '''
        zabbix_credentials = self.get_dict_from_file(self.ZABBIX_BM_FILE, file_format='ini')
        if 'zabbix_config' in zabbix_credentials:
            return zabbix_credentials['zabbix_config']

        raise UnExpectedSystemOutput(self.get_host_ip(), cmd="Checking contents of '{}'".format(self.ZABBIX_BM_FILE),
                                     output=zabbix_credentials, message="Zabbix credentials could not be obtained.")

    def _get_zabbix_credentials_from_hiera(self):
        zabbix_credentials = {'internal_virtual_ip': self.get_output_from_run_cmd(self.CMD_IP).splitlines()[0],
                              'zabbix_username': self.get_output_from_run_cmd(self.CMD_USER).splitlines()[0],
                              'zabbix_password': self.get_output_from_run_cmd(self.CMD_PASS).splitlines()[0],
                              'public_virtual_ip': self.get_output_from_run_cmd(self.CMD_PUB_IP).splitlines()[0]
                              }
        return zabbix_credentials

    def _get_zabbix_credentials(self):
        ncs_version = sys_parameters.get_version()

        if Version.V22_7 >= ncs_version >= Version.V20_FP2:  # Credentials on file
            return self._get_zabbix_credentials_from_file()
        elif ncs_version >= Version.V22_12:                 # Credentials not on file
            return self._get_zabbix_credentials_from_hiera()
        return None

    def _create_client_ncs(self, internal_ip, z_user, z_pass, public_ip=None):
        try:
            client = super(CheckZabbixAlarmsNcs, self).create_client(internal_ip, z_user, z_pass, hiera_tls='nil',
                                                                     port_str=':9443', set_ca=False)
        except Exception as e:
            # Can fail in some versions when public IP needs to be used instead
            if public_ip is not None:
                client = super(CheckZabbixAlarmsNcs, self).create_client(public_ip, z_user, z_pass, hiera_tls='',
                                                                         port_str=':9443', session_verify=False,
                                                                         set_ca=False)
            else:
                raise e

        return client

    def _get_zapi(self):
        z_credentials = self._get_zabbix_credentials()
        internal_ip, public_ip = z_credentials['internal_virtual_ip'], z_credentials['public_virtual_ip']
        z_user, z_pass = z_credentials['zabbix_username'], z_credentials['zabbix_password']

        zapi = self._create_client_ncs(internal_ip, z_user, z_pass, public_ip)
        return zapi


class VerifyZabbixServiceIsRunningOnOneNodeOnly(Validator):
    # comment out untill ICET-2448 is soloved
    objective_hosts = [Objectives.ONE_MANAGER]

    def set_document(self):
        self._unique_operation_name = "verify_zabbix_service_is_running_on_one_node_only"
        self._title = "Verify zabbix service is running on one node only"
        self._failed_msg = "Please make sure the zabbix service is only running on one node"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_prerequisite_fulfilled(self):
        all_hosts = GetInfo.get_setup_host_list() # includes the UN and HYP

        for host_data in list(all_hosts.values()):
            if 'monitoring' in host_data['roles']:
                return True

        return False

    def is_validation_passed(self):
        count = 0
        zabbix_server_running = []

        zabbix_server_details_dict = self.run_data_collector(ZabbixServiceIsRunningFromSystemDataCollector)

        for key, value in list(zabbix_server_details_dict.items()):
            if value == 0:
                count += 1
                zabbix_server_running.append(key)

        if count == 1:
            return True
        else:
            self._failed_msg = "Please make sure the zabbix service is only running on one node. The zabbix-server is currently running on the following hosts {}".format(zabbix_server_running)
            return False


class ZabbixServiceIsRunningFromSystemDataCollector(DataCollector):
    objective_hosts = [Objectives.ALL_NODES]

    def collect_data(self):
        cmd = "sudo systemctl status zabbix-server.service | grep Active: | grep running"
        return_code, out, err = self.run_cmd(cmd)

        return return_code


class CheckSelinuxContextForZabbix(Validator):
    objective_hosts = [Objectives.MASTERS]

    def set_document(self):
        self._unique_operation_name = "zabbix_selinux_context_check"
        self._title = "Check selinux context on /var/lib/zabbix for master nodes in config5 setups"
        self._failed_msg = "The selinux context for /var/lib/zabbix is incorrect"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        output1 = self.get_output_from_run_cmd ("ls -laZ /var/lib/ | grep zabbix")
        output2 = self.get_output_from_run_cmd("ls -laZ /var/lib/zabbix/* | grep -v 'total'")

        return self._get_type(output1) and self._get_type(output2)

    def _get_type(self, ls_output):
        for line in ls_output.splitlines():
            context = line.split()
            if len(context) < 4:
                raise UnExpectedSystemOutput("", "", "", "Unexpected context format: less than 4 parts found.")

            selinux_type = context[3].split(":")
            # Check if the third part of the SELinux context is not "var_lib_t"
            if len(selinux_type) > 2 and selinux_type[2] != "var_lib_t":
                return False
        return True

class GetVirtualIPDetailsFromControllers(DataCollector):
    objective_hosts = [Objectives.CONTROLLERS]

    def collect_data(self):
        cmd = "less /usr/lib/zabbix/alertscripts/zabbix_cbis_snmp.py | grep send_to | grep -i ="
        send_to_entry = self.get_output_from_run_cmd(cmd, timeout=60, add_bash_timeout=True)
        output = send_to_entry.strip()
        # Matches the 'send_to' parameter and captures its value (inside single quotes) from the output string
        correct_send_to_entry_match = re.search(r"send_to\s*=\s*'([^']+)'", output)
        if correct_send_to_entry_match:
            return correct_send_to_entry_match.group(1)
        return send_to_entry

class VerifyControllerVirtualIp(Validator):
    objective_hosts = [Objectives.ONE_CONTROLLER]

    def set_document(self):
        self._unique_operation_name = "virtual_router_ip_check"
        self._title = ("Verify if the controller_virtual_ip in zabbix_cbis_snmp.py matches the "
                       "expected hiera_data_ip on all CBIS controller nodes")
        self._failed_msg = "Verification of `controller_virtual_ip` failed on one or more CBIS controller nodes. " \
                           "The following controller(s) had mismatched IPs:\n"
        self._severity = Severity.ERROR

    def is_validation_passed(self):

        virtual_router_ip_dict = self.run_data_collector(GetVirtualIPDetailsFromControllers)
        hiera_data_ip = self._get_hiera_data_ip()

        # virtual_router_ip_dict : ({'overcloud-controller-cbis22-0': '172.31.3.144', 'overcloud-controller-cbis22-1': '172.31.3.144',
        # 'overcloud-controller-cbis22-2': '172.31.3.144'})
        # hiera_data_ip: 172.31.3.144

        mismatched_controllers = []
        is_all_ips_matching_expected_hiera_data_ip = True
        for controller, ip in virtual_router_ip_dict.items():
            if ip != hiera_data_ip:
                mismatched_controllers.append(
                    "Controller: {} - Expected IP: {}, Found IP: {}".format(controller, hiera_data_ip, ip))
                is_all_ips_matching_expected_hiera_data_ip = False

        if not is_all_ips_matching_expected_hiera_data_ip:
            self._failed_msg = self._failed_msg + "\n".join(mismatched_controllers)
        return  is_all_ips_matching_expected_hiera_data_ip

    def _get_hiera_data_ip(self):
        cmd = "sudo /bin/hiera tripleo::haproxy::controller_virtual_ip"
        hiera_data_ip = self.get_output_from_run_cmd(cmd).strip()
        if not hiera_data_ip:
            raise UnExpectedSystemOutput(self.get_host_ip(), cmd, hiera_data_ip, "Hiera data IP is missing or empty.")
        return hiera_data_ip
