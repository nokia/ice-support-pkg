from __future__ import absolute_import
import os
import sys

from PreFlowValidations import PreFlowValidations

# Add parent of working dir to path to be able to import ice/lib/global_configurations.py
sys.path.append(os.path.join(os.getcwd(), ".."))
import global_configurations

from tools.EnvironmentInfo import *
from tools.ExecutionModule.HostExecutorsFactory.CbisHostExecutorFactory import CbisHostExecutorFactory
from tools.ExecutionModule.HostExecutorsFactory.NcsVsphereOpenstackHostExecutorFactory import \
    NcsVsphereOpenstackHostExecutorFactory
from tools.ExecutionModule.HostExecutorsFactory.NcsBareMetalHostExecutorFactory import NcsBareMetalHostExecutorFactory
from tools.global_enums import Deployment_type


CONFIG_DEPLOYMENT_TYPE_TO_DEPLOYMENT_TYPE = {
    global_configurations.DeploymentType.CBIS: Deployment_type.CBIS,
    global_configurations.DeploymentType.NCS_OVER_BM: Deployment_type.NCS_OVER_BM,
    global_configurations.DeploymentType.NCS_OVER_OPENSTACK: Deployment_type.NCS_OVER_OPENSTACK,
    global_configurations.DeploymentType.NCS_OVER_VSPHERE: Deployment_type.NCS_OVER_VSPHERE
}


class InitializationFactory:
    def __init__(self):
        self.host_executor_factory = None
        self.environment_info = None

    @staticmethod
    def get_deployment_type(debug_flg):
        configuration_deployment_type_key = ExecutionHelper.get_deployment_type_from_configuration()
        try:
            config_deployment_type = global_configurations.DeploymentType(configuration_deployment_type_key)
        except ValueError:
            return False, "{} is not a valid DeploymentType".format(configuration_deployment_type_key), None

        deployment_type = CONFIG_DEPLOYMENT_TYPE_TO_DEPLOYMENT_TYPE[config_deployment_type]
        deployment_type_ok, message = PreFlowValidations.validate_deployment_type(deployment_type)

        if not deployment_type_ok:
            return False, message, None

        return True, message, deployment_type

    def initialize(self,debug_flg):
        is_ok, deployment_msg, deployment_type = InitializationFactory.get_deployment_type(debug_flg)

        if not is_ok:
            return False, deployment_msg, None
        if deployment_type == Deployment_type.CBIS:
            self.host_executor_factory = CbisHostExecutorFactory()
            self.environment_info = CbisEnvironmentInfo()
        elif deployment_type == Deployment_type.NCS_OVER_BM:
            self.host_executor_factory = NcsBareMetalHostExecutorFactory()
            self.environment_info = NCSBareMetalEnvironmentInfo()
        elif deployment_type == Deployment_type.NCS_OVER_VSPHERE:
            self.host_executor_factory = NcsVsphereOpenstackHostExecutorFactory()
            self.environment_info = NcsVsphereEnvironmentInfo()
        elif deployment_type == Deployment_type.NCS_OVER_OPENSTACK:
            self.host_executor_factory = NcsVsphereOpenstackHostExecutorFactory()
            self.environment_info = NcsOpenStackEnvironmentInfo()

        else:
            return False, 'deployment type is not supported', None
        return True, deployment_msg, deployment_type

    def activate(self, version_arg):
        assert self.environment_info
        is_ok, msg = self.environment_info.collect_info(version_arg)
        if not is_ok:
            return False, msg

        return self.host_executor_factory.build_host_executors_dict(self.environment_info.inventory_path,
                                                                    self.environment_info.base_conf)
