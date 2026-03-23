from __future__ import absolute_import
import pytest
import warnings

from tests.pytest.pytest_tools.operator.test_data_collector import DataCollectorTestBase, DataCollectorScenarioParams
from tests.pytest.tools.versions_alignment import Mock

from flows.OpenStack.Vms.openstack_resource.openstack_resource_validations import DuplicatePortRecords, \
    VmResourceAllocationOnRightCompute, ResourceAllocationsCheck, VolumeDeviceNotFound, CheckInstanceStatus, \
    GetAllBadVMSFromComputes, InterVMCommunicationPort, CheckStaleVolumes
from flows.OpenStack.openstack_utils_data_collector import OpenstackUtilsDataCollector
from tests.pytest.pytest_tools.operator.test_validation_base import ValidationTestBase, ValidationScenarioParams
from tools import user_params
from tools.global_enums import Version

from tests.pytest.pytest_tools.operator.test_operator import CmdOutput


class TestDuplicatePortRecords(ValidationTestBase):
    tested_type = DuplicatePortRecords

    user_params.vm = "6cab7036-a1fb-49eb-8cca-2618faeefe3a"

    scenario_passed = [
        ValidationScenarioParams(scenario_title="good scenario",
                                 data_collector_dict={
                                     OpenstackUtilsDataCollector: {
                                         "overcloud-controller-191-0": [
                                             {"port_id": "603af8f6-0de2-463f-9555-f63f925ca983", "status": "ACTIVE"}]}
                                 },
                                 library_mocks_dict={
                                     "VmsInfo.get_openstack_command_output": Mock(return_value=[
                                         {
                                             "Status": "DOWN",
                                             "Fixed IP Addresses": "ip_address='10.41.87.37', "
                                                                   "subnet_id='c27184ba-9bf6-49d8-8777-b09c954819a4'",
                                             "ID": "603af8f6-0de2-463f-9555-f63f925ca983",
                                             "MAC Address": "fa:16:3e:53:f7:44",
                                             "Name": "fi856-control-01-net-01"
                                         }
                                     ]
                                     )
                                 })
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="duplicate records in db",
                                 data_collector_dict={
                                     OpenstackUtilsDataCollector: {
                                         "overcloud-controller-191-0": [
                                             {"port_id": "603af8f6-0de2-463f-9555-f63f925ca983", "status": "ACTIVE"},
                                             {"port_id": "603af8f6-0de2-463f-9555-f63f925ca983", "status": "INACTIVE"}
                                         ]}
                                 },
                                 library_mocks_dict={
                                     "VmsInfo.get_openstack_command_output": Mock(return_value=[
                                         {
                                             "Status": "DOWN",
                                             "Fixed IP Addresses": "ip_address='10.41.87.37', "
                                                                   "subnet_id='c27184ba-9bf6-49d8-8777-b09c954819a4'",
                                             "ID": "603af8f6-0de2-463f-9555-f63f925ca983",
                                             "MAC Address": "fa:16:3e:53:f7:44",
                                             "Name": "fi856-control-01-net-01"
                                         }
                                     ]
                                     )
                                 })]

    scenario_unexpected_system_output = [
        ValidationScenarioParams(scenario_title="no id",
                                 library_mocks_dict={
                                     "VmsInfo.get_openstack_command_output": Mock(return_value=[{"Status": "DOWN"}])
                                 })
    ]

    scenario_no_suitable_host = [
        ValidationScenarioParams(scenario_title="no suitable host scenario",
                                 data_collector_dict={OpenstackUtilsDataCollector: {}},
                                 library_mocks_dict={
                                     "VmsInfo.get_openstack_command_output": Mock(return_value=[
                                         {
                                             "Status": "DOWN",
                                             "Fixed IP Addresses": "ip_address='10.41.87.37', "
                                                                   "subnet_id='c27184ba-9bf6-49d8-8777-b09c954819a4'",
                                             "ID": "603af8f6-0de2-463f-9555-f63f925ca983",
                                             "MAC Address": "fa:16:3e:53:f7:44",
                                             "Name": "fi856-control-01-net-01"
                                         }
                                     ]
                                     )
                                 })
    ]

    def _init_mocks(self, tested_object):
        tested_object.system_utils.get_stackrc_file_path = Mock()
        tested_object.system_utils.get_stackrc_file_path.return_value = '/home/stack/stackrc'

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_unexpected_system_output(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_no_suitable_host)
    def test_scenario_no_suitable_host(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_no_suitable_host(self, scenario_params, tested_object)


def get_openstack_command_output_side_effect(cmd, *args, **kwargs):
    if cmd == "openstack resource provider list":
        return [
            {
                "generation": 7,
                "uuid": "fe3745d6-5c41-4cbc-9899-50d1e03b393d",
                "name": "overcloud-ovscompute-fi856-1.localdomain"
            },
            {
                "generation": 7,
                "uuid": "22cd2f5a-f797-4fe7-8d94-71e987976170",
                "name": "overcloud-ovscompute-fi856-3.localdomain"
            }
        ]

    if cmd == "openstack resource provider allocation show {}".format(user_params.vm):
        return [
            {
                "generation": 7,
                "resource_provider": "22cd2f5a-f797-4fe7-8d94-71e987976170",
                "resources": {
                    "MEMORY_MB": 10240,
                    "VCPU": 10,
                    "DISK_GB": 450
                }
            }
        ]


def get_openstack_command_output_unexpected_side_effect(cmd, *args, **kwargs):
    if cmd == "openstack resource provider list":
        return [
            {
                "generation": 7,
                "uuid": "fe3745d6-5c41-4cbc-9899-50d1e03b393d",
                "name": "overcloud-ovscompute-fi856-1.localdomain"
            }
        ]

    if cmd == "openstack resource provider allocation show {}".format(user_params.vm):
        return [
            {
                "generation": 7,
                "resource_provider": "22cd2f5a-f797-4fe7-8d94-71e987976170",
                "resources": {
                    "MEMORY_MB": 10240,
                    "VCPU": 10,
                    "DISK_GB": 450
                }
            }
        ]


def _run_data_collector_side_effects(data_collector_class, **kwargs):
    if 'use nova_api;  select * from resource_providers' in kwargs['mysql_command']:
        return {
            "overcloud-controller-191-0": [
                {'created_at': '2023-07-19 00:06:31', 'id': '2', 'uuid': 'fe3745d6-5c41-4cbc-9899-50d1e03b393d'}]}

    if kwargs['mysql_command'] == 'use nova_api;  select consumer_id, resource_provider_id from allocations':
        return {
            "overcloud-controller-191-0": [
                {'resource_provider_id': '2', 'consumer_id': '0ebe85fd-4cd3-4b07-912f-accc10a2cb52'},
                {'resource_provider_id': '2','consumer_id': 'f83c8642-4096-4245-93f3-74b1678b1334'}]}

    if kwargs['mysql_command'] == 'use nova_api;  select * from allocations where resource_provider_id=2 ' \
                                  'and consumer_id="{}"'.format(user_params.vm):
        return {
            "overcloud-controller-191-0": [
                {'used': '10', 'resource_provider_id': '2', 'created_at': '2023-07-19 01:13:25', 'updated_at': 'NULL',
                 'consumer_id': '0ebe85fd-4cd3-4b07-912f-accc10a2cb52', u'resource_class_id': u'0', u'id': u'14'}]}


def _run_data_collector_failed_side_effects(data_collector_class, **kwargs):
    if 'use nova_api;  select * from resource_providers' in kwargs['mysql_command']:
        return {
            "overcloud-controller-191-0": [
                {'created_at': '2023-07-19 00:06:31', 'id': '2', 'uuid': 'fe3745d6-5c41-4cbc-9899-50d1e03b393d'}]}

    if kwargs['mysql_command'] == 'use nova_api;  select * from allocations where resource_provider_id=2':
        return {
            "overcloud-controller-191-0": [
                {'used': '10', 'resource_provider_id': '2', 'created_at': '2023-07-19 01:13:25', 'updated_at': 'NULL',
                 'consumer_id': '0ebe85fd-4cd3-4b07-912f-accc10a2cb52', u'resource_class_id': u'0', u'id': u'14'},
                {'used': '10', 'resource_provider_id': '2', 'created_at': '2023-07-19 01:13:28',
                 'updated_at': 'NULL', 'consumer_id': 'f83c8642-4096-4245-93f3-74b1678b1334',
                 'resource_class_id': '0', 'id': '17'}]}

    if kwargs['mysql_command'] == 'use nova_api;  select * from allocations where resource_provider_id=2 ' \
                                  'and consumer_id="{}"'.format(user_params.vm):
        return {
            "overcloud-controller-191-0": []}


class TestVmResourceAllocationOnRightCompute(ValidationTestBase):
    tested_type = VmResourceAllocationOnRightCompute

    user_params.vm = "6cab7036-a1fb-49eb-8cca-2618faeefe3a"

    scenario_passed = [
        ValidationScenarioParams(scenario_title="basic",
                                 tested_object_mock_dict={
                                     "run_data_collector": Mock(side_effect=_run_data_collector_side_effects)
                                 },
                                 version=Version.V19A,
                                 library_mocks_dict={
                                     "VmsInfo.get_openstack_command_output": Mock(
                                         side_effect=get_openstack_command_output_side_effect
                                     )
                                 })
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="vm is not running on provider compute",
                                 tested_object_mock_dict={
                                     "run_data_collector": Mock(side_effect=_run_data_collector_failed_side_effects)
                                 },
                                 version=Version.V19A,
                                 library_mocks_dict={
                                     "VmsInfo.get_openstack_command_output": Mock(
                                         side_effect=get_openstack_command_output_side_effect
                                     )
                                 })
    ]

    scenario_unexpected_system_output = [
        ValidationScenarioParams(scenario_title="empty vm provider list",
                                 version=Version.V19A,
                                 library_mocks_dict={
                                     "VmsInfo.get_openstack_command_output": Mock(
                                         return_value=[]
                                     )
                                 }),
        ValidationScenarioParams(scenario_title="No match to vm provider",
                                 version=Version.V19A,
                                 library_mocks_dict={
                                     "VmsInfo.get_openstack_command_output": Mock(
                                         side_effect=get_openstack_command_output_unexpected_side_effect)
                                 })
    ]

    scenario_no_suitable_host = [
        ValidationScenarioParams(scenario_title="no suitable host scenario",
                                 version=Version.V19A,
                                 data_collector_dict={OpenstackUtilsDataCollector: {}},
                                 library_mocks_dict={"VmsInfo.get_openstack_command_output": Mock(
                                     side_effect=get_openstack_command_output_side_effect
                                    )}),
        ValidationScenarioParams(scenario_title="no suitable host scenario with get_provider_id_from_uuid",
                                 version=Version.V19A,
                                 tested_object_mock_dict={"get_provider_id_from_uuid": Mock(return_value="compute_id")},
                                 data_collector_dict={OpenstackUtilsDataCollector: {}},
                                 library_mocks_dict={"VmsInfo.get_openstack_command_output": Mock(
                                   side_effect=get_openstack_command_output_side_effect
                                    )})]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_unexpected_system_output(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_no_suitable_host)
    def test_scenario_no_suitable_host(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_no_suitable_host(self, scenario_params, tested_object)


class TestResourceAllocationsCheck(ValidationTestBase):
    tested_type = ResourceAllocationsCheck

    nova_list = """+---------------+-----------------+----------------------------------------+
| ID                                   | Name                                 | Host     |
+--------------------------------------+--------------------------------------+--------------------+
| 0ebe85fd-4cd3-4b07-912f-accc10a2cb52 | bcmt-01-control-01      | overcloud-ovscompute-fi856-1.localdomain    |
| f83c8642-4096-4245-93f3-74b1678b1334 | bcmt-01-control-02      | {}.localdomain    |
| 358aed81-dc49-49b4-bf36-cdbff9725c30 | bcmt-01-control-03      | {}.localdomain    |
| 5e1f0b13-bae5-4c67-a540-cd283955b865 | bcmt-01-edge-01         | overcloud-ovscompute-cbis22-0.localdomain   |
| e37da0da-4f75-4d5e-bc22-3a048ffff1d2 | bcmt-01-worker-01       | overcloud-ovscompute-cbis22-1.localdomain   |
+---------------+-----------------+----------------------------------------+"""

    scenario_passed = [
        ValidationScenarioParams(scenario_title="basic",
                                 version=Version.V19A,
                                 library_mocks_dict={
                                     "VmsInfo.get_openstack_command_output": Mock(
                                         side_effect=get_openstack_command_output_side_effect),
                                     "VmsInfo.run_command_on_selected_host": Mock(
                                         return_value=nova_list.format("overcloud-ovscompute-fi856-1",
                                                                       "overcloud-ovscompute-cbis22-0"))
                                 },
                                 tested_object_mock_dict={
                                     "get_host_name": Mock(return_value="overcloud-ovscompute-fi856-1"),
                                     "run_data_collector": Mock(side_effect=_run_data_collector_side_effects)
                                 }),
        ValidationScenarioParams(scenario_title="compute is not a provider",
                                 version=Version.V19A,
                                 library_mocks_dict={
                                     "VmsInfo.get_openstack_command_output": Mock(
                                         side_effect=get_openstack_command_output_side_effect)
                                 },
                                 tested_object_mock_dict={
                                     "get_host_name": Mock(return_value="overcloud-ovscompute-fi856-4")
                                 })
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="in nova list, not in db",
                                 version=Version.V19A,
                                 library_mocks_dict={
                                     "VmsInfo.get_openstack_command_output": Mock(
                                         side_effect=get_openstack_command_output_side_effect),
                                     "VmsInfo.run_command_on_selected_host": Mock(
                                         return_value=nova_list.format("overcloud-ovscompute-fi856-1",
                                                                       "overcloud-ovscompute-fi856-1"))
                                 },
                                 tested_object_mock_dict={
                                     "get_host_name": Mock(return_value="overcloud-ovscompute-fi856-1"),
                                     "run_data_collector": Mock(side_effect=_run_data_collector_side_effects)
                                 }),
        ValidationScenarioParams(scenario_title="in db, not in nova list",
                                 version=Version.V19A,
                                 library_mocks_dict={
                                     "VmsInfo.get_openstack_command_output": Mock(
                                         side_effect=get_openstack_command_output_side_effect),
                                     "VmsInfo.run_command_on_selected_host": Mock(
                                         return_value=nova_list.format("overcloud-ovscompute-cbis22-0",
                                                                       "overcloud-ovscompute-cbis22-0"))
                                 },
                                 tested_object_mock_dict={
                                     "get_host_name": Mock(return_value="overcloud-ovscompute-fi856-1"),
                                     "run_data_collector": Mock(side_effect=_run_data_collector_side_effects)
                                 })
    ]

    scenario_no_suitable_host = [
        ValidationScenarioParams(scenario_title="no suitable host scenario",
                                 version=Version.V19A,
                                 data_collector_dict={OpenstackUtilsDataCollector: {}},
                                 library_mocks_dict={"VmsInfo.get_openstack_command_output": Mock(
                                     side_effect=get_openstack_command_output_side_effect
                                 )},
                                 tested_object_mock_dict={
                                     "get_host_name": Mock(return_value="overcloud-ovscompute-fi856-1")}),
        ValidationScenarioParams(scenario_title="no suitable host scenario with get_provider_id_from_uuid",
                                 version=Version.V19A,
                                 tested_object_mock_dict={
                                     "get_provider_id_from_uuid": Mock(return_value="compute_id"),
                                     "get_host_name": Mock(return_value="overcloud-ovscompute-fi856-1")},
                                 data_collector_dict={OpenstackUtilsDataCollector: {}},
                                 library_mocks_dict={"VmsInfo.get_openstack_command_output": Mock(
                                     side_effect=get_openstack_command_output_side_effect
                                 )})]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_no_suitable_host)
    def test_scenario_no_suitable_host(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_no_suitable_host(self, scenario_params, tested_object)



class TestVolumeDeviceNotFound(ValidationTestBase):

    tested_type = VolumeDeviceNotFound
    user_params.vm = "b7875927-cd34-47dd-bfba-45f3ad6c0b9e"
    mysql_password = "sudo /bin/hiera -c /etc/puppet/hiera.yaml mysql::server::root_password"

    command = 'SELECT CASE WHEN COUNT(*) > 1 THEN "False" ELSE "True" END AS result FROM cinder.volume_attachment WHERE attach_status = "attached" AND instance_uuid = "{}" GROUP BY instance_uuid, mountpoint;'.format(user_params.vm)

    maria_db_cmd = "sudo mysql -uroot --password={password} -e '{cmd}'".format(password="password", cmd=command)

    scenario_passed = [
        ValidationScenarioParams(scenario_title="Passed",
                                 cmd_input_output_dict={
                                     mysql_password: CmdOutput("password"),
                                     maria_db_cmd: CmdOutput("True")
                                 }
                                 )]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="Failed",
                                 cmd_input_output_dict={
                                     mysql_password: CmdOutput("password"),
                                     maria_db_cmd: CmdOutput("False")

                                 }
                                 )]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestGetAllBadVMSFromComputes(DataCollectorTestBase):
    tested_type = GetAllBadVMSFromComputes
    out = """
        28    instance-00000052              running
        """

    scenarios = [
        DataCollectorScenarioParams("Get virsh names of inactive instances from all compute", {"sudo virsh list --all | grep {virsh_name}": CmdOutput(out)},
                                    scenario_res=True),

    ]

    @pytest.mark.parametrize("scenario_params", scenarios)
    def test_collect_data(self, scenario_params, tested_object, **kwargs):
        self._init_data_collector_object(tested_object, scenario_params)


class TestCheckInstanceStatus(ValidationTestBase):
    tested_type = CheckInstanceStatus

    scenario_passed = [
        ValidationScenarioParams(scenario_title="When all VM is in 'running' state in Openstack",
                                 data_collector_dict={
                                     GetAllBadVMSFromComputes: {"overcloud-ovscompute-fi860-0": []}
                                 },
                                 library_mocks_dict={"VmsInfo.get_openstack_command_output": Mock(return_value=[
                                     {u'Status': u'ACTIVE', u'Name': u'ncs-20fp2-fi860b-2482-control-02',
                                      u'ID': u'45aee0fa-3ecb-4ee0-b700-f5b4e934ee61', u'Power State': u'Running',
                                      u'Host': u'overcloud-ovscompute-fi860-2.localdomain'},
                                     {u'Status': u'ACTIVE', u'Name': u'ncs-20fp2-fi860b-2482-control-03',
                                      u'ID': u'c2785d3c-e286-43fe-9587-652ecb8db6dd', u'Power State': u'Running',
                                      u'Host': u'overcloud-ovscompute-fi860-1.localdomain'}
                                 ]),
                                     "VmsInfo.get_vm_details": Mock(side_effect=[
                                         {'vm_name': u'ncs-20fp2-fi860b-2482-control-02',
                                          'virsh_name': u'instance-00000056'},
                                         {'vm_name': u'ncs-20fp2-fi860b-2482-control-03',
                                          'virsh_name': u'instance-00000055'}])
                                 }
                                 )
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="When one or more VM is NOT 'running' state in Openstack, "
                                                "but 'running' is compute host",
                                 data_collector_dict={GetAllBadVMSFromComputes: {
                                     "overcloud-ovscompute-fi860-0": [u' 2     instance-00000056              running\\n']
                                 }},

                                 library_mocks_dict={"VmsInfo.get_openstack_command_output": Mock(return_value=[
                                     {u'Status': u'NOSTATE', u'Name': u'ncs-20fp2-fi860b-2482-control-02', u'ID': u'45aee0fa-3ecb-4ee0-b700-f5b4e934ee61', u'Power State': u'Running',u'Host': u'overcloud-ovscompute-fi860-2.localdomain'},
                                     {u'Status': u'ERROR', u'Name': u'ncs-20fp2-fi860b-2482-control-03', u'ID': u'c2785d3c-e286-43fe-9587-652ecb8db6dd', u'Power State': u'Running',u'Host': u'overcloud-ovscompute-fi860-1.localdomain'}
                                 ]),
                                                     "VmsInfo.get_vm_details": Mock(side_effect=[
                                     {'vm_name': u'ncs-20fp2-fi860b-2482-control-02',
                                      'virsh_name': u'instance-00000056'},
                                     {'vm_name': u'ncs-20fp2-fi860b-2482-control-03',
                                      'virsh_name': u'instance-00000055'}])
                                     }

                                 )
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestInterVMCommunicationPort(ValidationTestBase):
    tested_type = InterVMCommunicationPort

    mysql_password_cmd = "sudo /bin/hiera -c /etc/puppet/hiera.yaml mysql::server::root_password"

    maria_db_cmd = (
        "sudo podman exec $(sudo podman ps -f name=galera-bundle -q)  "
        "mysql -uroot --password=password -e 'select port_id,status from ovs_neutron.ml2_port_bindings WHERE status = \"INACTIVE\";'"
    )

    scenario_passed = [
        ValidationScenarioParams(
            scenario_title="No inactive ports",
            cmd_input_output_dict={
                mysql_password_cmd: CmdOutput(out="password"),
                maria_db_cmd: CmdOutput(out="")
            },
            library_mocks_dict={
                "sys_parameters.get_version": Mock(return_value=Version.V24_7)
            }
        )
    ]

    scenario_failed = [
        ValidationScenarioParams(
            scenario_title="Inactive ports detected",
            cmd_input_output_dict={
                mysql_password_cmd: CmdOutput(out="password"),
                maria_db_cmd: CmdOutput(out="inactive_port_id_123")
            },
            library_mocks_dict={
                "sys_parameters.get_version": Mock(return_value=Version.V24_7)
            }
        )
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestCheckStaleVolumes(ValidationTestBase):
    tested_type = CheckStaleVolumes

    mysql_password_cmd = "sudo /bin/hiera -c /etc/puppet/hiera.yaml mysql::server::root_password"

    maria_db_cmd_podman = (
        'sudo podman exec $(sudo podman ps -f name=galera-bundle -q) mysql -uroot --password=password -e "select created_at,attach_status,volume_id from cinder.volume_attachment WHERE deleted=0 and attach_status!=\'attached\';\"'
    )

    scenario_passed = [
        ValidationScenarioParams(
            scenario_title="No stale volumes present",
            cmd_input_output_dict={
                mysql_password_cmd: CmdOutput(out="password"),
                maria_db_cmd_podman: CmdOutput(out="")
            },
            library_mocks_dict={
                "adapter.docker_or_podman": Mock(return_value="podman"),
            }
        )
    ]

    scenario_failed = [
        ValidationScenarioParams(
            scenario_title="Stale volumes detected",
            cmd_input_output_dict={
                mysql_password_cmd: CmdOutput(out="password"),
                maria_db_cmd_podman: CmdOutput(out="Detached")
            },
            library_mocks_dict={
                "adapter.docker_or_podman": Mock(return_value="podman"),
            }
        )
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)