from __future__ import absolute_import
from HealthCheckCommon.operations import *
from HealthCheckCommon.UnifySystemParameterCheck import UnifySystemParameterCheck
from tools.python_utils import PythonUtils
import re
from tools.Exceptions import UnExpectedSystemOutput


class UnifyHWCheck(UnifySystemParameterCheck):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.UC],
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
    }
    def set_document(self):
        self._unique_operation_name = "is_Manufacturer_and_Product Name_unified"
        self._title = "is Board Product and Product Manufacturer unified"
        self._failed_msg = "TBD"
        self._severity = Severity.CRITICAL

        self._system_info = ""
        self._title_of_info = "Manufacturer and Product Names"
        self._is_pure_info = False

    def _process_parameter_from_command_output(self, out, err, exit_code, host_name):
        if not out or not len(re.findall(r"Board Product\s*:\s*.*\s.*Product Manufacturer\s*:\s*.*", out)):
            raise UnExpectedSystemOutput(
                host_name, self._set_command_to_execute_on_each_host(), out)
        info_lines = [line for line in out.splitlines() if ':' in line]
        info_dict = {}
        for line in info_lines:
            k, v = line.split(':', 1)
            info_dict[k.strip()] = v.strip()
        info_str = "{manufacturer} - {board_product}".format(
            manufacturer=info_dict.get('Product Manufacturer'),
            board_product=info_dict.get('Board Product')
        )
        return info_str

    def _set_command_to_execute_on_each_host(self):
        return "sudo ipmitool fru print 0 | grep -E 'Board Product|Product Manufacturer'"

    def _user_set_info(self, is_check_relevant, parameter_host_dict):
        if len(parameter_host_dict) == 1:
            return list(parameter_host_dict.keys())[0]
        return PythonUtils.key_to_list2str("list of the host of each version:", parameter_host_dict)

    def _set_system_parameter_name(self):
        return "Manufacturer and Board Names"


class UnifyHWCheck_on_storage(UnifyHWCheck):
    def _set_target_roles(self):
        return [Objectives.STORAGE]

    def set_document(self):
        self._unique_operation_name = "is_Manufacturer_and_Product Name_unified_storage"
        self._title = "is Board Product and Product Manufacturer unified - for storage"
        self._failed_msg = "TBD"
        self._severity = Severity.CRITICAL

        self._system_info = ""
        self._title_of_info = "Board Product and Product Manufacturer storage"
        self._is_pure_info = False


class UnifyHWCheck_on_ncs_workers(UnifyHWCheck):
    objective_hosts = [Objectives.ONE_MASTER]


    def _set_target_roles(self):
        return [Objectives.WORKERS]

    def set_document(self):
        self._unique_operation_name = "is_Manufacturer_and_Product_Name_ncs_workers"
        self._title = "is Board Product and Product Manufacturer unified - for ncs workers"
        self._failed_msg = "TBD"
        self._severity = Severity.WARNING

        self._system_info = ""
        self._title_of_info = "Board Product and Product Manufacturer workers"
        self._is_pure_info = False


class UnifyHWCheck_on_ncs_edges(UnifyHWCheck):
    objective_hosts = [Objectives.ONE_MASTER]

    def _set_target_roles(self):
        return [Objectives.EDGES]

    def set_document(self):
        self._unique_operation_name = "is_Manufacturer_and_Product_Name_unified_ncs_edge"
        self._title = "is Board Product and Product Manufacturer unified - for ncs edges"
        self._failed_msg = "TBD"
        self._severity = Severity.WARNING

        self._system_info = ""
        self._title_of_info = "Board Product and Product Manufacturer edges"
        self._is_pure_info = False


class UnifyHWCheck_on_computes(UnifyHWCheck):
    def _set_target_roles(self):
        return [Objectives.CONTROLLERS, Objectives.COMPUTES, Objectives.MASTERS]

    def set_document(self):
        self._unique_operation_name = "is_Manufacturer_and_Product Name_unified_computes"
        self._title = "is Board Product and Product Manufacturer unified - for computes/masters"
        self._failed_msg = "TBD"
        self._severity = Severity.CRITICAL
        self._system_info = ""
        self._title_of_info = "Board Product and Product Manufacturer computes"
        self._is_pure_info = False
        self._is_highlighted_info = True
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]
