from __future__ import absolute_import
import copy
import warnings
import datetime

import pytest
from tests.pytest.tools.versions_alignment import patch

from flows.K8s.k8s_components.k8s_sanity_checks import AllNodesHaveRoutesToAPIServer, K8DefaultServiceIpDataCollector, \
    NodeAreReadyValidetor, RootCertificateExpiryValidator, TotalNumberOfPodsPerCluster, CheckBCMTRegistry
from tests.pytest.pytest_tools.operator.test_data_collector import DataCollectorTestBase, DataCollectorScenarioParams
from tests.pytest.pytest_tools.operator.test_operator import CmdOutput
from tests.pytest.pytest_tools.operator.test_validation_base import ValidationTestBase, ValidationScenarioParams
from tools.global_enums import Version


class TestAllNodesHaveRoutesToAPIServer(ValidationTestBase):
    tested_type = AllNodesHaveRoutesToAPIServer

    out = "kubernetes   ClusterIP   10.254.0.1   <none>   443/TCP   37d"
    cmd = "sudo kubectl get svc kubernetes -n default --no-headers"

    scenario_passed = [
        ValidationScenarioParams(scenario_title="version 19",
                                 cmd_input_output_dict={cmd: CmdOutput(out)},
                                 data_collector_dict={
                                     K8DefaultServiceIpDataCollector: {"fi-803-hpe-bm-workerbm-2": True}
                                 },
                                 version=Version.V19A)
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="version 19",
                                 cmd_input_output_dict={cmd: CmdOutput(out)},
                                 data_collector_dict={K8DefaultServiceIpDataCollector: {
                                     "fi-803-hpe-bm-workerbm-2": False
                                 }})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestK8DefaultServiceIpDataCollector(DataCollectorTestBase):
    tested_type = K8DefaultServiceIpDataCollector

    out = """
    10.254.0.1 {} infra-bond src 172.31.0.14 uid 0
    cache
    """

    scenarios = [
        DataCollectorScenarioParams("dev in out", {"sudo ip r g {ip}": CmdOutput(out.format("dev"))},
                                    scenario_res=True),
        DataCollectorScenarioParams("via in out", {"sudo ip r g {ip}": CmdOutput(out.format("via"))},
                                    scenario_res=True),
        DataCollectorScenarioParams("no dev or via in out", {"sudo ip r g {ip}": CmdOutput(out.format("no"))},
                                    scenario_res=False)
    ]

    kwargs_list = [
        {"ip_address": "10.10.10.10"}
    ]

    @pytest.mark.parametrize("kwargs", kwargs_list)
    @pytest.mark.parametrize("scenario_params", scenarios)
    def test_collect_data(self, scenario_params, kwargs, tested_object):
        self._format_cmd_keys(kwargs, scenario_params)

        DataCollectorTestBase.test_collect_data(self, scenario_params, tested_object, **kwargs)

    def _format_cmd_keys(self, kwargs, scenario_params):
        scenario_params_cmds_copy = copy.deepcopy(scenario_params.cmd_input_output_dict)
        for key, val in list(scenario_params_cmds_copy.items()):
            scenario_params.cmd_input_output_dict[key.format(ip=kwargs["ip_address"])] = \
                scenario_params.cmd_input_output_dict.pop(key)


class TestNodeAreReadyValidetor(ValidationTestBase):
    tested_type = NodeAreReadyValidetor

    validation_cmd = "sudo kubectl get nodes --no-headers"
    out = """fi-803-hpe-bm-edgebm-0     {state}   <none>   290d   v1.19.5
             fi-803-hpe-bm-masterbm-0   {state}   <none>   290d   v1.19.5
             fi-803-hpe-bm-workerbm-0   {state}   <none>   76d    v1.19.5"""

    scenario_passed = [
        ValidationScenarioParams(scenario_title="All nodes are ready",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out.format(state="Ready"))})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="Not all nodes are ready",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out.format(state='Other state'))}),
        ValidationScenarioParams(scenario_title="Could not get a list of nodes",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out="")})
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


class TestRootCertificateExpiryValidator(ValidationTestBase):
    tested_type = RootCertificateExpiryValidator

    fake_now_time = datetime.datetime(2023, 1, 2, 0, 0, 0)

    scenario_passed = [
        ValidationScenarioParams(
            scenario_title="passed scenario",
            cmd_input_output_dict={"sudo openssl x509 -enddate -noout -in /etc/kubernetes/ssl/ca.pem"
                                   : CmdOutput(out="notAfter=Aug 30 21:00:59 2024 GMT")}
        )
    ]

    scenario_failed = [
        ValidationScenarioParams(
            scenario_title="Expired yesterday",
            cmd_input_output_dict={"sudo openssl x509 -enddate -noout -in /etc/kubernetes/ssl/ca.pem"
                                   : CmdOutput(out="notAfter=Jan 01 21:00:59 2023 GMT")},
            failed_msg="The root certificate already expired."
        ),
        ValidationScenarioParams(
            scenario_title="will be expired in 59 days",
            cmd_input_output_dict={"sudo openssl x509 -enddate -noout -in /etc/kubernetes/ssl/ca.pem"
                                   : CmdOutput(out="notAfter=Mar 01 21:00:59 2023 GMT")},
            failed_msg="The expiry date of root cert is: Mar 01 21:00:59 2023 GMT. it is less than 180 days. "
                       "It will be expired in 58 days from today."
        )
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        with patch("flows.K8s.k8s_components.k8s_sanity_checks.datetime.datetime") as date_time_mock:
            date_time_mock.now.return_value = self.fake_now_time
            ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        with patch("flows.K8s.k8s_components.k8s_sanity_checks.datetime.datetime") as date_time_mock:
            date_time_mock.now.return_value = self.fake_now_time
            ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestTotalNumberOfPodsPerCluster(ValidationTestBase):
    tested_type = TotalNumberOfPodsPerCluster

    validation_cmd = "sudo kubectl get pods -A --no-headers | wc -l"

    scenario_passed = [
        ValidationScenarioParams(scenario_title="Less than 17000 pods running on cluster",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out=100)})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="Not all nodes are ready",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out=18000)})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


#class TestEtcdPerformanceCheck(ValidationTestBase):
#    tested_type = EtcdPerformanceCheck
#
#    find_command = "find /var/log -maxdepth 1 -type f -name 'messages-*' -exec ls -t {} +"
#    result = "/var/log/messages-20240225  /var/log/messages-20240218  /var/log/messages-20240211  /var/log/messages-20240204"
#    grep_cmd = "sudo grep 'took too long' /var/log/messages-20240225 | wc -l"
#
#    pattern_string = ''.join('"took too long " "took":"3.123{}s",'.format(i) for i in range(2, 1002))
#    pattern_string = pattern_string.rstrip(',')
#    test_string = '{{"data":[{}]}}'.format(pattern_string)
#
#    pattern_string_f = ''.join('"took too long " "took":"3.123{}s",'.format(i) for i in range(2, 2000))
#    pattern_string_f = pattern_string_f.rstrip(',')
#    test_string_f = '{{"data":[{}]}}'.format(pattern_string_f)
#
#    scenario_passed = [
#        ValidationScenarioParams(scenario_title="good performance",
#                                 cmd_input_output_dict={find_command: CmdOutput(result),
#                                                        grep_cmd: CmdOutput('1002')})
#    ]
#
#    scenario_failed = [
#        ValidationScenarioParams(scenario_title="bad performance",
#                                 cmd_input_output_dict={find_command: CmdOutput(result),
#                                                        grep_cmd: CmdOutput('2003')})
#    ]
#
#    @pytest.mark.parametrize("scenario_params", scenario_passed)
#    def test_scenario_passed(self, scenario_params, tested_object):
#        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)
#
#    @pytest.mark.parametrize("scenario_params", scenario_failed)
#    def test_scenario_failed(self, scenario_params, tested_object):
#        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

class TestCheckBCMTRegistry(ValidationTestBase):
    tested_type = CheckBCMTRegistry

    out_good = '''
    {"repositories":["bcmt/bcmt-autoscaler"]}
    '''

    out_bad = '''
    {}
    '''
    out_bad2 = '''
    curl: (7) Failed connect to bcmt-registry:5000; Connection refused
    '''

    validation_cmd = "sudo curl --max-time 10 https://bcmt-registry:5000/v2/_catalog?n=1 --cacert /etc/kubernetes/ssl/ca.pem"

    scenario_passed = [
        ValidationScenarioParams(scenario_title="BCMT registry is resolved",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out=out_good)})

    ]

    scenario_failed = [
        ValidationScenarioParams("exit code non-zero", cmd_input_output_dict={validation_cmd: CmdOutput(out_bad2, 2)},
                                 failed_msg="Failed to connect to bcmt-registry"),
        ValidationScenarioParams("exit code 35", cmd_input_output_dict={validation_cmd: CmdOutput(out_bad2, 35)},
                                 failed_msg="Failed to connect to bcmt-registry, SSL handshake failure."),
        ValidationScenarioParams("exit code zero but no repos", cmd_input_output_dict={validation_cmd: CmdOutput(out_bad, 0)},
                                 failed_msg="No repositories found in bcmt-registry"),
    ]

    scenario_unexpected_system_output = [
        ValidationScenarioParams("strange out", {validation_cmd: CmdOutput(out="some strange out")})
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
