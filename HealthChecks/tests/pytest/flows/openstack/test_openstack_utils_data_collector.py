from __future__ import absolute_import
import copy
import os

import pytest
from tests.pytest.tools.versions_alignment import Mock

from flows.OpenStack.openstack_utils_data_collector import OpenstackUtilsDataCollector
from tests.pytest.pytest_tools.operator.test_data_collector import DataCollectorTestBase, DataCollectorScenarioParams
from tests.pytest.pytest_tools.operator.test_operator import CmdOutput
from tools import sys_parameters
from tools.global_enums import Version

host_name_by_ip_mysql_passed = """+-------------+-----------------------------------------------------+
| ip_address  | host                                                |
+-------------+-----------------------------------------------------+
| 172.17.2.14 | overcloud-controller-191-0.localdomain              |
| 172.17.2.28 | overcloud-ovscompute-191-0.localdomain              |
+-------------+-----------------------------------------------------+"""
host_name_by_ip_mysql_tab_delimiter = """+-------------+-----------------------------------------------------+
\tip_address\thost
+-------------+-----------------------------------------------------+
\t172.17.2.14\tovercloud-controller-191-0.localdomain
\t172.17.2.28\tovercloud-ovscompute-191-0.localdomain
+-------------+-----------------------------------------------------+"""


class TestOpenstackUtilsDataCollector(DataCollectorTestBase):  # TODO: Test also scenario failed
    tested_type = OpenstackUtilsDataCollector
    scenarios = [
        DataCollectorScenarioParams(
            scenario_title="basic scenario",
            version=Version.V19A,
            cmd_input_output_dict={
                "sudo /bin/hiera -c /etc/puppet/hiera.yaml mysql::server::root_password": CmdOutput(out="xxx"),
                "sudo mysql -u root -pxxx -e '{mysql_command}'": CmdOutput(host_name_by_ip_mysql_passed)
            },
            scenario_res=[{"ip_address": "172.17.2.14", "host": "overcloud-controller-191-0.localdomain"},
                          {"ip_address": "172.17.2.28", "host": "overcloud-ovscompute-191-0.localdomain"}],
        ),
        DataCollectorScenarioParams(
            scenario_title="tab delimiter scenario",
            version=Version.V19A,
            cmd_input_output_dict={
                "sudo /bin/hiera -c /etc/puppet/hiera.yaml mysql::server::root_password": CmdOutput(out="xxx"),
                "sudo mysql -u root -pxxx -e '{mysql_command}'": CmdOutput(host_name_by_ip_mysql_tab_delimiter)
            },
            scenario_res=[{"ip_address": "172.17.2.14", "host": "overcloud-controller-191-0.localdomain"},
                          {"ip_address": "172.17.2.28", "host": "overcloud-ovscompute-191-0.localdomain"}]
        )
    ]
    kwargs_list = [
        {"mysql_command": "use ovs_neutron; select ip_address, host from  ml2_vxlan_endpoints"}
    ]

    @pytest.mark.parametrize("password, version",
                             [('xxx', Version.V20), ('xxx', Version.V22), ('xxx', Version.V22_12), ('nil', Version.V20),
                              ('nil', Version.V22), ('nil', Version.V22_7)])
    def test_get_base_mariadb_cmd(self, password, version, tested_object):
        tested_object.get_output_from_run_cmd = Mock(return_value=password)
        sys_parameters.get_version = Mock()
        sys_parameters.get_version.return_value = version
        cmd = tested_object.get_base_mariadb_cmd()
        if password == 'nil':
            assert (cmd == "sudo mysql -u root -e ")
        elif version >= Version.V22:
            assert cmd == "sudo podman exec -it $(sudo podman ps -f name=galera-bundle -q) " \
                          "mysql -u root -p{} -e ".format(password)
        else:
            assert cmd == "sudo mysql -u root -p{} -e ".format(password)

    @pytest.mark.parametrize("kwargs", kwargs_list)
    @pytest.mark.parametrize("scenario_params", scenarios)
    def test_collect_data(self, scenario_params, kwargs, tested_object):
        self._format_cmd_keys(kwargs, scenario_params)
        DataCollectorTestBase.test_collect_data(self, scenario_params, tested_object, **kwargs)

    def _format_cmd_keys(self, kwargs, scenario_params):
        cmd_dict_copy = copy.deepcopy(scenario_params.cmd_input_output_dict)
        for key, val in list(cmd_dict_copy.items()):
            scenario_params.cmd_input_output_dict[key.format(mysql_command=kwargs["mysql_command"])] = \
                scenario_params.cmd_input_output_dict.pop(key)
