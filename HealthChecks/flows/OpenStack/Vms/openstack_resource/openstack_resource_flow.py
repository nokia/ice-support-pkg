from __future__ import absolute_import
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
from flows.OpenStack.Vms.openstack_resource.openstack_resource_validations import DuplicatePortRecords, \
    DuplicateInstanceCheck, \
    VmResourceAllocationOnRightCompute, ResourceAllocationsCheck, \
    NetworkInfoForInstanceInInstanceInfoCaches, InterVMCommunicationPort, InterVMCommunicationHost, \
    VolumeDeviceNotFound, CheckInstanceStatus, CheckStaleVolumes
from tools import user_params
from tools.global_enums import Deployment_type, Version


class OpenstackResource(BaseValidationFlow):
    def _get_list_of_validator_class(self, version, deployment_type):
        res = [
            DuplicateInstanceCheck,
            ResourceAllocationsCheck,
            NetworkInfoForInstanceInInstanceInfoCaches,
            InterVMCommunicationPort,
            CheckInstanceStatus,
            CheckStaleVolumes
            #InterVMCommunicationHost
        ]

        if not user_params.vm:
            return res

        if version == Version.V20:
            return [DuplicatePortRecords,
                    VmResourceAllocationOnRightCompute,VolumeDeviceNotFound] + res
        else:
            return [DuplicatePortRecords,
                    VmResourceAllocationOnRightCompute] + res

    def command_name(self):
        return "openstack-resource"

    def deployment_type_list(self):
        return [Deployment_type.CBIS]
