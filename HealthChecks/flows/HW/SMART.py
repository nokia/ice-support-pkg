from __future__ import absolute_import
from HealthCheckCommon.operations import *
import re

from HealthCheckCommon.validator import InformatorValidator
from tools.Exceptions import *
from six.moves import range
from six.moves import zip


class IsSmartTestPassed(InformatorValidator):
    objective_hosts = [Objectives.STORAGE, Objectives.CONTROLLERS, Objectives.COMPUTES, Objectives.ALL_NODES,Objectives.MAINTENANCE]

    def set_document(self):
        self._unique_operation_name = "is_smart_test_passed"
        self._title = "Check if smart test passed"
        self._title_of_info = "Is S.M.A.R.T passed"
        self._failed_msg = "TBD"
        self._severity = Severity.WARNING
        self._is_pure_info = False
        self._system_info = ""
        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.ACTIVE_PROBLEM]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def get_device_dict(self):
        exit, output, error = self.run_cmd("lsscsi | grep -i disk")
        output_split = output.split()
        output_split_length = len(output_split)
        lsscsi_dict = {}
        drives = []
        hw_model = []
        for num in range(0, output_split_length):
            if 'disk' in output_split[num]:
                drives.append(output_split[num + 1])
            elif 'dev' in output_split[num]:
                hw_model.append(output_split[num])

        lsscsi_dict = dict(list(zip(hw_model, drives)))

        device_result_dict = {}
        megaraid_number = None
        exit_code, out, err = self.run_cmd("sudo smartctl --scan")
        if out:
            megaraid_number_list = re.findall(r'megaraid,\d+', out)
            if megaraid_number_list:
                megaraid_number = megaraid_number_list[0].split(',')[1]

            device_lines = re.findall(r"\/dev\/\w+\s+-d\s\w+", out)
            for device_line in device_lines:
                device_name, device_type = re.split(r"\s+-d\s+", device_line)
                if device_name and "bus" not in device_name:
                    if 'nvme' not in device_name:
                        if megaraid_number and device_type == 'scsi' and lsscsi_dict[device_name] != 'ATA':
                           device_result_dict[device_name] = 'megaraid,{}'.format(megaraid_number)
                        else:
                            device_result_dict[device_name] = 'auto'
                    else:
                        device_result_dict[device_name] = 'auto'
        else:
            exit_code, out, err = self.run_cmd("lsblk -ndp --output NAME")
            devices_list = out.splitlines()
            for dev in devices_list:
                device_result_dict[dev] = 'scsi'
        return device_result_dict

    def is_device_passed(self, device_name, device_type):
        cmd = "sudo smartctl -a {device_name} -d {device_type} ".format(
            device_name=device_name, device_type=device_type)
        exit_code, out, err = self.run_cmd(cmd)
        if not out:
            message = "no output from cmd\n{}".format(err or "")
            raise UnExpectedSystemOutput(self.get_host_name(), message, out)
        if not bool(re.search(r"SMART\s+support\s+is:\s+Enabled", out)):
            return None, "smartctl utility is not supported on device {}".format(device_name)
        result = re.findall(r"Health\s+Status:\s+\w+|test\s+result:\s+\w+", out)
        if not len(result):
            raise UnExpectedSystemOutput(self.get_host_name(), 'no health status in output', out)
        is_passed = bool(re.search(r"PASSED|OK", result[0]))
        test_result_str = None
        if not is_passed:
            test_result_str = out.split("=== START OF READ SMART DATA SECTION ===")[1]
        return is_passed, test_result_str

    def get_list_of_devices_status(self):
        un_supported_devices = []
        failed_devices = []
        device_dict = self.get_device_dict()
        for device_name in device_dict:
            device_type = device_dict[device_name]
            is_passed, message = self.is_device_passed(device_name, device_type)
            if is_passed is False:
                failed_devices.append("Device Name: {}\nMore info:{}\n".format(device_name, message))
            elif is_passed is None:
                if 'nvme' not in device_name:
                   un_supported_devices.append(device_name)
        return device_dict ,failed_devices, un_supported_devices


    def is_validation_passed(self):
        device_dict ,failed_devices,un_supported_devices = self.get_list_of_devices_status()
        self._system_info = failed_devices
        self._failed_msg = ""
        if len(failed_devices):
            self._severity = Severity.CRITICAL
            self._failed_msg += "Failed devices were detected on this node:\n{}".format(
                "\n".join(failed_devices))
            return False
        return True

class IsSmartEnabled(IsSmartTestPassed):
    def set_document(self):
        self._unique_operation_name = "is_smart_test_enable"
        self._title = "Check if smart test enable on all disks"
        self._title_of_info = "Is S.M.A.R.T enabled"
        self._failed_msg = "TBD"
        self._is_pure_info = True
        self._system_info = ""

    def get_system_info(self):
        device_dict, failed_devices, devices_not_enabled = self.get_list_of_devices_status()
        self._system_info = "S.M.A.R.T is not supported or not enabled on devices: {}".format(devices_not_enabled)
        return self._system_info


