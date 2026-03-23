from __future__ import absolute_import
from flows.Monitoring.zabbix_validations import *
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
from flows.Monitoring.btel_validations import *


class ZabbixFlows(BaseValidationFlow):

    def _get_list_of_validator_class(self, version, deployment_type):
        check_list_class = []

        if Deployment_type.is_cbis(deployment_type):
            check_list_class.extend([VerifyControllerVirtualIp])

        if Deployment_type.is_ncs(deployment_type) and version < Version.V24_7:
            check_list_class.extend([CheckWhetherZabbixAgentFirewallWorkingAsExpected])
                                  
        if Deployment_type.is_ncs(deployment_type) and version < Version.V23_10:
            check_list_class.extend([VerifyZabbixServiceIsRunningOnOneNodeOnly])
        
        if version >= Version.V19:
            check_list_class.extend([CheckZabbixAlarmsCbis])

        if Version.V24_7 > version >= Version.V20_FP2:  # zabbix removed on 24.7
            check_list_class.extend([CheckZabbixAlarmsNcs])

        if Version.V24_7 > version >= Version.V22 and gs.is_ncs_central():
            check_list_class.extend([CheckSelinuxContextForZabbix])

        return check_list_class

    def command_name(self):
        return "zabbix"

    def deployment_type_list(self):
        return [Deployment_type.CBIS, Deployment_type.NCS_OVER_BM]

