from __future__ import absolute_import
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
from flows.Monitoring.victoria_metrics_validations import *
from tools.global_enums import Version, Deployment_type


class VictoriaMetricsFlows(BaseValidationFlow):

    def _get_list_of_validator_class(self, version, deployment_type):
        check_list_class = []
        if version >= Version.V24_7:
            check_list_class.extend([VictoriaMetricsHasAlarms,
                                     GrafanaIsAvailable])

        if version >= Version.V24_11:
            check_list_class.extend([VictoriaMetrixIsAvailable])

        return check_list_class

    def command_name(self):
        return "victoriaMetrics"

    def deployment_type_list(self):
        return [Deployment_type.NCS_OVER_BM, Deployment_type.NCS_OVER_OPENSTACK, Deployment_type.NCS_OVER_VSPHERE]
