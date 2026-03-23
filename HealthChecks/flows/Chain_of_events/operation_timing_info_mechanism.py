from __future__ import absolute_import
from HealthCheckCommon.operations import DataCollector
from tools import python_versioning_alignment
from HealthCheckCommon.log_flows.base_log_issues_finder_flow import *
import re
import datetime
import tools.sys_parameters as gs
from tools.global_logging import log


class OperationTimeLineCmdRunner(DataCollector):
    objective_hosts = []
    handle_error = False

    def collect_data(self, **kwargs):
        code, out, err = self.run_cmd(cmd=kwargs['cmd'], timeout=kwargs['timeout'], add_bash_timeout=True)
        res = {}
        res["out"] = out
        res["err"] = err
        res["code"] = code
        return res


class OperationTimingInfoMechanism(object):
    TIME_FORMAT = '%Y-%m-%d %H:%M:%S'

    def __init__(self, objective_role, operation, caller_object):
        self._operation = operation
        self._objective_role = objective_role
        self._searched_patterns_type = None
        self._searched_patterns_value = None
        self._caller_operation_object = caller_object
        self._is_operation_host_name_in_log = self.is_operation_host_name_search_defined_in_json()

    def get_command_result(self, cmd, timeout=60):
        OperationTimeLineCmdRunner.objective_hosts = self._objective_role
        if type(self._objective_role) not in [dict, list]:
            OperationTimeLineCmdRunner.objective_hosts = [self._objective_role]
        res = list(self._caller_operation_object.run_data_collector(
            OperationTimeLineCmdRunner, cmd=cmd, timeout=timeout).values())
        if not res or not res[0]:
            return "", ""
        res = res[0]
        out = res.get("out", "")
        err = res.get("err", "")
        full_output = out + err
        if not out:
            return [], full_output
        return out, ""

    def _get_timestamp_from_log(self, log_line, separator=","):
        full_timestamp = re.split(separator, log_line)[0]
        timestamp = re.sub(',[0-9]+ ', '',
                           full_timestamp)  # remove chars after the seconds in the date, for example: remove ",591 " from "2022-02-17 11:27:26,591 "
        return timestamp

    def _create_list_of_times_dicts(self, log_path):
        raise NotImplementedError

    def _is_end_time_before_next_start_time(self, end_time, next_start_time):
        if next_start_time == '':
            return True
        if not isinstance(end_time, datetime.date):
            end_time = datetime.datetime.strptime(end_time, self.TIME_FORMAT)
        if not isinstance(next_start_time, datetime.date):
            next_start_time = datetime.datetime.strptime(next_start_time, self.TIME_FORMAT)
        if end_time < next_start_time:
            return True
        return False

    def _command_builder(self, pattern, log_path):
        return "{} {}".format(self._operation['searched_patterns'][pattern], log_path)

    def _execution_time_for_log_path(self, out):
        execution_time = []
        out_list = out.split("\n")
        for out in out_list:
            separator = "[[]| - "
            out_sep = re.split(separator, out)[0]
            time_line = re.sub(',[0-9]+', '',
                               out_sep)  # remove chars after the seconds in the date, for example: remove ",591" from "2022-02-17 11:27:26,591"
            if time_line != "":
                execution_time.append(time_line)
        execution_time = [i for i in execution_time if i]
        return execution_time

    def _verify_log_path(self, log_path):
        log_path_dir_list = ["/var/log/cbis", "/mnt/log/cbis", "/home/stack/overcloud-deploy/overcloud/heat-launcher/log/"]
        if gs.get_deployment_type() in Deployment_type.get_ncs_vsphere_openstack_types():
            log_path_dir_list = ["/opt/clcm/log/", "/opt/bcmt/log/"]
        is_log_dir_correct = False
        for item_log_dir in log_path_dir_list:
            if item_log_dir in log_path:
                is_log_dir_correct = True
                break
        assert is_log_dir_correct, "If log path not in regular place, " \
                                   "please add it to the container volume"

    def _is_timestamp_in_between(self, now, start, end):
        if not isinstance(now, datetime.date):
            now = datetime.datetime.strptime(now, self.TIME_FORMAT)
        if not isinstance(start, datetime.date):
            start = datetime.datetime.strptime(start, self.TIME_FORMAT)
        if not isinstance(end, datetime.date):
            end = datetime.datetime.strptime(end, self.TIME_FORMAT)
        end_in_20_seconds = end + timedelta(seconds=20)
        is_between = start <= now <= end_in_20_seconds
        return is_between

    def _get_host_name(self, log_path="", log_host_location=False):
        if self._is_operation_host_name_in_log and not log_host_location:
            return self._get_host_name_from_log(log_path)
        elif self._objective_role in ['hypervisor', 'undercloud']:
            return self._objective_role
        elif self._objective_role == Objectives.ICE_CONTAINER and Deployment_type.is_cbis(gs.get_deployment_type()):
            return 'undercloud'
        else:
            return list(gs.get_host_executor_factory().execute_cmd_by_roles(
                roles=[self._objective_role], cmd='hostname', timeout=10).values())[0]['out'].strip()

    def get_file_size(self, file_path):
        if os.path.splitext(file_path)[1] == ".gz":
            file_size_cmd = "gzip -dc {} | wc -c".format(file_path)
            file_size_out = list(gs.get_host_executor_factory().execute_cmd_by_roles(roles=[self._objective_role],
                                                                                     cmd=file_size_cmd).values())[0]
            file_size = file_size_out['out']
        else:
            file_size_cmd = "sudo ls -l {}".format(file_path)
            file_size_out = list(gs.get_host_executor_factory().execute_cmd_by_roles(roles=[self._objective_role],
                                                                                     cmd=file_size_cmd).values())[0]
            file_size = file_size_out['out'].split()[4]
        return file_size

    def _get_the_relevant_log_path_from_log_path_list(self):
        relevant_log_path = None
        for log_path in self._operation['log_path']:
            cmd = "sudo ls {}".format(log_path)
            out, full_output = self.get_command_result(cmd)
            if out:
                relevant_log_path = log_path
                break
        return relevant_log_path

    def get_times_dicts_list(self):
        log_path = self._get_the_relevant_log_path_from_log_path_list()  # Assuming only one relevant log path for each operation
        times_dicts_list = []
        if log_path:
            self._verify_log_path(log_path)
            log("Operation name is '{}', log_path: {}".format(self._operation['name'], log_path))
            times_dicts_list = self._create_list_of_times_dicts(log_path=log_path)
        return times_dicts_list

    def _get_host_name_from_log(self, log_path):
        '''
        pattern of CNA for cluster_heal ([^".]+) : Matches everything before the first dot within the double quotes.
        Catch 'ukytu-t10-kncs01-ctr-03' from:
        openstack --insecure server rebuild "ukytu-t10-kncs01-ctr-03.cluster.domain"
        pattern of CNB for cluster_heal \\[([^[\\]]+)\\] : Matches everything in square brackets [].
        Assuming the pattern includes the square brackets, so they will not be retrieved in the result of re.findall.
        '''
        hosts_names_list = []
        if log_path:
            cmd = self._command_builder('operation_host_name', log_path)
            out, full_output = self.get_command_result(cmd)
            pattern = self._operation['searched_patterns'].get('pattern_for_extracting_host_name')
            if out:
                found_hosts = re.findall(pattern, out)
                if len(found_hosts) == 1 and "," in found_hosts[0]:
                    if type(found_hosts[0]) == python_versioning_alignment.get_unicode_type():
                        found_hosts[0] = found_hosts[0].encode('ascii', 'ignore').decode('ascii')
                    found_hosts = found_hosts[0].split(',')
                updated_found_hosts = [host.strip().replace("u'", "").replace("'", "") for host in found_hosts]
                hosts_names_list = list(set(updated_found_hosts))
            else:
                hosts_names_list.append("No host name found in log")
        return hosts_names_list

    def is_operation_host_name_search_defined_in_json(self):
        if self._operation['searched_patterns'].get('operation_host_name'):
            assert self._operation['searched_patterns'].get('pattern_for_extracting_host_name'), \
                ("Assertion failed for operation '{}'. 'operation_host_name' field is defined, "
                 "but 'pattern_for_extracting_host_name' is missing. Both fields must be present together "
                 "in the JSON file.".format(self._operation['name']))
            return True
        return False
