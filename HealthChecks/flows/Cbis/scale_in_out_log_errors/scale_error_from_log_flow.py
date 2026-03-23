from __future__ import absolute_import
from HealthCheckCommon.log_flows.base_log_issues_finder_flow import *
from tools.paths import *

class scaleIsErrorInLogFlow(Log_issues_finder_flow):

    def get_conf_file_name(self):
        return ERROR_IN_LOG_CONFIG_FILE

    def command_name(self):
        return "scale_log_error_flow"

    def deployment_type_list(self):
        return [Deployment_type.CBIS]


