from __future__ import absolute_import
import pytest
import warnings

from flows.HW.HW_validations import CheckDiskUsage, HwSysClockCompare, ValidateDiskSpace, ValidateOsDiskOnSDA, ValidateSharedMountsSize
from tests.pytest.pytest_tools.operator.test_operator import CmdOutput
from tests.pytest.pytest_tools.operator.test_validation_base import ValidationTestBase, ValidationScenarioParams
from tests.pytest.tools.versions_alignment import Mock

from tools.global_enums import Objectives


class TestCheckDiskUsage(ValidationTestBase):
    tested_type = CheckDiskUsage

    out_fmt = '''Filesystem      Size  Used Avail Use%% Mounted on
    /dev/sda1        19G  %.1fG  %.1fG  {usage}% /home
    tmpfs           3.9G     0  3.9G   0% /dev/shm
    /dev/sdb1       1.8T  1.6T   87G  50% /data
    '''

    out_fmt_with_efivarfs = '''Filesystem      Size  Used Avail Use%% Mounted on
    /dev/sda1        19G  %.1fG  %.1fG  {usage}% /home
    tmpfs           3.9G     0  3.9G   0% /dev/shm
    /dev/sdb1       1.8T  1.6T   87G  50% /data
    efivarfs        100K  100K   0K  100% /sys/firmware/efi/efivars
    '''

    scenario_passed = [
        ValidationScenarioParams("usage 70", {'df -h': CmdOutput(out=out_fmt.format(usage=70))}),
        ValidationScenarioParams("usage 80", {'df -h': CmdOutput(out=out_fmt.format(usage=80))}),
        ValidationScenarioParams("usage 70 with efivarfs at 100%", {'df -h': CmdOutput(out=out_fmt_with_efivarfs.format(usage=70))})
    ]

    scenario_failed = [
        ValidationScenarioParams("usage 90", {'df -h': CmdOutput(out=out_fmt.format(usage=90))}),
        ValidationScenarioParams("usage 100", {'df -h': CmdOutput(out=out_fmt.format(usage=100))})
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


class TestValidateHwSysClockCompare(ValidationTestBase):
    tested_type = HwSysClockCompare

    scenario_passed = [
        ValidationScenarioParams(scenario_title="Clocks synced up to 1 sec - hwclock using ISO 8601 format",
                                 tested_object_mock_dict={
                                     "_get_hw_clock": Mock(return_value="2024-02-08 18:12:44.404676+00:00"),
                                     "_get_sys_clock": Mock(return_value="2024-02-08 18:11:48 +0000"),
                                 }),
        ValidationScenarioParams(scenario_title="Clocks synced up to 1 hour GMT-05- hwclock using ISO 8601 format",
                                 tested_object_mock_dict={
                                     "_get_hw_clock": Mock(return_value="2024-02-08 17:12:44.404676-05:00"),
                                     "_get_sys_clock": Mock(return_value="2024-02-08 18:11:48 -0500"),
                                 }),
        ValidationScenarioParams(scenario_title="Clocks synced up to 1 sec - hwclock using format 1",
                                 tested_object_mock_dict={
                                     "_get_hw_clock": Mock(return_value="Thu Feb  8 18:12:44 2024"),
                                     "_get_sys_clock": Mock(return_value="2024-02-08 18:11:48 +0000"),
                                 }),
        ValidationScenarioParams(scenario_title="Clocks synced up to 1 sec - hwclock using format 2",
                                 tested_object_mock_dict={
                                     "_get_hw_clock": Mock(return_value="Thu 08 Feb 2024 06:11:30 PM UTC"),
                                     "_get_sys_clock": Mock(return_value="2024-02-08 18:11:48 +0000"),
                                 }),
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="Clocks not synced - hwclock using ISO 8601 format",
                                 tested_object_mock_dict={
                                     "_get_hw_clock": Mock(return_value="2000-01-01 00:00:01.000000+00:00"),
                                     "_get_sys_clock": Mock(return_value="2024-02-08 18:11:48 +0000"),
                                 }),
        ValidationScenarioParams(scenario_title="Clocks not synced - hwclock using format 1",
                                 tested_object_mock_dict={
                                     "_get_hw_clock": Mock(return_value="Thu Feb  8 18:12:44 2020"),
                                     "_get_sys_clock": Mock(return_value="2024-02-08 18:11:48 +0000"),
                                 }),
        ValidationScenarioParams(scenario_title="Clocks not synced - hwclock using format 2",
                                 tested_object_mock_dict={
                                     "_get_hw_clock": Mock(return_value="Thu 08 Feb 2024 06:11:30 PM UTC"),
                                     "_get_sys_clock": Mock(return_value="2020-02-08 18:11:48 +0000"),
                                 }),
    ]

    scenario_unexpected_system_output = [
        ValidationScenarioParams(scenario_title="Wrong hwclock format - Empty string",
                                 tested_object_mock_dict={
                                     "_get_hw_clock": Mock(return_value=""),                                    # NOK
                                     "_get_sys_clock": Mock(return_value="2024-02-08 18:11:48 +0000"),          # OK
                                 }),
        ValidationScenarioParams(scenario_title="Wrong hwclock format - Wrong string",
                                 tested_object_mock_dict={
                                     "_get_hw_clock": Mock(return_value="Thu Feb  8 18:12:44 2024  -0.922926 seconds"),
                                     "_get_sys_clock": Mock(return_value="2024-02-08 18:11:48 +0000"),          # OK
                                 }),
    ]
    # Wrong 'date' format should never happen since we are directly stating the format we want.
    # The same can't be done on 'hwclock' utility though.

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_unexpected_system_output(self, scenario_params, tested_object)

class TestValidateDiskSpace(ValidationTestBase):
    tested_type = ValidateDiskSpace

    out1 = '''Filesystem      Size  Used Avail Use%% Mounted on
    /dev/vda3        59G  10G  {}G  40% /
    '''

    out2 = '''Filesystem      Size  Used Avail Use%% Mounted on
        /dev/vda10        229G     10G  {}G   0% /var
        '''

    out3 = '''Filesystem      Size  Used Avail Use%% Mounted on
        /dev/vda6        20G   7G  {}G  50% /tmp
        '''

    out4 = '''Filesystem      Size  Used Avail Use%% Mounted on
        /root/backup    889G    563G    {}G    64% /mnt/backup
        '''

    out5 = '''Filesystem      Size  Used Avail Use%% Mounted on
            /dev/vda5    40G    20G    {}G    64% /home
            '''

    out6 = '''Filesystem      Size  Used Avail Use%% Mounted on
            /dev/vda3    59G    34G    {}G    58% /.
            '''
    scenario_passed = [
        ValidationScenarioParams("HYP / available disk space", {'df -h -B G /': CmdOutput(out=out1.format('380'))},
                                 tested_object_mock_dict={"get_host_roles": Mock(return_value={Objectives.HYP})}),
        ValidationScenarioParams("UC available disks spaces", {'df -h -B G /': CmdOutput(out=out1.format('50')),
                                                               'df -h -B G /var': CmdOutput(out=out2.format('50')),
                                                               'df -h -B G /tmp': CmdOutput(out=out3.format('10')),
                                                               'df -h -B G /mnt/backup': CmdOutput(out=out4.format('380')),
                                                               'df -h -B G /home': CmdOutput(out=out5.format('10')),
                                                               'df -h -B G /srv': CmdOutput(out=out6.format('31'))},
                                 tested_object_mock_dict={"get_host_roles": Mock(return_value={Objectives.UC})})
    ]

    scenario_failed = [
        ValidationScenarioParams("HYP / no available disk space",
                                 {'df -h -B G /': CmdOutput(out=out1.format('38'))},
                                 tested_object_mock_dict={"get_host_roles": Mock(return_value={Objectives.HYP})}),
        ValidationScenarioParams("UC one disk has no space",
                                 {'df -h -B G /': CmdOutput(out=out1.format('50')),
                                  'df -h -B G /var': CmdOutput(out=out2.format('40')),
                                  'df -h -B G /tmp': CmdOutput(out=out3.format('10')),
                                  'df -h -B G /mnt/backup': CmdOutput(out=out4.format('380')),
                                  'df -h -B G /home': CmdOutput(out=out5.format('30')),
                                  'df -h -B G /srv': CmdOutput(out=out6.format('20'))},
                                 tested_object_mock_dict={"get_host_roles": Mock(return_value={Objectives.UC})}),
        ValidationScenarioParams("UC all disks have no space",
                                 {'df -h -B G /': CmdOutput(out=out1.format('5')),
                                  'df -h -B G /var': CmdOutput(out=out2.format('4')),
                                  'df -h -B G /tmp': CmdOutput(out=out3.format('1')),
                                  'df -h -B G /mnt/backup': CmdOutput(out=out4.format('38')),
                                  'df -h -B G /home': CmdOutput(out=out5.format('3')),
                                  'df -h -B G /srv': CmdOutput(out=out6.format('43'))},
                                 tested_object_mock_dict={"get_host_roles": Mock(return_value={Objectives.UC})})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestOsDiskOnSDA(ValidationTestBase):
    tested_type = ValidateOsDiskOnSDA
    cmd_root = "lsblk -o NAME,MOUNTPOINT | grep ' /$'"

    cmd_sda_partitions = "lsblk -no NAME /dev/sda"
    sda_partitions_output = """sda.
        sda1.
        sda2.
          md127.
            md127p1.
             vg_root-_data0.
            md127p2.
            md127p3.
"""

    scenario_passed = [
        ValidationScenarioParams("disk sda", {cmd_root: CmdOutput(out="sda2             /"),
                                              cmd_sda_partitions: CmdOutput(out=sda_partitions_output)}),
        ValidationScenarioParams("raid", {cmd_root: CmdOutput(out="md127p2             /"),
                                              cmd_sda_partitions: CmdOutput(out=sda_partitions_output)}),
        ValidationScenarioParams("logical volume", {cmd_root: CmdOutput(out="vg_root-_data0             /"),
                                              cmd_sda_partitions: CmdOutput(out=sda_partitions_output)})
    ]

    scenario_failed = [
        ValidationScenarioParams("disk sdb", {cmd_root: CmdOutput(out="sdb4             /"),
                                              cmd_sda_partitions: CmdOutput(out=sda_partitions_output)})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestValidateSharedMountsSize(ValidationTestBase):
    tested_type = ValidateSharedMountsSize

    out_fmt = '''Filesystem      Size  Used Avail Use%% Mounted on
    /opt/management        {size}G  10G  50G  40% /
    '''
    cmd = "df -h -B G {}".format("/opt/management")

    scenario_passed = [
        ValidationScenarioParams("size 100", {cmd: CmdOutput(out=out_fmt.format(size=100))}),
        ValidationScenarioParams("size > 100", {cmd: CmdOutput(out=out_fmt.format(size=180))})
    ]

    scenario_failed = [
        ValidationScenarioParams("usage 90", {cmd: CmdOutput(out=out_fmt.format(size=50))})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)
