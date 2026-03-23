from __future__ import absolute_import
from __future__ import print_function
from tools import user_params
from mains.base_main import *
from invoker.invoker import Invoker
import HealthCheckCommon.PreviousResults as PreviousResults
import tools.UI.table_print as table_print
from invoker.validations_flows_list import ValidationFlowList
from tools.SummaryFilesOperations import SummaryFilesOperations
from tools.python_versioning_alignment import get_user_input
from tools.global_logging import log_and_print
from tools.system_commands import SystemCommands
from tools.global_enums import ImplicationTag, BlockingTag


class ValidationsMain(MainBase):

    @staticmethod
    def get_available_tag_values():
        available_tags = []

        available_tags.extend(BlockingTag.get_all_blocking_tags())
        available_tags.extend(ImplicationTag.get_all_implication_tags())

        return available_tags

    @staticmethod
    def get_tags_help_text():
        available_tags = ValidationsMain.get_available_tag_values()
        tags_str = ', '.join(available_tags)
        return 'Filter validations by tags. Only validations with at least one of the provided tags (in either _implication_tags or _blocking_tags) will be run.\n\nAvailable tags:\n  {}'.format(tags_str)

    @staticmethod
    def validate_tags(tags_list):
        """Validate that all provided tags (by the user) are supported"""
        if not tags_list:
            return True, ""
        
        available_tags = ValidationsMain.get_available_tag_values()
        invalid_tags = [tag for tag in tags_list if tag not in available_tags]
        
        if invalid_tags:
            error_msg = "ERROR: Invalid tag(s) provided: {}\n\nSupported tags are:\n  {}".format(
                ', '.join(invalid_tags),
                ', '.join(available_tags)
            )
            return False, error_msg
        
        return True, ""

    def _prepare_system(self):
        if self._args.debug_validation:
            self._handle_debug_validation_flag()

        res = super(ValidationsMain, self)._prepare_system()

        if res is not True:
            return res

        if self._args.run_validations:
            user_params.run_validations = self._args.run_validations

        if hasattr(self._args, 'tags') and self._args.tags:
            is_valid, error_msg = ValidationsMain.validate_tags(self._args.tags)
            if not is_valid:
                print(error_msg)
                os._exit(1)
            user_params.filter_tags = self._args.tags

        if self._args.vm:
            user_params.vm = self._args.vm

        return True

    def _handle_debug_validation_flag(self):
        StructedPrinter.encrypt_out = False
        user_params.debug_validation_flag = True
        self._flg_quiet = True
        print('\n--------------------------------------------------------')
        print('| Note: Validation run may print sensitive information |')
        print('--------------------------------------------------------\n')
        user_params.debug_validation_name = get_user_input(
            'Enter validation title to run the validation, or hit ENTER to cancel\n')
        if user_params.debug_validation_name == '':
            print("Note: Validation run was canceled")
            os._exit(0)

    def _set_invoker(self, version, deployment_type, only_specific_hosts_list=None, roles=None,
                     specific_validations=None, specific_tags=None):

        self._invoker = Invoker(
            version=version,
            flg_is_passive_type_only=True,
            deployment_type=deployment_type,
            flow_list_class=ValidationFlowList,
            host_name_list=only_specific_hosts_list,
            roles=roles,
            specific_validations=specific_validations,
            specific_tags=specific_tags
        )


    def _create_summary_operations(self, cluster_name=""):
        SystemCommands.save_key_to_keys_file()
        return SummaryFilesOperations(cluster_name=cluster_name)


    def _get_flows_dict(self):
        arguments = self._args
        flow_dict = OrderedDict()
        if arguments.run_flows:
            all_possible_validation = self._invoker.get_available_flows(specific_flows=arguments.run_flows)
            for validation in arguments.run_flows:
                if validation not in list(all_possible_validation.keys()):
                    log.log_and_print(
                        "validation {} is not valid for this deployment type/version  ".format(validation))
                else:
                    flow_dict[validation] = all_possible_validation[validation]
        elif arguments.debug_validation or arguments.run_validations:
            flow_dict = self._invoker.get_available_flows()
        else:
            flow_dict = self._invoker.get_available_flows(run_only_default=True,
                                                          limited_output=tools.user_params.limited_output)
        return flow_dict

    def _get_specific_validations_list(self):
        arguments = self._args
        specific_validations = None
        if arguments.run_validations:
            specific_validations = user_params.run_validations
        if arguments.debug_validation:
            specific_validations = user_params.debug_validation_name
        if specific_validations and not isinstance(specific_validations, list):
            specific_validations = [specific_validations]
        return specific_validations

    def _get_specific_tags_list(self):
        arguments = self._args
        specific_tags = None
        if hasattr(arguments, 'tags') and arguments.tags:
            specific_tags = arguments.tags
        if specific_tags and not isinstance(specific_tags, list):
            specific_tags = [specific_tags]
        return specific_tags

    def _run_flows_dict(self, flow_dict):
        log_and_print('Creating a list of relevant validations to be performed\n')
        arguments = self._args
        failed_results = []
        minimum_failed_results = []
        is_vms_flow = len(list(flow_dict.keys())) and list(flow_dict.keys())[0] == 'vms'

        all_results = []
        # todo rebase this
        # create a list of the unique phase indexes and sort it (because the last phase index is max float and there are
        # many phases with index 0)
        indexes_list = [self._invoker.get_flow_object(validation).get_flow_order() for validation in list(flow_dict.keys())]
        unique_indexes_list = list(set(indexes_list))
        unique_indexes_list.sort()
        return_code = 0
        # go over the sorted indexes and for each index run the related validations

        for index in unique_indexes_list:
            for flow_name, validators_list in list(flow_dict.items()):
                flow = self._invoker.get_flow_object(flow_name)
                if flow.get_flow_order() != index:
                    continue
                validation_dependencies = flow.get_dependencies()
                if not PreviousResults.check_commands_results_exist(validation_dependencies):
                    return self.get_dict_result(1,
                                         "the flow {} depends on other flows that weren't fully executed:\n{}".format(
                                                    flow_name, validation_dependencies
                                                ))
                one_results = self._invoker.run(flow_name, validators_list)

                res = self.filtering(one_results["details"], self.should_validation_be_included)
                if res:
                    minimum_failed_results.append(res)
                if tools.user_params.limited_output:
                     one_results["details"] = res

                return_code = self.get_return_code_by_failuers(one_results["details"]["details"], return_code)
                if self._invoker._specific_validations is None or one_results['details']['details'] != OrderedDict():
                    all_results.append(one_results["details"])
                    PreviousResults.add_to_previous_results(flow_name, one_results["details"])
                    host_results_dict = self.get_failed_results(one_results["details"])
                    if host_results_dict:
                        failed_results.append(host_results_dict)
                    was_printed = False

                    if not was_printed and not is_vms_flow:
                        table_print.print_flows_result(one_results["details"], flg_only_failed=arguments.print_only_failed)
        log.logger.info(json.dumps({"top 10 large streams": HostExecutor.top_10_large_streams}))

        if all_results == [] and user_params.debug_validation_name:
            print("\nNote: Validation '{}' wasn't found".format(user_params.debug_validation_name))
        if not user_params.debug_validation_flag:
            table_print.print_minimum_json_out(minimum_failed_results)
            table_print.print_summarize_failures(failed_results, arguments.print_only_failed)
        if not self._flg_quiet and not self._no_out_files:

            is_ok, msg = self._summary_operations.run(
                sys_parameters.get_deployment_type(),
                Version.get_version_name(sys_parameters.get_version()),
                sys_parameters.get_sub_version(),
                sys_parameters.get_build(),
                sys_parameters.get_bcmt_build(),
                sys_parameters.get_hotfix_list(),
                self._roles_map,
                self._ice_version,
                self._ice_version_date,
                all_results,
                sys_parameters.get_cluster_name())
            if not is_ok:
                return self.get_dict_result(1, msg)
        log.logger.info("EOF")
        return self.get_dict_result(return_code, all_results)

    def get_return_code_by_failuers(self, one_results, return_code):
        for host_name in list(one_results.keys()):
            for validation_name in list(one_results[host_name].keys()):
                if one_results[host_name][validation_name].get("pass") and \
                        one_results[host_name][validation_name].get("pass") == Status.SYS_PROBLEM.value:
                    return_code = 130
                    log.log_and_print(
                        "Validation '{}' get unexpected output with return code {}: system problem detected.".format(
                            validation_name,
                            return_code), level='error')
                    return return_code
                if one_results[host_name][validation_name].get("severity"):
                    validation_severity = Severity.get_severity_order(one_results[host_name][validation_name].get("severity"))
                    if validation_severity <= Severity.ERROR.order:
                        return_code = 130
                        log.log_and_print(
                            "Validation '{}' completed with return code {} and severity '{}'".format(
                            validation_name, return_code, validation_severity), level='error')
                        return return_code
        return return_code

    def _add_argument_for_argparse(self):
        assert isinstance(self._parser, argparse.ArgumentParser)

        # in sys operation only one flow for a run is alowed Validation is all flow by defult and several flowes alwed

        self._parser.add_argument('--run-flows', type=str, nargs='+',
                                  help='Provide flow validation to be run. Default is all flows')

        self._parser.add_argument('--run-validations', type=str, nargs='+',
                                  help='Provide validation unique name to be run. Default is all validations')

        self._parser.add_argument('--tags', type=str, nargs='+',
                                  help=ValidationsMain.get_tags_help_text())

        self._parser.add_argument('--debug-validation', action='store_true',
                                  help='Print commands output of requested validation (interactive) - supports only single validation')

        self._parser.add_argument('--vm', help='The VM ID that will be tested '
                                               '(related to openstack-resource flow only)',
                                  type=str)

    def get_failed_results(self, one_results):
        filtered_one_result = self.filtering(one_results, self.filtering_by_passing_status)
        if not filtered_one_result["details"]:
            return {}
        return filtered_one_result

    def filtering(self, one_results, filtering_fun):
        host_results_dict = OrderedDict()
        for host_name in list(one_results["details"].keys()):
            for validation_name in list(one_results["details"][host_name].keys()):
                validation_result = one_results["details"][host_name][validation_name]
                if filtering_fun(validation_result):
                    host_results_dict.setdefault(host_name, {})[validation_name] = validation_result
        return {"details": host_results_dict, "command_name": one_results["command_name"]}


    def filtering_by_passing_status(self,validation_result):
        if validation_result.get("pass") not in [True, "--"]:
            return True
        return False

    def should_validation_be_included(self, validation_result):
        MIN_SEVERTY_LVL_FOR_LIMITED_OUTPUT = Severity.WARNING
        if validation_result.get("pass") in [True, "--"]:
            return False

        if validation_result.get("pass") == False:
            severity = OrderedConst.str2OrderedConst(Severity, validation_result.get("severity"))
            return severity <= MIN_SEVERTY_LVL_FOR_LIMITED_OUTPUT

        return True
