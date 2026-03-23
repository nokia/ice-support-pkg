import os
import sys

sys.path.append(os.path.join(os.getcwd(), "../ice/lib"))
from global_configurations import DeploymentType as GlobalConfigurationsDeploymentType

class DeploymentType:

    @staticmethod
    def get_available_deployment_types():
        return [GlobalConfigurationsDeploymentType.CBIS, GlobalConfigurationsDeploymentType.NCS_OVER_OPENSTACK,
                GlobalConfigurationsDeploymentType.NCS_OVER_BM, GlobalConfigurationsDeploymentType.NCS_OVER_VSPHERE]

    @staticmethod
    def get_ncs_type():
        return [
            GlobalConfigurationsDeploymentType.NCS_OVER_OPENSTACK,
            GlobalConfigurationsDeploymentType.NCS_OVER_BM,
            GlobalConfigurationsDeploymentType.NCS_OVER_VSPHERE
        ]

    @staticmethod
    def is_ncs(deployment_type):
        return deployment_type in DeploymentType.get_ncs_type()

    @staticmethod
    def is_ncs_over_bm(deployment_type):
        return deployment_type == GlobalConfigurationsDeploymentType.NCS_OVER_BM

    @staticmethod
    def is_cbis(deployment_type):
        return deployment_type in [GlobalConfigurationsDeploymentType.CBIS]

