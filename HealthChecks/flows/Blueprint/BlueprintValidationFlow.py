from __future__ import absolute_import
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
from flows.Blueprint.BlueprintDataCollectorsCommon import BlueprintDataCollector
from flows.Blueprint.BlueprintValidations import ValidateHWBlueprint, ValidateFWBlueprint, ValidateOsDiskMatch
from tools.global_enums import Deployment_type


class BlueprintValidationFlow(BaseValidationFlow):

    def _get_list_of_validator_class(self, version, deployment_type):
        check_list_class = [
            ValidateHWBlueprint,
            ValidateFWBlueprint,
            ValidateOsDiskMatch,
        ]
        return check_list_class

    def _clean_flow(self):
        '''
        clean cached pool.
        '''
        BlueprintDataCollector.cached_data_pool = {}

    def command_name(self):
        return "blueprint"

    def deployment_type_list(self):
        return [Deployment_type.CBIS, Deployment_type.NCS_OVER_BM]

    def is_part_of_limited_output(self):
        return False
