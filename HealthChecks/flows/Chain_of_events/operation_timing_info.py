from __future__ import absolute_import
import tools.paths as paths
from flows.Chain_of_events.operation_timing_info_single_file_for_attempts_mechanism import OperationTimingInfoSingleFileForAttemptsMechanism
from flows.Chain_of_events.operation_timing_info_file_per_attempt_operation_mechanism import \
    OperationTimingInfoFilePerAttemptOperationMechanism
from flows.Chain_of_events.operation_timing_info_task_id_mechanism import OperationTimingInfoTaskIdMechanism
from tools.ExecutionModule.execution_helper import ExecutionHelper
from tools.date_and_time_utils import DateAndTimeUtils
from tools.lazy_global_data_loader import *
from HealthCheckCommon.log_flows.base_log_issues_finder_flow import *
import json
import re
import tools.sys_parameters as gs
from tools.global_logging import log


class Operation_timing_info():
    TIME_FORMAT = '%Y-%m-%d %H:%M:%S'
    
    def __init__(self, caller_object):
        self._operation = {}
        self._objective_role = None
        self._searched_patterns_type = None
        self._searched_patterns_value = None
        self._caller_operation_object = caller_object

    def _set_role(self):
        deployment_type_class = Deployment_type.__name__
        objectives_class = Objectives.__name__
        regex_deployment_type = r"^{deployment_type_class}\..*".format(deployment_type_class=deployment_type_class)
        regex_objectives = r"^{objectives_class}\..*".format(objectives_class=objectives_class)
        for deployment in self._operation['role']:
            assert re.findall(regex_deployment_type, deployment), \
                "Expected deployment_type in regex format: {}, actual:{}".format(regex_deployment_type, deployment)
            assert re.findall(regex_objectives, self._operation['role'][deployment]), \
                "Expected objectives in regex format: {}, actual:{}".format(
                    regex_objectives, self._operation['role'][deployment])
        deployment_type_key = Deployment_type.get_deployment_type_key_from_value(gs.get_deployment_type())
        assert self._operation['role'].get(deployment_type_key), "{} is not supported for {}".format(
            self._operation["name"], gs.get_deployment_type())
        self._objective_role = eval(self._operation['role'][deployment_type_key])
        assert self._objective_role in Objectives.get_available_types(gs.get_deployment_type()), \
            "{} is not supported for {}".format(self._objective_role, gs.get_deployment_type())
        if ExecutionHelper.is_run_inside_container() and self._objective_role in [Objectives.UC,
                                                                                  Objectives.ONE_MANAGER]:
            self._objective_role = Objectives.ICE_CONTAINER
        assert self._objective_role in Objectives.get_all_single_types(), "{} isn't define on operation {}".format(
            self._objective_role, self._operation['name'])

    def _get_operation_details_dict(self):
        if Deployment_type.is_cbis(gs.get_deployment_type()):
            operations_info_file = paths.SYSTEM_OPERATION_JSON.format('cbis')
        if gs.get_deployment_type() == Deployment_type.NCS_OVER_BM:
            operations_info_file = paths.SYSTEM_OPERATION_JSON.format('cnb')
        if gs.get_deployment_type() in Deployment_type.get_ncs_vsphere_openstack_types():
            operations_info_file = paths.SYSTEM_OPERATION_JSON.format('cna')
        with open(operations_info_file) as json_file:
            operation_details_dict = json.load(json_file)
        return operation_details_dict

    @lazy_global_data_loader
    def get_operations_datetime(self):
        '''
        Example of returned value 'operations_timing_res':
        {'hardening': [{'log_path': u'/var/log/cbis/security_hardening.log', 'status': 'Passed', 'start_time': '2021-06-09 09:59:16', 'log_location': 'hypervisor', 'end_time': '2021-06-09 10:07:11'},
            {'log_path': '/var/log/cbis/security_hardening.log.2021-04-08T14:11:40.010194', 'status': 'Passed', 'start_time': '2021-03-25 17:41:49', 'log_location': 'hypervisor', 'end_time': '2021-03-25 18:39:23'}],
        'undercloud_backup': [{'log_path': '/var/log/cbis/undercloud_backup.log', 'start_time': '2022-04-04 16:31:56', 'log_location': 'hypervisor', 'end_time': '2022-04-04 16:45:14'}],
        'replace_controller': [{'log_path': '/var/log/cbis/replace_controller.log', 'start_time': '', 'log_location': 'hypervisor', 'end_time': ''}]}
        '''
        operation_details_dict = self._get_operation_details_dict()
        operations_timing_res = {}
        cluster_name = ''
        if gs.get_deployment_type() == Deployment_type.NCS_OVER_BM and gs.get_version() >= Version.V22:
            cluster_name = gs.get_cluster_name() + '/'
        for operation in operation_details_dict['operations']:
            missing_operation_fields = {"name", "role", "log_path", "searched_patterns"}.difference(
                set(operation.keys()))
            assert len(missing_operation_fields) == 0, "{} must be initialized for {}".format(missing_operation_fields,
                                                                                              operation)
            self._operation = operation
            self._set_role()
            operation_name = self._operation['name']
            self._update_log_path_list_with_cluster_name(cluster_name)
            operation_timing_info_mechanism = self.get_operation_timing_info_mechanism()
            times_dicts_list = operation_timing_info_mechanism.get_times_dicts_list()
            '''
            Example of times_dicts_list: 
            [{'log_path': '/var/log/cbis/deployment.log', 'status': 'Failed', 'start_time': '2021-03-05 16:00:56', 'log_location': 'hypervisor', 'end_time': '2021-03-05 16:11:59'}, 
            {'log_path': '/var/log/cbis/deployment.log.2021-02-26T12:39:49.770529', 'status': 'Passed', 'start_time': '2021-02-26 17:28:24', 'log_location': 'hypervisor', 'end_time': '2021-02-26 12:39:49'}]
            '''
            if not times_dicts_list:
                if self._operation['is_required']:
                    operation_name = operation_name + '_mandatory_operation'
                    err_msg = self._handle_missing_mandatory_operation()
                    times_dicts_list = [{'log_path': '', 'status': 'log_not_found', 'start_time': '1979-07-18 10:49:35',
                                         'host_name': '', 'end_time': '',
                                         'err_msg': err_msg}]
            if len(times_dicts_list) > 0:
                operations_timing_res[operation_name] = times_dicts_list
            log('times_dicts_list of operation {}:\n{}'.format(operation_name, times_dicts_list))
        self._caller_operation_object.raise_if_no_collector_passed()
        return operations_timing_res

    def _handle_missing_mandatory_operation(self):
        roles = [self._objective_role]
        if not len(gs.get_host_executor_factory().get_connected_host_executors_by_roles(roles)):
            err_details = "No suitable host was found for the roles {}".format(roles)
        else:
            host_name = list(gs.get_host_executor_factory().execute_cmd_by_roles(
                roles=roles, cmd='hostname', timeout=10).values())[0]['out'].strip()
            if len(self._operation['log_path']) == 1:
                one_or_more_logs = 'the following operation log'
            else:
                one_or_more_logs = 'one of the following operation logs'
            err_details = "Haven't found {} {} on {}".format(one_or_more_logs, self._operation['log_path'], host_name)
        err_msg = "The operation '{}' is mandatory on the system.\n\n{}\n\n" \
                  "Note: The environment may not work properly!".format(self._operation['name'], err_details)
        return err_msg

    def get_start_operation_times_as_datetime(self, operation_str_datetime_list):
        return self._get_operation_times_as_datetime(operation_str_datetime_list, "start_time")

    def get_end_operation_times_as_datetime(self, operation_str_datetime_list):
        return self._get_operation_times_as_datetime(operation_str_datetime_list, "end_time")

    def _get_operation_times_as_datetime(self, operation_str_datetime_list, date_key):
        start_dates_list = []
        for times_dict in operation_str_datetime_list:
            if date_key in list(times_dict.keys()):
                start_dates_list.append(times_dict[date_key])
        return DateAndTimeUtils.convert_str_list_to_datetime(start_dates_list, self.TIME_FORMAT)

    def _update_log_path_list_with_cluster_name(self, cluster_name):
        updated_log_path_list = []
        for log_path in self._operation['log_path']:
            updated_log_path_list.append(log_path.format(cluster_name=cluster_name))
        self._operation['log_path'] = updated_log_path_list

    def get_operation_timing_info_mechanism(self):
        if self._operation.get('file_per_attempt_operation') is True:
            operation_timing_info_mechanism = OperationTimingInfoFilePerAttemptOperationMechanism(
                self._objective_role, self._operation, self._caller_operation_object)
        elif self._operation["searched_patterns"].get("end_time_by_task_id"):
            operation_timing_info_mechanism = OperationTimingInfoTaskIdMechanism(self._objective_role,
                                                                                 self._operation,
                                                                                 self._caller_operation_object)
        else:
            operation_timing_info_mechanism = OperationTimingInfoSingleFileForAttemptsMechanism(self._objective_role,
                                                                                                self._operation,
                                                                                                self._caller_operation_object)
        return operation_timing_info_mechanism
