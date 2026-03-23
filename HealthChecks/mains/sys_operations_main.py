from __future__ import absolute_import

import argparse
import json
from collections import OrderedDict
import tools.global_logging as log
from mains.base_main import MainBase
import tools.UI.table_print as table_print
from invoker.sys_operation_flows_list import SysOperationFlowList
from invoker.invoker import Invoker
from tools import paths
from tools.SummaryFilesOperations import SummaryFilesOperations
from tools.system_commands import SystemCommands


class SysOperationMain(MainBase):
    def _add_argument_for_argparse(self):
        assert isinstance(self._parser, argparse.ArgumentParser)

        parent_parser = self._parser
        parser = argparse.ArgumentParser(add_help=False)
        subparsers = parser.add_subparsers(dest='run_flow')

        for flow in SysOperationFlowList.get_list_of_flows():
            flow_parser = argparse.ArgumentParser(add_help=False)
            flow.add_flow_arguments(flow_parser)
            subparsers.add_parser(flow.command_name(), parents=[parent_parser, flow_parser],
                                  formatter_class=argparse.RawTextHelpFormatter)

        self._parser = parser

    def _create_summary_operations(self, cluster_name=""):
        if not self._flg_quiet:
            SystemCommands.save_key_to_keys_file()
        return SummaryFilesOperations(prefix='SysOperationSummary', out_path=paths.ICE_LOGS_DIR, cluster_name=cluster_name)

    def _set_invoker(self, version, deployment_type, only_specific_hosts_list=None, roles=None,
                     specific_validations=None, specific_tags=None):

        self._invoker = Invoker(
            version=version,
            flg_is_passive_type_only=False,
            deployment_type=deployment_type,
            flow_list_class=SysOperationFlowList,
            host_name_list=only_specific_hosts_list,
            roles=roles)

    def _get_flows_dict(self):
        to_return = OrderedDict()
        arguments = self._args

        if not arguments.run_flow:
            log.log_and_print("For running any system flow, flow must chosen by --run-flow")
            return to_return

        flow = arguments.run_flow

        all_possible_flows = self._invoker.get_available_flows(specific_flows=[flow])


        if flow not in list(all_possible_flows.keys()):
            log.log_and_print(
                "flow {} is not valid for this deployment type/version  ".format(flow))
            return to_return
        to_return[flow] = all_possible_flows[flow]
        return to_return


    def _run_flows_dict(self, flow_dict):
        arguments = self._args
        assert len(list(flow_dict.keys())) == 1
        #flow =flow_dict.keys()[0]
        all_results =[]
        if not self._flg_quiet and not self._no_out_files:
            print_msg = 'Full log is found at {}'.format(self._summary_operations.get_logger_path())
            log.log_and_print_with_frame(print_msg)

        for operation_name, validators_list in list(flow_dict.items()):
            log.log_and_print('running: '+ operation_name)
            self._init_flow_args(operation_name)
            one_results = self._invoker.run(operation_name, validators_list)
            all_results.append(one_results["details"])

        if not self._flg_quiet:
            table_print.print_flows_result(one_results["details"], flg_only_failed=arguments.print_only_failed)
            if not self._no_out_files:
                log.logger.info(json.dumps(all_results, indent=4))


        log.logger.info("EOF")
        return self.get_dict_result(0, all_results)

    def _init_flow_args(self, operation_name):
        flow = self._invoker.get_flow_object_if_exist(operation_name)

        if flow:
            flow.init_args(self._args)

    def _create_parser(self, parser_description):
        return argparse.ArgumentParser(description=parser_description, add_help=False)
