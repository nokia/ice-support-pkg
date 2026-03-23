from __future__ import absolute_import
import pytest
from HealthCheckCommon.system_utils import SystemUtils
from tests.pytest.tools.versions_alignment import Mock
from tools.Exceptions import UnExpectedSystemOutput


@pytest.fixture
def system_utils():
    return SystemUtils(Mock())


cmd_out_with_component_ipv4 = 'LISTEN 0      4096    192.168.1.1:3000      [::]:*    users:(("grafana",pid=108196,fd=10))'
cmd_out_with_component_short_ipv6 = 'LISTEN 0      4096    [2001:a:a::3]:3000      [::]:*    users:(("grafana",pid=108196,fd=10))'
cmd_out_without_component_full_ipv6 = """
LISTEN 0      4096    [2a00:8a00:4000:6009::b:6f05]:3000          [::]:*    users:(("grafana",pid=108196,fd=10))
LISTEN 0      4096    [2a00:8a00:4000:6009::b:6f05]:3000          [::]:*    users:(("grafana",pid=108196,fd=10))
"""
expected_res_ipv4 = "192.168.1.1"
expected_res_short_ipv6 = "[2001:a:a::3]"
expected_res_full_ipv6 = "[2a00:8a00:4000:6009::b:6f05]"


@pytest.mark.parametrize("component, cmd_out, expected_res",
                         [('grafana', cmd_out_with_component_ipv4, expected_res_ipv4),
                          (None, cmd_out_with_component_short_ipv6, expected_res_short_ipv6),
                          (None, cmd_out_without_component_full_ipv6, expected_res_full_ipv6)])
def test_get_ip_from_ss(system_utils, component, cmd_out, expected_res):
    system_utils.operator.get_output_from_run_cmd = Mock()
    system_utils.operator.get_output_from_run_cmd.return_value = cmd_out
    res = system_utils.get_ip_from_ss(3000, component)
    expected_cmd = "sudo ss -ltnp | grep 3000"
    if component:
        expected_cmd = "{} | grep {}".format(expected_cmd, component)
    system_utils.operator.get_output_from_run_cmd.assert_called_once_with(expected_cmd)
    assert expected_res == res


def test_get_ip_from_ss_unexcpected(system_utils):
    cmd_out = 'LISTEN 0      4096    2a00:8a00:4000:600:3000      users:(("grafana",pid=108196,fd=10))'
    system_utils.operator.get_output_from_run_cmd = Mock()
    system_utils.operator.get_output_from_run_cmd.return_value = cmd_out
    with pytest.raises(UnExpectedSystemOutput):
        system_utils.get_ip_from_ss(3000)


@pytest.mark.parametrize(
    "ss_output, expected_ip, should_raise",
    [
        # 1. IPv4 with correct port
        ("LISTEN 0 128 192.168.0.42:8080 users:((", "192.168.0.42", False),

        # 2. IPv6 with correct port
        ("LISTEN 0 128 [2001:db8::1]:8080 users:((", "[2001:db8::1]", False),

        # 3. Multiple IPs, only one with correct port
        (
            "LISTEN 0 128 10.0.0.1:1111 192.168.1.5:8080 [2001:db8::2]:9999 users:((",
            "192.168.1.5",
            False,
        ),

        # 4. IPs but none with correct port (should fail)
        ("LISTEN 0 128 10.0.0.1:1111 [2001:db8::2]:9999 users:((", None, True),
    ]
)
def test_get_ip_from_ss(system_utils, ss_output, expected_ip, should_raise, port="8080"):
    system_utils.operator.get_output_from_run_cmd.return_value = ss_output
    system_utils.operator.get_host_ip.return_value = "127.0.0.1"

    if should_raise:
        with pytest.raises(UnExpectedSystemOutput):
            system_utils.get_ip_from_ss(port)
    else:
        ip = system_utils.get_ip_from_ss(port)
        assert ip == expected_ip
