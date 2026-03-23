from __future__ import absolute_import
import tools.user_params
from HealthCheckCommon.base_SystemOperator_flow import BaseSystemOperatorFlow
from flows_of_sys_operations.sys_data_collector.collector import CreateTarFile, ScpToManager, \
    TgzHostsTgzFilesOnManager, CleanHosts, PrintFilesList, CleanManager, CopyToFinalFolder, ChangePermissionsOnManager, \
    PrintFinalFilesLocation
from flows_of_sys_operations.sys_data_collector.telemetry_collector.sar_collector import \
    AppendSarFilesToTar, ZipSarTarFile, TelemetryCollectorPreFlow
from tools.global_enums import Deployment_type


class TelemetryCollectingFlow(BaseSystemOperatorFlow):

    def _get_list_of_validator_class(self, version, deployment_type):
        check_list_class = [
            CreateTarFile,
            AppendSarFilesToTar,
            ZipSarTarFile,
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
        return "telemetry_collector"

    def deployment_type_list(self):
        return [Deployment_type.CBIS, Deployment_type.NCS_OVER_BM]

    @staticmethod
    def add_flow_arguments(flow_parser):
        flow_parser.add_argument('--vms-flow-out-path', type=str, required=False,
                                 help='SAR collector - JSON output from vms flow for isolated CPU data.')
        flow_parser.add_argument('--sar-date', type=int, help='SAR collector - '
                                                              'The date of the sar data (can be only from last month, '
                                                              'an integer between 1-30).')
        flow_parser.add_argument('--sar-file', type=str, help='SAR collector - a specific full path to '
                                                              'sar data, this parameter is needed when need to parse '
                                                              'on customers sar info without the setup.'
                                                              'use with --hosts to specify the hosts that the path '
                                                              'exists on them. If define the full path no need to '
                                                              'define sar date.')

    @staticmethod
    def init_args(args):
        if args.vms_flow_out_path:
            tools.user_params.vms_info_path = args.vms_flow_out_path

        if args.sar_date:
            tools.user_params.sar_date = args.sar_date

        if args.sar_file:
            tools.user_params.sar_file = args.sar_file

    def _get_initiator_class(self):
        return TelemetryCollectorPreFlow()
