from __future__ import absolute_import
import pytest
from tests.pytest.tools.versions_alignment import Mock, patch
from flows.Ncs.ncs_validations import CheckSymLink, CheckManagerPort, CheckManagerContainers, \
    CheckWebsocketProcessCount, RedisActiveOperationsCheck, CheckResourceLimitsOfBcmtCitmIngress, ValidateTunedProfile, \
    GenOpensslCnfFileExists, BcmtImageMatchingNCSVersion, IrqServiceValidator, BcmtVrrpSecurityGroupValidation, \
    ValidateHelmStatus, GetNodeNameForRebootRequired, CheckNodeRebootRequired, CheckCburPvCount

from tests.pytest.pytest_tools.operator.test_operator import CmdOutput
from tests.pytest.pytest_tools.operator.test_validation_base import ValidationTestBase, ValidationScenarioParams
from tools import sys_parameters
from tools.global_enums import Version


class TestCheckSymLink(ValidationTestBase):
    tested_type = CheckSymLink

    out = """lrwxrwxrwx. 1 root root 28 May 16 15:06 /var/log/cbis -> /opt/management/manager/logs
    lrwxrwxrwx. 1 root root 38 May 16 15:06 /var/log/cbis_services -> /opt/management/manager/logs/node_8080
    """

    scenario_passed = [
        ValidationScenarioParams("ok status",
                                 {
                                     "sudo ls -l /var/log/cbis": CmdOutput(out=out),
                                     "sudo ls -l /var/log/cbis_services": CmdOutput(out=out),
                                 })
    ]

    scenario_failed = [
        ValidationScenarioParams("empty status",
                                 {
                                     "sudo ls -l /var/log/cbis": CmdOutput(out="", return_code=1),
                                     "sudo ls -l /var/log/cbis_services": CmdOutput(out="", return_code=1)
                                 })
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

class TestCheckManagerPort(ValidationTestBase):
    tested_type = CheckManagerPort

    out1 = """
    tcp        0      0 127.0.0.1:8000          0.0.0.0:*               LISTEN      3463056/python2
    """
    out2 = """
    3463056 ?        00:00:00 gunicorn
    """

    version_conf_out = """
    {
    'releases': [{
            'position': 'latest',
            'cbis_manager_port': '8002',
            'release_version': '24.7.0'
        }, {
            'position': 'minus1',
            'cbis_manager_port': '8001',
            'release_version': '23.10.0'
        }
        ]
    }
    """

    scenario_passed = [
        ValidationScenarioParams(scenario_title="ok status for NCS version < V23_10",
                                 cmd_input_output_dict={
                                     "sudo cat /root/cbis/version_conf.yaml": CmdOutput(out='', return_code=1),
                                     "sudo netstat -tulpn | grep ':8000 '": CmdOutput(out=out1),
                                     "ps --no-headers -p 3463056": CmdOutput(out=out2)
                                 }),
        ValidationScenarioParams(scenario_title="ok status for NCS version >= V23_10",
                                 cmd_input_output_dict={
                                     "sudo cat /root/cbis/version_conf.yaml": CmdOutput(out=version_conf_out,return_code=0),
                                     "sudo netstat -tulpn | grep ':8002 '": CmdOutput(out=out1),
                                     "ps --no-headers -p 3463056": CmdOutput(out=out2)
                                 },
                                 library_mocks_dict={"sys_parameters.get_version": Mock(return_value=Version.V24_7)})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="empty status  < V23_10",
                                 cmd_input_output_dict={
                                     "sudo cat /root/cbis/version_conf.yaml": CmdOutput(out='', return_code=1),
                                     "sudo netstat -tulpn | grep ':8000 '": CmdOutput(out="", return_code=1),
                                     "ps --no-headers -p 3463056": CmdOutput(out="", return_code=1)
                                 })
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestVerifyBCMTImageForNCSVersionGA(ValidationTestBase):
    tested_type = BcmtImageMatchingNCSVersion
    ncs_version = 'ncs -v'
    ncs_version_out = "25.11.0-166"
    scenario_passed = [
        ValidationScenarioParams(scenario_title="BCMT image is matching NCS GA version image",
                                 additional_parameters_dict={'get_image_name': "cluster-25-11",
                                                             'get_image_checksum': "9ae0c7d0a4ebfcdee2177c71bc18fb85"},
                                 cmd_input_output_dict={ncs_version: CmdOutput(out=ncs_version_out)}
                                 )]
    scenario_failed = [
        ValidationScenarioParams(scenario_title="BCMT image is not matching NCS GA version image",
                                 additional_parameters_dict={'get_image_name': "cluster-25-11",
                                                             'get_image_checksum': "e21342f8db2959413e958c63e0a6a01b"},
                                 cmd_input_output_dict={ncs_version: CmdOutput(out=ncs_version_out)}
                                 )]

    scenario_unexpected_system_output = [
        ValidationScenarioParams(scenario_title="Unknown system output",
                                 additional_parameters_dict={'get_image_name': "cluster-25-11",
                                                             'get_image_checksum': "e21342f8db2959413e958c63e0a6a01b"},
                                 cmd_input_output_dict={ncs_version: CmdOutput(out="", return_code=1)}
                                 )]

    def _init_mocks(self, tested_object):
        tested_object.get_image_name = Mock()
        tested_object.get_image_name.return_value = self.additional_parameters_dict.get("get_image_name")
        tested_object.get_image_checksum = Mock()
        tested_object.get_image_checksum.return_value = self.additional_parameters_dict.get("get_image_checksum")

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_unexpected_system_output(self, scenario_params, tested_object)

class TestCheckManagerContainers(ValidationTestBase):
    tested_type = CheckManagerContainers

    docker_get_manager_containers_cmd = "sudo /usr/bin/{} ps --format '{{{{.Names}}}}'".format("docker")
    docker_inspect_manager_container_running = "sudo /usr/bin/{} inspect --format '{{{{.State.Running}}}}' {}".format("docker", "cbis_manager")
    docker_inspect_manager_container_health = "sudo /usr/bin/{} inspect --format '{{{{.State.Healthcheck.Status}}}}' {}".format("docker", "cbis_manager")

    scenario_failed = [
        ValidationScenarioParams("Docker container is running but not healthy",
                                 cmd_input_output_dict={
                                     docker_get_manager_containers_cmd: CmdOutput("cbis_manager"),
                                     docker_inspect_manager_container_running: CmdOutput("true"),
                                     docker_inspect_manager_container_health: CmdOutput("unhealthy"),
                                 }),

        ValidationScenarioParams("Docker container is not running and not healthy",
                                 cmd_input_output_dict={
                                     docker_get_manager_containers_cmd: CmdOutput("cbis_manager"),
                                     docker_inspect_manager_container_running: CmdOutput("false"),
                                     docker_inspect_manager_container_health: CmdOutput("unhealthy"),
                                 }),
    ]

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

class TestCheckWebsocketProcessCount(ValidationTestBase):
    tested_type = CheckWebsocketProcessCount

    out = "2"

    scenario_passed = [
        ValidationScenarioParams("ok status",
                                 {
                                     "/usr/bin/ps -ef --no-headers| grep cbis_websocket | wc -l": CmdOutput(out=out)
                                 })
    ]

    scenario_failed = [
        ValidationScenarioParams("empty status",
                                 {
                                     "/usr/bin/ps -ef --no-headers| grep cbis_websocket | wc -l": CmdOutput(out="",return_code=1)
                                 })
    ]
    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestRedisActiveOperationsCheck(ValidationTestBase):
    tested_type = RedisActiveOperationsCheck

    get_all_redis_operation_status_cmd = "sudo podman exec -it redis redis-cli -n 7 hgetall general:fi835a-ncs24-7:is_active.yaml"
    get_all_redis_operation_status_cmd_out_pass = """1) "cluster_bm_heal"
                                                     2) "inactive"
                                                     3) "central_bm_scale_out"
                                                     4) "inactive"
                                                  """
    get_all_redis_operation_status_cmd_out_fail = """1) "cluster_bm_heal"
                                                     2) "inactive"
                                                     3) "central_bm_scale_out"
                                                     4) "active"
                                                  """

    scenario_passed = [
        ValidationScenarioParams("No current active operations",
                                 cmd_input_output_dict={
                                     get_all_redis_operation_status_cmd: CmdOutput(out=get_all_redis_operation_status_cmd_out_pass)
                                 },
                                 library_mocks_dict={"sys_parameters.get_version": Mock(return_value=Version.V24_7),
                                                     "sys_parameters.get_cluster_name": Mock(return_value="fi835a-ncs24-7"),
                                                     "adapter.docker_or_podman": Mock(return_value="podman")}
                                 )
    ]

    scenario_failed = [
        ValidationScenarioParams("There are current active operations",
                                 cmd_input_output_dict={
                                     get_all_redis_operation_status_cmd: CmdOutput(out=get_all_redis_operation_status_cmd_out_fail)
                                 },
                                 library_mocks_dict={"sys_parameters.get_version": Mock(return_value=Version.V24_7),
                                                     "sys_parameters.get_cluster_name": Mock(return_value="fi835a-ncs24-7"),
                                                     "adapter.docker_or_podman": Mock(return_value="podman")}
                                 )
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestCheckResourceLimitsOfBcmtCitmIngress(ValidationTestBase):
    tested_type = CheckResourceLimitsOfBcmtCitmIngress

    cmd = "sudo kubectl get daemonsets -n ncms bcmt-citm-ingress " \
          "-o jsonpath='{.spec.template.spec.containers[0].resources}'"
    out = '{{"limits":{{"cpu":"{}m","ephemeral-storage":"1Gi","memory":"{}Gi"}},"requests":{{"cpu":"100m"}}}}'

    scenario_passed = [
        ValidationScenarioParams("No limits - after the WA applied",
                                 cmd_input_output_dict={cmd: CmdOutput(out="{}")}),
        ValidationScenarioParams("limits in expected range",
                                 cmd_input_output_dict={cmd: CmdOutput(out.format(400, 2))})
    ]

    scenario_failed = [
        ValidationScenarioParams("cpu is smaller",
                                 cmd_input_output_dict={cmd: CmdOutput(out.format(200, 2))}),
        ValidationScenarioParams("memory is smaller",
                                 cmd_input_output_dict={cmd: CmdOutput(out.format(400, 1))}),
        ValidationScenarioParams("failed to parse",
                                 cmd_input_output_dict={cmd: CmdOutput(out.format("", 2))})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestValidateTunedProfile(ValidationTestBase):
    tested_type = ValidateTunedProfile

    out_good = '''
    Current active profile: throughput-performance
    '''

    out_bad = '''
    Current active profile: balanced
    '''

    validation_cmd = "sudo tuned-adm active"

    scenario_passed = [
        ValidationScenarioParams(scenario_title="Valid Tuned Profile ",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out=out_good)})

    ]

    scenario_failed = [
        ValidationScenarioParams("Invalid Tuned Profile", cmd_input_output_dict={validation_cmd: CmdOutput(out_bad)},
                                 failed_msg="Current Tuned profile set on this node is not matching with recommended tuned profile")

    ]

    scenario_unexpected_system_output = [
        ValidationScenarioParams("strange out", {validation_cmd: CmdOutput(out="some strange out", return_code=1)}),
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

class TestGenOpensslCnfFileExists(ValidationTestBase):
    tested_type = GenOpensslCnfFileExists

    scenario_passed = [
        ValidationScenarioParams(scenario_title="gen_openssl_cnf file exists",
                                 additional_parameters_dict={"file_exist": True})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="gen_openssl_cnf does not exist",
                                 additional_parameters_dict={"file_exist": False})
    ]

    def _init_mocks(self, tested_object):
        tested_object.file_utils.is_file_exist = Mock()
        tested_object.file_utils.is_file_exist.return_value = self.additional_parameters_dict['file_exist']

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestIrqServiceValidator(ValidationTestBase):
    tested_type = IrqServiceValidator

    mock_config_linux = {
        "hosts": {
            "host1": {
                "hieradata": {
                    "my_host_group": {
                        "cbis::my_host_group::irq_pinning_mode": "linux"
                    }
                }
            }
        }
    }

    mock_config_custom_numa = {
        "hosts": {
            "host1": {
                "hieradata": {
                    "my_host_group": {
                        "cbis::my_host_group::irq_pinning_mode": "custom-numa"
                    }
                }
            }
        }
    }

    mock_hosts_irq_linux = {
        "host1": {
            "irqbalance.service": "enabled",
            "cbis-irq-pinning.service": "disabled"
        }
    }

    mock_hosts_irq_custom_numa = {
        "host1": {
            "irqbalance.service": "disabled",
            "cbis-irq-pinning.service": "enabled"
        }
    }

    mock_hosts_irq_both_enabled = {
        "host1": {
            "irqbalance.service": "enabled",
            "cbis-irq-pinning.service": "enabled"
        }
    }

    mock_hosts_irq_both_disabled = {
        "host1": {
            "irqbalance.service": "disabled",
            "cbis-irq-pinning.service": "disabled"
        }
    }

    scenario_passed = [
        ValidationScenarioParams(scenario_title="irq linux mode config",
                                 additional_parameters_dict={"mock_config": mock_config_linux, "mock_hosts": mock_hosts_irq_linux}),
        ValidationScenarioParams(scenario_title="irq custom_numa mode config",
                                 additional_parameters_dict={"mock_config": mock_config_custom_numa,
                                                             "mock_hosts": mock_hosts_irq_custom_numa})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="irq mode mismatch the config",
                                 additional_parameters_dict={"mock_config": mock_config_linux, "mock_hosts": mock_hosts_irq_custom_numa}),
        ValidationScenarioParams(scenario_title="both irq services enabled",
                                 additional_parameters_dict={"mock_config": mock_config_linux,
                                                             "mock_hosts": mock_hosts_irq_both_enabled}),
        ValidationScenarioParams(scenario_title="both irq services disabled",
                                 additional_parameters_dict={"mock_config": mock_config_custom_numa,
                                                             "mock_hosts": mock_hosts_irq_both_disabled})
    ]

    def _init_mocks(self, tested_object):
        tested_object.run_data_collector = Mock()
        tested_object.run_data_collector.return_value = self.additional_parameters_dict['mock_hosts']

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        with patch("tools.ConfigStore.ConfigStore.get_ncs_bm_conf", return_value=scenario_params.additional_parameters_dict['mock_config']):
            ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        with patch("tools.ConfigStore.ConfigStore.get_ncs_bm_conf", return_value=scenario_params.additional_parameters_dict['mock_config']):
            ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestBcmtVrrpSecurityGroupValidation(ValidationTestBase):
    tested_type = BcmtVrrpSecurityGroupValidation

    vip_group_list_out = "default virtualip-instancegroup"

    vip_group_json_healthy = """
    {
      "status": { "vrrpState": [{"state": "ACTIVE"}, {"state": "STANDBY"}, {"state": "STANDBY"}] },
      "spec": { "nodeAssignment": [{"name": "node-1"}] }
    }
    """

    vip_group_json_unhealthy = """
    {
      "status": { "vrrpState": [{"state": "ACTIVE"}, {"state": "ACTIVE"}, {"state": "ACTIVE"}] },
      "spec": { "nodeAssignment": [{"name": "node-1"}] }
    }
    """

    server_list_out = '[{"ID": "server-123"}]'
    port_list_out = '[{"ID": "port-123"}]'
    port_show_out = '{"security_group_ids": ["sg-1"]}'

    scenario_passed = [
        ValidationScenarioParams(
            scenario_title="VRRP unhealthy but SG allows protocol 112",
            cmd_input_output_dict={
                "sudo /usr/local/bin/kubectl get virtualipinstancegroup -A --no-headers":
                    CmdOutput(out=vip_group_list_out),

                "sudo /usr/local/bin/kubectl get virtualipinstancegroup virtualip-instancegroup -n default -o json":
                    CmdOutput(out=vip_group_json_unhealthy),

                "server list --name node-1 -f json":
                    CmdOutput(out=server_list_out),

                "port list --server server-123 -f json":
                    CmdOutput(out=port_list_out),

                "port show port-123 -f json":
                    CmdOutput(out=port_show_out),

                "security group show sg-1 | grep '112' | wc -l":
                    CmdOutput(out="1"),
            }
        )
    ]

    scenario_failed = [
        ValidationScenarioParams(
            scenario_title="VRRP unhealthy and SG does not allow protocol 112",
            cmd_input_output_dict={
                "sudo /usr/local/bin/kubectl get virtualipinstancegroup -A --no-headers":
                    CmdOutput(out=vip_group_list_out),

                "sudo /usr/local/bin/kubectl get virtualipinstancegroup virtualip-instancegroup -n default -o json":
                    CmdOutput(out=vip_group_json_unhealthy),

                "server list --name node-1 -f json":
                    CmdOutput(out=server_list_out),

                "port list --server server-123 -f json":
                    CmdOutput(out=port_list_out),

                "port show port-123 -f json":
                    CmdOutput(out=port_show_out),

                "security group show sg-1 | grep '112' | wc -l":
                    CmdOutput(out="0"),
            }
        )
    ]

    def _init_mocks(self, tested_object):
        # Avoid kubectl exec lookup entirely
        tested_object.get_bcmt_exec_cmd = Mock(return_value="")

        # Make run_openstack_cmd behave like get_output_from_run_cmd
        tested_object.run_openstack_cmd = tested_object.get_output_from_run_cmd

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestValidateHelmStatus(ValidationTestBase):
    tested_type = ValidateHelmStatus

    helm_cmd_v22 = 'sudo helm ls -n ncms --all --output json | jq -r \'.[] | select(.status != "deployed") | .name\''
    helm_cmd_legacy = 'sudo helm ls --all --output json | jq -r \'.[] | select(.status != "deployed") | .name\''

    scenario_passed = [
        ValidationScenarioParams(
            scenario_title="All Helm deployments deployed (V22+)",
            version=Version.V22,
            cmd_input_output_dict={
                helm_cmd_v22: CmdOutput(out="")
            }
        ),
        ValidationScenarioParams(
            scenario_title="All Helm deployments deployed (Legacy)",
            version=Version.V20_FP2,
            cmd_input_output_dict={
                helm_cmd_legacy: CmdOutput(out="")
            }
        )
    ]

    scenario_failed = [
        ValidationScenarioParams(
            scenario_title="Helm deployments not deployed (V22+)",
            version=Version.V22,
            cmd_input_output_dict={
                helm_cmd_v22: CmdOutput(out="chart-a\nchart-b")
            }
        ),
        ValidationScenarioParams(
            scenario_title="Helm deployments not deployed (Legacy)",
            version=Version.V20,
            cmd_input_output_dict={
                helm_cmd_legacy: CmdOutput(out="chart-a")
            }
        )
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestCheckNodeRebootRequired(ValidationTestBase):
    tested_type = CheckNodeRebootRequired
    scenario_passed = [
        ValidationScenarioParams(
            scenario_title="no nodes require reboot",
            data_collector_dict={
                GetNodeNameForRebootRequired: {
                    "node-1": "",
                    "node-2": "",
                    "node-3": ""
                }
            }
        )
    ]

    scenario_failed = [
        ValidationScenarioParams(
            scenario_title="multiple nodes require reboot",
            data_collector_dict={
                GetNodeNameForRebootRequired: {
                    "node-1": "/var/run/reboot-required",
                    "node-2": "",
                    "node-3": "/var/run/reboot-required"
                }
            }
        )
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)
