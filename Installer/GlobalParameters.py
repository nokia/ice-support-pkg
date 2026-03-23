import yaml
import os
import Paths
from CbisManagerClient import CbisManagerClient
from DeploymentType import DeploymentType
from collections import OrderedDict

conf_dict = None
cbis_manager_client = None
version = None
plugins_paths_list = None
deployment_type = None
dict_installation_result = None
env_configuration = None

def load_conf():
    assert os.path.isfile(Paths.CONF_FILE)
    with open(Paths.CONF_FILE, 'r') as stream:
        global conf_dict
        conf_dict = yaml.safe_load(stream)


def init_cbis_manager_client():
    assert conf_dict
    timeout_seconds = 5
    cbis_manager_conf = conf_dict.get('cbis manager')
    global cbis_manager_client
    cbis_manager_client = CbisManagerClient(
        cbis_manager_conf.get('user name'),
        cbis_manager_conf.get('password'),
        cbis_manager_conf.get('hypervisor ip'),
        timeout_seconds
    )


def init_version(version_val):
    global version
    version = version_val


def init_dict_installation_result():
    global dict_installation_result
    dict_installation_result = OrderedDict()


def init_plugins_paths_list():
    assert os.path.isdir(Paths.PLUGINS_DIR)
    global plugins_paths_list
    plugins_paths_list = [os.path.join(Paths.PLUGINS_DIR, f)
                          for f in os.listdir(Paths.PLUGINS_DIR)
                          if f.endswith('tar.gz')]


def init_deployment_type(detected_deployment_type):
    assert detected_deployment_type in DeploymentType.get_available_deployment_types()
    global deployment_type
    deployment_type = detected_deployment_type


def init_env_configuration(configuration):
    global env_configuration
    env_configuration = configuration
