from __future__ import absolute_import
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
from flows.Monitoring.btel_validations import *

class btel_flows_ncs(BaseValidationFlow):

    def _get_list_of_validator_class(self, version, deployment_type):
        check_list_class = [
            FluentdDaemonSetRunningInAllNodesOrNot,
            FluentdDaemonSetReplicasAllRunning,
            AlertManagerAndCPROClusterIPAccessableOrNot,
            list_of_btel_components_installed,
            AreBtelPodsTerminatedWithOOMKILLED,
            CheckWhetherKibanaIsAccesible,
            IsBtelPodsReadyAndRunningWithNoRestarts,
            CheckWhetherElasticsearchIsWorkingAsExpected,
            CheckWhetherGrafanaIsAccesible,
            CheckWhetherBelkCuratorIsWorkingAsExpected,
            CheckNodeLabels,
            CproKubeStateMetricsTimeZoneValidation,
        ]

        if version == Version.V24_7:
            check_list_class.append(CheckPrometheusStorageUsage)

        return check_list_class

    def command_name(self):
        return "btel_validations"

    def deployment_type_list(self):
        return [Deployment_type.NCS_OVER_BM, Deployment_type.NCS_OVER_VSPHERE, Deployment_type.NCS_OVER_OPENSTACK]
