from __future__ import absolute_import
from HealthCheckCommon.operations import *
import yaml

#decripted !!!
'''
class env_info(InformatorValidator):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._is_pure_info = True
        self._unique_operation_name = "get_env_info"
        self._title_of_info = "Print environment host information"


    def _set_system_info(self):
        stream = self.get_output_from_run_cmd("cat /home/stack/templates/scale-info.yaml")
        scale_info = yaml.load(stream)
        for key, value in scale_info['parameter_defaults'].items():
            if key.endswith('Count'):
                self._system_info = ('{} : {}'.format(key, value))
                return self._system_info
'''