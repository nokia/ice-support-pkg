from __future__ import absolute_import
import pytest
from tests.pytest.pytest_tools.operator.test_operator import CmdOutput
from tests.pytest.pytest_tools.operator.test_validation_base import ValidationTestBase, ValidationScenarioParams
from tests.pytest.tools.versions_alignment import Mock
from flows.Monitoring.elk_validations import *
from six.moves import range

class TestCheckElkFsAccessibleOrNot(ValidationTestBase):
    tested_type = CheckElkFsAccessibleOrNot

    cmd = "sudo ls /elk"

    scenario_passed = [
        ValidationScenarioParams("Verify /elk is accessible",
                                 {cmd: CmdOutput(out="17G     /elk", return_code=0)})
    ]

    scenario_failed = [
        ValidationScenarioParams("Verify /elk is not accessible",
                                 {cmd: CmdOutput(out="", return_code=1)})
    ]

    scenario_prerequisite_not_fulfilled = [
        ValidationScenarioParams("prerequisite_not_fulfilled",
                                 {"grep -i 'monitor' /etc/hosts": CmdOutput(out="", return_code=0)},
                                 tested_object_mock_dict={"get_host_roles": Mock(return_value={})},
                                 library_mocks_dict={"gs.get_deployment_type": Mock(return_value=Deployment_type.NCS_OVER_BM),
                                                     "ConfigStore.get_ncs_bm_conf": Mock(return_value={'management_deployment':{'deploy_elk':False},
                                                                                                       'openstack_deployment':{'deploy_elk':False}})})
    ]

    scenario_prerequisite_fulfilled = [
        ValidationScenarioParams("prerequisite_fulfilled 'monitoring' in get_host_roles",
                                 {"grep -i 'monitor' /etc/hosts": CmdOutput(out="", return_code=0)},
                                 tested_object_mock_dict={"get_host_roles": Mock(return_value={"monitoring"})},
                                 library_mocks_dict={"gs.get_deployment_type": Mock(return_value=Deployment_type.NCS_OVER_BM),
                                                     "ConfigStore.get_ncs_bm_conf": Mock(return_value={'management_deployment':{'deploy_elk':True}})}),
        ValidationScenarioParams("prerequisite_fulfilled not has_monitoring_nodes",
                                 {"grep -i 'monitor' /etc/hosts": CmdOutput(out="", return_code=1)},
                                 tested_object_mock_dict={"get_host_roles": Mock(return_value={})},
                                 library_mocks_dict={"gs.get_deployment_type": Mock(return_value=Deployment_type.NCS_OVER_BM),
                                                     "ConfigStore.get_ncs_bm_conf": Mock(return_value={'management_deployment':{'deploy_elk':True}})}),
        ValidationScenarioParams("prerequisite_fulfilled 'monitoring' in get_host_roles and not has_monitoring_nodes",
                                 {"grep -i 'monitor' /etc/hosts": CmdOutput(out="", return_code=1)},
                                 tested_object_mock_dict={"get_host_roles": Mock(return_value={"monitoring"})},
                                 library_mocks_dict={"gs.get_deployment_type": Mock(return_value=Deployment_type.NCS_OVER_BM),
                                                     "ConfigStore.get_ncs_bm_conf": Mock(return_value={'management_deployment':{'deploy_elk':True}})})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_prerequisite_not_fulfilled)
    def test_prerequisite_not_fulfilled(self, scenario_params, tested_object):
        ValidationTestBase.test_prerequisite_not_fulfilled(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_prerequisite_fulfilled)
    def test_prerequisite_fulfilled(self, scenario_params, tested_object):
        ValidationTestBase.test_prerequisite_fulfilled(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestElkDaysRetentionConsistency(ValidationTestBase):
    tested_type = ElkDaysRetentionConsistency

    out = """actions:
  1:
    action: delete_indices
    description: Delete cloud- index older than unit_count days (as listed below)
    filters:
    - exclude: null
      filtertype: pattern
      kind: prefix
      value: cloud-
    - direction: older
      exclude: null
      unit_count: '{}'
    options:
      continue_if_exception: false
  2:
    action: delete_indices
    description: Delete ceph- index older than unit_count days (as listed below)
    filters:
    - exclude: null
      filtertype: pattern
    - direction: older
      exclude: null
      filtertype: age
      unit_count: '{}'
    options:
      continue_if_exception: false
      disable_action: false
      ignore_empty_list: true
      timeout_override: null
  3:
    action: delete_indices
    description: Delete metricbeat- index older than unit_count days (as listed below)
    filters:
    - exclude: null
    - direction: older
      unit_count: '5'
    options:
      continue_if_exception: false
      timeout_override: null"""

    scenario_passed = [ValidationScenarioParams("consistent",
                                                cmd_input_output_dict={
                                                    "sudo cat /etc/elk/curator/actions.yml": CmdOutput(out.format(5, 5))
                                                })]

    scenario_failed = [ValidationScenarioParams("not consistent",
                                                cmd_input_output_dict={
                                                    "sudo cat /etc/elk/curator/actions.yml": CmdOutput(out.format(1, 9))
                                                })]

    scenario_prerequisite_not_fulfilled = [ValidationScenarioParams(
        "prerequisite_not_fulfilled", {"sudo docker ps -a | grep curator": CmdOutput("", return_code=1)})]

    scenario_prerequisite_fulfilled = [ValidationScenarioParams(
        "prerequisite_fulfilled", {"sudo docker ps -a | grep curator": CmdOutput("", return_code=0)})]

    @pytest.mark.parametrize("scenario_params", scenario_prerequisite_not_fulfilled)
    def test_prerequisite_not_fulfilled(self, scenario_params, tested_object):
        ValidationTestBase.test_prerequisite_not_fulfilled(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_prerequisite_fulfilled)
    def test_prerequisite_fulfilled(self, scenario_params, tested_object):
        ValidationTestBase.test_prerequisite_fulfilled(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestValidateElkDeployedInLargeSystems(ValidationTestBase):
    tested_type = ValidateElkDeployedInLargeSystems

    get_setup_host_list_out = {'host1': {'roles': ['monitoring', 'controllers', 'all-hosts', 'one_controller']},
                               'host2': {'roles': ['monitoring', 'controllers', 'all-hosts', 'one_controller']},
                               'host3': {'roles': ['monitoring', 'controllers', 'all-hosts', 'one_controller']}}

    get_setup_host_list_out_without_monitor = {'host1': {'roles': ['controllers', 'all-hosts', 'one_controller']},
                               'host2': {'roles': ['controllers', 'all-hosts', 'one_controller']},
                               'host3': {'roles': ['controllers', 'all-hosts', 'one_controller']}}

    for i in range(4, 75):  # Creating host4 to host74
        get_setup_host_list_out['host{}'.format(i)] = {'roles': ['monitoring', 'controllers', 'all-hosts', 'one_controller']}
        get_setup_host_list_out_without_monitor['host{}'.format(i)] = {'roles': ['controllers', 'all-hosts', 'one_controller']}

    scenario_passed = [ValidationScenarioParams("ELK deployment type local",
                                                {"sudo du -s /elk": CmdOutput(out="42  /elk", return_code=0)},
                                                tested_object_mock_dict={
                                                    "get_host_roles": Mock(return_value={Objectives.UC})},

                                                library_mocks_dict={
                                                    'GetInfo.get_setup_host_list': Mock(
                                                        return_value=get_setup_host_list_out),
                                                    "ConfigStore.get_cbis_user_config": Mock(return_value={'CBIS': {
                                                        'openstack_deployment': {'elk_deployment_type': 'local'}}})

                                                }),
                       ValidationScenarioParams("SSC deployment type local",
                                                {"sudo du -s /elk": CmdOutput(out="42  /elk", return_code=0)},
                                                tested_object_mock_dict={
                                                    "get_host_roles": Mock(return_value={Objectives.UC})},

                                                library_mocks_dict={
                                                    'GetInfo.get_setup_host_list': Mock(
                                                        return_value=get_setup_host_list_out),
                                                    "ConfigStore.get_cbis_user_config": Mock(return_value={'CBIS': {
                                                        'openstack_deployment': {'ssc_deployment_type': 'local'}}})

                                                }),
                       ValidationScenarioParams("ELK deployment type remote",
                                                tested_object_mock_dict={
                                                    "get_host_roles": Mock(return_value={Objectives.UC})},

                                                library_mocks_dict={
                                                    'GetInfo.get_setup_host_list': Mock(
                                                        return_value=get_setup_host_list_out),
                                                    "ConfigStore.get_cbis_user_config": Mock(return_value={'CBIS': {
                                                        'openstack_deployment': {'elk_deployment_type': 'remote'}}})

                                                }),
                       ValidationScenarioParams("SSC deployment type remote",
                                                tested_object_mock_dict={
                                                    "get_host_roles": Mock(return_value={Objectives.UC})},

                                                library_mocks_dict={
                                                    'GetInfo.get_setup_host_list': Mock(
                                                        return_value=get_setup_host_list_out),
                                                    "ConfigStore.get_cbis_user_config": Mock(return_value={'CBIS': {
                                                        'openstack_deployment': {'ssc_deployment_type': 'remote'}}})

                                                })



                       ]

    scenario_failed = [ValidationScenarioParams(scenario_title="When ELK is set to local without Monitor node",
                                 tested_object_mock_dict={
                                     "get_host_roles": Mock(return_value={Objectives.UC})},
                                 library_mocks_dict={
                                                    'GetInfo.get_setup_host_list': Mock(return_value=get_setup_host_list_out_without_monitor),
                                                    "ConfigStore.get_cbis_user_config": Mock(return_value={'CBIS': {
                                                        'openstack_deployment': {'ssc_deployment_type': 'local'}}})

                                     })]

    scenario_prerequisite_not_fulfilled = [ValidationScenarioParams("prerequisite_not_fulfilled",
                                                                    library_mocks_dict={
                                                                        "ConfigStore.get_cbis_user_config": Mock(
                                                                            return_value={'CBIS': {
                                                                                'openstack_deployment': {
                                                                                    'deploy_elk': False}}})})]

    scenario_prerequisite_fulfilled = [ValidationScenarioParams("prerequisite_fulfilled",
                                                                library_mocks_dict={
                                                                    "ConfigStore.get_cbis_user_config": Mock(
                                                                        return_value={'CBIS': {'openstack_deployment': {
                                                                            'deploy_elk': True}}})})]

    @pytest.mark.parametrize("scenario_params", scenario_prerequisite_not_fulfilled)
    def test_prerequisite_not_fulfilled(self, scenario_params, tested_object):
        ValidationTestBase.test_prerequisite_not_fulfilled(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_prerequisite_fulfilled)
    def test_prerequisite_fulfilled(self, scenario_params, tested_object):
        ValidationTestBase.test_prerequisite_fulfilled(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestValidateElkCuratorCronTimeIsOffset(ValidationTestBase):
    tested_type = ValidateElkCuratorCronTimeIsOffset
    dummy_command = "dummy_get_cron_from_hosts"

    scenario_prerequisite_not_fulfilled = [
        ValidationScenarioParams(
            "ELK not deployed",
            {},
            library_mocks_dict={
                "ConfigStore.get_ncs_bm_conf": Mock(return_value={
                    'management_deployment': {'deploy_elk': False}
                })
            }
        )
    ]

    scenario_prerequisite_fulfilled = [
        ValidationScenarioParams(
            "ELK deployed",
            {},
            library_mocks_dict={
                "ConfigStore.get_ncs_bm_conf": Mock(return_value={
                    'management_deployment': {'deploy_elk': True}
                })
            }
        )
    ]

    scenario_passed = [
        ValidationScenarioParams(
            "All nodes have different cron times",
            {dummy_command: Mock(return_value={
                'node1': '0 1 * * * sudo /bin/podman start elk-curator',
                'node2': '0 2 * * * sudo /bin/podman start elk-curator',
                'node3': '0 3 * * * sudo /bin/podman start elk-curator',
            })},
            tested_object_mock_dict={
                "run_data_collector": Mock(return_value={
                    'node1': '0 1 * * * sudo /bin/podman start elk-curator',
                    'node2': '0 2 * * * sudo /bin/podman start elk-curator',
                    'node3': '0 3 * * * sudo /bin/podman start elk-curator',
                }),
                "is_prerequisite_fulfilled": Mock(return_value=True)
            },
            library_mocks_dict={
                "ConfigStore.get_ncs_bm_conf": Mock(return_value={
                    'management_deployment': {'deploy_elk': True}
                })
            }
        )
    ]

    scenario_failed = [
        ValidationScenarioParams(
            "Duplicate cron times found",
            {dummy_command: Mock(return_value={
                'node1': '0 3 * * * sudo /bin/podman start elk-curator',
                'node2': '0 3 * * * sudo /bin/podman start elk-curator',
                'node3': '0 5 * * * sudo /bin/podman start elk-curator',
            })},
            tested_object_mock_dict={
                "run_data_collector": Mock(return_value={
                    'node1': '0 3 * * * sudo /bin/podman start elk-curator',
                    'node2': '0 3 * * * sudo /bin/podman start elk-curator',
                    'node3': '0 5 * * * sudo /bin/podman start elk-curator',
                }),
                "is_prerequisite_fulfilled": Mock(return_value=True)
            },
            library_mocks_dict={
                "ConfigStore.get_ncs_bm_conf": Mock(return_value={
                    'management_deployment': {'deploy_elk': True}
                })
            }
        )
    ]

    @pytest.mark.parametrize("scenario_params", scenario_prerequisite_not_fulfilled)
    def test_prerequisite_not_fulfilled(self, scenario_params, tested_object):
        ValidationTestBase.test_prerequisite_not_fulfilled(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_prerequisite_fulfilled)
    def test_prerequisite_fulfilled(self, scenario_params, tested_object):
        ValidationTestBase.test_prerequisite_fulfilled(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)