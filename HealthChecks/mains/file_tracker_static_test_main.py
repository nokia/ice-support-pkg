from __future__ import absolute_import
from __future__ import print_function
from mains.base_main import *
from mains.file_tracker_tester import FileTrackerTester


class FileTrackerStaticTestMain(MainBase):

    def _add_argument_for_argparse(self):
        pass
    def _get_flows_dict(self):
       pass

    def _run_flows_dict(self, flow_dict):
        pass

    def _create_summary_operations(self, cluster_name=""):
        pass

    def _set_invoker(self, version, deployment_type, only_specific_hosts_list=None, roles=None,
                     specific_validations=None):
        pass


    def _run_and_get_result(self):
        MainBase._prepare_system(self)
        print ("---------start-printing----------")
        my_tester = FileTrackerTester()
        my_tester.run_tests()

        return self.get_dict_result(1, "--done---")



