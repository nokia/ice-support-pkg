from __future__ import absolute_import
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
from flows.Etcd.etcd_validations import EtcdBasicValidator, EtcdAlarmValidator, EtcdMemberNumberValidator, \
    EtcdLeaderValidator, EtcdEndpointHealthValidator, EtcdWriteReadValidator, EtcdBackendCommitDurationCheck, \
    EtcdWalFsyncdurationCheck, CalicoKubernetesAlignNodes, EtcdNetworkPeerRoundTripTimeCheck, EtcdDBSizeValidator, \
    VerifyETCDRulesPresentInIPtables, EtcdScaleInLeftovers, EtcdPerformanceCheck, EtcdBCMTTransactionsCountValidator
from tools.global_enums import Deployment_type


class EtcdFlow(BaseValidationFlow):

    def _get_list_of_validator_class(self, version, deployment_type):
        return [
            EtcdBasicValidator,
            EtcdAlarmValidator,
            EtcdMemberNumberValidator,
            EtcdLeaderValidator,
            EtcdEndpointHealthValidator,
            EtcdWriteReadValidator,
            EtcdWalFsyncdurationCheck,
            EtcdBackendCommitDurationCheck,
            CalicoKubernetesAlignNodes,
            EtcdNetworkPeerRoundTripTimeCheck,
            EtcdDBSizeValidator,
            # VerifyETCDRulesPresentInIPtables,
            EtcdScaleInLeftovers,
            EtcdPerformanceCheck,
            EtcdBCMTTransactionsCountValidator
        ]

    def deployment_type_list(self):
        return [Deployment_type.NCS_OVER_OPENSTACK, Deployment_type.NCS_OVER_BM, Deployment_type.NCS_OVER_VSPHERE]

    def command_name(self):
        return "test_etcd"
