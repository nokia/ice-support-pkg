"""
# Template for validation test.

from tests.pytest.pytest_tools.test_operator import ScenarioParams, CmdOutput
from tests.pytest.pytest_tools.test_validation_base import ValidationTestBase, ValidationScenarioParams



class Test<ValidationClassName>(ValidationTestBase):
    tested_type = <ValidationClass>

    scenario_passed = [
        ValidationScenarioParams(title="<scenario title>",
                                 cmd_input_output_dict={"<cmd from validation>": CmdOutput(out="<cmd output>")},
                                 version=Version.<version number>),
        ValidationScenarioParams(title="<scenario title>",
                                 cmd_input_output_dict={"<cmd from validation>": CmdOutput(out="<cmd output>")},
                                 version=Version.<version number>))
    ]

    scenario_failed = [
        ValidationScenarioParams(title="<scenario title>",
                                 cmd_input_output_dict={"<cmd from validation>": CmdOutput(out="<cmd output>")},
                                 version=Version.<version number>),
        ValidationScenarioParams(title="<scenario title>",
                                 cmd_input_output_dict={"<cmd from validation>": CmdOutput(out="<cmd output>")},
                                 version=Version.<version number>))
    ]

    scenario_unexpected_system_output = [
        ValidationScenarioParams(title="<scenario title>",
                                 cmd_input_output_dict={"<cmd from validation>": CmdOutput(out="<cmd output>")},
                                 version=Version.<version number>),
        ValidationScenarioParams(title="<scenario title>",
                                 cmd_input_output_dict={"<cmd from validation>": CmdOutput(out="<cmd output>")},
                                 version=Version.<version number>))
    ]

    # ---------- From here copy as is ----------
    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_unexpected_system_output(self, scenario_params, tested_object)

"""