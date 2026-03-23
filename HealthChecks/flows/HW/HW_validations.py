from __future__ import absolute_import
import json
import re
import tools.sys_parameters as gs
from tools.global_enums import Version
from HealthCheckCommon.validator import Validator
from tools.global_enums import Objectives, BlockingTag, Severity, ImplicationTag, Deployment_type
from datetime import timedelta
import dateutil.parser
from tools.date_and_time_utils import parse
from tools.Exceptions import UnExpectedSystemOutput
from tools.python_utils import PythonUtils
from six.moves import range

class CheckDiskUsage(Validator):
    objective_hosts = [Objectives.COMPUTES, Objectives.STORAGE, Objectives.ALL_NODES, Objectives.MAINTENANCE]
    THRESHOLD_WARN = 80
    THRESHOLD_ERR = 90

    def set_document(self):
        self._unique_operation_name = "is_disk_space_sufficient"
        self._title = "Verify disk space usage on computes and storage nodes"
        self._failed_msg = "disk usage warning: "
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.RISK_RESOURCE_CLEANING_RECOMMENDED, ImplicationTag.PRE_OPERATION, ImplicationTag.APPLICATION_DOMAIN]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        return_code, out, err = self.run_cmd("df -h")
        disk_space_usage = re.findall(r'(\S+).*\s+([0-9]+)%.*', out)
        result = True
        for disk in disk_space_usage:
            # Ignore efivarfs virtual disk
            if "efivarfs" in disk[0]:
                continue
            usage = int(disk[1])
            if usage > CheckDiskUsage.THRESHOLD_ERR:
                self._severity = Severity.ERROR
                self._failed_msg = self._failed_msg + "Note: {} usage is {}%. (threshold error is {})\n".format(
                    disk[0], usage, CheckDiskUsage.THRESHOLD_ERR)
                self._implication_tags.append(ImplicationTag.ACTIVE_PROBLEM)
                result = False
            elif usage > CheckDiskUsage.THRESHOLD_WARN:
                self._failed_msg = self._failed_msg + "Warning {} usage is {}%. (threshold warning is {})\n".format(
                    disk[0], usage, CheckDiskUsage.THRESHOLD_WARN)
                result = False
        return result


class CheckDiskUsageOnCriticalObjectives(CheckDiskUsage):
    objective_hosts = [Objectives.CONTROLLERS, Objectives.UC]

    def set_document(self):
        CheckDiskUsage.set_document(self)
        self._unique_operation_name = "is_disk_space_sufficient_on_critical_objectives"
        self._title = "Verify disk space usage on UC and controllers"
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]
        self._severity = Severity.WARNING


class BasicFreeMemoryValidation(Validator):
    objective_hosts = [Objectives.COMPUTES, Objectives.STORAGE, Objectives.ALL_NODES,Objectives.MAINTENANCE]

    THRESHOLD_RATIO = 0.15
    HIGH_PAGE_THRESHOLD_RATIO = 0.01

    def set_document(self):
        self._unique_operation_name = "basic_memory_validation"
        self._title = "Validate that the free memory in the system is more than 15%  on computes and storage nodes"
        self._failed_msg = "free memory is less than 15%"
        self._severity = Severity.WARNING

        self._implication_tags = [ImplicationTag.RISK_RESOURCE_CLEANING_RECOMMENDED, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.UPGRADE]

    def is_validation_passed(self):
        mem_total_cmd = "cat /proc/meminfo |grep MemTotal"
        mem_avi_cmd = "cat /proc/meminfo |grep MemAvailable"
        mem_total = float(self.run_and_get_the_nth_field(mem_total_cmd, 2))
        mem_avi = float(self.run_and_get_the_nth_field(mem_avi_cmd, 2))
        ratio = mem_avi / mem_total

        huge_pages_total_cmd = "cat /proc/meminfo |grep HugePages_Total"
        huge_pages_total = float(self.run_and_get_the_nth_field(huge_pages_total_cmd, 2))

        if ratio < self.THRESHOLD_RATIO:
            # test if it is due to HugePages

            huge_pages_free_cmd = "cat /proc/meminfo |grep HugePages_Free"
            huge_pages_free = float(self.run_and_get_the_nth_field(huge_pages_free_cmd, 2))

            if huge_pages_total > 0:
                huge_pages_ratio = huge_pages_free / huge_pages_total
                if huge_pages_ratio < self.HIGH_PAGE_THRESHOLD_RATIO:
                    self._failed_msg = "Available memory is only {}% and Free HugePages memory is only {}% ".format(
                        ratio * 100, huge_pages_ratio * 100)
                    return False
            else:
                self._failed_msg = "Available memory is only {}%".format(ratio * 100)
                return False

        return True


class BasicFreeMemoryValidationOnCriticalObjectives(BasicFreeMemoryValidation):
    objective_hosts = [Objectives.CONTROLLERS, Objectives.UC]

    def set_document(self):
        BasicFreeMemoryValidation.set_document(self)
        self._unique_operation_name = "basic_memory_validation_on_critical_objectives"
        self._title = "Validate that the free memory in the system is more than 15% on UC and controllers"
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]
        self._severity = Severity.ERROR


class CpuUsageValidation(Validator):
    objective_hosts = {Deployment_type.CBIS: [Objectives.CONTROLLERS, Objectives.STORAGE, Objectives.COMPUTES],
                       Deployment_type.NCS_OVER_BM: [Objectives.ALL_NODES]}

    def set_document(self):
        self._unique_operation_name = "cpu_usage_validation"
        self._title = "Validate that the idle cpu in the system is more than 25%"
        self._failed_msg = "idle cpu is less than 25%"
        self._severity = Severity.ERROR
        self._is_clean_cmd_info = True
        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.PERFORMANCE]
        self._blocking_tags = [BlockingTag.UPGRADE]

    def is_validation_passed(self):
        #Only checking idle cpu of host cpu's in compute nodes, Incase of cpu pinned to VM's overall idle cpu will be generally low for those cpu's.
        if Objectives.COMPUTES in self.get_host_roles():
            host_cpu_cmd = "sudo cat /etc/systemd/system.conf |grep -i 'CPUAffinity' | grep -v ^#"
            out = self.get_output_from_run_cmd(host_cpu_cmd).strip()
            cpus = []
            for cpu in out.split('=')[1].split():
                cpus.append(int(cpu))
            cpus_overload = []
            for cpu_number in cpus:
                cpu_idle_cmd = "sudo sar -u 2 1 -P {} | grep -i average ".format(cpu_number)
                cpu_idle = float(self.run_and_get_the_nth_field(cpu_idle_cmd, 8))
                cpus_overload.append(cpu_idle)
            avg_idle_cpu = sum(cpus_overload) / len(cpus_overload)
            if avg_idle_cpu < 25.0:
                self._failed_msg = "Average Idle cpu is only {:.2f}% for host CPU's".format(avg_idle_cpu)
                return False
            return True

        cpu_idle_cmd = "sudo sar -u 2 1 | grep -i average "
        cpu_idle_total = float(self.run_and_get_the_nth_field(cpu_idle_cmd, 8))

        if cpu_idle_total < 25.0:
            self._failed_msg = "Idle cpu is only {}%".format(cpu_idle_total)
            return False
        return True


class TempValidation(Validator):
    objective_hosts = {Deployment_type.CBIS: [Objectives.CONTROLLERS, Objectives.STORAGE, Objectives.COMPUTES,Objectives.MAINTENANCE],
                       Deployment_type.NCS_OVER_BM: [Objectives.ALL_NODES]}

    def set_document(self):
        self._unique_operation_name = "temp_validation"
        self._title = "Validate that the temperature of HW components are in a good state"
        self._failed_msg = "high temperature detected"
        self._severity = Severity.CRITICAL

        self._implication_tags = [ImplicationTag.PERFORMANCE, ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        # todo - check
        temp_cmd = "sudo ipmitool sdr elist full | grep -i degrees"
        exit_code, out, err = self.run_cmd(temp_cmd, timeout=30)
        result_dict = {}
        out_lines = out.splitlines()
        for line in out_lines:
            line_split = line.split('|')
            tmp_phrase = line_split[4].strip()
            temperature_value = tmp_phrase.split()[0]
            # temperature_value = int(filter(None, line_split[4].split(' '))[0])
            component_name_value = line_split[0].strip()
            status_value = line_split[2].strip()
            # status_value = str(filter(None, line_split[2].split(' '))[0])
            if status_value != 'ok':
                result_dict[component_name_value] = temperature_value
        bad_list = [key + ": " + str(result_dict[key]) for key in result_dict]
        if len(bad_list):
            self._failed_msg = "Based on the system configuration the high temperature detected on the following" \
                               " components: \n\n{}".format("\n".join(bad_list))
            return False
        return True


class CPUfreqScalingGovernorValidation(Validator):
    objective_hosts = {Deployment_type.CBIS: [Objectives.CONTROLLERS, Objectives.STORAGE, Objectives.COMPUTES,Objectives.MAINTENANCE],
                       Deployment_type.NCS_OVER_BM: [Objectives.ALL_NODES]}

    def set_document(self):
        self._unique_operation_name = "cpu_configuration_speed_validation"
        self._title = "Validate CPU governor it configure for performance"
        self._failed_msg = "CPU Governor not set to PERFORMANCE"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.PERFORMANCE]

    def is_validation_passed(self):
        lscpu = self.get_output_from_run_cmd("sudo /bin/lscpu|grep '^CPU(s):'").strip()
        total_cpus = lscpu.split(":")[1].strip()
        i = 0
        error_flag = 0
        for i in range(0, int(total_cpus)):
            cmd1 = "sudo cat /sys/devices/system/cpu/cpu"
            cmd2 = "/cpufreq/scaling_governor"
            cmd = cmd1 + str(i) + cmd2
            return_code, cpu_governor_output, err = self.run_cmd(cmd)
            if return_code == 0:
                if (cpu_governor_output.strip().upper()) == "PERFORMANCE":
                    pass
                else:
                    error_flag = error_flag + 1
                    self._failed_msg = self._failed_msg + "\nCPU" + str(i) + " -> " + cpu_governor_output.strip()
            else:
                pass
        if int(error_flag) == 0:
            return True
        else:
            return False


class DmidecodeOrIpmitool(Validator):
    def dmidecode_or_ipmitool(self):
        out = self.get_output_from_run_cmd("sudo dmidecode | grep -A3 '^System Information' | tail -n 3")
        if 'To be filled by O.E.M' in out:
            return_code, out, err = self.run_cmd('sudo ipmitool fru')
        return out


class CpuSpeedValidation(DmidecodeOrIpmitool):  # deprecated as mustly return false
    objective_hosts = {Deployment_type.CBIS: [Objectives.CONTROLLERS, Objectives.STORAGE, Objectives.COMPUTES,Objectives.MAINTENANCE],
                       Deployment_type.NCS_OVER_BM: [Objectives.ALL_NODES]}

    def set_document(self):
        self._unique_operation_name = "cpu_speed_validation"
        self._title = "Validate that the All CPU's are configured with High performance"
        self._failed_msg = "Some CPU are not running on maximum speed. \n " \
                           "please note that the compute is not configured with maximum performance and there for \n" \
                           "we might be facing performance impact on the VM's/containers that are hosted in this " \
                           "compute \n"

        self._severity = Severity.WARNING

        self._implication_tags = [ImplicationTag.PERFORMANCE]

    def is_prerequisite_fulfilled(self):
        out = self.dmidecode_or_ipmitool()
        return not ('Gen10' in out and 'HP' in out)

    def _get_cpupower_max_speed(self):
        max_cpu_speed_cmd = 'cpupower frequency-info |grep "hardware limits"'
        ret, out_speed, err = self.run_cmd(max_cpu_speed_cmd)
        # expect to return something like 'hardware limits: 1.60 GHz - 2.67 GHz'

        if ret != 0:
            return None

        if 'Not Available' in out_speed:
            return None

        out_speed = out_speed.split('-')[1]  # [".."," 2.67 GHz"]
        out_speed = out_speed.strip().split()  # [2.67,GHz]
        if out_speed[1].lower() == "ghz":
            # convert GHZ into MHZ
            max_cpu_speed = float(out_speed[0]) * 1000
        elif out_speed[1].lower() == "mhz":
            max_cpu_speed = float(out_speed[0])
        else:
            raise UnExpectedSystemOutput(self.get_host_ip(),
                                         max_cpu_speed_cmd, out_speed, "expected here GHZ or MHZ")

        return max_cpu_speed

    def _get_max_cpu_from_name(self):
        max_cpu_speed_cmd = "cat /proc/cpuinfo | grep -i 'model name' | head -n 1"
        max_cpu_speed = self.run_and_get_the_nth_field(max_cpu_speed_cmd, 2, separator='@')
        max_cpu_speed = max_cpu_speed.strip()
        # convert GHZ into MHZ
        max_cpu_speed = max_cpu_speed.lower().replace('ghz', "")
        max_cpu_speed = float(max_cpu_speed) * 1000
        return max_cpu_speed

    def _get_max_speed(self):
        max_speed = self._get_cpupower_max_speed()
        if max_speed is None:  # in case driver is not set
            max_speed = self._get_max_cpu_from_name()

        return max_speed

    def is_validation_passed(self):
        max_cpu_speed = self._get_max_speed()
        cpu_speed_current_cmd = "cat /proc/cpuinfo | grep -ie mhz"
        # get the speeds
        out_speed = self.get_output_from_run_cmd(cpu_speed_current_cmd)

        # get the processor id
        cpu_processor_current_cmd = "cat /proc/cpuinfo | grep -ie processor"
        out_processor = self.get_output_from_run_cmd(cpu_processor_current_cmd)

        speed_lines = out_speed.splitlines()
        processor_lines = out_processor.splitlines()
        processor_ids = [line.split(":")[1] for line in processor_lines]

        index = 0
        bad_list = []

        for line in speed_lines:
            line_split = line.split(':')
            cpu_speed = float(line_split[1].strip())
            if (max_cpu_speed - cpu_speed) > 10:  # less then 10 MHZ diff can be becouse of units diffrent
                # If the cpu is more then the max cpu speed - it can be explain by turbo
                # which is allowed
                bad_list.append("CPU ID with processor id {} has speed of {} ".format(processor_ids[index], cpu_speed))
            index = index + 1

        if len(bad_list):
            self._failed_msg = "thThe following CPU not running at maximum speed: {} \n\n{}".format(max_cpu_speed,
                                                                                                    "\n".join(bad_list))
            return False
        return True


class ValidateRaidModeSettings(DmidecodeOrIpmitool):
    objective_hosts = {Deployment_type.CBIS: [Objectives.CONTROLLERS, Objectives.COMPUTES, Objectives.STORAGE, Objectives.MAINTENANCE]}
    warning_msg = None
    warning_result = None

    def set_document(self):
        self._unique_operation_name = "validate_mode_with_raid_controllers"
        self._title = "Validate mode with RAID controllers"
        self._failed_msg = ""
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]

    def is_prerequisite_fulfilled(self):
        out = self.dmidecode_or_ipmitool()
        out_dict = PythonUtils.get_dict_from_string(out, 'space', custom_delimiter=':')
        return '/AF' in out_dict['Product Name']

    def is_validation_passed(self):
        is_raid = self.run_cmd_return_is_successful(cmd="sudo lspci | grep LSI")
        if "storage" in self.get_host_name().lower():
            result = self.validate_storage_settings_mode(is_raid=is_raid)
        else:
            result = self.validate_controller_and_compute_settings_mode(is_raid=is_raid)
        if result is not None:
            return result
        self.set_failed_msg_by_expected_result()
        return self.compare_expected_results_with_storcli_result()

    def validate_controller_and_compute_settings_mode(self, is_raid):
        if is_raid:
            if self.run_cmd_return_is_successful('sudo ipmitool fru print | grep AR-D52B'):
                self.expected_result = 'RWBD'
            else:
                self.expected_result = 'RWTD'
        else:
            return True

    def validate_storage_settings_mode(self, is_raid):
        if self.run_cmd_return_is_successful('sudo ipmitool fru print | grep AR-D52BQ1'):
            if is_raid:
                self.expected_result = 'RWBD'
            else:
                self._failed_msg = "RM18 and RM19 required raid controller on storage"
                self._severity = Severity.ERROR
                return False
        elif is_raid:
            self.expected_result = 'RWTD'
        else:
            return True

    def set_failed_msg_by_expected_result(self):
        if self.expected_result == 'RWTD':
            self._failed_msg = "No Super capacitor exist"
            self._severity = Severity.WARNING
        if self.expected_result == 'RWBD':
            self.warning_result = 'NRWBD'
            self.warning_msg = " {} is not recommended".format(self.warning_result)
            self._failed_msg = "Super capacitor exist"
            self._severity = Severity.WARNING

    def compare_expected_results_with_storcli_result(self):
        storcli64 = 'storcli64'
        if gs.get_version() < Version.V24:
            storcli64 = '/opt/MegaRAID/storcli/storcli64'
        cmd = "sudo {} /call show j".format(storcli64)
        storcli_result = self.get_output_from_run_cmd(cmd=cmd)
        storcli_result_dict = json.loads(storcli_result)
        unexpected_mode_list = []
        warning_mode_list = []
        for controller in storcli_result_dict['Controllers']:
            if 'VD LIST' in list(controller['Response Data'].keys()):
                for item in controller['Response Data']['VD LIST']:
                    if item['Cache'] != self.expected_result:
                        if self.warning_result and item['Cache'] == self.warning_result:
                            warning_mode_list.append(item['Cache'])
                        else:
                            unexpected_mode_list.append(item['Cache'])
        if len(unexpected_mode_list) == 0:
            self._severity = Severity.WARNING
        if len(unexpected_mode_list) > 0 or len(warning_mode_list) > 0:
            self._failed_msg = self._failed_msg + ", Wrong cache setting: {}, Expected cache setting: {}.".format(
                unexpected_mode_list + warning_mode_list, self.expected_result)
            if len(warning_mode_list) > 0:
                self._failed_msg = self._failed_msg + self.warning_msg
            return False
        return True


class HwSysClockCompare(Validator):
    '''
    This validation compares the hwclock date/time with the system date/time. If there is a significant difference it
    fails the validation.
    The hwclock tool returns the RTC time in the same time zone as the system, so there is no need to handle time zone
    separately.
    '''
    objective_hosts = {Deployment_type.CBIS: [Objectives.HYP, Objectives.CONTROLLERS, Objectives.STORAGE,
                                              Objectives.COMPUTES, Objectives.MONITOR],
                       Deployment_type.NCS_OVER_BM: [Objectives.ALL_NODES]}
    CRITERIA = timedelta(seconds=3600)
    HWCLOCK_CMD = "sudo hwclock"
    SYSCLOCK_CMD = "date +'%Y-%m-%d %H:%M:%S %z'"

    def set_document(self):
        self._unique_operation_name = "hw_sys_clock_compare"
        self._title = "Compare hwclock with system clock"
        self._msg = "This validation verifies if HW clock and System clock are reasonably close.\n"
        self._failed_msg = ""
        self._severity = Severity.NOTIFICATION
        self._implication_tags = [ImplicationTag.NOTE]
        self._blocking_tags = []

    def _get_hw_clock(self):
        '''
        Formats that need to work:
        ISO 8601 format e.g.: 2024-02-08 18:12:44.404676-05:00
        older formats:
            Thu Feb  8 18:12:44 2024  -0.922926 seconds
            Thu 08 Feb 2024 07:43:25 PM UTC  -0.047875 seconds
        '''
        hw_clock_output = self.get_output_from_run_cmd(self.HWCLOCK_CMD, message="hwclock cmd failed to be executed")
        try:
            hw_clock_output = hw_clock_output.splitlines()[0]
        except (IndexError, TypeError) as e:
            raise UnExpectedSystemOutput(self.get_host_ip(), cmd=self.HWCLOCK_CMD, output=hw_clock_output,
                                         message="No lines on the command output.\n{}".format(e.message))

        if 'seconds' in hw_clock_output:                                # non ISO 8601 format
            hw_clock_output = ' '.join(hw_clock_output.split()[:-2])    # remove microseconds not recognized by parser
        return hw_clock_output

    def _get_sys_clock(self):
        sys_clock_output = self.get_output_from_run_cmd(self.SYSCLOCK_CMD, message="date cmd failed to be executed.")
        try:
            sys_clock_output = sys_clock_output.splitlines()[0]
        except (IndexError, TypeError) as e:
            raise UnExpectedSystemOutput(self.get_host_ip(), cmd=self.SYSCLOCK_CMD, output=sys_clock_output,
                                         message="No lines on the command output.\n{}".format(e.message))

        return sys_clock_output

    def _convert_str_to_datetime(self, string_datetime, cmd=""):
        try:
            datetime_obj = parse(string_datetime)
        except (ValueError, dateutil.parser.ParserError) as e:
            raise UnExpectedSystemOutput(self.get_host_ip(), cmd=cmd, output=string_datetime,
                                         message="Date/time could not be parsed.\n{}".format(str(e)))
        return datetime_obj

    @staticmethod
    def _get_delta_of_datetime(date1, date2):
        if date1 > date2:
            return date1 - date2
        return date2 - date1

    @staticmethod
    def _fix_tz(hw_clock, sys_clock):
        '''In some cases, the hwclock output format doesn't contain the timezone,
        in that case take the TZ from the system clock'''
        if hw_clock.tzinfo is None and sys_clock.tzinfo is not None:
            hw_clock = hw_clock.replace(tzinfo=sys_clock.tzinfo)
        return hw_clock

    def is_validation_passed(self):
        hw_clock = self._convert_str_to_datetime(self._get_hw_clock(), self.HWCLOCK_CMD)
        sys_clock = self._convert_str_to_datetime(self._get_sys_clock(), self.SYSCLOCK_CMD)
        hw_clock = self._fix_tz(hw_clock, sys_clock)

        hw_sys_delta = self._get_delta_of_datetime(hw_clock, sys_clock)
        if hw_sys_delta > self.CRITERIA:
            self._failed_msg += "There is a significant difference between the hw clock (RTC) and the system clock.\n" \
                                 "HW Clock:     {}\nSystem Clock: {}\nCriteria: {} seconds\n" \
                .format(hw_clock, sys_clock, self.CRITERIA.total_seconds())
            return False
        return True

class ValidateDiskSpace(Validator):
    objective_hosts = {Deployment_type.CBIS: [Objectives.HYP, Objectives.ALL_HOSTS]}

    def set_document(self):
        self._unique_operation_name = "validate_available_disk_space_for_upgrade"
        self._title = "validate there are enough space for upgrade"
        self._failed_msg = "Don't have enough space for upgrade."
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.UPGRADE]


    def is_validation_passed(self):
        REQUIRED_SPACE_PER_ROLE_GB = {
            Objectives.HYP: [{"path": "/", "space": 370}],
            Objectives.UC: [
                {"path": "/", "space": 30},
                {"path": "/var", "space": 45},
                {"path": "/home", "space": 5},
                {"path": "/tmp", "space": 8},
                {"path": "/mnt/backup", "space": 370},
                {"path": "/srv", "space":30},
            ],
            Objectives.DPDK_COMPUTES: [{"path": "/", "space": 16}],
            Objectives.CONTROLLERS: [{"path": "/tmp", "space": 12}],
            Objectives.STORAGE: [{"path": "/tmp", "space": 12}],
            Objectives.COMPUTES: [{"path": "/tmp", "space": 12}],
            Objectives.MONITOR: [{"path": "/tmp", "space": 12}],
        }
        flg_has_enough_space = True
        role_types = self.get_host_roles()
        for role in role_types:
            if role in REQUIRED_SPACE_PER_ROLE_GB:
                path_space_pairs = REQUIRED_SPACE_PER_ROLE_GB[role]
                for config in path_space_pairs:
                    path = config["path"]
                    space = config["space"]
                    cmd = "df -h -B G {}".format(path)
                    out = self.get_output_from_run_cmd(cmd)
                    lines = out.strip().split('\n')
                    if len(lines) != 2:
                        raise UnExpectedSystemOutput(self.get_host_ip(),
                                                     cmd, out, "expected two lines")

                    if len (lines[1].split()) != 6:
                        raise UnExpectedSystemOutput(self.get_host_ip(),
                                                     cmd, out, "expected 6 words")

                    disk_space_available_g = lines[1].split()[3]
                    disk_space_available = int(disk_space_available_g.rstrip('G'))

                    if disk_space_available < space:
                        flg_has_enough_space = False
                        self._failed_msg += ("\nNeed to free space in path {} -"
                                                               " available space is {}G,"
                                                               " required space is {}G,"
                                                               " for host of role {} \n").format(path,
                                                                                                 disk_space_available,
                                                                                                 space,
                                                                                                 role)
        return flg_has_enough_space


class ValidateOsDiskOnSDA(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ALL_NODES],
        Deployment_type.CBIS: [Objectives.CONTROLLERS, Objectives.COMPUTES, Objectives.STORAGE]
    }

    def set_document(self):
        self._unique_operation_name = "os_disk_matches"
        self._title = "Check if OS root disk is installed on sda"
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._failed_msg = "Chosen Operating System disk mismatch found!!! \n " \
                           "When a wrong disk is used for the OS, it might represent a problem, specially in storage nodes.\n" \
                           "This misconfiguration can result to a failed upgrade, " \
                           "as the OS root disk will be erased during the disk-wiping task in the upgrade of storage nodes.\n"
        self._severity = Severity.ERROR
        self._blocking_tags = [BlockingTag.UPGRADE]

    def is_validation_passed(self):
        cmd_root = "lsblk -o NAME,MOUNTPOINT | grep ' /$'"
        root_output = self.get_output_from_run_cmd(cmd_root).strip()

        if not root_output:
            self._failed_msg += "OS root filesystem is not mounted."
            return False

        root_device = root_output.split()[0]

        cmd_sda_partitions = "lsblk -no NAME /dev/sda"
        sda_partitions_output = self.get_output_from_run_cmd(cmd_sda_partitions).strip().splitlines()
        sda_partitions_output = [partition.strip().rstrip('.') for partition in sda_partitions_output]

        if root_device in sda_partitions_output:
            return True
        else:
            self._failed_msg += "OS root filesystem is mounted on {} and it's not a partition of sda.".format(root_device)
            return False

class ValidateSharedMountsSize(Validator):
    objective_hosts = {Deployment_type.NCS_OVER_BM: [Objectives.ONE_MANAGER]}

    def set_document(self):
        self._unique_operation_name = "validate_right_disk_size_for_shared_directories"
        self._title = "validate the size of shared directories"
        self._failed_msg = "For a successful upgrade/manager_replacement the shared directories size should be increased to at least 100GB."
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = []


    def is_validation_passed(self):
        """
        Validate that /opt/management filesystem SIZE >= 100G (GiB-ish as reported by df -B G).
        """

        path = "/opt/management"
        required_size = 100

        flg_has_enough_size = True

        cmd = "df -h -B G {}".format(path)
        out = self.get_output_from_run_cmd(cmd)

        lines = out.strip().split("\n")
        if len(lines) != 2:
            raise UnExpectedSystemOutput(self.get_host_ip(), cmd, out, "expected two lines")

        cols = lines[1].split()
        if len(cols) != 6:
            raise UnExpectedSystemOutput(self.get_host_ip(), cmd, out, "expected 6 words")

        # df columns: Filesystem Size Used Avail Use% Mounted_on
        size_g_str = cols[1]  # <-- SIZE column
        if not size_g_str.endswith("G"):
            raise UnExpectedSystemOutput(
                self.get_host_ip(), cmd, out, "expected size in 'G', got {size_g_str}"
            )

        try:
            size_gb = int(size_g_str.rstrip("G"))
        except ValueError:
            raise UnExpectedSystemOutput(
                self.get_host_ip(), cmd, out, "failed to parse size field: {size_g_str}"
            )

        if size_gb < required_size:
            flg_has_enough_size = False
            self._failed_msg += (
                "\nShared mount {path} is too small - "
                "size is {size_gb}G, required size is {required_size}G\n"
            )

        return flg_has_enough_size



