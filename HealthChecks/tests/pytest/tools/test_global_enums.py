from __future__ import absolute_import
import pytest

from invoker.validations_flows_list import ValidationFlowList
from tools.adapter import initialize_adapter_instance
from tools.global_enums import Version, Deployment_type, BlockingTag, ImplicationTag
from tests.pytest.tools.versions_alignment import Mock
from tools import sys_parameters, user_params

class TestGlobalEnums():
    @pytest.mark.parametrize("version_str, expected_version, deployment_type",
                             [("19.0.0", Version.V19, Deployment_type.CBIS),
                              ("19.100.0", Version.V19A, Deployment_type.CBIS),
                              ("20.100.1", Version.V20, Deployment_type.CBIS),
                              ("20.03.1", Version.V20, Deployment_type.CBIS),
                              ("20.100.6", Version.V20, Deployment_type.CBIS),
                              ("20.100.12", Version.V20, Deployment_type.CBIS),
                              ("22.100.1", Version.V22, Deployment_type.CBIS),
                              ("22.02.1", Version.V22_FP1, Deployment_type.CBIS),
                              ("22.07.1", Version.V22, Deployment_type.CBIS),
                              ("22.100.12", Version.V22, Deployment_type.CBIS),
                              ("23.100.21", Version.NOT_EXIST_VERSION, Deployment_type.CBIS),
                              ("19.0.0", Version.NOT_EXIST_VERSION, Deployment_type.NCS_OVER_BM),
                              ("19.100.0", Version.NOT_EXIST_VERSION, Deployment_type.NCS_OVER_BM),
                              ("20.100.1", Version.V20, Deployment_type.NCS_OVER_BM),
                              ("20.03.1", Version.V20, Deployment_type.NCS_OVER_BM),
                              ("20.100.6", Version.V20_FP1, Deployment_type.NCS_OVER_BM),
                              ("20.100.12", Version.V20_FP2, Deployment_type.NCS_OVER_BM),
                              ("20.12.0", Version.V20_FP2, Deployment_type.NCS_OVER_BM),
                              ("22.100.1", Version.V22, Deployment_type.NCS_OVER_BM),
                              ("22.02.1", Version.V22, Deployment_type.NCS_OVER_BM),
                              ("22.07.1", Version.V22_7, Deployment_type.NCS_OVER_BM),
                              ("22.100.12", Version.V22_12, Deployment_type.NCS_OVER_BM),
                              ("23.100.21", Version.NOT_EXIST_VERSION, Deployment_type.NCS_OVER_BM),
                              ("23.10.0", Version.V23_10, Deployment_type.NCS_OVER_BM)])
    def test_convert_str_to_version_const(self, version_str, expected_version, deployment_type):
        assert Version.convert_str_to_version_const(deployment_type, version_str) == expected_version

    def dont_test_scale_upgrade_blocker(self):
        log_flows = ['scale_log_error_flow', 'system_log_error_flow']

        all_flows = ValidationFlowList.get_list_of_flows()
        ignore_scale_upgrade_blocker_dict = {BlockingTag.SCALE: [
            "is_runtime_cephfs_keyring_match_configured_cephfs_keyring",
            "is_runtime_cephrbd_keyring_match_configured_cephrbd_keyring",
            "is_runtime_openstack_keyring_match_configured_openstack_keyring",
            "is_runtime_admin_keyring_match_configured_admin_keyring",
            "is_runtime_baremetal.cephfs_keyring_match_configured_baremetal.cephfs_keyring",
            "is_runtime_radosgw_keyring_match_configured_radosgw_keyring",
            "basic_memory_validation",
            "cpu_usage_validation",
            "verify_ca_issuer_is_present",
            "overcloudrc_content_check",
            "verify_kubectl_command_execution",
            "calico_kubernetes_check"
        ],
            BlockingTag.UPGRADE: ["is_runtime_cephfs_keyring_match_configured_cephfs_keyring",
                                  "is_runtime_cephrbd_keyring_match_configured_cephrbd_keyring",
                                  "is_runtime_openstack_keyring_match_configured_openstack_keyring",
                                  "is_runtime_admin_keyring_match_configured_admin_keyring",
                                  "is_runtime_baremetal.cephfs_keyring_match_configured_baremetal.cephfs_keyring",
                                  "is_runtime_radosgw_keyring_match_configured_radosgw_keyring",
                                  "verify_ca_issuer_is_present",
                                  "overcloudrc_content_check",
                                  "verify_kubectl_command_execution",
                                  "calico_kubernetes_check"]}
        blocking_tag = [BlockingTag.SCALE, BlockingTag.UPGRADE]
        implication_tag = ImplicationTag.PRE_OPERATION
        missing_blocking_tag_dict = {}
        for flow in all_flows:
            current_flow = flow()
            for deployment_type in Deployment_type.AVAILABLE_TYPES:
                for version in Version.AVAILABLE_VERSIONS:
                    if deployment_type in current_flow.deployment_type_list():
                        if not current_flow.command_name() in log_flows:
                            validation_class_list = current_flow._get_list_of_validator_class(version, deployment_type)
                            for validation_class in validation_class_list:
                                initialize_adapter_instance(deployment_type, version)
                                validation_object = validation_class(Mock())
                                user_params.initialization_factory = Mock()
                                sys_parameters.get_version = Mock(return_value=version)
                                sys_parameters.get_deployment_type = Mock(return_value=deployment_type)
                                sys_parameters.get_hotfix_list = Mock(return_value=["hotfix"])
                                missing_blocking_tag_list = self.get_missing_blocking_tag_per_validation(
                                    implication_tag=implication_tag, validation_object=validation_object,
                                    validation_class=validation_class, blocking_tag=blocking_tag,
                                    ignore_blocker_dict=ignore_scale_upgrade_blocker_dict)
                                for tag in missing_blocking_tag_list:
                                    missing_blocking_tag_dict.setdefault(tag,[]).append(validation_object._unique_operation_name)
        assert_messages = []
        for tag, validations_list in list(missing_blocking_tag_dict.items()):
            if len(validations_list):
                assert_messages.append("missing {} on {}".format(tag, list(set(validations_list))))
        assert len(assert_messages) == 0, '\n'.join(assert_messages)

    def get_missing_blocking_tag_per_validation(self, implication_tag, validation_object, validation_class, blocking_tag,
                                ignore_blocker_dict):
        missing_tag_list = []
        if implication_tag in validation_object._implication_tags:
            for tag in blocking_tag:
                if tag not in validation_object._blocking_tags and validation_object._unique_operation_name not in ignore_blocker_dict[tag]:
                    missing_tag_list.append(tag)
        return missing_tag_list

