from __future__ import absolute_import
from HealthCheckCommon.validator import Validator
from tools.global_enums import *
import tools.sys_parameters as sys_parameters


class IronicNodeActiveValidator(Validator):
    # ToDo - This code should run only on cluster manager.
    # In NCS Bare-metal there are two types of deployment.
    # Central (dedicated cluster manager) and cluster( runs on mater node)
    # todo: Liat / Hodaya, implement this requirement :
    # know if this  NCS Bare-metal there are two types of deployment.
    # allowed different rules for different deployment types

    # first use - is for CBIS Only. next sprint - ncs

    # this is an important test, mainly before scaling and patch adding
    # based on:
    # https://confluence.ext.net.nokia.com/display/CBCS/How+ansible+was+set+up+and+push+changes+to+all+the+nodes+in+CBIS+cluster?focusedCommentId=1143092124
    # NCS validation code is valid for Baremetal NCS 22.7 and above as there was a bug in old NCS baremetal list output (JIRA: https://jiradc2.ext.net.nokia.com/browse/NCSFM-4559), this code is not applicable for NCS older than 22.7 versions
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.UC],
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MANAGER]
    }

    def set_document(self):

        self._unique_operation_name = "all_ironic_nodes_are_ready"
        self._title = "Verify nodes in Ironic are ready"
        self._failed_msg = "Not all nodes in Ironic are ready"
        self._severity = Severity.ERROR

        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.APPLICATION_DOMAIN]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        ready_list, not_ready_list = self.get_nodes_lists()
        if len(ready_list) == 0:
            self._failed_msg = "None of the nodes is Active in Ironic list"
            return False
        if len(not_ready_list) > 0:
            self._failed_msg = "The following nodes are not Active in Ironic list:\n{}".format(",\n".join(not_ready_list))
            return False
        return True

    def get_nodes_lists(self):
        cmd = "source {}; openstack baremetal node list -f yaml".format(self.system_utils.get_stackrc_file_path())
        nodes_list = self.get_output_from_run_cmd(cmd)
        return IronicNodeActiveValidator.parse_nodes_list(nodes_list)

    @staticmethod
    def parse_nodes_list(node_list_out):
        not_ready_list = []
        ready_list = []
        rows = PythonUtils.yaml_safe_load(node_list_out)

        for index, check in enumerate(rows):
            if len(rows) > 0:
                if sys_parameters.get_deployment_type() == Deployment_type.CBIS and (rows[index]['Provisioning State'] != 'active' or rows[index]['Power State'] != 'power on' or \
                            rows[index]['Maintenance'] != False or rows[index]['Instance UUID'] == None):
                    not_ready_list.append(rows[index]['Name'])
                elif sys_parameters.get_deployment_type() == Deployment_type.NCS_OVER_BM and (rows[index]['Provisioning State'] != 'active' or rows[index]['Power State'] != 'power on' or \
                         rows[index]['Maintenance'] != False):
                    not_ready_list.append(rows[index]['Name'])
                else:
                    ready_list.append(rows[index]['Name'])

        return ready_list, not_ready_list