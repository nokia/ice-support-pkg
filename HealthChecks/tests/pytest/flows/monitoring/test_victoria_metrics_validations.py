from __future__ import absolute_import
import copy
import warnings
import pytest
from mock.mock import Mock
from flows.Monitoring.victoria_metrics_validations import *
from HealthCheckCommon.validator import TableSystemInfo
from tests.pytest.pytest_tools.operator.test_data_collector import DataCollectorTestBase, DataCollectorScenarioParams
from tests.pytest.pytest_tools.operator.test_operator import CmdOutput
from tests.pytest.pytest_tools.operator.test_validation_base import ValidationTestBase, ValidationScenarioParams


# move back to HealthChecks/tests/pytest/flows/monitoring/test_victoria_metrics_validations.py

class TestVictoriaMetrixIsAvailable(ValidationTestBase):
    tested_type = VictoriaMetrixIsAvailable

    port_cmd = "sudo ss -ltnp | grep {} | grep {}".format(tested_type.PORT, tested_type.COMPONENT)
    curl_cmd = 'curl -H "Authorization: Basic `echo -n "{user}:{password}" | base64`" --insecure ' \
               'https://{ip}:{port}/api/v1/query -d "query=http_requests_total" |jq'.format(
        user=tested_type.USER_NAME, password="password", ip='192.168.1.1', port=tested_type.PORT)
    port_out = "192.168.1.1:{}".format(tested_type.PORT)
    out = '"status": "success"'

    scenario_passed = [
        ValidationScenarioParams("VictoriaMetrix is available on http",
                                 cmd_input_output_dict={port_cmd: CmdOutput(port_out),
                                                        curl_cmd: CmdOutput(out),
                                                        "sudo podman exec {} printenv VM_READ_PASS".format(
                                                            tested_type.COMPONENT): CmdOutput("password")},
                                 library_mocks_dict={"adapter.docker_or_podman": Mock(return_value="podman")}),
        ValidationScenarioParams("VictoriaMetrix is available on https",
                                 cmd_input_output_dict={port_cmd: CmdOutput(port_out),
                                                        curl_cmd: CmdOutput(out),
                                                        "sudo podman exec {} printenv VM_READ_PASS".format(
                                                            tested_type.COMPONENT): CmdOutput("password")},
                                 library_mocks_dict={"adapter.docker_or_podman": Mock(return_value="podman")
                                                     })
    ]

    scenario_failed = [
        ValidationScenarioParams("VictoriaMetrix is not available",
                                 cmd_input_output_dict={port_cmd: CmdOutput(port_out),
                                                        curl_cmd: CmdOutput(''),
                                                        "sudo podman exec {} printenv VM_READ_PASS".format(
                                                            tested_type.COMPONENT): CmdOutput("password")},
                                 library_mocks_dict={"adapter.docker_or_podman": Mock(return_value="podman")
                                                     })
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


class TestVictoriaMetricsHasAlarms(ValidationTestBase):
    tested_type = VictoriaMetricsHasAlarms

    class ResponseMock:
        def __init__(self, status_code, json):
            self.status_code = status_code
            self._json = json

        def json(self):
            return self._json

    class MyDateTime(datetime):
        @classmethod
        def now(cls):
            return datetime(2024, 2, 19, 12, 0, 0)

    alarms_list = [{
        "sourceObject": "system-cluster1/host-montreal-cluster1-edgebm-1",
        "text": "alm_secpam",
        "severity": "MAJOR",
        "repeatedCounter": 5,
        "createdAt": "2024-02-17T21:28:26.000Z",
        "lastSourceEventTime": "2024-02-18T09:18:00.000Z",

    }, {
        "sourceObject": "system-cluster1/host-montreal-cluster1-workerbm-2",
        "alarmCode": "UNIFIED_LOGGING_ALARM_EVENT",
        "text": "alm_secpam",
        "severity": "CRITICAL",
        "repeatedCounter": 5,
        "createdAt": "2024-02-17T21:28:26.000Z",
        "lastSourceEventTime": "2024-02-18T09:18:01.000Z",

    }]

    old_alarms_list = copy.deepcopy(alarms_list)
    old_alarms_list[1]["lastSourceEventTime"] = "2024-02-03T09:18:00.000Z"

    cmd = "sudo ss -ltnp | grep {}".format(tested_type.PORT)
    cmd_out = "192.168.1.1:{}".format(tested_type.PORT)
    scenario_passed = [
        ValidationScenarioParams("No alarms ipv4",
                                 cmd_input_output_dict={cmd: CmdOutput(cmd_out)},
                                 library_mocks_dict={
                                     "requests.get": Mock(return_value=ResponseMock(200, []))
                                 }),
        ValidationScenarioParams("Old critical alarm and new major alarm",
                                 cmd_input_output_dict={cmd: CmdOutput(cmd_out)},
                                 library_mocks_dict={
                                     "datetime": MyDateTime,
                                     "requests.get": Mock(return_value=ResponseMock(200, old_alarms_list))
                                 })
    ]

    scenario_failed = [
        ValidationScenarioParams("There are alarms",
                                 cmd_input_output_dict={cmd: CmdOutput(cmd_out)},
                                 library_mocks_dict={
                                     "datetime": MyDateTime,
                                     "requests.get": Mock(return_value=ResponseMock(200, alarms_list))
                                 })
    ]

    scenario_unexpected_system_output = [
        ValidationScenarioParams("status_code 400",
                                 cmd_input_output_dict={cmd: CmdOutput(cmd_out)},
                                 library_mocks_dict={
                                     "requests.get": Mock(return_value=ResponseMock(400, {}))
                                 })
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_unexpected_system_output(self, scenario_params, tested_object)

    def test_has_confluence(self, tested_object):
        # Override the func since this val doesn't have a confluence.
        # pls do not copy it! it's only for old validations that do not have a confluence page.
        warnings.warn("No confluence page")

    def test_sort_table_by_severity_and_time(self, tested_object):
        tested_object._table_system_info = TableSystemInfo(table=[
            ['2024-02-18T09:18:00.000Z', '2024-02-17T21:28:26.000Z', 'edgebm-1', 'major alarm', 'MAJOR', 5],
            ['2024-02-18T09:18:00.000Z', '2024-02-17T21:28:26.000Z', 'workerbm-2', 'critical alarm', 'CRITICAL', 5],
            ['2024-02-19T09:18:01.000Z', '2024-04-17T21:28:26.000Z', 'workerbm-0', 'unknown alarm', 'UNKNOWN', 5],
            ['2024-03-18T09:18:01.000Z', '2024-02-17T21:28:26.000Z', 'workerbm-2', 'newest major alarm', 'MAJOR', 5]
        ])

        tested_object._sort_table_by_time_and_severity()

        assert tested_object._table_system_info.table == [
            ['2024-03-18T09:18:01.000Z', '2024-02-17T21:28:26.000Z', 'workerbm-2', 'newest major alarm', 'MAJOR', 5],
            ['2024-02-19T09:18:01.000Z', '2024-04-17T21:28:26.000Z', 'workerbm-0', 'unknown alarm', 'UNKNOWN', 5],
            ['2024-02-18T09:18:00.000Z', '2024-02-17T21:28:26.000Z', 'workerbm-2', 'critical alarm', 'CRITICAL', 5],
            ['2024-02-18T09:18:00.000Z', '2024-02-17T21:28:26.000Z', 'edgebm-1', 'major alarm', 'MAJOR', 5]
        ]


class TestGrafanaIsAvailable(ValidationTestBase):
    tested_type = GrafanaIsAvailable

    scenario_passed = [
        ValidationScenarioParams("Verify Grafana is available",
                                 data_collector_dict={GetGrafanaProcessFromManagers: {"manager-0": "GRAFANA_RUNNING"}} 
                                )
    ]
    scenario_failed = [
        ValidationScenarioParams("Verify Grafana is not available 1",
                                data_collector_dict={GetGrafanaProcessFromManagers: {"manager-0": "NA"}}),
        ValidationScenarioParams("Verify Grafana is not available 2",
                                data_collector_dict={GetGrafanaProcessFromManagers: {"manager-0": "GRAFANA_NOT_RUNNING"}})
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


class TestGetGrafanaProcessFromManagers(DataCollectorTestBase):
    tested_type = GetGrafanaProcessFromManagers
    cmd = 'curl http://{ip}:3000/login'.format(ip='192.168.1.1')

    scenarios = [
        DataCollectorScenarioParams(
            scenario_title="good scenario",
            cmd_input_output_dict={
                cmd: CmdOutput(out="out", return_code=0)},
            scenario_res="GRAFANA_RUNNING"
        ),
        DataCollectorScenarioParams(
            scenario_title="bad scenario",
            cmd_input_output_dict={
                cmd: CmdOutput(out="out", return_code=1)},
            scenario_res="GRAFANA_NOT_RUNNING"
        )
    ]

    @pytest.mark.parametrize("scenario_params", scenarios)
    def test_collect_data(self, scenario_params, tested_object):
        DataCollectorTestBase.test_collect_data(self, scenario_params, tested_object, port=3000, component='grafana')

    def _init_mocks(self, tested_object):
        tested_object.system_utils.get_ip_from_ss = Mock()
        tested_object.system_utils.get_ip_from_ss.return_value = '192.168.1.1'
