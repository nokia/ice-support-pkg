from __future__ import absolute_import
from tests.pytest.tools.versions_alignment import patch, Mock

from flows_of_sys_operations.sys_data_collector.log_collector.configuration_generator.scenarios.base_log_scenario import \
    CompositeLogGroup
from tests.pytest.pytest_tools.operator.test_operator import OperatorTestBase
from tools.global_enums import Objectives, Deployment_type


class TestCompositeLogGroup(OperatorTestBase):
    tested_type = CompositeLogGroup

    def test_get_log_path_per_roles(self, tested_object):
        with patch("flows_of_sys_operations.sys_data_collector.log_collector.configuration_generator.scenarios."
                   "base_log_scenario.gs.get_deployment_type") as get_deployment_type_mock:
            get_deployment_type_mock.return_value = Deployment_type.CBIS
            tested_object.get_logs_of_interest = Mock()
            tested_object.get_logs_of_interest.return_value = {
                Objectives.COMPUTES: ["/path/1", "/path/2"]
            }
            tested_object.get_sub_groups = Mock(return_value=[])

            assert tested_object.get_log_path_per_roles() == {
                Objectives.COMPUTES: list({"/path/1", "/path/2"}),
                Objectives.CONTROLLERS: [],
                Objectives.HYP: [],
                Objectives.UC: [],
                Objectives.STORAGE: []
            }

    def test_clean_duplicate(self, tested_object):
        logs_dict = {
            Objectives.ALL_HOSTS: ["/all-nodes/path/to/log", "/2/path"],
            Objectives.COMPUTES: ["/2/path", "/3/path", "/2/path", "/3/path"],
            Objectives.OVS_COMPUTES: ["/3/path"]
        }

        expected_res = {
            Objectives.ALL_HOSTS: sorted(["/all-nodes/path/to/log", "/2/path"]),
            Objectives.COMPUTES: sorted(["/3/path"]),
            Objectives.OVS_COMPUTES: []
        }

        tested_object._clean_duplicate(logs_dict)

        for key in list(logs_dict.keys()):
            logs_dict[key] = sorted(logs_dict[key])

        assert logs_dict == expected_res
