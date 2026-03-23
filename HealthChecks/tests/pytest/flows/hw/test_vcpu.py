from __future__ import absolute_import
from tests.pytest.tools.versions_alignment import Mock

import pytest

from flows.HW.VCPU import ValidateCBISIsolationFileExist
from tests.pytest.pytest_tools.operator.test_validation_base import ValidationTestBase, ValidationScenarioParams
from tools.global_enums import Version
from tools.global_enums import Objectives
from tests.pytest.pytest_tools.operator.test_operator import CmdOutput


class TestValidateCBISIsolationFileExist(ValidationTestBase):
    tested_type = ValidateCBISIsolationFileExist

    out = "/usr/share/cbis/data/cbis.cpu_isolation"
    out1 = "/usr/share/cbis/data/cbis.dpdk_cpu_isolation"

    scenario_passed = [
        ValidationScenarioParams(scenario_title="cbis.dpdk_cpu_isolation file exists for Version >= 25",
                                 additional_parameters_dict={"file_exist": True},
                                 version=Version.V25,
                                 tested_object_mock_dict={"get_host_roles": Mock(return_value=[Objectives.COMPUTES, Objectives.DPDK_COMPUTES])},
                                 cmd_input_output_dict={
                                     "sudo find /usr/share/cbis/data/cbis.dpdk_cpu_isolation": CmdOutput(out=out1, return_code=0),
                                     "sudo find /usr/share/cbis/data/cbis.cpu_isolation": CmdOutput(out=out,return_code=0)
                                 }
                                 ),
        ValidationScenarioParams(scenario_title="cbis.cpu_isolation file exists for Version < 25",
                                 additional_parameters_dict={"file_exist": True},
                                 version=Version.V22,
                                 tested_object_mock_dict={"get_host_roles": Mock(return_value=[Objectives.COMPUTES, Objectives.DPDK_COMPUTES])},
                                 cmd_input_output_dict={
                                     "sudo find /usr/share/cbis/data/cbis.cpu_isolation": CmdOutput(out=out, return_code=0),
                                 }
                                 )
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="cbis.dpdk_cpu_isolation file exists for Version >= 25",
                                 additional_parameters_dict={"file_exist": False},
                                 version=Version.V25,
                                 tested_object_mock_dict={"get_host_roles": Mock(return_value=[Objectives.COMPUTES, Objectives.DPDK_COMPUTES])},
                                 cmd_input_output_dict={
                                     "sudo find /usr/share/cbis/data/cbis.dpdk_cpu_isolation": CmdOutput(out=out1, return_code=1),
                                     "sudo find /usr/share/cbis/data/cbis.cpu_isolation": CmdOutput(out=out,return_code=1)
                                 }
                                 ),
        ValidationScenarioParams(scenario_title="cbis.cpu_isolation file exists for Version < 25",
                                 additional_parameters_dict={"file_exist": False},
                                 version=Version.V22,
                                 tested_object_mock_dict={"get_host_roles": Mock(return_value=[Objectives.COMPUTES, Objectives.DPDK_COMPUTES])},
                                 cmd_input_output_dict={
                                     "sudo find /usr/share/cbis/data/cbis.cpu_isolation": CmdOutput(out=out, return_code=1),
                                 }
                                 )
    ]

    def _init_mocks(self, tested_object):
        tested_object.file_utils.is_file_exist = Mock()
        tested_object.file_utils.is_file_exist.return_value = self.additional_parameters_dict['file_exist']

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)
