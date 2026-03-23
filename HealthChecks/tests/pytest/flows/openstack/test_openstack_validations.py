from __future__ import absolute_import
import warnings
import pytest
from tests.pytest.tools.versions_alignment import Mock
from flows.OpenStack.openstack_validations import SpaceNotInAvailabilityZone, ValidateHttpdServiceUC, \
    PassthroughWhitelistInNova, CompareCorosyncNodeList, CorosyncConfDataCollector, VerifyPassthroughWhitelistInNovaConf,VerifyCbisManagerDockerLayers, TripleOVolumeTypeValidation
from tests.pytest.pytest_tools.operator.test_data_collector import DataCollectorTestBase, DataCollectorScenarioParams
from tests.pytest.pytest_tools.operator.test_operator import CmdOutput
from tests.pytest.pytest_tools.operator.test_validation_base import ValidationTestBase, ValidationScenarioParams


class TestSpaceNotInAvailabilityZone(ValidationTestBase):
    tested_type = SpaceNotInAvailabilityZone

    validation_cmd = "source {}; openstack aggregate list -f json -c 'Availability Zone'".format('/home/stack/overcpuldrc_locked')

    out = '''
        [
          {{
            "Availability Zone": {zone_name1}
          }},
          {{
            "Availability Zone": {zone_name2}
          }}
        ]
    '''

    scenario_passed = [
        ValidationScenarioParams(scenario_title="Two valid zone names",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out=out.format(zone_name1="\"ovs\"", zone_name2="\"fi862\""))}),
        ValidationScenarioParams(scenario_title="First valid zone name, Second null",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out=out.format(zone_name1="\"ovs\"", zone_name2="null"))})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="First valid zone name, Second zone name with space",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out=out.format(zone_name1="\"ovs\"", zone_name2="\"fi 862\""))}),
        ValidationScenarioParams(scenario_title="First zone name with space, Second valid zone name",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out=out.format(zone_name1="\"fi 862\"", zone_name2="\"ovs\""))})
    ]

    def _init_mocks(self, tested_object):
        tested_object.system_utils.get_overcloudrc_file_path = Mock()
        tested_object.system_utils.get_overcloudrc_file_path.return_value = '/home/stack/overcpuldrc_locked'

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestPassthroughWhitelistInNova(ValidationTestBase):
    tested_type = PassthroughWhitelistInNova

    validation_cmd = "sudo grep passthrough /var/lib/config-data/nova_libvirt/etc/nova/nova.conf | grep -v '#'"
    out = """ 
    passthrough_whitelist={"devname":"ens5f0","physical_network":"physnet1"}
    passthrough_whitelist={"devname":"ens5f1","physical_network":"physnet2"}
    passthrough_whitelist={"devname":"ens31f0","physical_network":"physnet1"}
    passthrough_whitelist={"devname":"ens31f1","physical_network":"physnet2"}
    """

    scenario_passed = [
        ValidationScenarioParams(scenario_title="Physnet configured",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out)})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="No physnets configured",
                                 cmd_input_output_dict={validation_cmd: CmdOutput("")})
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


class TestValidateHttpdServiceUC(ValidationTestBase):
    tested_type = ValidateHttpdServiceUC

    validation_cmd = "systemctl status httpd"

    out = '''
            httpd.service - The Apache HTTP Server
               Loaded: loaded (/usr/lib/systemd/system/httpd.service; enabled; vendor preset: disabled)
               Active: {status} (running) since Thu 2023-03-16 09:15:54 UTC; 7h ago
                 Docs: man:httpd(8)
                       man:apachectl(8)
             Main PID: 624577 (httpd)
               Status: "Total requests: 0; Current requests/sec: 0; Current traffic:   0 B/sec"
                Tasks: 6
               Memory: 14.9M
               CGroup: /system.slice/httpd.service
                       624577 /usr/sbin/httpd -DFOREGROUND
                       624579 /usr/sbin/httpd -DFOREGROUND
                       624580 /usr/sbin/httpd -DFOREGROUND
                       624581 /usr/sbin/httpd -DFOREGROUND
                       624582 /usr/sbin/httpd -DFOREGROUND
                       624583 /usr/sbin/httpd -DFOREGROUND
        '''

    scenario_passed = [
        ValidationScenarioParams(scenario_title="httpd is active",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out=out.format(status="active"))})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="httpd is not active",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out=out.format(status="failed"))})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestCorosyncConfDataCollector(DataCollectorTestBase):
    tested_type = CorosyncConfDataCollector
    scenarios = [
        DataCollectorScenarioParams(
            scenario_title="basic scenario",
            cmd_input_output_dict={
                "md5sum /etc/corosync/corosync.conf": CmdOutput("out")},
            scenario_res="out"
        )]

    @pytest.mark.parametrize("scenario_params", scenarios)
    def test_collect_data(self, scenario_params, tested_object):
        DataCollectorTestBase.test_collect_data(self, scenario_params, tested_object)

class TestCompareCorosyncNodeList(ValidationTestBase):
    tested_type = CompareCorosyncNodeList
    scenario_passed = [
        ValidationScenarioParams(scenario_title="base scenario",
                                 data_collector_dict={CorosyncConfDataCollector:
                                                          {"controller0": "value", "controller1": "value",
                                                           "controller2": "value"}})
    ]

    scenario_no_suitable_host = [
        ValidationScenarioParams(scenario_title="no suitable host scenario",
                                 data_collector_dict={CorosyncConfDataCollector: {}})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="failed scenario",
                                 data_collector_dict={
                                     CorosyncConfDataCollector: {"controller0": "value1", "controller1": "value2",
                                                                 "controller2": "value1", "controller3": "value2",
                                                                 "controller4": "value3", "controller5": "value3"}})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_no_suitable_host)
    def test_scenario_no_suitable_host(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_no_suitable_host(self, scenario_params, tested_object)

class TestVerifyPassthroughWhitelistInNovaConf(ValidationTestBase):
    tested_type = VerifyPassthroughWhitelistInNovaConf
    file_path = r"/var/lib/config-data/puppet-generated/nova_libvirt/etc/nova/nova.conf"
    target_key = "passthrough_whitelist"
    cmd = "sudo grep '{}' '{}'".format(target_key, file_path)
    passed_out1 = """
    passthrough_whitelist = {...}
    """
    passed_out2 = """
            #passthrough_whitelist = {...}
        #passthrough_whitelist = {...}
        passthrough_whitelist =
            passthrough_whitelist={...}
        """
    scenario_passed = [
        ValidationScenarioParams(
            "passthrough_whitelist found",
            additional_parameters_dict={'file_exist': True},
            cmd_input_output_dict={
                cmd: CmdOutput(passed_out1)
            },
        ),
        ValidationScenarioParams(
            "passthrough_whitelist found after comments",
            additional_parameters_dict={'file_exist': True},
            cmd_input_output_dict={
                cmd: CmdOutput(passed_out2)
            },
        )
    ]
    failed_out = """
        #passthrough_whitelist = {...}
    #passthrough_whitelist = {...}
    passthrough_whitelist =
    """
    scenario_failed = [
        ValidationScenarioParams(
            "passthrough_whitelist invalid",
            additional_parameters_dict={'file_exist': True},
            cmd_input_output_dict={
                cmd: CmdOutput(failed_out)
            },
        ),
        ValidationScenarioParams(
            "nova.conf not exist",
            additional_parameters_dict={'file_exist': False},
            cmd_input_output_dict={
                cmd: CmdOutput(failed_out)
            },
        ),
        ValidationScenarioParams(
            "no matches in nova.conf found",
            additional_parameters_dict={'file_exist': True},
            cmd_input_output_dict={
                cmd: CmdOutput(out="", return_code=1)
            },
        )
    ]

    scenario_unexpected_system_output = [
        ValidationScenarioParams(
            "grep return an error",
            additional_parameters_dict={'file_exist': True},
            cmd_input_output_dict={
                cmd: CmdOutput(out="", return_code=2)
            },
        )
    ]

    def _init_mocks(self, tested_object):
        tested_object.file_utils.is_file_exist = Mock()
        tested_object.file_utils.is_file_exist.return_value = self.additional_parameters_dict['file_exist']

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_unexpected_system_output(self, scenario_params, tested_object)



class TestVerifyCbisManagerDockerLayers(ValidationTestBase):
    tested_type = VerifyCbisManagerDockerLayers

    validation_cmd = "sudo docker history cbis_manager|wc -l"

    out = '''
    102
        '''
    out_fail = '''
    129
    '''

    scenario_passed = [
        ValidationScenarioParams(scenario_title="less_than_125_layers",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out)})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="more_than_125_layers",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out_fail)})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

class TestCheckTripleOVolume(ValidationTestBase):
    tested_type = TripleOVolumeTypeValidation
    tripleo_volume = "source {}; openstack volume type list --long -f json | jq -r '.[] | select(.Name == \"tripleo\") | .Name'".format('/home/stack/overcloudrc_locked')
    tripleo_volume_out = ""
    volumes = "source {};  openstack volume list --all-projects --long -f json | jq -r '.[] | select(.Type == \"tripleo\") | .Name'".format('/home/stack/overcloudrc_locked')
    volumes_out = ""
    scenario_passed = [
        ValidationScenarioParams(scenario_title="TripleO volume_type does not exist",
                                 additional_parameters_dict={'check_for_tripleo_volume_type': "","get_volumes_with_tripleo":""},
                                 cmd_input_output_dict={tripleo_volume: CmdOutput(out="")}
                                 )]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="TripleO volume_type exists",
                                 additional_parameters_dict={'check_for_tripleo_volume_type': "tripleo",
                                                             "get_volumes_with_tripleo": ""},
                                 cmd_input_output_dict={tripleo_volume: CmdOutput(out="tripleo")}
                                 ),

        ValidationScenarioParams(scenario_title="TripleO volume_type exists with some volumes using this type",
                             additional_parameters_dict={'check_for_tripleo_volume_type': "tripleo",
                                                         "get_volumes_with_tripleo": "vm-1"},
                             cmd_input_output_dict={tripleo_volume: CmdOutput(out=tripleo_volume_out), volumes: CmdOutput(out=volumes_out)}
                             )]

    def _init_mocks(self, tested_object):
        tested_object.system_utils.get_overcloudrc_file_path = Mock()
        tested_object.system_utils.get_overcloudrc_file_path.return_value = '/home/stack/overcloudrc_locked'

        tested_object.check_for_tripleo_volume_type = Mock()
        tested_object.check_for_tripleo_volume_type.return_value = self.additional_parameters_dict.get("check_for_tripleo_volume_type")

        tested_object.get_volumes_with_tripleo = Mock()
        tested_object.get_volumes_with_tripleo.return_value = self.additional_parameters_dict.get("get_volumes_with_tripleo")

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
         ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)