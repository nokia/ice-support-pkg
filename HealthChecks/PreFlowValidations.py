from __future__ import absolute_import
from tools import global_enums as enums
import os


class PreFlowValidations:
    @staticmethod
    def validate_deployment_type(deployment_type):
        if deployment_type not in enums.Deployment_type.AVAILABLE_TYPES:
            return False, "Deployment type {} is not supported".format(deployment_type)
        return True, ""

    @staticmethod
    def validate_inventory_path(inventory_path, deployment_type):
        if enums.Deployment_type.is_ncs(deployment_type) and not os.path.isfile(inventory_path):
            return False, "inventory file path {} does not exist".format(inventory_path)
        return True, ""

    @staticmethod
    def validate_connectivity(deployment_type, host_executor_factory):
        if enums.Deployment_type.is_cbis(deployment_type):
            hypervisor_host_executor = list(host_executor_factory.get_host_executors_by_roles([enums.Objectives.HYP]
                                                                                              ).values())[0]
            if not hypervisor_host_executor.is_connected:
                return False, [hypervisor_host_executor.host_name]
        return True, []

    @staticmethod
    def validate_key_file_exist(key_file_path):
        if os.path.isfile(key_file_path):
            return True, ""
        return False, "key file was deleted, regenerate it via the installer"
