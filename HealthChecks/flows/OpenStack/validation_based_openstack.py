from __future__ import absolute_import
from HealthCheckCommon.operations import *
import re

from HealthCheckCommon.validator import Validator, InformatorValidator
from flows.Chain_of_events.operation_timing_info import Operation_timing_info


class HasNovaConf(Validator):
    objective_hosts = [Objectives.COMPUTES]

    NOVA_PATH = "/var/lib/config-data/puppet-generated/nova_libvirt/etc/nova/nova.conf"

    def set_document(self):
        self._unique_operation_name = "has_nova_conf"
        self._title = "check that nova conf is in place"
        self._failed_msg = "nona conf is not found at " + self.NOVA_PATH
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]

    def is_validation_passed(self):
        ret, out, err = self.run_cmd("ls " + self.NOVA_PATH)
        return ret == 0


# class computes_memory_check(InformatorValidator):
#     objective_hosts = [Objectives.COMPUTES]
#
#     def set_document(self):
#         self._unique_operation_name = "free_memory_validation"
#         self._title = "Validate sufficient memory for vms"
#         self._failed_msg = "test not completed:"
#         self._severity = Severity.ERROR
#
#         self._implication_tags = [ImplicationTag.RISK]
#         self._title_of_info = "Check if HugePages are in use"
#         self._is_pure_info = False
#
#     def _get_vm_total_memory(self):
#
#         # will throw exeption and debug note if can not call virsh
#         out = self.get_output_from_run_cmd("sudo virsh list")
#
#         if 'instance' not in out:
#             # no instatnce on this set up
#             return 0, 0
#         else:
#
#             vm_ids = "sudo virsh list | grep instance"
#             out = self.run_and_get_the_nth_field(vm_ids, 1)
#             vm_ids_list = list(out.strip().split('\n'))
#
#             vms_mem_list = [0]
#             for vm_id in vm_ids_list:
#                 x = self.run_and_get_the_nth_field(
#                     "sudo virsh dumpxml {} | grep 'memory unit=' | sed \"s/[\'\<>]/ /g\"".format(vm_id), 4)
#                 mem_val = (x[1].strip())
#                 vms_mem_list.append(int(mem_val))
#
#             total_mem = sum(vms_mem_list)
#             max_vm_memory = max(vms_mem_list)
#             return (total_mem / 1024) / 1024, (max_vm_memory / 1024) / 1024
#
#     def _get_huge_pages_total(self):
#         hugpage_pool = 0
#         hugepages_total = self.run_and_get_the_nth_field("cat /proc/meminfo |grep HugePages_Total", 2)
#         hugepages_size = self.run_and_get_the_nth_field("cat /proc/meminfo |grep Hugepagesize", 2)
#         if hugepages_total > 0:
#             hugpage_pool = ((float(hugepages_size) / 1024) / 1024) * float(hugepages_total)
#         return hugpage_pool
#
#     def _get_total_mem_to_be_used_in_GB(self):
#
#         compute_mem_total = self.run_and_get_the_nth_field("cat /proc/meminfo |grep MemTotal", 2)
#         self._system_info = self._system_info + "total memory size of {} Gigs \n".format(compute_mem_total)
#         # Take the ram allocation ratio from nova.conf
#
#         #if no ram_allocation_ratio is defain it is set to the defult 1 (<=> not considured in this calculations)
#
#         ret, out, err = self.run_cmd(
#             "sudo grep ram_allocation_ratio /var/lib/config-data/puppet-generated/nova_libvirt/etc/nova/nova.conf | grep -v '#'")
#
#         if not out:
#             ram_allocation_ratio=1
#         else:
#             ram_allocation_ratio = PythonUtils.get_the_n_th_field(out , 3)
#
#
#         total_mem_to_be_used_in_GB = ((int(compute_mem_total) * float(ram_allocation_ratio)) / 1024) / 1024
#         return total_mem_to_be_used_in_GB
#
#     def _get_free_mem_for_vms(self,hugpage_pool_total,total_mem_to_be_used_in_GB):
#         vms_mem_total, max_vm_memory = self._get_vm_total_memory()
#         #total_mem_to_be_used_in_GB = self._get_total_mem_to_be_used_in_GB()
#
#         #hugpage_pool_total = self._get_huge_pages_total()
#
#         free_mem_for_vms = total_mem_to_be_used_in_GB - vms_mem_total - hugpage_pool_total
#         return free_mem_for_vms
#
#
#     def is_validation_passed(self):
#
#         vms_mem_total, max_vm_memory = self._get_vm_total_memory()
#
#         hugpage_pool_total = self._get_huge_pages_total()
#         if (hugpage_pool_total > 0):
#             self._system_info = self._system_info + " HugePages are in use with total size of {} Gigs \n".format(
#                 hugpage_pool_total)
#         else:
#             self._system_info = 'HugePages are not in use'
#
#         total_mem_to_be_used_in_GB = self._get_total_mem_to_be_used_in_GB()
#         free_mem_for_vms=self._get_free_mem_for_vms(hugpage_pool_total,total_mem_to_be_used_in_GB)
#         self._system_info = self._system_info + "free memory {} Gig".format(free_mem_for_vms)
#
#         if free_mem_for_vms < (max_vm_memory * 1.3):
#             self._failed_msg = "Insufficient memory for vm recovery process"
#             return False
#
#
#         free_mem_percent = (free_mem_for_vms / total_mem_to_be_used_in_GB) * 100
#
#         TRESHHOLD_HUGE_PAGES=5
#         TRESHHOLD_NO_HUGE_PAGES=15
#
#         if hugpage_pool_total>TRESHHOLD_HUGE_PAGES:
#             if free_mem_percent<5:
#                 self._failed_msg = "Insufficient memory for vm process: less then {}% left for VM (huge_pages is used)".format(TRESHHOLD_HUGE_PAGES)
#                 return False
#         else:
#             if free_mem_percent<TRESHHOLD_NO_HUGE_PAGES:
#                 self._failed_msg = "Insufficient memory for vm process: less then {}% left for VM (huge_pages is not used)".format(TRESHHOLD_NO_HUGE_PAGES)
#                 return False
#
#
#         return True

class computes_memory_check(InformatorValidator):
    objective_hosts = [Objectives.COMPUTES]

    def set_document(self):
        self._unique_operation_name = "free_memory_validation"
        self._title = "Validate sufficient memory for vms"
        self._failed_msg = "test not completed:"
        self._severity = Severity.NOTIFICATION
        self._implication_tags = [ImplicationTag.RISK_RESOURCE_CLEANING_RECOMMENDED]
        self._title_of_info = "Check if HugePages are in use"
        self._is_pure_info = False

    def is_security_hardening_enabled(self):
        operation_timing = Operation_timing_info(self)
        operations = operation_timing.get_operations_datetime()
        if operations and operations.get('security_hardening') != None:
            for security_hardening_operation in operations.get('security_hardening'):
                if security_hardening_operation['status'] == 'Passed':
                    return True
        return False

    def _get_running_vms_actual_memory(self):
        total_vms_actual_memory = 0.0
        out = self.get_output_from_run_cmd('sudo virsh list --state-running --uuid')
        if not out:
            return 0.0
        vms_uuids = [line for line in out.splitlines() if line.strip()]
        for vm_uuid in vms_uuids:
            cmd = 'sudo virsh dommemstat {uuid}'.format(uuid=vm_uuid)
            # pattern : actual 4194304
            actual_memory_lines = self.run_command_and_grep(cmd, r'actual\s+\d+')
            if not actual_memory_lines:
                raise UnExpectedSystemOutput(self.get_host_ip(), cmd, 'no actual memory info in output')
            actual_memory = float(re.findall(r'\d+', actual_memory_lines[0])[0])
            total_vms_actual_memory += actual_memory
        return total_vms_actual_memory

    def _get_ram_allocation_ratio(self):
        NOVA_LIBVIRT_CONF_PATH = '/var/lib/config-data/puppet-generated/nova_libvirt/etc/nova/nova.conf'
        conf = self.get_dict_from_file(NOVA_LIBVIRT_CONF_PATH, file_format='ini')
        ratio = conf.get('DEFAULT', {}).get('ram_allocation_ratio')
        if ratio:
            return float(ratio)
        return 0

    def is_validation_passed(self):
        # all the values here are in KB
        security_hardening_enabled = self.is_security_hardening_enabled()
        #RECOMMENDED_RATIO = 0.85 when Security Hardening is NOT Enabled
        #RECOMMENDED_RATIO = 0.90 when Security Hardening is Enabled
        if security_hardening_enabled:
            RECOMMENDED_RATIO = 0.90
        else:
            RECOMMENDED_RATIO = 0.85
        errors = []
        ratio = self._get_ram_allocation_ratio()
        if not ratio:
            ratio = RECOMMENDED_RATIO
            errors.append('ram_allocation_ratio is not defined in the host')
        elif ratio > RECOMMENDED_RATIO:
            errors.append('ram_allocation_ratio configured-{} is above the recommended ratio:{}'.format(
                ratio, RECOMMENDED_RATIO
            ))
        ratio_percents = ratio * 100
        memory_details_dict = self.get_dict_from_file('/proc/meminfo', file_format='yaml')
        os_total_memory = float(str(memory_details_dict['MemTotal']).replace('kB', ''))
        hugepage_size = float(str(memory_details_dict['Hugepagesize']).replace('kB', ''))
        hugepages_memory_limit = float(str(memory_details_dict['HugePages_Total'])) * hugepage_size
        is_hugepages_used = (hugepages_memory_limit != 0)

        if is_hugepages_used:
            total_vms_memory = hugepages_memory_limit
        else:
            total_vms_memory = self._get_running_vms_actual_memory()

        current_ratio_percents = (total_vms_memory / os_total_memory) * 100
        self._system_info = """
        Hugepages in use : {},
        Hugepage Size : {} KB,
        Total Compute Memory : {} KB,
        Hugepages/vms actual memory : {} KB,
        Memory used by vms/hugepages in percents : {} %
        *****(Hugepages_vms actual memory/Total Compute Memory)*100)*****
        configured / recommended ratio : {} %
        """.format(is_hugepages_used, hugepage_size, os_total_memory, total_vms_memory,
                   round(current_ratio_percents, 2), round(ratio_percents, 2))
        if current_ratio_percents > ratio_percents:
            errors.append('vms capacity is above the configures ratio:\n{}'.format(self._system_info))
            self._severity = Severity.ERROR

        if errors:
            self._failed_msg = 'Errors:\n{}'.format('\n'.join(errors))
            return False
        return True
