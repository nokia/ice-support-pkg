from __future__ import absolute_import
import pytest
from tests.pytest.tools.versions_alignment import Mock

from flows.Blueprint.NUMABlueprintDataCollectors import NumaCpus
from tests.pytest.pytest_tools.operator.test_data_collector import DataCollectorTestBase, DataCollectorScenarioParams
from tests.pytest.pytest_tools.operator.test_operator import CmdOutput


class TestNumaCpus(DataCollectorTestBase):
    tested_type = NumaCpus

    out_format = """NUMA node(s): 2
NUMA node{} CPU(s): {}
NUMA node{} CPU(s): {}"""

    scenarios = [
        DataCollectorScenarioParams(
            scenario_title="basic scenario",
            cmd_input_output_dict={"lscpu | grep NUMA": CmdOutput(out=out_format.format(
                0, "0-19,40-59", 1, "20-39,60-79"))},
            additional_parameters_dict={"numa_keys": {"node 0", "node 1"}},
            scenario_res={"node 0": "0-19,40-59", "node 1": "20-39,60-79"}
        ),
        DataCollectorScenarioParams(
            scenario_title="no input to 1 of keys",
            cmd_input_output_dict={"lscpu | grep NUMA": CmdOutput(out=out_format.format(0, "0-19,40-59", 1,
                                                                                        "20-39,60-79"))},
            additional_parameters_dict={"numa_keys": {"node 0", "node 2"}},
            scenario_res={"node 0": "0-19,40-59", "node 2": None}
        )
    ]

    @pytest.mark.parametrize("scenario_params", scenarios)
    def test_collect_data(self, scenario_params, tested_object):
        DataCollectorTestBase.test_collect_data(self, scenario_params, tested_object)

    def _init_mocks(self, tested_object):
        tested_object.get_system_ids = Mock(return_value=self.additional_parameters_dict["numa_keys"])
