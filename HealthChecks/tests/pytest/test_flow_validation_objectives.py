import pytest

from invoker.validations_flows_list import ValidationFlowList
from ...tools.global_enums import Version, Deployment_type, Objectives

def collect_flow_validations():
    validations_dict = {}
    cases = []
    for flow_class in ValidationFlowList.get_list_of_flows():
        flow = flow_class()
        all_validations = set()
        for version in Version.AVAILABLE_VERSIONS:
            for deployment_type in Deployment_type.AVAILABLE_TYPES:
                try:
                    validators = flow._get_list_of_validator_class(version, deployment_type)
                except Exception:
                    continue

                if validators:
                    all_validations.update(validators)

        for validation in all_validations:
            validation_dict = validations_dict.get(validation.__name__, None)
            if validation_dict:
                validation_dict["flows_set"].add(flow_class)
            else:
                flows_set = set()
                flows_set.add(flow_class)
                validations_dict[validation.__name__] = {"validation": validation,"flows_set": flows_set}

    for validation_dict in validations_dict.values():
        supported_deployments_types = set()
        flows_set = validation_dict["flows_set"]
        flows_string = str([flow_class.__name__ for flow_class in flows_set])
        for flow_class in flows_set:
            flow = flow_class()
            supported_deployments_types.update(flow.deployment_type_list())
        cases.append((flows_string, supported_deployments_types, validation_dict["validation"]))

    return cases

"""
This test ensures that all validations define objective_hosts that are consistent
with the flows they belong to.

How it works:
1. it call collect_flow_validations, which:
   - Iterates over all flows in the system (from ValidationFlowList).
   - For each flow, calls _get_list_of_validator_class with all possible
     version/deployment type combinations to discover every validation that
     can appear in that flow.
   - Builds a dictionary that maps each validation to the set of flows
     where it is used.
   - For each validation, gathers the union of all supported objective types
     from the flows deployment_type_list() definitions.

2. The test itself then verifies for each validation:
   - If objective_hosts is a list (or string), all entries must be included
     in the supported objective types collected from its flows.
   - If objective_hosts is a dict, then:
       a. Each deployment type used by the the validation have to be covered
          by it's validations deployment types.
       b. Each objective type under a given deployment must actually belong
          to that deployment type (sanity check).

In short:
This guarantees that a validation never declares objectives that cannot
actually be satisfied by the flows where it is used.
"""
@pytest.mark.parametrize("flows_string,supported_deployments_types,validation", collect_flow_validations())
def test_flow_validation_objectives(flows_string, supported_deployments_types, validation):
    supported_objectives = set()
    for deployment_type in supported_deployments_types:
        supported_objectives.update(Objectives.get_available_types(deployment_type))
    if isinstance(validation.objective_hosts, list) or isinstance(validation.objective_hosts, str):
        if isinstance(validation.objective_hosts, list):
            objective_hosts = validation.objective_hosts
        else:
            objective_hosts = [validation.objective_hosts]
        assert set(objective_hosts).issubset(supported_objectives), (
            "Error mismatch between validation {} objective_hosts {} and its flow {} "
            "the flow doesn't fit all the objective types that the validation is using!"
        ).format(validation.__name__, objective_hosts, flows_string)

    elif isinstance(validation.objective_hosts, dict):
        for deployment_type in validation.objective_hosts:
            assert deployment_type in supported_deployments_types, (
                "Error in validation {} deployment type {} not in it's flows {} deployment types set {}"
            ).format(validation.__name__, deployment_type, flows_string, supported_deployments_types)

            deployment_type_objective_set = set(validation.objective_hosts[deployment_type])
            assert deployment_type_objective_set.issubset(Objectives.get_available_types(deployment_type)), (
                "Error in validation {} objective_hosts "
                "One or more objective types of {} not belong to deployment type {}"
            ).format(validation.__name__, deployment_type_objective_set, deployment_type)

    else:
        assert False, (
            "validation {} doesn't have suitable objective_hosts type found {}"
        ).format(validation.__name__, type(validation.objective_hosts))
