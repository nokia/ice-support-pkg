from __future__ import absolute_import
import tools.paths as paths
import os

from tools.global_enums import Deployment_type
from six.moves import filter

bcmt_conf_path = None
clcm_user_input_path = None
ncs_bm_config_dir_path = None
ncs_bm_post_config_path = None


def init_bcmt_conf_path(bcmt_conf_path_arg):
    global bcmt_conf_path
    if bcmt_conf_path_arg:
        bcmt_conf_path = bcmt_conf_path_arg[0]
    else:
        bcmt_conf_path = paths.DEFAULT_BCMT_CONF_FILE


def init_clcm_user_input_path(clcm_user_input_path_arg):
    global clcm_user_input_path
    if clcm_user_input_path_arg:
        clcm_user_input_path = clcm_user_input_path_arg[0]
    else:
        clcm_user_input_path = paths.DEFAULT_NCS_CLCM_USER_INPUT


def init_ncs_bm_config_dir_path(ncs_bm_cluster_name_arg):
    '''
    the ncs conf directories hierarchy is:
    /opt/install/data/cbis-clusters/{cluster_name}/postconfig-inv.json
    we want to return the first cluster dir path that contains postconfig-inv.json
    or- if the user entered the cluster-name argument- to return the user's cluster post-config
    :rtype: tuple(int,str)
    :param ncs_bm_cluster_name_arg:str
    :return:
    (is_succeed, cluster_conf_path (/opt/install/data/cbis-clusters/{cluster_name}/))
    '''
    global ncs_bm_config_dir_path
    post_config_pattern = '{}/' + paths.NCS_BM_POST_CONFIG
    if ncs_bm_cluster_name_arg:
        # if user entered cluster name- we check if this cluster has post-config.
        # if not- we returns an error
        cluster_conf_dir = '/opt/install/data/cbis-clusters/{cluster_name}'.format(
            cluster_name=ncs_bm_cluster_name_arg)
        post_config_path = post_config_pattern.format(cluster_conf_dir)
        if os.path.isfile(post_config_path):
            ncs_bm_config_dir_path = cluster_conf_dir
            return True, ''
        return False, "user's cluster-name post-config file - {} does not exist".format(post_config_path)

    elif os.path.isdir(paths.NCS_BM_CLUSTER_DATA_DIR):
        '''
        if user didn't enter the cluster-name, we check if paths.NCS_BM_CLUSTER_DATA_DIR contains more than one dir of cluster name.
        if there's more than one cluster name folder, we returns an error and asking to specify cluster name
        if there's only one cluster name folder, we verify it contains the postconfig-inv.json
        '''
        path = paths.NCS_BM_CLUSTER_DATA_DIR
        list_subfolders = list(filter(os.path.isdir, [os.path.join(path,f) for f in os.listdir(path)]))
        if len(list_subfolders) > 1:
            return False, "Path {} has more than one of cluser name folder.\n" \
                          "Run again and specify the cluster name by using '--ncs-bm-cluster-name' flag".format(paths.NCS_BM_CLUSTER_DATA_DIR)
        dir_full_path = os.path.join(paths.NCS_BM_CLUSTER_DATA_DIR, list_subfolders[0])
        post_config_path = post_config_pattern.format(dir_full_path)
        if os.path.isfile(post_config_path):
            ncs_bm_config_dir_path = dir_full_path
            return True, ''
    return None, "no {} file was found. The path may not exist or may not be mounted inside the container.".format(paths.NCS_BM_POST_CONFIG)


def init_ncs_bm_post_config_path():
    assert ncs_bm_config_dir_path
    global ncs_bm_post_config_path
    ncs_bm_post_config_path = os.path.join(ncs_bm_config_dir_path, paths.NCS_BM_POST_CONFIG)


def init_paths_by_user_args(bcmt_conf_path_arg, clcm_user_input_path_arg):
    init_bcmt_conf_path(bcmt_conf_path_arg)
    init_clcm_user_input_path(clcm_user_input_path_arg)


def init_run_time_paths(
        deployment_type,
        ncs_bm_cluster_name_arg):
    if deployment_type == Deployment_type.NCS_OVER_BM:
        is_ok, msg = init_ncs_bm_config_dir_path(ncs_bm_cluster_name_arg)
        if not is_ok:
            return False, msg
        init_ncs_bm_post_config_path()
    return True, ''