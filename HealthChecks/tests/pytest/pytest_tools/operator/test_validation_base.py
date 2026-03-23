from __future__ import absolute_import
import json
import os
import re

from tests.pytest.tools.versions_alignment import nested

import pytest

from tests.pytest.pytest_tools.operator.test_operator import OperatorTestBase, ScenarioParams
from tools.Exceptions import UnExpectedSystemOutput, NoSuitableHostWasFoundForRoles, NonIdenticalValues
from tools.lazy_global_data_loader import LazyDataLoader


class ValidationScenarioParams(ScenarioParams):
    def __init__(self, scenario_title, cmd_input_output_dict=None, version=None, data_collector_dict=None,
                 library_mocks_dict=None, tested_object_mock_dict=None, failed_msg=None,
                 additional_parameters_dict=None):
        super(ValidationScenarioParams, self).__init__(scenario_title, cmd_input_output_dict, version, data_collector_dict,
                                                       library_mocks_dict, tested_object_mock_dict,
                                                       additional_parameters_dict)
        self.failed_msg = failed_msg


class ValidationTestBase(OperatorTestBase):
    scenario_passed = []
    scenario_failed = []
    scenario_unexpected_system_output = []
    scenario_no_suitable_host = []
    scenario_no_identical_values = []

    def test_has_confluence(self, tested_object):
        tested_object.set_document()
        name_to_url_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "tools",
                                        "name_to_url.json")

        with open(name_to_url_path) as f:
            name_to_url_dict = json.load(f)

        assert tested_object._unique_operation_name in list(name_to_url_dict.keys())

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_prerequisite_not_fulfilled(self, scenario_params, tested_object):
        self._init_validation_object(tested_object, scenario_params)

        context_managers = self._prepare_patches_list(tested_object)

        # python 3 not support nested
        with nested(*context_managers):
            assert tested_object.is_prerequisite_fulfilled() is False

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_prerequisite_fulfilled(self, scenario_params, tested_object):
        self._init_validation_object(tested_object, scenario_params)

        context_managers = self._prepare_patches_list(tested_object)

        # python 3 not support nested
        with nested(*context_managers):
            assert tested_object.is_prerequisite_fulfilled()

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        self._init_validation_object(tested_object, scenario_params)

        context_managers = self._prepare_patches_list(tested_object)

        # python 3 not support nested
        with nested(*context_managers):
            assert tested_object.is_validation_passed()

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        self._init_validation_object(tested_object, scenario_params)

        context_managers = self._prepare_patches_list(tested_object)

        # python 3 not support nested
        with nested(*context_managers):
            assert tested_object.is_validation_passed() is False

        if scenario_params.failed_msg is not None:
            assert self.normalize_unicode_repr(scenario_params.failed_msg) in \
                   self.normalize_unicode_repr(tested_object._failed_msg)

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        self._init_validation_object(tested_object, scenario_params)

        context_managers = self._prepare_patches_list(tested_object)

        # python 3 not support nested
        with nested(*context_managers):
            with pytest.raises(UnExpectedSystemOutput):
                tested_object.is_validation_passed()

    @pytest.mark.parametrize("scenario_params", scenario_no_suitable_host)
    def test_scenario_no_suitable_host(self, scenario_params, tested_object):
        self._init_validation_object(tested_object, scenario_params)

        context_managers = self._prepare_patches_list(tested_object)

        # python 3 not support nested
        with nested(*context_managers):
            with pytest.raises(NoSuitableHostWasFoundForRoles):
                tested_object.is_validation_passed()

    @pytest.mark.parametrize("scenario_params", scenario_no_identical_values)
    def test_scenario_no_identical_values(self, scenario_params, tested_object):
        self._init_validation_object(tested_object, scenario_params)

        context_managers = self._prepare_patches_list(tested_object)

        # python 3 not support nested
        with nested(*context_managers):
            with pytest.raises(NonIdenticalValues):
                tested_object.is_validation_passed()

    def _init_validation_object(self, val_object, scenario_params=None):
        LazyDataLoader.my_data_db = {}
        self._init_operator_object(val_object, scenario_params)

    def normalize_unicode_repr(self, s):
        if type(s) is str:
            return re.sub(r"u'([^']*)'", r"'\1'", s)
        return s
