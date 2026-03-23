from __future__ import absolute_import
import pytest
from mock.mock import Mock, patch

from flows.Chain_of_events.operation_timing_info import Operation_timing_info
from flows.Chain_of_events.operation_timing_info_mechanism import OperationTimeLineCmdRunner
from tools.global_enums import Objectives, Deployment_type


def get_operations_per_deployment_type():
    cbis_operation = {
        "name": "post_install",
        "role": {"Deployment_type.CBIS": "Objectives.UC"},
        "is_required": False,
        "log_path": "/var/log/cbis/overcloud_installation.log",
        "searched_patterns":
            {
                "start_time": "sudo grep -sr \"Executing playbooks: \\['/usr/share/cbis/cbis-ansible/post-install/post-install.yml'\\]\"",
                "end_time": "grep -i 'deployment ended'"
            }
    }
    cbis_patterns = {
        "start_time": "sudo grep -sr \"Executing playbooks: \\['/usr/share/cbis/cbis-ansible/post-install/post-install.yml'\\]\" /var/log/cbis/overcloud_installation.log",
        "end_time": "grep -i 'deployment ended' /var/log/cbis/overcloud_installation.log"}
    ncs_operation = {
        "name": "post_install_configuration",
        "role": {"Deployment_type.NCS_OVER_BM": "Objectives.ONE_MANAGER"},
        "is_required": False,
        "file_per_attempt_operation": True,
        "log_path": "/var/log/cbis/{cluster_name}add_bm_configuration*",
        "searched_patterns":
            {
                "success_search": "sudo grep -i 'New Bm Configuration Added Successfully'"
            }
    }
    ncs_patterns = {
        "success_search": "sudo grep -i 'New Bm Configuration Added Successfully' "
                          "/var/log/cbis/{cluster_name}add_bm_configuration*"}

    return [
        (Deployment_type.CBIS, cbis_operation, cbis_patterns, Objectives.UC),
        (Deployment_type.NCS_OVER_BM, ncs_operation, ncs_patterns, Objectives.ONE_MANAGER)
    ]


class TestOperationTimingInfoMechanism:
    @pytest.mark.parametrize("is_run_inside_container", [True, False])
    @pytest.mark.parametrize("deployment_type, operation, patterns, expected_role",
                             get_operations_per_deployment_type())
    def test_command_builder(self, deployment_type, operation, patterns, expected_role, is_run_inside_container):
        operation_timing = Operation_timing_info(Mock())

        if is_run_inside_container:
            expected_role = Objectives.ICE_CONTAINER

        operation_timing._operation = operation

        with patch("flows.Chain_of_events.operation_timing_info.gs.get_deployment_type",
                   Mock(return_value=deployment_type)):
            with patch("flows.Chain_of_events.operation_timing_info.ExecutionHelper.is_run_inside_container",
                       Mock(return_value=is_run_inside_container)):
                operation_timing._set_role()

        assert operation_timing._objective_role == expected_role

        for pattern in patterns:
            operation_timing_info_mechanism = operation_timing.get_operation_timing_info_mechanism()
            cmd = operation_timing_info_mechanism._command_builder(pattern, operation_timing._operation['log_path'])

            assert cmd == patterns[pattern]

    def test_create_list_of_times_dicts(self):
        validation_mock = Mock()
        validation_mock.run_data_collector.return_value = {
            "undercloud": {
                "out": "2020-10-20 12:08:34,357",
                "err": "",
                "code": 0}
        }
        operation_timing = Operation_timing_info(validation_mock)
        operation = {
            "name": "post_install",
            "role": {"Deployment_type.CBIS": "Objectives.UC"},
            "is_required": False,
            "log_path": "tests/validation_tests/inputs/overcloud_installation.log",
            "searched_patterns":
                {
                    "start_time": "sudo grep -sr "
                                  "\"Executing playbooks: "
                                  "\\['/usr/share/cbis/cbis-ansible/post-install/post-install.yml'\\]\"",
                    "end_time": "grep -i 'deployment ended'",
                    "success_search": "sudo grep 'END return value: 0'"
                }
        }
        operation_timing._operation = operation
        operation_timing._objective_role = Objectives.ICE_CONTAINER
        operation_timing_info_mechanism = operation_timing.get_operation_timing_info_mechanism()

        with patch("flows.Chain_of_events.operation_timing_info_single_file_for_attempts_mechanism.log"):
            with patch("flows.Chain_of_events.operation_timing_info_mechanism.gs.get_deployment_type",
                       Mock(return_value=Deployment_type.CBIS)):
                times_dicts_list = operation_timing_info_mechanism._create_list_of_times_dicts(
                    operation_timing._operation['log_path'])

        validation_mock.run_data_collector.assert_any_call(
            OperationTimeLineCmdRunner,
            cmd="sudo grep -sr \"Executing playbooks: \\['/usr/share/cbis/cbis-ansible/post-install/post-install.yml'"
                "\\]\" tests/validation_tests/inputs/overcloud_installation.log", timeout=60)
        assert len(times_dicts_list) > 0
