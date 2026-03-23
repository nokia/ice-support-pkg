from __future__ import absolute_import
import pytest
import warnings

from tests.pytest.tools.versions_alignment import Mock

from flows.ICE.ICEInternalValidations import VerifyIceContainerRuntime
from tests.pytest.pytest_tools.operator.test_operator import CmdOutput
from tests.pytest.pytest_tools.operator.test_validation_base import ValidationTestBase, ValidationScenarioParams


class TestCheckDiskUsage(ValidationTestBase):
    tested_type = VerifyIceContainerRuntime

    scenario_passed = [
        ValidationScenarioParams(scenario_title="scenario_passed",
                                 cmd_input_output_dict={
                                     'sudo podman ps --format "{{.Status}} {{.Names}}"| grep ice-': CmdOutput(
                                         out="Up 2 minutes ago ice-healthcheck-1")},
                                 library_mocks_dict={"adapter.docker_or_podman": Mock(return_value="podman")})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="scenario_failed",
                                 cmd_input_output_dict={
                                     'sudo podman ps --format "{{.Status}} {{.Names}}"| grep ice-': CmdOutput(
                                         out="Up 2 days ago ice-healthcheck-1"),
                                     "sudo podman inspect -f '{{ .State.StartedAt }}' ice-healthcheck-1": CmdOutput(
                                         out="2025-01-28 13:26:30.605695417 +0000 UTC"),
                                     'sudo podman logs --tail 10 ice-healthcheck-1': CmdOutput(
                                         out="""ten log lines"""
                                     )},
                                 library_mocks_dict={"adapter.docker_or_podman": Mock(return_value="podman")},
                                 failed_msg="Some containers are running for too much time:\ncontainer: "
                                            "ice-healthcheck-1, status: Up 2 days ago, "
                                            "start_time: 2025-01-28 13:26:30.605695417 +0000 UTC"),
        ValidationScenarioParams(scenario_title="scenario_failed 2 containers",
                                 cmd_input_output_dict={
                                     'sudo podman ps --format "{{.Status}} {{.Names}}"| grep ice-': CmdOutput(
                                         out="Up 2 days ago ice-healthcheck-1\nUp 2 monthes ago ice-healthcheck-2\nUp 2 minutes ago ice-healthcheck-3"),
                                     "sudo podman inspect -f '{{ .State.StartedAt }}' ice-healthcheck-1": CmdOutput(
                                         out="2025-01-28 13:26:30.605695417 +0000 UTC"),
                                     'sudo podman logs --tail 10 ice-healthcheck-1': CmdOutput(
                                         out="""ten1 log lines"""),
                                     "sudo podman inspect -f '{{ .State.StartedAt }}' ice-healthcheck-2": CmdOutput(
                                         out="2024-11-28 13:26:30.605695417 +0000 UTC"),
                                     'sudo podman logs --tail 10 ice-healthcheck-2': CmdOutput(
                                         out="""ten2 log lines""")},
                                 library_mocks_dict={"adapter.docker_or_podman": Mock(return_value="podman")},
                                 failed_msg="Some containers are running for too much time:\ncontainer: "
                                            "ice-healthcheck-1, status: Up 2 days ago, "
                                            "start_time: 2025-01-28 13:26:30.605695417 +0000 UTC\n"
                                            "container: ice-healthcheck-2, status: Up 2 monthes ago, "
                                            "start_time: 2024-11-28 13:26:30.605695417 +0000 UTC")
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    def test_has_confluence(self, tested_object):
        # Override the func since this val doesn't have a confluence.
        # pls do not copy it! it's only for old validations that do not have a confluence page.
        warnings.warn("No confluence page")
