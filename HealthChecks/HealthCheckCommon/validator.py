from __future__ import absolute_import
import abc

from HealthCheckCommon.table_system_info import TableSystemInfo
from tools import adapter
from HealthCheckCommon.operations import FlowsOperator
from tools.ConfigStore import ConfigStore
from tools.global_enums import Severity


class Validator(FlowsOperator):
    # Prerequisite checks - will be validate in unit test
    # put here list of validations you expect to be performed before this one
    # TODO: add dependencies of other validators
    PREREQUISITES_CHECKS = []

    def __init__(self, host_executor):
        self._is_action_type_active = False
        FlowsOperator.__init__(self, host_executor)  # calls set_initial_values and set_document
        assert (self._severity in Severity.AVAILABLE_SEVERITIES)  # make sure remember to set_severity
        adapter.init_adapter(self)

    def set_initial_values(self):
        self._severity = None
        self._blocking_tags = []
        self.set_document()  # need to know here if this is pure info or not
        FlowsOperator.set_initial_values(self)

    def get_prerequisites(self):
        return self.PREREQUISITES_CHECKS

    def get_severity(self):
        return self._severity

    def get_blocking_tags(self):
        assert not hasattr(self, "_blocking_tag"), "did you mean blocking_tags ?"
        return self._blocking_tags

    @abc.abstractmethod
    def is_validation_passed(self):  # to be overridden
        # pylint: disable=E9002
        '''return true if and only if the validation passed'''
        assert False, "is_validation_passed not implemented"

    def get_openstack_api_command(self, pre_command, post_command):
        conf_dict = ConfigStore.get_openstack_info()

        os_auth_url = conf_dict["openstack"]["OS_AUTH_URL"]
        os_username = conf_dict["openstack"]["OS_USERNAME"]
        os_cacert_content = conf_dict["openstack"]["OS_CACERT_CONTENT"]
        os_password = conf_dict["openstack"]["OS_PASSWORD"]
        os_user_domain_name = conf_dict["openstack"]["OS_USER_DOMAIN_NAME"]
        os_project_name = conf_dict["openstack"]["OS_PROJECT_NAME"]
        os_region_name = conf_dict["openstack"]["OS_REGION_NAME"]

        cmd = "{} -- /usr/local/bin/openstack --os-cacert \"{}\" --insecure --os-auth-url {} --os-username {} " \
              "--os-password \"{}\" --os-user-domain-name {} --os-identity-api-version 3 --os-project-name {} " \
              "--os-region-name {} --os-auth-type password {}" \
            .format(pre_command, os_cacert_content, os_auth_url, os_username, os_password, os_user_domain_name,
                    os_project_name, os_region_name, post_command)

        return cmd


class InformatorValidator(Validator):
    '''
    informator not only runs interesting information on the system to the user.
    it can be part of validation or it can be pure information fetching
    '''

    def __init__(self, ip):
        self._is_action_type_active = False
        Validator.__init__(self, ip)  # this calls again to set set_document()

        assert self._is_pure_info is not None, \
            "please set _is_pure_info in set_document at class informator validator " + str(self.__class__)
        assert self._title_of_info is not None, \
            "this is informator type, please implement self._title_of_info  " + str(self.__class__)

    def set_initial_values(self):
        self._title_of_info = ''
        self._system_info = ""
        self._table_system_info = TableSystemInfo()
        self._is_pure_info = None  # is True for information only, False in case collecting information for a validation
        self._is_highlighted_info = False
        self.set_document()  # need to know here if this is pure info or not

        Validator.set_initial_values(self)

        if self._is_pure_info:
            self._severity = Severity.NA
            self._title = 'Info - ' + self._title_of_info
            self._failed_msg = "could not get the needed info from the system"

    def set_document(self):
        assert False

    def get_severity(self):
        if self._is_pure_info:
            return Severity.NA
        else:
            return self._severity

    def get_system_info_title(self):
        return self._title_of_info

    def is_highlighted_info(self):
        return self._is_highlighted_info

    # overwrite this or make sure self._system_info get value in is_validation_passed
    def get_system_info(self):
        assert self._system_info is not None
        return self._system_info

    def get_table_system_info(self):
        self._table_system_info.assert_table_system_info()
        return self._table_system_info

    # should be overwritten if this is NOT PURE_INFO
    def is_validation_passed(self):
        # pylint: disable=E9002
        '''return true if and only if the validation passed'''
        if self._is_pure_info:
            return True
        else:
            assert "InformatorValidator that is not _is_pure_info must be implemented this at " + str(self.__class__)

    def is_pure_info(self):
        return self._is_pure_info
