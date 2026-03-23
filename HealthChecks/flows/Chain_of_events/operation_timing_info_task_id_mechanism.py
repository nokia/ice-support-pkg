from __future__ import absolute_import
from flows.Chain_of_events.operation_timing_info_mechanism import OperationTimingInfoMechanism
from HealthCheckCommon.log_flows.base_log_issues_finder_flow import *
import datetime
from tools.global_logging import  log
from six.moves import range

class OperationTimingInfoTaskIdMechanism(OperationTimingInfoMechanism):

    def _create_list_of_times_dicts(self, log_path):
        '''
        In this mechanism, we get task_id by 'start_time', grep log file by 'task_id' and go over all results

         Example of returned value  'operation_list':
        [{'start_time': '2021-03-05 15:00:07', 'end_time': '2021-03-05 17:25:03', 'status': 'Passed'},
        {'start_time': '2021-04-08 15:15:49', 'end_time': '2021-04-08 17:02:31', 'status': 'Failed'}
        '''
        if not os.path.splitext(log_path)[1].lower() == ".log":
            out_list = [log_path]
        else:
            out, full_output = self.get_command_result("sudo ls {}".format(log_path))
            if not out:
                return []
            out_list = [file_path for file_path in out.split() if int(self.get_file_size(file_path)) != 0]
        operation_list = []
        task_operations = {}
        for file_path in out_list:
            file_path_operation_dict = self._get_timestamps_by_task_id(file_path)
            log('datetimes_dict of operation {} by log path {}:'.format(self._operation['name'], file_path))
            log(file_path_operation_dict)
            task_operations = self.remove_duplicate_operations(file_path_operation_dict, task_operations, file_path)
        if task_operations:
            operation_list.extend(list(task_operations.values()))
        return operation_list

    def _get_timestamps_by_task_id(self, log_path):
        '''
        Example of returned value  'datetimes_dict':
        {'fc9d8ac5': {'start_time': '2021-03-05 15:00:07', 'end_time': '2021-03-05 17:25:03', 'status': 'Passed'},
         '31014b8a': {'start_time': '2021-04-08 15:15:49', 'end_time': '2021-04-08 17:02:31', 'statuss': 'Failed'}}
        '''
        datetimes_dict = {}
        assert (self._operation['searched_patterns'].get("end_time_by_task_id") and
                self._operation['searched_patterns'].get("start_time")) or \
               (not self._operation['searched_patterns'].get("end_time_by_task_id")), \
            "'start_time' must be initialized for {} if 'end_time_by_task_id' is initialized".format(
                self._operation["name"])
        assert (self._operation['searched_patterns'].get("end_time_by_task_id") and
                not self._operation['searched_patterns'].get("end_time")) or \
               (not self._operation['searched_patterns'].get("end_time_by_task_id")), \
            "Do not initialize 'end_time' if 'end_time_by_task_id' is initialized"
        cmd = self._command_builder("start_time", log_path)
        out, full_output = self.get_command_result(cmd)
        if not out:
            return datetimes_dict
        out_list = out.split("\n")
        for i in range(len(out_list)):
            line = out_list[i]
            start_timestamp = self._get_timestamp_from_log(line)
            if start_timestamp != "":
                next_start_time = self.get_next_start_time(out_list, i)
                task_id = line.split(" INFO:")[1].strip().split("-")[0]
                assert task_id, "couldn't get task_id from: '{}'".format(line)
                datetimes_dict[task_id] = {}
                datetimes_dict[task_id]["start_time"] = start_timestamp
                '''
                Example of start time line: "2021-06-08 11:32:02,858     INFO: afc204e5-Request: afc204e5 POST https://127.0.0.1:8082/ncms/api/v1/cluster?install_type=cli"
                '''
                end_time = self._get_end_time_from_start_time_task_id(task_id, log_path, next_start_time)
                if end_time:
                    datetimes_dict[task_id]["end_time"] = end_time
                    if self._operation['searched_patterns'].get("success_search"):
                        datetimes_dict[task_id]["status"] = self._get_success_search_from_start_time_task_id(
                            task_id, log_path, start_timestamp, self._operation['searched_patterns']["success_search"],
                            end_time)
        return datetimes_dict

    def _get_success_search_from_start_time_task_id(self, task_id, log_path, start_time, pattern, end_time):
        task_out, task_full_output = self.get_command_result("sudo grep -i {task_id} {log_path}  | {pattern}".format(
            task_id=task_id, log_path=log_path, pattern=pattern))
        if not task_out:
            return 'Failed'
        task_out_list = task_out.strip().split("\n")
        for task_line in task_out_list:
            search_time = self._get_timestamp_from_log(task_line)
            if self._is_timestamp_in_between(search_time, start_time, datetime.datetime.strptime(end_time, self.TIME_FORMAT)):
                return 'Passed'
        return 'Failed'

    def _get_end_time_from_start_time_task_id(self, task_id, log_path, next_start_time):
        task_out, task_full_output = self.get_command_result("sudo grep -i {} {}".format(task_id, log_path))
        task_out_list = task_out.strip().split("\n")
        for task_line in reversed(task_out_list):
            end_timestamp = self._get_timestamp_from_log(task_line)
            if end_timestamp != "" and self._is_end_time_before_next_start_time(end_timestamp, next_start_time):
                return end_timestamp

    def get_next_start_time(self, out_list, i):
        for inx in range(i + 1, len(out_list)):
            line = out_list[inx]
            start_timestamp = self._get_timestamp_from_log(line)
            if start_timestamp != "":
                return start_timestamp
        return ''

    def remove_duplicate_operations(self, file_path_operation_dict, task_operations, file_path):
        for task_id in file_path_operation_dict:
            if not task_operations or not task_operations.get(task_id) or \
                    task_operations[task_id]["start_time"] != file_path_operation_dict[task_id]["start_time"]:
                task_operations[task_id] = file_path_operation_dict[task_id]
                task_operations[task_id]['log_path'] = file_path
                task_operations[task_id]['host_name'] = self._get_host_name()
        return task_operations
