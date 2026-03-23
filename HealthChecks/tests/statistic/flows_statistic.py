from __future__ import absolute_import
from __future__ import print_function
from tools.global_enums import *
from collections import OrderedDict
from tests.debug_tools.static_tests.tests_tools.flows_set_factory import FlowsSetFactory


class FlowsStatistic(FlowsSetFactory):
    def nice_print_all_validation_list(self):
        flow_set_factory = FlowsSetFactory()
        detailed_validation_data = flow_set_factory.get_flows_sets(flg_detailed=True)
        # print (detailed_validation_data)

        print("--------------------------------------------------------------------")
        for flow_name in detailed_validation_data:
            print(" {}: ".format(flow_name))
            validations = detailed_validation_data[flow_name]
            print ("")
            for uniq_name in validations:
                details = validations[uniq_name]
                print("   -> {}".format(details["title"]))
                if details["doc"]:
                    print("   link: {} ".format(details["doc"]))
                if details["implication_tags"]:
                    print("   {}".format(" ".join(details["implication_tags"])))
                print("")

        print ("--------------------------------------------------------------------")

    def get_flows_statistic(self):
        flow_set_factory = FlowsSetFactory()
        data = flow_set_factory.get_flows_sets()
        all_deployments = set()
        cbis = set()
        ncs = set()
        num_per_flows = {}

        for flow in data:
            of_a_flow = set()
            for deployment_type in data[flow]:
                flows_set = data[flow][deployment_type]
                of_a_flow = of_a_flow.union(flows_set)
                all_deployments = all_deployments.union(flows_set)
                if Deployment_type.is_cbis(deployment_type):
                    cbis = cbis.union(flows_set)
                if Deployment_type.is_ncs(deployment_type):
                    ncs = ncs.union(flows_set)

            num_per_flows[flow] = len(of_a_flow)
        cbis_and_ncs = cbis.intersection(ncs)
        res = OrderedDict()
        res["total number of validations"] = len(all_deployments)
        res["CBIS and NCS"] = len(cbis_and_ncs)
        res["CBIS"] = len(cbis.difference(cbis_and_ncs))
        res["NCS"] = len(ncs.difference(cbis_and_ncs))
        res["Per_flow"] = num_per_flows
        return res
