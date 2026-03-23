from __future__ import absolute_import
from HealthCheckCommon.validator import Validator
from tools.global_enums import Objectives, Severity, BlockingTag, Deployment_type, ImplicationTag
import HealthCheckCommon.PreviousResults as PreviousResults


class OperationsBlocker(Validator):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.UC],
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MANAGER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.DEPLOYER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.DEPLOYER]
    }

    def set_document(self):
        self.operation_name = self.get_operation_name()
        self._title = "{operation} blocker".format(operation=self.operation_name)
        self._failed_msg = "TBD"
        self._severity = Severity.CRITICAL


    def get_operation_name(self):
        raise NotImplementedError

    def get_blocking_tag(self):
        raise NotImplementedError


    def is_validation_passed(self):
        is_passed = True
        failed_validations_title = []
        all_results = PreviousResults.get_all_collected_result()
        for flow_name in all_results:
            flow_details = all_results[flow_name]['details']
            for host_name in flow_details:
                host_details = flow_details[host_name]
                for validation_name in host_details:
                    validation_details = host_details[validation_name]
                    blocking_tag_name = self.get_blocking_tag()
                    assert blocking_tag_name in BlockingTag.get_all_blocking_tags(), "Unsupported blocking tag"
                    # Note - NA/sys_problem is like pass==True in this logic
                    if validation_details['pass'] is False and blocking_tag_name in validation_details['blocking_tags']:
                        is_passed = False
                        failed_validations_title.append(validation_details['description_title'])

        failed_validations_set = set(failed_validations_title)
        if is_passed is False:
            self._failed_msg = """
The following validations failed and are blocking {}:

{}

More details about these failed validations can be found in the current Healthcheck report.
You should not run {} before fixing these issues.
            """.format(self.operation_name, "\n".join(failed_validations_set), self.operation_name)

        return is_passed


class ScaleBlocker(OperationsBlocker):

    def set_document(self):
        OperationsBlocker.set_document(self)
        self._unique_operation_name = "scale_blocker"
        self._implication_tags = [ImplicationTag.PRE_OPERATION]

    def get_operation_name(self):
        return "scale"

    def get_blocking_tag(self):
        return BlockingTag.SCALE


class UpgradeBlocker(OperationsBlocker):

    def set_document(self):
       OperationsBlocker.set_document(self)
       self._unique_operation_name = "upgrade_blocker"
       self._implication_tags = [ImplicationTag.PRE_OPERATION]

    def get_operation_name(self):
        return "upgrade"

    def get_blocking_tag(self):
        return BlockingTag.UPGRADE


class MigrationBlocker(OperationsBlocker):

    def set_document(self):
        OperationsBlocker.set_document(self)
        self._unique_operation_name = "migration_blocker"
        self._implication_tags = [ImplicationTag.NOTE]

    def get_operation_name(self):
        return "migration"

    def get_blocking_tag(self):
        return BlockingTag.MIGRATION

class CertRenewalBlocker(OperationsBlocker):

    def set_document(self):
        OperationsBlocker.set_document(self)
        self._unique_operation_name = "cert_renewal"
        self._implication_tags = [ImplicationTag.NOTE]

    def get_operation_name(self):
        return "certification renewal"

    def get_blocking_tag(self):
        return BlockingTag.CERT_RENEWAL
