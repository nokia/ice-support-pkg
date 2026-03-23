from __future__ import absolute_import
import json
from tests.debug_tools.static_tests.tests_tools.flows_set_factory import FlowsSetFactory
import tools.paths as paths

# This is only an example tof validations white-list
white_list_validations = {
    'check_elk_fs_accessible_or_not', 'ceph_keys_values_as_runtime', 'certificate_check_key_haproxy', 'certificate_check_key_haproxy', 'certificate_check_expired_haproxy',
        'certificate_check_expired_nova', 'certificate_check_expired_barbican', 'certificate_check_key_cinder', 'certificate_check_expired_ca',
        'certificate_check_expired_cinder', 'certificate_check_key_nova'
}

class FlowsValidationsConfluenceCoverage(FlowsSetFactory):

    def list_validations_no_documentation(self):
        missing_confluences = {}
        flow_set_factory = FlowsSetFactory()
        data = flow_set_factory.get_flows_sets()
        all_deployments = set()

        with open(paths.NAME_TO_URL_FILE) as name_to_url:
            validations_confluences = json.load(name_to_url)
        validations_confluences = set(validations_confluences.keys())

        for flow in data:
            flow_set = set()
            for deployment_type in data[flow]:
                flow_deployment_set = set(data[flow][deployment_type])
                flow_set.update(flow_deployment_set)
            flow_validations_exclude_has_confluence = flow_set.difference(validations_confluences)
            flow_validations_exclude_white_list_validations = flow_validations_exclude_has_confluence.difference(white_list_validations)
            missing_confluences[flow] = list(flow_validations_exclude_white_list_validations)
            all_deployments = all_deployments.union(flow_set)

        missing_validations = validations_confluences.difference(all_deployments)
        return missing_validations, missing_confluences
