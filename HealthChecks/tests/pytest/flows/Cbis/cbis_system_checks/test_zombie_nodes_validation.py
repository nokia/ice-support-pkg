from __future__ import absolute_import
import warnings

import pytest
from tests.pytest.tools.versions_alignment import Mock

from flows.Cbis.cbis_system_checks.zombie_nodes_validation import CheckZombieNodes
from tests.pytest.pytest_tools.operator.test_operator import CmdOutput
from tests.pytest.pytest_tools.operator.test_validation_base import ValidationTestBase, ValidationScenarioParams
from tools.Exceptions import UnExpectedSystemOutput


class TestCheckZombieNodes(ValidationTestBase):
    tested_type = CheckZombieNodes

    STACKRC_PATH = '/home/stack/stackrc_locked'
    cmd = "source {}; openstack port list --column 'Fixed IP Addresses' --format value".format(STACKRC_PATH)

    os_port_list = """ip_address='172.17.3.26', subnet_id='94404961-d3cf-479f-985b-e55a197886d3'
                      ip_address='172.31.0.28', subnet_id='5c401320-4587-4e0a-9816-6166710d99a8'
                      ip_address='172.17.3.16', subnet_id='94404961-d3cf-479f-985b-e55a197886d3'"""

    # IPs involved in testing
    ZOMBIE_IP_OK = '172.17.3.17'
    ZOMBIE_IP_FAILING = '172.31.1.242'

    # Simple output mocks for IPMI commands
    MOCKED_IPMI_OUTPUT_OK = "IP Address : 192.168.0.17"
    MOCKED_IPMI_OUTPUT_FAIL = "IP Address : 192.168.0.242"

    # --- Command Keys Defined Directly ---
    # The complex command string template (using string concatenation)
    IPMI_CMD_TEMPLATE = (
        "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=2 -F /dev/null -o GlobalKnownHostsFile=/dev/null -o"
        " UserKnownHostsFile=/dev/null -F /dev/null  heat-admin@{} 'sudo ipmitool lan print'"
        " 2>/dev/null"
    )

    # Command Keys
    IPMI_CMD_OK = IPMI_CMD_TEMPLATE.format(ZOMBIE_IP_OK)
    IPMI_CMD_FAIL = IPMI_CMD_TEMPLATE.format(ZOMBIE_IP_FAILING)

    scenario_passed = [
        ValidationScenarioParams(scenario_title="basic scenario - PASS",
                                 tested_object_mock_dict={
                                     # FIX 1: Mock both start (16) and end (20) IP for the two calls
                                     "_get_dhcp_range_from_conf": Mock(side_effect=["172.17.3.16", "172.17.3.20"]),

                                     # FIX 2: Mocking IPMI failure command keys for safety (required by base class)
                                     IPMI_CMD_OK: CmdOutput(MOCKED_IPMI_OUTPUT_OK),
                                     IPMI_CMD_FAIL: CmdOutput(MOCKED_IPMI_OUTPUT_FAIL)
                                 },
                                 cmd_input_output_dict={
                                     cmd: CmdOutput(
                                         os_port_list),
                                     'for i in {16..20} ;do (ping 172.17.3.$i -c 1 -w 5  >/dev/null '
                                     '&& echo "172.17.3.$i" &) ;done': CmdOutput("172.17.3.16")

                                 }
                                 )
    ]

    scenario_failed = [
        ValidationScenarioParams(
            scenario_title="basic scenario - FAIL (Zombie Node found)",
            tested_object_mock_dict={
                "_get_dhcp_range_from_conf": Mock(side_effect=['172.17.3.16', '172.17.3.20']),
            },
            cmd_input_output_dict={
                cmd: CmdOutput(os_port_list),

                'for i in {16..20} ;do (ping 172.17.3.$i -c 1 -w 5  >/dev/null && echo "172.17.3.$i" &) ;done': CmdOutput(
                    "172.17.3.16\n" + ZOMBIE_IP_OK + "\n" + ZOMBIE_IP_FAILING),

                # Mock 1: The intended zombie IP
                IPMI_CMD_OK: CmdOutput(MOCKED_IPMI_OUTPUT_OK),

                # Mock 2: The unexpected failing IP
                IPMI_CMD_FAIL: CmdOutput(MOCKED_IPMI_OUTPUT_FAIL)
            }
        )
    ]

    def _init_mocks(self, tested_object):
        tested_object.system_utils.get_stackrc_file_path = Mock()
        tested_object.system_utils.get_stackrc_file_path.return_value = self.STACKRC_PATH

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    def test_has_confluence(self, tested_object):
        warnings.warn("No confluence page")

    @pytest.mark.parametrize("dhcp_start_out, expected_res", [("dhcp_start = 172.31.0.4", "172.31.0.4"),
                                                              ("dhcp_start = 172.31.0.4\ndhcp_start = 172.31.0.4",
                                                               "172.31.0.4")])
    def test_get_dhcp_range_from_conf(self, dhcp_start_out, expected_res, tested_object):
        tested_object.get_output_from_run_cmd = Mock(return_value=dhcp_start_out)
        assert tested_object._get_dhcp_range_from_conf("dhcp_start") == expected_res
        tested_object.get_output_from_run_cmd.assert_called_once_with("grep dhcp_start /home/stack/undercloud.conf "
                                                                      "|grep -v '#'")
