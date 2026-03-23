from __future__ import absolute_import
import pytest
from tests.pytest.tools.versions_alignment import Mock

from flows.OpenStack.swift_service_validator import CheckSrvDirOwner, ValidateSrvFolderSpace, CheckSwiftDirectorySrv, SwiftServiceValidator
from tests.pytest.pytest_tools.operator.test_operator import CmdOutput
from tests.pytest.pytest_tools.operator.test_validation_base import ValidationTestBase, ValidationScenarioParams


class TestCheckSrvDirOwner(ValidationTestBase):
    tested_type = CheckSrvDirOwner

    validation_cmd = "sudo stat -c '%U %G' /srv"

    scenario_passed = [
        ValidationScenarioParams(scenario_title="owner root, group root",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out="root root")})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="owner stack, group root",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out="stack root")}),
        ValidationScenarioParams(scenario_title="owner root, group stack",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out="root stack")}),
        ValidationScenarioParams(scenario_title="owner stack, group stack",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out="stack stack")})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestValidateSrvFolderSpace(ValidationTestBase):
    tested_type = ValidateSrvFolderSpace

    validation_cmd = "df -h /srv"

    out = '''
        Filesystem      Size  Used Avail Use% Mounted on
        /dev/vda3        59G   12G   47G  {usage}% /
    '''

    scenario_passed = [
        ValidationScenarioParams(scenario_title="space used 70",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out=out.format(usage=70))}),
        ValidationScenarioParams(scenario_title="space used 80",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out=out.format(usage=80))})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="space used 90 - SOFT_CONDITION",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out=out.format(usage=90))}),
        ValidationScenarioParams(scenario_title="space used 100 - HARD_CONDITION",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out=out.format(usage=100))})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestCheckSwiftDirectorySrv(ValidationTestBase):
    tested_type = CheckSwiftDirectorySrv

    scenario_passed = [
        ValidationScenarioParams(scenario_title="/srv/ dir exists", additional_parameters_dict={"dir_exist": True})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="/srv/ dir does not exist", additional_parameters_dict={"dir_exist": False})
    ]

    def _init_mocks(self, tested_object):
        tested_object.file_utils.is_dir_exist = Mock()
        tested_object.file_utils.is_dir_exist.return_value = self.additional_parameters_dict['dir_exist']

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestSwiftServiceValidator(ValidationTestBase):
    tested_type = SwiftServiceValidator

    good_scale_info = """parameter_defaults:
  ControllerCount: 1
  OvercloudControllerFlavor: Controller
  OvercloudDpdkPerformanceComputeFlavor: DpdkPerformanceCompute
  OvercloudMonitoringFlavor: Monitoring
  OvercloudOvsComputeFlavor: OvsCompute
  OvercloudSriovPerformanceComputeFlavor: SriovPerformanceCompute
  OvercloudStorageFlavor: Storage
  OvsComputeCount: {}"""

    swift_list = '''
    __cache__.
    ov-3sb3qpkdk2y-0-vftybuxduema-Controller-yw6znhgldpl6.
    ov-ui2vnc5vs3r-0-ozuzejgzagxg-OvsCompute-gxs2f55bvrgj.
    ov-ui2vnc5vs3r-1-miyb63bhrrow-OvsCompute-jxoq7rs6pytf.
    ov-ui2vnc5vs3r-2-k27d5nwd6ppb-OvsCompute-xcokl3oa4m57.
    overcloud.
    overcloud-config.
    overcloud-messages.
    overcloud-swift-rings.
    '''

    swift_grep_ov = ('["ov-3sb3qpkdk2y-0-vftybuxduema-Controller-yw6znhgldpl6","ov-ui2vnc5vs3r-0-ozuzejgzagxg-OvsCompute-gxs2f55bvrgj",'
                     '"ov-ui2vnc5vs3r-1-miyb63bhrrow-OvsCompute-jxoq7rs6pytf","ov-ui2vnc5vs3r-2-k27d5nwd6ppb-OvsCompute-xcokl3oa4m57"]')

    nova_list = '''
    overcloud-ovscompute-fi860-1.
    overcloud-ovscompute-fi860-2.
    overcloud-ovscompute-fi860-0.
    overcloud-{}controller-fi860-0.
    '''
    scenario_passed = [
        ValidationScenarioParams(scenario_title="Swift list eqals to nova list",
                                 cmd_input_output_dict={
                                    'cat /home/stack/templates/scale-info.yaml': CmdOutput(good_scale_info.format('3')),
                                    'source /home/stack/stackrc; swift list': CmdOutput(swift_list),
                                    "source /home/stack/stackrc; swift list | grep ov- | jq -R -s -c 'split(\"\\n\")[:-1]'": CmdOutput(swift_grep_ov),
                                    'source /home/stack/stackrc; openstack server list -c Name -f value': CmdOutput(nova_list.format(''))})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="Having different amount of controllers",
                                 cmd_input_output_dict={
                                     'cat /home/stack/templates/scale-info.yaml': CmdOutput(good_scale_info.format('4')),
                                     'source /home/stack/stackrc; swift list': CmdOutput(swift_list),
                                     "source /home/stack/stackrc; swift list | grep ov- | jq -R -s -c 'split(\"\\n\")[:-1]'": CmdOutput(swift_grep_ov),
                                     'source /home/stack/stackrc; openstack server list -c Name -f value': CmdOutput(nova_list.format(''))},
                                 ),
        ValidationScenarioParams(scenario_title="Mismatch of flavor",
                                 cmd_input_output_dict={
                                     'cat /home/stack/templates/scale-info.yaml': CmdOutput(good_scale_info.format('3')),
                                     'source /home/stack/stackrc; swift list': CmdOutput(swift_list),
                                     "source /home/stack/stackrc; swift list | grep ov- | jq -R -s -c 'split(\"\\n\")[:-1]'": CmdOutput(
                                         swift_grep_ov),
                                     'source /home/stack/stackrc; openstack server list -c Name -f value': CmdOutput(nova_list.format('e'))},
                                 )
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    def _init_mocks(self, tested_object):
        tested_object.system_utils.get_stackrc_file_path = Mock()
        tested_object.system_utils.get_stackrc_file_path.return_value = '/home/stack/stackrc'