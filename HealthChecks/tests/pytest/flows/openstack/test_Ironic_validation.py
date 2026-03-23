from __future__ import absolute_import
import pytest
from tests.pytest.tools.versions_alignment import Mock

from flows.OpenStack.Ironic_validations import IronicNodeActiveValidator
from tests.pytest.pytest_tools.operator.test_operator import CmdOutput
from tests.pytest.pytest_tools.operator.test_validation_base import ValidationTestBase, ValidationScenarioParams
import os

from tools import sys_parameters
from tools.global_enums import Deployment_type


class TestIronicNodeActiveValidator(ValidationTestBase):
    tested_type = IronicNodeActiveValidator
    validation_cmd = "source {}; openstack baremetal node list -f yaml".format('/home/stack/stackrc')
    current_dir_path = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(current_dir_path, 'inputs', 'ironic_output_yaml.txt')
    with open(path , 'r') as file:
        out_templete = file.read()

    scenario_passed = [
        ValidationScenarioParams(scenario_title="all nodes are good",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(
                                     out=out_templete.format(Maintenance='false',Power='on',State='active',
                                                             UUID='469c7709-2c35-48c2-9530-1296ce8cd2d6'))})
    ]
    scenario_failed = [
        ValidationScenarioParams(scenario_title="Maintenance ",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(
                                     out=out_templete.format(Maintenance='true', Power='on', State='active',
                                                             UUID='469c7709-2c35-48c2-9530-1296ce8cd2d6'))}),
        ValidationScenarioParams(scenario_title="Power ",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(
                                     out=out_templete.format(Maintenance='false', Power='off', State='active',
                                                             UUID='469c7709-2c35-48c2-9530-1296ce8cd2d6'))}),
        ValidationScenarioParams(scenario_title="State",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(
                                     out=out_templete.format(Maintenance='true', Power='on', State='sleep',
                                                             UUID='469c7709-2c35-48c2-9530-1296ce8cd2d6'))}),
        ValidationScenarioParams(scenario_title="UUID #1",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(
                                     out=out_templete.format(Maintenance='true', Power='on', State='sleep',
                                                             UUID=''))}),
        ValidationScenarioParams(scenario_title="UUID #2",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(
                                     out=out_templete.format(Maintenance='true', Power='on', State='sleep',
                                                             UUID=''))}),
        ValidationScenarioParams(scenario_title="UUID #3",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(
                                     out=out_templete.format(Maintenance='true', Power='on', State='sleep',
                                                             UUID='""'))})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    def _init_mocks(self, tested_object):
        sys_parameters.get_deployment_type = Mock(return_value=Deployment_type.CBIS)
        tested_object.system_utils.get_stackrc_file_path = Mock()
        tested_object.system_utils.get_stackrc_file_path.return_value = '/home/stack/stackrc'

