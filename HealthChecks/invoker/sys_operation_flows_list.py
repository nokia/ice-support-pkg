from __future__ import absolute_import
# return the list of flows in that can be run
# (this was part of the invoker)
from flows_of_sys_operations.FileTracker.FileTrackerFlow import FileTrackerFlow
from flows_of_sys_operations.sys_data_collector.log_collector.configuration_generator.log_scenarios_generator_flow \
    import LogScenariosGeneratorFlow
from flows_of_sys_operations.sys_data_collector.telemetry_collector.telemetry_collector_flow import \
    TelemetryCollectingFlow
from flows_of_sys_operations.test.test_sys_operator_flow import BaseSystemOperatorTestFlow
from flows_of_sys_operations.sys_data_collector.log_collector.logs_collecting_flow import LogCollectingFlow


class SysOperationFlowList:
    @staticmethod
    def get_list_of_flows():
        return [
            BaseSystemOperatorTestFlow,
            LogCollectingFlow,
            TelemetryCollectingFlow,
            FileTrackerFlow,
            LogScenariosGeneratorFlow
        ]
