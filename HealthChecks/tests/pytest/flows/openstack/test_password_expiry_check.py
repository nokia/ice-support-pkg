from __future__ import absolute_import
import pytest

from flows.OpenStack.Password_expiry_check import CheckCbisManagerNginxPodUserPasswordExpiry
from tests.pytest.pytest_tools.operator.test_operator import CmdOutput
from tests.pytest.pytest_tools.operator.test_validation_base import ValidationTestBase, ValidationScenarioParams


class TestCheckCbisManagerNginxPodUserPasswordExpiry(ValidationTestBase):
    tested_type = CheckCbisManagerNginxPodUserPasswordExpiry
    users_output = """manager_internal_user
cbis-admin
piyushnew
piyush"""

    future_expiry = "Password expires: Mar 15, 2027"
    past_expiry = "Password expires: Jan 01, 2026"
    soon_expiry = "Password expires: Feb 05, 2026"
    never_expiry = "Password expires: never"

    users_cmd = "sudo podman exec cbis-manager_nginx sh -c \"grep ':x:1[0-9][0-9][0-9]:' /etc/passwd | grep -o '^[^:]*'\""

    chage_manager_cmd = "sudo podman exec cbis-manager_nginx sh -c \"chage -l manager_internal_user | grep 'Password expires'\""
    chage_cbis_cmd = "sudo podman exec cbis-manager_nginx sh -c \"chage -l cbis-admin | grep 'Password expires'\""
    chage_piyushnew_cmd = "sudo podman exec cbis-manager_nginx sh -c \"chage -l piyushnew | grep 'Password expires'\""
    chage_piyush_cmd = "sudo podman exec cbis-manager_nginx sh -c \"chage -l piyush | grep 'Password expires'\""

    scenario_passed = [
        ValidationScenarioParams(
            scenario_title="passwords_not_expiring_within_2_weeks",
            cmd_input_output_dict={
                users_cmd: CmdOutput(users_output),
                chage_manager_cmd: CmdOutput(future_expiry),
                chage_cbis_cmd: CmdOutput(future_expiry),
                chage_piyushnew_cmd: CmdOutput(future_expiry),
                chage_piyush_cmd: CmdOutput(future_expiry),
            }
        )
    ]

    scenario_failed = [
        ValidationScenarioParams(
            scenario_title="password_expired_already",
            cmd_input_output_dict={
                users_cmd: CmdOutput(users_output),
                chage_manager_cmd: CmdOutput(past_expiry),
                chage_cbis_cmd: CmdOutput(never_expiry),
                chage_piyushnew_cmd: CmdOutput(never_expiry),
                chage_piyush_cmd: CmdOutput(never_expiry),
            }
        ),
        ValidationScenarioParams(
            scenario_title="password_expiring_soon",
            cmd_input_output_dict={
                users_cmd: CmdOutput(users_output),
                chage_manager_cmd: CmdOutput(soon_expiry),
                chage_cbis_cmd: CmdOutput(never_expiry),
                chage_piyushnew_cmd: CmdOutput(never_expiry),
                chage_piyush_cmd: CmdOutput(never_expiry),
            }
        )
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)