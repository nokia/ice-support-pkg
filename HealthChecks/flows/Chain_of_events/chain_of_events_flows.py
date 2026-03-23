from __future__ import absolute_import
from flows.Chain_of_events.chain_of_events_validations import *
from flows.Chain_of_events.identify_manual_changes import *
from HealthCheckCommon.base_validation_flow import BaseValidationFlow

from tools.global_enums import *


class ChainOfEventsFlow(BaseValidationFlow):
    def _get_list_of_validator_class(self, version, deployment_type):

        check_list_class = [
            FileTrackerUI,
            OperationsTimeline,
            ValidateUnwantedServicesOnNodes
        ]
        return check_list_class

    def command_name(self):
        return "chain_of_events"

    def deployment_type_list(self):
        return [Deployment_type.CBIS, Deployment_type.NCS_OVER_BM, Deployment_type.NCS_OVER_OPENSTACK,
                Deployment_type.NCS_OVER_VSPHERE]

    def is_part_of_limited_output(self):
        return False

    def get_flow_order(self):
        return -1
