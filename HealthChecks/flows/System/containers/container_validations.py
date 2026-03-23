from __future__ import absolute_import

from tools import adapter
from HealthCheckCommon.operations import *
import re
from tools.EnvironmentInfo import NCSBareMetalEnvironmentInfo
from HealthCheckCommon.validator import Validator, InformatorValidator
from flows.Storage.ceph.Ceph import CephValidation
import os

CONTAINERS_TO_EXCLUDE = "system_check_containers_to_exclude"


class ValidateDockersHealth(Validator):
    objective_hosts = {Deployment_type.CBIS: [Objectives.ALL_HOSTS],
                       Deployment_type.NCS_OVER_BM: [Objectives.ALL_NODES]}

    def set_document(self):
        self._unique_operation_name = "Dockers_health_check"
        self._title = "Verify docker containers are healthy"
        self._failed_msg = "TBD"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        docker_or_podman = adapter.docker_or_podman()
        docker_ps_cmd = "sudo {docker_or_podman} ps -a --format 'table {{{{.Names}}}} {{{{.Status}}}}'".format(
            docker_or_podman=docker_or_podman)
        return_code, out, err = self.run_cmd(r"{} | grep -i \"unhealthy\|restarting\|starting\"".format(docker_ps_cmd),
                                             timeout=30)
        if return_code == 1:
            return True
        elif out:
            self._failed_msg = 'The following containers are at failed state: \n {}'.format(out)
            return False
        raise SystemError

class ValidateDockersNotExited(InformatorValidator, CephValidation):

    objective_hosts = {Deployment_type.CBIS: [Objectives.ALL_HOSTS],
                       Deployment_type.NCS_OVER_BM: [Objectives.ALL_NODES]}

    def __init__(self, ip):
        Validator.__init__(self, ip)
        self.containers_to_exclude = ''
        self.containers_to_exclude = open(os.path.join(os.path.dirname(__file__), CONTAINERS_TO_EXCLUDE)).read().split()

    def set_document(self):
        self._unique_operation_name = "check_exited_dockers_with_errors"
        self._title = "Exited dockers with errors from last two weeks"
        self._failed_msg = "TBD"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.SYMPTOM]
        self._title_of_info = "All exited dockers"
        self._is_pure_info = False

    def is_validation_passed(self):
        info_dockers = []
        warning_dockers = []
        time_options = ['second', 'minute', 'hour', 'day']

        if CephValidation.is_prerequisite_fulfilled(self):
            self.containers_to_exclude.append('manila')

        docker_or_podman = adapter.docker_or_podman()
        docker_ps_cmd = "sudo {docker_or_podman} ps -a --format 'table {{{{.Names}}}} {{{{.Status}}}}'".format(
            docker_or_podman=docker_or_podman)
        cmd = "{} | grep -i exited | grep -v '(0)' ".format(docker_ps_cmd)

        return_code, out, err = self.run_cmd(cmd, timeout=30)
        if return_code == 1:
            return True
        elif out:
            for line in out.split('\n'):
                if line == "":
                    continue
                line_list = line.split()
                time_info = next((time for time in time_options if time in line), False)
                if time_info or ('week' in line and self._get_num_from_status(" ".join(line_list[3:]), cmd) <= 2):
                    should_be_excluded = False
                    for container in self.containers_to_exclude:
                        if container in line_list[0]:
                            should_be_excluded = True
                    if should_be_excluded:
                        info_dockers.append(line)
                    else:
                        warning_dockers.append(line)
                else:
                    info_dockers.append(line)
            if info_dockers:
                info_dockers += warning_dockers
                self.add_to_validation_log('All exited dockers: \n {}'.format('\n'.join(info_dockers)))
                self._system_info = '\n'.join(info_dockers)
            if warning_dockers:
                self._failed_msg = 'The following dockers exited on last two weeks: \n {}'.format(
                    '\n'.join(warning_dockers))
                self._failed_msg += '\n\nPlease consider relevant exited dockers according the deployment configuration'
                self.add_to_validation_log(self._failed_msg)
                return False
            return True
        raise UnExpectedSystemOutput(ip=self._host_executor.ip, cmd=cmd, output=out)

    def _get_num_from_status(self, status, cmd):
        if "About a" in status:
            return 1
        numbers_list = re.findall(r"\d+", status)

        if len(numbers_list) != 1:
            raise UnExpectedSystemOutput(self.get_host_ip(), cmd, status, "Expected to have 'About a' "
                                                                          "or only 1 number in status")
        return int(numbers_list[0])

class ValidateCbisManagerNginxHealth(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.MANAGERS]
    }

    def set_document(self):
        self._unique_operation_name = "validate_cbis_manager_nginx_health"
        self._title = "Validate CBIS manager nginx health"
        self._failed_msg = "Cbis manager nginx container failure detected"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def _investigate_nginx_config(self):
        config_path = "/data0/podman/storage/volumes/nginx_etc_vol/_data/nginx.conf"

        ncs_info = NCSBareMetalEnvironmentInfo().get_ncs_version_info()
        match= re.search(r"build.*?(\d+.\d+.\d+)-?(\d+)", ncs_info)
        ncs_version = match.group(1)

        cmd = "sudo cat {} | grep -A7 map".format(config_path)
        config_content = self.get_output_from_run_cmd(cmd)

        expected_entry = "{} 127.0.0.1:8001;".format(ncs_version)
        PLACEHOLDER = "LATEST_VERSION_IP_PORT"

        if PLACEHOLDER in config_content:
            self._failed_msg += (
                ", likely caused by unrendered Nginx template.\n"
                "Found placeholder '{}' instead of actual version mapping."
            ).format(PLACEHOLDER)
        elif expected_entry not in config_content:
            self._failed_msg += (
                ", mapping is incorrect.\n"
                "Expected to find: '{}'\n"
                "Please check the content of {}"
            ).format(expected_entry, config_path)
        else:
            self._failed_msg += ", but Nginx config looks correct.".format()

    def is_validation_passed(self):
        docker_or_podman = adapter.docker_or_podman()
        docker_ps_cmd = "sudo {docker_or_podman} ps -a --filter 'name=cbis-manager_nginx*' --format 'table {{{{.Names}}}} {{{{.Status}}}}'".format(
            docker_or_podman=docker_or_podman)
        return_code, out, err = self.run_cmd(r'{} | grep -Ei "unhealthy|restarting|starting|exited" | wc -l '.format(docker_ps_cmd),timeout=30)

        if int(out) == 0:
            return True

        self._investigate_nginx_config()
        return False

class ValidateCbisConductorHealth(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.MANAGERS]
    }

    def set_document(self):
        self._unique_operation_name = "validate_cbis_conductor_health"
        self._title = "Validate CBIS conductor health"
        self._failed_msg = "Cbis conductor container failure detected"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def _investigate_symlink(self):
        link_path = "/opt/install/data/hooks"
        actual_target = self.get_output_from_run_cmd("sudo readlink -f {}".format(link_path)).strip()

        if self.file_utils.is_dir_exist(actual_target):
            self._failed_msg += ", but {} symlink destination exists.\n".format(link_path)
        else:
            self._failed_msg += (
                ", likely caused by broken symlink.\n"
                "The link '{}' points to '{}', which does not exist."
            ).format(link_path, actual_target)

    def is_validation_passed(self):
        docker_or_podman = adapter.docker_or_podman()
        docker_ps_cmd = "sudo {docker_or_podman} ps -a --filter 'name=cbis_conductor*' --format 'table {{{{.Names}}}} {{{{.Status}}}}'".format(
            docker_or_podman=docker_or_podman)
        return_code, out, err = self.run_cmd(r'{} | grep -Ei "unhealthy|restarting|starting|exited" | wc -l '.format(docker_ps_cmd),timeout=30)

        if int(out) == 0:
            return True

        self._investigate_symlink()
        return False