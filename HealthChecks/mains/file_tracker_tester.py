from __future__ import absolute_import
from __future__ import print_function
from tests.tests_file_tracker.test_file_tracker_flow import TestFileTrackerFlow
from tools.ExecutionModule.HostExecutorsFactory.CbisHostExecutorFactory import *


class FileTrackerTester():

    def __init__(self):
        pass

    def run_tests(self):
        print('\n>>> File Tracker Tests ****:')
        status = self.test_file_tracker()
        base_dir_path = "/usr/share/ice/tests_out_files"
        json_path = "{}/file_tracker_tests_output.json".format(base_dir_path)

        local_operator = ExecutionHelper.get_local_operator(False)
        local_operator.get_output_from_run_cmd("sudo mkdir -p {}".format(base_dir_path))
        local_operator.get_output_from_run_cmd("sudo touch {json_path}; sudo chmod 777 {base_dir_path}".format(
            json_path=json_path, base_dir_path=base_dir_path))

        with open(json_path, 'w') as outfile:
            json.dump(status, outfile, indent=4)
        print("=================================================================================================")
        print("Tests output json is saved on {}".format(json_path))
        print("=================================================================================================")
        pretty_status = json.dumps(status, indent=4)
        print("Status OK: {} ".format(pretty_status))

    def test_file_tracker(self):
        my_flow = TestFileTrackerFlow()
        version = Version.V19A
        deployment_type = Deployment_type.CBIS
        validator_objects = my_flow._get_list_of_validator_object(version, deployment_type, True)
        status = my_flow.verify(version, deployment_type, validator_objects)
        return status
