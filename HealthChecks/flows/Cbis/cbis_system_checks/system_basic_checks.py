from __future__ import absolute_import
from datetime import datetime, timedelta
from tools import adapter
from HealthCheckCommon.operations import *
from HealthCheckCommon.validator import Validator, InformatorValidator
from xml.etree import ElementTree
import tools.sys_parameters as gs
import tools.paths as paths
from flows.Chain_of_events.operation_timing_info import Operation_timing_info
import os
import json
import time
import yaml

from tools.ConfigStore import ConfigStore
from tools.global_enums import Version
from flows.Ncs.ncs_validations import CheckSymLink
from six.moves import range
from tools.Info import GetInfo

try:
    import pika
except:
    pass


class ClusterResourcesStatus(Validator):
    objective_hosts = [Objectives.ONE_CONTROLLER]

    def set_document(self):
        self._unique_operation_name = "are_cluster_resources_healthy"
        self._title = "Verify pcs status"
        self._failed_msg = "TBD"
        self._severity = Severity.CRITICAL

        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        out = self.get_output_from_run_cmd("sudo pcs status xml", add_bash_timeout=True)
        if 'xml version' in out.split("\n", 1)[0]:
            resources_status_xml = out.split("\n", 1)[1]
        else:
            resources_status_xml = out
        res_dict = {}
        root = ElementTree.fromstring(resources_status_xml)

        for node in root.iter('node'):
            if node.get('online') == "false":
                res_dict.setdefault('offline_nodes', []).append(node.get('name'))

        for resource in root.iter('resource'):
            if resource.get('role') not in ('Started', 'Master', 'Slave', 'Promoted') or resource.get(
                    'failed') == "true" \
                    or resource.get('managed') == "false":
                res_dict.setdefault('failed resources status', []).append(
                    ': '.join([resource.get('id'), resource.get('role')]).strip())
        for failure_section in root.iter('failure'):
            res_dict.setdefault('failures', []).append(failure_section.attrib)
        if res_dict:
            self._failed_msg = "pcs status validation failed. following problems accrued:{}\n".format(
                json.dumps(res_dict, indent=4))
            return False
        return True


class CheckStackStatus(Validator):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "stack_status_check"
        self._title = "Verify stack is not in failed state"
        self._failed_msg = "No stack is installed"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PRE_OPERATION, ImplicationTag.SYMPTOM]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        stack = ''
        stack_status = ''
        if gs.get_version() >= Version.V25:
            out = self.get_output_from_run_cmd("openstack overcloud status", add_bash_timeout=True)
            for line in out.splitlines():
                if 'overcloud' in line:
                    stack = 'overcloud'
                    stack_status = line.split('|')[2].strip()
                    continue
        else:
            out = self.get_output_from_run_cmd(
                "source {}; timeout --kill-after=60 30 openstack stack list -f json".format(
                    self.system_utils.get_stackrc_file_path()))
            stack = json.loads(out)
        if not stack:
            return False
        if gs.get_version() < Version.V25:
            stack_status = str(stack[0]['Stack Status'])
        if stack_status in ["CREATE_COMPLETE", "UPDATE_COMPLETE", "CHECK_COMPLETE", "DEPLOY_SUCCESS"]:
            return True
        else:
            self._failed_msg = "Unexpected stack status - {}".format(stack_status)
            return False


class CheckSuccessFlgExist(Validator):
    objective_hosts = [Objectives.CONTROLLERS, Objectives.COMPUTES, Objectives.UC, Objectives.STORAGE]

    def set_document(self):
        self._unique_operation_name = "check_success_flg_exist"
        self._title = "Verify successful deployment of the node"
        self._failed_msg = "installation_success/update_success flag is missing"
        self._msg = "CBIS Installation/Scale-out was unsuccessful on this node.\n" \
                    "Cluster operations should not be performed, until this issue is resolved.\n" \
                    "Review installation or scale-out logs to determine why the installation/scale-out was unsuccessful."
        self._severity = Severity.CRITICAL

        self._implication_tags = [ImplicationTag.SYMPTOM]

    def is_validation_passed(self):
        suffix = '_locked' if self.system_utils.is_system_armed() else ''
        flg_has_installation_success = self.run_cmd_return_is_successful(
            "test -f /usr/share/cbis/installation_success{}".format(suffix))
        flg_has_update_success = self.run_cmd_return_is_successful(
            "test -f /usr/share/cbis/update_success{}".format(suffix))
        return flg_has_installation_success or flg_has_update_success


class CheckNetworkAgentHostnameMismatch(Validator):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "check_network_agent_hostname_mismatch"
        self._title = "Verify neutron agents hostname is matching UC hostname"
        self._failed_msg = "test not completed:"
        self._severity = Severity.CRITICAL

        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        out = self.get_output_from_run_cmd("source {}; timeout --kill-after=60 30 openstack network agent list -f json".
                                           format(self.system_utils.get_overcloudrc_file_path()))

        network_agents = json.loads(out)
        for key in network_agents:
            if 'neutron' in key['Binary']:
                pass
            else:
                self._failed_msg = "Hostname mismatch found for the following neutron agents \n {}".format(
                    key['Binary'])
                return False
        return True


class check_galera_is_synced_base(Validator):
    objective_hosts = [Objectives.CONTROLLERS]

    def set_document(self):
        self._unique_operation_name = None
        self._title = "Verify Galera is synced"
        self._failed_msg = "Galera is not synced"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_Galera_synced_in_out(self, command):
        ret, out, error = self.run_cmd(command, add_bash_timeout=True)
        if 'Galera cluster node is synced' in out:
            return True
        if 'Galera cluster node is not synced' in out:
            return False  #if return 1 but can tell us there is problem with Galera
        else:
            if ret != 0:
                raise UnExpectedSystemOutput(self.get_host_ip(),
                                             command,
                                             out,
                                             "un expected output clustercheck")
        return False


class check_galera_is_synced_docker(check_galera_is_synced_base):

    def set_document(self):
        check_galera_is_synced_base.set_document(self)
        self._unique_operation_name = "check_galera_is_synced_docker"

    def is_validation_passed(self):
        docker_or_podman = adapter.docker_or_podman()
        command = "sudo {docker_or_podman} exec clustercheck clustercheck".format(docker_or_podman=docker_or_podman)
        return self.is_Galera_synced_in_out(command)


class check_galera_is_synced(check_galera_is_synced_base):

    def set_document(self):
        check_galera_is_synced_base.set_document(self)
        self._unique_operation_name = "check_galera_is_synced"

    def is_validation_passed(self):
        command = "sudo clustercheck"
        return self.is_Galera_synced_in_out(command)


class CbisSystemCheckGnocchiCeilometerDocker(Validator):
    objective_hosts = [Objectives.ALL_HOSTS]

    def set_document(self):
        self._unique_operation_name = "check_gnocchi_and_ceilometer_docker_stopped"
        self._title = "Verify gnocchi and ceilometer containers are stopped"
        self._failed_msg = "gnocchi/ceilometer container(s) running"
        self._msg = "Gnocchi and Ceilometer have been removed in CBIS 19MP4 PP4 (CBIS-11657), " \
                    "CBIS 19ASP4 PP1 (CBIS-11658), CBIS 20 PP2 (CBIS-15102). " \
                    "These services are known to generate significant message volume, slowing down rabbitmq."
        self._severity = Severity.ERROR

        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION, ImplicationTag.PERFORMANCE]

    def is_validation_passed(self):
        docker_or_podman = adapter.docker_or_podman()
        out = self.get_output_from_run_cmd(
            "sudo {docker_or_podman} ps --format '{{{{.Names}}}}' --filter 'name=^/ceilo|gnocchi'".
            format(docker_or_podman=docker_or_podman))
        if out:
            self._details = "running containers:\n {} ".format(out.strip())
            return False
        return True


class CbisSystemCheckGnocchiCeilometer(Validator):
    objective_hosts = [Objectives.ALL_HOSTS]

    def set_document(self):
        self._unique_operation_name = "check_gnocchi_and_ceilometer_disabled"
        self._title = "Verify gnocchi and ceilometer are stopped/disabled"
        self._failed_msg = "gnocchi/ceilometer is not stopped/disabled"
        self._msg = "These services are known to generate significant message volume, slowing down rabbitmq."
        self._severity = Severity.ERROR

        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION, ImplicationTag.PERFORMANCE]

    def is_validation_passed(self):
        msg = []

        code, out, err = self.run_cmd("systemctl list-units --type=service | egrep 'gnocchi|ceilo|aodh'")
        units = [x.split(None, 4) for x in out.splitlines()]

        code, out, err = self.run_cmd("systemctl list-unit-files --type=service | egrep 'gnocchi|ceilo|aodh'")
        unit_files = [x.split(None, 2) for x in out.splitlines()]

        for unit in units:
            if unit[3] == 'running':
                msg.append("{} is running".format(unit[0]))

        for unit_file in unit_files:
            if unit_file[1] == 'enabled':
                msg.append("{} is enabled".format(unit_file[0]))

        if msg:
            self._details = "\n".join(msg)
            return False
        return True


'''
# should we delete it - it's not in use
class FileTrackerCheck(Validator):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "file tracker check"
        self._title = "Check if file tracker has at least one snapshot"
        self._failed_msg = "test not completed:"
        self._severity = Severity.CRITICAL


    def is_validation_passed(self):
        FILE_TRACKER_SHARE_DIR = '/usr/share/ice/filetracker/'
        if os.path.isdir(FILE_TRACKER_SHARE_DIR):
            snapshots_count = len(os.listdir(FILE_TRACKER_SHARE_DIR))
            if snapshots_count:
                return True
        self._failed_msg = """
        file tracker is not used/installed in your system.
        This plugin used for tracking configurations.
        You should install it ASAP and take a snapshot when the system is healthy'
        """
        return False
'''


class BIOSCheck(Validator):  #deprecated
    objective_hosts = [Objectives.CONTROLLERS, Objectives.COMPUTES, Objectives.STORAGE]

    def set_document(self):
        self._unique_operation_name = "bios_version_check"
        self._title = "Check BIOS version"
        self._failed_msg = "test not completed:"
        self._severity = Severity.CRITICAL

    def dmidecode(self, arg):
        current_bios_version = self.get_output_from_run_cmd("sudo dmidecode -s %s" % arg, timeout=60)
        current_bios_version = current_bios_version.replace("\n", "")
        output = current_bios_version.strip()
        return output

    def is_validation_passed(self):
        CBIS_version = gs.get_version()
        current_bios_version = self.dmidecode("bios-version")
        hardware_type = self.dmidecode("system-product-name")
        hardware_type = hardware_type.split("/")[0]

        with open(paths.INFRA_JSON_PATH) as json_file:
            data = json.load(json_file)

        bios_version = data["CBIS%s" % CBIS_version].get(hardware_type, None)
        if bios_version:
            bios_version = bios_version.get('BIOS-version', None)
            if bios_version and current_bios_version in bios_version:
                return True
            else:
                err = "There is no BIOS version was match to supported hardware configuration %s " % current_bios_version
                self._failed_msg = err
                self._severity = Severity.ERROR
                return False
        else:
            err = "There is no BIOS version was match to supported hardware configuration %s " % hardware_type
            self._failed_msg = err
            self._severity = Severity.ERROR
            return False
        err = "The current bios version %s is not aligned with original one %s " % (current_bios_version, bios_version)
        self._failed_msg = err
        return False


class UCBackupTimeCollector(DataCollector):
    objective_hosts = [Objectives.HYP]

    def collect_data(self):
        uc_backup_dir = self._get_uc_backup_dir()
        cmd = 'sudo ls -lt --time-style=long-iso {} | grep "undercloud_backup" | head -n 1'.format(uc_backup_dir)
        out = self.get_output_from_run_cmd(cmd)
        if not out:
            return None
        out_parts = out.split()
        date_time_field_start_idx = 5
        str_backup_time = " ".join(out_parts[date_time_field_start_idx:date_time_field_start_idx + 2])
        datetime_backup_time = datetime.strptime(str_backup_time, "%Y-%m-%d %H:%M")
        last_backup_time = datetime_backup_time.strftime('%Y-%m-%d %H:%M:%S')
        return last_backup_time

    def _get_uc_backup_dir(self):
        user_config_path = "/root/cbis-installer/user_config.yaml"
        cmd = 'sudo grep backup_nfs_mountpoint {}'.format(user_config_path)
        out = self.get_output_from_run_cmd(cmd)
        uc_backup_dir = out.split()[1].strip()
        return uc_backup_dir


class UCBackupCheck(Validator):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "uc_backups_checks"
        self._title = "Check uc backups exists"
        self._failed_msg = "uc backups may do not exist"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.RISK_NO_HIGH_AVAILABILITY]

    # Fetch the last PP/MP time
    def last_hotfix_timing(self):
        operation_timing = Operation_timing_info(self)
        res = operation_timing.get_operations_datetime()
        if not res.get('hotfix'):
            return '1900-01-01 00:00:00'
        return res['hotfix'][-1]["start_time"]

    # Fetch the last Undercloud VM Backup time
    def get_last_uc_backup_time_by_log(self):
        operation_timing = Operation_timing_info(self)
        res = operation_timing.get_operations_datetime()
        self.add_to_validation_log("CBIS operations: {}".format(res))
        if res.get('undercloud_backup') == None:
            return None
        return res['undercloud_backup'][-1]["start_time"]

    def get_last_uc_backup_time_by_dir(self):
        res = self.run_data_collector(UCBackupTimeCollector)
        return res["hypervisor"]

    def get_the_latest_backup_time(self, uc_backup_time_from_log, uc_backup_time_from_dir):
        timestamp_format = "%Y-%m-%d %H:%M:%S"
        if not uc_backup_time_from_log and not uc_backup_time_from_dir:
            return None
        if uc_backup_time_from_log and uc_backup_time_from_dir:
            uc_backup_time_from_log = datetime.strptime(uc_backup_time_from_log, timestamp_format)
            uc_backup_time_from_dir = datetime.strptime(uc_backup_time_from_dir, timestamp_format)
            max_uc_backup_time = max(uc_backup_time_from_log, uc_backup_time_from_dir)
            uc_backup_time = max_uc_backup_time.strftime(timestamp_format)
        elif uc_backup_time_from_log:
            uc_backup_time = uc_backup_time_from_log
        else:
            uc_backup_time = uc_backup_time_from_dir
        return uc_backup_time

    def is_UCBackup_timing_valid(self, UC_backup_time, UC_stack_time, UC_hotfix_time):
        time_format = '%Y-%m-%d %H:%M:%S'
        backup_time = datetime.strptime(UC_backup_time, time_format)
        stack_time = datetime.strptime(UC_stack_time, time_format)
        hotfix_time = datetime.strptime(UC_hotfix_time, time_format)
        if backup_time > hotfix_time and backup_time > stack_time:
            return True
        return False

    def is_validation_passed(self):
        uc_backup_time_from_log = self.get_last_uc_backup_time_by_log()
        uc_backup_time_from_dir = self.get_last_uc_backup_time_by_dir()
        UC_backup_time = self.get_the_latest_backup_time(uc_backup_time_from_log, uc_backup_time_from_dir)
        self.add_to_validation_log('UC_backup_time: {}'.format(UC_backup_time))
        if UC_backup_time == None:
            self._failed_msg = "We could not find valid Undercloud VM backups stored on the Hypervisor." \
                               " please verify manually that Undercloud VM backups exists or" \
                               " Refer Chapter - Undercloud VM Backup and Restore in CBIS manager or Operations Manual Documents"
            self._severity = Severity.WARNING
            return False
        if gs.get_version() < Version.V25:
            UC_stack_time = self.get_last_stack_update_time_by_cmd()
        else:
            UC_stack_time = self.get_last_stack_update_time_by_log()
        self.add_to_validation_log('UC_stack_time: {}'.format(UC_stack_time))
        UC_hotfix_time = self.last_hotfix_timing()
        self.add_to_validation_log('UC_hotfix_time: {}'.format(UC_hotfix_time))

        if UC_stack_time and self.is_UCBackup_timing_valid(UC_backup_time, UC_stack_time, UC_hotfix_time):
            return True
        elif not UC_stack_time:
            self._failed_msg = ("Could not find Undercloud stack time. Please verify manually the last Undercloud "
                                "stack time, and make sure it is earlier than the last backup time")
            return False
        else:
            self._failed_msg = "There are no valid Undercloud VM backups stored on the Hypervisor after Stack Update or Hotfix installation.  Refer Chapter - Undercloud VM Backup and Restore in CBIS manager or Operations Manual Documents"
            self._severity = Severity.ERROR
            return False

    # Fetch the Overcloud stack creation or update time
    def get_last_stack_update_time_by_cmd(self):
        cmd = 'source {}; openstack stack list -f yaml'.format(self.system_utils.get_stackrc_file_path())
        out = self.get_output_from_run_cmd(cmd)
        if not out or out.strip() == "[]":
            raise UnExpectedSystemOutput(ip=self.get_host_ip(), cmd=cmd, output=out,
                                         message="Stack list is empty - overcloud is not installed")
        y = PythonUtils.yaml_safe_load(out)
        if y[0]['Updated Time'] == None:
            stack_datetime = datetime.strptime(y[0]['Creation Time'], "%Y-%m-%dT%H:%M:%SZ")
        else:
            stack_datetime = datetime.strptime(y[0]['Updated Time'], "%Y-%m-%dT%H:%M:%SZ")
        return stack_datetime.strftime('%Y-%m-%d %H:%M:%S')

    def get_last_stack_update_time_by_log(self):
        operation_timing = Operation_timing_info(self)
        res = operation_timing.get_operations_datetime()
        if res.get('stack_update') is None:
            return None
        return res['stack_update'][-1]["end_time"]


class OvercloudBackupCheck(Validator):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "overcloud_backups_checks"
        self._title = "Check overcloud backups are exists"
        self._failed_msg = "Overcloud backup is not exists"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.RISK_NO_HIGH_AVAILABILITY, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        controllers_with_no_backup = []

        controllers_executors = gs.get_host_executor_factory().get_host_executors_by_roles(Objectives.CONTROLLERS)
        errors = []
        for controller in controllers_executors:
            oc_backup = True
            if gs.get_version() < Version.V24:
                overcloud_backup_path = '/mnt/backup'
                overcloud_backup_path = os.path.join(overcloud_backup_path, controller)
                return_code, out, _ = self.run_cmd("sudo ls -ltr {} | tail -3".format(overcloud_backup_path))
                if not out:
                    oc_backup = False
                else:
                    found_backup = False
                    for line in reversed(out.splitlines()):
                        backup_folder = line.strip().split()[-1]
                        overcloud_backup_folder = os.path.join(overcloud_backup_path, backup_folder)
                        return_code, out, _ = self.run_cmd("sudo ls -ltr {} | tail -1".format(overcloud_backup_folder))
                        if not out or 'total 0' in out:
                            continue
                        else:
                            found_backup = True
                            overcloud_backup_path = os.path.join(overcloud_backup_folder, out.strip().split()[-1])
                            break
                    if not found_backup:
                        oc_backup = False
            else:
                overcloud_backup_path = '/mnt/backup/overcloud_db_backups'
                return_code, out, _ = self.run_cmd(
                    "sudo ls -ltr {} | grep {} | tail -1".format(overcloud_backup_path, controller))
                if not out or 'total 0' in out:
                    oc_backup = False
                else:
                    backup_file = out.strip().split()[-1]
                    overcloud_backup_path = os.path.join(overcloud_backup_path, backup_file)
            if oc_backup:
                if not self.file_utils.is_file_modified_on_last_x_days(overcloud_backup_path, 3):
                    errors.append("The overcloud backup of '{}' at {} isn't from the last 3 days".format(controller,
                                                                                                         overcloud_backup_path))
                    controllers_with_no_backup.append(controller)
                elif self.file_utils.is_file_empty(overcloud_backup_path):
                    errors.append(
                        "The overcloud backup of '{}' at {} is empty".format(controller, overcloud_backup_path))
                    controllers_with_no_backup.append(controller)
            else:
                errors.append(
                    "The overcloud backup does not exists for '{}' at {}".format(controller, overcloud_backup_path))
                controllers_with_no_backup.append(controller)

        if ((gs.get_version() < Version.V24 and controllers_with_no_backup) or
                (gs.get_version() >= Version.V24 and len(controllers_with_no_backup) == len(controllers_executors))):
            self._failed_msg = "\n".join(errors)
            return False

        return True


class ValidationReadPermissions(Validator):
    objective_hosts = [Objectives.UC]

    CRITICAL_DIRECTORIES = ["/usr/share/cbis", "/home/stack/templates"]
    ALLOWED_FILES_WITH_NO_PERMISSIONS = ['/usr/share/cbis/undercloud/templates/platform/user_config.json']
    cmd_all_files_with_permissions = "sudo find {} -type f | xargs ls -l 2>/dev/null "
    cmd_all_dir_with_permissions = "sudo find {} -type d | xargs ls -ld 2>/dev/null"

    @staticmethod
    def is_correct_permissions(name_with_permissions):
        if len(name_with_permissions) < 8:
            raise UnExpectedSystemOutput("uc", "sudo find {} -type f | xargs ls -l 2>/dev/null ",
                                         "expectind the begging of the out to have the premitions str")
        if name_with_permissions[7] == 'r':
            return True
        #check if this file allowed not to have permissions
        for file_name in ValidationReadPermissions.ALLOWED_FILES_WITH_NO_PERMISSIONS:
            if file_name in name_with_permissions:
                return True
        return False

    def set_document(self):
        self._unique_operation_name = "read_permissions_of_critical_directories"
        self._title = "validate read permissions of critical directories"
        self._failed_msg = "permissions issue"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        bad_files = []
        for dir in ValidationReadPermissions.CRITICAL_DIRECTORIES:
            ret_cod, list_all_files_permission, err = self.run_cmd(
                ValidationReadPermissions.cmd_all_files_with_permissions.format(dir),
                20)

            #return code in this case is not expected to be 0
            ret_cod, list_all_dir_permission, err = self.run_cmd(
                ValidationReadPermissions.cmd_all_dir_with_permissions.format(dir))

            list_all_files_permission = list_all_dir_permission.splitlines() + list_all_files_permission.splitlines()

            bad_files = bad_files + [file for file in list_all_files_permission
                                     if not ValidationReadPermissions.is_correct_permissions(file)]

        if len(bad_files) == 0:
            return True

        max_printable = 100  #do not want to have a print out of too many file list. first 100 is enoth.

        if len(bad_files) < max_printable:
            printable_bad_files_list = "\n".join(bad_files)
            self._failed_msg = "Warning: this validation is important if you are about to perform scale in/out or upgrade:\n" \
                               " the following file/dirs do not have read permissions for others:\n {}".format(
                printable_bad_files_list)
        else:
            bad_files = bad_files[:max_printable]
            printable_bad_files_list = "\n".join(bad_files)
            self._failed_msg = "Warning: this is important if you are about to perform scale in/out or upgrade:\n" \
                               "more then {} file/dirs have permissions issues,\n" \
                               "for example, the following file/dirs do not have read permissions for others:\n {} ".format(
                max_printable, printable_bad_files_list)
        return False


class validate_three_controllers(Validator):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "validate_three_controllers_exist"
        self._title = "Verify that system has 3 controllers"
        self._failed_msg = "TBD"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.RISK_NO_HIGH_AVAILABILITY, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        controllers = gs.get_host_executor_factory().get_host_executors_by_roles([Objectives.CONTROLLERS])
        controllers_count = len(controllers)
        if controllers_count < 3:
            self._failed_msg = "There are just {} controllers in the system. 3 controllers are required!".format(
                controllers_count)
            return False
        return True


class UniformBaremetalPropertiesValidation(Validator):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "Baremetal host properties checker"
        self._title = "Check that the Hosts Baremetal having the same properties per type"
        self._failed_msg = "We have one or more host is not unified\n"
        self._severity = Severity.WARNING
        self._is_pure_info = False
        self._implication_tags = [ImplicationTag.NOTE]

    def is_validation_passed(self):

        servers_list_cmd = "source {}; openstack baremetal node list -f json".format(
            self.system_utils.get_stackrc_file_path())
        baremetal_properties_cmd = "source {}, openstack baremetal node show {} -f json"
        server_list_out = self.get_output_from_run_cmd(servers_list_cmd
                                                       , add_bash_timeout=True)
        servers_list = json.loads(server_list_out)
        controllers_properties_count_list = []
        controllers_properties = {}
        storages_properties_count_list = []
        storages_properties = {}

        for server in servers_list:
            server_name = server["Name"]
            server_properties_out = self.get_output_from_run_cmd(baremetal_properties_cmd.format(
                self.system_utils.get_stackrc_file_path(), server_name), add_bash_timeout=True)
            server_properties = json.loads(server_properties_out)
            server_class = server_properties["resource_class"]
            instance_info = server_properties["instance_info"]
            properties_len = len(server_properties["properties"])
            properties = server_properties["properties"]

            if "ontrolle" in server_class:
                controllers_properties_count_list.append(properties_len)
                controllers_properties[server_name] = properties
            if "torrag" in server_class:
                storages_properties_count_list.append(properties_len)
                storages_properties[server_name] = properties

        result = True
        msg = "\nOne or more {} nodes have additional or fewer properties, please check/compare using the below command: \n\nopenstack baremetal node show <server#>\n#This could be caused by a human mistake\n"
        if len(set(controllers_properties_count_list)) > 1:
            result = False
            self._failed_msg = self._failed_msg + msg.format("controller")

        if len(set(storages_properties_count_list)) > 1:
            result = False
            self._failed_msg = self._failed_msg + msg.format("storage")

        return result


class RabbitmqBaseClass(Validator):
    RABBITMQ_PORT = '5672'

    def Rabbitmqhealthcheck(self):
        docker_or_podman = adapter.docker_or_podman()
        if gs.get_version() >= Version.V25:
            cmd = (
                "sudo {docker_or_podman} exec $(sudo {docker_or_podman} ps -f name=rabbit -q) rabbitmq-diagnostics -q ping".
                format(docker_or_podman=docker_or_podman))
            return_code, RabbitMQStatus, err = self.run_cmd(cmd, add_bash_timeout=True)
            if "succeeded" not in RabbitMQStatus or return_code != 0:
                self._failed_msg = 'RabbitMQ is not working:\n{}'.format(RabbitMQStatus)
                self._severity = Severity.ERROR
                return False
            return True
        else:
            linux_cmd = "sudo netstat  -antplu | grep -i beam.smp | grep ':{}'".format(self.RABBITMQ_PORT)
            return_code, linux_cmd_out, err = self.run_cmd(linux_cmd)
            # here linux_cmd_out will be in unicode format
            if not linux_cmd_out:
                self._failed_msg = "Rabbitmq not running + {}".format(err)
                return False
            pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5})\s'
            matches = re.findall(pattern, linux_cmd_out)
            # matches will be in list and each eliemnt will have 7 rows and will filter only 5672 entry frome each elliment.
            desired_part = [match for match in matches if match.endswith(self.RABBITMQ_PORT)]
            # since all desired_part will have only ip:5672 , we can pic only one entry for our test.
            curl_cmd = 'curl http://{}'.format(desired_part[0])
            cmd = "sudo {docker_or_podman} exec $(sudo {docker_or_podman} ps -f name=rabbit -q) {curl_cmd}".format(
                docker_or_podman=docker_or_podman, curl_cmd=curl_cmd)
            return_code, RabbitMQStatus, err = self.run_cmd(cmd, add_bash_timeout=True)
            if 'AMQP' in RabbitMQStatus:
                cmd = "sudo {docker_or_podman} exec `sudo {docker_or_podman} ps --filter name=rabbit --format '{{{{.Names}}}}'` rabbitmqctl node_health_check". \
                    format(docker_or_podman=docker_or_podman)
                return_code, RabbitMQStatus, err = self.run_cmd(cmd, add_bash_timeout=True)
            else:
                self._failed_msg = 'RabbitMQ port {} is not responding {}'.format(self.RABBITMQ_PORT, RabbitMQStatus)
                self._severity = Severity.ERROR
                return False
            if "Health check passed" not in RabbitMQStatus or return_code != 0:
                self._failed_msg = 'RabbitMQ is not working:\n{}'.format(RabbitMQStatus)
                self._severity = Severity.ERROR
                return False
            return True


class RabbitMQCheckOnUC(RabbitmqBaseClass):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "rabbitmq_check_on_uc"
        self._title = "RabbitMQ check on UnderCloud"
        self._failed_msg = "RabbitMQ on UnderCloud is not working!"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        self.Version = Version.V19A
        output = self.Rabbitmqhealthcheck()
        if output == True:
            return True
        else:
            return False


class RabbitMQCheckOnControllers(RabbitmqBaseClass):
    objective_hosts = [Objectives.CONTROLLERS]

    def set_document(self):
        self._unique_operation_name = "rabbitmq_check_on_controllers"
        self._title = "RabbitMQ check on controller"
        self._failed_msg = "RabbitMQ on controller is not working!"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        self.Version = Version.V19
        output = self.Rabbitmqhealthcheck()
        if output == True:
            return True
        else:
            return False


class RabbitMQQueueCheck(Validator):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "rabbitmq_queue_check"
        self._title = "RabbitMQ queue checks"
        self._failed_msg = "RabbitMQ queue is not working!"
        self._severity = Severity.CRITICAL
        self.passed = False
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        CBIS_version = gs.get_version()
        if CBIS_version <= Version.V19:
            return_code, ip, err = self.run_cmd(
                "sudo cat /etc/rabbitmq/rabbitmq.config | grep ip | awk -F'\"' '{ print $2 }'")
            return_code, username, err = self.run_cmd(
                "sudo cat /etc/rabbitmq/rabbitmq.config | grep default_user | awk -F'\"' '{ print $2 }'")
            return_code, password, err = self.run_cmd(
                "sudo cat /etc/rabbitmq/rabbitmq.config | grep default_pass | awk -F'\"' '{ print $2 }'")

        else:
            docker_or_podman = adapter.docker_or_podman()
            return_code, ip, err = self.run_cmd(
                "sudo {docker_or_podman} exec `sudo {docker_or_podman} ps --filter name=rabbit --format '{{{{.Names}}}}'` "
                "cat /etc/rabbitmq/rabbitmq.config | grep tcp_listeners | awk -F'\"' '{{ print $2 }}'".format(
                    docker_or_podman=docker_or_podman)
                , add_bash_timeout=True)
            return_code, username, err = self.run_cmd(
                "sudo {docker_or_podman} exec `sudo {docker_or_podman} ps --filter name=rabbit --format '{{{{.Names}}}}'` "
                "cat /etc/rabbitmq/rabbitmq.config | grep default_user | awk -F'\"' '{{ print $2 }}'".format(
                    docker_or_podman=docker_or_podman)
                , add_bash_timeout=True)
            return_code, password, err = self.run_cmd(
                "sudo {docker_or_podman} exec `sudo {docker_or_podman} ps --filter name=rabbit --format '{{{{.Names}}}}'` "
                "cat /etc/rabbitmq/rabbitmq.config | grep default_pass | awk -F'\"' '{{ print $2 }}'".format(
                    docker_or_podman=docker_or_podman)
                , add_bash_timeout=True)

        ip = ip.strip()
        username = username.strip()
        password = password.strip()

        credentials = pika.PlainCredentials(username, password)
        connection = pika.BlockingConnection(pika.ConnectionParameters(ip, 5672, '/', credentials))
        channel = connection.channel()
        channel.queue_declare(queue='hello')
        channel.basic_publish(exchange='', routing_key='hello', body='Hello World!')

        # print(" [x] Sent 'Hello World!'")

        def callback(ch, method, properties, body):
            # print(" [x] Received %r" % body)
            self.passed = True
            connection.close()

        auto_ack = True
        #basic_consume(queue, on_message_callback, auto_ack=False, exclusive=False, consumer_tag=None, arguments=None, callback=None)
        channel.basic_consume('hello',
                              callback,
                              auto_ack)

        # print(' [*] Waiting for messages.')
        channel.start_consuming()
        time.sleep(1)
        if self.passed:
            return True
        else:
            self._failed_msg = "The message was not received! please check RabbitMQ connections"
            return False


class RabbitMQQueueNotHuge(Validator):
    objective_hosts = [Objectives.CONTROLLERS]

    def set_document(self):
        self._unique_operation_name = "rabbitmq_queue_not_huge"
        self._title = "Checks that RabbitMQ notification queues are smaller than 100k"
        self._failed_msg = "RabbitMQ notification queues are bigger than 100k"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]

    def is_validation_passed(self):
        queue_list = []
        rbmq_cmd = "rabbitmqctl list_queues name consumers messages | grep notifications"
        if gs.get_version() < Version.V19:
            cmd = 'sudo {}'.format(rbmq_cmd)
        else:
            docker_or_podman = adapter.docker_or_podman()
            cmd = "sudo {docker_or_podman} exec $(sudo {docker_or_podman} ps -f name=rabbitmq-bundle -q) {rbmq_cmd}".format(
                docker_or_podman=docker_or_podman, rbmq_cmd=rbmq_cmd)
        out = self.get_output_from_run_cmd(cmd, add_bash_timeout=True)
        if out:
            lines = out.split('\n')
            for line in lines:
                if line:
                    notification_name = line.split()[0]
                    queue_size = line.split()[2]
                    try:
                        queue_size = int(queue_size)
                    except ValueError:
                        self._set_cmd_info(cmd, 30, 1, queue_size, "")
                        raise UnExpectedSystemOutput(ip=self._host_executor.ip,
                                                     cmd=cmd,
                                                     output="expected int found '{}' in line '{}'".
                                                     format(queue_size, line))
                    if queue_size > 100000:
                        queue_list.append(notification_name)
            if queue_list:
                self._failed_msg = "The following queues has more than 100k: {}".format(queue_list)
                return False
        else:
            self._failed_msg = "Notification queue was not found, validation did not run"
            return False
        return True


class MySQLDirectoryNotLarge(Validator):
    objective_hosts = [Objectives.CONTROLLERS]
    MYSQL_MAX_SIZE = 50

    def set_document(self):
        self._unique_operation_name = "mysql_directory_not_large"
        self._title = "Checks that MySQL directory size is smaller than {}GB".format(self.MYSQL_MAX_SIZE)
        self._failed_msg = "/var/lib/mysql directory size is larger than {}GB".format(self.MYSQL_MAX_SIZE)
        self._severity = Severity.CRITICAL
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]
        self._implication_tags = [ImplicationTag.RISK_RESOURCE_CLEANING_RECOMMENDED]

    def is_validation_passed(self):
        cmd = 'sudo du -sh /var/lib/mysql'
        out = self.get_output_from_run_cmd(cmd, add_bash_timeout=True)
        out = out.split()
        if "G" in out[0]:
            if float(out[0][:-1]) >= self.MYSQL_MAX_SIZE:
                self._failed_msg = "/var/lib/rabbitmq directory size is larger than {}GB: currently {}".format(
                    self.MYSQL_MAX_SIZE, out[0])
                return False
        return True


class RabbitMQDirectoryNotLarge(Validator):
    objective_hosts = [Objectives.CONTROLLERS]
    RABBITMQ_MAX_SIZE = 1

    def set_document(self):
        self._unique_operation_name = "rabbitmq_directory_not_large"
        self._title = "Checks that RabbitMQ directory size is smaller than {}GB".format(self.RABBITMQ_MAX_SIZE)
        self._failed_msg = "/var/lib/rabbitmq directory size is larger than {}GB".format(self.RABBITMQ_MAX_SIZE)
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.RISK_RESOURCE_CLEANING_RECOMMENDED]

    def is_validation_passed(self):
        cmd = 'sudo du -sh /var/lib/rabbitmq'
        out = self.get_output_from_run_cmd(cmd, add_bash_timeout=True)
        out = out.split()

        if "G" in out[0]:
            if float(out[0][:-1]) >= self.RABBITMQ_MAX_SIZE:
                self._failed_msg = "/var/lib/rabbitmq directory size is larger than {}GB: currently {}".format(
                    self.RABBITMQ_MAX_SIZE, out[0])
                return False
        return True


class RabbitMQConnectionPoolLimitCheck(Validator):
    objective_hosts = [Objectives.CONTROLLERS]

    def set_document(self):
        self._unique_operation_name = "rabbitmq_connection_pool_limit_check"
        self._title = "Checks that RabbitMQ reached connection pool limit"
        self._failed_msg = "RabbitMQ reached connection pool limit"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        cmd = "sudo grep 'Connection pool limit exceeded:' /var/log/containers/nova/nova-conductor.log"
        return_code, out, err = self.run_cmd(cmd, add_bash_timeout=True)
        if out == "":
            return True
        else:
            out = out.splitlines()
            self._failed_msg = "RabbitMQ reached connection pool limit: {}".format(out[-1])
            return False


class MYSQLCheck(Validator):
    objective_hosts = [Objectives.CONTROLLERS, Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "mysql_check"
        self._title = "MYSQL checks"
        self._failed_msg = "Connection to MySQL is failing. This needs immediate attention"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        CBIS_version = gs.get_version()
        mysql_password = self.get_output_from_run_cmd(
            "sudo /bin/hiera -c /etc/puppet/hiera.yaml mysql::server::root_password")
        password = mysql_password.strip()
        if password == 'nil':
            cmd = 'sudo mysql -u root -e "use mysql; show tables"'
        else:
            cmd = 'sudo mysql -u root -p{} -e "use mysql; show tables"'.format(password)
            if CBIS_version >= Version.V22:
                mysql_cmd = cmd.partition(' ')[2]
                if Objectives.UC in self.get_host_roles():
                    container_name = 'mysql'
                else:
                    container_name = 'galera-bundle'
                cmd = "sudo podman exec -it $(sudo podman ps -f name={} -q) {}".format(container_name, mysql_cmd)
        tables = self.get_output_from_run_cmd(cmd)
        tables = tables.split("\n")
        if tables:
            return True
        else:
            self._failed_msg = 'Connection to MySQL is failing. This needs immediate attention'
            self._severity = Severity.ERROR
            return False


class check_haproxy(Validator):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.CONTROLLERS]
    }

    def set_document(self):
        self._unique_operation_name = "haproxy_keystone_admin_check"
        self._title = "Verify keystone has proper URLs in haproxy"
        self._failed_msg = "Keystone is missing haproxy configuration."
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]
        self._is_clean_cmd_info = True

    def is_validation_passed(self):
        public_virtual_ip = self.get_output_from_run_cmd(
            "/usr/bin/sudo /usr/bin/hiera tripleo::haproxy::public_virtual_ip")
        line = "  bind {}:13357 transparent ssl crt /etc/pki/tls/private/overcloud_endpoint.pem" \
            .format(public_virtual_ip.splitlines()[0])
        out = self.get_output_from_run_cmd(
            "/usr/bin/sudo /usr/bin/cat /var/lib/config-data/puppet-generated/haproxy/etc/haproxy/haproxy.cfg")
        if line in out:
            return True
        else:
            return False


class check_haproxy_config_valid(Validator):
    objective_hosts = [Objectives.CONTROLLERS]

    def set_document(self):
        self._unique_operation_name = "haproxy_config_valid"
        self._title = "Verify if haproxy config is valid"
        self._failed_msg = "Please repair the haproxy config file."
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]

    def is_validation_passed(self):
        if gs.get_version() >= Version.V22:
            cmd = "sudo podman exec $(sudo podman ps -f name=haproxy-bundle -q) haproxy -c -V -f /etc/haproxy/haproxy.cfg"
        else:
            cmd = "sudo docker exec $(sudo docker ps -f name=haproxy-bundle -q) haproxy -c -V -f /etc/haproxy/haproxy.cfg"
        # note : -c check mode : only check config files and exit
        status, out, err = self.run_cmd(cmd, add_bash_timeout=True)
        if status != 0:
            self._failed_msg = "haproxy isn't running"
            return False
        if gs.get_version() >= Version.V22:
            err = out
        list_error = err.split("\n")
        HARMLESS_WARNINGS = ["HTTP log/header format not usable with proxy",
                             "Setting tune.ssl.default-dh-param to 1024 by default"]
        for error in list_error:
            if "[ALERT]" in error:
                self._severity = Severity.CRITICAL
                return False
            elif "[WARNING]" in error:
                ignore_warning = False
                for harmless_warning in HARMLESS_WARNINGS:
                    if harmless_warning in error:
                        ignore_warning = True
                        break
                if not ignore_warning:
                    return False
        return True


class security_hardening_info(InformatorValidator):
    objective_hosts = [Objectives.HYP]

    def set_document(self):
        self._is_pure_info = True
        self._unique_operation_name = "security_hardening_info"
        self._title_of_info = "Check if any security hardening tasks applied on this enviroment"
        self._system_info = ""
        self._is_highlighted_info = True

    def get_system_info(self):
        security_tasks_set = set()
        security_hardening_cmd = "sudo grep 'validating name' /var/log/cbis/api.log | grep -i Security | grep  True | sort -u"
        security_tasks = self.get_output_from_run_cmd(security_hardening_cmd)
        for line in security_tasks.split('\n'):
            line_s = line.split(':')
            if len(line_s) > 2:
                condition = line_s[4]
                validation_name = line_s[3]
                out = validation_name.split()[0] + ": " + condition.split()[0]
                security_tasks_set.add(out)
        if len(security_tasks_set) > 0:
            security_tasks_set = "\n".join(security_tasks_set)
            self._system_info = "\n\nThe applied security hardening tasks: \n" + "----------------------------------------\n" + security_tasks_set
        else:
            self._system_info = "No security hardening tasks found"

        return self._system_info

    def sort_file_tracker_timing(self, hosts_diff_list):
        sorted_file_tracker_diff = sorted(hosts_diff_list, key=lambda d: d['modify timestamp'], reverse=True)
        return sorted_file_tracker_diff


class CheckMaxProcessesForKeystone(Validator):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "check_max_processes_for_keystone"
        self._title = "Check max processes for keystone"
        self._failed_msg = "Error: Exception KeyError\n\nThis error indicates that there aren't enough processes for keystone to handle the requests\n\nRecovery steps:\n\n1. Restore the UC backup taken before starting Scale In/Out\n2. Edit the following parameters processes, threads in following files:\n\n10-keystone_wsgi_admin.conf\n10-keystone_wsgi_main.conf\n\n3. Restart keystone and keystone_cron containers on the UC\n4. Retry scale In/Out"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        path = "/var/log/containers/httpd/keystone"
        if gs.get_version() in [Version.V18_5, Version.V19]:
            path = "/var/log/httpd"
        keystone_wsgi_error_log = "keystone_wsgi_main_error.log"
        if gs.get_version() > Version.V20:
            keystone_wsgi_error_log = "keystone_wsgi_error.log"
        log_search_dict = {
            "error_log": "[mpm_prefork:error] *.* AH00161:",
            keystone_wsgi_error_log: "Exception KeyError *.* in <function remove at"
        }
        for file_name, pattern in list(log_search_dict.items()):
            file_path = os.path.join(path, file_name)
            if not self.file_utils.is_file_exist(file_path):
                self._failed_msg = "{} not found".format(file_path)
                return False
            cmd = 'sudo grep -n -E "{pattern}" {file_path} | grep -v \'grep\' | tail -1'.format(pattern=pattern,
                                                                                                file_path=file_path)
            return_code, out, err = self.run_cmd(cmd, timeout=90, add_bash_timeout=True)
            if return_code == 2 or out == '':  # if not found pattern
                continue
            log_datetime = self.get_log_line_datetime(out)
            if log_datetime:
                if not self.is_operation_passed_after_error_log(log_datetime):
                    return False
        return True

    def is_operation_passed_after_error_log(self, log_datetime):
        operation_timing_date_format = "%Y-%m-%d %H:%M:%S"
        operations_datetime = None
        operation_timing = Operation_timing_info(self)
        try:
            operations_datetime = operation_timing.get_operations_datetime()
        except NoSuitableHostWasFoundForRoles:
            pass
        operations_keys = ['scale_in', 'scale_out', 'controller_replacement']
        if not any(key in operations_datetime for key in operations_keys):
            return True
        for operation_name in operations_keys:
            if operations_datetime.get(operation_name):
                for operation in operations_datetime[operation_name]:
                    if operation['start_time'] == '':
                        raise ValueError("operation start time should be in date format")
                    if log_datetime <= datetime.strptime(operation['start_time'], operation_timing_date_format):
                        if operation['status'] == 'Passed':
                            return True
        return False

    def get_log_line_datetime(self, line):
        tmp_lines = line.split(":")
        formated_line = line.replace(tmp_lines[0] + ":", "")
        found_date, date_format, short_date_format = PythonUtils.find_dates(formated_line)
        if found_date is not None:
            match = re.sub('[.][0-9]+', '', found_date)
            return datetime.strptime(match, "%a %b %d %H:%M:%S %Y")
        found_date, date_format, short_date_format = PythonUtils.find_dates(line)
        if found_date is not None:
            match = re.sub(r'\.\d+', '', found_date)
            return datetime.strptime(match, "%a %b %d %H:%M:%S %Y")


class OvercloudrcPasswordCollector(DataCollector):
    objective_hosts = [Objectives.CONTROLLERS]

    def collect_data(self):
        oc_password = None
        password_cmd = 'grep "^[^#;]" /home/cbis-admin/overcloudrc | grep -im1 OS_PASSWORD'
        out = self.get_output_from_run_cmd(password_cmd)
        if "ansible-vault" in out:
            oc_password = self.system_utils.get_ansible_vault_decrypted_password("CBIS.openstack_deployment",
                                                                                 "admin_password",
                                                                                 "/usr/share/cbis/data/user_config.yaml")
        if not oc_password:
            oc_password = CheckOvercloudrcPasswdOnCbisCluster.get_split_output(out)
        return oc_password


class CheckOvercloudrcPasswdOnCbisCluster(Validator):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "CheckOvercloudrcPasswdOnCbisCluster"
        self._title = "check overcloudrc passwd on cbis cluster"
        self._failed_msg = ""
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]
        self._is_clean_cmd_info = True

    @staticmethod
    def get_split_output(out):
        return out.strip().split('=')[1].strip("'").strip('"')  # Remove quotes since it's not meter
        # if pass wrapped with quotes

    def is_validation_passed(self):
        res = self.run_data_collector(OvercloudrcPasswordCollector)
        uc_pass = self._get_uc_password()
        count = 0
        failed = []
        for controller in res:
            if res[controller] == uc_pass:
                count += 1
            else:
                failed.append(controller)
        if count == len(res):
            return True
        else:
            self._failed_msg = "Check the overcloudrc password on undercloud and controllers. There seems to be a discrepancy between undercloud and {}".format(
                failed)
            return False

    def _get_uc_password(self):
        uc_password = None
        password_cmd = 'grep "^[^#;]" {} | grep -im1 OS_PASSWORD'.format(self.system_utils.get_overcloudrc_file_path())
        out = self.get_output_from_run_cmd(password_cmd)
        if "ansible-vault" in out:
            uc_password = self.system_utils.get_ansible_vault_decrypted_password("CBIS.openstack_deployment",
                                                                                 "admin_password",
                                                                                 "/home/stack/user_config.yaml")
        if not uc_password:
            uc_password = CheckOvercloudrcPasswdOnCbisCluster.get_split_output(out)
        return uc_password


class VerifyUnercloudHostname(Validator):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "verify_uc_hostname"
        self._title = "Verify Undercloud hostname"
        self._failed_msg = "Undercloud hostname should be 'undercloud'"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        uc_host_name = self.get_host_name()
        if uc_host_name != 'undercloud':
            self._failed_msg += " - currently '{}' is configured".format(uc_host_name)
            return False
        else:
            return True


class ValidateBMCPasswordValidAndSync(Validator):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "validate_bmc_password_valid_and_sync"
        self._title = "Validation of IPMI password valid and sync"
        self._failed_msg = ""
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._is_clean_cmd_info = True
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        cbis_version = gs.get_version()
        find_path = 'sudo find /home/stack -iname "hosts.yaml"'
        path = self.get_output_from_run_cmd(find_path)
        if not path:
            raise UnExpectedSystemOutput(ip=self.get_host_ip(), cmd=find_path, output=path,
                                         message="Failed to find /home/stack/hosts.yaml")
        path = path.split()[0].strip()
        cmd_out = self.get_output_from_run_cmd("cat {path}".format(path=path))
        try:
            data = PythonUtils.yaml_safe_load(cmd_out)
            server_count = len(data['nodes'])
            servers_details = []
            for node_idx in range(0, server_count):
                each_server_details = [data['nodes'][node_idx][j] for j in ['pm_user', 'pm_password', 'pm_addr']]
                if "ANSIBLE_VAULT" in each_server_details[1]:
                    decrypted_password = self.system_utils.decrypt_password(each_server_details[1])
                    each_server_details[1] = decrypted_password
                servers_details.append(each_server_details)
            passwd = servers_details[0][1]
            wrong_passwd_servers = []
            for server in servers_details:
                if passwd == server[1]:
                    continue
                else:
                    wrong_passwd_servers.append(server[2])
            if len(wrong_passwd_servers) != 0:
                self._failed_msg += "These IPMI server password's are not in sync {server}".format(
                    server=wrong_passwd_servers)
                self._severity = Severity.CRITICAL
                return False
            for [pm_user, pm_pass, pm_addr] in servers_details:
                if cbis_version >= Version.V24:
                    self.redfish_validate_bmc_password(pm_user, pm_pass, pm_addr)
                else:
                    command = "ipmitool -I lanplus -U {pm_user} -P '{password}' -H {pm_addr} power status" \
                        .format(pm_user=pm_user, password=pm_pass, pm_addr=pm_addr)
                    return_code, out, err = self.run_cmd(command, timeout=40, add_bash_timeout=True)
                    self.validate_power_response(return_code, out, err)
                if self._failed_msg:
                    return False
            return True
        except yaml.YAMLError as err:
            self._failed_msg += err
            return False

    def redfish_validate_bmc_password(self, pm_user, pm_pass, pm_addr):
        if PythonUtils.is_ipv6(pm_addr):
            pm_addr = "[{}]".format(pm_addr)
        assert self._is_clean_cmd_info, "'self._is_clean_cmd_info' must be True, but found it to be False"
        redfish_out = self.get_output_from_run_cmd(
            'curl --max-time 40 -s -k -u {pm_user}:"{password}" -H "Content-Type: '
            'application/json" https://{pm_addr}/redfish/v1/'.format(
                pm_user=pm_user, password=pm_pass, pm_addr=pm_addr))
        if not redfish_out:
            self._failed_msg += "Error encountered while retrieving data from Redfish API\n"
            return
        redfish_systems_url = "https://{pm_addr}{system}".format(pm_addr=pm_addr,
                                                                 system=json.loads(redfish_out)["Systems"]["@odata.id"])
        out = self.get_output_from_run_cmd('curl --max-time 40 -s -k -u {pm_user}:"{password}" -H "Content-Type: '
                                           'application/json" {redfish_systems_url}'.format(
            pm_user=pm_user, password=pm_pass, redfish_systems_url=redfish_systems_url))
        out_dict = json.loads(out)
        members_identities = [member['@odata.id'] for member in out_dict["Members"]]
        for member in members_identities:
            command = "curl --max-time 40 -k -u {pm_user}:'{password}' -X GET" \
                      " https://{pm_addr}{member}?\\$select=PowerState| python -m json.tool" \
                .format(pm_user=pm_user, password=pm_pass, pm_addr=pm_addr, member=member)
            return_code, out, err = self.run_cmd(command)
            self.validate_power_response(return_code, out, err)
            if self._failed_msg:
                return

    def validate_power_response(self, return_code, out, err):
        if return_code == 0 and ("Chassis Power" in out or "PowerState" in out):
            return
        else:
            self._failed_msg += "Problem with getting the response:\n {err}".format(err=err)


class VerifyMACandBondAddress(Validator):
    objective_hosts = [Objectives.CONTROLLERS]

    def set_document(self):
        self._unique_operation_name = "verify_mac_and_bond_address"
        self._title = "Verify MAC and Bond Address"
        self._failed_msg = "Mismatch between MAC and Bond Address"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION, ImplicationTag.ACTIVE_PROBLEM]

    def return_mac_address(self, file):
        mac_addresses = []
        if self.file_utils.is_file_exist(file):
            path = self.get_output_from_run_cmd('cat {}'.format(file))
            lines = path.splitlines()
            for line in lines:
                # Check if the line contains "Permanent HW addr"
                if "Permanent HW addr" in line:
                    # Split the line by ':' to get the part after "Permanent HW addr"
                    parts = line.split(':', 1)
                    if len(parts) > 1:
                        # Extract the MAC address and strip any surrounding whitespace
                        mac_address = parts[1].strip()
                        mac_addresses.append(mac_address)
        return mac_addresses

    def check_ip_val(self, bond, mac_address_ip):
        cmd = "sudo ip link show | grep {} -A1".format(bond)
        ip_val = self.get_output_from_run_cmd(cmd)
        lines = ip_val.splitlines()
        ip_pattern = re.compile(r'link/ether\s+([\dA-Fa-f:.]+)')
        """
        The Above regex will get the Mac address from the following output
        7: ens1f1: <BROADCAST,MULTICAST,SLAVE,UP,LOWER_UP> mtu 9000 qdisc mq master infra-bond state UP group default qlen 1000
            link/ether 88:e9:a4:55:80:d4 brd ff:ff:ff:ff:ff:ff permaddr 88:e9:a4:55:80:d5
            The MAC address 88:e9:a4:55:80:d4 will be captured by the regex.
        """
        ips = []
        faulty_ips = []
        for line in lines:
            # Search for the IP pattern
            match = ip_pattern.search(line)
            if match:
                # Extract the IP address
                ip = match.group(1)
                if ip not in ips:
                    ips.append(ip)

        for ip in ips:
            if ip not in mac_address_ip:
                faulty_ips.append(ip)
        return faulty_ips

    def is_validation_passed(self):
        find_path = ['/proc/net/bonding/infra-bond', '/proc/net/bonding/tenant-bond']
        bond = ["infra-bond", "tenant-bond"]
        for i in range(len(find_path)):
            mac_address_ip = self.return_mac_address(find_path[i])
            if mac_address_ip:
                faulty_ip = self.check_ip_val(bond[i], mac_address_ip)
                if faulty_ip:
                    mac_address_ip_str = ', '.join(mac_address_ip)
                    faulty_ip_str = ', '.join(faulty_ip)
                    self._failed_msg = "Mismatch between MAC: {} and Bond Address: {}".format(mac_address_ip_str,
                                                                                              faulty_ip_str)
                    return False
        return True


class CheckDeploymentServerBlacklist(Validator):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "deployment_server_blacklist_check"
        self._title = "Verify that the deployment server black list does not contain any nodes"
        self._failed_msg = ""
        self._severity = Severity.WARNING
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]
        self._implication_tags = [ImplicationTag.PRE_OPERATION]

    def is_validation_passed(self):
        out = self.get_output_from_run_cmd(
            "source {}; openstack stack show overcloud  | grep DeploymentServerBlacklist".
            format(self.system_utils.get_stackrc_file_path()), timeout=120)
        if "DeploymentServerBlacklist: ''" in out:
            return True

        blacklist_lines = out.splitlines()

        if len(blacklist_lines) > 1:
            nodes = [line.strip() for line in blacklist_lines[1:]]
            self._failed_msg = "Blacklist is not empty, the list include: {}".format(nodes)
            return False

        # If DeploymentServerBlacklist is not found in the output, treat as empty
        return True


class VerifySymlinkForCACert(CheckSymLink):
    objective_hosts = [Objectives.CONTROLLERS]

    def set_document(self):
        self._unique_operation_name = "verify_sym_link_for_cacert_in_podman_containers"
        self._title = "Check symbolic link for cacert.pem in horizon and keystone podman containers"
        self._failed_msg = ""
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        podman_containers = ['keystone', 'horizon']
        link_file = ['/usr/lib/python2.7/site-packages/certifi/cacert.pem']
        symlink_missing_files = []
        result = True
        for container in podman_containers:
            status_code, out, err = self.run_cmd(
                "sudo /usr/bin/podman ps --format '{{{{.Names}}}}' | grep -w {} ".format(container))
            if status_code != 0:
                self._failed_msg += "Failed to find container: {}\n".format(container)
                result = False
            else:
                for file_path in link_file:
                    cmd = 'sudo podman exec -it {} ls -l {} 2>/dev/null'.format(container, file_path)
                    if not self.verify_symlink_for_source_file(cmd, file_path, container):
                        symlink_missing_files.append(file_path)
        if len(symlink_missing_files) > 0:
            result = False
        return result


class VerifyDefaultLibvirtNetwork(Validator):
    objective_hosts = [Objectives.COMPUTES]

    def set_document(self):
        self._unique_operation_name = "verify_default_libvirt_network_not_exist"
        self._title = "Check default libvirt network not exist"
        self._failed_msg = ""
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        cmd = "sudo virsh net-list --name"
        out = self.get_output_from_run_cmd(cmd).splitlines()
        if 'default' in out:
            self._failed_msg += "default network should not exist in virsh network list"
            return False
        return True


class GetARPResponderFromHosts(DataCollector):
    objective_hosts = [Objectives.COMPUTES]

    def collect_data(self):
        cmd = "sudo grep -A 20 '\\[agent\\]' /var/lib/config-data/puppet-generated/neutron/etc/neutron/plugins/ml2/openvswitch_agent.ini | grep '^arp_responder' | head -n1 | cut -d '=' -f2 | tr -d ' '"
        out = self.get_output_from_run_cmd(cmd).strip()
        vm_array = out.splitlines()
        return vm_array

class ValidateARPResponder(Validator):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "validate_arp_responder"
        self._title = "Validation of arp_responder in user_config.yaml"
        self._failed_msg = "Inconsistent arp_responder in user_config.yaml"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._is_clean_cmd_info = True
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]


    def is_validation_passed(self):
        agent_arp_responder = self.run_data_collector(GetARPResponderFromHosts)
        user_config_host = ConfigStore.get_cbis_user_config()['CBIS']['host_group_config']
        user_config = {}
        for host_grp in user_config_host:
            host = user_config_host[host_grp]
            c_host = str(host_grp).lower()
            val = host.get('arp_responder')
            user_config[c_host] = val

        user_config_agent_mismatch = []
        agent_missing = []
        user_config_missing = set()

        for node in agent_arp_responder:
            used_flavor = set()
            try:
                agent_arp_responder[node][0]
            except (IndexError, TypeError):
                agent_arp_responder[node] = ["Missing"]

            ignore_compare = False
            matched_flavor = None
            substring_matches = [flavor for flavor in user_config if flavor in node]
            if substring_matches:
                matched_flavor = max(substring_matches, key=len)
            if matched_flavor:
                used_flavor.add(matched_flavor)
                if str(agent_arp_responder[node][0]) == "Missing":
                    agent_missing.append(node)
                    ignore_compare = True
                if not isinstance(user_config[matched_flavor], bool):
                    user_config_missing.add(matched_flavor)
                    ignore_compare = True
                if not ignore_compare:
                    if str(user_config[matched_flavor]) != str(agent_arp_responder[node][0]):
                        user_config_agent_mismatch.append(node)

        fail = False
        if self._return_user_config_agent_mismatch(user_config_agent_mismatch):
            fail = True
        if self._return_agent_missing(agent_missing):
            fail = True
        if self._return_user_config_missing(user_config_missing):
            fail = True

        return not fail

    def _return_user_config_agent_mismatch(self, mismatch_nodes):
        fail = False
        if mismatch_nodes:
            self._failed_msg += (
                "\n\nThese nodes have an arp_responder setting mismatch between "
                "/home/stack/user_config.yaml on UC and "
                "/var/lib/config-data/puppet-generated/neutron/etc/neutron/plugins/ml2/"
                "openvswitch_agent.ini on the host:\n"
            )
            self._failed_msg += "\n".join(mismatch_nodes)
            fail = True
        return fail

    def _return_agent_missing(self, missing_nodes):
        fail = False
        if missing_nodes:
            self._failed_msg += (
                "\n\nThese nodes have the arp_responder setting missing in "
                "/var/lib/config-data/puppet-generated/neutron/etc/neutron/plugins/ml2/"
                "openvswitch_agent.ini on the node (fix and rerun):\n"
            )
            self._failed_msg += "\n".join(missing_nodes)
            fail = True
        return fail

    def _return_user_config_missing(self, missing_host_groups):
        fail = False
        if missing_host_groups:
            self._failed_msg += (
                "\n\nThese host_groups have the arp_responder setting missing in "
                "/home/stack/user_config.yaml on UC (fix and rerun):\n"
            )
            self._failed_msg += "\n".join(missing_host_groups)
            fail = True
        return fail


class RabbitMQErrorLogValidation(Validator):
    objective_hosts = [Objectives.CONTROLLERS]

    def set_document(self):
        self._unique_operation_name = "rabbitmq_error_log_check"
        self._title = "Checks that RabbitMQ has no logs containing CRASH, partition, or alarm errors today"
        self._failed_msg = "CRASH, partition, or alarm errors found in RabbitMQ today logs:\n"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.SYMPTOM]


    def is_validation_passed(self):
        base_cmd = "sudo {docker_or_podman} exec $(sudo {docker_or_podman} ps -f name=rabbitmq-bundle -q) bash -c {inner_cmd}"
        docker_or_podman = self.get_docker_or_podman()
        find_files_cmd = base_cmd.format(docker_or_podman=docker_or_podman, inner_cmd=""""find /var/log/rabbitmq/ -type f -name '*.log*' -newermt '$(date +%F) 00:00:00'" """)
        out = self.get_output_from_run_cmd(find_files_cmd, add_bash_timeout=True)
        if not out:
            return True
        files = " ".join(out.splitlines())

        count_cmd = base_cmd.format(docker_or_podman=docker_or_podman, inner_cmd=""""grep -Ei 'CRASH|partition|alarm' {files} | wc -l" """.format(files=files))
        out = self.get_output_from_run_cmd(count_cmd, add_bash_timeout=True)
        if out.strip() == "0":
            return True
        find_lines_cmd = base_cmd.format(docker_or_podman=docker_or_podman, inner_cmd=""""grep -Ei 'CRASH|partition|alarm' {files}" """.format(files=files))
        out = self.get_output_from_run_cmd(find_lines_cmd, add_bash_timeout=True)
        self._failed_msg += out
        return False

    def get_docker_or_podman(self):
        return adapter.docker_or_podman()

class RedisMasterRoleAvailability(Validator):
    objective_hosts = [Objectives.CONTROLLERS]

    def set_document(self):
        self._unique_operation_name = "redis_master_availability_check"
        self._title = "Redis Master Node Status Check"
        self._failed_msg = "No Redis Master found in cluster status. This will cause LCM activity failures."
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]


    def is_validation_passed(self):
        cmd = "sudo pcs status | grep redis"
        out = self.get_output_from_run_cmd(cmd)
        if 'Master' not in out:
            return False
        return True

class RabbitMQMessagesLogValidation(Validator):
    objective_hosts = [Objectives.CONTROLLERS]

    def set_document(self):
        self._unique_operation_name = "rabbitmq_messages_log_check"
        self._title = "Check /var/log/messages has no recent RabbitMQ node state errors"
        self._failed_msg = "Recent RabbitMQ-related errors found in /var/log/messages:\n"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.NOTE]

    def is_validation_passed(self):
        today, yesterday = self.get_today_yesterday_dates()
        grep_cmd = "sudo grep -Ei 'Node rabbitmq-bundle-[^ ]+ state is now lost|Removing all rabbitmq-bundle-[^ ]+ attributes for peer' /var/log/messages | grep -Ei '{today}|{yesterday}'".format(today=today, yesterday=yesterday)
        count_cmd = "{} | wc -l".format(grep_cmd)
        out = self.get_output_from_run_cmd(count_cmd)
        if out.strip() == "0":
            return True
        out = self.get_output_from_run_cmd(grep_cmd)
        self._failed_msg += out
        return False

    def get_today_yesterday_dates(self):
        today = datetime.now().strftime('%b %d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%b %d')
        return today, yesterday


class CinderDefaultVolumeType(Validator):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "cinder_default_volume_type"
        self._title = "Check if cinder_default_volume_type in user_config is empty"
        self._failed_msg = "cinder_default_volume_type in user_config should not be empty."
        self._severity = Severity.WARNING
        self._blocking_tags = [BlockingTag.UPGRADE]

    def cinder_default_volume_type(self):
        user_config_host = ConfigStore.get_cbis_user_config()['CBIS']['storage']
        cinder_default_volume_type = user_config_host['cinder_default_volume_type']
        return cinder_default_volume_type

    def is_validation_passed(self):
        if self.cinder_default_volume_type() is None:
            self._failed_msg += " Check point 27 in the confluence page."
            return False
        return True

class ZaqarConfDataCollector(DataCollector):
    objective_hosts = [Objectives.CONTROLLERS, Objectives.UC]

    def _get_timeout_value(self, file_path, grep, regex):
        raw_line = self.file_utils.get_value_from_file(file_path,grep)
        match = re.search(regex, raw_line) if raw_line else None
        return match.group(1) if match else None

    def _find_plugin_py(self):
        python_ver = "3.6" if gs.get_version() == Version.V24 else "2.7"
        return "/usr/lib/python{0}/site-packages/tripleoclient/plugin.py".format(python_ver)

    def collect_data(self):
        results = dict(zaqar_val=None, ttl_val=None)

        results['zaqar_val'] = self._get_timeout_value(
            file_path="/usr/share/openstack-puppet/modules/tripleo/manifests/haproxy.pp",
            grep=r"\$zaqar_ws_timeout_tunnel",
            regex=r"hiera\(.+?,\s*['\"](\d+)['\"]"
        )

        if self.get_host_name() == "undercloud":
            plugin_path = self._find_plugin_py()
            results['ttl_val'] = self._get_timeout_value(
                file_path=plugin_path,
                grep="ttl",
                regex=r"'ttl':\s*(\d+)"
            )

        return results

class ZaqarTimeoutValidation(InformatorValidator):
    objective_hosts = Objectives.UC

    NODE_THRESHOLD = 68
    EXPECTED_VAL = 43200
    NON_CLUSTER_NODES = 2 # UC + HV

    def set_document(self):
        self._unique_operation_name = "zaqar_timeout_check"
        self._title = "Check Zaqar websocket timeout parameters"
        self._failed_msg = ""

        if self._get_node_count() >= self.NODE_THRESHOLD:
            self._is_pure_info = False
            self._failed_msg = "Zaqar websocket timeout parameters not fitting for cluster size\n"
            self._severity = Severity.WARNING
            self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION, ImplicationTag.PRE_OPERATION]
            self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]
        else:
            self._is_pure_info = True
            self._title_of_info = self._title

    def _get_node_count(self):
        return max(0, len(GetInfo.get_setup_host_list()) - self.NON_CLUSTER_NODES)

    def _populate_system_info(self, res):
        if not self._table_system_info.headers:
            self._table_system_info.headers = ["Host", "Parameters"]

        for host, data in res.items():
            info_lines = []
            if data['zaqar_val']:
                info_lines.append("zaqar_ws_timeout: {}".format(data['zaqar_val']))
            if data['ttl_val']:
                info_lines.append("ttl: {}".format(data['ttl_val']))

            if info_lines:
                self._table_system_info.table.append([host, "\n".join(info_lines)])

    def _validate_param(self, host_name, name, value):
        try:
            if int(value) < self.EXPECTED_VAL:
                self._failed_msg += "[{}]\nExpected {} value: {}\nCurrent {} value: {}\n\n".format(host_name,name,self.EXPECTED_VAL, name, value)
                is_valid = False
            else:
                self._failed_msg += "[{}]\nCurrent {} value IS OK: {}\n\n".format(host_name,name, value)
                is_valid = True
        except (ValueError, TypeError):
            self._failed_msg += "[{}]\nInvalid non-numeric value for {}: {}\n\n".format(host_name, name, value)
            return False
        return is_valid

    def is_validation_passed(self):
        res = self.run_data_collector(ZaqarConfDataCollector)

        if self._is_pure_info:
            self._populate_system_info(res)
            return True

        is_passed = True

        for host, data in res.items():
            if not self._validate_param(host,"zaqar timeout", data['zaqar_val']):
                is_passed = False

            if data.get('ttl_val') is not None:
                if not self._validate_param(host, "ttl", data['ttl_val']):
                    is_passed = False

        if not is_passed:
            self._failed_msg += "\nPlease update timeout value(s) to avoid issues during cluster upgrade"

        return is_passed
