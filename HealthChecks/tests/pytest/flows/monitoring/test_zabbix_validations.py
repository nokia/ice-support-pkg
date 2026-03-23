from __future__ import absolute_import
import pytest

from flows.Monitoring.zabbix_validations import (CheckSelinuxContextForZabbix, VerifyControllerVirtualIp,
                                                 GetVirtualIPDetailsFromControllers)
from tests.pytest.pytest_tools.operator.test_operator import CmdOutput
from tests.pytest.pytest_tools.operator.test_validation_base import ValidationTestBase, ValidationScenarioParams
from tests.pytest.pytest_tools.operator.test_data_collector import DataCollectorTestBase, DataCollectorScenarioParams
from tests.pytest.tools.versions_alignment import Mock

class TestCheckSelinuxContextForZabbix(ValidationTestBase):
    tested_type = CheckSelinuxContextForZabbix

    cmd1 = "ls -laZ /var/lib/ | grep zabbix"
    out1 = "drwxrwxr-x. root        root        unconfined_u:object_r:var_lib_t:s0 zabbix"

    cmd2 = "ls -laZ /var/lib/zabbix/* | grep -v 'total'"
    out2 = """drwxrwxr-x. root root unconfined_u:object_r:var_lib_t:s0 .
drwxrwxr-x. root root unconfined_u:object_r:var_lib_t:s0 ..
-rw-r--r--. root root unconfined_u:object_r:var_lib_t:s0 ca.crt.pem
-rw-r--r--. root root unconfined_u:object_r:var_lib_t:s0 node.crt.pem
-rw-r--r--. root root unconfined_u:object_r:var_lib_t:s0 node.key.pem"""

    out3 = "drwxrwxr-x. root        root        unconfined_u:object_r:zabbix_var_lib_t:s0 zabbix"
    out4 = """drwxrwxr-x. root root unconfined_u:object_r:zabbix_var_lib_t:s0 .
    drwxrwxr-x. root root unconfined_u:object_r:zabbix_var_lib_t:s0 ..
    -rw-r--r--. root root unconfined_u:object_r:zabbix_var_lib_t:s0 ca.crt.pem
    -rw-r--r--. root root unconfined_u:object_r:zabbix_var_lib_t:s0 node.crt.pem
    -rw-r--r--. root root unconfined_u:object_r:zabbix_var_lib_t:s0 node.key.pem"""

    scenario_passed = [
        ValidationScenarioParams("Verify var_lib_t in all files",
                                 {cmd1: CmdOutput(out1),
                                  cmd2: CmdOutput(out2)}),
    ]

    scenario_failed = [
        ValidationScenarioParams("var_lib_t been modified",
                                 {cmd1: CmdOutput(out3),
                                  cmd2: CmdOutput(out4)}),
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

class TestGetVirtualIPDetailsFromControllers(DataCollectorTestBase):
    tested_type = GetVirtualIPDetailsFromControllers
    cmd = "less /usr/lib/zabbix/alertscripts/zabbix_cbis_snmp.py | grep send_to | grep -i ="
    cmd_out = "     send_to = '172.31.3.144'\n"
    out = "172.31.3.144"
    scenarios = [
        DataCollectorScenarioParams("get router virtual ip in controllers",cmd_input_output_dict= {cmd: CmdOutput(cmd_out)},
                                    scenario_res=out)
    ]

    @pytest.mark.parametrize("scenario_params", scenarios)
    def test_collect_data(self, scenario_params, tested_object):
        DataCollectorTestBase.test_collect_data(self, scenario_params, tested_object)

class TestVerifyControllerVirtualIp(ValidationTestBase):
    tested_type = VerifyControllerVirtualIp

    scenario_passed = [
        ValidationScenarioParams(scenario_title="Verify controller_virtual_ip in zabbix_cbis_snmp.py on all CBIS controller nodes",
                                 tested_object_mock_dict={"_get_hiera_data_ip": Mock(return_value="172.31.3.144")},
                                 data_collector_dict={
                                     GetVirtualIPDetailsFromControllers: {"overcloud-controller-cbis22-0": "172.31.3.144",
                                                                   "overcloud-controller-cbis22-1": "172.31.3.144",
                                                                   "overcloud-controller-cbis22-2": "172.31.3.144"}
                                 })
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="Verify that controller_virtual_ip differs across CBIS controller node in zabbix_cbis_snmp.py",
                                 tested_object_mock_dict={"_get_hiera_data_ip": Mock(return_value="172.31.3.144")},
                                 data_collector_dict={
                                     GetVirtualIPDetailsFromControllers: {"overcloud-controller-cbis22-0": "172.31.3.145",
                                                                   "overcloud-controller-cbis22-1": "172.31.3.144",
                                                                   "overcloud-controller-cbis22-2": "172.31.3.144"}
                                 })
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)
