from __future__ import absolute_import
from __future__ import print_function
from tools import user_params
from tools.adapter import initialize_adapter_instance
from tools.global_logging import log_and_print, log_error
import os
import tools.user_params
from tools.ExecutionModule.execution_helper import ExecutionHelper

try:
    import redis
except ImportError:
    from PythonLibraries import redis
import tools.paths as paths
import tools.DynamicPaths as DynamicPaths
from tools.global_enums import *
from tools.python_versioning_alignment import *
import tools.SubVersions as SubVersions
from tools.lazy_global_data_loader import *
import traceback

class EnvironmentInfo:
    def __init__(self):
        self.version_str, self.sub_version_str, self.build, self.bcmt_build = None, None, None, None
        self.deployment_type = self.fetch_deployment_type()
        self.version = None
        self.sub_version = None
        self.base_conf = None
        self.inventory_path = None
        self.priority_packs = None
        self.cluster_name = None
        self.ncs_config_type = ''
        self.ncs_clusters_names = None
        self.is_docker_support_standard_timeout = None

    def collect_info(self, version_arg):
        try:
            is_success, message, self.inventory_path = self.fetch_inventory_path()
            if not is_success:
                return False, message

            if version_arg:
                self.version_str = version_arg[0]
                self.sub_version_str, self.build = None, None
            else:
                version_info_dict, message = self.fetch_version_str_and_build()
                if not version_info_dict['version']:
                    log_and_print(message, 'error')
                    return False, message
                self.version_str = version_info_dict['version']
                self.sub_version_str = version_info_dict['sub_version']
                self.build = version_info_dict['build']
                self.bcmt_build = version_info_dict.get('bcmt_build')
                log_and_print('Detected version: version: {}, build: {}, bcmt_build: {}'.format(
                    self.version_str, self.build, self.bcmt_build))
            self.version = self.fetch_version()

            if self.version == Version.NOT_EXIST_VERSION:
                return False, "version {} is not supported for this deployment type".format(self.version_str)

            self.sub_version = self.fetch_sub_version()

            ### CONFIG checks and Numer of NCS Clusters Present NCS22 ######
            if (self.version >= Version.V22 and self.deployment_type == "ncs_bare-metal"):
                self.ncs_config_type = self.fetch_ncs_config_type()
                self.ncs_clusters_names = self.fetch_ncs_clusters_names()
            else:
                pass

            ##############################################################
            self.cluster_name = self.fetch_cluster_name()

            self.priority_packs = self.fetch_priority_packs()

            self.is_docker_support_standard_timeout = ExecutionHelper.is_support_standard_timeout()

            is_ok, msg, self.base_conf = self.fetch_base_conf()
            if not is_ok:
                return False, msg

            initialize_adapter_instance(self.deployment_type, self.version)

            return True, ""
        except Exception as e:
            full_trace = get_full_trace()
            print(full_trace)
            return False, 'could not collect info :\n {}'.format(str(e))

    def fetch_deployment_type(self):
        raise NotImplementedError

    def fetch_version_str_and_build(self):
        raise NotImplementedError

    def fetch_version(self):
        return Version.convert_str_to_version_const(self.deployment_type, self.version_str)

    def fetch_sub_version(self):
        if self.sub_version_str:
            return SubVersions.SUB_VERSION_DICT.get(self.deployment_type, {}). \
                get(self.version, {}).get(self.sub_version_str)
        return None

    #########################################

    def fetch_ncs_config_type(self):
        return redis.Redis(db=7).get('general:setup_type')

    def fetch_ncs_clusters_names(self):
        return redis.Redis().get('cmdata.clusters')

    ###########################################

    def fetch_priority_packs(self):
        raise NotImplementedError

    def fetch_inventory_path(self):
        # returns tuple: is_success, msg,  path
        raise NotImplementedError

    def fetch_base_conf(self):
        raise NotImplementedError

    @staticmethod
    def fetch_cluster_name():
        raise NotImplementedError


class CbisEnvironmentInfo(EnvironmentInfo):
    def fetch_deployment_type(self):
        return Deployment_type.CBIS

    # this function gets the str version without converting it to enum
    def fetch_version_str_and_build(self):
        return CbisEnvironmentInfo.fetch_version_str_and_build_cbis_style()

    @staticmethod
    def fetch_version_str_and_build_cbis_style():
        log_and_print('Fetch version from {}'.format(paths.CBIS_VERSION_FILE))
        version_info_dict = {'version': None,
                             'sub_version': None,
                             'build': None}
        host_operator = ExecutionHelper.get_hosting_operator(True)
        data_loaded = host_operator.get_dict_from_file(paths.CBIS_VERSION_FILE, file_format='yaml')
        version_str = data_loaded.get("version")
        if version_str:
            version_info_dict['version'] = re.findall(r"\d+.\d+.\d+", version_str)[0]

            version_str_splitd = version_str.split('-')
            if len(version_str_splitd) < 3:
                version_info_dict['build'] = 0
            else:
                build_number_str = version_str_splitd[2]
                build_number_str = to_unicode(build_number_str, 'utf-8')

                if not build_number_str.isnumeric():
                    return version_info_dict, "issue in parsing the build number at {} file, expected number found {}".\
                        format(paths.CBIS_VERSION_FILE, build_number_str)
                version_info_dict['sub_version'] = int(build_number_str)
                version_info_dict['build'] = int(build_number_str)
            return version_info_dict, ""
        log_and_print('Failed to fetch version from {}'.format(paths.CBIS_VERSION_FILE), level='error')
        return version_info_dict, "no version field in {} file".format(paths.CBIS_VERSION_FILE)

    def fetch_priority_packs(self):
        installed_hotfix_dict = {}
        host_operator = ExecutionHelper.get_hosting_operator(True)
        if host_operator.file_utils.is_file_exist(paths.CBIS_HOTFIX_FILE) and \
                not host_operator.file_utils.is_file_empty(paths.CBIS_HOTFIX_FILE):
            hotfix_list = host_operator.get_dict_from_file(paths.CBIS_HOTFIX_FILE, "json")
            for hotfix in hotfix_list:
                if hotfix.get('status', {}).get('result') == 'success':
                    hotfix_name = hotfix.get('hotfix')
                    hotfix_date = hotfix.get('time')
                    installed_hotfix_dict[hotfix_name] = hotfix_date
        return installed_hotfix_dict

    def fetch_base_conf(self):
        host_operator = ExecutionHelper.get_hosting_operator()
        if not host_operator.file_utils.is_file_exist(paths.CBIS_USER_CONFIG):
            return False, "file {} does not exist".format(paths.CBIS_USER_CONFIG), None
        return True, "", host_operator.get_dict_from_file(paths.CBIS_USER_CONFIG, file_format='yaml')

    def fetch_inventory_path(self):
        return True, "", tools.user_params.path_to_cbis_hosts_file

    @staticmethod
    def fetch_cluster_name():
        return None


class NCSBareMetalEnvironmentInfo(EnvironmentInfo):
        
    def get_ncs_version_info(self, should_print=False):
        host_operator = ExecutionHelper.get_hosting_operator()
        cmd = "openstack cbis version --ncs"
        if should_print:
            log_and_print("Fetch version by running command '{}'".format(cmd))
        exit_code, out, err = host_operator.run_cmd(cmd)
        if exit_code != 0:
            if should_print:
                log_and_print("out of cmd:\n{}".format(out))
                log_and_print("Failed to fetch version by running command '{}'".format(cmd), level='error')
            return None
        return out

    def get_bcmt_version(self):
        version_info_dict = {'version': None,
                             'sub_version': None,
                             'build': None,
                             'bcmt_build': None}
        ncs_version_info = self.get_ncs_version_info(should_print=True)
        if ncs_version_info:
            full_version = re.findall(r"BCMT.*?\d+.\d+.\d+-?(\d+)", ncs_version_info)
            if len(full_version) != 1:
                log_and_print("Failed to fetch version from BCMT field", level='error')
                return version_info_dict, 'Failed to get version and build'
            version_info_dict['bcmt_build'] = full_version[0]

            full_version = re.findall(r"build.*?(\d+.\d+.\d+)-?(\d+)", ncs_version_info)
            if len(full_version) != 1:
                return version_info_dict, 'Failed to get version and build'
            version_info_dict['version'], version_info_dict['build'] = full_version[0]
            version_info_dict['sub_version'] = version_info_dict['version'].split('.')[1]

        return version_info_dict, ""

    def fetch_deployment_type(self):
        return Deployment_type.NCS_OVER_BM

    def NCS_BM_version_style(self):
        version_info_dict = {'version': None,
                             'sub_version': None,
                             'build': None,
                             'bcmt_build': None}
        data_loaded = ExecutionHelper.get_hosting_operator().get_dict_from_file(
            paths.NCS_BM_VERSION_FILE, file_format='yaml')
        version_info_dict['version'] = data_loaded.get('bcmt_ver_main')
        version_info_dict['bcmt_build'] = data_loaded.get('bcmt_ver_sub')

        if not (version_info_dict['version'] and version_info_dict['bcmt_build']):
            return version_info_dict, 'Failed to get version and BCMT build info from {}'.format(paths.NCS_BM_VERSION_FILE)
        version_info_dict['sub_version'] = re.findall(r"\d+.(\d+).\d+", version_info_dict['version'])

        if len(version_info_dict['sub_version']) != 1:
            return version_info_dict, 'Failed to get sub version info from {}'.format(paths.NCS_BM_VERSION_FILE)
        version_info_dict['sub_version'] = version_info_dict['sub_version'][0]

        ncs_version_info = self.get_ncs_version_info()
        if ncs_version_info:
            full_version = re.findall(r"build.*?\d+.\d+.\d+-?(\d+)", ncs_version_info)
            version_info_dict['build'] = full_version[0]
        return version_info_dict, ""


    def fetch_version_str_and_build(self):
        log_and_print('Fetch version from {}'.format(paths.NCS_BM_VERSION_FILE))
        if os.path.exists(paths.NCS_BM_VERSION_FILE):
            version_info_dict, msg = self.NCS_BM_version_style()
            if version_info_dict['version']:
                return version_info_dict, msg
        else:
            log_and_print('Failed to fetch version from {} as file not exists'.format(paths.NCS_BM_VERSION_FILE), level='error')

        version_info_dict, msg = self.get_bcmt_version()
        if version_info_dict['version']:
            return version_info_dict, msg

        version_info_dict, msg = CbisEnvironmentInfo.fetch_version_str_and_build_cbis_style()

        if version_info_dict['version']:
            return version_info_dict, msg
        else:
            return version_info_dict,  "No version files where found: no {} and not by using 'openstack cbis version --ncs'" \
                           " ".format(paths.NCS_BM_VERSION_FILE)

    def fetch_priority_packs(self):
        installed_hotfix_dict = {}
        host_operator = ExecutionHelper.get_hosting_operator()

        try:
            cmd = 'sudo -E bash -c "openstack cbis version --ncs -f json"'
            out = host_operator.get_output_from_run_cmd(cmd)
            pp_version = self.get_pp_version(json.loads(out))

            if pp_version is None:
                if self.version == Version.V22_12 and self.build == '274':
                    # The product doesn't display properly that NCS 22.12 with build 274 is actually MP1
                    hotfix_name = 'NCS {}-MP1'.format(self.version)
                    installed_hotfix_dict[hotfix_name] = ''
                elif self.version == Version.V22_7 and self.build == '264':
                    # The product doesn't display properly that NCS 22.7 with build 264 is actually PP2
                    hotfix_name = 'NCS{}-PP2'.format(self.version)
                    installed_hotfix_dict[hotfix_name] = ''
                return installed_hotfix_dict
            else:
                hotfix_name = pp_version
                hotfix_date = ""
            installed_hotfix_dict[hotfix_name] = hotfix_date
            return installed_hotfix_dict
        except Exception:
            full_trace = get_full_trace()
            log_and_print('Failed to fetch priority pack:\n{}'.format(full_trace))
            return {"N/A": ""}

    def get_pp_version(self, version_info):
        for option in version_info:
            if option.get('Component') == self.cluster_name:
                return option.get('Version').split('\n')[-1] if option.get('Version') else None
        return None

    def fetch_base_conf(self):
        assert DynamicPaths.ncs_bm_post_config_path
        ExecutionHelper.copy_single_file_to_container(DynamicPaths.ncs_bm_post_config_path, "/tmp/post_config_file")
        DynamicPaths.ncs_bm_post_config_path = "/tmp/post_config_file"
        local_operator = ExecutionHelper.get_local_operator(is_log_initialized=False)
        user_uid = ExecutionHelper.get_local_uid()
        local_operator.file_utils.change_file_owner(user_uid, DynamicPaths.ncs_bm_post_config_path)
        local_operator.file_utils.change_file_permissions(775, DynamicPaths.ncs_bm_post_config_path)

        with open(DynamicPaths.ncs_bm_post_config_path) as f:
            post_conf_dict = json.load(f)
        conf_dict = post_conf_dict.get('all', {}).get('vars')
        if not conf_dict:
            return False, 'cannot find the conf parameters in the conf file', None
        return True, "", conf_dict

    def fetch_inventory_path(self):
        assert DynamicPaths.ncs_bm_post_config_path
        return True, "", DynamicPaths.ncs_bm_post_config_path

    @staticmethod
    def fetch_cluster_name():
        assert DynamicPaths.ncs_bm_config_dir_path
        split_path = DynamicPaths.ncs_bm_config_dir_path.split('/')
        assert len(split_path) > 1
        return split_path[-1]


class NcsCnaEnvironmentInfo(EnvironmentInfo):
    @staticmethod
    @lazy_global_data_loader
    def get_bcmt_config_dict():
        return ExecutionHelper.get_local_operator().get_dict_from_file(DynamicPaths.bcmt_conf_path)

    @staticmethod
    @lazy_global_data_loader
    def get_clcm_user_input_dict():
        return ExecutionHelper.get_local_operator().get_dict_from_file(DynamicPaths.clcm_user_input_path, 'yaml')

    @staticmethod
    def get_inventory_path():
        configuration = ExecutionHelper.get_configuration()
        host_operator = ExecutionHelper.get_hosting_operator()

        if configuration["bcmt_config_file"]:
            DynamicPaths.bcmt_conf_path = configuration["bcmt_config_file"]

        if not configuration["user_input_container_name"]:
            if configuration["user_config_file"]:
                DynamicPaths.clcm_user_input_path = configuration["user_config_file"]
        else:
            container_name = configuration["user_input_container_name"]
            container_exec_prefix = NcsCnaEnvironmentInfo._get_container_exec_prefix_by_container_name(container_name)
            user_input_path = configuration["user_config_file"]
            user_input_content = host_operator.get_output_from_run_cmd("{} cat {}".format(container_exec_prefix,
                                                                                          user_input_path),
                                                                       add_bash_timeout=True)

            DynamicPaths.clcm_user_input_path = os.path.join("/tmp", "user_input.yml")
            with open(DynamicPaths.clcm_user_input_path, "w") as f:
                f.write(user_input_content)

        if not configuration["inventory_container_name"]:
            return configuration["inventory_file"]

        container_name = configuration["inventory_container_name"]
        container_exec_prefix = NcsCnaEnvironmentInfo._get_container_exec_prefix_by_container_name(container_name)

        node_inventory_path = configuration["inventory_file"]

        node_inventory_content = host_operator.get_output_from_run_cmd("{} cat {}".format(container_exec_prefix,
                                                                                          node_inventory_path),
                                                                       add_bash_timeout=True)

        _, inventory_file_name = os.path.split(node_inventory_path)
        inventory_path_in_ice_container = os.path.join("/tmp", inventory_file_name)

        with open(inventory_path_in_ice_container, "w") as f:
            f.write(node_inventory_content)

        return inventory_path_in_ice_container

    @staticmethod
    def _get_container_exec_prefix_by_container_name(container_name):
        podman_docker = ExecutionHelper.get_podman_docker()
        container_exec_prefix = "sudo {} exec -i {}".format(podman_docker, container_name)

        return container_exec_prefix

    def fetch_version_str_and_build(self):
        version_info_dict = {'version': None,
                             'sub_version': None,
                             'build': None}
        host_operator = ExecutionHelper.get_hosting_operator()
        try:
            podman_or_docker = host_operator.get_output_from_run_cmd("sudo find /usr/bin/podman | wc -l")

            podman_docker = "podman" if podman_or_docker.strip() == "1" else "docker"
            cmd = "sudo {} exec bcmt-admin ncs -v".format(podman_docker)
            log_and_print("Fetch version by running command '{}'".format(cmd))
            out = host_operator.get_output_from_run_cmd(cmd, add_bash_timeout=True)
            version = re.findall(r"\d+.\d+.\d+", out)

            if not version:  # In ncs 23.10, version out doesn't include build number
                version = re.findall(r"\d+.\d+", out)

            version_info_dict['version'] = version[0]
            _, version_info_dict['sub_version'] = re.findall(r"\d+", out)[0:2]

            return version_info_dict, ""
        except Exception as e:
            full_trace = get_full_trace()
            print(full_trace)
            return version_info_dict, 'Could not get ncs version \n' + str(e)

    def fetch_inventory_path(self):
        return True, '', NcsCnaEnvironmentInfo.get_inventory_path()

    @staticmethod
    def fetch_cluster_name():
        if os.path.isfile(DynamicPaths.bcmt_conf_path):
            return NcsCnaEnvironmentInfo.get_bcmt_config_dict().get('cluster_config', {}).get('cluster_name')

        if os.path.isfile(DynamicPaths.clcm_user_input_path):
            return NcsCnaEnvironmentInfo.get_clcm_user_input_dict().get('Clusters', {}).get('cluster-01', {}).get(
                'cluster_name')

        return None

    def fetch_deployment_type(self):
        raise NotImplementedError

    def fetch_versions(self, out, installed_hotfix_dict):
        hotfix_number = out.strip()
        hotfix_mapping_dict_of_version = SubVersions.CNA_HOTFIX_MAPPING_DICT.get(self.version, {})
        hotfix_date = ""
        if hotfix_mapping_dict_of_version and hotfix_number in list(hotfix_mapping_dict_of_version.keys()):
            hotfix_name = hotfix_mapping_dict_of_version.get(hotfix_number)
            installed_hotfix_dict[hotfix_name] = hotfix_date
        elif hotfix_number == "None" or hotfix_number == "0":
            if self.deployment_type == Deployment_type.NCS_OVER_OPENSTACK and self.version == Version.V22_12:
                builds = self.get_ncs_build()
                if not [build for build in builds if build != '274']:
                    hotfix_name = "MP1"
                    installed_hotfix_dict[hotfix_name] = hotfix_date
        else:
            pass

    def get_ncs_build(self):
        host_operator = ExecutionHelper.get_hosting_operator()
        out = host_operator.get_output_from_run_cmd("sudo cat /etc/bcmt-deployserver-release | "
                                                    "grep -e baseos -e deployserver")
        builds = re.findall(r"\d+.\d+.\d+-?(\d+).", out)
        return builds

    def patch_hotfix_dictionary(self, version, installed_hotfix_dict):
        installed_hotfix_dict = installed_hotfix_dict
        host_operator = ExecutionHelper.get_hosting_operator()

        if version >= Version.V22:
            out = host_operator.get_output_from_run_cmd("sudo podman ps | grep -i 'bcmt-admin' | head -1 | "
                                                        "awk '{print $2}' | cut -d ':' -f2 | cut -d '.' -f3")
            self.fetch_versions(out, installed_hotfix_dict)
                       
        else:
            out = host_operator.get_output_from_run_cmd("sudo docker ps | grep -i 'bcmt-admin' | head -1 | "
                                                        "awk '{print $2}' | cut -d ':' -f2 | cut -d '.' -f3")
            self.fetch_versions(out, installed_hotfix_dict)
    
    def fetch_priority_packs(self):
        installed_hotfix_dict = {}
        try:
            self.patch_hotfix_dictionary(self.version, installed_hotfix_dict)
            return installed_hotfix_dict
        
        except Exception:
            full_trace = get_full_trace()
            print(full_trace)
            return {"N/A": ""}

    def fetch_base_conf(self):
        if os.path.exists(DynamicPaths.bcmt_conf_path):
            return True, "", NcsCnaEnvironmentInfo.get_bcmt_config_dict()

        return True, "", None


class NcsVsphereEnvironmentInfo(NcsCnaEnvironmentInfo):
    def fetch_deployment_type(self):
        return Deployment_type.NCS_OVER_VSPHERE

    def fetch_priority_packs(self):
        installed_hotfix_dict = {}
        try:
            self.patch_hotfix_dictionary(self.version, installed_hotfix_dict)
            return installed_hotfix_dict                    
        except Exception:
            full_trace = get_full_trace()
            print(full_trace)
            return {"N/A": ""}


class NcsOpenStackEnvironmentInfo(NcsCnaEnvironmentInfo):
    def fetch_deployment_type(self):
        return Deployment_type.NCS_OVER_OPENSTACK
