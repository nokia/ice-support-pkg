from __future__ import absolute_import
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
from flows.Network.dumpflows_validations import *


class NetworkTrafficFlows(BaseValidationFlow):

    def _get_list_of_validator_class(self, version, deployment_type):
        check_list_class = [
                          #  MulticastDumpFlows,
                            UnicastDumpFlows,
                            ValidateUnicastFlows
                           # ValidateMulticastFlows
                            ]
        return check_list_class

    def command_name(self):
        return "network_traffic_flows"

    def deployment_type_list(self):
        return [Deployment_type.CBIS]
