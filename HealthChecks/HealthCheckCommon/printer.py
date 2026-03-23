from __future__ import absolute_import
from datetime import datetime
import threading
import six
from HealthCheckCommon.relevance_analyzer import RelevanceAnalyzer
import tools.user_params
from tools.global_enums import *
from HealthCheckCommon.secret_filter import SecretFilter

# -----------------------------------------------------------------------------------------------------------------------

class StructedPrinter:
    """used to save the out put in a structure that can be handled as a Json/Yaml"""
    encrypt_out = True

    def __init__(self):
        self._data = OrderedDict()

    def get_msg(self):
        return self._data

    def _format_list_of_datestime(self, list_time):
        # todo move to comperhancve python
        dt_strings = []
        for issue_time in list_time:
            dt_strings.append(self._time_formated(issue_time))
        return dt_strings

    def _time_formated(self, issue_time):
        """make sure all time is in formatted format"""
        dt_string = issue_time.strftime("%d/%m/%Y %H:%M:%S")
        return dt_string

    def _get_time_now(self):
        now = datetime.now()
        dt_string = self._time_formated(now)
        return dt_string

    # todo add host ip
    def print_found_error_in_log(self, unique_operation_name, title_description, severity, describe_msg, full_error_msg,
                                 line_numbers, starting_searching_date_time, issue_datetime, host):
        validation_data = {'pass': False, 'description_title': title_description,
                           'severity': severity, 'describe_msg': describe_msg, 'full_error_msg': full_error_msg,
                           "starting_searching_date_time": self._time_formated(starting_searching_date_time)}

        date_time_of_issue = self._format_list_of_datestime(issue_datetime)
        validation_data['issue_datetime'] = date_time_of_issue
        validation_data['line_numbers'] = line_numbers
        # validation_data['operation_name'] = unique_operation_name

        host_key = host
        if host_key not in self._data:
            self._data[host_key] = OrderedDict()

        self._data[host_key][unique_operation_name] = validation_data

    def print_system_info(self, unique_operation_name, title_description, host_ip, host_name, bash_cmd_lines,
                          validation_log, system_info, implication_tags, table_system_info, is_highlighted_info, run_time, in_maintenance,
                          documentation_link):
        self.print_result(unique_operation_name=unique_operation_name,
                          title_description=title_description,
                          host_ip=host_ip,
                          host_name=host_name,
                          bash_cmd_lines=bash_cmd_lines,
                          validation_log=validation_log,
                          is_passed="--",
                          severity=None,
                          describe_msg=None,
                          system_info=system_info,
                          implication_tags=implication_tags,
                          table_system_info=table_system_info,
                          is_highlighted_info=is_highlighted_info,
                          run_time=run_time,
                          in_maintenance=in_maintenance,
                          documentation_link=documentation_link)

    def limit_data_printed_len(self, data_printed):
        data_printed_len = 0
        LEN_THRESHOLD = 100000
        DATA_PRINTED_LIMITATION = 1000
        limited_data_printed = []
        if isinstance(data_printed, six.string_types):
            if len(data_printed) > LEN_THRESHOLD:
                return data_printed[:DATA_PRINTED_LIMITATION] + "\n....."
        if type(data_printed) is list:
            for item in data_printed:
                if data_printed_len < DATA_PRINTED_LIMITATION:
                    limited_data_printed.append(item)
                    data_printed_len += len(item)
                if data_printed_len > LEN_THRESHOLD:
                    limited_data_printed.append(".....")
                    return limited_data_printed
        return data_printed

    def print_result(self, unique_operation_name, title_description, host_ip, host_name, bash_cmd_lines, validation_log,
                     in_maintenance, run_time=None, is_passed=None, exception=None, severity=None, implication_tags=[],
                     describe_msg=None, system_info=None, documentation_link=None, blocking_tags=[],
                     table_system_info=None,  is_highlighted_info=None):

        # unsafe: bash cmd lines, systeminfo, exception, describe message, validation log
        # safe: uniq op name, title descr, host_<ip,name>, is_passed, severity, docu link, blocking tags,  runtime
        if StructedPrinter.encrypt_out:
            bash_cmd_lines = SecretFilter.filter_string_array(bash_cmd_lines)
            validation_log = SecretFilter.filter_string_array(validation_log)

        validation_data = {'host_ip': host_ip, 'bash_cmd_lines': self.limit_data_printed_len(bash_cmd_lines),
                           'validation_log': self.limit_data_printed_len(validation_log), 'description_title': title_description,
                           'time': self._get_time_now()}
        host_key = '{} - {}'.format(host_name, host_ip)

        if in_maintenance:
            host_key += " - in maintenance"

        if is_passed is None:
            validation_data['pass'] = Status.NA.value
        else:
            validation_data['pass'] = is_passed
        if documentation_link:
            validation_data['documentation_link'] = documentation_link
        if exception:
            validation_data['exception'] = exception
        if describe_msg:
            validation_data['describe_msg'] = describe_msg
        if system_info is not None:
            validation_data['system_info'] = self.limit_data_printed_len(system_info)
        if run_time:
            validation_data['run_time'] = run_time
        if blocking_tags is not None:
            validation_data['blocking_tags'] = blocking_tags
        if table_system_info:
            validation_data['table_system_info'] = table_system_info.to_dict()
        if is_highlighted_info is not None:
            validation_data['is_highlighted_info'] = is_highlighted_info
        validation_data = RelevanceAnalyzer.update_validation_data_with_relevant_to_domain_field(
            severity, implication_tags, validation_data)
        if severity and is_passed not in [True, '--']:
            validation_data['severity'] = str(severity)
        if host_key not in self._data:
            self._data[host_key] = OrderedDict()
        self._data[host_key][unique_operation_name] = validation_data

    def print_failed(self, unique_operation_name, title_description, severity, implication_tags, describe_msg, host_ip,
                     host_name, bash_cmd_lines, validation_log, run_time, documentation_link, blocking_tags,
                     in_maintenance):
        self.print_result(unique_operation_name, title_description, host_ip, host_name, bash_cmd_lines,
                          validation_log, is_passed=False, severity=severity, implication_tags=implication_tags,
                          describe_msg=describe_msg, run_time=run_time, documentation_link=documentation_link,
                          blocking_tags=blocking_tags, in_maintenance=in_maintenance)

    def print_ok(self, unique_operation_name, title_description, severity, host_ip, host_name, bash_cmd_lines, implication_tags,
                 validation_log, run_time, blocking_tags, in_maintenance):
        self.print_result(unique_operation_name, title_description, host_ip, host_name, bash_cmd_lines, validation_log,
                          severity=severity, implication_tags=implication_tags, run_time=run_time, is_passed=True,
                          blocking_tags=blocking_tags, in_maintenance=in_maintenance)

    def print_not_performed(self, unique_operation_name, title_description, severity, implication_tags, exception, describe_msg, host_ip, host_name,
                            bash_cmd_lines, validation_log, blocking_tags, in_maintenance,
                            documentation_link=None):
        self.print_result(unique_operation_name, title_description, host_ip, host_name, bash_cmd_lines,
                          validation_log, severity=severity, implication_tags=implication_tags, exception=exception, describe_msg=describe_msg, blocking_tags=blocking_tags,
                          documentation_link=documentation_link, in_maintenance=in_maintenance)

    def print_basic_problem(self, problem_name, unique_operation_name, title_description, severity, implication_tags, describe_msg, host_ip,
                            host_name, bash_cmd_lines, validation_log, exception, blocking_tags,
                            in_maintenance, documentation_link=None):
        self.print_result(unique_operation_name, title_description, host_ip, host_name, bash_cmd_lines,
                          validation_log, is_passed=problem_name, severity=severity, implication_tags=implication_tags, exception=exception, describe_msg=describe_msg,
                          blocking_tags=blocking_tags, documentation_link=documentation_link,
                          in_maintenance=in_maintenance)


#-----------------------------------------------------------------------------------------------------------------------
class dataPrinter():
    def __init__(self):
        self._data = OrderedDict()
        self._exception_dict = dict()
        self._validation_log =dict()
        self._bash_cmd_lines = []

    def add_data(self, host_name, data, validation_log="",bash_cmd_lines=[], exception=None):
        if validation_log:
            self._validation_log[host_name] = validation_log

        self._data[host_name] = data
        if exception:
            self._exception_dict[host_name] = exception
        if bash_cmd_lines:
            self._bash_cmd_lines.extend(["host: {} cmd: '{}'".format(host_name, cmd) for cmd in bash_cmd_lines])

    def get_data(self):
        return self._data

    def get_validation_log(self):
        return self._validation_log

    def get_printer_bash_cmd_lines(self):
        return self._bash_cmd_lines


    def get_exceptions(self):
        return self._exception_dict



