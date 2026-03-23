from __future__ import absolute_import
import pytest
import copy
import warnings

from tests.pytest.tools.versions_alignment import Mock

from flows.K8s.k8s_components.k8s_components_validator import CheckRedisClusterStatus, CheckMariaDbAdminPodLogs, \
    CheckRedisHAStatus, CheckWhereaboutsCleanerPodIsFrozen, VerifyDeploymentAndStatefulsetResilient, \
    ValidateLockForPodmanVolumes, CheckK8sPendingJobsCount, ValidatePvSizeAgainstHelmChart, ValidateGaleraDiskUsage, \
    CheckHarborRegistryDiskUsage, ValidateCsiCephRbdConfigFile, HarborCertVipValidation, VerifyCkeyServiceConnectivity
from tests.pytest.pytest_tools.operator.test_operator import CmdOutput
from tests.pytest.pytest_tools.operator.test_validation_base import ValidationTestBase, ValidationScenarioParams
from flows.K8s.k8s_components.k8s_components_validator import EtcdDefragCronjobValidation


class TestCheckRedisClusterStatus(ValidationTestBase):
    tested_type = CheckRedisClusterStatus

    out = """
    # Sentinel
    sentinel_masters:1
    sentinel_tilt:0
    sentinel_running_scripts:0
    sentinel_scripts_queue_length:0
    master0:name=cbis_cluster,status={},address=172.31.0.6:6379,slaves=2,sentinels=3
    """
    cmd = "sudo docker exec redis-sentinel redis-cli -p 26379 info Sentinel"

    scenario_passed = [
        ValidationScenarioParams("ok status", {cmd: CmdOutput(out=out.format("ok"))})
    ]

    scenario_failed = [
        ValidationScenarioParams("empty status", {cmd: CmdOutput(out=out.format(""))}),
        ValidationScenarioParams("odown status", {cmd: CmdOutput(out=out.format("odown"))})
    ]

    scenario_unexpected_system_output = [
        ValidationScenarioParams("strange out", {cmd: CmdOutput(out="some strange out")})
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


class TestEtcdDefragCronjobValidation(ValidationTestBase):
    tested_type = EtcdDefragCronjobValidation

    cmd_1 = "sudo kubectl get cronjobs -n ncms -o custom-columns=NAME:.metadata.name |grep -i 'etcd-defrag'"

    out_cmd = """etcd-defrag-1
etcd-defrag-2
etcd-defrag-3
"""

    cmd_final = "sudo kubectl describe cronjobs {} -nncms |grep -i 'sleep'"

    out_1 = """sleep 5s;ETCDCTL_API=3 /usr/local/bin/etcdctl --endpoints=https://$MY_HOST_IP:2379
    --cacert=/etc/etcd/ssl/ca.pem --cert=/etc/etcd/ssl/etcd-client.pem --key=/etc/etcd/ssl/etcd-client-key.pem defrag
    """

    out_2 = """sleep 5s"""

    cmd_input_output_dict_passed_scenario = {cmd_1: CmdOutput(out=out_cmd)}

    for i, cronjob in enumerate(['etcd-defrag-1', 'etcd-defrag-2', 'etcd-defrag-3']):
        cmd_input_output_dict_passed_scenario[cmd_final.format(cronjob)] = CmdOutput(out=out_1)

    scenario_passed = [
        ValidationScenarioParams("Correct Format", cmd_input_output_dict=cmd_input_output_dict_passed_scenario)
    ]

    cmd_input_output_dict_failed_scenario = copy.deepcopy(cmd_input_output_dict_passed_scenario)
    cmd_input_output_dict_failed_scenario.update({cmd_final.format("etcd-defrag-1"): CmdOutput(out=out_2),
                                                  cmd_final.format("etcd-defrag-2"): CmdOutput(out=out_2),
                                                  cmd_final.format("etcd-defrag-3"): CmdOutput(out=out_2)})

    scenario_failed = [
        ValidationScenarioParams("Invalid Format", cmd_input_output_dict=cmd_input_output_dict_failed_scenario)
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


class TestCheckMariaDbAdminPodLogs(ValidationTestBase):
    tested_type = CheckMariaDbAdminPodLogs

    cmd_get_mariadb_admin_pod = "sudo /usr/local/bin/kubectl get pods -n ncms --no-headers | grep -i 'cmdb-admin' |" \
                                " grep Running"
    cmd_count_paused = "sudo kubectl logs -n ncms bcmt-cmdb-admin-0 | grep -i 'Auto-Heal Paused' | wc -l"
    cmd_count_enabled = "sudo kubectl logs -n ncms bcmt-cmdb-admin-0 | grep -i 'Auto-Heal Enabled' | wc -l"

    scenario_passed = [
        ValidationScenarioParams("Paused in log",
                                 cmd_input_output_dict={
                                     cmd_get_mariadb_admin_pod: CmdOutput("bcmt-cmdb-admin-0  1/1  Running  0  11d"),
                                     cmd_count_paused: CmdOutput("2"),
                                     cmd_count_enabled: CmdOutput("1")
                                 }),
        ValidationScenarioParams("No paused in logs",
                                 cmd_input_output_dict={
                                     cmd_get_mariadb_admin_pod: CmdOutput("bcmt-cmdb-admin-0  1/1  Running  0  11d"),
                                     cmd_count_paused: CmdOutput("0")
                                 })
    ]

    scenario_failed = [
        ValidationScenarioParams("No enabled in log",
                                 cmd_input_output_dict={
                                     cmd_get_mariadb_admin_pod: CmdOutput("bcmt-cmdb-admin-0  1/1  Running  0  11d"),
                                     cmd_count_paused: CmdOutput("2"),
                                     cmd_count_enabled: CmdOutput("0")},
                                 failed_msg="ERROR!! ADMIN POD Has Error LOGS UNPAUSE")
    ]

    scenario_unexpected_system_output = [
        ValidationScenarioParams("Small out length",
                                 cmd_input_output_dict={
                                     cmd_get_mariadb_admin_pod: CmdOutput("bcmt-cmdb-admin-0|1/1|Running|0|11d")
                                 }),
        ValidationScenarioParams("No 1/1 in out",
                                 cmd_input_output_dict={
                                     cmd_get_mariadb_admin_pod: CmdOutput("bcmt-cmdb-admin-0  1/2  Running  0  11d")
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


class TestCheckRedisHAStatus(ValidationTestBase):
    tested_type = CheckRedisHAStatus

    basic_out_format = """
    {{
  "OciVersion": "1.0.2-dev",
  {}: {},
  "Running": true,
  "Restarting": false,
  "Dead": false,
  "Pid": 23215,
  "ExitCode": 0,
  "StartedAt": "2023-05-05T16:15:12.518936201Z",
  "FinishedAt": "0001-01-01T00:00:00Z",
  {}: {{
    "Status": {},
    "FailingStreak": 0,
    "Log": [
      {{
        "Start": "2023-06-07T11:21:28.336357351Z",
        "End": "2023-06-07T11:21:28.490054864Z",
        "ExitCode": 0,
        "Output": "PONG"
      }}
    ]
  }},
  "CheckpointedAt": "0001-01-01T00:00:00Z",
  "RestoredAt": "0001-01-01T00:00:00Z"
}}"""

    scenario_passed = [
        ValidationScenarioParams("Health in out",
                                 {"sudo docker inspect redis-sentinel | jq '.[0].State'": CmdOutput(
                                     basic_out_format.format('"Status"', '"running"', '"Health"', '"healthy"')),
                                  "sudo docker inspect redis | jq '.[0].State'": CmdOutput(
                                      basic_out_format.format('"Status"', '"running"', '"Health"', '"healthy"'))}),
        ValidationScenarioParams("Healthcheck in out",
                                 {"sudo docker inspect redis-sentinel | jq '.[0].State'": CmdOutput(
                                     basic_out_format.format('"Status"', '"running"', '"Healthcheck"', '"healthy"')),
                                     "sudo docker inspect redis | jq '.[0].State'": CmdOutput(
                                         basic_out_format.format('"Status"', '"running"', '"Healthcheck"', '"healthy"'))
                                 })
    ]

    scenario_failed = [
        ValidationScenarioParams("Health not-healthy",
                                 {"sudo docker inspect redis-sentinel | jq '.[0].State'": CmdOutput(
                                     basic_out_format.format('"Status"', '"running"', '"Health"', '"healthy"')),
                                     "sudo docker inspect redis | jq '.[0].State'": CmdOutput(
                                         basic_out_format.format('"Status"', '"running"', '"Health"', '"not-healthy"'))
                                 },
                                 tested_object_mock_dict={
                                     "get_host_name": Mock(return_value="some-host")
                                 }),
        ValidationScenarioParams("status paused",
                                 {"sudo docker inspect redis-sentinel | jq '.[0].State'": CmdOutput(
                                     basic_out_format.format('"Status"', '"paused"', '"Healthcheck"', '"healthy"')),
                                     "sudo docker inspect redis | jq '.[0].State'": CmdOutput(
                                         basic_out_format.format('"Status"', '"running"', '"Healthcheck"', '"healthy"'))},
                                 tested_object_mock_dict={
                                     "get_host_name": Mock(return_value="some-host")
                                 })

    ]

    scenario_unexpected_system_output = [
        ValidationScenarioParams("no Status in keys",
                                 {"sudo docker inspect redis-sentinel | jq '.[0].State'": CmdOutput(
                                     basic_out_format.format('"Status"', '"running"', '"Health"', '"healthy"')),
                                     "sudo docker inspect redis | jq '.[0].State'": CmdOutput(
                                         basic_out_format.format('"status"', '"running"', '"Health"', '"healthy"'))}),
        ValidationScenarioParams("no Health and Healthcheck in keys",
                                 {"sudo docker inspect redis-sentinel | jq '.[0].State'": CmdOutput(
                                     basic_out_format.format('"Status"', '"running"', '"Health"', '"healthy"')),
                                     "sudo docker inspect redis | jq '.[0].State'": CmdOutput(
                                         basic_out_format.format('"Status"', '"running"', '"Healthy"', '"healthy"'))})
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


class TestCheckWhereaboutsCleanerPodIsFrozen(ValidationTestBase):
    tested_type = CheckWhereaboutsCleanerPodIsFrozen

    get_pod_name_cmd = "sudo kubectl get pods -n kube-system -l app=whereabouts-cleaner | grep whereabouts |" \
                       "grep -i Running | awk '{print $1}'"
    get_pod_interval_param_cmd = "sudo kubectl get pod {} -n kube-system -o json | jq -r 'if has(\"spec\")" \
                                 "and .spec.containers[0].env then .spec.containers[0].env[]" \
                                 "| select(.name == \"SCRIPT_INTERVAL\") | .value else empty end'".format("whereabouts-cleaner-88fb89444-j5jml")
    get_pod_latest_log_cmd = "sudo kubectl logs -n kube-system {0} | tail -n1".format("whereabouts-cleaner-88fb89444-j5jml")
    get_current_date_cmd = "date"

    scenario_passed = [
        ValidationScenarioParams("Pod is not frozen",
                                 cmd_input_output_dict={
                                     get_pod_name_cmd: CmdOutput("whereabouts-cleaner-88fb89444-j5jml"),
                                     get_pod_interval_param_cmd: CmdOutput("180"),
                                     get_pod_latest_log_cmd: CmdOutput("Wed Dec 27 17:00:10 UTC 2023"),
                                     get_current_date_cmd: CmdOutput("Wed Dec 27 17:00:10 UTC 2023")
                                 }),
        ValidationScenarioParams("Pod is not frozen",
                                 cmd_input_output_dict={
                                     get_pod_name_cmd: CmdOutput("whereabouts-cleaner-88fb89444-j5jml"),
                                     get_pod_interval_param_cmd: CmdOutput(""),
                                     get_pod_latest_log_cmd: CmdOutput("Wed Dec 27 17:00:10 UTC 2023"),
                                     get_current_date_cmd: CmdOutput("Wed Dec 27 17:00:10 UTC 2023")
                                 })
    ]

    scenario_failed = [
        ValidationScenarioParams("Pod is frozen",
                                 cmd_input_output_dict={
                                     get_pod_name_cmd: CmdOutput("whereabouts-cleaner-88fb89444-j5jml"),
                                     get_pod_interval_param_cmd: CmdOutput("180"),
                                     get_pod_latest_log_cmd: CmdOutput("Wed Dec 25 17:00:10 UTC 2023"),
                                     get_current_date_cmd: CmdOutput("Wed Dec 27 17:00:10 UTC 2023")
                                 }),
        ValidationScenarioParams("Pod is with error",
                                 cmd_input_output_dict={
                                     get_pod_name_cmd: CmdOutput("whereabouts-cleaner-88fb89444-j5jml"),
                                     get_pod_interval_param_cmd: CmdOutput(""),
                                     get_pod_latest_log_cmd: CmdOutput("Other than date log"),
                                     get_current_date_cmd: CmdOutput("Wed Dec 27 17:00:10 UTC 2023")
                                 })
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

class TestValidateLockForVolumes(ValidationTestBase):
    tested_type = ValidateLockForPodmanVolumes

    podman_volume_list_cmd = "sudo podman volume list"
    pass_podman_volume_list = '''
    "DRIVER      VOLUME NAME",
        "local       21eba56e37c58f95ff93ff6886c1bb177d15e1a88b9184e9fc719efa6fe69b33",
        "local       60c0e6816c2e4ec04e3401369aa621081b2ae5f3cd387924e8de4131ee1a2089",
        "local       7ab9688401e47d32884be049af648187da0240656fbce965a1b9f68ffd85d67f",
        "local       7b0be066587ff6a76635c0aa20813f3298c9ee3f26b0730ae761ec214802e502",'''
    fail_podman_volume_list = '''
    "ERRO[0000] Retrieving volume fe5722c80851834af14c1ac12030784f7ef16cd2703843dcb0b2e4467416edcf from the database"
    "ERRO[0000] Retrieving volume fff0360ca31d033175b071bd4d492bcafa78383d6ea620c2dcb1854b21656859 from the database"
    "DRIVER      VOLUME NAME",
    "local       21eba56e37c58f95ff93ff6886c1bb177d15e1a88b9184e9fc719efa6fe69b33",
    "local       60c0e6816c2e4ec04e3401369aa621081b2ae5f3cd387924e8de4131ee1a2089",
    "local       7ab9688401e47d32884be049af648187da0240656fbce965a1b9f68ffd85d67f",
    "local       7b0be066587ff6a76635c0aa20813f3298c9ee3f26b0730ae761ec214802e502", '''


    scenario_passed = [
        ValidationScenarioParams("No Lock Error",
                                 cmd_input_output_dict={
                                     podman_volume_list_cmd: CmdOutput(pass_podman_volume_list)
                                 })
    ]

    scenario_failed = [
        ValidationScenarioParams("Lock Error",
                                 cmd_input_output_dict={
                                     podman_volume_list_cmd: CmdOutput(fail_podman_volume_list)
                                 })
    ]


class TestVerifyDeploymentAndStatefulsetResilient(ValidationTestBase):
    tested_type = VerifyDeploymentAndStatefulsetResilient

    get_workload_cmd = "sudo /usr/local/bin/kubectl get deployments,statefulset -A -o json | jq -r '.items[] | \"\\(.kind) \\(.metadata.namespace) \\(.metadata.name) \\(.spec.template.spec.affinity.podAntiAffinity) \\(.status.replicas) \\(.spec.template.metadata.labels)\"' "
    skipped_namespace_out = 'Deployment ncms bcmt-redis null 1 {"ncms":"bcmt-redis"}'
    valid_workload_out = 'StatefulSet myname ccas-apache1 {} 2 {"app":"ccas-apache1"}'
    one_replica_out = 'Deployment myname ccas-apache1 {} 1 {"app":"ccas-apache1"}'
    no_anti_affinity_out = 'StatefulSet myname ccas-apache1 null 2 {"app":"ccas-apache1"}'

    get_pdb_cmd = "sudo /usr/local/bin/kubectl get pdb -n myname -o json"
    matched_pdb_zero_disruptions = '{"items":[{"metadata":{"name":"ccas-apache1","namespace":"myname"},"spec":{"selector":{"matchLabels":{"app":"ccas-apache1"}}},"status":{"disruptionsAllowed":0}}]}'
    matched_pdb_none_zero_disruptions = '{"items":[{"metadata":{"name":"ccas-apache1","namespace":"myname"},"spec":{"selector":{"matchLabels":{"app":"ccas-apache1"}}},"status":{"disruptionsAllowed":1}}]}'
    unmatched_pdb_zero_disruptions = '{"items":[{"metadata":{"name":"ccas-apache1","namespace":"myname"},"spec":{"selector":{"matchLabels":{"app":"ccas-apache1","release":"ccas-apache1"}}},"status":{"disruptionsAllowed":0}}]}'

    scenario_passed = [
        ValidationScenarioParams("Skipped namespace",
                                 cmd_input_output_dict={
                                     get_workload_cmd: CmdOutput(skipped_namespace_out)
                                 }),
        ValidationScenarioParams("Valid workload pdb disruptions not zero",
                                 cmd_input_output_dict={
                                     get_workload_cmd: CmdOutput(valid_workload_out),
                                     get_pdb_cmd: CmdOutput(matched_pdb_none_zero_disruptions)
                                 }),
        ValidationScenarioParams("Valid workload no pdb matched",
                                 cmd_input_output_dict={
                                     get_workload_cmd: CmdOutput(valid_workload_out),
                                     get_pdb_cmd: CmdOutput(unmatched_pdb_zero_disruptions)
                                 })
    ]

    scenario_failed = [
        ValidationScenarioParams("One replica workload",
                                 cmd_input_output_dict={
                                     get_workload_cmd: CmdOutput(one_replica_out),
                                     get_pdb_cmd: CmdOutput(matched_pdb_none_zero_disruptions)
                                 }),
        ValidationScenarioParams("No anti-affinity workload",
                                 cmd_input_output_dict={
                                     get_workload_cmd: CmdOutput(no_anti_affinity_out),
                                     get_pdb_cmd: CmdOutput(unmatched_pdb_zero_disruptions)
                                 }),
        ValidationScenarioParams("Valid workload no pdb disruptions is zero",
                                 cmd_input_output_dict={
                                     get_workload_cmd: CmdOutput(valid_workload_out),
                                     get_pdb_cmd: CmdOutput(matched_pdb_zero_disruptions)
                                 })
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestCheckK8sPendingJobsCount(ValidationTestBase):
    tested_type = CheckK8sPendingJobsCount

    tested_type.MAX_PENDING_JOBS_COUNT = 3

    cmd = "sudo kubectl get jobs.batch -A --no-headers"

    valid_out = '''istio-system   istio-crd-install-cist-istio-init-post-install   1/1           13s        20d
istio-system   istio-crd-install-cist-istio-init-x5hfel         1/1           7s         20d
istio-system   istio-crd-install-cist-istio-init-x5hfel         1/1           7s         20d'''

    high_count_out = '''istio-system   istio-crd-install-cist-istio-init-post-install   1/1           13s        20d
istio-system   istio-crd-install-cist-istio-init-x5hfel         1/1           7s         20d
istio-system   istio-crd-install-cist-istio-init-post-install   1/1           13s        20d
istio-system   istio-crd-install-cist-istio-init-post-install   1/1           13s        20d'''

    scenario_passed = [
        ValidationScenarioParams(scenario_title="count under threshold",
                                 cmd_input_output_dict={cmd: CmdOutput(out=valid_out)})

    ]

    scenario_failed = [
        ValidationScenarioParams("count over threshold",
                                 cmd_input_output_dict={cmd: CmdOutput(out=high_count_out)})

    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestValidatePvSizeAgainstHelmChart(ValidationTestBase):
    tested_type = ValidatePvSizeAgainstHelmChart

    harbor_persistence_values_cmd = "sudo helm get values -n ncms harbor -o json"
    persistence_config_passed = '''
    {
      "persistence": {
        "persistentVolumeClaim": {
          "database": {
            "size": "1Gi",
            "storageClass": "csi-cephrbd"
          },
          "redis": {
            "size": "1Gi",
            "storageClass": "csi-cephrbd"
          },
          "registry": {
            "accessMode": "ReadWriteOnce",
            "size": "100Gi",
            "storageClass": "csi-cephrbd"
          },
          "trivy": {
            "size": "5Gi",
            "storageClass": null
          }
        }
      }
    }
    '''

    pvc_sizes = {"data-harbor-harbor-redis-0": "1Gi", "data-harbor-harbor-trivy-0": "5Gi", "database-data-harbor-harbor-database-0": "1Gi", "harbor-harbor-registry": "100Gi"}

    persistence_config_failed = '''
    {
      "persistence": {
        "persistentVolumeClaim": {
          "database": {
            "size": "2Gi",
            "storageClass": "csi-cephrbd"
          },
          "redis": {
            "size": "1Gi",
            "storageClass": "csi-cephrbd"
          },
          "registry": {
            "accessMode": "ReadWriteOnce",
            "size": "100Gi",
            "storageClass": "csi-cephrbd"
          },
          "trivy": {
            "size": "5Gi",
            "storageClass": null
          }
        }
      }
    }
    '''

    persistence_config_unexpected = '''
    {
      "persistence": {
        "persistentVolumeClaim": {
          "dataunexpected": {
            "size": "2Gi",
            "storageClass": "csi-cephrbd"
          },
          "redis": {
            "size": "1Gi",
            "storageClass": "csi-cephrbd"
          },
          "registry": {
            "accessMode": "ReadWriteOnce",
            "size": "100Gi",
            "storageClass": "csi-cephrbd"
          },
          "trivy": {
            "size": "5Gi",
            "storageClass": null
          }
        }
      }
    }
    '''
    scenario_passed = [
        ValidationScenarioParams("PV size matches Helm chart configuration",
                                 cmd_input_output_dict={
                                     harbor_persistence_values_cmd: CmdOutput(persistence_config_passed)
                                 },
                                 tested_object_mock_dict = {"_get_harbor_pvc_sizes": Mock(return_value=pvc_sizes)})
    ]

    scenario_failed = [
        ValidationScenarioParams("PV size mismatches Helm chart configuration",
                                 cmd_input_output_dict={
                                     harbor_persistence_values_cmd: CmdOutput(persistence_config_failed)
                                 },
                                 tested_object_mock_dict = {"_get_harbor_pvc_sizes": Mock(return_value=pvc_sizes)})
    ]

    scenario_unexpected = [
        ValidationScenarioParams("PV size mismatches Helm chart configuration",
                                 cmd_input_output_dict={
                                     harbor_persistence_values_cmd: CmdOutput(persistence_config_failed)
                                 },
                                 tested_object_mock_dict = {"_get_harbor_pvc_sizes": Mock(return_value=pvc_sizes)})
    ]

    scenario_unexpected_system_output = [
        ValidationScenarioParams("Unexpected system output scenario",
                                 cmd_input_output_dict={
                                     harbor_persistence_values_cmd: CmdOutput(persistence_config_unexpected)
                                 },
                                 tested_object_mock_dict={"_get_harbor_pvc_sizes": Mock(return_value=pvc_sizes)})
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


class TestValidateGaleraDiskUsage(ValidationTestBase):
    tested_type = ValidateGaleraDiskUsage

    cmd = "sudo kubectl exec -ti -n ncms bcmt-galera-mariadb-galera-0 -- bash -c df -h | grep mariadb"
    mariadb_disk_usage_output = ("/dev/rbd0                    8154588   368200   7770004   44% /bitnami/mariadb."
                                 "tmpfs                        1048576       24   1048552   79% /bitnami/mariadb/certs.")
    mariadb_disk_usage_output_failed = ("/dev/rbd0                    8154588   368200   7770004   44% /bitnami/mariadb."
                                 "tmpfs                        1048576       24   1048552   89% /bitnami/mariadb/certs.")

    mariadb_pods_list = ["bcmt-galera-mariadb-galera-0"]

    scenario_passed = [
        ValidationScenarioParams("",
                                 cmd_input_output_dict={
                                     cmd: CmdOutput(mariadb_disk_usage_output)
                                 },
                                 tested_object_mock_dict = {"_get_mariadb_pods": Mock(return_value=mariadb_pods_list)})
    ]

    scenario_failed = [
        ValidationScenarioParams("",
                                 cmd_input_output_dict={
                                     cmd: CmdOutput(mariadb_disk_usage_output_failed)
                                 },
                                 tested_object_mock_dict = {"_get_mariadb_pods": Mock(return_value=mariadb_pods_list)})
    ]


    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestCheckHarborRegistryDiskUsage(ValidationTestBase):
    tested_type = CheckHarborRegistryDiskUsage

    cmd_list_pods = "sudo kubectl get pods --all-namespaces -l app=harbor-harbor -o name | grep harbor-harbor-registry"
    cmd_disk_usage = "sudo kubectl exec -i {} -n ncms -c registry -- df -h"
    df_output_ok = """
        Filesystem      Size  Used Avail Use% Mounted on
        /dev/root        10G  8.0G  2.0G  80% /
        tmpfs            64M     0   64M   0% /dev
        """

    df_output_high = """
        Filesystem      Size  Used Avail Use% Mounted on
        /dev/root        10G  9.0G  1.0G  90% /
        tmpfs            64M     0   64M   0% /dev
        """

    df_output_malformed_no_percentage = """
        Filesystem      Size  Used Avail Use% Mounted on
        /dev/root        10G  9.0G  1.0G  90 /
        tmpfs            64M     0   64M   0 /dev
        """

    df_output_malformed_too_few_fields = """
        Filesystem      Size  Used Avail Use% Mounted on
        /dev/root        10G  9.0G
        """

    scenario_passed = [
        ValidationScenarioParams(
            "disk usage within threshold",
            {
                cmd_list_pods: CmdOutput(out="pod/harbor-harbor-registry-test-123\n"),
                cmd_disk_usage.format("pod/harbor-harbor-registry-test-123"): CmdOutput(out=df_output_ok)
            }
        ),
        ValidationScenarioParams(
            "no harbor pods found (Code will graceful exit)",
            {
                cmd_list_pods: CmdOutput(out="")
            }
        ),
    ]

    scenario_failed = [
        ValidationScenarioParams(
            "disk usage exceeds threshold",
            {
                cmd_list_pods: CmdOutput(out="pod/harbor-harbor-registry-test-123\n"),
                cmd_disk_usage.format("pod/harbor-harbor-registry-test-123"): CmdOutput(out=df_output_high)
            }
        )
    ]

    scenario_unexpected_system_output = [
        ValidationScenarioParams(
            "malformed df output - no percentage sign",
            {
                cmd_list_pods: CmdOutput(out="pod/harbor-harbor-registry-test-123\n"),
                cmd_disk_usage.format("pod/harbor-harbor-registry-test-123"): CmdOutput(out=df_output_malformed_no_percentage)
            }
        ),
        ValidationScenarioParams(
            "malformed df output - too few fields",
            {
                cmd_list_pods: CmdOutput(out="pod/harbor-harbor-registry-test-123\n"),
                cmd_disk_usage.format("pod/harbor-harbor-registry-test-123"): CmdOutput(out=df_output_malformed_too_few_fields)
            }
        ),
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


class TestValidateCsiCephRbdConfigFile(ValidationTestBase):
    tested_type = ValidateCsiCephRbdConfigFile

    get_pods_cephfs_cmd = "sudo kubectl get pods -nncms -l component=nodeplugin,app=csi-cephfs"
    get_pods_cephfs_out = "NAME                           READY   STATUS    RESTARTS       AGE\n" \
                   "csi-cephfs-nodeplugin-5tchq   3/3     Running   7 (8d ago)   13d.\n"

    get_pods_cephrbd_cmd = "sudo kubectl get pods -nncms -l component=nodeplugin,app=csi-cephrbd"
    get_pods_cephrbd_out = "NAME                           READY   STATUS    RESTARTS       AGE\n" \
                   "csi-cephrbd-nodeplugin-5kb7x   3/3     Running   9 (9d ago)   13d."

    cephrbd_config_file_path = "/etc/ceph-csi-config/config.json"
    cephrbd_config_check_cmd = "sudo kubectl exec -it {} -nncms -c {} -- /bin/ls {}"
    cephrbd_config_output_failed = "'/etc/ceph-csi-config/config.json': No such file or directory"

    scenario_passed = [
        ValidationScenarioParams("",
                                 cmd_input_output_dict={
                                     get_pods_cephfs_cmd: CmdOutput(get_pods_cephfs_out),
                                     get_pods_cephrbd_cmd: CmdOutput(get_pods_cephrbd_out),
                                     cephrbd_config_check_cmd.format("csi-cephfs-nodeplugin-5tchq",
                                                                     "csi-cephfsplugin", cephrbd_config_file_path): CmdOutput(
                                         cephrbd_config_file_path),
                                     cephrbd_config_check_cmd.format("csi-cephrbd-nodeplugin-5kb7x",
                                                                     "csi-rbdplugin",
                                                                     cephrbd_config_file_path): CmdOutput(
                                         cephrbd_config_file_path)
                                 }),
    ]

    scenario_failed = [
        ValidationScenarioParams("",
                                 cmd_input_output_dict={
                                     get_pods_cephfs_cmd: CmdOutput(get_pods_cephfs_out),
                                     cephrbd_config_check_cmd.format("csi-cephfs-nodeplugin-5tchq", "csi-cephfsplugin", cephrbd_config_file_path): CmdOutput(
                                         cephrbd_config_output_failed),
                                     get_pods_cephrbd_cmd: CmdOutput(get_pods_cephrbd_out),
                                     cephrbd_config_check_cmd.format("csi-cephrbd-nodeplugin-5kb7x",
                                                                     "csi-rbdplugin",
                                                                     cephrbd_config_file_path): CmdOutput(
                                         cephrbd_config_output_failed)
                                 })
    ]


    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestHarborCertVipValidation(ValidationTestBase):
    tested_type = HarborCertVipValidation

    cmd_list_pods = "sudo kubectl get pods -nncms -l app=harbor-harbor"
    cmd_vip_addresses = "sudo kubectl get certificates -nncms harbor-harbor-nginx-cert -o json | jq .spec.ipAddresses"
    vip_cmd = "sudo /bin/hiera -c /usr/share/cbis/data/cbis_hiera.yaml tripleo::haproxy::public_virtual_ip"
    get_cert_cmd = "sudo kubectl get certificates -n ncms harbor-harbor-nginx-cert --no-headers | wc -l"
    cert_cmd_code = 1
    vip_output_ok = '["10.203.116.41", "10.203.116.42", "10.203.116.43", "10.203.116.44"]'

    vip_output_wrong = '["10.203.116.41", "10.203.116.42", "10.203.116.43"]'
    vip = "10.203.116.44"
    scenario_passed = [
        ValidationScenarioParams(
            "ipv addresss exists",
            {
                cmd_list_pods: CmdOutput(out="harbor-harbor-nginx-8456f99d7c-p45sl"),
                cmd_vip_addresses: CmdOutput(out=vip_output_ok),
                vip_cmd: CmdOutput(out=vip)
            }
        )
    ]

    scenario_failed = [
        ValidationScenarioParams(
            "ipv address not exists",
            {
                cmd_list_pods: CmdOutput(out="harbor-harbor-nginx-8456f99d7c-p45sl"),
                cmd_vip_addresses: CmdOutput(out=vip_output_wrong),
                vip_cmd: CmdOutput(out=vip)
            }
        )
    ]

    scenario_unexpected_system_output = [
        ValidationScenarioParams(
            "malformed df output - no percentage sign",
            {
                cmd_list_pods: CmdOutput(out=""),
                cmd_vip_addresses: CmdOutput(out=vip_output_ok),
                vip_cmd: CmdOutput(out=vip)
            }
        )
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


class TestVerifyCkeyServiceConnectivity(ValidationTestBase):
    tested_type = VerifyCkeyServiceConnectivity

    mariadb_pod_0 = "bcmt-cmdb-mariadb-0"
    mariadb_pod_1 = "bcmt-cmdb-mariadb-1"

    cmd = "sudo kubectl exec -n ncms {} -- curl -k https://bcmt-ckey-ckey.ncms.svc:8443/auth/realms/master/protocol/openid-connect/token"


    scenario_passed = [
        ValidationScenarioParams(scenario_title="passed, return code 0",
                                 cmd_input_output_dict={cmd.format(mariadb_pod_0): CmdOutput(out="", return_code=0),
                                                        cmd.format(mariadb_pod_1): CmdOutput(out="", return_code=0)},
                                 additional_parameters_dict={"mariadb_pods": [mariadb_pod_0, mariadb_pod_1]}),
        ValidationScenarioParams(scenario_title="no mariadb pods running",
                                 additional_parameters_dict={"mariadb_pods": []})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="failed, couldn't connect to service",
                                 cmd_input_output_dict={cmd.format(mariadb_pod_0): CmdOutput(out="", return_code=0),
                                                        cmd.format(mariadb_pod_1): CmdOutput(out="", return_code=7)},
                                 additional_parameters_dict={"mariadb_pods": [mariadb_pod_0, mariadb_pod_1]})
    ]

    def _init_mocks(self, tested_object):
        tested_object.get_mariadb_Pods = Mock()
        tested_object.get_mariadb_Pods.return_value = self.additional_parameters_dict['mariadb_pods']

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

