from __future__ import absolute_import
from HealthCheckCommon.base_SystemOperator_flow import BaseSystemOperatorFlow
from flows_of_sys_operations.sys_data_collector.log_collector.configuration_generator.\
    scenarios.create_customized_scenario_template import Customized
from flows_of_sys_operations.sys_data_collector.log_collector.configuration_generator.scenarios.log_scenarios import \
    Storage, Installation, Upgrade, General, Horizon, AccessAndAuthentication, BackupAndRestore, ScaleIn, ScaleOut, \
    Migration, Evacuation, VmNotLoading, Gluster, NodesFailures, Zabbix, KernelAndHw, Nova, Networking, RabbitMq, \
    Redis, Swift, Security
from tools.global_enums import Deployment_type


class LogScenariosGeneratorFlow(BaseSystemOperatorFlow):
    def _get_list_of_validator_class(self, version, deployment_type):
        return [
            Storage,
            Installation,
            Upgrade,
            General,
            Horizon,
            AccessAndAuthentication,
            BackupAndRestore,
            ScaleIn,
            ScaleOut,
            Migration,
            Evacuation,
            VmNotLoading,
            Gluster,
            NodesFailures,
            Zabbix,
            KernelAndHw,
            Nova,
            Networking,
            RabbitMq,
            Redis,
            Swift,
            Security,
            Customized
        ]

    def deployment_type_list(self):
        return [Deployment_type.CBIS, Deployment_type.NCS_OVER_BM]

    @staticmethod
    def command_name():
        return "log_scenarios_generator"
