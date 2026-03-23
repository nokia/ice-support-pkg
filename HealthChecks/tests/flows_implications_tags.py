from __future__ import absolute_import
from __future__ import print_function
from tests.debug_tools.static_tests.tests_tools.flows_set_factory import FlowsSetFactory


class FlowsImplicationTags(FlowsSetFactory):
    def print_validations_without_implication_tags(self):
        print("--------------------------------------------------------------------")
        print("Validations without implications tags:")
        validations_details = self.get_flows_sets(flg_detailed=True)

        for flow, flow_data in list(validations_details.items()):
            print("    flow: {}".format(flow))
            for validation_name, validation_data in list(flow_data.items()):
                if not validation_data["implication_tags"]:
                    print("        {}".format(validation_name))
        print("--------------------------------------------------------------------")
