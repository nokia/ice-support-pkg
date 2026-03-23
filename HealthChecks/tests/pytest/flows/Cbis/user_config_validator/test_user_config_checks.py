from __future__ import absolute_import
import copy
from tests.pytest.tools.versions_alignment import Mock
import warnings
import pytest

from flows.Cbis.user_config_validator.user_config_checks import *
from tests.pytest.pytest_tools.operator.test_operator import CmdOutput
from tests.pytest.pytest_tools.operator.test_validation_base import ValidationTestBase, ValidationScenarioParams
from tools import sys_parameters
from tools.global_enums import Version


class MockBaseUserConfigValidator(ValidationTestBase):

    def _init_mocks(self, tested_object):
        sys_parameters.get_base_conf = Mock()
        sys_parameters.get_base_conf.return_value = self.additional_parameters_dict['base_conf']


class TestIsDnsCorrect(MockBaseUserConfigValidator):
    tested_type = IsDnsCorrect
    ipv4_base_conf = {
        "CBIS": {"common": {"dns_servers": ["135.239.25.18", "135.239.25.17"]}}
    }

    ipv6_base_conf = {
        "CBIS": {"common": {"dns_servers": ["2a00:8a00:4000:20c::8d:53", "2a00:8a00:4000:20c::8d:54"]}}
    }

    cmd_input_ipv4_output_dict_passed = {
        "cat /etc/resolv.conf | grep 'nameserver '": CmdOutput(
            out="nameserver 135.239.25.18.\nnameserver 135.239.25.17.")
    }

    cmd_input_ipv6_output_dict_passed = {
        "cat /etc/resolv.conf | grep 'nameserver '": CmdOutput(
            out="nameserver 2a00:8a00:4000:20c::8d:53\nnameserver 2a00:8a00:4000:20c::8d:54")
    }

    cmd_input_output_dict_failed = {
        "cat /etc/resolv.conf | grep 'nameserver '": CmdOutput(
            out="nameserver 135.239.25.111\nnameserver 135.239.25.17.")
    }

    scenario_passed = [
        ValidationScenarioParams(scenario_title="IPV4 - runtime 'dns' match configured 'dns'",
                                 cmd_input_output_dict=cmd_input_ipv4_output_dict_passed,
                                 additional_parameters_dict={"base_conf": ipv4_base_conf}),
        ValidationScenarioParams(scenario_title="IPV6 - runtime 'dns' match configured 'dns'",
                                 cmd_input_output_dict=cmd_input_ipv6_output_dict_passed,
                                 additional_parameters_dict={"base_conf": ipv6_base_conf})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="runtime 'dns' not match configured 'dns'",
                                 cmd_input_output_dict=cmd_input_output_dict_failed,
                                 additional_parameters_dict={"base_conf": ipv4_base_conf})
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


class TestIsNtpCorrect(MockBaseUserConfigValidator):
    conf_file_out = """
# ntp.conf: Managed by puppet.
#
# Enable next tinker options:
# panic - keep ntpd from panicking in the event of a large clock skew
# when a VM guest is suspended and resumed;
# stepout - allow ntpd change offset faster
tinker panic 0

disable monitor

# Permit time synchronization with our time source, but do not
# permit the source to query or modify the service on this system.
restrict default kod nomodify notrap nopeer noquery
restrict -6 default kod nomodify notrap nopeer noquery
restrict 127.0.0.1
restrict -6 ::1



# Set up servers for ntpd with next options:
# server - IP address or DNS name of upstream NTP server
# iburst - allow send sync packages faster if upstream unavailable
# prefer - select preferrable server
# minpoll - set minimal update frequency
# maxpoll - set maximal update frequency
server {ip1} iburst
server {ip2} iburst


# Driftfile.
driftfile /var/lib/ntp/drift    
"""
    tested_type = IsNtpCorrect
    base_conf = {
        "CBIS": {"common": {"ntp_servers": ["10.75.223.4", "10.75.223.5"]}}
    }

    scenario_passed = [
        ValidationScenarioParams(scenario_title="runtime 'ntp' match configured 'ntp' version 22", version=Version.V22,
                                 additional_parameters_dict={"base_conf": base_conf,
                                                             "value_from_system": ['10.75.223.4', '10.75.223.5']},
                                 ),
        ValidationScenarioParams(scenario_title="runtime 'ntp' match configured 'ntp' version 20", version=Version.V20,
                                 additional_parameters_dict={"base_conf": base_conf,
                                                             "value_from_system": ['10.75.223.4', '10.75.223.5']})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="runtime 'ntp' not match configured 'ntp'", version=Version.V22,
                                 additional_parameters_dict={"base_conf": base_conf,
                                                             "value_from_system": ['10.75.223.6', '10.75.223.5']})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    def _init_mocks(self, tested_object):
        MockBaseUserConfigValidator._init_mocks(self, tested_object)
        tested_object._get_value_from_system = Mock()
        tested_object._get_value_from_system.return_value = self.additional_parameters_dict['value_from_system']


class TestIsTimeZoneCorrect(MockBaseUserConfigValidator):
    tested_type = IsTimeZoneCorrect
    base_conf = {
        "CBIS": {"common": {"dns_servers": ["135.239.25.18", "135.239.25.17"], "time_zone": "UTC"}}
    }

    cmd_input_output_dict_passed = {"timedatectl status |grep zone": CmdOutput(out=" Time zone: UTC (UTC, +0000)")}

    cmd_input_output_dict_failed = {
        "timedatectl status |grep zone": CmdOutput(out="Time zone: America/Chicago (CDT, -0500)")}

    scenario_passed = [
        ValidationScenarioParams(scenario_title="runtime 'time_zone' match configured 'time_zone'",
                                 cmd_input_output_dict=cmd_input_output_dict_passed,
                                 additional_parameters_dict={"base_conf": base_conf})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="runtime 'time_zone' not match configured 'time_zone'",
                                 cmd_input_output_dict=cmd_input_output_dict_failed,
                                 additional_parameters_dict={"base_conf": base_conf})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestIsHypervisorCidrCorrect(MockBaseUserConfigValidator):
    tested_type = IsHypervisorCidrCorrect
    base_conf = {
        "CBIS": {
            "common": {"dns_servers": ["135.239.25.18", "135.239.25.17"], "time_zone": "UTC"}, "undercloud": {
                "enable_ipv6": "IPv4",
                "hypervisor_cidr": "10.75.236.194/27"}}
    }

    cmd_input_output_dict_passed = {
        "sudo /sbin/ip a l br-public |grep 'inet '": CmdOutput(
            out="inet 10.75.236.194/27 brd 10.75.236.223 scope global br-public")}

    cmd_input_output_dict_failed = {
        "sudo /sbin/ip a l br-public |grep 'inet '": CmdOutput(
            out="inet 10.75.236.195/27 brd 10.75.236.223 scope global br-public")}

    scenario_passed = [
        ValidationScenarioParams(scenario_title="runtime 'hypervisor_cidr' match configured 'hypervisor_cidr'",
                                 cmd_input_output_dict=cmd_input_output_dict_passed,
                                 additional_parameters_dict={"base_conf": base_conf})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="runtime 'hypervisor_cidr' not match configured 'hypervisor_cidr'",
                                 cmd_input_output_dict=cmd_input_output_dict_failed,
                                 additional_parameters_dict={"base_conf": base_conf})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestIsBackupNfsMountpointCorrect(MockBaseUserConfigValidator):
    tested_type = IsBackupNfsMountpointCorrect
    base_conf = {
        "CBIS": {"common": {"dns_servers": ["135.239.25.18", "135.239.25.17"], "time_zone": "UTC"},
                 "openstack_deployment": {"elk_disk": "sda", "backup_nfs_mountpoint": "/root/backup"
                                          }}
    }

    cmd_input_output_dict_passed = {"sudo crontab -l | grep 'CbisOvercloudDatabaseBackup' | cut -d' ' -f7": CmdOutput(
        out="/root/backup/CbisOvercloudDatabaseBackup.py"),
        "dirname /root/backup/CbisOvercloudDatabaseBackup.py": CmdOutput(out="/root/backup")}
    cmd_input_output_dict_failed = {"sudo crontab -l | grep 'CbisOvercloudDatabaseBackup' | cut -d' ' -f7": CmdOutput(
        out="/root/backup/CbisOvercloudDatabaseBackup.py"),
        "dirname /root/backup/CbisOvercloudDatabaseBackup.py": CmdOutput(out="mismatch/root/backup")}
    cmd_input_output_dict_unexpected_system_output = {
        "sudo crontab -l | grep 'CbisOvercloudDatabaseBackup' | cut -d' ' -f7": CmdOutput(
            out=""),
        "dirname /root/backup/CbisOvercloudDatabaseBackup.py": CmdOutput(out="mismatch/root/backup")}

    scenario_passed = [
        ValidationScenarioParams(
            scenario_title="runtime 'backup_nfs_mountpoint' match configured 'backup_nfs_mountpoint'",
            cmd_input_output_dict=cmd_input_output_dict_passed,
            additional_parameters_dict={"base_conf": base_conf})
    ]

    scenario_failed = [
        ValidationScenarioParams(
            scenario_title="runtime 'backup_nfs_mountpoint' not match configured 'backup_nfs_mountpoint'",
            cmd_input_output_dict=cmd_input_output_dict_failed,
            additional_parameters_dict={"base_conf": base_conf})
    ]

    scenario_unexpected_system_output = [
        ValidationScenarioParams(scenario_title="no data file",
                                 cmd_input_output_dict=cmd_input_output_dict_unexpected_system_output,
                                 additional_parameters_dict={"base_conf": base_conf})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_unexpected_system_output(self, scenario_params, tested_object)


class TestIsBackupMinuteCorrect(MockBaseUserConfigValidator):
    tested_type = IsBackupMinuteCorrect
    base_conf = {
        "CBIS": {"common": {"dns_servers": ["135.239.25.18", "135.239.25.17"], "time_zone": "UTC"},
                 "openstack_deployment": {"backup_minute": 0, "elk_disk": "sda"
                                          }}
    }

    cmd_input_output_dict_passed = {"sudo crontab -l | grep 'CbisOvercloudDatabaseBackup' | cut -d' ' -f1": CmdOutput(
        out="0")}
    cmd_input_output_dict_failed = {"sudo crontab -l | grep 'CbisOvercloudDatabaseBackup' | cut -d' ' -f1": CmdOutput(
        out="1")}
    cmd_input_output_dict_unexpected_system_output_empty = {
        "sudo crontab -l | grep 'CbisOvercloudDatabaseBackup' | cut -d' ' -f1": CmdOutput(
            out="")}
    cmd_input_output_dict_unexpected_system_output_str = {
        "sudo crontab -l | grep 'CbisOvercloudDatabaseBackup' | cut -d' ' -f1": CmdOutput(
            out="str")}
    cmd_input_output_dict_unexpected_system_output_float = {
        "sudo crontab -l | grep 'CbisOvercloudDatabaseBackup' | cut -d' ' -f1": CmdOutput(
            out="1.5")}

    scenario_passed = [
        ValidationScenarioParams(scenario_title="runtime 'backup_minute' match configured 'backup_minute'",
                                 cmd_input_output_dict=cmd_input_output_dict_passed,
                                 additional_parameters_dict={"base_conf": base_conf})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="runtime 'backup_minute' not match configured 'backup_minute'",
                                 cmd_input_output_dict=cmd_input_output_dict_failed,
                                 additional_parameters_dict={"base_conf": base_conf})
    ]

    scenario_unexpected_system_output = [
        ValidationScenarioParams(scenario_title="no backup_minute",
                                 cmd_input_output_dict=cmd_input_output_dict_unexpected_system_output_empty,
                                 additional_parameters_dict={"base_conf": base_conf}),
        ValidationScenarioParams(scenario_title="str backup_minute",
                                 cmd_input_output_dict=cmd_input_output_dict_unexpected_system_output_str,
                                 additional_parameters_dict={"base_conf": base_conf}),
        ValidationScenarioParams(scenario_title="float backup_minute",
                                 cmd_input_output_dict=cmd_input_output_dict_unexpected_system_output_float,
                                 additional_parameters_dict={"base_conf": base_conf})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_unexpected_system_output(self, scenario_params, tested_object)


class TestIsBackupHourCorrect(MockBaseUserConfigValidator):
    tested_type = IsBackupHourCorrect
    base_conf = {
        "CBIS": {"common": {"dns_servers": ["135.239.25.18", "135.239.25.17"], "time_zone": "UTC"},
                 "openstack_deployment": {"backup_hour": 2, "elk_disk": "sda"
                                          }}
    }

    cmd_input_output_dict_passed = {"sudo crontab -l | grep 'CbisOvercloudDatabaseBackup' | cut -d' ' -f2": CmdOutput(
        out="2")}
    cmd_input_output_dict_failed = {"sudo crontab -l | grep 'CbisOvercloudDatabaseBackup' | cut -d' ' -f2": CmdOutput(
        out="1")}
    cmd_input_output_dict_unexpected_system_output_empty = {
        "sudo crontab -l | grep 'CbisOvercloudDatabaseBackup' | cut -d' ' -f2": CmdOutput(
            out="")}
    cmd_input_output_dict_unexpected_system_output_str = {
        "sudo crontab -l | grep 'CbisOvercloudDatabaseBackup' | cut -d' ' -f2": CmdOutput(
            out="str")}
    cmd_input_output_dict_unexpected_system_output_float = {
        "sudo crontab -l | grep 'CbisOvercloudDatabaseBackup' | cut -d' ' -f2": CmdOutput(
            out="1.5")}

    scenario_passed = [
        ValidationScenarioParams(scenario_title="runtime 'backup_hour' match configured 'backup_hour'",
                                 cmd_input_output_dict=cmd_input_output_dict_passed,
                                 additional_parameters_dict={"base_conf": base_conf})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="runtime 'backup_hour' not match configured 'backup_hour'",
                                 cmd_input_output_dict=cmd_input_output_dict_failed,
                                 additional_parameters_dict={"base_conf": base_conf})
    ]

    scenario_unexpected_system_output = [
        ValidationScenarioParams(scenario_title="no backup_hour",
                                 cmd_input_output_dict=cmd_input_output_dict_unexpected_system_output_empty,
                                 additional_parameters_dict={"base_conf": base_conf}),
        ValidationScenarioParams(scenario_title="str backup_hour",
                                 cmd_input_output_dict=cmd_input_output_dict_unexpected_system_output_str,
                                 additional_parameters_dict={"base_conf": base_conf}),
        ValidationScenarioParams(scenario_title="float backup_hour",
                                 cmd_input_output_dict=cmd_input_output_dict_unexpected_system_output_float,
                                 additional_parameters_dict={"base_conf": base_conf})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_unexpected_system_output(self, scenario_params, tested_object)


class TestIsUndercloudCidrCorrect(MockBaseUserConfigValidator):
    tested_type = IsUndercloudCidrCorrect
    base_conf = {
        "CBIS": {"common": {"dns_servers": ["135.239.25.18", "135.239.25.17"], "time_zone": "UTC"},
                 "undercloud": {"server_cert": "util/server-cert.pem", "undercloud_cidr": "10.75.236.195/27"}}
    }

    cmd_input_output_dict_passed = {"/sbin/ip a l eth1 | grep 'inet '": CmdOutput(
        out="inet 10.75.236.195/27 brd 10.75.236.223 scope global noprefixroute eth1")}
    cmd_input_output_dict_failed = {"/sbin/ip a l eth1 | grep 'inet '": CmdOutput(
        out="inet 10.75.236.191/27 brd 10.75.236.223 scope global noprefixroute eth1")}

    scenario_passed = [
        ValidationScenarioParams(scenario_title="runtime 'undercloud_cidr' match configured 'undercloud_cidr'",
                                 cmd_input_output_dict=cmd_input_output_dict_passed,
                                 additional_parameters_dict={"base_conf": base_conf})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="runtime 'undercloud_cidr' not match configured 'undercloud_cidr'",
                                 cmd_input_output_dict=cmd_input_output_dict_failed,
                                 additional_parameters_dict={"base_conf": base_conf})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestIsGuestsMtuCorrect(MockBaseUserConfigValidator):
    tested_type = IsGuestsMtuCorrect
    base_conf = {
        "CBIS": {"common": {"dns_servers": ["135.239.25.18", "135.239.25.17"], "guests_mtu": 9000}}
    }
    cmd_input_output_dict_passed = {"cat /sys/class/net/eth0/mtu": CmdOutput(out="9000")}
    cmd_input_output_dict_passed_50 = {"cat /sys/class/net/eth0/mtu": CmdOutput(out="9050")}
    cmd_input_output_dict_failed = {"cat /sys/class/net/eth0/mtu": CmdOutput(out="1")}
    scenario_passed = [
        ValidationScenarioParams(scenario_title="runtime 'guests_mtu' match configured 'guests_mtu'",
                                 cmd_input_output_dict=cmd_input_output_dict_passed,
                                 additional_parameters_dict={"base_conf": base_conf}),
        ValidationScenarioParams(scenario_title="runtime 'guests_mtu' match configured 'guests_mtu'+50",
                                 cmd_input_output_dict=cmd_input_output_dict_passed_50,
                                 additional_parameters_dict={"base_conf": base_conf})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="runtime 'guests_mtu' not match configured 'guests_mtu'",
                                 cmd_input_output_dict=cmd_input_output_dict_failed,
                                 additional_parameters_dict={"base_conf": base_conf})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestIsHostUnderlayMtuCorrect(MockBaseUserConfigValidator):
    tested_type = IsHostUnderlayMtuCorrect
    base_conf = {
        "CBIS": {"common": {"dns_servers": ["135.239.25.18", "135.239.25.17"], "host_underlay_mtu": 9000}}
    }
    cmd_input_output_dict_passed = {"cat /sys/class/net/br-public/mtu": CmdOutput(out="9000")}
    cmd_input_output_dict_failed = {"cat /sys/class/net/br-public/mtu": CmdOutput(out="1")}
    scenario_passed = [
        ValidationScenarioParams(scenario_title="runtime 'host_underlay_mtu' match configured 'host_underlay_mtu'",
                                 cmd_input_output_dict=cmd_input_output_dict_passed,
                                 additional_parameters_dict={"base_conf": base_conf})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="runtime 'host_underlay_mtu' not match configured 'guests_mtu'",
                                 cmd_input_output_dict=cmd_input_output_dict_failed,
                                 additional_parameters_dict={"base_conf": base_conf})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestIsConfiguredVlansCorrect(MockBaseUserConfigValidator):
    tested_type = IsConfiguredVlansCorrect
    base_conf_20 = {
        "CBIS":
            {
                "common": {
                    "dns_servers": ["135.239.25.18", "135.239.25.17"], "host_underlay_mtu": 9000
                },
                "subnets":
                    {"__inline_sub1": "hw_common/provisioning_network_config",
                     "storage": {"pcp": "ref:common_network_config.pcp.storage", "vlan": 98,
                                 "network_address": "172.17.3.0/24", "mtu": "ref:common.host_underlay_mtu"},
                     "nuage_tenant_2": {"mtu": "ref:common.host_underlay_mtu"},
                     "provisioning": {"network_address": {
                         "list_join": ["/", ["{get_param: ControlPlaneIp}", "{get_param: ControlPlaneSubnetCidr}"]]},
                         "gateway": "127.0.0.1",
                         "mtu": "ref:common.host_underlay_mtu"},
                     "external": {"ip_range_start": "10.11.166.25", "ip_range_end": "10.11.166.62",
                                  "pcp": "ref:common_network_config.pcp.external", "vlan": 94,
                                  "network_address": "10.11.166.0/26", "gateway": "10.11.166.1",
                                  "mtu": "ref:common.host_underlay_mtu"},
                     "internal_api": {"pcp": "ref:common_network_config.pcp.internal_api", "vlan": 97,
                                      "network_address": "172.17.1.0/24", "mtu": "ref:common.host_underlay_mtu"},
                     "aux": {"mtu": "ref:common.host_underlay_mtu"},
                     "storage_mgmt": {"pcp": "ref:common_network_config.pcp.storage_mgmt", "vlan": 96,
                                      "network_address": "172.17.4.0/24", "mtu": "ref:common.host_underlay_mtu"},
                     "nuage_tenant": {"mtu": "ref:common.host_underlay_mtu"},
                     "tenant": {"pcp": "ref:common_network_config.pcp.tenant", "vlan": 95,
                                "network_address": "172.17.2.0/24", "mtu": "ref:common.host_underlay_mtu"},
                     "tenant_2": {"mtu": "ref:common.host_underlay_mtu"}}}}
    base_conf_22 = copy.deepcopy(base_conf_20)
    base_conf_22["CBIS"]["subnets"]["provisioning"]["vlan"] = None
    out_passed = """vlan94: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 9050
vlan9{}: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 9050
vlan9{}: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 9050
vlan97: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 9050
vlan98: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 9050"""
    cmd_input_output_dict_passed = {"sudo ifconfig -a | grep vlan": CmdOutput(out=out_passed.format("5", "6"))}
    cmd_input_output_dict_failed_1_not_match = {"sudo ifconfig -a | grep vlan": CmdOutput(out=out_passed.format("5",
                                                                                                                "2"))}
    cmd_input_output_dict_failed_2_not_match = {"sudo ifconfig -a | grep vlan": CmdOutput(out=out_passed.format("1",
                                                                                                                "2"))}
    scenario_passed = [
        ValidationScenarioParams(scenario_title="runtime 'vlans' match configured 'vlans' version=22", version=Version.V22,
                                 cmd_input_output_dict=cmd_input_output_dict_passed,
                                 additional_parameters_dict={"base_conf": base_conf_22}),
        ValidationScenarioParams(scenario_title="runtime 'vlans' match configured 'vlans' version=20", version=Version.V20,
                                 cmd_input_output_dict=cmd_input_output_dict_passed,
                                 additional_parameters_dict={"base_conf": base_conf_20})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="runtime 'vlans' 1 not match configured 'vlans' version=22", version=Version.V22,
                                 cmd_input_output_dict=cmd_input_output_dict_failed_1_not_match,
                                 additional_parameters_dict={"base_conf": base_conf_22}),
        ValidationScenarioParams(scenario_title="runtime 'vlans' 2 not match configured 'vlans' version=22", version=Version.V22,
                                 cmd_input_output_dict=cmd_input_output_dict_failed_2_not_match,
                                 additional_parameters_dict={"base_conf": base_conf_22}),
        ValidationScenarioParams(scenario_title="runtime 'vlans' 1 not match configured 'vlans' version=20", version=Version.V20,
                                 cmd_input_output_dict=cmd_input_output_dict_failed_1_not_match,
                                 additional_parameters_dict={"base_conf": base_conf_20}),
        ValidationScenarioParams(scenario_title="runtime 'vlans' 2 not match configured 'vlans' version=20", version=Version.V20,
                                 cmd_input_output_dict=cmd_input_output_dict_failed_2_not_match,
                                 additional_parameters_dict={"base_conf": base_conf_20})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

def mock_inet_pton(ipv6_cidr):
    if ipv6_cidr == '2a00:8a00:4000:d4a::':
        return '2A00:8A00:4000:0d4a::0'
    elif ipv6_cidr.startswith('2a17:8a00'):
        return '2a17:8a00:4000:d4a::'
    return ipv6_cidr

class TestIsConfiguredNetworkAddressCorrect(MockBaseUserConfigValidator):
    tested_type = IsConfiguredNetworkAddressCorrect
    base_conf = {
        "CBIS":
            {
                "common": {
                    "dns_servers": ["135.239.25.18", "135.239.25.17"], "host_underlay_mtu": 9000
                },
                "subnets":
                    {"__inline_sub1": "hw_common/provisioning_network_config",
                     "storage": {"pcp": "ref:common_network_config.pcp.storage", "vlan": 98,
                                 "network_address": "172.17.3.0/24", "mtu": "ref:common.host_underlay_mtu"},
                     "nuage_tenant_2": {"mtu": "ref:common.host_underlay_mtu"},
                     "provisioning": {"network_address": {
                         "list_join": ["/", ["{get_param: ControlPlaneIp}", "{get_param: ControlPlaneSubnetCidr}"]]},
                         "gateway": "127.0.0.1",
                         "mtu": "ref:common.host_underlay_mtu"},
                     "external": {"ip_range_start": "2A00:8A00:4000:0d4a::10", "ip_range_end": "2A00:8A00:4000:0d4a::20",
                                  "pcp": "ref:common_network_config.pcp.external", "vlan": 94,
                                  "network_address": "2A00:8A00:4000:0d4a::0/64", "gateway": "2A00:8A00:4000:0d4a::1",
                                  "mtu": "ref:common.host_underlay_mtu"},
                     "internal_api": {"pcp": "ref:common_network_config.pcp.internal_api", "vlan": 97,
                                      "network_address": "172.17.1.0/24", "mtu": "ref:common.host_underlay_mtu"},
                     "aux": {"mtu": "ref:common.host_underlay_mtu"},
                     "storage_mgmt": {"pcp": "ref:common_network_config.pcp.storage_mgmt", "vlan": 96,
                                      "network_address": "172.17.4.0/24", "mtu": "ref:common.host_underlay_mtu"},
                     "nuage_tenant": {"mtu": "ref:common.host_underlay_mtu"},
                     "tenant": {"pcp": "ref:common_network_config.pcp.tenant", "vlan": 95,
                                "network_address": "172.17.2.0/24", "mtu": "ref:common.host_underlay_mtu"},
                     "tenant_2": {"mtu": "ref:common.host_underlay_mtu"}}}}

    base_conf_25 = copy.deepcopy(base_conf)
    base_conf_25['CBIS']['subnets']['provisioning']['network_address'] = "'{{ ctlplane_ip }}/{{ ctlplane_subnet_cidr }}'"

    cmd_output_dict_passed = {
        "sudo ip route  | grep '.*vlan.*proto kernel scope link src' | grep -v docker | wc -l": CmdOutput(out="4"),
        "sudo ip route  | grep '.*vlan.*proto kernel scope link src' | grep -v docker | sed -n 1p ": CmdOutput(
            out="172.17.1.0/24 dev vlan97 proto kernel scope link src 172.17.1.13"),
        "sudo ip route  | grep '.*vlan.*proto kernel scope link src' | grep -v docker | sed -n 2p ": CmdOutput(
            out="172.17.2.0/24 dev vlan95 proto kernel scope link src 172.17.2.19"),
        "sudo ip route  | grep '.*vlan.*proto kernel scope link src' | grep -v docker | sed -n 3p ": CmdOutput(
            out="172.17.3.0/24 dev vlan98 proto kernel scope link src 172.17.3.14"),
        "sudo ip route  | grep '.*vlan.*proto kernel scope link src' | grep -v docker | sed -n 4p ": CmdOutput(
            out="172.17.4.0/24 dev vlan96 proto kernel scope link src 172.17.4.20"),
        "sudo ip -6 route  | grep '.*vlan.*proto kernel' | grep -v docker | grep -v fe80 | wc -l": CmdOutput(out='2'),
        "sudo ip -6 route  | grep '.*vlan.*proto kernel' | grep -v docker | grep -v fe80 | sed -n 1p ": CmdOutput(
            out="2a00:8a00:4000:d4a::10 dev vlan94 proto kernel metric 256 pref medium"),
        "sudo ip -6 route  | grep '.*vlan.*proto kernel' | grep -v docker | grep -v fe80 | sed -n 2p ": CmdOutput(
            out="2a00:8a00:4000:d4a::/64 dev vlan94 proto kernel metric 256 pref medium"),
    }

    cmd_input_output_dict_failed_1_not_match = {
        "sudo ip route  | grep '.*vlan.*proto kernel scope link src' | grep -v docker | wc -l": CmdOutput(out="4"),
        "sudo ip route  | grep '.*vlan.*proto kernel scope link src' | grep -v docker | sed -n 1p ": CmdOutput(
            out="172.17.1.0/24 dev vlan97 proto kernel scope link src 172.17.1.13"),
        "sudo ip route  | grep '.*vlan.*proto kernel scope link src' | grep -v docker | sed -n 2p ": CmdOutput(
            out="172.17.2.0/24 dev vlan95 proto kernel scope link src 172.17.2.19"),
        "sudo ip route  | grep '.*vlan.*proto kernel scope link src' | grep -v docker | sed -n 3p ": CmdOutput(
            out="172.17.3.0/24 dev vlan98 proto kernel scope link src 172.17.3.14"),
        "sudo ip route  | grep '.*vlan.*proto kernel scope link src' | grep -v docker | sed -n 4p ": CmdOutput(
            out="172.17.4.0/24 dev vlan96 proto kernel scope link src 172.17.4.20"),
        "sudo ip -6 route  | grep '.*vlan.*proto kernel' | grep -v docker | grep -v fe80 | wc -l": CmdOutput(out='2'),
        "sudo ip -6 route  | grep '.*vlan.*proto kernel' | grep -v docker | grep -v fe80 | sed -n 1p ": CmdOutput(
            out="2a17:8a00:4000:d4a::10 dev vlan94 proto kernel metric 256 pref medium"),
        "sudo ip -6 route  | grep '.*vlan.*proto kernel' | grep -v docker | grep -v fe80 | sed -n 2p ": CmdOutput(
            out="2a17:8a00:4000:d4a::/64 dev vlan94 proto kernel metric 256 pref medium"),
    }

    cmd_input_output_dict_failed_2_not_match = {
        "sudo ip route  | grep '.*vlan.*proto kernel scope link src' | grep -v docker | wc -l": CmdOutput(out="4"),
        "sudo ip route  | grep '.*vlan.*proto kernel scope link src' | grep -v docker | sed -n 1p ": CmdOutput(
            out="172.17.1.0/24 dev vlan97 proto kernel scope link src 172.17.1.13"),
        "sudo ip route  | grep '.*vlan.*proto kernel scope link src' | grep -v docker | sed -n 2p ": CmdOutput(
            out="172.17.5.0/24 dev vlan95 proto kernel scope link src 172.17.2.19"),
        "sudo ip route  | grep '.*vlan.*proto kernel scope link src' | grep -v docker | sed -n 3p ": CmdOutput(
            out="172.17.3.0/24 dev vlan98 proto kernel scope link src 172.17.3.14"),
        "sudo ip route  | grep '.*vlan.*proto kernel scope link src' | grep -v docker | sed -n 4p ": CmdOutput(
            out="172.17.4.0/24 dev vlan96 proto kernel scope link src 172.17.4.20"),
        "sudo ip -6 route  | grep '.*vlan.*proto kernel' | grep -v docker | grep -v fe80 | wc -l": CmdOutput(out='2'),
        "sudo ip -6 route  | grep '.*vlan.*proto kernel' | grep -v docker | grep -v fe80 | sed -n 1p ": CmdOutput(
            out="2a17:8a00:4000:d4a::10 dev vlan94 proto kernel metric 256 pref medium"),
        "sudo ip -6 route  | grep '.*vlan.*proto kernel' | grep -v docker | grep -v fe80 | sed -n 2p ": CmdOutput(
            out="2a00:8a00:4000:d4a::/64 dev vlan94 proto kernel metric 256 pref medium"),
    }

    scenario_passed = [
        ValidationScenarioParams(scenario_title="runtime 'network_addresses' match configured 'network_addresses'",
                                 cmd_input_output_dict=cmd_output_dict_passed,
                                 additional_parameters_dict={"base_conf": base_conf},
                                 library_mocks_dict={"PythonUtils.set_to_ipv6_format": Mock(side_effect=mock_inet_pton)}),
        ValidationScenarioParams(scenario_title="runtime 'network_addresses' match configured 'network_addresses' for CBIS 25",
                                 cmd_input_output_dict=cmd_output_dict_passed,
                                 additional_parameters_dict={"base_conf": base_conf_25},
                                 library_mocks_dict={"PythonUtils.set_to_ipv6_format": Mock(side_effect=mock_inet_pton)})
    ]

    scenario_failed = [
        ValidationScenarioParams(
            scenario_title="runtime 'network_addresses' not match configured 'network_addresses' 1 not match",
            version=Version.V22,
            cmd_input_output_dict=cmd_input_output_dict_failed_1_not_match,
            additional_parameters_dict={"base_conf": base_conf},
            library_mocks_dict={"PythonUtils.set_to_ipv6_format": Mock(side_effect=mock_inet_pton)}),
        ValidationScenarioParams(
            scenario_title="runtime 'network_addresses' not match configured 'network_addresses' 2 not match",
            version=Version.V22,
            cmd_input_output_dict=cmd_input_output_dict_failed_2_not_match,
            additional_parameters_dict={"base_conf": base_conf},
            library_mocks_dict={"PythonUtils.set_to_ipv6_format": Mock(side_effect=mock_inet_pton)})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)
