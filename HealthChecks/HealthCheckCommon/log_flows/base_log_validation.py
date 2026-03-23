from __future__ import absolute_import
from HealthCheckCommon.validator import Validator
from tools.global_enums import *
import os
from tools.date_and_time_utils import parse
from datetime import timedelta, datetime
from tools.python_utils import PythonUtils


class issues_in_log_file_validator(Validator):
    objective_hosts = [Objectives.NA]

    def __init__(self, ip, log_file_path, patterns, component, id, severity, issue_msg,
                 relevant_data_time_start=None, relevant_data_time_end=None):
        Validator.__init__(self, ip)
        self._component = component
        self._log_file_path = log_file_path
        self._patterns = patterns
        self._id = id
        self._severity = severity
        self._issue_msg = issue_msg

        self._relevant_data_time_start = relevant_data_time_start
        self._relevant_data_time_end = relevant_data_time_end

        default_time_start, default_time_end = self.get_default_time_range()

        if self._relevant_data_time_start is None:
            self._relevant_data_time_start = default_time_start

        if self._relevant_data_time_end is None:
            self._relevant_data_time_end = default_time_end

        file_name = os.path.basename(self._log_file_path)
        self._title = "test if the known issue {} in {}".format(self._id, file_name)
        self._unique_operation_name = "known_log_" + self._component + self._id
        self._failed_msg = self._issue_msg + " is found in the log file"

        assert severity in Severity.AVAILABLE_SEVERITIES
        self._severity = severity

    def set_document(self):
        # - implement in init
        self._title = "tmp"
        self._unique_operation_name = "tmp"
        self._failed_msg = "tmp"
        self._severity = Severity.ERROR

    def _get_grep_cmd(self, pattern):
        return "sudo grep -n -E "'"' + pattern + '"'" " + self._log_file_path + " | grep -v 'grep'"

    def get_default_time_range(self):
        # today = datetime.date.today()
        now = datetime.now()
        # yesterday = today - datetime.timedelta(days=1)
        two_weeks_ago = now - timedelta(days=14)
        tomorrow = now + timedelta(days=1)
        return two_weeks_ago, tomorrow

    def _is_any_pattern_found(self):
        flg_any_pattern_found = False

        for pattern in self._patterns:
            # if log_cmd_type == "file":
            #    cmd_grepted = "grep -n -E '" + pattern + "' " + log_cmd
            # elif log_cmd_type == "cmd":
            #    cmd_grepted = log_cmd + " | grep -n -E '" + pattern + "'"
            # else:
            #    assert False, "unknown log_cmd_type " + cmd_grepted

            cmd = self._get_grep_cmd(pattern)
            # make sure file is reachable
            self.get_output_from_run_cmd("sudo ls " + self._log_file_path)

            return_code, out, err = self.run_cmd(cmd, timeout=90, add_bash_timeout=True)
            if return_code == 2:  # if not found pattern
                continue

            lines = out.split('\n')
            list_of_dates = []
            line_numbers = []
            flg_pattern_found = False
            for line in lines:
                if line == "":
                    continue

                tmp_lines = line.split(":")
                line_num = int(tmp_lines[0])

                line = line.replace(tmp_lines[0] + ":", "")

                match, date_format, short_date_format = PythonUtils.find_dates(line)

                my_datatime = parse(match)

                if my_datatime > self._relevant_data_time_start or my_datatime < self._relevant_data_time_end:
                    flg_pattern_found = True
                    list_of_dates.append(my_datatime)
                    line_numbers.append(line_num)

            if flg_pattern_found:
                flg_any_pattern_found = True
                full_error_msg = "\n\nat #lines {} @{} found the pattern '{}'".format(line_numbers, self._log_file_path,
                                                                                      pattern)
                self._failed_msg = self._failed_msg + " " + full_error_msg

        return flg_any_pattern_found

    def is_validation_passed(self):
        return not self._is_any_pattern_found()


class issues_in_cmd_log_validator(issues_in_log_file_validator):
    def __init__(self, ip, log_cmd, patterns, component, id, severity, issue_msg,
                 relevant_data_time_start=None, relevant_data_time_end=None):
        issues_in_log_file_validator.__init__(self,ip=ip, log_file_path=log_cmd,patterns= patterns,
                                              component= component,id= id,
                                              severity=severity, issue_msg=issue_msg,
                                              relevant_data_time_start=relevant_data_time_start,
                                              relevant_data_time_end=relevant_data_time_end)
        self._log_cmd = log_cmd


    def _get_grep_cmd(self, pattern, log_cmd):
        return "sudo " + self._log_cmd + " | grep -n -E '" + pattern + "'"+ " | grep -v 'grep'"
