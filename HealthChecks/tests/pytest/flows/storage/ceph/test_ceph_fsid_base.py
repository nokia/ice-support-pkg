from __future__ import absolute_import
import warnings
from tests.pytest.tools.versions_alignment import nested

import pytest
from tests.pytest.tools.versions_alignment import Mock, patch
from flows.Storage.ceph.CephFSID import *
from tests.pytest.pytest_tools.operator.test_operator import CmdOutput
from tests.pytest.pytest_tools.operator.test_validation_base import ValidationTestBase, ValidationScenarioParams


class TestCephFSIDValidation(ValidationTestBase):
    tested_type = CephFSIDValidation
    ipmitool_lan_print = """
Set in Progress         : Set Complete
IP Address              : 10.75.243.84
Subnet Mask             : 255.255.240.0
Cipher Suite Priv Max   : XuuaXXXXXXXXXXX
                        :     X=Cipher Suite Unused
                        :     c=CALLBACK
                        :     u=USER
                        :     o=OPERATOR
                        :     a=ADMIN
                        :     O=OEM
Bad Password Threshold  : Not Available"""
    host_groups = {"host_groups": [{"pm_addr": ['10.75.243.83', '10.75.243.84'], "vm_pool": "sriov"},
                                   {"pm_addr": ['10.75.243.86', '10.75.243.87'], "vm_pool": "dpdk"}]}
    uuid_pools = {"ovs": "1eef0798-5679-4a20-b565-2e7a7557b803", "sriov": "6ae21dfe-dd69-472b-bdff-1532d8bce82a",
                  "dpdk": "8a9ffdd6-1385-41e4-b1d2-c856cf48a0b7"}
    ipmitool_lan_print_missing_ip_address = re.sub(".*"+"IP Address"+".*\n?", "", ipmitool_lan_print)

    scenario_get_ip_address = [
        ValidationScenarioParams("base scenario", cmd_input_output_dict={
            "sudo ipmitool lan print": CmdOutput(ipmitool_lan_print)}, additional_parameters_dict={
            'expected_res': "10.75.243.84"}),
        ValidationScenarioParams("missing_ip_address scenario", cmd_input_output_dict={
            "sudo ipmitool lan print": CmdOutput(ipmitool_lan_print_missing_ip_address)},
                                 additional_parameters_dict={'expected_res': None})]

    scenario_get_pool_uuid_if_exist = [ValidationScenarioParams("base scenario", library_mocks_dict={
        "CephInfo.is_multiple_pools_enable": Mock(return_value=True),
        "CephInfo.get_uuid_pools": Mock(return_value=uuid_pools)}, tested_object_mock_dict={
        "get_ip_address": Mock(return_value="xxxx.x.x.x"), "get_vm_pool_by_pm_addr": Mock(return_value="sriov")},
        additional_parameters_dict={'expected_res': "6ae21dfe-dd69-472b-bdff-1532d8bce82a"}),
        ValidationScenarioParams("missing vm_pool scenario", library_mocks_dict={
            "CephInfo.is_multiple_pools_enable": Mock(return_value=True)}, tested_object_mock_dict={
            "get_ip_address": Mock(return_value="xxxx.x.x.x"), "get_vm_pool_by_pm_addr": Mock(return_value=None)},
            additional_parameters_dict={'expected_res': None}),
        ValidationScenarioParams("disable multiple_pools scenario", library_mocks_dict={
            "CephInfo.is_multiple_pools_enable": Mock(return_value=False)}, additional_parameters_dict={
            'expected_res': None})]

    scenario_unexpected_system_output_get_pool_uuid_if_exist = [ValidationScenarioParams("unexpected_system_output scenario", library_mocks_dict={
        "CephInfo.is_multiple_pools_enable": Mock(return_value=True),
        "CephInfo.get_uuid_pools": Mock(return_value=uuid_pools)}, tested_object_mock_dict={
        "get_ip_address": Mock(return_value="xxxx.x.x.x"), "get_vm_pool_by_pm_addr": Mock(return_value="xxx")})]

    scenario_get_vm_pool_by_pm_addr = [
        ValidationScenarioParams("base scenario", tested_object_mock_dict={
            "get_dict_from_file": Mock(return_value=host_groups)}, additional_parameters_dict={
            'expected_res': "sriov", "pm_addr": "10.75.243.83"}),
        ValidationScenarioParams("missing vm_pool scenario", tested_object_mock_dict={
            "get_dict_from_file": Mock(return_value={"host_groups": [{"pm_addr": ['10.75.243.83']}]})},
                              additional_parameters_dict={'expected_res': None, "pm_addr": "10.75.243.83"}),
        ValidationScenarioParams("missing_pm_addr scenario", tested_object_mock_dict={
            "get_dict_from_file": Mock(return_value=host_groups)}, additional_parameters_dict={
            'expected_res': None, "pm_addr": "10.75.243.81"})]

    scenario_unexpected_system_output_get_vm_pool_by_pm_addr = [
        ValidationScenarioParams("missing hosts_groups scenario", tested_object_mock_dict={"get_dict_from_file": Mock(
            return_value={"xxx": "yyy"})}, additional_parameters_dict={"pm_addr": "10.75.243.81"}),
        ValidationScenarioParams("missing pm_addr scenario", tested_object_mock_dict={"get_dict_from_file": Mock(
            return_value={"host_groups": [{"xxx": "yyy"}]})}, additional_parameters_dict={"pm_addr": "10.75.243.81"})]

    @pytest.fixture
    def mock_enforce_have_document(self, monkeypatch):
        mock = Mock()
        monkeypatch.setattr(CephFSIDValidation, '_enforce_have_document', mock)
        return mock

    @pytest.fixture
    def mock_set_initial_values(self, monkeypatch):
        mock = Mock()
        monkeypatch.setattr(CephFSIDValidation, 'set_initial_values', mock)
        return mock

    @pytest.fixture
    def mock_set_document(self, monkeypatch):
        mock = Mock()
        monkeypatch.setattr(CephFSIDValidation, 'set_document', mock)
        CephFSIDValidation.objective_hosts = [Objectives.ALL_HOSTS]
        CephFSIDValidation._severity = Severity.CRITICAL
        CephFSIDValidation._is_clean_cmd_info = False
        return mock

    @pytest.mark.parametrize("scenario_params", scenario_get_vm_pool_by_pm_addr)
    def test_get_vm_pool_by_pm_addr(self, mock_enforce_have_document, mock_set_initial_values, mock_set_document, scenario_params, tested_object):
        self._init_validation_object(tested_object, scenario_params)
        context_managers = self._prepare_patches_list(tested_object)
        # python 3 not support nested
        with nested(*context_managers):
            assert tested_object.get_vm_pool_by_pm_addr(self.additional_parameters_dict["pm_addr"]) == self.additional_parameters_dict['expected_res']

    @pytest.mark.parametrize("scenario_params", scenario_get_pool_uuid_if_exist)
    def test_get_pool_uuid_if_exist(self, mock_enforce_have_document, mock_set_initial_values, mock_set_document, scenario_params, tested_object):
        self._init_validation_object(tested_object, scenario_params)
        context_managers = self._prepare_patches_list(tested_object)
        # python 3 not support nested
        with nested(*context_managers):
            assert tested_object.get_pool_uuid_if_exist() == self.additional_parameters_dict['expected_res']

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output_get_pool_uuid_if_exist)
    def test_unexpected_system_output_get_pool_uuid_if_exist(self, mock_enforce_have_document, mock_set_initial_values, mock_set_document, scenario_params, tested_object):
        self._init_validation_object(tested_object, scenario_params)
        context_managers = self._prepare_patches_list(tested_object)
        # python 3 not support nested
        with nested(*context_managers):
            with pytest.raises(UnExpectedSystemOutput):
                tested_object.get_pool_uuid_if_exist()

    @pytest.mark.parametrize("scenario_params", scenario_get_ip_address)
    def test_get_ip_address(self, mock_enforce_have_document, mock_set_initial_values, mock_set_document, scenario_params, tested_object):
        self._init_validation_object(tested_object, scenario_params)
        context_managers = self._prepare_patches_list(tested_object)
        # python 3 not support nested
        with nested(*context_managers):
            assert tested_object.get_ip_address() == self.additional_parameters_dict['expected_res']

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output_get_vm_pool_by_pm_addr)
    def test_unexpected_system_output_get_vm_pool_by_pm_addr(self, mock_enforce_have_document, mock_set_initial_values, mock_set_document, scenario_params, tested_object):
        self._init_validation_object(tested_object, scenario_params)
        context_managers = self._prepare_patches_list(tested_object)
        # python 3 not support nested
        with nested(*context_managers):
            with pytest.raises(UnExpectedSystemOutput):
                tested_object.get_vm_pool_by_pm_addr(self.additional_parameters_dict["pm_addr"])

    def test_has_confluence(self, mock_enforce_have_document, mock_set_initial_values, mock_set_document, tested_object):
        # Override the func since this val doesn't have a confluence.
        # pls do not copy it! it's only for old validations that do not have a confluence page.
        warnings.warn("No confluence page")