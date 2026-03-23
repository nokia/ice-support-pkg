from __future__ import absolute_import
from flows.Storage.glusterfs.GlusterFS import *
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
from tools.global_enums import *

class GlusterFsFlow(BaseValidationFlow):
    def _get_list_of_validator_class(self, version, deployment_type):
        check_list_class = [
                            GlusterPeerStatus,
                            heketi_pod_status,
                            heketi_db_pending_operation,
                            heketi_db_inconsistency_check,
                            VolumeHealNeedCheck,
                            gluster_db_cluster_check,
                            GlusterHeketiMountDiskSpaceValidation,
                            GlusterFSInvalidGFIDs,
                            StorageSpaceValidationBeforeRecovery
                            ]
        return check_list_class

    def command_name(self):
        return "glusterfs_validations"

    def deployment_type_list(self):
        return [Deployment_type.CBIS,Deployment_type.NCS_OVER_OPENSTACK,Deployment_type.NCS_OVER_VSPHERE]