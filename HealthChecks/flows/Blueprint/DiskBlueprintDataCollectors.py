from __future__ import absolute_import
from flows.Blueprint.BlueprintDataCollectorsCommon import *
from six.moves import filter


class Disk(BlueprintDataCollector):
    REAL_DISKS_PREFIXES = ["sd", "nvme", "hd"]

    def get_system_ids(self):
        cmd = "sudo lsblk -d -o name,model"
        out = self.get_output_from_run_cmd(cmd, hosts_cached_pool=BlueprintDataCollector.cached_data_pool).splitlines()
        out = self.get_output_without_title(out, cmd)
        real_disks = list(filter(self._is_real_disk, out))

        return set([disk.split()[0] for disk in real_disks])

    def filter_real_disks_from_lshw(self, cmd):
        disks_json = self.get_lshw_json(classes_name_list=["storage", "disk", "volume"])
        res = []
        disks_info_list = []
        for disk in disks_json:
            if disk.get("id", "") == "nvme" and disk.get("logicalname"):
                disks_info_list.append(disk)
            elif disk.get("children"):
                for child_disk in disk.get("children"):
                    if "disk:" in child_disk.get("id", ""):
                        disks_info_list.append(child_disk)
        for disk in disks_info_list:
            if "Virtual" not in self.get_key_from_json(disk, "product", cmd):
                res.append(disk)
        return res

    def convert_name_to_lshw_id(self, disks_json, name):
        cmd = "sudo lshw -class disk -json"

        for disk_info in disks_json:
            if name in self.get_key_from_json(disk_info, "logicalname", cmd):
                return disk_info["id"]

        return None

    def get_output_without_title(self, output_lines, cmd):
        if len(output_lines) < 1:
            raise UnExpectedSystemOutput(self.get_host_ip(), cmd, output_lines, "Expected to get a table title.")

        return output_lines[1:]

    def get_name_val_from_lsblk_output(self, out):
        name_value = out.split(" ", 1)
        if len(name_value) == 1:
            return name_value, u"----"

        name, val = name_value

        if name not in self.get_ids():
            name = None

        return name, val

    def collect_lsblk_data(self, data_name, is_number=False, flags=None):
        cmd = "lsblk -d -o name,{}".format(data_name)
        if flags:
            cmd = cmd + " {}".format(flags)
        disks_info = self.get_output_from_run_cmd(
            cmd, hosts_cached_pool=BlueprintDataCollector.cached_data_pool).splitlines()
        disks_info = self.get_output_without_title(disks_info, cmd)
        res_dict = {}

        for info in disks_info:
            disk_name, disk_data = self.get_name_val_from_lsblk_output(info)
            if disk_name:
                if is_number:
                    if not disk_data.strip().isnumeric():
                        raise UnExpectedSystemOutput(self.get_host_ip(), cmd, info,
                                                     "Expected to get a number, got: {}.".format(disk_data))
                    disk_data = int(disk_data)
                else:
                    disk_data = disk_data.strip()
                res_dict[disk_name] = disk_data

        return res_dict

    def _is_real_disk(self, disk_data):
        return disk_data.startswith(tuple(self.REAL_DISKS_PREFIXES)) and "Virtual" not in disk_data


class DiskType(Disk):

    def get_blueprint_objective_key_name(self):
        return "Disk@type"

    def collect_blueprint_data(self, **kwargs):
        res_dict = self.collect_lsblk_data("rota", True)
        cmd = "sudo lsblk -d -o name,rota"

        for disk_name, type_number in list(res_dict.items()):
            type_str = self._convert_type_number_to_str(type_number, disk_name, cmd)
            res_dict[disk_name] = type_str

        return res_dict

    def _convert_type_number_to_str(self, type_number, disk_name, cmd):
        type_num_str = {1: "HDD", 0: "SSD"}
        type_str = type_num_str.get(type_number)
        if not type_str:
            raise UnExpectedSystemOutput(self.get_host_ip(), cmd, type_number,
                                         "Type number expected to be 0 or 1. but got: {}.".format(type_number))
        if type_str == "SSD":
            type_str = self._find_specific_ssd_type(disk_name)

        return type_str

    def _find_specific_ssd_type(self, disk_name):
        # If a disk has *old* indications of failure in its SMART log, a return code of 64 is provided.
        # Ignore return code to ignore old failures.
        cmd = "sudo smartctl -a /dev/{}".format(disk_name)
        _, out, _ = self.run_cmd(cmd, hosts_cached_pool=BlueprintDataCollector.cached_data_pool)

        if "Total NVM Capacity:" in out:
            return "NVMe"

        return "SSD"


class DiskModel(Disk):

    def get_blueprint_objective_key_name(self):
        return "Disk@model"

    def collect_blueprint_data(self, **kwargs):
        return self.collect_lsblk_data("model")


class DiskVendor(Disk):
    def get_blueprint_objective_key_name(self):
        return "Disk@vendor"

    def collect_blueprint_data(self, **kwargs):
        disks_model = self.collect_lsblk_data("model")
        disks_vendor = self.collect_lsblk_data("vendor")

        for disk_name, vendor in list(disks_vendor.items()):
            if vendor == "----":
                disks_vendor[disk_name] = disks_model[disk_name]

        return disks_vendor


class DiskSize(Disk):
    BYTES_IN_MB = 1024 ** 2

    def get_blueprint_objective_key_name(self):
        return "Disk@size_in_mb"

    def collect_blueprint_data(self, **kwargs):
        disks_sizes = self.collect_lsblk_data("size", True, "-b")

        for disk_name, size in list(disks_sizes.items()):
            disks_sizes[disk_name] = size / self.BYTES_IN_MB

        return disks_sizes


class DiskInterfaceType(Disk):
    def get_blueprint_objective_key_name(self):
        return "Disk@interface_type"

    def collect_blueprint_data(self, **kwargs):
        cmd = "sudo lshw -class storage -class disk -class volume"
        disks_json = self.filter_real_disks_from_lshw(cmd)
        disks_names = self.get_ids()
        res = {}

        for name in disks_names:
            res[name] = "----"
            for disk_info in disks_json:
                if name in self.get_key_from_json(disk_info, "logicalname", cmd):
                    res[name] = disk_info["description"]
        return res


class OperatingSystemDisk(BlueprintDataCollector):

    def get_system_ids(self):
        return {"disk used for / (root filesystem)"}

    def get_topic(self):
        return "operating_system_disk"

    @staticmethod
    def _get_separator():
        return ", "


class OperatingSystemDiskName(OperatingSystemDisk):

    def get_blueprint_objective_key_name(self):
        return self.get_topic() + "@name"

    def _parse_data(self, out):
        out_lines = [x.strip() for x in out.splitlines()]
        physical_disks, physical_disk = [], ""

        for line in out_lines:
            if line.endswith("disk"):   # physical drives do not have special chars at the beginning
                physical_disk = line.split()[0]
            if line.endswith("/") and physical_disk not in physical_disks:
                physical_disks.append(physical_disk)
                # due to lsblk cmd output, always shows up prior to its volumes and software raid devices

        return sorted(physical_disks)

    def collect_blueprint_data(self, **kwargs):
        cmd = "lsblk -n"
        out = self.get_output_from_run_cmd(cmd, hosts_cached_pool=BlueprintDataCollector.cached_data_pool)
        physical_disks = self._parse_data(out)
        return {os_id: self._get_separator().join(physical_disks) for os_id in self.get_ids()}


class OperatingSystemDiskTemplate(OperatingSystemDisk):

    def collect_blueprint_data(self, **kwargs):
        relevant_disks_dict = OperatingSystemDiskName(host_executor=self._host_executor).collect_blueprint_data()
        relevant_disks = list(relevant_disks_dict.values())[0].split(self._get_separator())
        disk_att_dict = eval(kwargs['class_to_use'] + '(host_executor=self._host_executor).collect_blueprint_data()')
        return {os_id: self._get_separator().join([str(disk_att_dict[disk]) for disk in relevant_disks]) for os_id in
                self.get_ids()}


class OperatingSystemDiskType(OperatingSystemDiskTemplate):

    def get_blueprint_objective_key_name(self):
        return self.get_topic() + "@type"

    def collect_blueprint_data(self, **kwargs):
        return super(OperatingSystemDiskType, self).collect_blueprint_data(class_to_use='DiskType')


class OperatingSystemDiskSize(OperatingSystemDiskTemplate):

    def get_blueprint_objective_key_name(self):
        return self.get_topic() + "@size_in_mb"

    def collect_blueprint_data(self, **kwargs):
        return super(OperatingSystemDiskSize, self).collect_blueprint_data(class_to_use='DiskSize')
