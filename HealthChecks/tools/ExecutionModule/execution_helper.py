from __future__ import absolute_import
import os
import re
import sys

from tools import paths
from tools.Exceptions import HostNotReachable
from tools.python_utils import PythonUtils

# Add parent of working dir to path to be able to import ice/lib/global_configurations.py
sys.path.append(os.path.join(os.getcwd(), ".."))
import global_configurations


class ExecutionHelper:
    configuration = None
    _hosting_operator = None
    _local_operator = None

    @staticmethod
    def get_container_id():
        container_name = ExecutionHelper.get_container_name()
        podman_docker = ExecutionHelper.get_podman_docker()
        cmd = 'sudo {} inspect {} | jq .[0].Id'.format(podman_docker, container_name)
        exit_code, container_id, err = ExecutionHelper.get_hosting_operator(False).run_cmd(cmd)
        if exit_code == 0:
            return container_id.strip()
        assert False, "Failed to get container ID by running:\n{}".format(cmd)

    @staticmethod
    def get_podman_docker():
        operator = ExecutionHelper.get_hosting_operator(is_log_initialized=False)

        for item in ['podman', 'docker']:
            exit_code, out, err = operator.run_cmd("which {}".format(item), timeout=30)
            if exit_code == 0:
                return item

        assert False, "podman and docker are not enabled on the system"

    @staticmethod
    def get_hosting_operator(is_log_initialized=True):
        assert ExecutionHelper._hosting_operator, "Please init host operator before use"

        ExecutionHelper._hosting_operator.is_log_initialized = is_log_initialized

        return ExecutionHelper._hosting_operator

    @staticmethod
    def get_local_operator(is_log_initialized=True):
        assert ExecutionHelper._local_operator, "Please init local operator before use"

        ExecutionHelper._local_operator.is_log_initialized = is_log_initialized

        return ExecutionHelper._local_operator

    @staticmethod
    def get_mem_usage_stats_out():
        container_name = ExecutionHelper.get_container_name()
        host_operator = ExecutionHelper.get_hosting_operator(is_log_initialized=False)
        cmd = 'sudo bash -c "{} stats {} --no-stream"'.format(
            ExecutionHelper.get_podman_docker(),
            container_name)
        stats_out = host_operator.get_output_from_run_cmd(cmd)

        # implemented  manually "--format "{{.MemUsage}}" for older docker versions (cbis 18.5)
        stats_out = stats_out.replace("\t", "   ")
        mem_usage_key = "MEM USAGE / LIMIT"

        assert mem_usage_key in stats_out, "missing {} in cmd: '{}' output".format(mem_usage_key, cmd)
        stats_list_headers = re.split(r"\s\s+", stats_out.splitlines()[0])
        stats_list_out = re.split(r"\s\s+", stats_out.splitlines()[1])
        memory_index = stats_list_headers.index("MEM USAGE / LIMIT")

        return stats_list_out[memory_index]

    @staticmethod
    def get_free_memory():
        memory_free_str = ExecutionHelper.get_local_operator(False).get_output_from_run_cmd(
            'grep MemAvailable: /proc/meminfo')
        memory_free_localhost = int(memory_free_str.split("MemAvailable:")[1].strip().split()[0]) * 1024
        if ExecutionHelper.is_run_inside_container():
            memory_usage = ExecutionHelper.get_mem_usage_stats_out()
            total_memory = memory_usage.split('/')[1].strip()
            total_memory_in_b = PythonUtils.convert_str_with_unit_to_bytes(total_memory)
            memory_used = memory_usage.split('/')[0].strip()
            memory_used_in_b = PythonUtils.convert_str_with_unit_to_bytes(memory_used)
            container_memory_free = total_memory_in_b - memory_used_in_b
            if container_memory_free < memory_free_localhost:
                return container_memory_free
        return memory_free_localhost

    @staticmethod
    def get_memory_used():
        status = None
        result = {'peak': 0, 'rss': 0}
        try:
            status = open('/proc/self/status')
            for line in status:
                parts = line.split()
                key = parts[0][2:-1].lower()
                if key in result:
                    result[key] = int(parts[1])
        finally:
            for key in list(result.keys()):
                result[key] = "{} KB".format(result[key])
            if status is not None:
                status.close()
        return result

    @staticmethod
    def is_central_cluster(cluster_name):
        if "central" in cluster_name:
            return True
        return False

    @staticmethod
    def get_host_home_dir():
        return ExecutionHelper.get_configuration()["user_home_dir"]

    @staticmethod
    def get_host_username():
        return ExecutionHelper.get_configuration()["user"]

    @staticmethod
    def get_local_uid():
        return os.getuid()

    @staticmethod
    def get_local_gid():
        return os.getgid()

    @staticmethod
    def get_deployment_type_from_configuration():
        return ExecutionHelper.get_configuration()["deployment_type"]

    @staticmethod
    def is_run_inside_container():
        is_container = os.environ.get('IS_INSIDE_CONTAINER', False)
        if is_container:
            return True
        return False

    @staticmethod
    def get_container_name():
        return os.environ.get('ICE_CONTAINER_NAME')

    @staticmethod
    def is_support_standard_timeout():
        local_operator = ExecutionHelper.get_local_operator()
        code, out, err = local_operator.run_cmd("sudo timeout --kill-after=2 2 echo 'Hi'", 10)
        if 'Hi' in out:
            return True
        elif "timeout [-s SIG]" in err:
            return False
        assert False, "linux timeout cmd is not supported in our container linux"

    @staticmethod
    def copy_single_file_to_container(path_on_host, path_on_container):
        ExecutionHelper.get_hosting_operator(False).get_output_from_run_cmd("sudo {} cp {} {}:{}".format(
            ExecutionHelper.get_podman_docker(), path_on_host, ExecutionHelper.get_container_name(), path_on_container))

    @staticmethod
    def get_local_host_name():
        return ExecutionHelper.get_local_operator(False).get_output_from_run_cmd("hostname").strip()

    @staticmethod
    def get_path_to_pkey_from_container_to_host():
        return os.path.join(ExecutionHelper.get_host_home_dir(), ".ssh", paths.PRIVATE_KEY_FROM_CONTAINER_TO_HOST)

    @staticmethod
    def get_configuration():
        assert ExecutionHelper.configuration
        return ExecutionHelper.configuration

    @staticmethod
    def init_configuration():
        '''
        Take the configuration from ice/lib/configuration.yaml that was created by icerc
        '''
        if not os.path.isfile(global_configurations.RESULT_FILE_PATH):
            raise Exception("Expected to have {} file, Please verify you run HC from icerc".format(
                global_configurations.RESULT_FILE_PATH))
        ExecutionHelper.configuration = global_configurations.get_configuration_dict(sudo_enabled=False)

    @staticmethod
    def init_hosting_operator(host_operator):
        ExecutionHelper._hosting_operator = host_operator

    @staticmethod
    def init_local_operator(host_operator):
        ExecutionHelper._local_operator = host_operator

    @staticmethod
    def validate_connectivity_to_host():
        if ExecutionHelper.is_run_inside_container():
            host = ExecutionHelper.get_hosting_operator(is_log_initialized=False)
            exit_code, _, _ = host.run_cmd("echo hi")

            if exit_code != 0:
                raise HostNotReachable("localhost",
                                       "Can not run a command on host, please try ssh to {} user manually.".format(
                                           ExecutionHelper.get_host_username()),
                                       details="Issue can be related to user password expiry")
