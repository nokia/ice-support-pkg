from __future__ import absolute_import
from __future__ import print_function
import tools.user_params
from HealthCheckCommon.base_SystemOperator_flow import BaseSystemOperatorFlow
from flows_of_sys_operations.FileTracker.OperatorsOnAllHosts import *
from flows_of_sys_operations.FileTracker.OperatorsOnLocalHost import *
from flows_of_sys_operations.FileTracker.commands_diffs_collector import CommandsDiffsCollector
from flows_of_sys_operations.FileTracker.dynamic_diffs_collector import DynamicDiffsCollector
from tools.global_enums import *


class FileTrackerFlow(BaseSystemOperatorFlow):

    def _get_list_of_validator_class(self, version, deployment_type):
        check_list_class = [
            FileTrackerStarter,
            DiffsCollector,
            FoldersDiffsCollector,
            DynamicDiffsCollector,
        ]
        check_list_class_after_diff_collector = [
            DiffsWriter,
            SnapshotsUpdater,
            FileTrackerFinisher,
            SaveEncryptionKey
        ]
        if version >= Version.V24_11:
            check_list_class = check_list_class + [CommandsDiffsCollector] + check_list_class_after_diff_collector

        else:
            check_list_class = check_list_class + check_list_class_after_diff_collector

        return check_list_class

    @staticmethod
    def command_name():
        return "file_tracker"

    @staticmethod
    def add_flow_arguments(flow_parser):
        flow_parser.add_argument('--config-json-path', type=str, nargs=1, required=False,
                                 help='Provide path of JSON file with all the paths and configurations according to the '
                                      'deployment type')

    @staticmethod
    def init_args(args):
        if args.config_json_path:
            print(args.config_json_path)
            tools.user_params.config_json_path = args.config_json_path[0]

    def deployment_type_list(self):
        return [Deployment_type.CBIS, Deployment_type.NCS_OVER_BM, Deployment_type.NCS_OVER_OPENSTACK,
                Deployment_type.NCS_OVER_VSPHERE]
