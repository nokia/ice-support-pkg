from __future__ import absolute_import
import pytest
from tests.pytest.tools.versions_alignment import Mock, patch

import tools.user_params
from HealthCheckCommon.operations import FlowsOperator
from tools.Exceptions import UnExpectedSystemOutput
from tools import sys_parameters


@pytest.fixture
def operator():
    host_executor = Mock()

    with patch.object(FlowsOperator, "__init__", lambda self, executor: None):
        operator_fixture = FlowsOperator(host_executor)
    operator_fixture._host_executor = host_executor
    operator_fixture._is_clean_cmd_info = False

    return operator_fixture


cached_pool = {}


def test_get_unique_name(operator):
    operator._unique_operation_name = "some name"
    assert operator._unique_operation_name == operator.get_unique_name()


@pytest.mark.parametrize("unique_name, expected_link", [("some_name", "https://some-link"), ("no_name", None)])
def test_get_documentation_link(operator, unique_name, expected_link):
    tools.user_params.name_to_url_dict = {
        "some_name": "https://some-link"}
    operator._unique_operation_name = unique_name

    assert operator.get_documentation_link() == expected_link


@pytest.mark.parametrize("get_not_ascii", [True, False])
@pytest.mark.parametrize("hosts_cached_pool", [cached_pool, None])
def test_run_cmd(operator, hosts_cached_pool, get_not_ascii):
    operator._host_executor.execute_cmd = Mock()
    operator._bash_cmd_lines = []
    operator._host_executor.execute_cmd.return_value = None, None, None

    res = operator.run_cmd("test cmd", 10, hosts_cached_pool=hosts_cached_pool, get_not_ascii=get_not_ascii)
    operator._host_executor.execute_cmd.assert_called_once_with("test cmd", 10, get_not_ascii=get_not_ascii)

    assert res == (None, None, None)

    if hosts_cached_pool:
        assert len(cached_pool) > 0
        operator.run_cmd("test cmd", 10, hosts_cached_pool=hosts_cached_pool, get_not_ascii=get_not_ascii)
        operator._host_executor.execute_cmd.assert_called_once_with("test cmd", 10, get_not_ascii=get_not_ascii)


@pytest.mark.parametrize("return_code, out, err", [(0, "some out", ""), (1, "", "some error")])
def test_get_output_from_run_cmd(operator, return_code, out, err):
    operator.run_cmd = Mock()
    operator.run_cmd.return_value = return_code, out, err

    if return_code == 0:
        res = operator.get_output_from_run_cmd("some cmd")
        operator.run_cmd.assert_called_once_with("some cmd", 30, None, False, False, True)
        assert res == out

    else:
        with pytest.raises(UnExpectedSystemOutput):
            operator.get_output_from_run_cmd("some cmd")
