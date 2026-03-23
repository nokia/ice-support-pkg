from __future__ import absolute_import
import json

from invoker.validations_flows_list import ValidationFlowList
from tools.adapter import initialize_adapter_instance
import tools.paths as paths
import tools.sys_parameters as gs
from tools.global_enums import Deployment_type, Version


class HostMock:
    ip = "xx.xx.xx.xx"


class FlowsSet():

    def __init__(self, data):
        assert isinstance(data, dict)
        # ...
        self._data = data


class FlowsSetFactory:
    def __init__(self):
        self._my_host_executor_moke = HostMock()
        with open(paths.NAME_TO_URL_FILE) as name_to_url:
            self._validations_confluences = json.load(name_to_url)

    def _validation_class_list_2_validation_details(self, validation_class_list):
        validation_details = {}
        for validation_class in validation_class_list:
            validation_object = validation_class(self._my_host_executor_moke)
            unique_name = validation_object.get_unique_name()
            if not unique_name in validation_details:
                details = {}
                details["title"] = validation_object._title
                details["implication_tags"] = validation_object._implication_tags
                details["doc"] = self._validations_confluences.get(unique_name, '')
                validation_details[unique_name] = details
        return validation_details

    def _validation_class_list_2_unique_names_set(self, validation_class_list):
        unique_names_set = set()
        for validation_class in validation_class_list:
            validation_object = validation_class(self._my_host_executor_moke)
            unique_name = validation_object.get_unique_name()
            unique_names_set.add(unique_name)
        return unique_names_set

    def get_flows_sets(self, flg_detailed=False):
        initialize_adapter_instance(Deployment_type.CBIS, Version.V22)

        gs.get_base_conf = lambda: None
        gs.get_hotfix_list = lambda: []

        log_flows = ['scale_log_error_flow', 'system_log_error_flow']

        detailed_validation_data = {}
        all_flows = ValidationFlowList.get_list_of_flows()
        data = {}

        for flow in all_flows:
            current_flow = flow()
            flow_name = current_flow.command_name()
            flow_data = {}
            detailed_validation_data[flow_name] = {}

            for deployment_type in Deployment_type.AVAILABLE_TYPES:
                flow_data[deployment_type] = set()

                for version in Version.AVAILABLE_VERSIONS:
                    gs.get_version = lambda: version

                    for is_central in [True, False]:
                        gs.is_ncs_central = lambda: is_central

                        for is_more_than_one_cluster in [True, False]:
                            gs.is_more_than_one_cluster = lambda: is_more_than_one_cluster

                            self._update_unique_name_from_flow(deployment_type, version, current_flow,
                                                               detailed_validation_data, flg_detailed, flow_data,
                                                               flow_name, log_flows)
            data[flow_name] = flow_data

        if flg_detailed:
            return detailed_validation_data
        else:
            return data

    def _update_unique_name_from_flow(self, deployment_type, version, current_flow, detailed_validation_data,
                                      flg_detailed, flow_data, flow_name, log_flows):
        if deployment_type in current_flow.deployment_type_list():
            if not current_flow.command_name() in log_flows:
                validation_class_list = current_flow._get_list_of_validator_class(version, deployment_type)
                unique_names_set = self._validation_class_list_2_unique_names_set(validation_class_list)

                if flg_detailed:
                    detailed_data_out = self._validation_class_list_2_validation_details(validation_class_list)
                    detailed_validation_data[flow_name].update(detailed_data_out)
            else:
                unique_names_set = set(current_flow.get_validations_name(version, deployment_type, None))
            flow_data[deployment_type] = flow_data[deployment_type].union(unique_names_set)
