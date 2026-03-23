from __future__ import absolute_import
from tools.ExecutionModule.HostExecutorsFactory.BaseHostExecutorsFactory import BaseHostExecutorFactory
from tools.global_enums import Objectives


class NcsHostExecutorFactory(BaseHostExecutorFactory):
    def improve_single_host_selection(self, connected_hosts_by_role, role_of_single, selected_single):
        ready_nodes = []

        if role_of_single == Objectives.ONE_MASTER:
            for host in connected_hosts_by_role:
                exit_code, out, err = self._host_executors_dict[host].execute_cmd("sudo kubectl get nodes | grep Ready")

                if exit_code == 0 and self._host_executors_dict[host].host_name in out:
                    ready_nodes.append(host)

            if selected_single in ready_nodes:
                return selected_single
            if ready_nodes:
                return ready_nodes[0]

        return selected_single
