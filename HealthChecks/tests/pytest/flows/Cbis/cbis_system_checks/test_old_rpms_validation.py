from __future__ import absolute_import

import pytest
from tests.pytest.tools.versions_alignment import Mock

from  flows.Cbis.cbis_system_checks.RPM_Validation import VerifyOldRPMs
from tests.pytest.pytest_tools.operator.test_operator import CmdOutput
from tests.pytest.pytest_tools.operator.test_validation_base import ValidationTestBase, ValidationScenarioParams


class TestCheckOldRPMs(ValidationTestBase):
    tested_type = VerifyOldRPMs
    rpms = 'sudo rpm -qa --qf "%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH},%{INSTALLTIME:date}\n"'
    rpms_out = "kernel-5.14.0-427.44.1.el9_4.x86_64,Wed 23 Apr 2025 10:57:38 AM IST"

    scenario_passed = [
        ValidationScenarioParams(scenario_title="Old kernel RPMs dont exist on the environment",
                                 additional_parameters_dict={'get_current_old_rpms': ""},
                                 cmd_input_output_dict={rpms: CmdOutput(out=rpms_out)}
                                 )]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="Old kernel RPMs exist on the environment",
                                 additional_parameters_dict={'get_current_old_rpms': "kernel-debug-3.10.0-957.27.2.el7.x86_64"},
                                 cmd_input_output_dict={rpms: CmdOutput(out=rpms_out)}
                                 )]


    def _init_mocks(self, tested_object):
        tested_object.get_current_old_rpms = Mock()
        tested_object.get_current_old_rpms.return_value = self.additional_parameters_dict.get("get_current_old_rpms")


    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
         ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

