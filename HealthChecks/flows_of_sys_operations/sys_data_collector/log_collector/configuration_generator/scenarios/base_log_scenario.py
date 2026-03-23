from __future__ import absolute_import
import os
import re
import yaml
from HealthCheckCommon.operations import SystemOperator
from tools import paths
from tools.global_enums import Objectives, Deployment_type
import tools.sys_parameters as gs


class CompositeLogGroup(SystemOperator):
    objective_hosts = [Objectives.UC, Objectives.ONE_MANAGER]

    def set_document(self):
        self._unique_operation_name = "set_json_for_{}_scenario".format(self._camel_to_snake(self.__class__.__name__))
        self._title = "Set Json for {} scenario".format(self.__class__.__name__)
        self._failed_msg = "Failed to set Json for {} scenario".format(self.__class__.__name__)
        self._run_in_parallel = True
        self._prerequisite_unique_operation_name = ""

    def get_sub_groups(self):
        return []

    def get_log_path_per_roles(self):
        roles_list = self._get_roles_for_json_keys()
        res = {role: [] for role in roles_list}
        self._update_dict_with_sub_group(res, self.get_logs_of_interest())

        for sub_group in self.get_sub_groups():
            assert type(sub_group) != type(self)
            sub_group_logs = sub_group.get_log_path_per_roles()
            self._update_dict_with_sub_group(res, sub_group_logs)
        self._clean_duplicate(res)

        return res

    def _get_roles_for_json_keys(self):
        if Deployment_type.is_cbis(gs.get_deployment_type()):
            return [Objectives.HYP, Objectives.UC, Objectives.COMPUTES, Objectives.CONTROLLERS, Objectives.STORAGE]
        return [Objectives.MASTERS, Objectives.EDGES, Objectives.WORKERS, Objectives.MANAGERS, Objectives.STORAGE,
                Objectives.MONITOR]

    def get_logs_of_interest(self):
        return {}

    def run_system_operation(self):
        log_path_per_roles = self.get_log_path_per_roles()
        self._create_file_for_scenario(log_path_per_roles)

        return True

    def _create_file_for_scenario(self, log_path_per_roles):
        log_path_per_roles = self._change_dict_keys_to_var_name(log_path_per_roles)

        if not os.path.isdir(paths.LOG_SCENARIOS_DIR_PATH):
            os.makedirs(paths.LOG_SCENARIOS_DIR_PATH)
        os.chmod(paths.LOG_SCENARIOS_DIR_PATH, 0o777)

        file_name = self._camel_to_snake(self.__class__.__name__) + ".yaml"
        file_path = os.path.join(paths.LOG_SCENARIOS_DIR_PATH, file_name)

        self._write_to_yaml(file_path, log_path_per_roles)
        os.chmod(file_path, 0o777)

    def _write_to_yaml(self, file_path, log_path_per_roles):
        with open(file_path, "w") as f:
            yaml.dump(log_path_per_roles, f, indent=2)

    def _update_dict_with_sub_group(self, logs_dict, sub_group_logs_dict):
        for objective, objective_data in list(sub_group_logs_dict.items()):
            assert type(logs_dict[objective]) is list

            if objective in list(logs_dict.keys()):
                for log_path in objective_data:
                    logs_dict[objective].append(log_path)

    def _clean_duplicate(self, logs_dict):
        for objective in list(logs_dict.keys()):
            logs_dict[objective] = list(set(logs_dict[objective]))

        for objective, objective_data in list(logs_dict.items()):
            objectives_included_by_objective = Objectives.get_included_objectives(objective)

            for log_path in objective_data:
                for included_obj in objectives_included_by_objective:
                    if log_path in logs_dict.get(included_obj, []):
                        logs_dict[included_obj].remove(log_path)

    def _camel_to_snake(self, name):
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

    def _change_dict_keys_to_var_name(self, logs_dict):
        objectives_dict = Objectives.__dict__
        res = {}
        var_key = ""

        for obj_str, obj_data in list(logs_dict.items()):
            assert obj_str in list(objectives_dict.values())
            for var_name, value in list(objectives_dict.items()):
                if value == obj_str:
                    var_key = var_name
                    break
            res[Objectives.__name__ + "." + var_key] = obj_data

        return res
