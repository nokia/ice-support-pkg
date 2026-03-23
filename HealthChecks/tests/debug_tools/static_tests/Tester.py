from __future__ import absolute_import
from __future__ import print_function
import json

from tests.flows_implications_tags import FlowsImplicationTags
from tests.run_validations_confluences import FlowsValidationsConfluenceCoverage
from tests.statistic.flows_statistic import FlowsStatistic


class Tester():
    def run_tests(self):
        print ('\n>>> all validations')
        myFlowsStatistic = FlowsStatistic()

        print('\n available validations')
        myFlowsStatistic.nice_print_all_validation_list()

        all_flows = myFlowsStatistic.get_flows_statistic()
        print(json.dumps(all_flows, indent=4))

        FlowsImplicationTags().print_validations_without_implication_tags()

        print('\n>>> List validations with no documentation:\n')
        flows_confluence = FlowsValidationsConfluenceCoverage()
        missing_validations, missing_confluences = flows_confluence.list_validations_no_documentation()
        print("The following validations has confluence page but it's missing:")
        for validation in missing_validations:
            print(validation)
        print('\n')
        print("The following validations doesn't have confluences pages:")
        print(json.dumps(missing_confluences, indent=4, sort_keys=True))
        print('\n')
        print('\n>>> End of tests')



