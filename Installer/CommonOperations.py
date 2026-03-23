import os
import subprocess

from PopenTimeOut import PopenTimeOut
import yaml
import re
import Paths
from DeploymentType import DeploymentType
from Version import Version
from global_enums import Objectives
from generate_configuration import GenerateConfiguration
import global_configurations


def get_cbis_version():
    cmd = "cat {} | grep version".format(Paths.CBIS_VERSION_FILE)
    try:
        out, err = execute_command_on_undercloud(cmd, handle_error=True)
        if '!!binary' in out:
            return True, "", 'binary'

        # example : 19.0.0.1-1945 -> 19.0
        version = re.findall(r"\d+\.\d", out)[0]
        version = version.replace("19.1", "19A")
        version = re.sub(r"\.[0,1]", '', version)
        return True, "", version
    except Exception as e:
        return False, 'cannot get CBIS version.\n{}'.format(e), None


def get_version(deployment_type):
    if DeploymentType.is_cbis(deployment_type):
        is_success, msg, version = get_cbis_version()
        if is_success:
            version = Version.convert_str_to_version_const(deployment_type, version)
        return is_success, msg, version
    else:
        return True, "", None


def get_create_ice_dir_cmd():
    # CAUTION: Similar functionality might exist elsewhere, requiring synchronization to maintain consistency across the codebase.
    return "sudo mkdir -p /usr/share/ice/; sudo chmod 775 /usr/share/ice/"


def build_command_run_if_manager_active(command):
    return "sudo test ! -f /var/lib/.keepalived_state || " \
           "sudo grep -q '(Active)' /var/lib/.keepalived_state && {}".format(command)


def restart_cbis_manager():
    # works for 18-19A (including 19A)
    cmd = "systemctl restart cbis_manager.service"
    out, err = execute_command(cmd, timeout=60, handle_error=True)
    return out, err


def is_dir_exist(dir_path):
    exit_code, out, err = execute_command('sudo cd {dir_path}'.format(dir_path=dir_path), return_exit_code=True, handle_error=False)
    if exit_code != 0:
        return False
    return True


def is_dir_exist_on_undercloud(dir_path):
    exit_code, out, err = execute_command_on_undercloud('sudo cd {dir_path}'.format(dir_path=dir_path), return_exit_code=True,handle_error=False)
    if exit_code != 0:
        return False
    return True


def execute_command(cmd, timeout=30, handle_error=False, return_exit_code=False):
    p = PopenTimeOut(cmd, timeout=timeout)
    exit_code, out, err = p.execute_command()
    if hasattr(out, 'decode'):
        out = out.decode('ascii', 'ignore')
        err = err.decode('ascii', 'ignore')
    if handle_error:
        handle_execution_error(cmd, out, err, exit_code)
    if return_exit_code:
        return exit_code, out, err
    return out, err


def execute_command_on_undercloud(cmd, timeout=30, handle_error=False, return_exit_code=False, run_on_bkg="2>/dev/null"):
    # 2>/dev/null - errors on uc should not prevent from being able to install the support package
    if return_exit_code:
        exit_code, out, err = execute_command("ssh -o StrictHostKeyChecking=no -q stack@uc \"{}\" {}".format(
            cmd, run_on_bkg), timeout, handle_error, return_exit_code)
        return exit_code, out, err
    out, err = execute_command("ssh -o StrictHostKeyChecking=no -q stack@uc \"{}\" {}".format(cmd, run_on_bkg),
                               timeout, handle_error, return_exit_code)
    return out, err


def execute_command_on_host(cmd, host, timeout=30, handle_error=False, return_exit_code=False):
    # 2>/dev/null - errors on uc should not prevent from being able to install the support package
    if host is Objectives.UC:
        cmd = "ssh -o StrictHostKeyChecking=no -q stack@uc \"{}\" 2>/dev/null".format(cmd)
    elif host not in [Objectives.ONE_MANAGER, Objectives.HYP]:
        raise NotImplementedError('execute_command is not supported yet to {}'.format(host))
    if return_exit_code:
        exit_code, out, err = execute_command(cmd, timeout, handle_error, return_exit_code)
        return exit_code, out, err
    out, err = execute_command(cmd, timeout, handle_error, return_exit_code)
    return out, err


def execute_background_command_on_host(cmd, host):
    # 2>/dev/null - errors on uc should not prevent from being able to install the support package
    if host is Objectives.UC:
        cmd = "ssh -o StrictHostKeyChecking=no -q stack@uc \"{}\" 2>/dev/null".format(cmd)
    elif host not in [Objectives.ONE_MANAGER, Objectives.HYP]:
        raise NotImplementedError('execute_command is not supported yet to {}'.format(host))
    subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def is_file_exist(file_path, host):
    exit_code, out, err = execute_command_on_host(
        'sudo find {file_path}'.format(file_path=file_path), host=host, return_exit_code=True, handle_error=False)
    if exit_code != 0:
        return False
    return True


def handle_execution_error(cmd, out, err, exit_code):
    if exit_code != 0:
        raise Exception('\n\tcommand:{}\n\tOutput:{}\n\tError:{}'.format(cmd, out, err))


def podman_or_docker():
    host = Objectives.ONE_MANAGER
    exit_code, out, err = execute_command(cmd="ssh -o StrictHostKeyChecking=no stack@uc exit",
                                          handle_error=False, return_exit_code=True)
    if exit_code == 0:
        host = Objectives.UC
    podman_exit_code, _, _ = execute_command_on_host(cmd="which podman", handle_error=False,
                                                     host=host, return_exit_code=True)
    docker_exit_code, _, _ = execute_command_on_host(cmd="which docker", handle_error=False,
                                                     host=host, return_exit_code=True)
    if podman_exit_code == 0:
        return "podman"
    if docker_exit_code == 0:
        return "docker"
    return None


def detect_deployment_type(configuration):
    try:
        config_deployment_type = global_configurations.DeploymentType(configuration["deployment_type"])
    except ValueError:
        raise ValueError("{} is not a valid DeploymentType".format(configuration["deployment_type"]))
    return config_deployment_type


def get_env_configuration():
    return global_configurations.get_configuration_dict()


def generate_configuration():
    GenerateConfiguration(podman_or_docker(), None, None, True).create_hc_config_yaml_file()
