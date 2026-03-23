from __future__ import absolute_import
import re

from tools.ConfigStore import ConfigStore
from tools.Exceptions import UnExpectedSystemOutput
from tools.global_enums import Deployment_type

import tools.sys_parameters as gs


class BlueprintInventory:
    processor_type = {"6138": "SKL",
                      "6238": "CLK",
                      "6338": "ICK",
                      "5218": "CLK"}

    def build_actual_blueprint_name(self, collected_data):
        hw_model_type = self.get_hw_model_type()
        cpu_model = self._get_one_value_from_data(collected_data, 'Processor@type')
        nic_model = self._get_one_value_from_data(collected_data, 'Network Interface@model')

        return self._covert_hw_type_to_hw_name(hw_model_type) + "_" + self._convert_cpu_model_to_processor_family(
            cpu_model) + "_" + self._convert_nic_model_to_cx(nic_model)

    @staticmethod
    def get_hw_model_type():
        deployment_type = gs.get_deployment_type()

        if Deployment_type.is_cbis(deployment_type):
            return ConfigStore.get_cbis_user_config()['CBIS']['common'].get('hw_model_type')

        if Deployment_type.is_ncs(deployment_type):
            return ConfigStore.get_cbis_user_config()['common'].get('hw_model_type')

        raise UnExpectedSystemOutput("", "", deployment_type, message="Expected deployment type CBIS / NCS")

    def _convert_cpu_model_to_processor_family(self, cpu_model):
        numbers_in_cpu_model = re.findall(r'\d+', cpu_model)

        for number in numbers_in_cpu_model:
            if self.processor_type.get(number):
                return self.processor_type[number]

        return "_".join(numbers_in_cpu_model)

    def _covert_hw_type_to_hw_name(self, hw_type):
        if "hp" in hw_type:
            gen = re.findall(r'g\d+', hw_type)

            if len(gen) != 1:
                raise UnExpectedSystemOutput("", "", gen, "Expected to have g<number> in hp hw type.")

            return "hp" + "_" + gen[0]

        return hw_type

    def _convert_nic_model_to_cx(self, nic_model):
        if "ConnectX-" not in nic_model:
            return "intel_nic"

        cx_list = re.findall(r'ConnectX-(\d+)', nic_model)
        if len(cx_list) != 1:
            raise UnExpectedSystemOutput("", "", nic_model, "Expected to have ConnectX-<number> in nic model.")
        return "cx" + cx_list[0]

    def _get_one_value_from_data(self, data, key_name):
        first_host_values = self._get_first_value_from_dict(data.get(key_name))

        return self._get_first_value_from_dict(first_host_values)

    def _get_first_value_from_dict(self, dict_):
        if not isinstance(dict_, dict):
            return "unknown"

        if len(dict_) < 1:
            return "unknown"

        first_key = list(dict_.keys())[0]

        return dict_[first_key]
