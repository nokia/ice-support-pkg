from __future__ import absolute_import
import pytest

from tools import adapter
from tests.pytest.tools.versions_alignment import Mock, patch, decode_res

from HealthCheckCommon.operations import DataCollector
from tools import sys_parameters
from tools.adapter import OldNokiaAdapter, initialize_adapter_instance
from tools.global_enums import Deployment_type, Version


class CmdOutput:
    def __init__(self, out, return_code=0, err=""):
        self.out = out
        self.return_code = return_code
        self.err = err


class ScenarioParams(object):
    def __init__(self, scenario_title, cmd_input_output_dict=None, version=None, data_collector_dict=None,
                 library_mocks_dict=None, tested_object_mock_dict=None, additional_parameters_dict=None):
        self.scenario_title = scenario_title
        self.cmd_input_output_dict = cmd_input_output_dict
        self.version = version
        self.data_collector_dict = data_collector_dict
        self.library_mocks_dict = library_mocks_dict
        self.tested_object_mock_dict = tested_object_mock_dict
        self.additional_parameters_dict = additional_parameters_dict


class OperatorTestBase(object):
    tested_type = None

    @pytest.fixture
    def tested_object(self):
        assert self.tested_type, "Please init validation type."

        with patch("HealthCheckCommon.validator.adapter"):
            tested_obj = self.tested_type(Mock())
        return tested_obj

    def _init_operator_object(self, operator_object, scenario_params):
        self.cmd_to_output_dict = scenario_params.cmd_input_output_dict
        operator_object.run_cmd = Mock(side_effect=self._run_cmd_side_effects)

        self.data_collectors = scenario_params.data_collector_dict
        operator_object.run_data_collector = Mock(side_effect=self._run_data_collector_side_effects)

        if scenario_params.library_mocks_dict is not None:
            self.library_mocks_dict = scenario_params.library_mocks_dict
        else:
            self.library_mocks_dict = {}

        if scenario_params.tested_object_mock_dict is not None:
            self.tested_object_mock_dict = scenario_params.tested_object_mock_dict
        else:
            self.tested_object_mock_dict = {}

        self.version = scenario_params.version
        self.additional_parameters_dict = scenario_params.additional_parameters_dict

        self._init_base_mocks(operator_object)
        self._init_mocks(operator_object)

    def _run_cmd_side_effects(self, cmd, timeout=20,
                              hosts_cached_pool=None,
                              get_not_ascii=False, add_bash_timeout=False, trim_warnings=True):
        assert type(self.cmd_to_output_dict) is dict, "please init self.cmd_inputs"
        assert cmd in self.cmd_to_output_dict, "Please init all CMDs you want to use before running the test."

        res = self.cmd_to_output_dict[cmd]
        out, err = decode_res(res, get_not_ascii)
        return res.return_code, out, err

    def _host_executor_factory_execute_cmd_by_roles_side_effects(self, roles, cmd, timeout=30):
        assert type(self.cmd_to_output_dict) is dict, "please init self.cmd_inputs"
        assert cmd in self.cmd_to_output_dict, "Please init all CMDs you want to use before running the test."
        assert type(self.cmd_to_output_dict[cmd]) is dict, \
            "please init self.cmd_inputs[{}] with dict of {{host_name: res}}".format(cmd)
        result_dict = {}
        for host_name, res in list(self.cmd_to_output_dict[cmd].items()):
            result_dict[host_name] = {
                "out": res.out,
                "err": res.err,
                "exit_code": res.return_code,
                "ip": "172.31.0.21",
                "roles": roles
            }
        return result_dict

    def _run_data_collector_side_effects(self, data_collector_class, **kwargs):
        assert issubclass(data_collector_class, DataCollector), "The data collector type isn't correct"
        assert data_collector_class in list(self.data_collectors.keys()), \
            "Please init all DataCollectors you run in the validation with all their params."

        res = self.data_collectors[data_collector_class]

        return res

    def _init_mocks(self, tested_object):
        pass

    def _init_base_mocks(self, tested_object):
        initialize_adapter_instance(Deployment_type.CBIS, Version.V20)
        sys_parameters.get_host_executor_factory = Mock()
        sys_parameters.get_host_executor_factory().execute_cmd_by_roles = Mock(
            side_effect=self._host_executor_factory_execute_cmd_by_roles_side_effects)
        sys_parameters.get_host_executor_factory().run_command_on_first_host_from_selected_roles = Mock(
            side_effect=self._run_command_on_first_host_from_selected_roles_side_effect)
        tested_object._debug_pipes = Mock()
        tested_object._debug_pipes.return_value = ""

        sys_parameters.get_version = Mock()
        sys_parameters.get_version.return_value = self.version

        for tested_object_method, mock_object in list(self.tested_object_mock_dict.items()):
            setattr(tested_object, tested_object_method, mock_object)

    def _run_command_on_first_host_from_selected_roles_side_effect(self, cmd, roles, timeout=60):
        return self.cmd_to_output_dict[cmd].out

    def _prepare_patches_list(self, tested_object):
        """
        This function prepare a list of temporary mock objects,
        the mocks will be activated only in a nested with block
        :param tested_object: the object that is tested
        :return: list of patch objects
        """
        context_managers = []
        for object_module, mock_object in list(self.library_mocks_dict.items()):
            full_module = tested_object.__module__ + "." + object_module
            context_managers.append(patch(full_module, mock_object))

        return context_managers
