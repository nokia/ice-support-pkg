from __future__ import absolute_import
from HealthCheckCommon.operations import *
from HealthCheckCommon.validator import Validator
from tools.ConfigStore import ConfigStore
from tools.Info import GetInfo
from tools.system_commands import SystemCommands
from flows.Cbis.user_config_validator.user_config_checks import BaseUserConfigValidator
from flows.Monitoring.btel_flows_ncs import BTELValidationStatusRequirement
from six.moves import range
from collections import defaultdict


class ValidateElkDeployedInLargeSystems(Validator):
    objective_hosts = {Deployment_type.CBIS: [Objectives.UC, Objectives.CONTROLLERS, Objectives.MONITOR]}

    def set_document(self):
        self._unique_operation_name = "validate_elk_is_not_set_local_in_large_set_up"
        self._title = "validate ELK is not installed locally in system that have more than 68 nodes"
        self._failed_msg = "CBIS does not support local deployment of ELK in a more than 68 computes setup.\n" \
                           "Your system is at high risk of resource starvation\n"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]

    def is_prerequisite_fulfilled(self):
        if ConfigStore.get_cbis_user_config()['CBIS']['openstack_deployment'].get('deploy_elk') == False:
            return False
        return True

    def is_validation_passed(self):
        system_size = 0
        monitoring_hosts_amount = 0

        if Objectives.UC in self.get_host_roles():
            all_hosts = GetInfo.get_setup_host_list()  # includes the UN and HYP
            system_size = len(all_hosts) - 2
            for host in all_hosts:
                if 'monitoring' in all_hosts[host]['roles']:
                    monitoring_hosts_amount += 1

        if system_size >= 68:
            self.add_to_validation_log('System has more than 68 nodes')
            try:
                config = ConfigStore.get_cbis_user_config()['CBIS']['openstack_deployment']
                # User_config will have either 'elk_deployment_type' or 'ssc_deployment_type (CBIS24)
                if "elk_deployment_type" in config:
                    deployment_type = config["elk_deployment_type"]
                elif "ssc_deployment_type" in config:
                    deployment_type = config["ssc_deployment_type"]
                else:
                    self._failed_msg += ("There is no valid deployment type found for ELK, "
                                         "Kindly check the user configuration file.")
                    return False

            except UnExpectedSystemOutput as e:
                self._failed_msg = ("Error reading deployment configuration (ELK/SSC). "
                                    "Kindly check configuration structure \n {}").format(e)
                return False
            if deployment_type == "local":
                self.add_to_validation_log('ELK is deployed on local')
                if monitoring_hosts_amount < 3:
                    self._failed_msg += 'Currently configured {} monitoring hosts.\n Your setup has more than 68 computes and ELK is configured on local - three monitoring hosts should be deployed'. \
                        format(monitoring_hosts_amount)
                    return False
                self.add_to_validation_log('System has more than 3 monitoring nodes')
                command = 'sudo du -s /elk'
                if Objectives.MONITOR in self.get_host_roles():
                    elk_size = self.get_output_from_run_cmd(command, add_bash_timeout=True).split()[0]
                    if int(elk_size) == 0:
                        self._failed_msg += 'Size of /elk on {} is {}, while it should be greater than 0 on monitoring host'.format(
                            self._host_executor.host_name, elk_size)
                        return False
                if Objectives.CONTROLLERS in self.get_host_roles():
                    elk_size = self.get_output_from_run_cmd(command, add_bash_timeout=True).split()[0]
                    if int(elk_size) != 0:
                        self._failed_msg += 'Size of /elk on {} is {}, while it should be 0 on controller host'.format(
                            self._host_executor.host_name, elk_size)
                        return False
            else:
                self.add_to_validation_log('ELK is deployed on remote')

        else:
            self.add_to_validation_log('System has less than 68 nodes - no need to verify this validation')
        return True


class ElkDaysRetentionConsistency(Validator):
    objective_hosts = [Objectives.CONTROLLERS]

    def set_document(self):
        self._unique_operation_name = "check_elk_retention_consistency"
        self._title = "Check ELK Retention Days"
        self._failed_msg = "ELK retention days are inconsistent between the indices"
        self._severity = Severity.NOTIFICATION
        self._implication_tags = [ImplicationTag.NOTE]

    def is_prerequisite_fulfilled(self):
        cmd = SystemCommands.is_container_deployed("curator")
        ret_code, out, err = self.run_cmd(cmd)
        return ret_code == 0

    def is_validation_passed(self):
        days_set = set()
        actions_dict = self.get_dict_from_file('/etc/elk/curator/actions.yml', file_format='yaml')
        for action in actions_dict['actions']:
            filters_dicts = actions_dict['actions'][action]['filters']
            for filters_dic in filters_dicts:
                if 'unit_count' in filters_dic:
                    unit_count = int(filters_dic['unit_count'])
                    days_set.add(unit_count)
        return len(days_set) <= 1


class CheckElkFsAccessibleOrNot(Validator):
    objective_hosts = {Deployment_type.NCS_OVER_BM: [Objectives.MANAGERS, Objectives.MONITOR],
                       Deployment_type.NCS_OVER_OPENSTACK: [Objectives.MANAGERS, Objectives.MONITOR],
                       Deployment_type.NCS_OVER_VSPHERE: [Objectives.MANAGERS, Objectives.MONITOR]}

    def set_document(self):
        self._unique_operation_name = "check_elk_fs_accessible_or_not"
        self._title = "Check /elk is accessible or not on Manager/Monitor node"
        self._failed_msg = "please note if you have a monitor node it can be a false positive"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_prerequisite_fulfilled(self):
        has_monitoring_nodes = self._has_monitoring_nodes()
        is_elk_deployed = self._is_elk_deployed()
        if has_monitoring_nodes and is_elk_deployed:
            self.add_to_validation_log("Having monitoring nodes - expect to have /elk on monitoring nodes")
        else:
            self.add_to_validation_log("Don't have monitoring nodes - expect to have /elk on manager nodes")
        return ('monitoring' in self.get_host_roles() or not has_monitoring_nodes) and is_elk_deployed

    def _has_monitoring_nodes(self):
        rc, out, err = self.run_cmd("grep -i 'monitor' /etc/hosts")
        return rc == 0

    def _is_elk_deployed(self):
        if gs.get_deployment_type() == Deployment_type.NCS_OVER_BM:
            if not ConfigStore.get_ncs_bm_conf()['management_deployment'].get("deploy_elk") and \
                    not ConfigStore.get_ncs_bm_conf()['openstack_deployment'].get("deploy_elk"):
                return False
        return True

    def is_validation_passed(self):
        command = 'sudo ls /elk'
        exit_code, out, err = self.run_cmd(command, add_bash_timeout=True)
        if exit_code == 0:
            return True
        else:
            return False


class IsElkDaysRetentionCorrect(BaseUserConfigValidator):
    objective_hosts = [Objectives.CONTROLLERS]

    def __init__(self, ip):
        BaseUserConfigValidator.__init__(self, ip)

    def is_prerequisite_fulfilled(self):
        cmd = SystemCommands.is_container_deployed("curator")
        ret_code, out, err = self.run_cmd(cmd)
        return ret_code == 0

    def _get_unique_operation_name(self):
        return "is_elk_days_retention_correct"

    def _set_document_config_validator(self):
        objective = 'elk_days_retention'
        self._severity = Severity.ERROR
        return objective

    def _get_value_from_config(self):
        to_return = self._get_conf()['CBIS']['openstack_deployment']['elk_keep_data']
        return str(to_return)

    def _get_value_from_system(self):
        unit_count = ''
        actions_dict = self.get_dict_from_file('/etc/elk/curator/actions.yml', file_format='yaml')
        for action in actions_dict['actions']:
            filters_dicts = actions_dict['actions'][action]['filters']
            for filters_dic in filters_dicts:
                if 'unit_count' in filters_dic:
                    unit_count = filters_dic['unit_count']
        return str(unit_count)


class CheckBtelElkPodsCrashingOrNot(BTELValidationStatusRequirement):

    def check_elk_pods_status(self, error_to_grep):
        btel_dict = self.namespace_app_exists_dict()
        count = 0
        for namespace in list(btel_dict.keys()):
            cmd = "sudo kubectl get pods -n {} | grep -i elastic | grep -i master".format(namespace)
            out = self.get_output_from_run_cmd(cmd)
            out_split = out.split()
            for num in range(2, len(out_split), 5):
                if 'Running' not in out_split[num]:
                    cmd = "sudo kubectl logs  {} -n {} | grep -i '{}'".format(out_split[num - 2], namespace,
                                                                              error_to_grep)
                    ex, out, err = self.run_cmd(cmd)
                    if len(out) != 0:
                        count += 1
        return count


class CheckElkPodsCrashWithNoUpAndRunningPrivateAddr(CheckBtelElkPodsCrashingOrNot):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._unique_operation_name = "check_elk_pods_crash_with_no_up_and_running_private_addr"
        self._title = "check whether elk pods crashed with no up-and-running site-local addr found or not"
        self._failed_msg = "please check the elk pods. looks like elk pods crashed due to No up-and-running site-local (private) addresses found error"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.SYMPTOM]

    def is_prerequisite_fulfilled(self):
        return self._is_app_installed('elasticsearch')

    def is_validation_passed(self):
        error_to_grep = 'No up-and-running site-local (private) addresses found'
        count = self.check_elk_pods_status(error_to_grep=error_to_grep)
        if count > 0:
            return False
        else:
            return True


class CheckElkPodsCrashedWithLowMemoryHeapSize(CheckBtelElkPodsCrashingOrNot):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._unique_operation_name = "check_elk_pods_crashed_with_low_memory_heap_size"
        self._title = "check whether elk pods crashed with low memory heap size or not"
        self._failed_msg = "please check the elk pods. looks like elk pods crashed due to low memory heap size. increase vm.max_map_count"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.SYMPTOM]

    def is_prerequisite_fulfilled(self):
        return self._is_app_installed('elasticsearch')

    def is_validation_passed(self):
        error_to_grep = r'max virtual memory areas vm.max_map_count \[[0-9]*\] is too low'
        count = self.check_elk_pods_status(error_to_grep=error_to_grep)
        if count > 0:
            return False
        else:
            return True


class GetCronFromHosts(DataCollector):
    objective_hosts = [Objectives.MANAGERS]

    def collect_data(self):
        cmd = r'sudo crontab -l | grep elk-curator | grep -v "^\s*#"'
        out = self.get_output_from_run_cmd(cmd).strip()
        return out


class ValidateElkCuratorCronTimeIsOffset(Validator):
    objective_hosts = {Deployment_type.NCS_OVER_BM: [Objectives.ONE_MANAGER]}

    def set_document(self):
        self._unique_operation_name = "verify_elk_curator_cron"
        self._title = "Verify cron for elk-curator runs at different times"
        self._failed_msg = "Verification Failed: \n"
        self._severity = Severity.NOTIFICATION
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]

    def is_prerequisite_fulfilled(self):
        if ConfigStore.get_ncs_bm_conf()['management_deployment'].get("deploy_elk") is False:
            return False
        return True

    def is_validation_passed(self):
        out = self.run_data_collector(GetCronFromHosts)
        schedule_to_nodes = defaultdict(list)
        for node, command in out.items():
            schedule = tuple(command.split(' ')[0:5])
            schedule_to_nodes[schedule].append(node)
        duplicates = {schedule: nodes for schedule, nodes in schedule_to_nodes.items() if len(nodes) > 1}
        if duplicates:
            for schedule, nodes in duplicates.items():
                self._failed_msg += "Schedule {} is shared by nodes: {}".format(' '.join(schedule), nodes)
            return False
        else:
            return True
