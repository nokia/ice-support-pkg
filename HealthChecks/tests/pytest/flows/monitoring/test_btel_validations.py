from __future__ import absolute_import
import pytest
import warnings
from flows.Monitoring.btel_validations import *
from tests.pytest.pytest_tools.operator.test_informator_validator import InformatorValidatorTestBase, \
    InformatorValidatorScenarioParams
from tests.pytest.pytest_tools.operator.test_operator import CmdOutput
from tests.pytest.pytest_tools.operator.test_validation_base import ValidationTestBase, ValidationScenarioParams
from tools.global_enums import Objectives
from tools.global_enums import Version
from tools.python_versioning_alignment import read_file
import tools.sys_parameters as sys_parameters

class BTELValidationStatusRequirementTestBase(ValidationTestBase):

    scenario_prerequisite_not_fulfilled = [ValidationScenarioParams("prerequisite_not_fulfilled",
                                                                    {"sudo helm list": CmdOutput("xxx")})]

    scenario_prerequisite_fulfilled = [ValidationScenarioParams("prerequisite_fulfilled",
                                                                    {"sudo helm list": CmdOutput("btel")})]

    @pytest.mark.parametrize("scenario_params", scenario_prerequisite_not_fulfilled)
    def test_prerequisite_not_fulfilled(self, scenario_params, tested_object):
        ValidationTestBase.test_prerequisite_not_fulfilled(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_prerequisite_fulfilled)
    def test_prerequisite_fulfilled(self, scenario_params, tested_object):
        ValidationTestBase.test_prerequisite_fulfilled(self, scenario_params, tested_object)

    def _init_mocks(self, tested_object):
        BTELValidationStatusRequirement.is_BTEL_installed = None

class TestFluentdDaemonSetRunningInAllNodesOrNot(BTELValidationStatusRequirementTestBase):
    tested_type = FluentdDaemonSetRunningInAllNodesOrNot

    cmd1 = "sudo /usr/local/bin/kubectl get nodes --no-headers=true | wc -l"
    out1 = "{}"

    cmd2 = "sudo /usr/local/bin/kubectl get daemonset btel-belk-fluentd-daemonset --namespace btel -o jsonpath='{.status.desiredNumberScheduled}'"
    out2 = "{}"

    scenario_passed = [
        ValidationScenarioParams("Verify FluentdDaemonSet run on all nodes",
                                 {cmd1: CmdOutput(out1.format("9")),
                                  cmd2: CmdOutput(out2.format("9"))}),
    ]

    scenario_failed = [
        ValidationScenarioParams("Verify FluentdDaemonSet NOT run on all nodes",
                                 {cmd1: CmdOutput(out1.format("9")),
                                  cmd2: CmdOutput(out2.format("6"))}),
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


class TestFluentdDaemonSetReplicasAllRunning(BTELValidationStatusRequirementTestBase):
    tested_type = FluentdDaemonSetReplicasAllRunning

    cmd1 = "sudo /usr/local/bin/kubectl get daemonset btel-belk-fluentd-daemonset --namespace btel -o jsonpath='{.status.desiredNumberScheduled}'"
    out1 = "{}"

    cmd2 = "sudo /usr/local/bin/kubectl get daemonset btel-belk-fluentd-daemonset --namespace btel -o jsonpath='{.status.numberAvailable}'"
    out2 = "{}"

    scenario_passed = [
        ValidationScenarioParams("Verify FluentdDaemonSet replicas all running",
                                 {cmd1: CmdOutput(out1.format("9")),
                                  cmd2: CmdOutput(out2.format("9"))}),
    ]

    scenario_failed = [
        ValidationScenarioParams("Verify FluentdDaemonSet replicas all NOT running",
                                 {cmd1: CmdOutput(out1.format("9")),
                                  cmd2: CmdOutput(out2.format("6"))}),
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


class TestAlertManagerAndCPROClusterIPAccessableOrNot(BTELValidationStatusRequirementTestBase):
    tested_type = AlertManagerAndCPROClusterIPAccessableOrNot

    cmd1 = "sudo /usr/local/bin/kubectl get svc -n btel {} -o=jsonpath='{{.spec.clusterIP}}'"
    out1 = "{}"

    cmd2 = "sudo curl --connect-timeout 2 {}"
    out2_timeout = 'curl: (28) Connection timed out after 2001 milliseconds'

    cpro_service = {'cpro-server-ext': {'ip': '10.254.225.168',
                                        'out': """
                                                <a href="/graph">Found</a>.
                                                """},
                    'cpro-alertmanager-ext': {'ip': '10.254.67.137',
                                              'out': """
                                                    <!DOCTYPE html>
                                                    // HTML content
                                                    """}
                    }
    cmd_out_pass = {}
    for service in cpro_service:
        cmd_out_pass[cmd1.format(service)] = CmdOutput(out1.format(cpro_service[service]['ip']))
        cmd_out_pass[cmd2.format(cpro_service[service]['ip'])] = CmdOutput(cpro_service[service]['out'])

    scenario_passed = [
        ValidationScenarioParams("Verify BTEL-CPRO PROMETHEUS and BTEL-CPRO AlertManager ClusterIP is accessible",
                                 cmd_out_pass)]

    cmd_out_fail = {}
    for service in cpro_service:
        cmd_out_fail[cmd1.format(service)] = CmdOutput(out1.format(cpro_service[service]['ip']))
        cmd_out_fail[cmd2.format(cpro_service[service]['ip'])] = CmdOutput(out2_timeout)

    scenario_failed = [
        ValidationScenarioParams("Verify BTEL-CPRO PROMETHEUS and BTEL-CPRO AlertManager ClusterIP is accessible",
                                 cmd_out_fail)]

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


class TestCheckNodeLabels(ValidationTestBase):
    tested_type = CheckNodeLabels

    out = """
    [
      {{
        "name": "fi-808-ncs2212-edgebm-0",
        "labels": {{
          "bcmt_storage_node": "false",
          "beta.kubernetes.io/arch": "amd64",
          "cpu_pooler_active": "false",
          "{}": "false",
          "kubernetes.io/arch": "amd64",
          "ncs.nokia.com/group": "EdgeBM",
          "ncs.nokia.com/multus_node": "true",
          "sriov": "enabled"
        }}
      }},
      {{
        "name": "fi-808-ncs2212-masterbm-0",
        "labels": {{
          "dynamic_local_storage_node": "false",
          "is_control": "true",
          "is_worker": "false",
          "topology.kubernetes.io/zone": "Zone-1"
        }}
      }}
    ]
    """
    cmd = "sudo kubectl get node -o json | jq -r '[.items[] | {name:.metadata.name,labels:.metadata.labels}]'"

    scenario_passed = [
        ValidationScenarioParams("Valid label name 'is_worker'", {cmd: CmdOutput(out=out.format('is_worker'))}),
        ValidationScenarioParams("Valid label name 'is_worker2'", {cmd: CmdOutput(out=out.format('is_worker2'))})
    ]

    scenario_failed = [
        ValidationScenarioParams("Inalid label name 'is-worker'", {cmd: CmdOutput(out=out.format('is-worker'))}),
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)









class Testlist_of_btel_components_installed(InformatorValidatorTestBase):
    tested_type = list_of_btel_components_installed

    get_helm_list = "sudo helm list --output json --deployed"
    helm_list_output_expected = '{"Next":"","Releases":[{"Name":"app-api","Revision":1,"Updated":"Thu Jan 30 12:02:22 2025","Status":"DEPLOYED","Chart":"ncm-app-1.14.2","AppVersion":"1.13.9","Namespace":"ncms"},{"Name":"bcmt-citm-ingress","Revision":1,"Updated":"Thu Jan 30 12:16:45 2025","Status":"DEPLOYED","Chart":"citm-ingress-1.18.11-4","AppVersion":"1.18.0-2.2","Namespace":"ncms"},{"Name":"bcmt-ckey","Revision":1,"Updated":"Thu Jan 30 12:11:02 2025","Status":"DEPLOYED","Chart":"ckey-8.10.12","AppVersion":"10.0.1","Namespace":"ncms"},{"Name":"bcmt-cmdb","Revision":1,"Updated":"Thu Jan 30 12:05:08 2025","Status":"DEPLOYED","Chart":"cmdb-7.13.5","AppVersion":"cmdb-4.21-3_mariadb-10.3.25","Namespace":"ncms"},{"Name":"btel","Revision":1,"Updated":"Fri Feb  7 07:12:56 2025","Status":"DEPLOYED","Chart":"btel-2.0.0","AppVersion":"1.0","Namespace":"btel"},{"Name":"cbur-master","Revision":1,"Updated":"Thu Jan 30 12:04:28 2025","Status":"DEPLOYED","Chart":"cbur-1.4.5","AppVersion":"1.9-06-2604","Namespace":"ncms"},{"Name":"cert-manager","Revision":1,"Updated":"Thu Jan 30 12:02:04 2025","Status":"DEPLOYED","Chart":"cert-manager-v0.15.2","AppVersion":"v0.15.2","Namespace":"ncms"},{"Name":"citm-ingress","Revision":1,"Updated":"Fri Feb  7 11:35:43 2025","Status":"DEPLOYED","Chart":"citm-ingress-1.18.3-6","AppVersion":"1.18.0-1.6","Namespace":"citm"},{"Name":"csi-cinder","Revision":1,"Updated":"Thu Jan 30 12:03:19 2025","Status":"DEPLOYED","Chart":"csi-cinder-1.19.2","AppVersion":"v1.19.0","Namespace":"kube-system"},{"Name":"default404","Revision":1,"Updated":"Fri Feb  7 11:36:11 2025","Status":"DEPLOYED","Chart":"default404-1.0.30","AppVersion":"4.0.4-5","Namespace":"citm"},{"Name":"gatekeeper","Revision":1,"Updated":"Thu Jan 30 12:03:36 2025","Status":"DEPLOYED","Chart":"gatekeeper-3.2.1","AppVersion":"v3.2.1","Namespace":"ncms"},{"Name":"harbor","Revision":1,"Updated":"Thu Jan 30 12:18:35 2025","Status":"DEPLOYED","Chart":"harbor-1.0.56","AppVersion":"2.1.0","Namespace":"ncms"},{"Name":"k8s-dashboard-gk","Revision":1,"Updated":"Thu Jan 30 12:17:25 2025","Status":"DEPLOYED","Chart":"keycloak-gatekeeper-3.3.1","AppVersion":"10.0.0","Namespace":"ncms"}]}'
    get_btel_status = 'sudo helm status btel | grep -i "Release Name"  -A 20'
    btel_status_output_expected = ''' Release Name:                                  Chart Version:
=============================================================
  cmdb                                           7.13.5
  crmq                                           2.4.6
  cnot                                           1.5.15
  calm                                           20.9.2
  cpro                                           2.11.0
  gen3gppxml                                     2.3.0
  grafana                                        3.16.1
  belk                                           6.3.2
  citm                                           1.18.7
'''
    btel_status_output_absent='{"Next":"","Releases":[{"Name":"app-api","Revision":1,"Updated":"Thu Jan 30 12:02:22 2025","Status":"DEPLOYED","Chart":"ncm-app-1.14.2","AppVersion":"1.13.9","Namespace":"ncms"}]}'
    btel_status_output_expected_clean = btel_status_output_expected.replace('=', '')
    system_info_btel_installed = "The installed btel components are : \n {}".format(btel_status_output_expected_clean)
    system_info_btel_not_installed = "BTEL is not installed on the cluster"
    scenario_passed = [
        InformatorValidatorScenarioParams(scenario_title="Passed BTEL Installed",
                                          expected_system_info=system_info_btel_installed,
                                 cmd_input_output_dict={
                                     get_helm_list: CmdOutput(helm_list_output_expected),
                                     get_btel_status: CmdOutput(btel_status_output_expected),

                                 },
                                 version=Version.V20
                                 ),
        InformatorValidatorScenarioParams(scenario_title="Passed BTEL Not Installed",
                                          expected_system_info=system_info_btel_not_installed,
                                          cmd_input_output_dict={
                                              get_helm_list: CmdOutput(btel_status_output_absent),
                                              get_btel_status: CmdOutput(btel_status_output_absent),

                                          },
                                          version=Version.V20
                                          )


    ]


    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        InformatorValidatorTestBase.test_scenario_passed(self, scenario_params, tested_object)


    def test_has_confluence(self, tested_object):
        # Override the func since this val doesn't have a confluence.
        # pls do not copy it! it's only for old validations that do not have a confluence page.
        warnings.warn("No confluence page")


class TestCheckPrometheusStorageUsage(ValidationTestBase):
    tested_type = CheckPrometheusStorageUsage

    get_pods_cmd = "sudo kubectl get pods -n ncms | grep prometheus-operator"

    get_pods_out ="prometheus-operator-prometheus-0                            2/2     Running   0               55d"

    prometheus_volume_cmd = 'sudo kubectl exec -n ncms -c prometheus prometheus-operator-prometheus-0 -- df -kh | grep " /prometheus$"'

    prometheus_volume_valid_out = "/dev/rbd0                48.9G    429.1M     48.5G   1% /prometheus"

    prometheus_volume_high_usage_out = "/dev/rbd0                48.9G    39.7G     9.2G   81% /prometheus"

    prometheus_volume_unexpected_out_1 = "/dev/rbd0                 429.1M     48.5G   1% /prometheus"
    prometheus_volume_unexpected_out_2 = "/dev/rbd0                48.9G    429.1M     48.5G   a% /prometheus"

    scenario_passed = [
        ValidationScenarioParams(scenario_title="usage under threshold",
                                 cmd_input_output_dict={get_pods_cmd: CmdOutput(out=get_pods_out),
                                                        prometheus_volume_cmd: CmdOutput(out=prometheus_volume_valid_out)})

    ]

    scenario_failed = [
        ValidationScenarioParams("usage over threshold",
                                 cmd_input_output_dict={get_pods_cmd: CmdOutput(out=get_pods_out),
                                                        prometheus_volume_cmd: CmdOutput(out=prometheus_volume_high_usage_out)})
    ]

    scenario_unexpected_system_output = [
        ValidationScenarioParams("unexpected number of values in the output",
                                 cmd_input_output_dict={get_pods_cmd: CmdOutput(out=get_pods_out),
                                                        prometheus_volume_cmd: CmdOutput(out=prometheus_volume_unexpected_out_1)}),
        ValidationScenarioParams("failed to parse percentage to integer",
                                 cmd_input_output_dict={get_pods_cmd: CmdOutput(out=get_pods_out),
                                                        prometheus_volume_cmd: CmdOutput(out=prometheus_volume_unexpected_out_2)})
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
