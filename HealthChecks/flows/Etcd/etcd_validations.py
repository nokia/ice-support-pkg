from __future__ import absolute_import
import json
import re

from HealthCheckCommon.validator import Validator
from tools import sys_parameters
from tools.Exceptions import UnExpectedSystemOutput
from tools.global_enums import Objectives, Severity, ImplicationTag, BlockingTag


class EtcdBasicValidator(Validator):
    objective_hosts = [Objectives.ONE_MASTER]

    def __init__(self, ip):
        Validator.__init__(self, ip)

    def set_document(self):
        self._title = "Check etcd exist and reachable"
        self._unique_operation_name = "etcd_reachable"
        self._failed_msg = "could not connect to etcd"
        self._severity = Severity.CRITICAL

        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        cmd = "sudo ETCDCTL_API=3 bash -c 'etcdctl version'"
        ok = self.run_cmd_return_is_successful(cmd)
        return ok


class EtcdValidator(Validator):
    PATH_CLIENT_CERT = "/etc/etcd/ssl/etcd-client.pem"
    PATH_CLIENT_KEY = "/etc/etcd/ssl/etcd-client-key.pem"
    PATH_CA_CERT = "/etc/etcd/ssl/ca.pem"
    PATH_ETCD_ENDPOINTS = "/etc/etcd/etcd_endpoints.yml"
    ETCD_BASE_CMD_PATTERN = "sudo ETCDCTL_API=3 bash -c " \
                            "'etcdctl --endpoints={} --cacert=" + PATH_CA_CERT + " --cert=" + PATH_CLIENT_CERT + \
                            " --key=" + PATH_CLIENT_KEY + " {} '"
    PREREQUISITES_CHECKS = [EtcdBasicValidator]
    objective_hosts = [Objectives.ONE_MASTER]
    flg_is_ETCD_API_3 = None

    def is_etcd_API_3(self):
        if EtcdValidator.flg_is_ETCD_API_3 is None:
            cmd = "sudo ETCDCTL_API=3 bash -c 'etcdctl version'"
            EtcdValidator.flg_is_ETCD_API_3 = self.run_cmd_return_is_successful(cmd)
            # print (EtcdValidator.flg_is_ETCD_API_3)
        return EtcdValidator.flg_is_ETCD_API_3

    def get_etcd_command(self, command_body, only_available_endpoints=True):
        if only_available_endpoints:
            available_endpoints, unavailable_endpoints = self.get_etcd_endpoints_list()
            endpoints = ','.join(available_endpoints)
        else:
            cmd = "sudo cat {}".format(self.PATH_ETCD_ENDPOINTS)
            endpoints = self.get_output_from_run_cmd(cmd)
            endpoints_after_strip = re.findall('etcd_endpoints: "(.*)"', endpoints)

            if len(endpoints_after_strip) != 1:
                raise UnExpectedSystemOutput(self.get_host_ip(), cmd, endpoints,
                                             "Expected to have 'etcd_endpoints: \"<endpoints>\"' in out.")
            endpoints = endpoints_after_strip[0]

        return self.ETCD_BASE_CMD_PATTERN.format(endpoints, command_body)

    def get_curl_command_prefix(self):
        return "sudo curl --max-time 10 -s --key {} --cert {} --cacert {} -XGET ".format(self.PATH_CLIENT_KEY,
                                                                                         self.PATH_CLIENT_CERT,
                                                                                         self.PATH_CA_CERT)

    def get_etcd_members_dict(self):
        cmd = self.get_etcd_command(' member list -w=json ', only_available_endpoints=False)
        out = self.get_output_from_run_cmd(cmd)
        out_dict = json.loads(out)
        return out_dict.get('members')

    def get_etcd_endpoints_list(self):
        endpoints_list = []
        members_dict = self.get_etcd_members_dict()
        for member in members_dict:
            endpoints_list.extend(member['clientURLs'])
        return self.get_etcd_endpoints_status(endpoints_list)

    def get_etcd_endpoints_status(self, endpoints_list):
        available_endpoints = []
        unavailable_endpoints = []
        for endpoint in endpoints_list:
            cmd = self.get_curl_command_prefix() + "{}/health".format(endpoint)
            return_code, out, err = self.run_cmd(cmd, timeout=30)
            if return_code != 0:
                unavailable_endpoints.append(endpoint)
            else:
                available_endpoints.append(endpoint)
        return available_endpoints, unavailable_endpoints


class EtcdAlarmValidator(EtcdValidator):
    objective_hosts = [Objectives.ONE_MASTER]

    def __init__(self, ip):
        Validator.__init__(self, ip)

    def is_prerequisite_fulfilled(self):
        return self.is_etcd_API_3()

    def set_document(self):
        self._unique_operation_name = "etcd_alarm_validator"
        self._title = "Check if there are any alarm on etcd"
        self._failed_msg = "etcd had alarm"
        self._severity = Severity.ERROR

        self._implication_tags = [ImplicationTag.SYMPTOM, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        cmd = self.get_etcd_command("alarm list")
        # cmd = self.ETCD_BASE_CMD + "alarm list'"
        out = self.get_output_from_run_cmd(cmd)
        is_valid = (len(out.strip()) == 0)  # expecting empty string
        self._details = "the alarm from 'etcdctl alarm list' is:" + out
        return is_valid


class EtcdMemberNumberValidator(EtcdValidator):
    objective_hosts = [Objectives.ONE_MASTER]

    def __init__(self, ip):
        EtcdValidator.__init__(self, ip)

    def is_prerequisite_fulfilled(self):
        return self.is_etcd_API_3()

    def set_document(self):
        self._unique_operation_name = "etcd_has_three_members"
        self._title = "Check if there are at least 3 etcd members"
        self._failed_msg = "ETCD does not have at least three members"
        self._severity = Severity.ERROR

        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        number_of_etcd_nodes = len(self.get_etcd_members_dict())
        is_valid = number_of_etcd_nodes >= 3
        self._details = "There are " + str(number_of_etcd_nodes) + " etcd members"
        return is_valid


class EtcdLeaderValidator(EtcdValidator):
    objective_hosts = [Objectives.ONE_MASTER]

    def __init__(self, ip):
        EtcdValidator.__init__(self, ip)

    def is_prerequisite_fulfilled(self):
        return self.is_etcd_API_3()

    def set_document(self):
        self._unique_operation_name = "etcd_has_leader"
        self._title = "Check if etcd has a leader"
        self._failed_msg = "ETCD does not have a leader"
        self._severity = Severity.ERROR

        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        etcd_cmd_body = " endpoint status -w table"
        cmd = self.get_etcd_command(etcd_cmd_body)
        endpoints_status_dict = self.get_dict_from_command_output(cmd, 'linux_table', custom_delimiter='|')

        leaders = [item for item in endpoints_status_dict if item['IS LEADER'] == 'true']
        if not leaders:
            return False
        return True


class EtcdEndpointHealthValidator(EtcdValidator):
    objective_hosts = [Objectives.ONE_MASTER]

    def __init__(self, ip):
        EtcdValidator.__init__(self, ip)

    def is_prerequisite_fulfilled(self):
        return self.is_etcd_API_3()

    def set_document(self):
        self._unique_operation_name = "etcd_health_check"
        self._title = "Check etcd health with curl :2379/health"
        self._failed_msg = "ETCD endpoint is not healthy"
        self._severity = Severity.ERROR

        self._details = "The status of the accessible endpoints:\n"
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        available_endpoints, unavailable_endpoints = self.get_etcd_endpoints_list()
        for endpoint in available_endpoints:
            cmd = self.get_curl_command_prefix() + "{}/health".format(endpoint)
            return_code, out, err = self.run_cmd(cmd)
            self._details += "The health status of {} is: {}\n".format(endpoint, out)
            json_output = json.loads(out)
            if json_output.get('health') != 'true':
                unavailable_endpoints.append(endpoint)
        if unavailable_endpoints:
            self._failed_msg += "\nThe following endpoints are not available: {}".format(unavailable_endpoints)
            return False
        return True


class EtcdWriteReadValidator(EtcdValidator):
    objective_hosts = [Objectives.ONE_MASTER]

    def __init__(self, ip):
        Validator.__init__(self, ip)

    def is_prerequisite_fulfilled(self):
        return self.is_etcd_API_3()

    def set_document(self):
        self._unique_operation_name = "etcd_read_write_cycle"
        self._title = "Write data to etcd and read it back"
        self._failed_msg = "Could not complete a write and read back operation"
        self._severity = Severity.ERROR

        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        # These are just randomly generated uuid's
        key = "52093047-521a-4039-baee-429e1779c268"
        value = "40c774ad-35e4-46c5-bcd3-e1ff2b95fb67"

        cmd = self.get_etcd_command("put " + key + " " + value)
        self.get_output_from_run_cmd(cmd)

        cmd = self.get_etcd_command("get " + key)
        out = self.get_output_from_run_cmd(cmd)
        response = out.splitlines()
        cmd = self.get_etcd_command("del " + key)

        self.get_output_from_run_cmd(cmd)
        return response[1] == value


class EtcdWalFsyncdurationCheck(EtcdValidator):
    objective_hosts = [Objectives.ONE_MASTER]

    def __init__(self, ip):
        EtcdValidator.__init__(self, ip)

    def set_document(self):
        self._unique_operation_name = "etcd_wal_fsync_duration_check_based_on_metrics"
        self._title = "Check etcd  wal_fsync_duration_seconds  with curl :2379/metrics"
        self._failed_msg = "ETCD performance is slow"
        self._severity = Severity.WARNING
        self._details = ""
        self._implication_tags = [ImplicationTag.SYMPTOM, ImplicationTag.ACTIVE_PROBLEM,
                                  ImplicationTag.APPLICATION_DOMAIN]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_prerequisite_fulfilled(self):
        return self.is_etcd_API_3()

    def is_validation_passed(self):
        not_ready_list = []
        available_endpoints, unavailable_endpoints = self.get_etcd_endpoints_list()
        #        print("endpoints are {}".format(available_endpoints))
        # https://confluence.ext.net.nokia.com/display/CBCS/ETCD+Performance+Troubleshooting
        for endpoint in available_endpoints:
            cmd = self.get_curl_command_prefix() + "{}/metrics | grep etcd_disk_wal_fsync_duration_seconds".format(
                endpoint)
            out = self.get_output_from_run_cmd(cmd)
            infinity_value = 0
            check_value = 0
            total_value = 0
            if not all(k in out for k in ("Inf", "0.008", "etcd_disk_wal_fsync_duration_seconds_count")):
                self._failed_msg = "Histogram values are not present in output"
                raise UnExpectedSystemOutput(ip=endpoint,
                                             cmd=cmd,
                                             output=out,
                                             message='Histogram values are not present in output')
            for lines in out.splitlines():
                if 'Inf' in lines:
                    infinity_value = float(lines.split()[1])
                if '0.008' in lines:
                    check_value = float(lines.split()[1])
                if 'etcd_disk_wal_fsync_duration_seconds_count' in lines:
                    total_value = float(lines.split()[1])

            check_percent = (((infinity_value - check_value) / total_value) * 100)

            if check_percent > 1:
                not_ready_list.append(endpoint)
                self._failed_msg += "\nendpoint {} is slow - {} % of etcd_disk_wal_fsync_duration_seconds is more than 8 ms".format(
                    endpoint, check_percent)

        if unavailable_endpoints:
            self._failed_msg += "\nThe following endpoints are not available: {}".format(unavailable_endpoints)
        if len(not_ready_list) > 0:
            return False
        return True


class EtcdBackendCommitDurationCheck(EtcdValidator):
    objective_hosts = [Objectives.ONE_MASTER]

    def __init__(self, ip):
        EtcdValidator.__init__(self, ip)

    def set_document(self):
        self._unique_operation_name = "etcd_backend_commit_duration_check_based_on_metrics"
        self._title = "Check etcd backend_commit_duration with curl :2379/metrics"
        self._failed_msg = "ETCD performance is slow"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.SYMPTOM, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_prerequisite_fulfilled(self):
        return self.is_etcd_API_3()

    def is_validation_passed(self):
        not_ready_list = []
        available_endpoints, unavailable_endpoints = self.get_etcd_endpoints_list()

        for endpoint in available_endpoints:
            cmd = self.get_curl_command_prefix() + "{}/metrics | grep etcd_disk_backend_commit_duration_seconds". \
                format(endpoint)
            out = self.get_output_from_run_cmd(cmd)
            if not all(k in out for k in ("Inf", "0.032", "etcd_disk_backend_commit_duration_seconds_count")):
                self._failed_msg = "Histogram values are not present in output"
                raise UnExpectedSystemOutput(ip=endpoint,
                                             cmd=cmd,
                                             output=out,
                                             message='Histogram values are not present in output')
            infinity_value = 0
            check_value = 0
            total_value = 0
            for lines in out.splitlines():
                if 'Inf' in lines:
                    infinity_value = float(lines.split()[1])
                if '0.032' in lines:
                    check_value = float(lines.split()[1])
                if 'etcd_disk_backend_commit_duration_seconds_count' in lines:
                    total_value = float(lines.split()[1])
            check_percent = (((infinity_value - check_value) / total_value) * 100)
            if check_percent > 1:
                not_ready_list.append(endpoint)
                self._failed_msg += "\nEndpoint {} is slow, {} % of etcd_disk_backend_commit_duration_seconds_count is more than 32 ms".format(
                    endpoint, check_percent)
        if unavailable_endpoints:
            self._failed_msg += "\nThe following endpoints are not available: {}".format(unavailable_endpoints)
        if len(not_ready_list) > 0:
            return False

        return True


class CalicoKubernetesAlignNodes(EtcdValidator):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._unique_operation_name = "calico_kubernetes_check"
        self._title = "Check if nodes in Calico align with nodes in Kubernetes"
        self._failed_msg = "Nodes on Calico not aligned with nodes in Kubernetes"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._is_clean_cmd_info = True

    def is_prerequisite_fulfilled(self):
        return self.is_etcd_API_3()

    def is_validation_passed(self):
        etcd_cmd = 'sudo ETCDCTL_API=3 bash -c "etcdctl get /calico/resources/v3/projectcalico.org/nodes/ --prefix ' \
                   '--keys-only --endpoints=$(sudo cat /etc/etcd/etcd_endpoints.yml|cut -d\' \' -f2|tr -d \'\"\') ' \
                   '--cacert={} --cert={} --key={}| awk NF"'.format(EtcdValidator.PATH_CA_CERT,
                                                                    EtcdValidator.PATH_CLIENT_CERT,
                                                                    EtcdValidator.PATH_CLIENT_KEY)
        kube_cmd = "sudo kubectl get nodes"

        return_code, etcd_output, etcd_err = self.run_cmd(etcd_cmd)
        kube_output = self.get_output_from_run_cmd(kube_cmd)

        etcd_names = [line.split('/')[-1].strip() for line in etcd_output.strip().split('\n')]
        kubectl_names = [line.split()[0] for line in kube_output.strip().split('\n')[1:]]

        if sorted(etcd_names) == sorted(kubectl_names):
            return True
        missing_calico_nodes = list(set(kubectl_names) - set(etcd_names))
        if missing_calico_nodes:
            self._failed_msg += '\nFollowing nodes not on Calico: {}'.format(missing_calico_nodes)
        missing_k8s_nodes = list(set(etcd_names) - set(kubectl_names))
        if missing_k8s_nodes:
            self._failed_msg += '\nFollowing nodes not on Kubernetes: {}'.format(missing_k8s_nodes)
        return False


class EtcdNetworkPeerRoundTripTimeCheck(EtcdValidator):
    objective_hosts = [Objectives.ONE_MASTER]

    def __init__(self, ip):
        EtcdValidator.__init__(self, ip)

    def is_prerequisite_fulfilled(self):
        host_executors = sys_parameters.get_host_executor_factory().get_all_host_executors()
        all_nodes = [host_executor for host_executor in list(host_executors.values()) if Objectives.ALL_NODES in host_executor.roles]
        # when only 1 node in cluster no peer.
        if len(list(all_nodes)) > 1 and self.is_etcd_API_3():
            return True

        return False

    def set_document(self):
        self._unique_operation_name = "etcd_network_peer_round_trip_time_check_based_on_metrics"
        self._title = "Check etcd network_peer_round_trip_time with curl :2379/metrics"
        self._failed_msg = "ETCD performance is slow"
        self._severity = Severity.ERROR
        self._details = ""
        self._implication_tags = [ImplicationTag.SYMPTOM, ImplicationTag.APPLICATION_DOMAIN]

    def is_validation_passed(self):
        member_raw_dict = self.get_etcd_members_raw_dict()
        #        print(member_raw_dict)
        # "{u'https://172.17.3.4:2379': u'18378e0f18dcbd28', u'https://172.17.3.5:2379': u'2ec849e0b90211f1', u'https://172.17.3.3:2379': u'99c33a6bf63820bf'}",'
        member_notreadylist = []
        for k in member_raw_dict:
            #    print(k)
            sample_dict = member_raw_dict.copy()
            sample_dict.pop(k)
            cmd1 = self.get_curl_command_prefix() + k + "/metrics | grep etcd_network_peer_round_trip_time_seconds"
            out1 = self.get_output_from_run_cmd(cmd1)
            if not all(k in out1 for k in ("Inf", "0.0512", "etcd_network_peer_round_trip_time_seconds_count")):
                self._failed_msg = "Histogram values are not present in output"
                raise UnExpectedSystemOutput(ip=self._host_executor.ip,
                                             cmd=cmd1,
                                             output=out1,
                                             message='Histogram values are not present in output')

            not_readylist = []
            for value in list(sample_dict.values()):
                value_list = []
                for lines in out1.splitlines():
                    if value in lines:
                        value_list.append(lines)
                status, percent = self.test_etcd_network_peer_round_trip_time(value_list)
                if not status:
                    not_readylist.append(value)
                    self._validation_log.append("for member{} with endpoint {}, {} % percent of ".format(
                        member_raw_dict[k], k, percent) +
                                                " etcd_network_peer_round_trip_time to member {} is ".format(value) + ""
                                                                                                                      "more than 50 ms")
            if len(not_readylist) > 0:
                member_notreadylist.append(k)
        self._validation_log.append("member_notreadylist is {}".format(member_notreadylist))
        if len(member_notreadylist) > 0:
            return False
        return True

    def get_etcd_members_raw_dict(self):
        '''[root@fi808-ncs20fp2fi808-masterbm-0 ~]# ETCDCTL_API=3 etcdctl --endpoi7nts=$(cat /etc/etcd/etcd_endpoints.yml|cut -d' ' -f2|tr -d '"') --cacert=/etc/etcd/ssl/ca.pem --cert=/etc/etcd/ssl/etcd-client.pem --key=/etc/etcd/ssl/etcd-client-key.pem member list
18378e0f18dcbd28, started, fi808-ncs20fp2fi808-masterbm-1, https://172.17.3.4:2380, https://172.17.3.4:2379
2ec849e0b90211f1, started, fi808-ncs20fp2fi808-masterbm-2, https://172.17.3.5:2380, https://172.17.3.5:2379
99c33a6bf63820bf, started, fi808-ncs20fp2fi808-masterbm-0, https://172.17.3.3:2380, https://172.17.3.3:2379
[root@fi808-ncs20fp2fi808-masterbm-0 ~]# ETCDCTL_API=3 etcdctl --endpoints=$(cat /etc/etcd/etcd_endpoints.yml|cut -d' ' -f2|tr -d '"') --cacert=/etc/etcd/ssl/ca.pem --cert=/etc/etcd/ssl/etcd-client.pem --key=/etc/etcd/ssl/etcd-client-key.pem member list -w json
{"header":{"cluster_id":17344006751478806447,"member_id":3371025550612238833,"raft_term":87},"members":[{"ID":1745019576122129704,"name":"fi808-ncs20fp2fi808-masterbm-1","peerURLs":["https://172.17.3.4:2380"],"clientURLs":["https://172.17.3.4:2379"]},{"ID":3371025550612238833,"name":"fi808-ncs20fp2fi808-masterbm-2","peerURLs":["https://172.17.3.5:2380"],"clientURLs":["https://172.17.3.5:2379"]},{"ID":11079763743628337343,"name":"fi808-ncs20fp2fi808-masterbm-0","peerURLs":["https://172.17.3.3:2380"],"clientURLs":["https://172.17.3.3:2379"]}]}
[root@fi808-ncs20fp2fi808-masterbm-0 ~]#'''

        available_endpoints, unavailable_endpoints = self.get_etcd_endpoints_list()
        cmd = self.get_etcd_command(' member list')
        out = self.get_output_from_run_cmd(cmd)
        mem_dict = dict.fromkeys(available_endpoints, 0)
        for lines in out.splitlines():
            for key in mem_dict:
                if key in lines:
                    mem_dict[key] = lines.split(",")[0]
        return mem_dict

    def test_etcd_network_peer_round_trip_time(self, value_list):
        infinity_value = 0
        check_value = 0
        total_value = 0
        for lines in value_list:
            if 'Inf' in lines:
                infinity_value = float(lines.split()[1])
            if '0.0512' in lines:
                check_value = float(lines.split()[1])
            if 'etcd_network_peer_round_trip_time_seconds_count' in lines:
                total_value = float(lines.split()[1])
        check_percent = (((infinity_value - check_value) / total_value) * 100)
        if check_percent > 1:
            return False, check_percent
        return True, check_percent

class EtcdDBSizeValidator(EtcdValidator):
    objective_hosts = [Objectives.ONE_MASTER]
    THRESHOLD_DB_SIZE = 70
    BYTES_IN_GB = 1024 ** 3

    def is_prerequisite_fulfilled(self):
        return self.is_etcd_API_3()

    def set_document(self):
        self._unique_operation_name = "etcd_db_size_check"
        self._title = "Validate ETCD DB usage exceeded {}%".format(EtcdDBSizeValidator.THRESHOLD_DB_SIZE)
        self._failed_msg = "ETCD DB usage exceeds {}% ".format(EtcdDBSizeValidator.THRESHOLD_DB_SIZE)
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.RISK_RESOURCE_CLEANING_RECOMMENDED, ImplicationTag.SYMPTOM,
                                  ImplicationTag.APPLICATION_DOMAIN]
        self._is_clean_cmd_info = True

    def is_validation_passed(self):
        available_endpoints, unavailable_endpoints = self.get_etcd_endpoints_list()
        if len(available_endpoints) == 0:
            raise UnExpectedSystemOutput(self.get_host_ip(), available_endpoints, available_endpoints,
                                         "Expected to have etcd_endpoints")
        grep_command = self.get_curl_command_prefix() + "{}/metrics | grep etcd_server_quota_backend_bytes | grep -v '#' ".format(available_endpoints[0])
        configured_db_size = self.get_output_from_run_cmd(grep_command).split()[1]
        try:
            configured_db_size_gb = float(configured_db_size) / self.BYTES_IN_GB
        except ValueError:
            raise UnExpectedSystemOutput(ip=self._host_executor.ip,
                                         cmd=configured_db_size,
                                         output="expected int found '{}'".format(configured_db_size))

        exceeded_db_size_list = []
        etcd_cmd_body = " endpoint status -w json"
        cmd = self.get_etcd_command(etcd_cmd_body)
        endpoints_status_dict = self.get_dict_from_command_output(cmd, out_format='json')
        for item in endpoints_status_dict:
            used_db_size = item['Status']['dbSize']
            try:
                used_db_size_gb = float(used_db_size) / self.BYTES_IN_GB
            except ValueError:
                raise UnExpectedSystemOutput(ip=self._host_executor.ip,
                                             cmd=used_db_size,
                                             output="expected int found '{}'".format(used_db_size))

            db_filled_percentage = ((used_db_size_gb / configured_db_size_gb) * 100)
            if db_filled_percentage > EtcdDBSizeValidator.THRESHOLD_DB_SIZE:
                self._failed_msg += "\nendpoint {} ETCD DB use is {:.2f} GB and it's more than {}% of the configured DB size of {:.2f} GB".format(
                    item['Endpoint'], used_db_size_gb, EtcdDBSizeValidator.THRESHOLD_DB_SIZE, configured_db_size_gb)
                exceeded_db_size_list.append(item['Endpoint'])
        if len(exceeded_db_size_list) > 0:
            return False
        return True


class VerifyETCDRulesPresentInIPtables(EtcdValidator):
    objective_hosts = [Objectives.MASTERS]

    def is_prerequisite_fulfilled(self):
        return self.is_etcd_API_3()

    def set_document(self):
        self._unique_operation_name = "verify_etcd_rules_present_in_iptables"
        self._title = "Verify ETCD rules present in IP tables"
        self._failed_msg = "ETCD rules not present in IP tables"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        cmd = "sudo iptables -t nat -L | grep 2379"
        return_code, out, err = self.run_cmd(cmd)
        if not out:
            return False
        return True
class EtcdScaleInLeftovers(Validator):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._title = "ETCD Scale-in Leftovers"
        self._unique_operation_name = "etcd_scale_in_leftovers"
        self._failed_msg = "Leftover data in etcd db after scale in"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.RISK_GARBAGE_CLEANING_RECOMMENDED]
        self._blocking_tags = [BlockingTag.SCALE]

    def is_validation_passed(self):
        check_leftover_values_etcd = ("ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 "
                                      "--cacert=/etc/etcd/ssl/ca.pem --cert=/etc/etcd/ssl/etcd-client.pem "
                                      "--key=/etc/etcd/ssl/etcd-client-key.pem get /ncms --prefix")
        leftover_values_etcd = self.run_cmd_return_is_successful(check_leftover_values_etcd)
        if leftover_values_etcd:
            return False
        else:
            return True

class EtcdPerformanceCheck(Validator):
    objective_hosts = [Objectives.MASTERS]
    THRESHOLD_WARNING_MSG = 1500
    def set_document(self):
        self._unique_operation_name = "ETCD_Performance"
        self._title = "Validate that ETCD requests don't take longer than 2 seconds"
        self._failed_msg = "ETCD requests took longer than 2 seconds.\n"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.PERFORMANCE]

    def get_grep_cmd_for_high_duration(self, file_name):
        # greping only etcd lines that "took" more than 2 seconds:
        # We utilized grep logic despite its lower maintainability because we wanted to avoid loading the
        # entire output into memory, as the number of lines could be extremely large
        # note this grep wil catch "took":"2.66s","took":"22.66s", and "took":"3.66s", (good)
        # will not catch "took":"1.66s" or "took":"21.66s" (good, bad)
        # This is acceptable because we are statistically summing values above 2 seconds,
        # so a very small fraction of values around 21 seconds is not significant.
        grep_command = r"sudo grep 'took too long' {}| grep etcd | grep -E '[2-9]+\.[0-9]+s'".format(file_name)
        return grep_command

    def is_validation_passed(self):
        find_command = "find /var/log -maxdepth 1  -mtime -5 -type f -name 'messages*' -exec ls -t {} +"
        out = self.get_output_from_run_cmd(find_command)
        if out:
            file_name = out.split()[0]
            grep_command = self.get_grep_cmd_for_high_duration(file_name) + "| wc -l"
            number_of_matches_str = self.get_output_from_run_cmd(grep_command).strip()
            if not number_of_matches_str.isnumeric():
                raise UnExpectedSystemOutput(self.get_host_ip(), grep_command, number_of_matches_str)
            number_of_matches = int(number_of_matches_str)
            if number_of_matches > EtcdPerformanceCheck.THRESHOLD_WARNING_MSG:
                self._failed_msg += "There're about {} messages requests with 'took too long' that took more then 2 seconds at {} \n".format(
                    number_of_matches, file_name)
                return False
        return True


class EtcdBCMTTransactionsCountValidator(EtcdValidator):
    objective_hosts = [Objectives.ONE_MASTER]
    TRANSACTION_COUNT_THRESHOLD = 30000

    def set_document(self):
        self._unique_operation_name = "etcd_bcmt_transactions_count_check"
        self._title = "Verify number of BCMT transactions in ETCD is not too high"
        self._failed_msg = "Too many transactions found under /BCMTClusterManager/transactions in etcd"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.PERFORMANCE]

    def is_prerequisite_fulfilled(self):
        return self.is_etcd_API_3()

    def is_validation_passed(self):
        command_body = (
            "get --prefix /BCMTClusterManager/ --keys-only | "
            "grep BCMTClusterManager/transactions/ | wc -l"
        )
        etcd_cmd = self.get_etcd_command(command_body, only_available_endpoints=False)
        etcd_output = self.get_output_from_run_cmd(etcd_cmd)
        transactions_count = int(etcd_output)

        if transactions_count > self.TRANSACTION_COUNT_THRESHOLD:
            self._failed_msg +="\nnumber of transactions found: {} , transactions threshold: {}".format(transactions_count, self.TRANSACTION_COUNT_THRESHOLD)
            return False
        return True
