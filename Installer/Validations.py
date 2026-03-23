import sys

import CommonOperations
import os
import Paths
import GlobalParameters
from DeploymentType import DeploymentType
from Action import Action
from distutils.version import StrictVersion


class VersionValidation(object):
    def __init__(self, existing_version, current_version, is_plugin=True):
        self.existing_version = existing_version.replace("\n", "") if existing_version else None
        assert current_version, "current package/plugin does not contains ice version info"
        self.current_version = current_version.replace("\n", "")
        self.is_plugin = is_plugin

    #  returns  0 if the  version is equal  to   the existing version
    #  returns  1 if the  version is higher than the existing version
    #  returns -1 if the  version is lower  than the existing version
    @staticmethod
    def get_version_and_build(version_str):
        version_str, build_str = version_str.split("-b")
        return StrictVersion(version_str), int(build_str)

    def compare_versions(self):
        if not self.existing_version:
            return 1
        version_existing, build_existing = VersionValidation.get_version_and_build(self.existing_version)
        version_current, build_current = VersionValidation.get_version_and_build(self.current_version)
        if version_existing > version_current or (
                version_existing == version_current and build_existing > build_current):
            return -1
        if version_existing == version_current and build_existing == build_current:
            return 0
        if version_existing < version_current or (
                version_existing == version_current and build_existing < build_current):
            return 1

    def confirm_installation(self):
        trials_count = 3
        trials_counter = 0
        installed_component = 'plugin' if self.is_plugin else 'ice package'
        message = """
                ----------------------------------------------------------------------------
                Version {} of the {} is installed already.
                You try to install an older version- {}
                Do you want to continue the installation?    (y/n)
                ----------------------------------------------------------------------------
                """.format(self.existing_version, installed_component, self.current_version)
        while trials_counter < trials_count:
            if trials_counter:
                message = 'invalid input. try again:(y/n)'
            if sys.version_info[0] == 2:
                user_response = str(raw_input(message))
            else:
                user_response = str(input(message))
            if user_response == 'y':
                return True
            if user_response == 'n':
                return False
            trials_counter += 1
        print('invalid output .Aborting installation...')
        return False


class Validations:
    @staticmethod
    def validate_conf_file_exists():
        if not os.path.isfile(Paths.CONF_FILE):
            return False, "Conf file {path} does not exist".format(path=Paths.CONF_FILE)
        return True, ""

    @staticmethod
    def validate_ice_version_is_newer_than_existing(deployment_type, actions_list, auto_installer, force_install):
        if Action.INSTALLATION not in actions_list:
            return True, ""
        existing_version = ""
        if DeploymentType.is_cbis(deployment_type):
            existing_version, err = CommonOperations.execute_command_on_undercloud('cat /home/stack/ice/ice_version', handle_error=False)
        elif deployment_type == DeploymentType.is_ncs(deployment_type):
            ice_version_file = '{home}/ice/ice_version'.format(home=os.environ['HOME'])
            if os.path.isfile(ice_version_file):
                with open(ice_version_file, "r") as f:
                    existing_version = f.read()
        with open('../ice/ice_version', "r") as f:
            package_version = f.read()
        version_validation = VersionValidation(existing_version, package_version, is_plugin=False)
        version_comparison = version_validation.compare_versions()
        if version_comparison == -1:
            is_installation_confirmed = False
            if force_install:
                return True, ""
            if not auto_installer:
                is_installation_confirmed = version_validation.confirm_installation()
            if not is_installation_confirmed:
                return False, "A newer version of ice-support-package detected."
        return True, ""

    @staticmethod
    def check_keys_existence(required_structure, structure, missing_keys=[], path=''):
        for key in required_structure:
            key_full_path = '{} : {}'.format(path, key) if path else key
            if key not in structure:
                missing_keys.append(key_full_path)
                continue
            if required_structure.get(key):
                missing_keys = Validations.check_keys_existence(
                    required_structure.get(key), structure.get(key),
                    missing_keys=missing_keys, path=key_full_path)
        return missing_keys

    @staticmethod
    def validate_conf():
        required_structure = {
            'cbis manager': {
                'user name': None,
                'password': None,
                'hypervisor ip': None
            },
            'plugins installation timeout seconds': {
                'default timeout': None
            }
        }
        missing_keys = Validations.check_keys_existence(required_structure, GlobalParameters.conf_dict)
        if len(missing_keys):
            message = 'Error : Missing Field in conf.yaml configuration file:\n\t\t{}'.format(
                '\n\t\t'.join(missing_keys))
            return False, message
        return True, ""

    @staticmethod
    def validate_cbis_manager_connectivity():
        assert GlobalParameters.cbis_manager_client
        try:
            GlobalParameters.cbis_manager_client.get_server_status()
            return True, ""
        except Exception as e:
            return False, str(e)

    @staticmethod
    def validate_execution_environment(deployment_type):
        if not DeploymentType.is_cbis(deployment_type):
            return True, ""
        out, err = CommonOperations.execute_command('whoami')
        if 'stack' in out:
            return False, "Installer cannot run on UC. please run it from Hypervisor."
        return True, ""

    @staticmethod
    def validate_plugins_dir_exists():
        if not os.path.isdir(Paths.PLUGINS_DIR):
            return False, "Plugins Dir {} does not exist".format(Paths.PLUGINS_DIR)
        return True, ""

    @staticmethod
    def validate_execution_path(execution_rel_path, ice_installer_rel_dir):
        execution_dir = os.path.abspath(execution_rel_path)
        ice_installer_dir = os.path.dirname(os.path.abspath(ice_installer_rel_dir))
        if ice_installer_dir != execution_dir:
            return False, "You have to execute ice installer from installer directory- {} ".format(ice_installer_dir)
        return True, ""

    @staticmethod
    def validate_deployment_type(deployment_type):
        if not deployment_type:
            return False, "No deployment type was detected"
        if deployment_type not in DeploymentType.get_available_deployment_types():
            return False, "deployment type is not supported yet"
        return True, ""
