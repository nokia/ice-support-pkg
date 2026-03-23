from __future__ import absolute_import
import os.path
from flows_of_sys_operations.sys_data_collector.log_collector.configuration_generator.scenarios.base_log_scenario \
    import CompositeLogGroup
from tools import paths
from tools.global_enums import Deployment_type
import tools.sys_parameters as gs
from tools.python_utils import PythonUtils


class Customized(CompositeLogGroup):
    def get_logs_of_interest(self):
        if Deployment_type.is_cbis(gs.get_deployment_type()):
            logs_of_interest_path = os.path.join(paths.LOG_COLLECTOR_CONF_FILES_DIR, paths.CBIS_LOG_OF_INTEREST)
        else:
            logs_of_interest_path = os.path.join(paths.LOG_COLLECTOR_CONF_FILES_DIR, paths.NCS_LOG_OF_INTEREST)

        with open(logs_of_interest_path) as f:
            logs_of_interest = PythonUtils.yaml_safe_load(f)
        commented_logs = {}

        for role, role_logs_list in list(logs_of_interest.items()):
            commented_logs[eval(role)] = [None] + role_logs_list

        return commented_logs

    def _write_to_yaml(self, file_path, log_path_per_roles):
        super(Customized, self)._write_to_yaml(file_path, log_path_per_roles)

        with open(file_path) as f:
            yaml_file = f.read()

        yaml_file = yaml_file.replace("\n-", "\n#-")
        yaml_file = yaml_file.replace("#- null", "- null")

        with open(file_path, "w") as f:
            f.write(yaml_file)
