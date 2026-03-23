from __future__ import absolute_import
from HealthCheckCommon.log_flows.base_log_issues_finder_flow import *
from tools.paths import *

class SystemErrorInLogFlow(Log_issues_finder_flow):

    def get_conf_file_name(self):
        return SYS_ERROR_CONF_FILE

    def command_name(self):
        return "system_log_error_flow"

    def deployment_type_list(self):
        return [Deployment_type.CBIS]


