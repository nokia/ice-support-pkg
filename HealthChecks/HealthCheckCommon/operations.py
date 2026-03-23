from __future__ import absolute_import

import abc
import sys
import threading
import tools.user_params
from HealthCheckCommon.file_utils import FileUtils
from HealthCheckCommon.secret_filter import SecretFilter
from HealthCheckCommon.system_utils import SystemUtils
from tools.global_enums import *
import tools.sys_parameters as gs
from tools.python_utils import PythonUtils
from tools.global_enums import Objectives
from tools.Exceptions import *
import json
import HealthCheckCommon.PreviousResults as PreviousResults
from HealthCheckCommon.parallel_runner import ParallelRunner
from HealthCheckCommon.printer import dataPrinter, StructedPrinter
from tools.global_logging import log_and_print, log
from six.moves import filter
from six.moves import range


class Operator(object):
    TIMEOUT_EXIT_CODE = 124
    BUSYBOX_DOCKER_TIMEOUT_EXIT_CODE = 137
    TIMEOUT_KILL_EXIT_CODE = 137
    TIMEOUT_BEFORE_KILL = 60

    WARNING_PATTERNS = [
        r"Warning: your password will expire in.*$"
    ]

    def __init__(self, host_executor):
        self._host_executor = host_executor
        self.file_utils = FileUtils(self)
        self.system_utils = SystemUtils(self)

    def get_host_ip(self):
        return self._host_executor.ip

    def get_host_name(self):
        return self._host_executor.host_name

    def run_cmd(self, cmd, timeout=20, hosts_cached_pool=None,
                get_not_ascii=False, add_bash_timeout=False, trim_warnings = True):
        bash_timeout = None
        self.assert_add_bash_timeout(cmd, add_bash_timeout)
        if add_bash_timeout:
            bash_timeout = timeout
            timeout = timeout + self.TIMEOUT_BEFORE_KILL + 1
            cmd = self._add_bash_timeout(cmd, bash_timeout)

        if hosts_cached_pool is not None:
            return self._run_cmd_use_cached(cmd, hosts_cached_pool, timeout,
                                            get_not_ascii, add_bash_timeout)

        else:
            self._add_cmd_to_log(cmd)
            return_code, out, err = self._host_executor.execute_cmd(cmd, timeout, get_not_ascii=get_not_ascii)

            if tools.user_params.debug_validation_flag:
                self._collect_cmd_info(cmd, out, err)

            if add_bash_timeout:
                self.verify_exit_code_not_from_bash_timeout(return_code, cmd, bash_timeout)

            if trim_warnings and out:
                out = self.trim_warnings(out)

            return return_code, out, err


    @staticmethod
    def trim_warnings(out):
        try:
            lines = out.splitlines(keepends=True)
        except TypeError:
            lines = out.splitlines(True)

        def fullmatch(pattern, string, flags=0):
            return re.match(r"(?:%s)\Z" % pattern, string, flags)

        if hasattr(re, "fullmatch"):
            match_func = re.fullmatch
        else:
            match_func = fullmatch

        while lines:
            last_line = lines[-1]
            matched = False

            for pattern in Operator.WARNING_PATTERNS:
                if match_func(pattern, last_line.rstrip("\r\n"), flags=re.IGNORECASE):
                    lines.pop()
                    matched = True
                    break

            if not matched:
                break

        return "".join(lines)

    def run_and_get_the_nth_field(self, cmd, n, separator=None, timeout=30,
                                  add_bash_timeout=False):
        out = self.get_output_from_run_cmd(cmd, timeout, add_bash_timeout=add_bash_timeout)
        out = PythonUtils.get_the_n_th_field(out, n, separator)
        return out

    def get_output_from_run_cmd(self, cmd, timeout=30, message='', hosts_cached_pool=None, get_not_ascii=False,
                                add_bash_timeout=False, trim_warnings = True):
        base_msg = 'Un-Expected system output (details in the .json file)'
        if message:
            final_message  = '{} - {}'.format(base_msg, message)
        else:
            final_message = base_msg

        return_code, out, err = self.run_cmd(cmd, timeout, hosts_cached_pool,
                                             get_not_ascii, add_bash_timeout, trim_warnings)
        if return_code == 0:
            return out
        else:
            self._set_cmd_info(cmd, timeout, return_code, out, err)
            raise UnExpectedSystemOutput(ip=self._host_executor.ip, cmd=cmd, output='[command output:\n{}\ncommand error:\n{}]'.
                                         format(out, err), message=final_message )

    def get_int_output_from_run_cmd(self, cmd, timeout=30,
                                    hosts_cached_pool=None, add_bash_timeout=False):
        out = self.get_output_from_run_cmd(cmd, timeout, hosts_cached_pool,
                                           add_bash_timeout=add_bash_timeout)
        try:
            return int(out)
        except ValueError:
            self._set_cmd_info(cmd, timeout, 1, out, "")
            raise UnExpectedSystemOutput(ip=self._host_executor.ip,
                                         cmd=cmd,
                                         output="expected int found '{}'".format(out))

    def run_cmd_return_is_successful(self, cmd, timeout=30,
                                     add_bash_timeout=False):
        return_code, out, err = self.run_cmd(cmd, timeout,
                                             add_bash_timeout=add_bash_timeout)

        if return_code == 0:
            return True
        else:
            pass
            # self._set_cmd_info(cmd, timeout, return_code, out, err)
        return False

    def run_cmd_return_is_successful_by_err_message(self, cmd, timeout=30, expected_err_msg_list=None,
                                                    add_bash_timeout=False):
        return_code, out, err = self.run_cmd(cmd, timeout, add_bash_timeout=add_bash_timeout)

        if return_code == 0:
            return True
        elif expected_err_msg_list:
            for expected_err in expected_err_msg_list:
                if expected_err in err:
                    return False
        raise UnExpectedSystemOutput(ip=self._host_executor.ip, cmd=cmd, output=out + err)

    def get_dict_from_file(self, path, file_format="json"):
        file_content = self.file_utils.read_file(path)
        if not file_content:
            error = "The file: {} is empty\n".format(path)
            raise UnExpectedSystemOutput(self.get_host_name(), "", error)
        return PythonUtils.get_dict_from_string(file_content, file_format)

    def _collect_cmd_info(self, cmd, out, err):
        pass

    def _add_cmd_to_log(self, cmd):
        pass

    def _set_cmd_info(self, cmd, timeout, return_code, out, err):
        pass

    def _run_cmd_use_cached(self, cmd, cached_pool, timeout=20,
                            get_not_ascii=False, add_bash_timeout=False):
        hostname = self.get_host_name()

        if cached_pool.get(hostname, {}).get(cmd):
            return cached_pool[hostname][cmd]

        cached_pool[hostname] = cached_pool.get(hostname, {})
        res = self.run_cmd(cmd, timeout, hosts_cached_pool=None,
                           get_not_ascii=get_not_ascii, add_bash_timeout=add_bash_timeout)

        if sys.getsizeof(res) > 1024 ** 4:
            raise UnExpectedSystemOutputSize(self.get_host_ip(), cmd, sys.getsizeof(res), 1024 ** 4)

        cached_pool[hostname][cmd] = res

        return res

    def _add_bash_timeout(self, cmd, timeout):
        assert ";" not in cmd, "If you need to add bash timeout to a nested command, please do it explicit." \
                               "you can add the timeout before the long command or to run: " \
                               "'[sudo] timeout <timeout> bash -c '<command>'," \
                               "Note that you need to verify the exit code by verify_exit_code_not_from_bash_timeout" \
                               "method."
        prefix = ""
        if cmd.startswith("sudo "):
            cmd = cmd[5:]
            prefix = "sudo "
        if not self._host_executor.is_local or gs.is_docker_support_standard_timeout():
            return "{}timeout --kill-after={} {} {}".format(prefix, self.TIMEOUT_BEFORE_KILL, timeout, cmd)
        else:
            return "{}timeout -s KILL {} {}".format(prefix, timeout, cmd)
            # Usage: timeout [-s SIG] SECS PROG ARGS
            # Runs PROG. Sends SIG to it if it is not gone in SECS seconds.
            # Default SIG: TERM.

    def verify_exit_code_not_from_bash_timeout(self, exit_code, cmd, timeout):
        if exit_code == self.TIMEOUT_EXIT_CODE or exit_code == self.TIMEOUT_KILL_EXIT_CODE:
            raise UnExpectedSystemTimeOut(cmd=cmd,
                                          ip=self.get_host_ip(),
                                          timeout=timeout, exited_from="bash timeout command")

        if self._host_executor.is_local and not gs.is_docker_support_standard_timeout() \
                and exit_code == self.BUSYBOX_DOCKER_TIMEOUT_EXIT_CODE:
            raise UnExpectedSystemTimeOut(cmd=cmd,
                                          ip=self.get_host_ip(),
                                          timeout=timeout,
                                          exited_from="busybox (ice docker) bash killed sig, "
                                                      "probably by timeout command")

    def assert_add_bash_timeout(self, cmd, add_bash_timeout):
        if ';' in cmd:
            return
        cmd_list = ["du", "docker exec", "podman exec"]
        for item in cmd_list:
            if bool(re.compile(r'\b{}\b'.format(item)).search(cmd)):
                assert add_bash_timeout, \
                    "cmd: {}\nExpected add_bash_timeout enabled on command that contains: {}".format(cmd, item)


# ----------------------------------------------------------------------------------------------------------

class FlowsOperator(Operator):
    '''
    run operation on some system component. can be InfoCheck, Validation and (coming soon) system repairer
    '''
    objective_hosts = []  # where this validation expected to run, must be field

    def __init__(self, host_executor):
        super(FlowsOperator, self).__init__(host_executor)
        self.set_initial_values()
        self.set_document()
        self._enforce_have_document()
        assert len(
            self.__class__.objective_hosts) > 0, "please define the objective of this validation (class method) " \
                                                 + str(self.__class__)

    def _enforce_have_document(self):  # overwrite this if you dont want force document on operator
        assert self._title != "---", "class" + str(self.__class__)
        assert self._failed_msg != "---", "class" + str(self.__class__)
        assert self._unique_operation_name != "---", "class" + str(self.__class__)

    def set_initial_values(self):
        self._severity = None
        self._unique_operation_name = "---"  # do not change this after the first version
        # do not change this for different test of the same thing on different versions
        # should be the same for all validations that is the same but for different system version
        # describe what is tested (as accurate as possible -please use the word all or any if needed)
        self._title = "---"  # describe what is tested (as accurate as possible)
        self._failed_msg = "---"  # msg if not successful
        self._implication_tags = []
        self._details = ""
        self._msg = ""  # additional out put to the user
        self._cmd_info = ""
        self._bash_cmd_lines = []
        self._validation_log = []
        self._is_clean_cmd_info = False
        self.any_passed_data_collector = False
        self.data_collectors_exceptions = []

    def set_document(self):
        # init the documentation fields:
        # for example:
        # self._title = "description of this system test"
        # self._failed_msg = "failed msg"
        assert False, "please implement set_document at " + str(self.__class__)

    def get_unique_name(self):
        return self._unique_operation_name

    def should_add_base_hosts(self):
        return False

    def get_documentation_link(self):
        # documentation link name in case operation is complicated.
        # before setting a link name you have to add the unique operation name as key and
        # documentation link as a value to name_to_url dict in tools/name_to_url.json

        if self._unique_operation_name in tools.user_params.name_to_url_dict:
            return tools.user_params.name_to_url_dict.get(self._unique_operation_name)
        return None

    def is_clean_cmd_info(self):
        return self._is_clean_cmd_info

    def is_prerequisite_fulfilled(self):
        return True

    def get_severity(self):
        return self._severity

    def get_implication_tags(self):
        return self._implication_tags

    def get_roles_for_current_deployment(self, deployment_type=None):
        if deployment_type is None:
            current_deployment_type = gs.get_deployment_type()
        else:
            current_deployment_type = deployment_type

        if type(self.objective_hosts) is dict:

            roles_for_current_deployment_type = self.objective_hosts.get(current_deployment_type)
        else:
            roles_for_current_deployment_type = self.objective_hosts
        return roles_for_current_deployment_type

    @staticmethod
    def filter_all_hosts(string):
        if string in [Objectives.ALL_HOSTS, Objectives.ALL_NODES]:
            return False
        return True

    def get_host_roles(self):
        return list(filter(self.filter_all_hosts, self._host_executor.roles))

    def title_description(self):
        return self._title

    def get_bash_cmd_lines(self):
        if self.is_clean_cmd_info():
            return []
        return self._bash_cmd_lines

    def get_validation_log(self):
        if self._cmd_info != "":

            if self.is_clean_cmd_info() and not tools.user_params.debug_validation_flag:
                self._cmd_info = "** cmd info is not available here for this validation **"
            else:
                self._cmd_info = "\n" + self._cmd_info
            self._validation_log += ["cmds that failed to run:{}".format(self._cmd_info)]

        return self._validation_log

    def add_to_validation_log(self, log_):
        self._validation_log.append(log_)

    def get_dependency_flow_result(self, command_name):
        return PreviousResults.get_validation_result_to_specific_host(command_name, self.get_host_name())

    def run_data_collector_on_specific_hosts(self, data_collector_class, hosts_names_list, **kwargs):
        assert not data_collector_class.objective_hosts, "Do not provide objective hosts if run on specific hosts"
        data_collector_class.objective_hosts = ["dummy host"]
        data_collector_object = data_collector_class(
            source_objective_roles_list=self.get_roles_for_current_deployment())

        return self._run_data_collector_on_hosts(data_collector_class, data_collector_object, hosts_names_list,
                                                 **kwargs)

    def run_data_collector(self, data_collector_class, **kwargs):
        data_collector_object = data_collector_class(
            source_objective_roles_list=self.get_roles_for_current_deployment())

        return self._run_data_collector_on_hosts(data_collector_class, data_collector_object, **kwargs)

    def _run_data_collector_on_hosts(self, data_collector_class, data_collector_object, hosts_names_list=None,
                                     **kwargs):
        if self.is_clean_cmd_info():
            data_collector_object._is_clean_cmd_info = True
        data_collected = data_collector_object.collect_all_data(hosts_names_list=hosts_names_list, **kwargs)
        collector_exceptions = data_collector_object.get_collector_exceptions()
        data_collector_name = data_collector_class.__name__
        self._bash_cmd_lines.extend(data_collector_object.get_bash_cmd_lines())
        collector_log = {data_collector_name: data_collector_object.get_collector_validation_log()}
        is_collector_failed_on_all_hosts = data_collector_object.is_collector_failed_on_all_hosts()
        # if we want to take off this from the validation log we can add this only
        # if data_collector_object.get_collector_validation_log()
        if not is_collector_failed_on_all_hosts:
            self.any_passed_data_collector = True
        if collector_exceptions:
            self.data_collectors_exceptions.append({data_collector_name: collector_exceptions})
            collector_log.setdefault(data_collector_name, []).append({"DataCollector Exceptions": collector_exceptions})
        if len(collector_log[data_collector_name]):
            self._validation_log.append(collector_log)
        if is_collector_failed_on_all_hosts and data_collector_object.handle_error:
            raise UnExpectedSystemOutput(
                self.get_host_ip(), cmd="",
                output="DataCollector Un-Expected output, Please check the validation log for details",
                message="DataCollector Un-Expected output")
        return data_collected

    def raise_if_no_collector_passed(self):
        if not self.any_passed_data_collector:
            raise UnExpectedSystemOutput(
                "", "", output="DataCollector Un-Expected output, Please check the validation log for details",
                message="DataCollector Un-Expected output - No collector passed")


    def get_first_value_from_data_collector(self, data_collector_class, **kwargs):
        data_collector_dict = self.run_data_collector(data_collector_class, **kwargs)
        if not len(data_collector_dict):
            raise NoSuitableHostWasFoundForRoles(data_collector_class.objective_hosts)
        return list(data_collector_dict.values())[0]

    def run_command_and_grep(self, cmd, pattern_to_grep, timeout=30):
        result_lines = []
        out = self.get_output_from_run_cmd(cmd, timeout)
        out_lines = out.splitlines()
        for line in out_lines:
            if PythonUtils.is_string_contains_pattern(line, pattern_to_grep):
                result_lines.append(line)
        return result_lines

    def get_dict_from_command_output(self, cmd, out_format, timeout=60, header_line=0, custom_delimiter=None,
                                     custom_header=None):
        out = self.get_output_from_run_cmd(cmd, timeout=timeout)
        return PythonUtils.get_dict_from_string(
            out, out_format, header_line=header_line, custom_delimiter=custom_delimiter, custom_header=custom_header)

    def get_dict_from_run_cmd(self, cmd, out_format, timeout=60, header_line=0, custom_delimiter=None,
                              custom_header=None):
        return_code, out, err = self.run_cmd(cmd, timeout=timeout)
        out_dict = PythonUtils.get_dict_from_string(out, out_format, header_line=header_line,
                                                    custom_delimiter=custom_delimiter, custom_header=custom_header)
        return return_code, out_dict, err

    def _collect_cmd_info(self, cmd, out, err, max_line=50, max_chars_in_line=1000, host_name=None):
        if host_name:
            self._validation_log.append("Host name: '{}'".format(host_name))
        self._validation_log.append("Running command: '{}'".format(cmd))
        out_lines = out.splitlines()
        if len(out_lines) > max_line:
            num_of_loops = max_line
            self._validation_log.append("Command output is too long. "
                                        "Printing out first {} rows - "
                                        "run the command manually to get full output".format(max_line))
        else:
            num_of_loops = len(out_lines)

        if num_of_loops == 1:
            self._validation_log.append("Command output: {}".format(out))
        else:
            self._validation_log.append("Command output:")
            for i in range(0, num_of_loops):
                if len(out_lines[i]) < max_chars_in_line:
                    self._validation_log.append("{}.".format(out_lines[i]))
                else:
                    self._validation_log.append("Command output is too long - will print part of the output:")
                    self._validation_log.append("{}.".format(out_lines[i][0:max_chars_in_line]))
        if err:
            self._validation_log.append("Command error: {}".format(err))
        self._validation_log.append("================================================")

    def run_cmd_by_roles(self, cmd, roles, timeout=30, list_output=False, add_bash_timeout=False):
        bash_timeout = None

        if add_bash_timeout:
            bash_timeout = timeout
            timeout = timeout + self.TIMEOUT_BEFORE_KILL + 1
            cmd = self._add_bash_timeout(cmd, bash_timeout)

        self._bash_cmd_lines.append("roles: {} cmd: '{}' ".format(roles, cmd))
        result = gs.get_host_executor_factory().execute_cmd_by_roles(roles, cmd, timeout)
        for host in result:
            self._collect_cmd_info(cmd=cmd, out=result[host]["out"], err=result[host]["err"], host_name=host)
        if add_bash_timeout:
            for item in list(result.values()):
                self.verify_exit_code_not_from_bash_timeout(item['exit_code'], cmd, bash_timeout)

        if list_output:
            return list(result.values())
        else:
            return result

    def get_output_from_run_cmd_by_roles(self, cmd, roles, timeout=30, list_output=False, add_bash_timeout=False):
        result = self.run_cmd_by_roles(cmd, roles, timeout, list_output, add_bash_timeout)
        result_as_list = result
        if not list_output:
            result_as_list = list(result.values())
        for item in result_as_list:
            if item['exit_code'] != 0:
                message = "Un-Expected output"
                if not item['out']:
                    message += ", no output from cmd\n{}".format(item['err'] or "")
                raise UnExpectedSystemOutput(ip=self._host_executor.ip, cmd=cmd, output=item['out'] + item['err'],
                                             message=message)
        return result

    def _debug_pipes(self, cmd, timeout=30):
        cmd_list = PythonUtils.brack_cmd_pipes(cmd)
        to_return = {}
        for cmd in cmd_list:
            return_code, out, err = self._host_executor.execute_cmd(cmd, timeout)
            to_return[cmd] = (return_code, out, err)
            if return_code != 0:
                break
        return to_return

    def _set_cmd_info(self, cmd, timeout, return_code, out, err):

        pipe_debug = ""
        if "|" in cmd:
            pipe_debug = self._debug_pipes(cmd, timeout)

        msg = {}
        msg['cmd'] = cmd
        msg['out'] = out
        msg['err'] = err
        msg['return_code'] = return_code
        if pipe_debug != "":
            msg['debug'] = pipe_debug

        self._cmd_info = str(msg)

    def parse_to_int(self, parm_to_parse, cmd="", out="", timeout=30):
        try:
            return int(parm_to_parse)
        except ValueError:
            self._set_cmd_info(cmd, timeout=timeout, return_code='-', out=out, err='-')
            raise UnExpectedSystemOutput(ip=self._host_executor.ip,
                                         cmd=cmd,
                                         output="expected int found '{}'".format(parm_to_parse))

    def is_run_cmd_successful_on_host_role(self, cmd, host_role_list, expected_err_msg_list):
        out = gs.get_host_executor_factory().execute_cmd_by_roles(host_role_list, cmd, 10)
        host_name = list(out.keys())[0]
        if out[host_name]['exit_code'] == 0:
            return True
        elif expected_err_msg_list:
            for err_msg in expected_err_msg_list:
                if err_msg in out[host_name]['err']:
                    return False
        raise UnExpectedSystemOutput(ip=self._host_executor.ip, cmd=cmd,
                                     output=out[host_name]['out'] + out[host_name]['err'])

        # needs to be deprecated

    def describe_when_validation_fails(self):
        if self._msg != "":
            self._msg = "\n" + self._msg

        if self._details != "":
            self._details = "\n\n" + self._details

        implication_tags_str = ""
        if self._implication_tags:
            implication_tags_str = "\n\nHashtags:\n" + "\n".join(self._implication_tags) + "\n"

        to_return = self._failed_msg + self._msg + self._details + implication_tags_str

        return to_return

    def _add_cmd_to_log(self, cmd):
        self._bash_cmd_lines.append('{}'.format(cmd))


# ----------------------------------------------------------------------------------------------------------

class DataCollector(FlowsOperator):
    objective_hosts = []
    handle_error = True
    threadLock = threading.RLock()

    def _enforce_have_document(self):
        pass

    def set_document(self):
        pass

    def __init__(self, host_executor=None, source_objective_roles_list=None):
        FlowsOperator.__init__(self, host_executor)
        self._collector_exceptions = dict()
        self._is_collector_failed_on_all_hosts = None
        if source_objective_roles_list:
            if type(source_objective_roles_list) == str:
                source_objective_roles_list = [source_objective_roles_list]
            self.is_many_to_one = self.is_many_to_one_relationship(source_objective_roles_list)

    def is_many_to_one_relationship(self, source_objective_roles_list):
        for source_objective_role in source_objective_roles_list:
            if source_objective_role not in Objectives.get_all_single_types():
                current_roles = self.get_roles_for_current_deployment()
                assert isinstance(current_roles, list), "current_roles is '{}' and expected to be list as '[{}]'". \
                    format(current_roles, current_roles)
                assert set(current_roles).issubset(set(
                    Objectives.get_all_single_types())), ("Data collector does not support many to many relationships.\n"
                                                          "Validation objectives: {}\n"
                                                          "Data collector objectives: {}".format(source_objective_role, current_roles))
                return True
        return False

    def collect_data(self, **kwargs):
        raise NotImplementedError

    def get_collector_exceptions(self):
        return self._collector_exceptions

    def get_collector_validation_log(self):
        return self._validation_log if type(self._validation_log) is list else list(self._validation_log)

    def is_collector_failed_on_all_hosts(self):
        return self._is_collector_failed_on_all_hosts

    def collect_all_data(self, hosts_names_list=None, **kwargs):
        host_executors = self._get_host_executors(hosts_names_list)
        active_host_executors = self._get_active_host_executors(hosts_names_list)
        if hosts_names_list:
            active_host_executors = dict([host for host in list(active_host_executors.items()) if host[0] in hosts_names_list])
        for host in list(set(host_executors.keys()) - set(active_host_executors.keys())):
            self._collector_exceptions[host] = str(UnExpectedSystemOutput(ip=host, cmd="", output="{} not connected".format(host)))
        inner_data_collectors = []
        mydataPrinter = dataPrinter()
        for host_name in active_host_executors:
            inner_data_collector = self.__class__(host_executor=active_host_executors[host_name])
            if self.is_clean_cmd_info():
                inner_data_collector._is_clean_cmd_info = True
            inner_data_collectors.append(inner_data_collector)
        ParallelRunner.run_data_collector_on_all_host(inner_data_collectors, mydataPrinter, self.is_many_to_one, **kwargs)
        self._collector_exceptions.update(mydataPrinter.get_exceptions())
        self._is_collector_failed_on_all_hosts = self._collector_exceptions and set(host_executors.keys()) == set(self._collector_exceptions.keys())
        if mydataPrinter.get_validation_log():
            self._validation_log.append(mydataPrinter.get_validation_log())
        self._bash_cmd_lines.extend(mydataPrinter.get_printer_bash_cmd_lines())

        data = mydataPrinter.get_data()
        return data

    def _get_host_executors(self, hosts_names_list=None):
        if hosts_names_list:
            host_executors = gs.get_host_executor_factory().get_host_executors_by_ip_or_hostname(hosts_names_list)
        else:
            host_executors = gs.get_host_executor_factory().get_host_executors_by_roles(
                roles=self.get_roles_for_current_deployment())
        return host_executors

    def _get_active_host_executors(self, hosts_names_list=None):
        host_executors = self._get_host_executors(hosts_names_list)
        return self._filter_active_host_executors(host_executors)

    def _filter_active_host_executors(self, host_executors):
        return dict([host_item for host_item in list(host_executors.items()) if host_item[1].is_connected])


# ----------------------------------------------------------------------------------------------------------


# -----------------------------------------------------------------------------------------------------------------------
class SystemOperator(FlowsOperator):

    def __init__(self, ip):
        self._is_action_type_active = True
        FlowsOperator.__init__(self, ip)
        self._is_passed = None
        assert self._run_in_parallel is not None  # make sure no one forget to fill this parameter
        assert self._prerequisite_unique_operation_name is not None, \
            "no prerequisite set. if no prerequisite expected put "" .\noperation {}".format(self.get_unique_name())

    def set_initial_values(self):
        FlowsOperator.set_initial_values(self)
        self._run_in_parallel = None
        self._severity = Severity.ERROR
        self._failed_msg = ""
        self._printable_title = None

        self._prerequisite_unique_operation_name = None  # if no prerequisite put ""
        self._is_prerequisite_on_multiple_hosts = False
        self._is_prerequisite_pass_if_any_passed = True
        self._flg_run_only_if_prerequisite_failed = False

        # return prerequisite check pass iif:
        # 1) it passed on the same host as this one OR
        # 2) it passed on UC/ONE_MANAGER/HYP/etc (see Objectives.get_all_single_types() - single points of run) OR
        # 3) for cases this operation runs from UC/ONE_MANAGER/HYP/etc - if any prerequisite seceded
        # 4) #3 - can change from 'any' to 'all' by setting self._is_prerequisite_for_all_hosts to True
        # (default is False)

        # adding prerequisite for failed operation can be chosen by setting
        # self._flg_run_only_if_prerequisite_failed =True

        # if this an operation depend on prerequisite that run on UC/Master/or other single role type - test on it
        # if this an operation depend on prerequisite that run on all hosts  - depend on "this" host
        # if this an operation run on single host depend on prerequisite that run on all hosts  - you can set
        # _is_prerequisite_for_all_hosts =True if you want return value of True on ALL hosts. default is false

    def _get_is_passed(self):
        return self._is_passed

    def _set_passed(self, set_passed):
        self._is_passed = set_passed

    def _get_printable_title(self):
        return self._printable_title

    def log_cmd(self, str_to_print):
        if not self.is_clean_cmd_info():
            str_to_print = SecretFilter.filter_string_array(str_to_print)
        if tools.user_params.debug:
            log_and_print(str_to_print)
        else:
            log(str_to_print)

    def safe_run_cmd(self, cmd, timeout=30):
        # self.get_output_from_run_cmd(cmd, timeout)
        return_code, out, err = self.run_cmd(cmd, timeout)
        if return_code != 0:
            message = 'Un-Expected output, cmd:{} ret:{} out:{} err:{}'.format(cmd, return_code, out, err)
            exception = UnExpectedSystemOutput(ip=self._host_executor.ip, cmd=cmd, output=out + err, message=message)
            log_and_print("******* unexpected fail on host {} operation {} {}".format(
                self.get_host_ip(), self.get_unique_name(), str(exception)))
            raise exception

    def run_cmd(self, cmd, timeout=30, hosts_cached_pool=None,
                get_not_ascii=False, add_bash_timeout=False, trim_warnings = True):

        cmd_to_print = "** cmd info is not available here for this validation **" if self.is_clean_cmd_info() else cmd

        before_running_log = "{}: starting running {} on {} ".format(self.get_unique_name(), cmd_to_print, self.get_host_ip())
        self.log_cmd(before_running_log)

        return_code, out, err = FlowsOperator.run_cmd(self, cmd, timeout,
                                                      hosts_cached_pool, get_not_ascii, add_bash_timeout)
        out_to_print = out
        err_to_print = err
        if self.is_clean_cmd_info():
            out = "** out info is not available here for this validation **"
            err = "** err info is not available here for this validation **"

        str_to_print = "run_cmd details:\n" \
                       + "+----------------------------------------------------------\n" \
                       + "| {}: on host {} ({}) \n".format(self.get_unique_name(), self.get_host_ip(),
                                                           self.get_host_name()) \
                       + "| runs:{} \n".format(cmd_to_print) \
                       + "| return value {} \n".format(return_code) \
                       + "| out: {} \n".format(out_to_print) \
                       + "| err: {}\n".format(err_to_print) \
                       + "+----------------------------------------------------------\n"

        self.log_cmd(str_to_print)
        return return_code, out, err

    def run_sudo_cmd(self, cmd, timeout=30):
        return_code, out, err = self.run_cmd("sudo {}".format(cmd), timeout)
        if 'permission denied' in err.lower():
            return_code, out, err = self.run_cmd('sudo su -c "{}"'.format(cmd), timeout)
        return return_code, out, err

    @abc.abstractmethod
    def run_system_operation(self):
        '''
        do the operation
        :return:
        the True if and only if went ok
        '''
        assert False

    # todo!!! remove this
    def get_blocking_tags(self):
        return []
