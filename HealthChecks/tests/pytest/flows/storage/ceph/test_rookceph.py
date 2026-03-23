from __future__ import absolute_import

import pytest

from flows.Storage.ceph.RookCeph import *

from tests.pytest.pytest_tools.operator.test_operator import CmdOutput
from tests.pytest.pytest_tools.operator.test_validation_base import ValidationTestBase, ValidationScenarioParams



class TestVerifyCephHealth(ValidationTestBase):
    scenario_prerequisite_not_fulfilled = [ValidationScenarioParams("prerequisite_not_fulfilled",
                                                                    {"sudo kubectl get namespaces -o jsonpath='{.items[?(@.metadata.name==\"rook-ceph\")].metadata.name}'": CmdOutput("xxx")})]

    scenario_prerequisite_fulfilled = [ValidationScenarioParams("prerequisite_fulfilled",
                                                                {"sudo kubectl get namespaces -o jsonpath='{.items[?(@.metadata.name==\"rook-ceph\")].metadata.name}'": CmdOutput("rook-ceph")})]

    tested_type = VerifyRookCephHealth
    cmd_getpod = "sudo kubectl -n rook-ceph get pods -lapp=ceph-oam -o jsonpath='{.items[0].metadata.name}'"
    pod_name="ceph-oam-64bf67ccf4-g68lr"
    cmd_namespace = "sudo kubectl get namespaces -o jsonpath='{.items[?(@.metadata.name==\"rook-ceph\")].metadata.name}'"
    cmd_podstatus = "sudo kubectl -n rook-ceph get pods -l app=ceph-oam -o=jsonpath='{.items[*].status.phase}'"
    cmd_rookstatus = "sudo kubectl -n rook-ceph exec -it {} -c ceph-oam -- ceph health".format(pod_name)

    scenario_passed = [
        ValidationScenarioParams(scenario_title="Passed",
                                 cmd_input_output_dict={
                                     cmd_getpod: CmdOutput("ceph-oam-64bf67ccf4-g68lr"),
                                     cmd_namespace: CmdOutput("rook-ceph"),
                                     cmd_podstatus: CmdOutput("Running"),
                                     cmd_rookstatus: CmdOutput("HEALTH_OK")
                                 }
                                 )]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="Failed",
                                 cmd_input_output_dict={
                                     cmd_getpod: CmdOutput("ceph-oam-64bf67ccf4-g68lr"),
                                     cmd_namespace: CmdOutput("rook-ceph"),
                                     cmd_podstatus: CmdOutput("Running"),
                                     cmd_rookstatus: CmdOutput("HEALTH_ERR")
                                 }
                                 )]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_prerequisite_not_fulfilled)
    def test_prerequisite_not_fulfilled(self, scenario_params, tested_object):
        ValidationTestBase.test_prerequisite_not_fulfilled(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_prerequisite_fulfilled)
    def test_prerequisite_fulfilled(self, scenario_params, tested_object):
        ValidationTestBase.test_prerequisite_fulfilled(self, scenario_params, tested_object)

