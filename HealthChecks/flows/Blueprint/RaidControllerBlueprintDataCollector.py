from __future__ import absolute_import
import re

from flows.Blueprint.BlueprintDataCollectorsCommon import BlueprintDataCollector
from flows.Blueprint.BlueprintInventory import BlueprintInventory
from tools.Exceptions import UnExpectedSystemOutput
from six.moves import range


class HwRaidControllerCmd(object):
    def __init__(self):
        self.regex_to_find_pci_address = None
        self.cmd_to_get_raid_data = None

    def get_val_from_list(self, found_list, cmd, expected_msg):
        if len(found_list) != 1:
            raise UnExpectedSystemOutput("", cmd, found_list, expected_msg)

        return found_list[0]

    def get_slot_location(self, raid_data):
        assert self.regex_to_find_pci_address, "Please add regex_to_find_pci_address to class."
        assert self.cmd_to_get_raid_data, "Please add cmd_to_get_raid_data to class."
        res_list = re.findall(self.regex_to_find_pci_address, raid_data)

        return self.get_val_from_list(res_list, self.cmd_to_get_raid_data,
                                      "Expected to get pci address in raid data.")


class HPRaidController(HwRaidControllerCmd):
    def __init__(self):
        super(HPRaidController, self).__init__()
        self.cmd_to_get_all_raid_controllers = "sudo ssacli ctrl all show"
        self.regex_to_find_slot_numbers = r"Slot (\d+)"
        self.cmd_to_get_raid_data = "sudo ssacli ctrl slot={slot} show"
        self.regex_to_find_pci_address = r"PCI Address .+\): (.+)"

    def get_slots_set(self, raid_data):
        slots = re.findall(self.regex_to_find_slot_numbers, raid_data)

        return {int(slot) for slot in slots}

    def get_product(self, raid_data):
        raid_lines = raid_data.strip().splitlines()

        if len(raid_lines) < 1:
            raise UnExpectedSystemOutput("", self.cmd_to_get_raid_data, raid_data,
                                         "Expected to get more than 1 data line")

        return raid_lines[0]

    def get_firmware(self, raid_data):
        regex_to_find_firmware = r"Firmware Version: (.+)"
        res_list = re.findall(regex_to_find_firmware, raid_data)

        return self.get_val_from_list(res_list, self.cmd_to_get_raid_data,
                                      "Expected to get Firmware Version: <firmware version>")


class AirframeRaidController(HwRaidControllerCmd):
    def __init__(self):
        super(AirframeRaidController, self).__init__()
        storcli64_paths = [
            'storcli64',
            '/opt/MegaRAID/storcli/storcli64',
            '/opt/hpe/storcli/storcli64'
        ]

        self.cmd_to_get_all_raid_controllers = " || ".join("sudo {} show".format(path) for path in storcli64_paths)
        self.regex_to_find_slot_numbers = r"Number of Controllers = (\d+)"
        self.cmd_to_get_raid_data = " || ".join("sudo {} /c{{slot}} show".format(path) for path in storcli64_paths)
        self.regex_to_find_pci_address = r"PCI Address = (.+)"

    def get_slots_set(self, raid_data):
        slots_num_list = re.findall(self.regex_to_find_slot_numbers, raid_data)
        slots_num = self.get_val_from_list(slots_num_list, self.cmd_to_get_all_raid_controllers,
                                           "Expected to get Number of Controllers = <number>")

        return {slot for slot in range(int(slots_num))}

    def get_product(self, raid_data):
        regex_to_find_product = r"Product Name = (.+)"
        res_list = re.findall(regex_to_find_product, raid_data)

        return self.get_val_from_list(res_list, self.cmd_to_get_raid_data,
                                      "Expected to get Product Name = <product name>")

    def get_firmware(self, raid_data):
        regex_to_find_firmware = r"FW Version = (.+)"
        res_list = re.findall(regex_to_find_firmware, raid_data)

        return self.get_val_from_list(res_list, self.cmd_to_get_raid_data,
                                      "Expected to get FW Version = <firmware version>")


# class DellRaidController(HwRaidControllerCmd):
#     def __init__(self):
#         super(DellRaidController, self).__init__()
#         self.cmd_to_get_all_raid_controllers = "lspci -nn | grep -i 'raid bus controller'"
#         self.regex_to_find_slot_numbers = r"\[([A-Za-z0-9]+:[A-Za-z0-9]+)\]"
#         self.cmd_to_get_raid_data = "sudo lspci -nn -k -d {slot}:"
#         self.regex_to_find_pci_address = r"(.+) RAID bus controller"
#
#     def get_slots_set(self, raid_data):
#         slots_names = re.findall(self.regex_to_find_slot_numbers, raid_data)
#         return set(slots_names)
#
#     def get_product(self, raid_data):
#         regex_to_find_product = r"Subsystem: (.+) \["
#         res_list = re.findall(regex_to_find_product, raid_data)
#
#         return self.get_val_from_list(res_list, self.cmd_to_get_raid_data,
#                                       "Expected to get Subsystem: <RAID Controller name>")
class DellRaidController(AirframeRaidController):
    pass


def get_hw_collector():
    hw_type = BlueprintInventory.get_hw_model_type()
    if "hp" in hw_type:
        return HPRaidController()
    if "airframe" in hw_type:
        return AirframeRaidController()
    if "dell" in hw_type:
        return DellRaidController()

    raise NotImplementedError("No implementation for hw type: {}".format(hw_type))


class RaidController(BlueprintDataCollector):
    _collector_by_hw = None

    def get_system_ids(self):
        ids, _ = self._collect_data(only_ids=True)
        return ids

    def get_raid_slots_numbers(self):
        return_code, raid_data, err = self.run_cmd(self._collector_by_hw.cmd_to_get_all_raid_controllers,
                                                   hosts_cached_pool=BlueprintDataCollector.cached_data_pool)

        if (not (return_code == 0 or return_code == 1) or
                (self._collector_by_hw.cmd_to_get_all_raid_controllers.count('||') + 1 == err.count('command not found'))):
            raise UnExpectedSystemOutput(self.get_host_ip(), self._collector_by_hw.cmd_to_get_all_raid_controllers,
                                         raid_data, "Return code: {}, err: {}".format(return_code, err))

        return self._collector_by_hw.get_slots_set(raid_data)

    def _collect_data(self, only_ids=False):
        if not self._collector_by_hw:
            self._collector_by_hw = get_hw_collector()
        slots_set = self.get_raid_slots_numbers()
        ids = set()
        res = {}

        for slot in slots_set:
            slot_data = self.get_output_from_run_cmd(self._collector_by_hw.cmd_to_get_raid_data.format(slot=slot),
                                                     hosts_cached_pool=BlueprintDataCollector.cached_data_pool)
            slot_location = self._collector_by_hw.get_slot_location(slot_data)
            ids.add(slot_location)
            if not only_ids:
                if isinstance(self, RaidControllerFirmware):    # RaidControllerFirmware class: get_firmware method
                    slot_property = self._collector_by_hw.get_firmware(slot_data)
                else:                                           # RaidControllerProduct class: get_product method
                    slot_property = self._collector_by_hw.get_product(slot_data)
                res[slot_location] = slot_property

        return ids, res

    def collect_blueprint_data(self, **kwargs):
        _, data = self._collect_data(only_ids=False)
        return data


class RaidControllerProduct(RaidController):

    def get_blueprint_objective_key_name(self):
        return "Raid Controller@product"


class RaidControllerFirmware(RaidController):

    def get_blueprint_objective_key_name(self):
        return "Raid Controller@firmware"
