#!/usr/bin/python
import getpass
import subprocess
import sys
import os
import time

if sys.version_info[0] < 3:
    sys.path.append('./PythonLibraries/')
else:
    sys.path.append('./Python3Libraries/')
import argparse
from PackageInstaller import CBISPackageInstaller, NCSPackageInstaller
import Paths
import GlobalParameters
import GlobalLogging
from Validations import Validations
from PluginInstaller import PluginInstaller
import CommonOperations
from Action import Action
from DeploymentType import DeploymentType


def perform_plugins_actions(actions_list, is_plugins_disable):
    plugin_action = None
    if Action.INSTALLATION in actions_list and not is_plugins_disable:
        plugin_action = Action.INSTALLATION
    elif Action.UNINSTALLATION in actions_list:
        plugin_action = Action.UNINSTALLATION

    if not plugin_action or not DeploymentType.is_cbis(GlobalParameters.deployment_type):
        return True, ""
    # validate plugins dir exist, if not - quit
    is_plugin_dir_exist, message = Validations.validate_plugins_dir_exists()
    if not is_plugin_dir_exist:
        return False, message

    GlobalParameters.init_plugins_paths_list()

    # validate conf file exists, if not - quit
    is_conf_exists, message = Validations.validate_conf_file_exists()
    if not is_conf_exists:
        return False, message

    GlobalParameters.load_conf()

    # validate conf parameters are set
    is_conf_valid, message = Validations.validate_conf()
    if not is_conf_valid:
        return False, message

    GlobalParameters.init_cbis_manager_client()

    # check if cbis manager client is connected
    is_cbis_manager_connected, message = Validations.validate_cbis_manager_connectivity()
    if not is_cbis_manager_connected:
        return False, message

    # install plugins
    plugin_installer = None
    GlobalLogging.print_header("PLUGINS {}".format(plugin_action))
    for plugin_path in GlobalParameters.plugins_paths_list:
        plugin_installer = PluginInstaller(plugin_path)
        plugin_installer.run(plugin_action)
    if plugin_installer:
        plugin_installer.confirm_deprecated_file_tracker()
    return True, ""


def verify_undercloud_is_ready(max_retries=12, delay_seconds=10):
    undercloud_is_ready = False
    for attempt in range(1, max_retries + 1):
        return_code = subprocess.call("ssh stack@uc true".split(), stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        if return_code == 0:
            undercloud_is_ready = True
            break
        if attempt < max_retries:
            time.sleep(delay_seconds)
    if not undercloud_is_ready:
        GlobalLogging.log_and_print('INSTALLATION STOPPED:\n{}'.format("Undercloud isn't reachable by SSH"))
        sys.exit(1)

def local_installer(arguments):
    if DeploymentType.is_cbis(GlobalParameters.deployment_type):
        verify_undercloud_is_ready()
    is_ok, result_message = run_and_get_result(arguments)
    if not is_ok:
        GlobalLogging.log_and_print("""
        INSTALLATION STOPPED:
        {}
        """.format(result_message))
    else:
        if result_message:
            GlobalLogging.log_and_print(result_message)

        if not arguments.uninstall:
            if DeploymentType.is_ncs(GlobalParameters.deployment_type):
                GlobalLogging.log_and_print("ice package is located under: {}".format(os.path.expanduser("~")))
            else:
                GlobalLogging.log_and_print("ice package is located in undercloud under: /home/stack")


def run_and_get_result(args):
    # init loggers
    GlobalParameters.init_dict_installation_result()
    is_deployment_type_ok, message = Validations.validate_deployment_type(GlobalParameters.deployment_type)
    if not is_deployment_type_ok:
        return False, message

    actions_list = Action.get_actions_list_from_args(args.uninstall, args.recreate_ice_key, args.no_file_tracker,
                                                     args.rollback)
    # validate Installer is executed from Installer dir
    is_execution_path_ok, message = Validations.validate_execution_path(os.getcwd(), __file__)
    if not is_execution_path_ok:
        return False, message

    # validate execution environment
    is_execution_env_ok, message = Validations.validate_execution_environment(GlobalParameters.deployment_type)
    if not is_execution_env_ok:
        return False, message

    # check if there is newer version installed, and in such a case , get user input if to continue
    to_continue, message = Validations.validate_ice_version_is_newer_than_existing(GlobalParameters.deployment_type, actions_list, args.auto_installer, args.force_install)
    if not to_continue:
        return False, message

    package_installer = None
    if DeploymentType.is_cbis(GlobalParameters.deployment_type):
        package_installer = CBISPackageInstaller()
    elif DeploymentType.is_ncs(GlobalParameters.deployment_type):
        package_installer = NCSPackageInstaller()
    else:
        return False, "Deployment type is not supported"

    is_success, msg, version = CommonOperations.get_version(GlobalParameters.deployment_type)
    if not is_success:
        return False, msg
    GlobalParameters.init_version(version)
    for action_to_run in actions_list:
        is_success, message = package_installer.run(action_to_run)
        if not is_success:
            GlobalParameters.dict_installation_result[action_to_run] = False
            if Action.is_action_essential(action_to_run):
                return False, message
            else:
                msg = """
-------------------------------------------------
 {} FAILED 
 
 {}
------------SKIPPING-----------------------------
-------------------------------------------------
                """.format(action_to_run, message)
                GlobalLogging.log_and_print(msg)

    is_plugins_disable = not args.install_plugins
    is_success, message = perform_plugins_actions(actions_list, is_plugins_disable)
    if not is_success:
        GlobalParameters.dict_installation_result['PLUGIN'] = False
    GlobalLogging.print_results(GlobalParameters.dict_installation_result)
    if not is_success:
        return False, message
    return True, ""


def get_arguments():
    parser = argparse.ArgumentParser(description='ICE Installer')
    parser.add_argument('--uninstall', action='store_true', help='un-install ice package')
    parser.add_argument('--rollback', action='store_true', help='rollback ice package')
    parser.add_argument('--file-tracker', action='store_true', help='install ice package with file_tracker')
    parser.add_argument('--no-file-tracker', action='store_true', help='install ice package without file tracker')
    parser.add_argument('--recreate-ice-key', action='store_true', help='recreate the ice key')
    parser.add_argument('--force-install', action='store_true', default=False, help='force ice package installation regardless its version')

    # deprecated, --no-plugins becomed the default, This version is compatible with the automatic installation of CBIS
    parser.add_argument('--no-plugins', action='store_true', help='install ice package without plugins (default)')
    parser.add_argument('--install-plugins', action='store_true', help='install ice package with plugins')
    parser.add_argument('--auto-installer', action='store_true', help='install ice package without user intervention')

    args = parser.parse_args()

    if args.no_file_tracker and args.file_tracker:
        raise ValueError("Both --no-file-tracker and --file-tracker cannot be set simultaneously")

    if not args.no_file_tracker and not args.uninstall and not args.rollback and not args.recreate_ice_key:
        print("""
+--------------------------------------------------------------------------------------------------+
| Warning: By default, the installation includes the file tracker, which creates a daily cron job. | 
|          If you want to install without the file tracker,                                        |
|          run uninstall first:                                                                    |
|          $ python IceInstaller.py --uninstall                                                    |
|          and then install with the --no-file-tracker flag:                                       |
|          $ python IceInstaller.py --no-file-tracker                                              |
+--------------------------------------------------------------------------------------------------+"""
              )
    return args


def install_on_managers(arguments):
    ansible_args = get_str_args(arguments)
    os.chmod("hosts.hfx", 0o755)
    CommonOperations.execute_command(cmd=CommonOperations.get_create_ice_dir_cmd(), handle_error=True)
    CommonOperations.execute_command(cmd="sudo cp hosts.hfx {}".format(Paths.ICE_SHARE_DIR), handle_error=True)
    host_path = os.path.join(Paths.ICE_SHARE_DIR, "hosts.hfx")
    ansible_tty = arguments.force_install or is_tty()
    ansible_command = "sudo ansible-playbook install_on_all_managers.yaml -i {} -e hc_args='{}' -e is_tty={}".format(
        host_path, ansible_args, str(ansible_tty).lower())
    GlobalLogging.log_and_print("Install ice-support-package on all managers for cbis-admin user\n"
                                "Run the ansible command on localhost: {}".format(ansible_command))
    if not is_tty():
        out, err = CommonOperations.execute_command(cmd=ansible_command, timeout=480)
        GlobalLogging.log_and_print(out)
        GlobalLogging.log_and_print(err, is_error=True)
    else:
        child_process = subprocess.Popen(ansible_command, shell=True)

        try:
            # Wait for the child process to complete
            child_exit_code = child_process.wait()
            sys.exit(child_exit_code)

        except KeyboardInterrupt:
            # User pressed Ctrl+C, terminate the child process
            child_process.terminate()
            sys.exit(1)  # Exiting with non-zero code indicating termination due to interruption


def is_tty():
    return sys.stdout.isatty()


def get_str_args(arguments):
    filtered_args = ["--{} ".format(arg.replace('_', '-')) for arg, value in vars(arguments).items() if value]
    str_args = ' '.join(filtered_args)

    return str_args


def validate_user(args):
    if args.auto_installer:
        return

    if DeploymentType.is_ncs(GlobalParameters.deployment_type):
        current_user = getpass.getuser()
        if DeploymentType.is_ncs_over_bm(GlobalParameters.deployment_type):
            allowed_user = "cbis-admin"
        else:
            allowed_user = "cloud-user"

        if current_user != allowed_user:
            raise Exception("User {} is not allowed, the only allowed user is: {}.".format(
                current_user, allowed_user))
        GlobalLogging.log_and_print("Proceeding with the installation for user: {}".format(current_user))


def main():
    arguments = get_arguments()
    CommonOperations.generate_configuration()
    configuration = CommonOperations.get_env_configuration()
    GlobalParameters.init_env_configuration(configuration)
    deployment_type = CommonOperations.detect_deployment_type(configuration)
    GlobalParameters.init_deployment_type(deployment_type)
    GlobalLogging.init_loggers()
    validate_user(arguments)

    if DeploymentType.is_ncs_over_bm(GlobalParameters.deployment_type):
        install_on_managers(arguments)
    else:
        local_installer(arguments)


if __name__ == '__main__':
    main()
