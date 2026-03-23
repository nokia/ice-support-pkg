from __future__ import absolute_import
import copy
from collections import OrderedDict

import pytest
from tests.pytest.tools.versions_alignment import Mock, MagicMock

from flows.Blueprint.BlueprintDataCollectors import ProcessorCurrentFrequency, ProcessorType
from flows.Blueprint.BlueprintValidations import ValidateHWBlueprint, ValidateOsDiskMatch
from flows.Blueprint.DiskBlueprintDataCollectors import DiskType
from tests.pytest.pytest_tools.operator.old_style.test_inner_funcs import OperatorTestInnerFunctions, InnerFuncsScenarioParams
from tests.pytest.pytest_tools.operator.test_validation_base import ValidationTestBase, ValidationScenarioParams
from tools.global_enums import Objectives
from tests.pytest.flows.blueprint.inputs.get_scenarios import get_os_disk_data_scenario, get_os_disk_data_scenario_nodes


class TestValidateHWBlueprint(ValidationTestBase):
    tested_type = ValidateHWBlueprint

    blueprint_inventory_mock = Mock()
    blueprint_inventory_mock.return_value.build_actual_blueprint_name.return_value = "airframe_rm20_ICK_cx6"

    tested_object_mock_dict = {
        "get_collected_data": Mock(return_value={
            "processor@frequency_in_mhz": {"controller-0": {"id_1": 500, "id_2": 100}},
            "processor@type": {"controller-0": {"id_1": "type1", "id_2": "type2"}},
            "disk@type": {"compute-0": {"id_1": "SSD"}}
        }),
        "get_expected_blueprint": Mock(return_value={"controllers": {"processor": [{"frequency_in_mhz": 500},
                                                                                   {"frequency_in_mhz": 100}]}}),
        "_get_representatives_values": Mock(return_value={
            "controllers": {
                "processor": {"frequency_in_mhz": {"is_uniform": True, "value": {"id_1": 500, "id_2": 100}},
                              "type": {"is_uniform": True, "value": {"id_1": "type1", "id_2": "type2"}}
                              }
            },
            "computes": {
                "disk": {"type": {"is_uniform": True, "value": {"id_1": "SSD"}}}
            }
        }),
        "_get_knowledge_dict_by_field": Mock(return_value={})
    }

    tested_object_mock_dict_passed_scenario = copy.deepcopy(tested_object_mock_dict)
    tested_object_mock_dict_passed_scenario["_compare_blueprint"] = Mock(return_value=([], {}))

    scenario_passed = [
        ValidationScenarioParams(scenario_title="scenario passed, no failed topics",
                                 library_mocks_dict={"BlueprintInventory": blueprint_inventory_mock},
                                 tested_object_mock_dict=tested_object_mock_dict_passed_scenario)
    ]

    tested_object_mock_dict_failed_scenario = copy.deepcopy(tested_object_mock_dict)
    tested_object_mock_dict_failed_scenario["_compare_blueprint"] = Mock(return_value=(["computes: numa"], {}))

    scenario_failed = [
        ValidationScenarioParams(scenario_title="scenario failed, failed topics",
                                 library_mocks_dict={"BlueprintInventory": blueprint_inventory_mock},
                                 tested_object_mock_dict=tested_object_mock_dict_failed_scenario)
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


def create_scenarios_for_get_collected_data():
    scenarios = []

    expected_res = OrderedDict()
    expected_res["processor@frequency_in_mhz"] = {"id_1": 500, "id_2": 100}
    expected_res["processor@type"] = {"id_1": "type1", "id_2": "type2"}
    expected_res["disk@type"] = {"id_1": "SSD"}

    scenarios.append(InnerFuncsScenarioParams(
        scenario_title="basic scenario",
        function_res=expected_res,
        data_collector_dict={
            ProcessorCurrentFrequency: ("processor@frequency_in_mhz", {"id_1": 500, "id_2": 100}),
            ProcessorType: ("processor@type", {"id_1": "type1", "id_2": "type2"}),
            DiskType: ("disk@type", {"id_1": "SSD"})
        }))

    scenarios.append(InnerFuncsScenarioParams(
        scenario_title="Assertion error no unique name",
        exception_raised=AssertionError,
        data_collector_dict={
            ProcessorCurrentFrequency: ("processor@frequency_in_mhz", {"id_1": 500, "id_2": 100}),
            ProcessorType: ("processor@frequency_in_mhz", {"id_1": "type1", "id_2": "type2"}),
            DiskType: ("disk@type", {"id_1": "SSD"})
        }
    ))

    return scenarios


def create_scenarios_for_get_expected_blueprint():
    blueprint_json = {
        "airframe_rm20_ICK_cx6": {"ALL_VERSIONS": {
            "computes": {
                "network_interface": [
                    {
                        "model": "ConnectX-6 Lx"
                    }
                ]
            }
        }},
        "hp_g10_CLK_cx5": {"ALL_VERSIONS": {
            "computes": {
                "network_interface": [
                    {
                        "model": "ConnectX-5 Lx"
                    }
                ]
            }
        }}
    }
    json_load_list = [blueprint_json,
                      {"ALL_VERSIONS": {"computes": {"network_interface": [{"model": "customer: ConnectX-5 Lx"}]}}}]

    return [
        InnerFuncsScenarioParams(scenario_title="only in customers db",
                                 function_args="airframe_rm20_ICK_cx6",
                                 function_res={"computes": {"network_interface": [{"model": "ConnectX-6 Lx"}]}},
                                 library_mocks_dict={
                                     # MagicMock to have also open __enter__ and __exit__ (for 'with' statement)
                                     "open": MagicMock(),
                                     "json.load": Mock(side_effect=json_load_list),
                                     "os.listdir": Mock(return_value=[
                                         "new_airframe_rm20_ICK_cx6.json", "hp_g10_CLK_cx5.json"])
                                 }),
        InnerFuncsScenarioParams(scenario_title="in customers db and json, tests if take from customers",
                                 function_args="hp_g10_CLK_cx5",
                                 function_res={
                                     "computes": {"network_interface": [{"model": "customer: ConnectX-5 Lx"}]}},
                                 library_mocks_dict={
                                     "open": MagicMock(),
                                     "json.load": Mock(side_effect=json_load_list),
                                     "os.listdir": Mock(return_value=[
                                         "new_airframe_rm20_ICK_cx6.json", "hp_g10_CLK_cx5.json"])
                                 }),
        InnerFuncsScenarioParams(scenario_title="unknown blueprint name",
                                 function_args="unknown",
                                 function_res={},
                                 library_mocks_dict={
                                     "open": MagicMock(),
                                     "json.load": Mock(side_effect=json_load_list),
                                     "os.listdir": Mock(return_value=[
                                         "new_airframe_rm20_ICK_cx6.json", "hp_g10_CLK_cx5.json"])
                                 })
    ]


class TestValidateHWBlueprintInnerFunctions(OperatorTestInnerFunctions):
    tested_type = ValidateHWBlueprint

    @pytest.mark.parametrize("scenario", create_scenarios_for_get_collected_data())
    def test_get_collected_data(self, scenario, tested_object):
        tested_object.get_list_of_data_collectors = Mock()
        tested_object.any_passed_data_collector = True
        tested_object.get_list_of_data_collectors.return_value = [
            ProcessorCurrentFrequency,
            ProcessorType,
            DiskType
        ]

        self.run_test_on_inner_func(tested_object.get_collected_data, tested_object, scenario)

    @pytest.mark.parametrize("scenario", create_scenarios_for_get_expected_blueprint())
    def test_get_expected_blueprint(self, scenario, tested_object):
        self.run_test_on_inner_func(tested_object.get_expected_blueprint, tested_object, scenario)

    values_per_host = {"compute-0": {"processor@frequency_in_mhz": {"id_1": 500, "id_2": 100}},
                       "controller-0": {"disk@type": {"id_1": "SSD"}},
                       "controller-1": {"id_1": "SSD"}}

    @pytest.mark.parametrize("scenario", [
        InnerFuncsScenarioParams(scenario_title="res with more than 1",
                                 function_args=(values_per_host, Objectives.CONTROLLERS),
                                 function_res={
                                     "controller-0": {"disk@type": {"id_1": "SSD"}}, "controller-1": {"id_1": "SSD"}}),
        InnerFuncsScenarioParams(scenario_title="empty res",
                                 function_args=(values_per_host, Objectives.STORAGE),
                                 function_res={}),
        InnerFuncsScenarioParams(scenario_title="1 in res",
                                 function_args=(values_per_host, Objectives.COMPUTES),
                                 function_res={"compute-0": {"processor@frequency_in_mhz": {"id_1": 500, "id_2": 100}}})
    ])
    def test_get_values_per_host_by_role(self, scenario, tested_object):
        get_host_executor_factory_mock = Mock()
        # Create a mock that return a mock with method get_host_executor_by_host_name,
        # and add a return value to this method
        get_host_executor_factory_mock.return_value.get_host_executor_by_host_name = Mock(
            side_effect=self._get_host_executor_by_host_name_side_effect)
        # Init the library mocks of scenario her because it's same for all scenarios.
        scenario.library_mocks_dict = {"gs.get_host_executor_factory": get_host_executor_factory_mock}
        self.run_test_on_inner_func(tested_object.get_values_per_host_by_role, tested_object, scenario)

    @pytest.mark.parametrize("scenario", [
        InnerFuncsScenarioParams(scenario_title="basic passed", function_args="disk@type", function_res=("type", "disk")),
        InnerFuncsScenarioParams(scenario_title="passed with numbers in name", function_args="processor_1@frequency_in_mhz",
                                 function_res=("frequency_in_mhz", "processor_1")),
        InnerFuncsScenarioParams(scenario_title="assertion error no topic", function_args="@frequency_in_mhz",
                                 exception_raised=AssertionError),
        InnerFuncsScenarioParams(scenario_title="assertion error no name", function_args="processor@",
                                 exception_raised=AssertionError),
        InnerFuncsScenarioParams(scenario_title="assertion error no @", function_args="processor$frequency_in_mhz",
                                 exception_raised=AssertionError)
    ])
    def test_get_topic_and_name_from_objective_name(self, scenario, tested_object):
        self.run_test_on_inner_func(tested_object.get_topic_and_name_from_objective_name, tested_object, scenario)

    def test_compare_blueprint(self, tested_object):
        get_host_executor_factory_mock = Mock()
        get_host_executor_factory_mock.return_value.get_host_executors_by_roles = Mock(return_value={})
        expected_blueprint = {
            u'controllers': {u'ipmi': {u'controller_manager_version ': u'', u'controller_manager_firmware': u''}},
            u'computes': {u'memory': [{u'size_in_mb': 262144, u'total_size_in_mb': 524288, u'type': u'DDR4'},
                                      {u'size_in_mb': 262144, u'total_size_in_mb': 524288, u'type': u'DDR5'}],
                          u'raid_controller': {u'product': u'Smart Array Gen9 Controllers', u'vendor': u'BOSS or HP'}},
            u'storages': {u'raid_controller': {u'product': u'Smart Array Gen10 Controllers', u'vendor': u'BOSS'}}}
        system_data = {
            'controllers': {'kernel': {'version': {'is_uniform': True, 'value': {1: u'3.10.0-957.27.2.el7.x86_64'}}}},
            'computes': OrderedDict([
                ('raid_controller', {'product': {'is_uniform': True,
                                                 'value': {u'raid': u'Smart Array Gen9 Controllers'}},
                                     'vendor': {'is_uniform': True,
                                                'value': {u'raid': u'BOSS'}}}),
                ('memory', {'type': {'is_uniform': True, 'value': {'PROC 2 DIMM 6': 'DDR5',
                                                                   'PROC 2 DIMM 1': 'DDR4'}},
                            'size_in_mb': {'is_uniform': True, 'value': {'PROC 2 DIMM 6': 262144,
                                                                         'PROC 2 DIMM 1': 262144}},
                            'total_size_in_mb': {'is_uniform': True, 'value': {'PROC 2 DIMM 6': 524288,
                                                                               'PROC 2 DIMM 1': 524288}}})]),
            'storages': {'raid_controller': {'product': {'is_uniform': True,
                                                         'value': {u'raid': u'Smart Array Gen9 Controllers'}}}}}

        expected_return_value = (['storages >> raid_controller >> raid >> product'],
                                 OrderedDict([
                                     ('controllers', OrderedDict([(u'ipmi', {
                                         'pairs_by_id': OrderedDict([('missing_item_0', {
                                             'expected blueprint': {u'controller_manager_version ': u'',
                                                                    u'controller_manager_firmware': u''},
                                             'system output': {}})]),
                                         'knowledge_data': {}}),
                                                                  ('kernel',
                                                                   {'pairs_by_id': {
                                                                       1: {'expected blueprint': {},
                                                                           'system output': {
                                                                               'version':
                                                                                   {'is equal': True,
                                                                                    'value':
                                                                                        u'3.10.0-957.27.2.el7.x86_64'}}}
                                                                   }, 'knowledge_data': {}})])),
                                     ('computes', OrderedDict([
                                         ('raid_controller',
                                          {'pairs_by_id': {u'raid': {'expected blueprint':
                                                                         {u'product': u'Smart Array Gen9 Controllers',
                                                                          u'vendor': u'BOSS or HP'},
                                                                     'system output':
                                                                         {'product':
                                                                              {'is equal': True,
                                                                               'value': u'Smart Array Gen9 Controllers'
                                                                               },
                                                                          'vendor':
                                                                              {'is equal': True, 'value': u'BOSS'}}}},
                                           'knowledge_data': {}}),
                                         ('memory', {'pairs_by_id':
                                                         {'PROC 2 DIMM 6': {'expected blueprint':
                                                                                {u'size_in_mb': 262144,
                                                                                 u'total_size_in_mb': 524288,
                                                                                 u'type': u'DDR5'},
                                                                            'system output': {'size_in_mb':
                                                                                                  {'is equal': True,
                                                                                                   'value': 262144},
                                                                                              'total_size_in_mb': {
                                                                                                  'is equal': True,
                                                                                                  'value': 524288},
                                                                                              'type': {'is equal': True,
                                                                                                       'value': 'DDR5'}}},
                                                          'PROC 2 DIMM 1': {'expected blueprint':
                                                                                {u'size_in_mb': 262144,
                                                                                 u'total_size_in_mb': 524288,
                                                                                 u'type': u'DDR4'},
                                                                            'system output':
                                                                                {'size_in_mb':
                                                                                     {'is equal': True,
                                                                                      'value': 262144},
                                                                                 'total_size_in_mb':
                                                                                     {'is equal': True,
                                                                                      'value': 524288},
                                                                                 'type': {'is equal': True,
                                                                                          'value': 'DDR4'}}}},
                                                     'knowledge_data': {}})])),
                                     ('storages', OrderedDict([
                                         ('raid_controller',
                                          {'pairs_by_id': {u'raid':
                                                               {'expected blueprint':
                                                                    {u'product': u'Smart Array Gen10 Controllers',
                                                                     u'vendor': u'BOSS'}, 'system output':
                                                                   {'product': {'is equal': False,
                                                                                'value': u'Smart Array Gen9 Controllers'
                                                                                }}}}, 'knowledge_data': {}})]))]))
        knowledge_dict = {
            u'disk': {
                u'size_in_mb': [{
                    u'blueprint_sub_names': [u'airframe'],
                    u'remark': u'disk example only',
                    u'roles': [u'storages', u'computes']
                }
                ]
            },
            u'network_interface': {
                u'vendor': []
            }
        }

        scenario = InnerFuncsScenarioParams(scenario_title="test compare blueprint",
                                            function_args=(expected_blueprint, system_data, knowledge_dict),
                                            function_res=expected_return_value,
                                            library_mocks_dict={
                                                "gs.get_host_executor_factory": get_host_executor_factory_mock})

        self.run_test_on_inner_func(tested_object._compare_blueprint, tested_object, scenario)

    def _get_host_executor_by_host_name_side_effect(self, hostname):
        res = Mock()
        if "controller" in hostname:
            res.roles = [Objectives.CONTROLLERS]
        if "compute" in hostname:
            res.roles = [Objectives.COMPUTES]

        return "", res


class TestValidateOsDiskMatch(ValidationTestBase):
    tested_type = ValidateOsDiskMatch

    scenarios, scenario_names = [], ['fi803', 'fi819', 'fi803-bad', 'fi819-bad']

    for scenario_name in scenario_names:
        scenario = get_os_disk_data_scenario(scenario_name)
        node_names = get_os_disk_data_scenario_nodes(scenario_name)

        scenarios.append({"get_collected_data": Mock(return_value=scenario),
                          "get_node_names_from_system": Mock(return_value=node_names),
                          })

    scenario_passed = [
        ValidationScenarioParams(scenario_title="NCS - single - same disk type/size",
                                 tested_object_mock_dict=scenarios[0]),
        ValidationScenarioParams(scenario_title="CBIS - single/raid - same disk type/size",
                                 tested_object_mock_dict=scenarios[1]),
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="NCS - single - storage-1 wrong type",
                                 tested_object_mock_dict=scenarios[2]),
        ValidationScenarioParams(scenario_title="CBIS - raid - controller 1 wrong sizes",
                                 tested_object_mock_dict=scenarios[3]),
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)
