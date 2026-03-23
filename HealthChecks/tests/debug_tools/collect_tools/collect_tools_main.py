from __future__ import absolute_import
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../..")))
from tests.debug_tools.debug_tools_helper import *

sys.path.append(DebugToolsHelper.get_parent_path_until(DebugToolsHelper.get_current_dir(), "lib"))
from invoker.invoker import Invoker
from mains.validations_main import ValidationsMain
from tests.debug_tools.collect_tools.collect_tools_flows_list import CollectToolsFlowsList


class CollectToolsMain(ValidationsMain):

    def _set_invoker(self, version, deployment_type, only_specific_hosts_list=None, roles=None,
                     specific_validations=None):
        self._invoker = Invoker(
            version=version,
            flg_is_passive_type_only=True,
            deployment_type=deployment_type,
            flow_list_class=CollectToolsFlowsList,
            host_name_list=only_specific_hosts_list,
            roles=roles,
            specific_validations=specific_validations
        )


if __name__ == '__main__':
    my_main = CollectToolsMain()
    os.chdir(DebugToolsHelper.get_parent_path_until(DebugToolsHelper.get_current_dir(), "HealthChecks"))
    my_main.run_me(parser_description='run flow based scripts main')
