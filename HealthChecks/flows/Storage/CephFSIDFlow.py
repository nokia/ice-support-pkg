from __future__ import absolute_import
from flows.Storage.ceph.CephFSID import *
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
from tools.global_enums import *

class CephFSIDFlow(BaseValidationFlow):
    def _get_list_of_validator_class(self, version, deployment_type):
        check_list_class = [FsidInfo,
                            TemplateOpenStackKeyringCheck,
                            KeyringOpenstackConfigCheck,
                            KeyringAdminConfigCheck,
                            FSIDPuppetConfValidator,
                            FSIDCinderConfValidator,
                            FsidNovaConfValidator,
                            FSIdNovaSecretValidator,
                            VmsFSIDCheck,
                            VirshSecretFsidCheck,
                            KeyringCephFSConfigCheck,
                            KeyringBareMetalConfigCheck,
                            KeyringCephRBDConfigCheck,
                            KeyringRadosGWConfigCheck,
                            # CephKeysConfigValidator,      # Removed as decided on ICET-1606,
                            KeyringMultiplePoolConfigCheck,
                            FSIdNovaSecretMultiplePoolsValidator,
                            CheckCEPHStoreDBSize
                            ]

        if version < Version.V24_11:
            check_list_class.extend([
                CephPoolSizeConfigCheck,
                FSIDCephConfValidator,
                TemplateFSIDCheck
            ])

        if version < Version.V25:
            check_list_class.append(CephJournalSizeConfCheck)

        return check_list_class

    def command_name(self):
        return "ceph_fsid"

    def deployment_type_list(self):
        return [Deployment_type.CBIS, Deployment_type.NCS_OVER_BM, Deployment_type.NCS_OVER_OPENSTACK]
