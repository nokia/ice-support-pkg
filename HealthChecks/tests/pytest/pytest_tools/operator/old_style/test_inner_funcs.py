from __future__ import absolute_import
from tests.pytest.tools.versions_alignment import nested

import pytest

from tests.pytest.pytest_tools.operator.test_operator import OperatorTestBase, ScenarioParams


class InnerFuncsScenarioParams(ScenarioParams):
    def __init__(self, scenario_title, function_args=tuple(), function_res=None, exception_raised=None, cmd_input_output_dict=None,
                 version=None, data_collector_dict=None, library_mocks_dict=None, tested_object_mock_dict=None,
                 additional_parameters_dict=None):
        super(InnerFuncsScenarioParams, self).__init__(scenario_title, cmd_input_output_dict, version, data_collector_dict,
                                                       library_mocks_dict, tested_object_mock_dict,
                                                       additional_parameters_dict)
        if type(function_args) is not tuple:
            function_args = (function_args,)
        self.function_args = function_args
        self.function_res = function_res
        self.exception_raised = exception_raised


class OperatorTestInnerFunctions(OperatorTestBase):
    def run_test_on_inner_func(self, func_object, tested_object, inner_func_scenario_params):
        assert type(inner_func_scenario_params) is InnerFuncsScenarioParams
        self._init_operator_object(tested_object, inner_func_scenario_params)
        context_managers = self._prepare_patches_list(tested_object)

        # python 3 not support nested
        with nested(*context_managers):
            if inner_func_scenario_params.exception_raised:
                with pytest.raises(inner_func_scenario_params.exception_raised):
                    func_object(*inner_func_scenario_params.function_args)
            else:
                assert inner_func_scenario_params.function_res == func_object(*inner_func_scenario_params.function_args)
