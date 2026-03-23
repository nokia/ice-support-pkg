from __future__ import absolute_import
import json
import os

import tools.user_params
from flows.OpenStack.Vms import VmsInfoFlow
from flows.OpenStack.Vms.VmsInfoInformators import VmsVcpuInfo
from flows.HW.VCPU import CPU_affinity_base
from flows_of_sys_operations.sys_data_collector.collector import FilesCollector, ZipTarFile, FilesCollectorPreFlow
from tools.global_enums import Deployment_type, Objectives, Severity
from tools.global_logging import log_and_print


class TelemetryCollectorPreFlow(FilesCollectorPreFlow):
    def init_validations(self):
        super(TelemetryCollectorPreFlow, self).init_validations()
        FilesCollector.ICE_COLLECTOR_FILE_MANE = "telemetry_collector.ice.tar"
        FilesCollector.COLLECTOR_TGZ_FILE_MANE = "{}.gz".format(FilesCollector.ICE_COLLECTOR_FILE_MANE)
        FilesCollector.collector_path = os.path.join(FilesCollector.FINAL_TAR_GZ_FOLDER,
                                                     FilesCollector.COLLECTOR_TGZ_FILE_MANE)


class IsolatedCPU(CPU_affinity_base):
    def set_document(self):
        self._unique_operation_name = "dummy_validation_to_get_cpu_data"
        self._title = "dummy validation to get cpu data"
        self._failed_msg = ""
        self._severity = Severity.NOTIFICATION


class AppendSarFilesToTar(FilesCollector):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.ALL_HOSTS, Objectives.HYP],
        Deployment_type.NCS_OVER_BM: [Objectives.ALL_NODES, Objectives.MANAGERS],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ALL_NODES, Objectives.MANAGERS]
    }

    def set_document(self):
        self._unique_operation_name = "append_sar_files_to_tar_file"
        self._title = "Append SAR files to tar"
        self._failed_msg = "Failed to append SAR files to the tar file"
        self._run_in_parallel = True
        self._prerequisite_unique_operation_name = "create_tar_file"
        self._printable_title = 'Collecting SAR files from each host'

    def run_system_operation(self):
        sar_dir = os.path.join(FilesCollector.working_dir, "sar")
        self.safe_run_cmd("sudo mkdir -m 777 -p {}".format(sar_dir))
        tar_name = self.get_tar_name()
        files_to_append = []

        collect_sar_commands_dict = {
            "all_cpu": "sadf -d -- -P ALL",
            "network": "sadf -d -- -n DEV",
            "memory": "sadf -d -- -r",
            "sys_load": "sadf -d -- -q",
            "disk": "sadf -d -- -d",
            "swap": "sadf -d -- -S",
            "ram": "sadf -d -- -r",
            "huge": "sadf -d -- -H",
            "disk_io_usage": "sadf -d -- -p -d",
            "interface_pack_drop": "sadf -d -- -n EDEV",
            "interface_incoming_or_outgoing": "sadf -d -- -n DEV",
            "cached_entries": "sadf -d -- -v"
        }

        if Objectives.COMPUTES in self.get_host_roles():
            sar_cmd_for_isolated_cpu = self._get_sar_cmd_for_isolated_cpu()
            if sar_cmd_for_isolated_cpu:
                collect_sar_commands_dict["isolated_cpu"] = sar_cmd_for_isolated_cpu
        cpu_used_by_vm_cmd = None

        if tools.user_params.vms_info_path:
            vm_to_cpu_dict = self._get_vm_to_cpu_dict()

            cpu_used_by_vm_cmd = self._get_sar_cmd_for_cpu_used_by_vm(vm_to_cpu_dict)
            if cpu_used_by_vm_cmd:
                collect_sar_commands_dict["cpu_used_by_vm"] = cpu_used_by_vm_cmd

        if not cpu_used_by_vm_cmd:
            log_and_print("{} - Not collecting cpu that used by VM SAR data - No VMs data".format(self.get_host_ip()))

        if tools.user_params.sar_file or tools.user_params.sar_date:
            self._add_path_to_sar_commands(collect_sar_commands_dict)

        for sar_type, sar_cmd in list(collect_sar_commands_dict.items()):
            sar_path = os.path.join(sar_dir, "{}.sar.csv".format(sar_type))
            create_sar_cmd = "{} > {}".format(sar_cmd, sar_path)
            return_code, out, err = self.run_sudo_cmd(create_sar_cmd, timeout=60)
            if return_code != 0:
                self._failed_msg = "Failed to generate '{}' using command '{}'".format(sar_path, sar_cmd)
                return False
            files_to_append.append(sar_path)

        self.run_cmd(
            # give priority to others
            'nice -n 4 sudo tar --append -v --file {} -C {} sar'.format(tar_name, FilesCollector.working_dir),
            timeout=300)

        for one_file in files_to_append:
            FilesCollector.all_added_files[self.get_host_name()].append(one_file)

        return True

    def _add_path_to_sar_commands(self, collect_sar_commands_dict):
        sar_date_file_full_path = ""

        if tools.user_params.sar_date:
            sar_date_file_full_path = self._get_sar_date_file_path()
        if tools.user_params.sar_file:
            sar_date_file_full_path = tools.user_params.sar_file

        for sar_type, sar_cmd in list(collect_sar_commands_dict.items()):
            collect_sar_commands_dict[sar_type] = sar_cmd + " " + sar_date_file_full_path

    def _get_sar_date_file_path(self):
        sa_path = "/var/log/sa/"
        sysstat_path = "/var/log/sysstat/"

        if self.file_utils.is_file_exist(sa_path):
            sar_data_path = sa_path
        else:
            self.file_utils.verify_file_exists(sysstat_path)
            sar_data_path = sysstat_path
        sar_data_file = "sa0{}".format(tools.user_params.sar_date) if tools.user_params.sar_date < 10 else "sa{}".format(
            tools.user_params.sar_date)
        sar_date_file_full_path = os.path.join(sar_data_path, sar_data_file)
        self.file_utils.verify_file_exists(sar_date_file_full_path)

        return sar_date_file_full_path

    def _get_sar_cmd_for_cpu_used_by_vm(self, vm_to_cpu_dict):
        cpu_numbers = []

        for vm_data in list(vm_to_cpu_dict.values()):
            for cpu in vm_data:
                cpu_numbers.append(cpu["cpu"])

        return self._get_sar_cpu_cmd_by_cpu_list(cpu_numbers)

    def _get_sar_cmd_for_isolated_cpu(self):
        cpu_data_getter = IsolatedCPU(self._host_executor)
        cpu_list = cpu_data_getter.get_host_isolated_scheme()

        return self._get_sar_cpu_cmd_by_cpu_list(cpu_list)

    def _get_sar_cpu_cmd_by_cpu_list(self, cpu_list):
        if cpu_list:
            cpu_numbers_str = ",".join([str(cpu) for cpu in cpu_list])

            return "sadf -d -P {}".format(cpu_numbers_str)

        log_and_print("{} - Failed to collect isolated cpu data.".format(self.get_host_ip()))
        return None

    def _get_vm_to_cpu_dict(self):
        with open(tools.user_params.vms_info_path) as f:
            vms_info = json.load(f)

        for flow in vms_info:
            if flow.get("command_name") == VmsInfoFlow.flow_name:
                for hostname, vms_data in list(flow.get("details", {}).items()):
                    if self.get_host_name() in hostname:
                        vcpu_info = vms_data.get("info_" + VmsVcpuInfo.info_name, {})
                        return self._get_vm_to_cpu_numbers(vcpu_info)

        return {}

    def _get_vm_to_cpu_numbers(self, vcpu_data):
        system_info = vcpu_data.get("system_info", {})
        res = {}

        for vm_id, vm_data in list(system_info.items()):
            res[vm_id] = []
            cpu_list = vm_data.get("result", [])
            if cpu_list != "---":
                for cpu in cpu_list:
                    res[vm_id].append({"cpu": cpu["CPU"], "virtual_name": cpu["VCPU"]})

        return res


class ZipSarTarFile(ZipTarFile):
    def set_document(self):
        super(ZipSarTarFile, self).set_document()
        self._prerequisite_unique_operation_name = "append_sar_files_to_tar_file"
