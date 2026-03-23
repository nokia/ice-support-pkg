from __future__ import absolute_import

import pytest
from tests.pytest.tools.versions_alignment import Mock

from tools.global_enums import *

from flows.Storage.glusterfs.GlusterFS import VolumeHealNeedCheck
from tests.pytest.pytest_tools.operator.test_operator import CmdOutput
from tests.pytest.pytest_tools.operator.test_validation_base import ValidationTestBase, ValidationScenarioParams
from tools.global_enums import Objectives


class TestVolumeHealNeedCheck(ValidationTestBase):
    tested_type = VolumeHealNeedCheck

    validation_cmd_a = 'sudo /usr/sbin/gluster volume list'
    out_a = '''
        bcmt-glusterfs
        cbur-glusterfs-backup
        '''
    validation_cmd_1 = "sudo /usr/sbin/gluster volume heal bcmt-glusterfs info | grep -i 'Number of entries:'"
    validation_cmd_2 = "sudo /usr/sbin/gluster volume heal cbur-glusterfs-backup info | grep -i 'Number of entries:'"
    out_bad_1 = '''
        Number of entries: -
        Number of entries: 5
        Number of entries: 6
        '''

    out_bad_2 = '''
         Number of entries: 0
         Number of entries: 100
         Number of entries: 6
         '''
    out_note = '''
         Number of entries: 0
         Number of entries: 1
         Number of entries: 6
         '''

    out_good = '''
            Number of entries: 0
            Number of entries: 0
            Number of entries: 0
            '''


    scenario_passed = [
        ValidationScenarioParams(scenario_title="ok",
                                 tested_object_mock_dict={"glusterFs_installed_or_not_status": Mock(return_value=True),
                                                          "is_prerequisite_fulfilled": Mock(return_value=True)},

                                 cmd_input_output_dict={

                                                        validation_cmd_a: CmdOutput(out=out_a, return_code=0),
                                                        validation_cmd_1: CmdOutput(out=out_good, return_code=0),
                                                        validation_cmd_2: CmdOutput(out=out_good, return_code=0)
                                                        })
    ]


    scenario_failed = [
        ValidationScenarioParams(scenario_title="note",
                                 tested_object_mock_dict={"glusterFs_installed_or_not_status": Mock(return_value=True),
                                                          "is_prerequisite_fulfilled":Mock(return_value=True)},
                                 cmd_input_output_dict={
                                     validation_cmd_a: CmdOutput(out=out_a, return_code=0),
                                     validation_cmd_1: CmdOutput(out=out_note, return_code=0),
                                     validation_cmd_2: CmdOutput(out=out_good, return_code=0)
                                 }),

        ValidationScenarioParams(scenario_title="out_bad_1",
                                 tested_object_mock_dict={"glusterFs_installed_or_not_status": Mock(return_value=True),
                                                          "is_prerequisite_fulfilled": Mock(return_value=True)},
                                 cmd_input_output_dict={
                                     validation_cmd_a: CmdOutput(out=out_a, return_code=0),
                                     validation_cmd_1: CmdOutput(out=out_bad_1, return_code=0),
                                     validation_cmd_2: CmdOutput(out=out_good, return_code=0)
                                 }),

        ValidationScenarioParams(scenario_title="out_bad_2",
                                 tested_object_mock_dict={"glusterFs_installed_or_not_status": Mock(return_value=True),
                                                          "is_prerequisite_fulfilled": Mock(return_value=True)},
                                 cmd_input_output_dict={
                                     validation_cmd_a: CmdOutput(out=out_a, return_code=0),
                                     validation_cmd_1: CmdOutput(out=out_note, return_code=0),
                                     validation_cmd_2: CmdOutput(out=out_bad_1, return_code=0)
                                 }),

        ValidationScenarioParams(scenario_title="note",
                                 tested_object_mock_dict={"glusterFs_installed_or_not_status": Mock(return_value=True),
                                                          "is_prerequisite_fulfilled": Mock(return_value=True)},
                                 cmd_input_output_dict={
                                     validation_cmd_a: CmdOutput(out=out_a, return_code=0),
                                     validation_cmd_1: CmdOutput(out=out_bad_1, return_code=0),
                                     validation_cmd_2: CmdOutput(out=out_note, return_code=0)
                                 }),

        ValidationScenarioParams(scenario_title="note",
                                 tested_object_mock_dict={"glusterFs_installed_or_not_status": Mock(return_value=True),
                                                          "is_prerequisite_fulfilled": Mock(return_value=True)},
                                 cmd_input_output_dict={
                                     validation_cmd_a: CmdOutput(out=out_a, return_code=0),
                                     validation_cmd_1: CmdOutput(out=out_note, return_code=0),
                                     validation_cmd_2: CmdOutput(out=out_good, return_code=0)
                                 })
    ]








    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


