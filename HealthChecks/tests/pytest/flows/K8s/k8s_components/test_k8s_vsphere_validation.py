from __future__ import absolute_import
import pytest

from flows.K8s.k8s_components.k8s_vsphere_validation import ValidateProviderId
from tests.pytest.pytest_tools.operator.test_operator import CmdOutput
from tests.pytest.pytest_tools.operator.test_validation_base import ValidationTestBase, ValidationScenarioParams


class TestValidateProviderId(ValidationTestBase):
    tested_type = ValidateProviderId
    cmd_input_output_dict_passed = {
        "sudo /usr/local/bin/kubectl get nodes -o=jsonpath='{range .items[*]}{.metadata.name}{\" \"}{end}'": CmdOutput(
            out="ncs-vc-ctrl-1 ncs-vc-ctrl-2 ncs-vc-ctrl-3 ncs-vc-edg-1 ncs-vc-edg-2 ncs-vc-wrk-1 ncs-vc-wrk-2"),
        "sudo /usr/local/bin/kubectl get node ncs-vc-ctrl-1 -o 'jsonpath={.spec.providerID}'": CmdOutput(
            out="vsphere://42249b37-ed1b-c2db-e5d4-e1a933b366c0"),
        "sudo /usr/local/bin/kubectl get node ncs-vc-ctrl-2 -o 'jsonpath={.spec.providerID}'": CmdOutput(
            out="vsphere://42245b9e-0df7-c335-ef9e-2d0efabe151c"),
        "sudo /usr/local/bin/kubectl get node ncs-vc-ctrl-3 -o 'jsonpath={.spec.providerID}'": CmdOutput(
            out="vsphere://42245470-c58b-fb06-7bcc-ef36cea0f0b9"),
        "sudo /usr/local/bin/kubectl get node ncs-vc-edg-1 -o 'jsonpath={.spec.providerID}'": CmdOutput(
            out="vsphere://422421d8-1a60-1aae-60a5-3ffd06f3bc52"),
        "sudo /usr/local/bin/kubectl get node ncs-vc-edg-2 -o 'jsonpath={.spec.providerID}'": CmdOutput(
            out="vsphere://42246cb9-622d-29c1-11bf-a18687755383"),
        "sudo /usr/local/bin/kubectl get node ncs-vc-wrk-1 -o 'jsonpath={.spec.providerID}'": CmdOutput(
            out="vsphere://4224497e-a3ab-c554-66e9-b1a4259542d0"),
        "sudo /usr/local/bin/kubectl get node ncs-vc-wrk-2 -o 'jsonpath={.spec.providerID}'": CmdOutput(
            out="vsphere://422457b6-5eee-3360-f592-ab5a94c7b8bc")
    }

    cmd_input_output_dict_failed = {
        "sudo /usr/local/bin/kubectl get nodes -o=jsonpath='{range .items[*]}{.metadata.name}{\" \"}{end}'": CmdOutput(
            out="ncs-vc-ctrl-1 ncs-vc-ctrl-2"),
        "sudo /usr/local/bin/kubectl get node ncs-vc-ctrl-1 -o 'jsonpath={.spec.providerID}'": CmdOutput(
            out="vsphere://42249b37-ed1b-c2db-e5d4-e1a933b366c0"),
        "sudo /usr/local/bin/kubectl get node ncs-vc-ctrl-2 -o 'jsonpath={.spec.providerID}'": CmdOutput(
            out="wrong_vsphere://42245b9e-0df7-c335-ef9e-2d0efabe151c"),
    }

    scenario_passed = [
        ValidationScenarioParams(scenario_title="vsphere in out",
                                 cmd_input_output_dict=cmd_input_output_dict_passed)
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="vsphere not in out",
                                 cmd_input_output_dict=cmd_input_output_dict_failed)
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

