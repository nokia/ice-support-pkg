from __future__ import absolute_import
from datetime import datetime, timedelta
from HealthCheckCommon.operations import *
from HealthCheckCommon.validator import Validator, InformatorValidator
from enum import Enum
import requests
from requests.exceptions import ConnectionError
from HealthCheckCommon.table_system_info import TableSystemInfo
from HealthCheckCommon.validator import Validator, InformatorValidator
from tools import adapter
from tools.Exceptions import UnExpectedSystemOutput
from tools.global_enums import Objectives, Severity
from six.moves import filter

class VictoriaMetrixIsAvailable(Validator):
    objective_hosts = [Objectives.ONE_MANAGER]
    PORT = 8427
    COMPONENT = 'vmauth'
    USER_NAME = 'vm-read'

    def set_document(self):
        self._unique_operation_name = "validate_victoria_metrics_is_available"
        self._title = "Check VictoriaMetrix is available by getting Prometheus metrix"
        self._failed_msg = "Failed to get Prometheus metrix from VictoriaMetrix"
        self._severity = Severity.WARNING
        self._is_clean_cmd_info = True
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        virtual_ip = self.system_utils.get_ip_from_ss(self.PORT, self.COMPONENT)
        password = self.get_output_from_run_cmd("sudo {docker_or_podman} exec {component} printenv VM_READ_PASS".format(
            docker_or_podman=adapter.docker_or_podman(), component=self.COMPONENT), add_bash_timeout=True).strip()
        cmd = 'curl -H "Authorization: Basic `echo -n "{}:{}" | base64`" --insecure https://{}:{}/api/v1/query ' \
              '-d "query=http_requests_total" |jq'.format(self.USER_NAME, password, virtual_ip, self.PORT)
        out = self.get_output_from_run_cmd(cmd)
        if out:
            return True
        else:
            return False


class VictoriaMetricsHasAlarms(InformatorValidator):
    objective_hosts = [Objectives.ONE_MANAGER]
    PORT = 8182

    class TableIndexes(Enum):
        LAST_SOURCE_EVENT_TIME = 0
        CREATED_AT = 1
        SOURCE_OBJECT = 2
        TEXT = 3
        SEVERITY = 4
        REPEAT_COUNTER = 5

    def set_document(self):
        self._unique_operation_name = "validate_victoria_metrics_does_not_have_alarms"
        self._title = "Check Victoria Metrix does not have critical alarms"
        self._failed_msg = "There are critical alarms from victoria metrics - for more information check out 'VICTORIA METRIX VALIDATIONS' tab"
        self._severity = Severity.NOTIFICATION
        self._is_pure_info = False

        self._table_system_info = TableSystemInfo(table=[], headers=["Last Source Event Time", "Created At", "Source Object", "Text", "Severity",
                                                                     "Repeated Counter"], print_host_as_title=False)
        self._title_of_info = "Victoria Metrix alarms"
        self._implication_tags = [ImplicationTag.SYMPTOM]

    def is_validation_passed(self):
        virtual_ip = self.system_utils.get_ip_from_ss(self.PORT)
        url = "http://{}:{}/api/alma/alarms".format(virtual_ip, self.PORT)

        try:
            response = requests.get(url, timeout=30)
        except ConnectionError:
            raise UnExpectedSystemOutput(self.get_host_ip(),
                                         "curl http://{}:8182/api/alma/alarms -v 2".format(virtual_ip),
                                         "Couldn't connect to API",
                                         "Failed to get victoria metrics from API.")

        if response.status_code != 200:
            raise UnExpectedSystemOutput(self.get_host_ip(),
                                         "curl http://{}:8182/api/alma/alarms -v 2".format(virtual_ip),
                                         "status code: {}".format(response.status_code),
                                         "Failed to get victoria metrics from API.")

        json_response = response.json()

        if not json_response:
            return True

        for alarm in json_response:
            alarm_line = [alarm["lastSourceEventTime"], alarm["createdAt"], alarm["sourceObject"], alarm["text"],
                          alarm["severity"], alarm["repeatedCounter"]]
            self._table_system_info.table.append(alarm_line)

        self._table_system_info.table = self._remove_duplications_from_table()
        self._sort_table_by_time_and_severity()
        self._table_system_info.table = list(filter(self._is_in_last_two_weeks, self._table_system_info.table))

        if self._is_critical_alarm_appear():
            return False

        return True

    def _sort_table_by_time_and_severity(self):
        self._table_system_info.table.sort(key=self._get_time_and_severity_order_from_alarm, reverse=True)

    def _get_time_and_severity_order_from_alarm(self, alarm):
        severity_mapping = {"CRITICAL": 3, "MAJOR": 2, "WARNING": 1, "MINOR": 0}

        alarm_datetime = self._convert_time_str_to_datetime(alarm[self.TableIndexes.LAST_SOURCE_EVENT_TIME.value])
        alarm_severity = severity_mapping.get(alarm[self.TableIndexes.SEVERITY.value], -1)

        return alarm_datetime, alarm_severity

    def _remove_duplications_from_table(self):
        return [list(t) for t in {tuple(lst) for lst in self._table_system_info.table}]

    def _is_in_last_two_weeks(self, alarm):
        threshold_date = datetime.now() - timedelta(weeks=2)
        last_alarm_event_time = self._convert_time_str_to_datetime(
            alarm[self.TableIndexes.LAST_SOURCE_EVENT_TIME.value])

        return last_alarm_event_time >= threshold_date

    def _convert_time_str_to_datetime(self, time_str):
        return datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S.%fZ")

    def _is_critical_alarm_appear(self):
        return any([alarm[self.TableIndexes.SEVERITY.value] == "CRITICAL" for alarm in self._table_system_info.table])


#####   SOUVIK DAS  |   ICET-2657   #####
#####   DATE :    08-11-2024
#####   ICET BUG FIX | GRAFANA PROCESS runs via HAPROXY and at a time it runs on only one CENTRALSITE MANAGER node on CONFIG 5 setup or on one MASTER node on a CONFIG 2/4 setup

class GetGrafanaProcessFromManagers(DataCollector):
    objective_hosts = [Objectives.MANAGERS]
    def collect_data(self, port, component):
        try:
            virtual_ip = self.system_utils.get_ip_from_ss(port, component)
        except UnExpectedSystemOutput:
            return "GRAFANA_NOT_RUNNING"
        url = "http://{}:{}/login".format(virtual_ip, port)
        return_code, out, err = self.run_cmd('curl {}'.format(url))
        if return_code == 0:
            return "GRAFANA_RUNNING"
        else:
            return "GRAFANA_NOT_RUNNING"

class GrafanaIsAvailable(Validator):
    objective_hosts = [Objectives.ONE_MANAGER]
    PORT = 3000             ### CONSTAND VALUES FOR GRAFANA
    COMPONENT = 'grafana'       #### ### CONSTAND VALUES FOR GRAFANA

    def set_document(self):
        self._unique_operation_name = "validate_grafana_is_available"
        self._title = "Verify Grafana is available"
        self._failed_msg = "Grafana isn't available\n"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        values_dict = self.run_data_collector(GetGrafanaProcessFromManagers, port=self.PORT, component=self.COMPONENT)
        PASS_FLAG = 0
        grafana_status_on_managers = {}
        for key, value in list(values_dict.items()):
            if value == "GRAFANA_RUNNING":
                PASS_FLAG = PASS_FLAG + 1
                grafana_status_on_managers[key] = value
        
        if (PASS_FLAG == 1):
            return True
        elif (PASS_FLAG > 1):
            self._failed_msg = "Grafana is Running on More than One Manager, As Grafana service is Part of HAPROXY so at a time only on one Manager node GRAFANA should be active and Running.\n" + str(grafana_status_on_managers)
            return False
        else:
            self._failed_msg = self._failed_msg + "\n" + str(values_dict)
            return False