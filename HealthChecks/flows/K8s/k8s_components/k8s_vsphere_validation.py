from __future__ import absolute_import
from HealthCheckCommon.operations import *
from HealthCheckCommon.validator import Validator


class ValidateProviderId(Validator):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._unique_operation_name = "validate_provider_id"
        self._title = "Validate Provider ID"
        self._failed_msg = "Please check the Provider ID"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]

    def is_validation_passed(self):
        cmd = "sudo /usr/local/bin/kubectl get nodes -o=jsonpath='{range .items[*]}{.metadata.name}{\" \"}{end}'"
        return_code, out, err = self.run_cmd(cmd)
        out = out.rstrip()
        master_node_name = out.split(" ")
        for node in master_node_name:
            cmd_check_provider_id = "sudo /usr/local/bin/kubectl get node " + node + " -o 'jsonpath={.spec.providerID}'"
            return_code_node, out_node, err_node = self.run_cmd(cmd_check_provider_id)
            if not out_node.startswith('vsphere://'):
                return False
        return True
