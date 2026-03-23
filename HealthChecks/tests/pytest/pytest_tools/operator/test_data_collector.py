from __future__ import absolute_import
import pytest
from tests.pytest.tools.versions_alignment import nested
from tools.Exceptions import UnExpectedSystemOutput, NoSuitableHostWasFoundForRoles, NonIdenticalValues
from tests.pytest.pytest_tools.operator.test_operator import OperatorTestBase, ScenarioParams


class DataCollectorScenarioParams(ScenarioParams):
    def __init__(self, scenario_title, cmd_input_output_dict=None, version=None, data_collector_dict=None,
                 library_mocks_dict=None, tested_object_mock_dict=None, scenario_res=None,
                 additional_parameters_dict=None, expected_exception=None):
        super(DataCollectorScenarioParams, self).__init__(scenario_title, cmd_input_output_dict, version, data_collector_dict,
                                                          library_mocks_dict, tested_object_mock_dict,
                                                          additional_parameters_dict)
        self.scenario_res = scenario_res
        self.expected_exception = expected_exception


class DataCollectorTestBase(OperatorTestBase):
    scenarios = []

    @pytest.mark.parametrize("scenario_params", scenarios)
    def test_collect_data(self, scenario_params, tested_object, **kwargs):
        self._init_data_collector_object(tested_object, scenario_params)

        context_managers = self._prepare_patches_list(tested_object)

        # python 3 not support nested
        with nested(*context_managers):
            if scenario_params.expected_exception:
                with pytest.raises(expected_exception=scenario_params.expected_exception):
                        tested_object.collect_data(**kwargs)
            else:
                assert self.scenario_res == tested_object.collect_data(**kwargs), "Please init scenario_res with expected" \
                                                                              " values to the specific scenario"

    def _init_data_collector_object(self, data_collector_object, scenario_params=None):
        self.scenario_res = scenario_params.scenario_res
        self._init_operator_object(data_collector_object, scenario_params)
