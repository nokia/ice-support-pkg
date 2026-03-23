from __future__ import absolute_import
# implementation of data collectors
import warnings

from flows.Blueprint.BlueprintDataCollectorsCommon import *
from flows.HW.VCPU import CPU_affinity_base
import requests


class Processor(BlueprintDataCollector):
    ID_NAME = "Socket Designation"

    def get_system_ids(self):
        processors_info = self.get_real_cpu_entries()

        return set(
            [self.get_key_from_json(info, "Socket Designation", "sudo dmidecode") for info in processors_info])

    def get_real_cpu_entries(self):
        processors_info = self.get_dmidecode_json_by_type("processor", "Processor Information")

        return list([cpu_entry for cpu_entry in processors_info if cpu_entry.get("Status") != "Unpopulated"])


class ProcessorCurrentFrequency(Processor):

    def get_blueprint_objective_key_name(self):
        return "Processor@frequency_in_mhz"

    def collect_blueprint_data(self, **kwargs):
        cmd = "sudo dmidecode -t processor"
        processors_info = self.get_real_cpu_entries()
        speeds_with_mh_suffix = self.get_id_val_from_json_by_property(processors_info, self.ID_NAME,
                                                                      "Current Speed", "sudo dmidecode -t processor")
        res = self.set_dict_values_to_numeric(speeds_with_mh_suffix, 'speed', 'MHz', cmd)

        return res


# NumberOfPhysicalCoresPerProcessor not in use:
class NumberOfPhysicalCoresPerProcessor(Processor):

    def get_blueprint_objective_key_name(self):
        return "Processor@number_of_physical_cores_per_processor"

    def collect_blueprint_data(self, **kwargs):
        cmd = "lscpu | grep 'Core(s) per socket'"
        out = self.get_output_from_run_cmd(cmd, hosts_cached_pool=BlueprintDataCollector.cached_data_pool)
        num = self.split_result_from_output(cmd, out, is_number=True)[0]

        return {processor_id: int(num) for processor_id in self.get_ids()}


class NumberOfThreadsPerCore(Processor):

    def get_blueprint_objective_key_name(self):
        return "Processor@number_of_threads_per_core"

    def collect_blueprint_data(self, **kwargs):
        cmd = "lscpu |grep 'Thread(s) per core'"
        out = self.get_output_from_run_cmd(cmd, hosts_cached_pool=BlueprintDataCollector.cached_data_pool)
        num = self.split_result_from_output(cmd, out, is_number=True)[0]

        return {processor_id: int(num) for processor_id in self.get_ids()}


class ProcessorType(Processor):

    def get_blueprint_objective_key_name(self):
        return "Processor@type"

    def collect_blueprint_data(self, **kwargs):
        cmd = "lscpu | grep 'Model name'"
        out = self.get_output_from_run_cmd(cmd, hosts_cached_pool=BlueprintDataCollector.cached_data_pool)
        out = out.split('@')[0].strip()
        out_without_brackets = re.sub(r'\([^)]*\)','', out)
        model_name = self.split_result_from_output(cmd, out=out_without_brackets)[0]

        return {processor_id: model_name for processor_id in self.get_ids()}


class BIOS(BlueprintDataCollector):

    def get_system_ids(self):
        return {1}


class BIOSVersion(BIOS):

    def get_blueprint_objective_key_name(self):
        return "Bios@version"

    def collect_blueprint_data(self, **kwargs):
        cmd = "sudo dmidecode -s bios-version"
        bios_version = self.get_output_from_run_cmd(cmd, hosts_cached_pool=BlueprintDataCollector.cached_data_pool)

        return {bios_id: bios_version.strip() for bios_id in self.get_ids()}


class BIOSFirmware(BIOS):

    def get_blueprint_objective_key_name(self):
        return "Bios@firmware"

    def collect_blueprint_data(self, **kwargs):
        cmd = "sudo dmidecode --type bios | grep 'Firmware'"
        return_code, out, err = self.run_cmd(cmd, hosts_cached_pool=BlueprintDataCollector.cached_data_pool)
        if return_code != 0:
            cmd = "sudo ipmitool mc info | grep 'Firmware Revision'"
            out = self.get_output_from_run_cmd(cmd, hosts_cached_pool=BlueprintDataCollector.cached_data_pool)
        bios_firmware = self.split_result_from_output(cmd, out)

        return {bios_id: bios_firmware[0] for bios_id in self.get_ids()}


class BIOSRevision(BIOS):

    def get_blueprint_objective_key_name(self):
        return "Bios@revision"

    def collect_blueprint_data(self, **kwargs):
        bios_firmware = ['----']
        cmd = "sudo dmidecode --type bios | grep -i 'BIOS Revision'"
        return_code, out, err = self.run_cmd(cmd, hosts_cached_pool=BlueprintDataCollector.cached_data_pool)
        if return_code == 0:
            bios_firmware = self.split_result_from_output(cmd, out)

        return {bios_id: bios_firmware[0] for bios_id in self.get_ids()}


class BIOSReleaseDate(BIOS):

    def get_blueprint_objective_key_name(self):
        return "Bios@release-date"

    def collect_blueprint_data(self, **kwargs):
        cmd = "sudo dmidecode -s bios-release-date"
        bios_release_date = self.get_output_from_run_cmd(cmd, hosts_cached_pool=BlueprintDataCollector.cached_data_pool)

        return {bios_id: bios_release_date.strip() for bios_id in self.get_ids()}


########## SOUVIK DAS CODE STARTS   #############

class Memory(BlueprintDataCollector):
    def get_system_ids(self):
        memory_info = self.filter_valid_memory_from_dmidecode_json()

        return set([self.get_key_from_json(info, "Locator", "sudo dmidecode") for info in memory_info])
    
    def filter_valid_memory_from_dmidecode_json(self):
        dmidecode_json = self.get_dmidecode_json_by_type("memory", "Memory Device")
        res = []

        for memory_dict in dmidecode_json:
            if self.get_key_from_json(memory_dict, "Size", "dmidecode -t memory") != "No Module Installed":
                res.append(memory_dict)

        return res

    def get_memory_size(self):
        cmd = "sudo dmidecode -t memory"
        memory_info = self.filter_valid_memory_from_dmidecode_json()
        sizes_with_mb_suffix = self.get_id_val_from_json_by_property(memory_info, "Locator", "Size",
                                                                     "dmidecode -t memory")
        return self.set_dict_values_to_numeric(sizes_with_mb_suffix, 'size', 'MB', cmd)


class MemorySize(Memory):

    def get_blueprint_objective_key_name(self):
        return "Memory@size_in_mb"

    def collect_blueprint_data(self, **kwargs):
        return self.get_memory_size()


class MemoryType(Memory):

    def get_blueprint_objective_key_name(self):
        return "Memory@type"

    def collect_blueprint_data(self, **kwargs):
        memory_info = self.filter_valid_memory_from_dmidecode_json()
        return self.get_id_val_from_json_by_property(memory_info, "Locator", "Type", "dmidecode -t memory")


class MemorySpeed(Memory):

    def get_blueprint_objective_key_name(self):
        return "Memory@speed_in_mhz"

    def collect_blueprint_data(self, **kwargs):
        cmd = "sudo dmidecode -t memory"
        memory_info = self.filter_valid_memory_from_dmidecode_json()
        speeds_with_mts_suffix = self.get_id_val_from_json_by_property(memory_info, "Locator", "Speed",
                                                                       "dmidecode -t memory")
        res = self.set_dict_values_to_numeric(speeds_with_mts_suffix, 'speed', 'MT/s', cmd)

        return res


class MemoryTotalSize(Memory):

    def get_system_ids(self):
        return {'Total of all units'}

    def get_blueprint_objective_key_name(self):
        return "Total memory@total_size_in_mb"

    def collect_blueprint_data(self, **kwargs):
        id_memory_size_dict = self.get_memory_size()
        total_size = sum(id_memory_size_dict.values())

        return {id_: total_size for id_ in self.get_ids()}
############ SOUVIK DAS CODE ENDS ##################


class OperatingSystemVersion(BlueprintDataCollector):
    def get_system_ids(self):
        return {1}

    def get_blueprint_objective_key_name(self):
        return "Operating system@version"

    def collect_blueprint_data(self, **kwargs):
        cmd = "cat /etc/redhat-release"
        out = self.get_output_from_run_cmd(cmd, hosts_cached_pool=BlueprintDataCollector.cached_data_pool)

        return {os_id: out for os_id in self.get_ids()}


class KernelVersion(BlueprintDataCollector):
    def get_system_ids(self):
        return {1}

    def get_blueprint_objective_key_name(self):
        return "Kernel@version"

    def collect_blueprint_data(self, **kwargs):
        out = self.get_output_from_run_cmd("uname -r",
                                           hosts_cached_pool=BlueprintDataCollector.cached_data_pool).rstrip()

        return {kernel_id: out for kernel_id in self.get_ids()}


class IsolatedCPU(CPU_affinity_base):
    def set_document(self):
        self._unique_operation_name = "dummy_validation_to_get_cpu_data"
        self._title = "dummy validation to get cpu data"
        self._failed_msg = ""
        self._severity = Severity.NOTIFICATION


class CpuIsolated(BlueprintDataCollector):
    objective_hosts = {Deployment_type.CBIS: [Objectives.COMPUTES],
                       Deployment_type.NCS_OVER_BM: [Objectives.WORKERS, Objectives.EDGES]}

    def get_system_ids(self):
        return {1}

    def get_blueprint_objective_key_name(self):
        return "CPU@isolated"

    def collect_blueprint_data(self):
        cpu_data_getter = IsolatedCPU(self._host_executor)

        return {id_: cpu_data_getter.get_host_isolated_scheme() for id_ in self.get_ids()}


class RedfishVersion(BlueprintDataCollector):
    def get_system_ids(self):
        return {1}

    def get_blueprint_objective_key_name(self):
        return "Redfish@version"

    def _get_host_ipmi(self):
        info_table = self.get_dict_from_command_output('sudo ipmitool lan print', 'space', custom_delimiter=':')
        return info_table.get('IP Address')

    def _get_redfish_api_version(self, host_ipmi):
        url = "https://{}/redfish".format(host_ipmi)
        payload = {}
        headers = {}

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                response = requests.request("GET", url, headers=headers, data=payload, verify=False, timeout=30)
                api_version = None

                if response.status_code == 200:
                    response_dict = json.loads(response.text)
                    api_version = list(response_dict.keys())[0]
        except:
            api_version = None
        return api_version

    def collect_blueprint_data(self, **kwargs):
        redfish_version = None
        host_ipmi = self._get_host_ipmi()
        redfish_api_version = self._get_redfish_api_version(host_ipmi)
        if redfish_api_version:
            url = "https://{}/redfish/{}/".format(host_ipmi, redfish_api_version)
            payload = {}
            headers = {}

            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    response = requests.request("GET", url, headers=headers, data=payload, verify=False, timeout=30)
                    redfish_version = "----"

                    if response.status_code == 200:
                        response_dict = json.loads(response.text)
                        redfish_version = response_dict.get("RedfishVersion")
            except Exception as e:
                raise UnExpectedSystemOutput(self.get_host_ip(), "send get request to {}".format(url), output=str(e))

        return {redfish_id: redfish_version for redfish_id in self.get_ids()}


