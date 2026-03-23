from __future__ import absolute_import
from HealthCheckCommon.validator import InformatorValidator
from tools.Info import *
from tools.python_utils import *


class UnifySystemParameterCheck(InformatorValidator):
    objective_hosts = [Objectives.UC, Objectives.ONE_MASTER]

    def __init__(self, ip):
        InformatorValidator.__init__(self, ip)  # calls set_initial_values and set_document
        self._flg_is_check_relevant = None
        self._parameter_host_dict = {}
        self._parameter_host_dict_str = None

    def _is_check_relevant(self, parameter_host_dict):
        return True

    def _process_parameter_from_command_output(self, out, err, exit_code, host_name):
        #  this function has to return the parameter as string
        raise NotImplementedError("abstract function _set_parameter_from_command_output was not implemented")

    def _set_command_to_execute_on_each_host(self):
        #  You have to return the command string to execute on each host to get the parameter
        raise NotImplementedError("abstract function _set_command_to_execute_on_each_host was not implemented")

    def _set_target_roles(self):
        #  You have to return the list of objective roles the parameter has to be unify
        raise NotImplementedError("abstract function _set_target_roles was not implemented")

    def _set_command_time_out(self):
        #  this function returns a default command time out. you can override.
        return 30

    def _user_set_info(self, is_check_relevant, parameter_host_dict):
        # if you want to set info to the user
        raise NotImplementedError
        # return None

    def _set_system_parameter_name(self):
        raise NotImplementedError("abstract method _set_system_parameter_name has to return the name of the checked parameter")

    def is_prerequisite_fulfilled(self):
        roles = self._set_target_roles()
        available_roles = GetInfo.get_system_available_roles()
        roles_intersection = PythonUtils.list_intersection(roles, available_roles)
        return len(roles_intersection) > 0

    def is_validation_passed(self):
        timeout = self._set_command_time_out()
        assert type(timeout) is int
        command = self._set_command_to_execute_on_each_host()
        assert type(command) is str
        roles = self._set_target_roles()
        assert type(roles) is list
        parameter_name = self._set_system_parameter_name()
        assert type(parameter_name) is str
        result_dict = self.run_cmd_by_roles(command, roles, timeout=timeout)
        for host_name in result_dict:
            out, err, exit_code = [
                result_dict[host_name].get('out'),
                result_dict[host_name].get('err'),
                result_dict[host_name].get('exit_code')
            ]
            parameter = self._process_parameter_from_command_output(out, err, exit_code, host_name).strip()
            if parameter not in self._parameter_host_dict:
                self._parameter_host_dict[parameter] = []
            self._parameter_host_dict[parameter].append(host_name)
        self._flg_is_check_relevant = self._is_check_relevant(self._parameter_host_dict)

        self._system_info = self._user_set_info(self._flg_is_check_relevant, self._parameter_host_dict)

        if (not self._flg_is_check_relevant) or (len(self._parameter_host_dict) == 1):
            return True

        self._failed_msg = "{parameter} is not uniform in all hosts: \n{description}".format(
            parameter=parameter_name,
            description=PythonUtils.key_to_list2str("list of the host of each version:", self._parameter_host_dict)
        )
        return False


# not in use for now

class UnifySystemParameterCheckDisplayInfo(UnifySystemParameterCheck):
    def _user_set_info(self, is_check_relevant, parameter_host_dict):
        if len(parameter_host_dict) == 1:
            return list(parameter_host_dict.keys())[0]
        return PythonUtils.key_to_list2str(
            "list of the {} of each host:".format(self._set_system_parameter_name()), parameter_host_dict)
