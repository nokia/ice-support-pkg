from __future__ import absolute_import
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
import tools.sys_parameters as  sys_parameters
from HealthCheckCommon.log_flows.base_log_validation import *


class Log_issues_finder_flow(BaseValidationFlow):

    def get_conf_file_name(self):
        raise NotImplementedError('please implement get_conf_file_name()')

    def _get_list_of_validator_class(self, version, deployment_type):
        assert False

    def read_log_error_conf_file(self, conf_file_name):
        with open(conf_file_name) as fd:
            data = json.load(fd)
            return data

    def _is_issue_relevent(self, issue, deployment_type, version):
        # todo add log here
        if deployment_type not in issue["deployment_types"]:
            return False
        if str(version) not in issue["versions"]:
            return False
        return True

    def get_validations_name(self, version, deployment_type, validator_objects):
        conf_file_name = self.get_conf_file_name()
        all_issues = self.read_log_error_conf_file(conf_file_name)

        to_return = []
        for component in all_issues:
            for issue in all_issues[component]:
                if self._is_issue_relevent(issue, deployment_type, version):
                    to_return.append(issue["id"])
        return to_return

    def should_be_created(self, flg_is_passive_type_only, validation_object, validation_host_executor,
                          deployment_type, hosts_list=None, roles=None, specific_validations=None):
        if specific_validations:
            if validation_object._unique_operation_name not in specific_validations:
                return False
        if not validation_host_executor.is_connected:
            return False
        if roles:
            matched_roles = PythonUtils.list_intersection(roles, validation_host_executor.roles)
            if not len(matched_roles):
                return False
        matched_validation_roles = PythonUtils.list_intersection(validation_host_executor.roles, roles)
        if not len(matched_validation_roles):
            return False
        if hosts_list:
            if validation_host_executor.host_name not in hosts_list:
                return False

        return True

    def _get_list_of_validator_object(self, version, deployment_type, flg_is_passive_type_only,
                                      only_specific_hosts_ip_list=None, roles=None, specific_validations=None,
                                      specific_tags=None):
        """
        this is the main interface of the system
        :return: data type of the structure of dict with return code and message:
        for example:
        {'return_code': 200, 'message': 'done'}
        """

        assert (version in self.version_list())
        assert (deployment_type in self.deployment_type_list())

        validations_list = []
        conf_file_name = self.get_conf_file_name()
        all_issues = self.read_log_error_conf_file(conf_file_name)

        object_list = []
        for component in all_issues:

            for issue in all_issues[component]:

                if not self._is_issue_relevent(issue, deployment_type, version):
                    continue

                if issue.get("severity"):
                    severity = issue.get("severity")
                else:
                    severity = Severity.WARNING

                host_executors = sys_parameters.get_host_executor_factory().get_all_host_executors()
                for host_name in host_executors:

                    log_cmd_type = issue["log_cmd_type"]

                    if log_cmd_type == "file":
                        validation_object = issues_in_log_file_validator(ip=host_executors[host_name],
                                                                         log_file_path=issue["log_cmd"],
                                                                         patterns=issue["patterns"],
                                                                         component=component,
                                                                         id=issue["id"],
                                                                         severity=severity,
                                                                         issue_msg=issue["issue"])
                    elif log_cmd_type == "cmd":
                        validation_object = issues_in_cmd_log_validator(ip=host_executors[host_name],
                                                                        log_cmd=issue["log_cmd"],
                                                                        patterns=issue["patterns"],
                                                                        component=component,
                                                                        id=issue["id"],
                                                                        severity=severity,
                                                                        issue_msg=issue["issue"])
                    else:
                        assert False, "log_cmd_type un known"

                    validation_roles = issue["host_roles"]

                    if self.should_be_created(flg_is_passive_type_only, validation_object, host_executors[host_name],
                                              deployment_type, only_specific_hosts_ip_list, validation_roles,
                                              specific_validations):
                        validations_list.append(validation_object)

        if len(validations_list) > 0:  # add all to one que. in the case of multiple groups this is much more efficient
            object_list.append(validations_list)
        return object_list
