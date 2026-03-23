from __future__ import absolute_import
# return the list of flowes in that can be ran
# (this was part of the invoker)
from tests.debug_tools.collect_tools.logs_by_roles_flow import LogsByRolesFlow
from tests.debug_tools.collect_tools.certificates_by_roles_flow import CertificatesByRolesFlow


class CollectToolsFlowsList:

    @staticmethod
    def get_list_of_flows():
        return [
            LogsByRolesFlow,
            CertificatesByRolesFlow
        ]
