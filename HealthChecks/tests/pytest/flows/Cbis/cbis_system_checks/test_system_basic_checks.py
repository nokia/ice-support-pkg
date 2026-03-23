from __future__ import absolute_import
import warnings
import pytest
import os
from tests.pytest.tools.versions_alignment import Mock
import yaml

from flows.Cbis.cbis_system_checks.system_basic_checks import ClusterResourcesStatus, CheckStackStatus, \
    CheckNetworkAgentHostnameMismatch, CbisSystemCheckGnocchiCeilometer, OvercloudBackupCheck, \
    MySQLDirectoryNotLarge, RabbitMQDirectoryNotLarge, ValidateBMCPasswordValidAndSync, CheckDeploymentServerBlacklist, \
    VerifySymlinkForCACert, VerifyDefaultLibvirtNetwork, ValidateARPResponder, GetARPResponderFromHosts, RabbitMQErrorLogValidation, \
    RedisMasterRoleAvailability, RabbitMQMessagesLogValidation, CinderDefaultVolumeType
from tests.pytest.pytest_tools.operator.test_data_collector import DataCollectorTestBase, DataCollectorScenarioParams
from tests.pytest.pytest_tools.operator.test_operator import CmdOutput
from tests.pytest.pytest_tools.operator.test_operator import OperatorTestBase
from tests.pytest.pytest_tools.operator.test_validation_base import ValidationTestBase, ValidationScenarioParams
from tools.global_enums import Version


def path_join(*args):
    return '/'.join(args)


class TestClusterResourcesStatus(ValidationTestBase):
    tested_type = ClusterResourcesStatus

    validation_cmd = "sudo pcs status xml"
    current_dir_path = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(current_dir_path, 'inputs', 'pcs_status_xml.txt')
    with open(path, 'r') as file:
        out = file.read()

    failure = """<failure op_key="rabbitmq_monitor_10000" node="rabbitmq-bundle-1" exitstatus="not running" exitreason="" exitcode="7" call="32" status="complete" last-rc-change="Mon Apr  3 22:22:27 2023" queued="0" exec="0" interval="10000" task="monitor" />"""

    scenario_passed = [
        ValidationScenarioParams(scenario_title="All resources running",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(
                                     out=out.format(online='true', role_s='Started', role_m='Master', role_sl='Slave',
                                                    failed='false', managed='true', list_of_failures={""}))})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="There are offline nodes",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(
                                     out=out.format(online='false', role_s='Started', role_m='Master', role_sl='Slave',
                                                    failed='false', managed='true', list_of_failures={""}))}),
        ValidationScenarioParams(scenario_title="There are paused resources",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(
                                     out=out.format(online='true', role_s='Paused', role_m='Master', role_sl='Slave',
                                                    failed='false', managed='true', list_of_failures={""}))}),
        ValidationScenarioParams(scenario_title="There are resources in an Unknown state",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(
                                     out=out.format(online='true', role_s='Unknown', role_m='Master', role_sl='Slave',
                                                    failed='false', managed='true', list_of_failures={""}))}),
        ValidationScenarioParams(scenario_title="There are failed resources",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(
                                     out=out.format(online='true', role_s='Started', role_m='Master', role_sl='Slave',
                                                    failed='true', managed='true', list_of_failures={""}))}),
        ValidationScenarioParams(scenario_title="There are unmanaged resources",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(
                                     out=out.format(online='true', role_s='Started', role_m='Master', role_sl='Slave',
                                                    failed='false', managed='false', list_of_failures={""}))}),
        ValidationScenarioParams(scenario_title="There are failures",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(
                                     out=out.format(online='true', role_s='Started', role_m='Master', role_sl='Slave',
                                                    failed='false', managed='true', list_of_failures=failure))})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    def test_has_confluence(self, tested_object):
        # Override the func since this val doesn't have a confluence. 
        # pls do not copy it! it's only for old validations that do not have a confluence page.
        warnings.warn("No confluence page")


class TestCheckStackStatus(ValidationTestBase):
    tested_type = CheckStackStatus

    old_version_cmd = "source {}; timeout --kill-after=60 30 openstack stack list -f json".format('/home/stack/stackrc_locked')
    old_version_out = '''
        [
          {{
            "Stack Status": {},
            "Stack Name": "overcloud",
            "Updated Time": "2023-03-07T23:49:28Z",
            "Creation Time": "2021-03-05T11:00:32Z",
            "Project": "793b455acdbc48b9860fdfa17e496447",
            "ID": "188ee915-7c30-46fd-a3b0-f91a13806aa7"
          }}
        ]
    '''
    new_version_cmd = "openstack overcloud status"
    new_version_out = """
        +------------+-------------------+
        | Stack Name | Deployment Status |
        +------------+-------------------+
        | overcloud  |   {}  |
        +------------+-------------------+
        """
    new_version_out_no_stack = """
        +------------+-------------------+
        | Stack Name | Deployment Status |
        +------------+-------------------+
    """

    scenario_passed = [
        ValidationScenarioParams(scenario_title="Stack created - CREATE_COMPLETE",
                                 cmd_input_output_dict={
                                     old_version_cmd: CmdOutput(out=old_version_out.format('"CREATE_COMPLETE"'))},
                                 version=Version.V20),
        ValidationScenarioParams(scenario_title="Stack updated - UPDATE_COMPLETE",
                                 cmd_input_output_dict={
                                     old_version_cmd: CmdOutput(out=old_version_out.format('"UPDATE_COMPLETE"'))},
                                 version=Version.V24),
        ValidationScenarioParams(scenario_title="Stack checked - CHECK_COMPLETE",
                                 cmd_input_output_dict={
                                     old_version_cmd: CmdOutput(out=old_version_out.format('"CHECK_COMPLETE"'))},
                                 version=Version.V20),
        ValidationScenarioParams(scenario_title="Stack checked - DEPLOY_SUCCESS",
                                 cmd_input_output_dict={
                                     new_version_cmd: CmdOutput(out=new_version_out.format('DEPLOY_SUCCESS'))},
                                 version=Version.V25)
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="Stack in failed state - version < CBIS 25",
                                 cmd_input_output_dict={
                                     old_version_cmd: CmdOutput(out=old_version_out.format('"Other state"'))},
                                 version=Version.V20),
        ValidationScenarioParams(scenario_title="Stack in failed state - version >= CBIS 25",
                                 cmd_input_output_dict={
                                     new_version_cmd: CmdOutput(out=new_version_out.format('DEPLOY_FAILED'))},
                                 version=Version.V25),
        ValidationScenarioParams(scenario_title="Not having Stack - version >= CBIS 25",
                                 cmd_input_output_dict={
                                     new_version_cmd: CmdOutput(out=new_version_out_no_stack)},
                                 version=Version.V25)
    ]

    def _init_mocks(self, tested_object):
        tested_object.system_utils.get_stackrc_file_path = Mock()
        tested_object.system_utils.get_stackrc_file_path.return_value = '/home/stack/stackrc_locked'

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestCheckNetworkAgentHostnameMismatch(ValidationTestBase):
    tested_type = CheckNetworkAgentHostnameMismatch

    validation_cmd = "source {}; timeout --kill-after=60 30 openstack network agent list -f json".format('/home/stack/overcloudrc_locked')
    out = '''
        [
          {{
            "Availability Zone": null,
            "Binary": "ironic-neutron-agent",
            "Agent Type": "Baremetal Node",
            "State": "UP",
            "Alive": ":-)",
            "Host": "b058419b-d33f-4e93-9106-e908793ba406",
            "ID": "17439589-3ea2-4af0-b9da-305e43250ae9"
          }},
          {{
            "Availability Zone": null,
            "Binary": {},
            "Agent Type": "Baremetal Node",
            "State": "UP",
            "Alive": ":-)",
            "Host": "982727cc-6833-448d-b44e-2c61d95e902e",
            "ID": "e8786fb4-273c-4d41-9000-d82456cbdab3"
          }}
        ]
    '''
    def _init_mocks(self, tested_object):
        tested_object.system_utils.get_overcloudrc_file_path = Mock()
        tested_object.system_utils.get_overcloudrc_file_path.return_value = '/home/stack/overcloudrc_locked'

    scenario_passed = [
        ValidationScenarioParams(scenario_title="Neutron OvS agent",
                                 cmd_input_output_dict={
                                     validation_cmd: CmdOutput(out=out.format('"neutron-openvswitch-agent"'))}),
        ValidationScenarioParams(scenario_title="Neutron DHCP agent",
                                 cmd_input_output_dict={
                                     validation_cmd: CmdOutput(out=out.format('"neutron-dhcp-agent"'))}),
        ValidationScenarioParams(scenario_title="Neutron L3 agent",
                                 cmd_input_output_dict={
                                     validation_cmd: CmdOutput(out=out.format('"neutron-l3-agent"'))}),
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="Non neutron agent",
                                 cmd_input_output_dict={
                                     validation_cmd: CmdOutput(out=out.format('"Other agent"'))})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestCbisSystemCheckGnocchiCeilometer(ValidationTestBase):
    tested_type = CbisSystemCheckGnocchiCeilometer

    validation_cmd = "systemctl list-units --type=service | egrep 'gnocchi|ceilo|aodh'"
    validation_cmd2 = "systemctl list-unit-files --type=service | egrep 'gnocchi|ceilo|aodh'"

    out = '''gnocchi_api.service                     loaded active running  Dump dmesg to /var/log/dmesg
        gnocchi_metricd.service                 loaded active running  Read and set NIS domainname from /etc/sysconfig/network
        gnocchi_statsd.service                  loaded active running  Import network configuration from initramfs
        ceilometer_agent_notification.service   loaded active exited   Load legacy module configuration
        ceilometer_agent_central.service        loaded active running  Configure read-only root support'''
    out2 = '''gnocchi_api.service                           static
        gnocchi_statsd.service                        enabled
        ceilometer_agent_central.service              static'''

    scenario_passed = [
        ValidationScenarioParams(scenario_title="No output",
                                 cmd_input_output_dict={
                                     validation_cmd: CmdOutput(out=""), validation_cmd2: CmdOutput(out="")})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="Active services found",
                                 cmd_input_output_dict={
                                     validation_cmd: CmdOutput(out), validation_cmd2: CmdOutput(out2)})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    def test_has_confluence(self, tested_object):
        # Override the func since this val doesn't have a confluence. 
        # pls do not copy it! it's only for old validations that do not have a confluence page.
        warnings.warn("No confluence page")


class TestMySQLDirectoryNotLarge(ValidationTestBase):
    tested_type = MySQLDirectoryNotLarge

    validation_cmd = "sudo du -sh /var/lib/mysql"
    out = '{}    /var/lib/mysql'

    scenario_passed = [
        ValidationScenarioParams(scenario_title="mysql dir size less than 5GB",
                                 cmd_input_output_dict={
                                     validation_cmd: CmdOutput(out=out.format('5G'))}),
        ValidationScenarioParams(scenario_title="mysql dir size less than 50GB",
                                 cmd_input_output_dict={
                                     validation_cmd: CmdOutput(out=out.format('49.9G'))}),
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="mysql dir size more than 50GB",
                                 cmd_input_output_dict={
                                     validation_cmd: CmdOutput(out=out.format('50G'))}),
        ValidationScenarioParams(scenario_title="mysql dir size more than 50GB float",
                                 cmd_input_output_dict={
                                     validation_cmd: CmdOutput(out=out.format('85.9G'))}),
        ValidationScenarioParams(scenario_title="mysql dir size more than 50GB int",
                                 cmd_input_output_dict={
                                     validation_cmd: CmdOutput(out=out.format('70G'))}),
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestRabbitMQDirectoryNotLarge(ValidationTestBase):
    tested_type = RabbitMQDirectoryNotLarge

    validation_cmd = "sudo du -sh /var/lib/rabbitmq"
    out = '{}    /var/lib/rabbitmq'

    scenario_passed = [
        ValidationScenarioParams(scenario_title="rabbit dir size less than 1GB",
                                 cmd_input_output_dict={
                                     validation_cmd: CmdOutput(out=out.format('3.2M'))})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="rabbit dir size more than 1GB",
                                 cmd_input_output_dict={
                                     validation_cmd: CmdOutput(out=out.format('1G'))}),
        ValidationScenarioParams(scenario_title="rabbit dir size more than 1GB float",
                                 cmd_input_output_dict={
                                     validation_cmd: CmdOutput(out=out.format('5.9G'))}),
        ValidationScenarioParams(scenario_title="rabbit dir size more than 50GB int",
                                 cmd_input_output_dict={
                                     validation_cmd: CmdOutput(out=out.format('10G'))}),
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestValidateBMCPasswordValidAndSync(ValidationTestBase):
    tested_type = ValidateBMCPasswordValidAndSync
    redfish_cmd = 'curl --max-time 40 -s -k -u cloudband:"RMgC47jh_fR8hgQm" -H "Content-Type: application/json" https://10.11.223.16/redfish/v1/'
    base_redfish_out = """{"Systems": {"@odata.id": "/redfish/v1/Systems/"}}"""
    validation_cmd = 'sudo find /home/stack -iname "hosts.yaml"'
    validation_cmd2 = "cat /home/stack/hosts.yaml"
    validation_cmd_dell = "curl --max-time 40 -k -u cloudband:'RMgC47jh_fR8hgQm' -X GET https://10.11.223.16/redfish/v1/Systems/Self?\$select=PowerState| python -m json.tool"
    validation_cmd4 = "ipmitool -I lanplus -U cloudband -P 'RMgC47jh_fR8hgQm' -H 10.11.223.16 power status"
    validation_cmd_airframe = "curl --max-time 40 -k -u cloudband:'RMgC47jh_fR8hgQm' -X GET https://10.11.223.16/redfish/v1/Systems/System.Embedded.1?\$select=PowerState| python -m json.tool"
    members_identities_cmd = 'curl --max-time 40 -s -k -u cloudband:"RMgC47jh_fR8hgQm" -H "Content-Type: application/json" https://10.11.223.16/redfish/v1/Systems/'
    out = '/home/stack/hosts.yaml'
    dell_member_out = """{"@Redfish.CollectionCapabilities":{"@odata.type":"#CollectionCapabilities.v1_0_0.CollectionCapabilities","Capabilities":[{"CapabilitiesObject":{"@odata.id":"/redfish/v1/Systems/Capabilities"},"Links":{"RelatedItem":[{"@odata.id":"/redfish/v1/CompositionService/ResourceZones/1"}],"TargetCollection":{"@odata.id":"/redfish/v1/Systems"}},"UseCase":"ComputerSystemComposition"}]},"@odata.context":"/redfish/v1/$metadata#ComputerSystemCollection.ComputerSystemCollection","@odata.id":"/redfish/v1/Systems","@odata.type":"#ComputerSystemCollection.ComputerSystemCollection","Description":"Collection of Computer Systems","Members":[{"@odata.id":"/redfish/v1/Systems/Self"}],"Members@odata.count":1,"Name":"Systems Collection"}"""
    airframe_member_out = """{"@odata.context":"/redfish/v1/$metadata#ComputerSystemCollection.ComputerSystemCollection","@odata.id":"/redfish/v1/Systems","@odata.type":"#ComputerSystemCollection.ComputerSystemCollection","Description":"Collection of Computer Systems","Members":[{"@odata.id":"/redfish/v1/Systems/System.Embedded.1"}],"Members@odata.count":1,"Name":"Computer System Collection"}"""
    out2 = """
    nodes:
      - arch: x86_64
        availability_zone: ''
        capabilities: profile:Controller,boot_mode:bios
        cpu: 1
        disk: 100
        host_group: Controller
        hw_model_type:
          - airframe_rm18
          - airframe_rm19
        mac:
          - 04:3F:72:C5:58:9A
        memory: 4096
        name: server-1
        pm_addr: 10.11.223.16
        pm_password: RMgC47jh_fR8hgQm
        pm_type: pxe_ipmitool
        pm_user: cloudband
        rack_location: ''
        resource_class: baremetal.Controller
    """

    out3 = 'Chassis Power is on'

    redfish_out = '''
        [
          {{
            "@odata.context": "/redfish/v1/$metadata#ComputerSystem.ComputerSystem",
            "@odata.etag": "W/\"1697142072\"",
            "@odata.id": "/redfish/v1/Systems/Self",
            "@odata.type": "#ComputerSystem.v1_5_0.ComputerSystem",
            "PowerState": "On"
          }}
        ]
    '''

    scenario_passed = [
        ValidationScenarioParams(scenario_title="IPMI is enabled",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out),
                                                        validation_cmd2: CmdOutput(out2),
                                                        validation_cmd_dell: CmdOutput(out="", return_code=1,
                                                                                       err="err"),
                                                        validation_cmd4: CmdOutput(out3),
                                                        redfish_cmd: CmdOutput(base_redfish_out)},
                                 version=Version.V20),

        ValidationScenarioParams(scenario_title="IPMI isn't enabled",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out),
                                                        redfish_cmd: CmdOutput(base_redfish_out),
                                                        validation_cmd2: CmdOutput(out2),
                                                        validation_cmd_dell: CmdOutput(redfish_out),
                                                        members_identities_cmd: CmdOutput(dell_member_out),
                                                        validation_cmd4: CmdOutput(out="", return_code=1, err="err")},
                                 version=Version.V24),

        ValidationScenarioParams(scenario_title="redfish airframe",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out),
                                                        redfish_cmd: CmdOutput(base_redfish_out),
                                                        validation_cmd2: CmdOutput(out2),
                                                        members_identities_cmd: CmdOutput(airframe_member_out),
                                                        validation_cmd_airframe: CmdOutput(redfish_out)},
                                 version=Version.V25)
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="No output",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out),
                                                        redfish_cmd: CmdOutput(base_redfish_out),
                                                        validation_cmd2: CmdOutput(
                                                            out2.format('pm_addr', 'password', 'pm_user')),
                                                        validation_cmd_dell: CmdOutput(out="", return_code=1,
                                                                                       err="err"),
                                                        members_identities_cmd: CmdOutput(dell_member_out),
                                                        validation_cmd4: CmdOutput(out="", return_code=1, err="err")},
                                 version=Version.V24),
        ValidationScenarioParams(scenario_title="No output ipmitool",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out),
                                                        redfish_cmd: CmdOutput(base_redfish_out),
                                                        validation_cmd2: CmdOutput(
                                                            out2.format('pm_addr', 'password', 'pm_user')),
                                                        validation_cmd4: CmdOutput(out="", return_code=1, err="err")},
                                 version=Version.V20)
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestOvercloudBackupCheck(ValidationTestBase):
    tested_type = OvercloudBackupCheck

    get_host_executor_factory_mock = Mock()
    get_host_executor_factory_mock.return_value.get_host_executors_by_roles = Mock(return_value={
        'overcloud-controller-fi856-0': Mock(is_connected=True)})

    cmd1_lower_version = 'sudo ls -ltr /mnt/backup/overcloud-controller-fi856-0 | tail -3'
    cmd2_lower_version = "sudo ls -ltr /mnt/backup/overcloud-controller-fi856-0/{} | tail -1"
    cmd3_lower_version = "find /mnt/backup/overcloud-controller-fi856-0/{}/db_backup.enc -type f -mtime -3"
    cmd4_lower_version = "sudo cat /mnt/backup/overcloud-controller-fi856-0/{}/db_backup.enc | head -20 | wc -w"

    out1_lower_version = """drwxr-xr-x. 2 root root 6 Mar 19 03:00 2024.03.19.02.00.01
                            drwxr-xr-x. 2 root root 6 Mar 20 03:00 2024.03.20.02.00.01
                            drwxr-xr-x. 2 root root 6 Mar 21 03:00 2024.03.21.02.00.02"""

    out1_lower_version_older = """drwxr-xr-x. 2 root root 6 Jan 19 03:00 2024.01.19.02.00.01
                                  drwxr-xr-x. 2 root root 6 Jan 20 03:00 2024.01.20.02.00.01
                                  drwxr-xr-x. 2 root root 6 Jan 21 03:00 2024.01.21.02.00.02"""

    cmd1_higher_version = 'sudo ls -ltr /mnt/backup/overcloud_db_backups | grep overcloud-controller-fi856-0 | tail -1'
    cmd2_higher_version = 'find /mnt/backup/overcloud_db_backups/oc_db_backup_overcloud-controller-fi856-0_2024.03.20.03.02.00.enc -type f -mtime -3'
    cmd3_higher_version = 'sudo cat /mnt/backup/overcloud_db_backups/oc_db_backup_overcloud-controller-fi856-0_2024.03.20.03.02.00.enc | head -20 | wc -w'

    scenario_passed = [
        ValidationScenarioParams(scenario_title="CBIS version < V24 - Having overcloud backup",
                                 cmd_input_output_dict={cmd1_lower_version: CmdOutput(out1_lower_version),
                                                        cmd2_lower_version.format('2024.03.21.02.00.02'): CmdOutput(
                                                            '-rw-r--r--. 1 root root 55619072 Mar 21 03:00 db_backup.enc'),
                                                        cmd3_lower_version.format('2024.03.21.02.00.02'): CmdOutput(
                                                            '/mnt/backup/overcloud-controller-fi856-0/2024.03.21.02.00.02/db_backup.enc'),
                                                        cmd4_lower_version.format('2024.03.21.02.00.02'): CmdOutput(
                                                            '1')},
                                 version=Version.V20,
                                 library_mocks_dict={"gs.get_host_executor_factory": get_host_executor_factory_mock,
                                                     "os.path.join": Mock(side_effect=path_join)}),

        ValidationScenarioParams(scenario_title="CBIS version = V24 - Having overcloud backup",
                                 cmd_input_output_dict={cmd1_higher_version: CmdOutput(
                                     '-rw-r--r--. 1 root root 54412608 Mar 21 04:00 oc_db_backup_overcloud-controller-fi856-0_2024.03.20.03.02.00.enc'),
                                                        cmd2_higher_version: CmdOutput(
                                                            '/mnt/backup/overcloud_db_backups/oc_db_backup_overcloud-controller-fi856-0_2024.03.20.03.02.00.enc'),
                                                        cmd3_higher_version: CmdOutput('1')},
                                 version=Version.V24,
                                 library_mocks_dict={"gs.get_host_executor_factory": get_host_executor_factory_mock,
                                                     "os.path.join": Mock(side_effect=path_join)})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="CBIS version < V24 - no folder of controller",
                                 cmd_input_output_dict={cmd1_lower_version: CmdOutput('')},
                                 version=Version.V20,
                                 library_mocks_dict={"gs.get_host_executor_factory": get_host_executor_factory_mock,
                                                     "os.path.join": Mock(side_effect=path_join)}),

        ValidationScenarioParams(scenario_title="CBIS version < V24 - no *.enc backup file",
                                 cmd_input_output_dict={cmd1_lower_version: CmdOutput(out1_lower_version),
                                                        cmd2_lower_version.format('2024.03.19.02.00.01'): CmdOutput(''),
                                                        cmd2_lower_version.format('2024.03.20.02.00.01'): CmdOutput(''),
                                                        cmd2_lower_version.format('2024.03.21.02.00.02'): CmdOutput(
                                                            '')},
                                 version=Version.V20,
                                 library_mocks_dict={"gs.get_host_executor_factory": get_host_executor_factory_mock,
                                                     "os.path.join": Mock(side_effect=path_join)}),

        ValidationScenarioParams(scenario_title="CBIS version < V24 - backup file wasn't taken from last 3 days",
                                 cmd_input_output_dict={cmd1_lower_version: CmdOutput(out1_lower_version_older),
                                                        cmd2_lower_version.format('2024.01.21.02.00.02'): CmdOutput(
                                                            '-rw-r--r--. 1 root root 55619072 Jan 21 03:00 db_backup.enc'),
                                                        cmd3_lower_version.format('2024.01.21.02.00.02'): CmdOutput(
                                                            '')},
                                 version=Version.V20,
                                 library_mocks_dict={"gs.get_host_executor_factory": get_host_executor_factory_mock,
                                                     "os.path.join": Mock(side_effect=path_join)}),

        ValidationScenarioParams(scenario_title="CBIS version < V24 - backup file is empty",
                                 cmd_input_output_dict={cmd1_lower_version: CmdOutput(out1_lower_version),
                                                        cmd2_lower_version.format('2024.03.21.02.00.02'): CmdOutput(
                                                            '-rw-r--r--. 1 root root 55619072 Mar 21 03:00 db_backup.enc'),
                                                        cmd3_lower_version.format('2024.03.21.02.00.02'): CmdOutput(
                                                            '/mnt/backup/overcloud-controller-fi856-0/2024.03.21.02.00.02/db_backup.enc'),
                                                        cmd4_lower_version.format('2024.03.21.02.00.02'): CmdOutput(
                                                            '0')},
                                 version=Version.V20,
                                 library_mocks_dict={"gs.get_host_executor_factory": get_host_executor_factory_mock,
                                                     "os.path.join": Mock(side_effect=path_join)}),

        ValidationScenarioParams(scenario_title="CBIS version = V24 - no *.enc backup file for controller",
                                 cmd_input_output_dict={cmd1_higher_version: CmdOutput('')},
                                 version=Version.V24,
                                 library_mocks_dict={"gs.get_host_executor_factory": get_host_executor_factory_mock,
                                                     "os.path.join": Mock(side_effect=path_join)}),

        ValidationScenarioParams(scenario_title="CBIS version = V24 - backup file wasn't taken from last 3 days",
                                 cmd_input_output_dict={cmd1_higher_version: CmdOutput(
                                     '-rw-r--r--. 1 root root 54412608 Mar 21 04:00 oc_db_backup_overcloud-controller-fi856-0_2024.03.20.03.02.00.enc'),
                                                        cmd2_higher_version: CmdOutput(''),
                                                        cmd3_higher_version: CmdOutput('1')},
                                 version=Version.V24,
                                 library_mocks_dict={"gs.get_host_executor_factory": get_host_executor_factory_mock,
                                                     "os.path.join": Mock(side_effect=path_join)}),

        ValidationScenarioParams(scenario_title="CBIS version = V24 - backup file is empty",
                                 cmd_input_output_dict={cmd1_higher_version: CmdOutput(
                                     '-rw-r--r--. 1 root root 54412608 Mar 21 04:00 oc_db_backup_overcloud-controller-fi856-0_2024.03.20.03.02.00.enc'),
                                                        cmd2_higher_version: CmdOutput(
                                                            '/mnt/backup/overcloud_db_backups/oc_db_backup_overcloud-controller-fi856-0_2024.03.20.03.02.00.enc'),
                                                        cmd3_higher_version: CmdOutput('0')},
                                 version=Version.V24,
                                 library_mocks_dict={"gs.get_host_executor_factory": get_host_executor_factory_mock,
                                                     "os.path.join": Mock(side_effect=path_join)})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    def test_has_confluence(self, tested_object):
        # Override the func since this val doesn't have a confluence.
        # pls do not copy it! it's only for old validations that do not have a confluence page.
        warnings.warn("No confluence page")


class TestCheckDeploymentServerBlacklist(ValidationTestBase):
    tested_type = CheckDeploymentServerBlacklist

    validation_cmd = 'source {}; openstack stack show overcloud  | grep DeploymentServerBlacklist'.format('/home/stack/stackrc_locked')

    out = """
        |                       | DeploymentServerBlacklist: ''  

                                                               |
        """

    out1 = """
    DeploymentServerBlacklist:
    - overcloud-ovscompute-1
    - overcloud-storage-1
    - overcloud-ovscompute-0
    - overcloud-dpdkperformancecompute-1
    - overcloud-storage-0
    - overcloud-dpdkperformancecompute-0
    - overcloud-sriovperformancecompute-0
    """

    out2 = """  """

    def _init_mocks(self, tested_object):
        tested_object.system_utils.get_stackrc_file_path = Mock()
        tested_object.system_utils.get_stackrc_file_path.return_value = '/home/stack/stackrc_locked'

    scenario_passed = [
        ValidationScenarioParams(scenario_title="No Deployment Server Blacklist",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out)}),
        ValidationScenarioParams(scenario_title="DeploymentServerBlacklist is not found in the output",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out2)})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="Deployment Server Black list not empty",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out1)})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestVerifySymlinkForCACert(ValidationTestBase):
    tested_type = VerifySymlinkForCACert
    validation_cmd1 = "sudo /usr/bin/podman ps --format '{{{{.Names}}}}' | grep -w {} "
    out1 = "keystone"

    validation_cmd2 = "sudo podman exec -it keystone ls -l /usr/lib/python2.7/site-packages/certifi/cacert.pem 2>/dev/null"
    pass_out = "lrwxrwxrwx. 1 root root 49 Apr 22 13:27 /usr/lib/python2.7/site-packages/certifi/cacert.pem -> /etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem"
    failed_out = "-rwxrwxrwx. 1 root root 49 Apr 22 13:27 /usr/lib/python2.7/site-packages/certifi/cacert.pem"

    scenario_passed = [ValidationScenarioParams(scenario_title="symlink present",
                                                cmd_input_output_dict={
                                                    validation_cmd1.format("keystone"): CmdOutput(out1),
                                                    validation_cmd1.format("horizon"): CmdOutput(out1),
                                                    validation_cmd2: CmdOutput(pass_out)},
                                                tested_object_mock_dict={
                                                    "verify_symlink_for_source_file": Mock(return_value=True)}
                                                )
                       ]

    scenario_failed = [ValidationScenarioParams(scenario_title="symlink not present",
                                                cmd_input_output_dict={
                                                    validation_cmd1.format("keystone"): CmdOutput(out1),
                                                    validation_cmd1.format("horizon"): CmdOutput(out1),
                                                    validation_cmd2: CmdOutput(failed_out)},
                                                tested_object_mock_dict={
                                                    "verify_symlink_for_source_file": Mock(return_value=False)}
                                                ),
                       ValidationScenarioParams(scenario_title="file not present",
                                                cmd_input_output_dict={
                                                    validation_cmd1.format("keystone"): CmdOutput(out1),
                                                    validation_cmd1.format("horizon"): CmdOutput(out1),
                                                    validation_cmd2: CmdOutput("")},
                                                tested_object_mock_dict={
                                                    "verify_symlink_for_source_file": Mock(return_value=False)}
                                                ),
                       ValidationScenarioParams(scenario_title="podman container not present",
                                                cmd_input_output_dict={
                                                    validation_cmd1.format("keystone"): CmdOutput(""),
                                                    validation_cmd1.format("horizon"): CmdOutput("")},
                                                tested_object_mock_dict={
                                                    "verify_symlink_for_source_file": Mock(return_value=False)}
                                                )
                       ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestVerifyDefaultLibvirtNetwork(ValidationTestBase):
    tested_type = VerifyDefaultLibvirtNetwork

    validation_cmd = "sudo virsh net-list --name"
    out = " "
    failed_out = "default"

    scenario_passed = [
        ValidationScenarioParams(scenario_title="default libvirt network doesn't exist",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out)})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="default libvirt network exist",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(failed_out)})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)



class TestValidateARPResponder(ValidationTestBase):
    tested_type = ValidateARPResponder


    scenario_passed = [
        ValidationScenarioParams(
            scenario_title="All configs match (user_config, agent, neutron)",
            cmd_input_output_dict={
                "collector:GetARPResponderFromHosts": {
                    "controller-0": ["True"],
                    "compute-0": ["True"],
                },
                "configstore": {
                    'CBIS': {
                        'host_group_config': {
                            'controller': {'arp_responder': True},
                            'compute': {'arp_responder': True},
                        }
                    }
                },
            },
        ),
    ]

    scenario_failed = [
        ValidationScenarioParams(
            scenario_title="Agent reports False while user_config True",
            cmd_input_output_dict={
                "collector:GetARPResponderFromHosts": {
                    "controller-0": ["False"],
                },
                "configstore": {
                    'CBIS': {
                        'host_group_config': {
                            'controller': {'arp_responder': True},
                        }
                    }
                },
            },
        ),
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        tested_object._host_executor = Mock()

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        tested_object._host_executor = Mock()


class TestRabbitMQErrorLogValidation(ValidationTestBase):
    tested_type = RabbitMQErrorLogValidation
    docker_or_podman = "podman"
    base_cmd = "sudo {docker_or_podman} exec $(sudo {docker_or_podman} ps -f name=rabbitmq-bundle -q) {inner_cmd}"
    find_files_cmd = base_cmd.format(docker_or_podman=docker_or_podman,
                                     inner_cmd="""bash -c "find /var/log/rabbitmq/ -type f -name '*.log*' -newermt '$(date +%F) 00:00:00'" """)
    files = "mylog.log mylog.log.1"

    count_cmd = base_cmd.format(docker_or_podman=docker_or_podman,
                               inner_cmd="""bash -c "grep -Ei 'CRASH|partition|alarm' {files} | wc -l" """.format(files=files))
    find_lines_cmd = base_cmd.format(docker_or_podman=docker_or_podman,
                               inner_cmd="""bash -c "grep -Ei 'CRASH|partition|alarm' {files}" """.format(files=files))
    scenario_passed = [
        ValidationScenarioParams(
            "logs files presented, no errors in them",
            cmd_input_output_dict={find_files_cmd: CmdOutput(out=files, return_code=0),
                                   count_cmd: CmdOutput(out="0", return_code=0)},
            tested_object_mock_dict={"get_docker_or_podman": Mock(return_value="podman")}
        ),
        ValidationScenarioParams(
            "logs files not presented",
            cmd_input_output_dict={find_files_cmd: CmdOutput(out="", return_code=0)},
            tested_object_mock_dict={"get_docker_or_podman": Mock(return_value="podman")}
        )
    ]

    scenario_failed = [
        ValidationScenarioParams(
            "logs files presented, crash found",
            cmd_input_output_dict={find_files_cmd: CmdOutput(out=files, return_code=0),
                                   count_cmd: CmdOutput(out="1", return_code=0),
                                   find_lines_cmd: CmdOutput(out="CRASH ...", return_code=0)},
            tested_object_mock_dict={"get_docker_or_podman": Mock(return_value="podman")}
        )
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

class TestRedisMasterRoleAvailability(ValidationTestBase):
    tested_type = RedisMasterRoleAvailability

    validation_cmd = "sudo pcs status | grep redis"
    out = """GuestOnline: [ galera-bundle-0@overcloud-controller-cbis22-0 galera-bundle-1@overcloud-controller-cbis22-1 galera-bundle-2@overcloud-controller-cbis22-2 rabbitmq-bundle-0@overcloud-controller-cbis22-0 rabbitmq-bundle-1@overcloud-controller-cbis22-1 rabbitmq-bundle-2@overcloud-controller-cbis22-2 redis-bundle-0@overcloud-controller-cbis22-0 redis-bundle-1@overcloud-controller-cbis22-1 redis-bundle-2@overcloud-controller-cbis22-2 ]
    podman container set: redis-bundle [cluster.common.tag/centos-binary-redis:pcmklatest]
      redis-bundle-0       (ocf::heartbeat:redis): Master overcloud-controller-cbis22-0
      redis-bundle-1       (ocf::heartbeat:redis): Slave overcloud-controller-cbis22-1
      redis-bundle-2       (ocf::heartbeat:redis): Slave overcloud-controller-cbis22-2"""

    failed_out = """GuestOnline: [ galera-bundle-0@overcloud-controller-cbis22-0 galera-bundle-1@overcloud-controller-cbis22-1 galera-bundle-2@overcloud-controller-cbis22-2 rabbitmq-bundle-0@overcloud-controller-cbis22-0 rabbitmq-bundle-1@overcloud-controller-cbis22-1 rabbitmq-bundle-2@overcloud-controller-cbis22-2 redis-bundle-0@overcloud-controller-cbis22-0 redis-bundle-1@overcloud-controller-cbis22-1 redis-bundle-2@overcloud-controller-cbis22-2 ]
    podman container set: redis-bundle [cluster.common.tag/centos-binary-redis:pcmklatest]
      redis-bundle-0       (ocf::heartbeat:redis): Slave overcloud-controller-cbis22-0
      redis-bundle-1       (ocf::heartbeat:redis): Slave overcloud-controller-cbis22-1
      redis-bundle-2       (ocf::heartbeat:redis): Slave overcloud-controller-cbis22-2"""

    scenario_passed = [
        ValidationScenarioParams(scenario_title="passed scenario",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out)})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="failed scenario",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(failed_out)})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestRabbitMQMessagesLogValidation(ValidationTestBase):
    tested_type = RabbitMQMessagesLogValidation
    today, yesterday = "Dec 17", "Dec 18"
    grep_cmd = "sudo grep -Ei 'Node rabbitmq-bundle-[^ ]+ state is now lost|Removing all rabbitmq-bundle-[^ ]+ attributes for peer' /var/log/messages | grep -Ei '{today}|{yesterday}'".format(today=today, yesterday=yesterday)
    count_cmd = "{} | wc -l".format(grep_cmd)
    scenario_passed = [
        ValidationScenarioParams(
            "no errors found",
            cmd_input_output_dict={count_cmd: CmdOutput(out="0", return_code=0)},
            tested_object_mock_dict={"get_today_yesterday_dates": Mock(return_value=(today, yesterday))}
        )
    ]

    scenario_failed = [
        ValidationScenarioParams(
            "error found",
            cmd_input_output_dict={count_cmd: CmdOutput(out="1", return_code=0),
                                   grep_cmd: CmdOutput(out="Node rabbitmq-bundle-2 state is now lost", return_code=0)},
            tested_object_mock_dict={"get_today_yesterday_dates": Mock(return_value=(today, yesterday))}
        )
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

class TestCinderDefaultVolumeType(ValidationTestBase):
    tested_type = CinderDefaultVolumeType

    scenario_passed = [
        ValidationScenarioParams(scenario_title="Cinder default volume type in user config is not empty",
                                 library_mocks_dict={"ConfigStore.get_cbis_user_config": Mock(return_value={'CBIS': {
                                         'storage': {'cinder_default_volume_type': 'tripleo-ceph'}}})
                                 })]


    scenario_failed = [ValidationScenarioParams(scenario_title="Cinder default volume type in user config is empty",
                                                library_mocks_dict={
                                                    "ConfigStore.get_cbis_user_config": Mock(return_value={'CBIS': {
                                                        'storage': {'cinder_default_volume_type': None}}})
                                                                   })]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
         ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)