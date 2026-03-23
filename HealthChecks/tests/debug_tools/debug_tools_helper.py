from __future__ import absolute_import
import os
from subprocess import call
import getpass


class DebugToolsHelper:

    @staticmethod
    def get_parent_path_until(directory, target_directory):
        while os.path.basename(directory) != target_directory:
            directory = os.path.dirname(directory)
        return directory

    @staticmethod
    def get_current_dir():
        return os.path.dirname(os.path.abspath(__file__))

    @staticmethod
    def get_support_path():
        return DebugToolsHelper.get_parent_path_until(DebugToolsHelper.get_current_dir(), "support")

    @staticmethod
    def get_out_dir():
        return os.path.join(DebugToolsHelper.get_support_path(), "tools/ice_dev_testing/out_files")

    @staticmethod
    def run_flow(flow_name):
        call(["ansible-playbook",
              os.path.join(DebugToolsHelper.get_support_path(), "tools/ice_dev_testing/ice_run.yaml"),
              "-i", os.path.join(DebugToolsHelper.get_support_path(), "tools/ice_dev_testing/ice_inventory"),
              "-e", "copy_health_check_to_directory=true", "-f", "10", "-e", "tester_name={}".format(getpass.getuser()),
              "-e", "params=\"'--run-flows={}'\"".format(flow_name), "-e", "script_type='collect_tools'"])
