from __future__ import absolute_import

import json

from HealthCheckCommon.table_system_info import TableSystemInfo
from tests.pytest.tools.versions_alignment import nested

import pytest

from tests.pytest.pytest_tools.operator.test_validation_base import ValidationScenarioParams, ValidationTestBase


class InformatorValidatorScenarioParams(ValidationScenarioParams):
    def __init__(self, scenario_title, expected_system_info, cmd_input_output_dict=None, version=None,
                 data_collector_dict=None, library_mocks_dict=None, tested_object_mock_dict=None, failed_msg=None,
                 additional_parameters_dict=None, table_system_info=TableSystemInfo()):
        super(InformatorValidatorScenarioParams, self).__init__(scenario_title, cmd_input_output_dict, version,
                                                                data_collector_dict, library_mocks_dict,
                                                                tested_object_mock_dict, failed_msg,
                                                                additional_parameters_dict)
        self.expected_system_info = expected_system_info
        self.table_system_info = table_system_info


class InformatorValidatorTestBase(ValidationTestBase):
    scenarios = []

    @pytest.mark.parametrize("scenario_params", scenarios)
    def test_is_validation_passed(self, scenario_params, tested_object):
        self._init_validation_object(tested_object, scenario_params)

        context_managers = self._prepare_patches_list(tested_object)

        # python 3 not support nested
        with nested(*context_managers):
            tested_object.is_validation_passed()

        assert self._conver_dict(self.normalize_unicode_repr(scenario_params.expected_system_info)) == \
               self._conver_dict(self.normalize_unicode_repr(tested_object._system_info))
        assert scenario_params.table_system_info.table == tested_object._table_system_info.table

    def _conver_dict(self, s):
        try:
            return json.loads(s)
        except:
            return s
