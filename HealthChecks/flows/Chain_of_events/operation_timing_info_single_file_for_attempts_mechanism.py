from __future__ import absolute_import
from flows.Chain_of_events.operation_timing_info_mechanism import OperationTimingInfoMechanism
from HealthCheckCommon.log_flows.base_log_issues_finder_flow import *
import datetime
from tools.global_logging import log
from six.moves import range

class OperationTimingInfoSingleFileForAttemptsMechanism(OperationTimingInfoMechanism):

    def _create_list_of_times_dicts(self, log_path):
        '''
        In this mechanism, we grep log file by 'searched_patterns' and go over all results

         Example of returned value  'operation_list':
        [{'start_time': '2021-03-05 15:00:07', 'end_time': '2021-03-05 17:25:03', 'status': 'Passed'},
        {'start_time': '2021-04-08 15:15:49', 'end_time': '2021-04-08 17:02:31', 'status': 'Failed'}
        '''
        datetimes_dict = self._get_timestamps_from_cmd_output(log_path)
        log('datetimes_dict of operation {} by log path {}:'.format(self._operation['name'], log_path))
        log(datetimes_dict)
        operation_list = []
        if datetimes_dict:
            operation_list = self._datetimes_dict_to_operation_list(datetimes_dict)
        for attempt in operation_list:
            attempt['log_path'] = log_path.split('|')[0]
            attempt['host_name'] = self._get_host_name()
        return operation_list

    def _get_timestamps_from_cmd_output(self, log_path):
        '''
        Example of returned value  'datetimes_dict':
        {'start_time': ['2021-03-05 15:00:07', '2021-04-08 15:15:49', '2021-10-22 04:02:52'],
         'end_time': ['2021-03-05 17:25:03', '2021-04-08 17:02:31', '2021-10-22 04:40:46', ],
         'success_search': ['2021-03-05 17:25:06', '2021-04-08 17:02:34', '2021-10-22 04:40:49']}
        '''
        datetimes_dict = {}
        for pattern in self._operation['searched_patterns']:
            datetimes_dict[pattern] = []
            cmd = self._command_builder(pattern, log_path)
            out, full_output = self.get_command_result(cmd)
            if not out:
                continue
            out_list = out.split("\n")
            for line in out_list:
                timestamp = self._get_timestamp_from_log(line)
                if timestamp != "":
                    datetimes_dict[pattern].append(timestamp)

        return datetimes_dict

    def _datetimes_dict_to_operation_list(self, datetimes_dict):
        operation_list = []
        end_idx = 0
        self._check_if_operation_searched_patterns_are_supported()
        start_time_range = list(range(len(datetimes_dict['start_time'])))
        if datetimes_dict['start_time'] is not None:
            for start_idx in start_time_range:
                attemp_dict = {}
                attemp_dict['start_time'] = datetimes_dict['start_time'][start_idx]
                if 'end_time' in self._operation['searched_patterns']:
                    if datetimes_dict['end_time']:
                        if end_idx >= len((datetimes_dict['end_time'])):
                            attempt_end_time = ''
                        else:
                            attempt_end_time = datetimes_dict['end_time'][end_idx]
                        if attempt_end_time != '':
                            next_start_time = datetimes_dict['start_time'][start_idx + 1] if start_idx != \
                                                                                             start_time_range[
                                                                                                 -1] else ''
                            if self._is_end_time_before_next_start_time(attempt_end_time, next_start_time):
                                attemp_dict['end_time'] = attempt_end_time
                                end_idx += 1
                                if 'success_search' in self._operation['searched_patterns']:
                                    attemp_dict['status'] = self._get_success_search(attemp_dict['start_time'],
                                                                                     attemp_dict['end_time'],
                                                                                     datetimes_dict['success_search'])
                operation_list.append(attemp_dict)
            return operation_list

    def _check_if_operation_searched_patterns_are_supported(self):
        supported_searched_patterns = ['start_time', 'end_time', 'end_time_by_task_id', 'success_search']
        unsupported_searched_patterns = [x for x in self._operation['searched_patterns'] if
                                         x not in supported_searched_patterns]
        assert not unsupported_searched_patterns, "The searched_patterns {} of operation '{}' not suppported".format(
            unsupported_searched_patterns, self._operation['name'])

    def _get_success_search(self, start_time, end_time, search_time_list):
        for search_time in search_time_list:
            if not isinstance(start_time, datetime.date):
                start_time = datetime.datetime.strptime(start_time, self.TIME_FORMAT)
            if not isinstance(end_time, datetime.date):
                end_time = datetime.datetime.strptime(end_time, self.TIME_FORMAT)
            search_time = datetime.datetime.strptime(search_time, self.TIME_FORMAT)
            if self._is_timestamp_in_between(search_time, start_time, end_time):
                return 'Passed'
        return 'Failed'
