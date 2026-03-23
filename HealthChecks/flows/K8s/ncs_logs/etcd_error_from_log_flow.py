from __future__ import absolute_import
from HealthCheckCommon.log_flows.base_log_issues_finder_flow import *

error_in_log_config_file="./etcd_issues_in_log_nsc.json"

class etcdIsErrorInLogValidationFlow(Log_issues_finder_flow):

    def get_conf_file_name(self):
        return error_in_log_config_file

    def command_name(self):
        return "etcd_log_error_flow"

    def deployment_type_list(self):
        return Deployment_type.get_ncs_types()