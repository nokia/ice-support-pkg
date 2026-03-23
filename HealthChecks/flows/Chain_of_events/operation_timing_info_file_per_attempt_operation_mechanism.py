from __future__ import absolute_import
from flows.Chain_of_events.operation_timing_info_mechanism import OperationTimingInfoMechanism
import os
import tools.sys_parameters as gs
import datetime


class OperationTimingInfoFilePerAttemptOperationMechanism(OperationTimingInfoMechanism):

    def _create_list_of_times_dicts(self, log_path):
        '''
        In this mechanism, each attempt of the operation creates a new log file.
         'start_time' by having timestamp from first line of log file.
         'end_time' by having timestamp from last line of log file.

         Example of returned value  'operation_list':
        [{'log_path': '/var/log/cbis/deployment.log', 'status': 'Failed', 'start_time': '2021-03-05 16:00:56', 'host_name': 'hypervisor', 'end_time': '2021-03-05 16:11:59'},
        {'log_path': '/var/log/cbis/deployment.log.2021-02-26T12:39:49.770529', 'status': 'Failed', 'start_time': '2021-02-26 17:28:24', 'host_name': 'hypervisor', 'end_time': '2021-02-26 12:39:49'}]
        '''
        skipped_hosts = ['entire-cluster', 'all-controllers', 'all-storage-nodes', 'OVS Aggregate', 'OvsCompute Aggregate']
        operation_list = []
        cmd = "sudo ls {}".format(log_path)
        out, full_output = self.get_command_result(cmd)
        for file_path in out.splitlines():
            file_size = self.get_file_size(file_path)
            if int(file_size) == 0:
                continue
            log_path = file_path
            if self._is_operation_host_name_in_log:
                # Add the host name where the log is located, before the log path. For example: 'deployer: /opt/clcm/log/clcm*.log'
                log_path = "{log_location}: {file_path}".format(log_location=self._get_host_name(
                    log_host_location=True), file_path=file_path)
            if self._operation['searched_patterns'].get('operation_search'):
                if not self.is_operation_search_found(file_path):
                    continue
            host_names = self._get_host_name(log_path=file_path)
            if not isinstance(host_names, list):
                host_names = [host_names]
            for host_name in host_names:
                if host_name in skipped_hosts:
                    continue
                self._set_operation_info_values(log_path, host_name, file_path, operation_list)

        return operation_list

    def _set_operation_info_values(self, log_path, host_name, file_path, operation_list):
        operation_info = {}
        operation_info['log_path'] = log_path
        operation_info['host_name'] = host_name.strip()
        operation_info['start_time'] = self._get_operation_time('start_time', file_path)
        operation_info['end_time'] = self._get_operation_time('end_time', file_path)
        if self._operation['searched_patterns'].get('success_search'):
            operation_info['status'] = self._get_operation_status(operation_info, file_path)
        if operation_info is not None:
            operation_list.append(operation_info)

    def _get_operation_time(self, key_time, file_path):
        if self._operation['searched_patterns'].get(key_time):
            return self._get_time_by_pattern(key_time, file_path)
        else:
            return self._get_time_from_log(key_time, file_path)

    def _get_time_by_pattern(self, key_time, file_path):
        return self.get_log_info(file_path, self._operation['searched_patterns'][key_time])

    def _get_time_from_log(self, key_time, file_path):
        return self.get_log_info(file_path, key_time)

    def _get_operation_status(self, operation_info, file_path):
        origin_searched_patterns = self._operation['searched_patterns']['success_search']
        if '{host_name}' in self._operation['searched_patterns']['success_search']:
            self._operation['searched_patterns']['success_search'] = origin_searched_patterns.format(
                host_name=operation_info['host_name'])
        operation_info['status'] = self.get_log_info(file_path, self._operation['searched_patterns']['success_search'], is_datetime=False)
        self._operation['searched_patterns']['success_search'] = origin_searched_patterns
        return operation_info['status']

    def get_log_info(self, file_path, requested_info='start_time', is_datetime=True):
        '''
        using 'awk' as it problematic to get timestamp from log
        requested_time should be:
         - start_time >> 'head -1'
         - end_time >> 'tail -1'
         - success_search >> a specif string on log file for a success status
        '''
        LOG_ROWS_AMOUNT = 30
        if requested_info == 'start_time':
            cmd_info = 'head -{}'.format(LOG_ROWS_AMOUNT)
        elif requested_info == 'end_time':
            cmd_info = 'tail -{}'.format(LOG_ROWS_AMOUNT)
        else:
            cmd_info = requested_info

        if os.path.splitext(file_path)[1] == ".gz":
            cmd = "sudo zcat {} | {} | awk '{{print $1, $2}}' | cut -d , -f 1".format(file_path, cmd_info)
        elif os.path.splitext(file_path)[1] == ".bzip2":
            cmd = "sudo bzcat {} | {} | awk '{{print $1, $2}}' | cut -d , -f 1".format(file_path, cmd_info)
        else:
            cmd = "sudo {} {} | awk '{{print $1, $2}}' | cut -d , -f 1".format(cmd_info, file_path)
        log_info_out = list(gs.get_host_executor_factory().execute_cmd_by_roles(
            roles=[self._objective_role], cmd=cmd, timeout=10).values())[0]
        log_info_lines = []
        for line in log_info_out["out"].splitlines():
            stripped_line = line.strip()
            if stripped_line:
                log_info_lines.append(str(stripped_line))
        log_info = None
        if log_info_lines:
            log_info = log_info_lines[0]
        if len(log_info_lines) > 1 and requested_info in ['start_time', 'end_time']:
            log_info_lines = reversed(log_info_lines) if requested_info == 'end_time' else log_info_lines
            return self._get_last_datetime_from_out_list(log_info_lines)
        if is_datetime and log_info:
            try:
                if "." in log_info:
                    log_info = log_info.split(".")[0]
                datetime.datetime.strptime(log_info, self.TIME_FORMAT)
                return log_info
            except ValueError:
                return ''
        else:
            return 'Passed' if log_info else 'Failed'

    def is_operation_search_found(self, log_path):
        cmd = self._command_builder('operation_search', log_path)
        out, full_output = self.get_command_result(cmd)
        return out

    def _get_last_datetime_from_out_list(self, log_info_list):
        for log_info in log_info_list:
            try:
                if "." in log_info:
                    log_info = log_info.split(".")[0]
                datetime.datetime.strptime(log_info, self.TIME_FORMAT)
                return log_info
            except ValueError:
                continue
        return ''
