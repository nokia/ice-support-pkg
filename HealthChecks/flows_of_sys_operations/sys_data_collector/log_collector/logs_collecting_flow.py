from __future__ import absolute_import
import os
from datetime import datetime, timedelta

import yaml
from yaml import YAMLError

from HealthCheckCommon.base_SystemOperator_flow import BaseSystemOperatorFlow
from flows_of_sys_operations.sys_data_collector.collector import *
from flows_of_sys_operations.sys_data_collector.log_collector import log_collector_params
from flows_of_sys_operations.sys_data_collector.log_collector.log_collector import AppendLogsFilesToTar, \
    LogsCollectorPreFlow
from tools import paths
from tools.python_utils import PythonUtils
from tools.global_enums import *


class LogCollectingFlow(BaseSystemOperatorFlow):

    def _get_list_of_validator_class(self, version, deployment_type):
        check_list_class = [
            CreateTarFile,
            AppendLogsFilesToTar,
            ZipTarFile,
            ScpToManager,
            TgzHostsTgzFilesOnManager,
            CleanHosts,
            PrintFilesList,
            CleanManager,
            CopyToFinalFolder,
            PrintFinalFilesLocation
        ]

        return check_list_class

    @staticmethod
    def command_name():
        return "log_collector"

    @staticmethod
    def add_flow_arguments(flow_parser):
        flow_parser.add_argument('-d', '--period-of-log-collecting-in-days', type=int, nargs=1, required=False,
                                 help='Log collector - Collect logs from the last X days. '
                                      'If not specified - '
                                      'logs will be collected by default value of {} days'.format(
                                     log_collector_params.period_of_log_collecting_in_days))
        flow_parser.add_argument('-s', '--scenario-file-name', type=str, required=False,
                                 help='Log collector - collect logs for specific scenario.\n'
                                      'Please find the available scenarios under -- ice/log_scenarios -- folder.\n'
                                      'Need to supply the file name of the expected scenario\n'
                                      'You can edit the customized.yaml scenario to choose the specific logs '
                                      'and then run with -s customized.yaml')
        flow_parser.add_argument('-SD', '--start-date', type=str, required=False,
                                 help='Log collector - Collect logs from the given start date - '
                                      'Expected format YYYY-MM-DD')
        flow_parser.add_argument('-ED', '--end-date', type=str, required=False,
                                 help='Log collector - Collect logs until the given end date - '
                                      'Expected format YYYY-MM-DD')
        flow_parser.add_argument('--base-collector-dir', type=str, required=False,
                                 help='Log collector - Specify path for log collector base folder, e.g., /tmp/.')

    @staticmethod
    def init_args(args):
        if args.period_of_log_collecting_in_days:
            if args.start_date or args.end_date:
                LogCollectingFlow._print_arg_err_msg_and_exit(
                    "Expecting not to get '--period-of-log-collecting-in-days' flag with one of the flags: "
                    "'--start-date' and '--end-date'")
            log_collector_params.period_of_log_collecting_in_days = args.period_of_log_collecting_in_days[0]

        if args.scenario_file_name:
            log_collector_params.path_to_specific_scenario = os.path.join(paths.LOG_SCENARIOS_DIR_PATH,
                                                                          args.scenario_file_name)
            if not os.path.exists(log_collector_params.path_to_specific_scenario):
                available_scenarios = os.listdir(paths.LOG_SCENARIOS_DIR_PATH)
                LogCollectingFlow._print_arg_err_msg_and_exit(
                    "Couldn't find the scenario {} under ice/log_scenarios, "
                    "Please provide correct scenario file name.\nThe available scenarios are: {}".format(
                        args.scenario_file_name, ", ".join(available_scenarios)))
            try:
                with open(log_collector_params.path_to_specific_scenario) as f:
                    PythonUtils.yaml_safe_load(f)
            except YAMLError as e:
                LogCollectingFlow._print_arg_err_msg_and_exit("Yaml file: {} is broken, "
                                                              "yaml load failed with the error: {}\n"
                                                              "Please fix the yaml file and run the log "
                                                              "collector again.".format(args.scenario_file_name, e))

        if args.start_date:
            LogCollectingFlow.validate_date_format(args.start_date)
            LogCollectingFlow.validate_start_date_is_before_today(args.start_date)
            log_collector_params.start_date_log_collecting = args.start_date
            if args.end_date:
                LogCollectingFlow.validate_date_format(args.end_date)
                LogCollectingFlow.validate_start_date_is_before_end_date(args.start_date, args.end_date)
                end_date_datetime = datetime.strptime(args.end_date, log_collector_params.date_format) + timedelta(
                    days=1)
                log_collector_params.end_date_log_collecting = end_date_datetime.strftime(
                    log_collector_params.date_format)
            else:
                current_date = datetime.now().date()
                log_collector_params.end_date_log_collecting = current_date.strftime(log_collector_params.date_format)
        if args.end_date and not args.start_date:
            LogCollectingFlow._print_arg_err_msg_and_exit("Expecting to provide '--start-date' while using "
                                                          "'--end-date' flag")

        if args.base_collector_dir:
            log_collector_params.base_collector_dir = args.base_collector_dir

    @staticmethod
    def validate_date_format(str_date):
        try:
            datetime.strptime(str_date, log_collector_params.date_format)
        except ValueError:
            LogCollectingFlow._print_arg_err_msg_and_exit(
                'Invalid date format or date does not exist for date: {}. '
                'Please provide the date in format YYYY-MM-DD and ensure that the date you entered is valid.'.format(
                    str_date))

    @staticmethod
    def _print_arg_err_msg_and_exit(msg):
        emphasizing_message = "*" * len(msg)
        log_and_print(emphasizing_message)
        log_and_print(msg)
        log_and_print(emphasizing_message)
        os._exit(2)

    @staticmethod
    def validate_start_date_is_before_today(start_date):
        current_date = datetime.now()
        start_date_datetime = datetime.strptime(start_date, log_collector_params.date_format)
        if start_date_datetime > current_date:
            LogCollectingFlow._print_arg_err_msg_and_exit("Expect to get a '--start-date' that is before today's date")

    def deployment_type_list(self):
        return [Deployment_type.CBIS, Deployment_type.NCS_OVER_BM]

    def _get_initiator_class(self):
        return LogsCollectorPreFlow()

    @staticmethod
    def validate_start_date_is_before_end_date(start_date, end_date):
        start_date_datetime = datetime.strptime(start_date, log_collector_params.date_format)
        end_date_datetime = datetime.strptime(end_date, log_collector_params.date_format)
        if start_date_datetime > end_date_datetime:
            LogCollectingFlow._print_arg_err_msg_and_exit(
                "Expect to get a '--start-date' that is before the '--end-date'")
