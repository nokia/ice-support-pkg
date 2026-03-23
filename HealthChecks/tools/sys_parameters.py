from __future__ import absolute_import
import tools.paths as paths
from tools.EnvironmentInfo import NcsCnaEnvironmentInfo
from tools.InitializationFactory.InitializationFactory import InitializationFactory
from tools import global_enums
from tools import user_params


# todo: maybe change to global_setup_params


def init_name_to_url_dict():
    # todo add asset dict is correct
    with open(paths.NAME_TO_URL_FILE, 'r') as name_to_url_file:
        user_params.name_to_url_dict = global_enums.json.load(name_to_url_file)


def init_globals():
    init_name_to_url_dict()
    user_params.initialization_factory = InitializationFactory()


def get_deployment_type():
    assert user_params.initialization_factory.environment_info
    return user_params.initialization_factory.environment_info.deployment_type


def get_host_executor_factory():
    assert user_params.initialization_factory.host_executor_factory
    return user_params.initialization_factory.host_executor_factory


def get_version():
    assert user_params.initialization_factory.environment_info
    return user_params.initialization_factory.environment_info.version


def get_sub_version():
    assert user_params.initialization_factory.environment_info
    return user_params.initialization_factory.environment_info.sub_version

def get_build():
    assert user_params.initialization_factory.environment_info
    return user_params.initialization_factory.environment_info.build

def get_bcmt_build():
    assert user_params.initialization_factory.environment_info
    return user_params.initialization_factory.environment_info.bcmt_build

def get_hotfix_list():
    assert user_params.initialization_factory.environment_info
    return user_params.initialization_factory.environment_info.priority_packs


def get_cluster_name():
    assert user_params.initialization_factory.environment_info
    return user_params.initialization_factory.environment_info.cluster_name


def get_base_conf():
    assert user_params.initialization_factory.environment_info
    return user_params.initialization_factory.environment_info.base_conf


def get_ncs_cna_user_conf():
    assert user_params.initialization_factory.environment_info
    assert isinstance(user_params.initialization_factory.environment_info, NcsCnaEnvironmentInfo)
    return user_params.initialization_factory.environment_info.get_clcm_user_input_dict()


def get_ncs_config_type():
    assert user_params.initialization_factory.environment_info
    return user_params.initialization_factory.environment_info.ncs_config_type.strip()


def is_ncs_central():
    if len(get_ncs_config_type()) > 0:
        if get_ncs_config_type().decode('UTF-8') == 'CENTRAL':
            return True
    return False


def is_central_cluster():
    if 'central' in get_cluster_name():
        return True
    return False

def fetch_ncs_clusters_names():
    assert user_params.initialization_factory.environment_info
    return user_params.initialization_factory.environment_info.ncs_clusters_names.strip()

def is_more_than_one_cluster():
    clusters_list = fetch_ncs_clusters_names().decode('UTF-8').split(",")
    if len(clusters_list) > 1:
        return True
    return False


def is_docker_support_standard_timeout():
    assert user_params.initialization_factory.environment_info
    return user_params.initialization_factory.environment_info.is_docker_support_standard_timeout


def get_node_names_from_system():
   hosts = list(get_host_executor_factory().get_all_host_executors().keys())
   node_names = [x for x in hosts if x]
   return node_names



def get_hostgroup_from_config():
   hostgroups_from_config = list(get_base_conf()['CBIS']['host_group_config'].keys())
   return list(hostgroups_from_config)


def get_hostgroup_name():
    hosts = get_node_names_from_system()
    hostgroups_from_config = get_hostgroup_from_config()
    final_hostgroup = []
    for hostgroup in hostgroups_from_config:
        for host in hosts:
            if hostgroup.lower() in host.lower():
                 final_hostgroup.append(hostgroup)
                 break
    return final_hostgroup
