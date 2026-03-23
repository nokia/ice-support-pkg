from __future__ import absolute_import
from tools import adapter
from HealthCheckCommon.operations import *
import json
import re

from HealthCheckCommon.validator import Validator


class KeycloakLoginErrorsCheck(Validator):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._unique_operation_name = "is_keycloak_has_login_errors"
        self._title = "Check if keycloak has login errors"
        self._severity = Severity.WARNING

        self._failed_msg = "TBD"
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        THRESHOLD = 30
        problematic_users_dict = {}
        result_dict = {}
        get_ckey_pods = r"sudo kubectl get pods -A |grep -oPe 'bcmt-ckey-ckey-\d'"
        out = self.get_output_from_run_cmd(get_ckey_pods)

        for ckey_pod in out.splitlines():

            get_login_errors = r"sudo kubectl logs {pod_name} -n ncms |grep LOGIN_ERROR |grep -oPe 'username=[\w_-]+'". \
                format(pod_name=ckey_pod)
            ret_code, out, err = self.run_cmd(get_login_errors)
            if out.strip(): #if LOGIN_ERROR is found
                problematic_users = out.replace('username=', '')
                for user in problematic_users.splitlines():
                    if not problematic_users_dict.get(user):
                        problematic_users_dict[user] = 0
                    problematic_users_dict[user] += 1

        for user_name in problematic_users_dict:
            failed_login_counts = problematic_users_dict[user_name]
            if failed_login_counts > THRESHOLD:
                result_dict[user_name] = failed_login_counts

        if len(result_dict):
            failed_str = re.sub(r"{|}", "", json.dumps(result_dict, indent=4))
            self._failed_msg = "There are at least {} failed login attempts for the following users: \n{}".format(THRESHOLD, failed_str)
            return False
        return True


class VerifyCbisAdminKeyHost(Validator):
    objective_hosts = {Deployment_type.NCS_OVER_BM: [Objectives.MANAGERS]}

    def set_document(self):
        self._unique_operation_name = "is_cbis_admin_key_matching_containers_with_host"
        self._title = "Check if cbis-admin key in host is matching with cbis_manager  cbis_conductor container"
        self._severity = Severity.WARNING
        self._is_clean_cmd_info = True
        self._failed_msg = "keys are not matching, please check if any manual changes happened"
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        docker_or_podman = adapter.docker_or_podman()
        cbis_conductor_name = self.get_output_from_run_cmd(' sudo {}  ps --format "{{{{.Names}}}}" | grep cbis_conductor'.format(docker_or_podman))
        cbis_manager_name = self.get_output_from_run_cmd(' sudo {}  ps --format "{{{{.Names}}}}" | grep cbis_manager'.format(docker_or_podman))
        cbis_conductor_modulus = self.get_output_from_run_cmd(
            'sudo {} exec {}  openssl rsa -in  /home/cbis-admin/.ssh/id_rsa -noout -modulus'.format(docker_or_podman, cbis_conductor_name), add_bash_timeout=True)
        cbis_manager_modulus= self.get_output_from_run_cmd(
            'sudo {} exec {}  openssl rsa -in  /home/cbis-admin/.ssh/id_rsa -noout -modulus'.format(docker_or_podman, cbis_manager_name), add_bash_timeout=True)
        host_out = self.get_output_from_run_cmd('sudo openssl rsa -in  /home/cbis-admin/.ssh/id_rsa -noout -modulus')

        if host_out == cbis_conductor_modulus and host_out == cbis_manager_modulus:
            return True
        return False


