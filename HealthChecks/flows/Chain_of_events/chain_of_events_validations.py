from __future__ import absolute_import
import os

from HealthCheckCommon.operations import *
from HealthCheckCommon.validator import InformatorValidator
from flows.ICE.ICEInternalValidations import IsFileTrackerInstalledDataCollector
from flows_of_sys_operations.FileTracker.FileTrackerPaths import FileTrackerPaths, FileTrackerPathsInitiator
from flows.Chain_of_events.operation_timing_info import Operation_timing_info
import traceback
import sys
import datetime
import tools.paths as paths
from tools.date_and_time_utils import DateAndTimeUtils


TIME_FORMAT = '%Y-%m-%d %H:%M:%S'

class FileTrackerUI(InformatorValidator):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.UC],
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MANAGER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.DEPLOYER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.DEPLOYER]
    }

    def set_document(self):
        self._unique_operation_name = "file_tracker_ui"
        self._title = self._title_of_info = "Check if file tracker find diff"
        self._is_pure_info = True
        self._system_info = "File Tracker:\n"

    def is_validation_passed(self):
        collected_diffs_dict = self.get_file_tracker_diff()

        if collected_diffs_dict.get('config_files_diffs'):
            collected_diffs_dict['config_files_diffs'] = self.sort_file_tracker_timing(
                collected_diffs_dict['config_files_diffs'])

        if collected_diffs_dict.get('folders_diffs'):
            collected_diffs_dict['folders_diffs'] = self.sort_file_tracker_timing(collected_diffs_dict['folders_diffs'])

        self._system_info = collected_diffs_dict

        return True

    def get_file_tracker_diff(self):
        FileTrackerPathsInitiator()
        collected_diffs = {}
        hosts_diff_list_for_config_files = []
        hosts_diff_list_for_folders = []
        hosts_diff_list_for_resources = []
        hosts_diff_list_for_commands = []
        num_of_diff_json_files = int(self.get_output_from_run_cmd(
            "sudo ls {} | grep diff.json | wc -l".format(FileTrackerPaths.MAIN_FILE_TRACKER_DIR_PATH)))
        if num_of_diff_json_files > 1:
            self.add_to_validation_log("Having multiple diff.json files")
        if self.file_utils.is_file_exist(FileTrackerPaths.DIFFERENCES_SUMMARY_FILE):
            ice_shared_folder = os.path.abspath(os.path.join(FileTrackerPaths.MAIN_FILE_TRACKER_DIR_PATH, os.pardir))
            self.file_utils.change_file_owner(self._host_executor.user_name, ice_shared_folder)
            self.file_utils.change_file_owner(self._host_executor.user_name, FileTrackerPaths.MAIN_FILE_TRACKER_DIR_PATH)
            with self.file_utils.with_file_permissions(FileTrackerPaths.DIFFERENCES_SUMMARY_FILE, "444"):
                with open(FileTrackerPaths.DIFFERENCES_SUMMARY_FILE, 'r') as f:
                    try:
                        current_diff = json.load(f)
                    except ValueError:
                        e_type, e_value, e_traceback = sys.exc_info()
                        ex = ''.join(traceback.format_exception(e_type, e_value, e_traceback))
                        output = '\n'.join(['The value is not in JSON format', ex])
                        raise UnExpectedSystemOutput(ip=self._host_executor.ip, cmd="json.load({})".format(f),
                                                     output=output)
            if current_diff:
                for run in current_diff:
                    for host in run:
                        for diff in run[host]:
                            if diff.get('file name') != None and not diff.get('folder path'):
                                host_diff = self._set_fields_for_config_files(host, diff)
                                hosts_diff_list_for_config_files.append(host_diff)
                            elif diff.get('resource name'):
                                host_diff = self._set_fields_for_resources(diff)
                                hosts_diff_list_for_resources.append(host_diff)
                            elif diff.get('added / deleted'):
                                host_diff = self._set_fields_for_folders(host, diff)
                                hosts_diff_list_for_folders.append(host_diff)
                            elif diff.get('command'):
                                host_diff = self._set_fields_for_commands(host, diff)
                                hosts_diff_list_for_commands.append(host_diff)
                collected_diffs['config_files_diffs'] = hosts_diff_list_for_config_files
                collected_diffs['resources_diffs'] = list(reversed(hosts_diff_list_for_resources))
                collected_diffs['folders_diffs'] = hosts_diff_list_for_folders
                collected_diffs['commands_diffs'] = list(reversed(hosts_diff_list_for_commands))
        elif self._is_ft_installed():
            ft_start_time = self._get_ft_start_time()
            collected_diffs['no_diffs'] = "No changes found in File Tracker runs, since the {}".format(ft_start_time)
        return collected_diffs

    def sort_file_tracker_timing(self, hosts_diff_list):
        sorted_file_tracker_diff = sorted(hosts_diff_list, key=lambda d: d['modify timestamp'], reverse=True)
        return sorted_file_tracker_diff

    def _set_fields_for_config_files(self, host, diff):
        host_diff = {}
        host_diff['host name'] = host
        host_diff['full path'] = diff['full path']
        host_diff['is file exist'] = diff['is file exist']
        host_diff['modify timestamp'] = diff['modify timestamp']
        host_diff['changes'] = ''
        for row in diff['changes']:
            host_diff['changes'] += row + '\n'
        return host_diff

    def _set_fields_for_folders(self, host, diff):
        host_diff = {}
        host_diff['host name'] = host
        host_diff['folder path'] = diff['folder path']
        host_diff['file name'] = diff['file name']
        host_diff['modify timestamp'] = diff['modify timestamp']
        host_diff['added / deleted'] = diff['added / deleted']

        return host_diff

    def _set_fields_for_commands(self, host, diff):
        host_diff = {}
        host_diff['host name'] = host
        host_diff['command'] = diff['command']
        host_diff['estimated modify timestamp'] = diff['estimated modify timestamp']
        host_diff['changes'] = ''
        for row in diff['changes']:
            host_diff['changes'] += row + '\n'
        return host_diff

    def _set_fields_for_resources(self, diff):
        host_diff = {}
        host_diff['resource name'] = diff['resource name']
        host_diff['resource type'] = diff['resource type']
        host_diff['namespace'] = diff['namespace']
        host_diff['is resource exist'] = diff['is resource exist']
        host_diff['estimated modify timestamp'] = diff['estimated modify timestamp']
        host_diff['changes'] = ''
        for row in diff['changes']:
            host_diff['changes'] += row + '\n'
        return host_diff

    def _is_ft_installed(self):
        res = self.get_first_value_from_data_collector(IsFileTrackerInstalledDataCollector)
        return res['is_installed']

    def _get_ft_start_time(self):
        oldest_ft_log_out = self.get_output_from_run_cmd("sudo ls -tr {} | grep file_tracker.log*".format(FileTrackerPaths.MAIN_FILE_TRACKER_DIR_PATH))
        oldest_ft_log_file_name = oldest_ft_log_out.splitlines()[0]
        oldest_ft_log_file_path = FileTrackerPaths.MAIN_FILE_TRACKER_DIR_PATH + oldest_ft_log_file_name
        first_line_in_log = self.get_output_from_run_cmd("sudo head -1 {}".format(oldest_ft_log_file_path))
        if not first_line_in_log:
            return self.get_output_from_run_cmd("date +'%d-%m-%Y'")
        first_date_in_ft_log = first_line_in_log.split(" ")[0]
        date_in_format = self.get_output_from_run_cmd("date -d '{}' +'%d-%m-%Y'".format(first_date_in_ft_log))

        return date_in_format


class RebootsDataCollector(DataCollector):
    objective_hosts = {Deployment_type.CBIS: [Objectives.HYP, Objectives.ALL_HOSTS],
                       Deployment_type.NCS_OVER_BM: [Objectives.ALL_NODES],
                       Deployment_type.NCS_OVER_VSPHERE: [Objectives.ALL_NODES],
                       Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ALL_NODES]}

    def collect_data(self):
        reboot_attempts = {}
        cmd = 'sudo last reboot -F'
        out = self.get_output_from_run_cmd(cmd)
        for line in out.splitlines():
            reboot_attempt = {}
            reboot_attempt['host_name'] = self.get_host_name()
            if 'reboot' in line:
                reboot_attempt['name'] = 'reboot'
                reboot_attempt['start_time'] = self._get_reboot_timestamp(line)
                reboot_attempts.setdefault("reboot", []).append(reboot_attempt)
        return reboot_attempts

    def _get_reboot_timestamp(self, line_output):
        line_output = line_output.split('still running')[0]
        year = line_output.split(' - ')[0].split()[-1]
        time = line_output.split(' - ')[0].split()[-2]
        day = line_output.split(' - ')[0].split()[-3]
        month = line_output.split(' - ')[0].split()[-4]
        extracted_date_and_time_str = "{} {} {} {}".format(month, day, time, year)
        extracted_date_and_time = datetime.datetime.strptime(extracted_date_and_time_str, '%b %d %H:%M:%S %Y')
        return extracted_date_and_time.strftime(TIME_FORMAT)


class BcmtApiOperationsCNADataCollector(DataCollector):
    objective_hosts = {Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER],
                       Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER]}

    def __init__(self, host_executor=None, source_objective_roles_list=None):
        super(BcmtApiOperationsCNADataCollector, self).__init__(host_executor, source_objective_roles_list)

    def collect_data(self, **kwargs):
        operation_timing = Operation_timing_info(self)
        operations = kwargs['operations']
        operations_timing_res = {}
        for operation in operations:
            if gs.get_deployment_type() not in [eval(key) for key in list(operation['role'].keys())]:
                continue
            operation_timing._operation = operation
            operation_timing._set_role()
            operation_timing_info_mechanism = operation_timing.get_operation_timing_info_mechanism()
            assert operation.get("searched_patterns"), "'searched_patterns' must be initialized for {}".format(
                operation)
            assert operation["searched_patterns"].get("end_time_by_task_id"), \
                "'end_time_by_task_id' must be initialized for {}".format(operation)
            datetimes_list = self.get_all_pods_datetimes_list(operation_timing_info_mechanism)
            operations_timing_res[operation["name"]] = datetimes_list
        return operations_timing_res

    def get_all_pods_datetimes_list(self, operation_timing_info_mechanism):
        pod_list = self.get_output_from_run_cmd(
            "sudo kubectl get pods -l app=bcmt-api -nncms -o=jsonpath='{.items[*].metadata.name}'").split()
        all_pods_datetimes_list = []
        for pod in pod_list:
            cmd = "sudo kubectl logs {} -nncms".format(pod)
            pod_datetimes_list = operation_timing_info_mechanism._create_list_of_times_dicts("< <({})".format(cmd))
            for item in pod_datetimes_list:
                item["log_path"] = cmd
            all_pods_datetimes_list.extend(pod_datetimes_list)
        return all_pods_datetimes_list


class OperationsTimeline(InformatorValidator):
    objective_hosts = {Deployment_type.CBIS: [Objectives.UC],
                       Deployment_type.NCS_OVER_BM: [Objectives.ONE_MANAGER],
                       Deployment_type.NCS_OVER_VSPHERE: [Objectives.DEPLOYER],
                       Deployment_type.NCS_OVER_OPENSTACK: [Objectives.DEPLOYER]}

    def set_document(self):
        self._unique_operation_name = "operation_timing"
        self._title = self._title_of_info = "Check CBIS / NCS operation timing"
        self._is_pure_info = True
        self._system_info = "Operations timeline:\n"

    def is_validation_passed(self):
        operation_timing = Operation_timing_info(self)
        operations_timing_res = operation_timing.get_operations_datetime()
        operations_info_file = paths.SYSTEM_OPERATION_JSON.format('data_collector')
        with open(operations_info_file) as json_file:
            data_collectors_list = json.load(json_file)
        for data_collector in data_collectors_list:
            if gs.get_deployment_type() not in eval(data_collector["deployment_types_list"]):
                continue
            data_collector_operation_res = self.get_data_collector_operation_res(data_collector)
            operations_timing_res = self.add_data_collector_res_to_operations_timing_res(
                data_collector_operation_res, operations_timing_res)
        self._system_info = self.sort_operation_timing_by_start(operations_timing_res)
        return True

    def get_data_collector_operation_res(self, data_collector):
        if data_collector.get("operations"):
            return self.run_data_collector(eval(data_collector["data_collector_name"]),
                                           operations=data_collector.get("operations"))
        else:
            return self.run_data_collector(eval(data_collector["data_collector_name"]))

    def add_data_collector_res_to_operations_timing_res(self, data_collector_operation_res, operations_timing_res):
        if list(data_collector_operation_res.keys()):
            if 'reboot' in data_collector_operation_res[list(data_collector_operation_res.keys())[0]]:
                data_collector_operation_res = self.remove_duplicate_reboots(data_collector_operation_res, operations_timing_res)

        for host in data_collector_operation_res:
            if data_collector_operation_res[host] is not None:
                for operation_name in data_collector_operation_res[host]:
                    operations_timing_res.setdefault(operation_name, []).extend(data_collector_operation_res[host][operation_name])
        return operations_timing_res

    def remove_duplicate_reboots(self, data_collector_operation_res, operations_timing_res):
        for host, host_data in list(data_collector_operation_res.items()):
            reboot_events = host_data.get('reboot', [])
            gracefull_reboots = operations_timing_res.get('gracefull_reboot', [])
            for gracefull_reboot in gracefull_reboots:
                if gracefull_reboot.get('host_name') == host:
                    if not gracefull_reboot.get('start_time'):
                        continue
                    gracefull_reboot_start_time = DateAndTimeUtils.get_datetime_object_by_date_and_time_str(gracefull_reboot.get('start_time'), TIME_FORMAT)
                    gracefull_reboot_end_time = DateAndTimeUtils.get_datetime_object_by_date_and_time_str(
                        gracefull_reboot.get('end_time', datetime.datetime.now().strftime(TIME_FORMAT)), TIME_FORMAT)

                    reboot_events = self._filter_out_graceful_reboot_from_collcted_reboots(reboot_events, gracefull_reboot_start_time, gracefull_reboot_end_time)

            host_data['reboot'] = reboot_events
        return data_collector_operation_res

    def _filter_out_graceful_reboot_from_collcted_reboots(self, reboot_events, gracefull_reboot_start_time, gracefull_reboot_end_time):
        reboot_events = [event for event in reboot_events if
                         datetime.datetime.strptime(event['start_time'], TIME_FORMAT) < gracefull_reboot_start_time or
                         datetime.datetime.strptime(event['start_time'], TIME_FORMAT) > gracefull_reboot_end_time]
        return reboot_events

    def sort_operation_timing_by_start(self, operation_timing):
        list_of_all_operations = []
        for operation_name, list_of_timing in list(operation_timing.items()):
            for attempt in list_of_timing:
                attempt['name'] = operation_name
                for key in ['start_time', 'end_time', 'log_path', 'status']:
                    if not attempt.get(key):
                        attempt[key] = ''
            for attempt in list_of_timing:
                list_of_all_operations.append(attempt)
        sorted_list_of_operations = sorted(list_of_all_operations, key=lambda d: d['start_time'], reverse=True)
        return sorted_list_of_operations
