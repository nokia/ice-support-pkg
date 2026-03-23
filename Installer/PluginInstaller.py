import time
import os
import re
import yaml
import GlobalLogging
import GlobalParameters
from Action import Action
import tarfile
from Validations import VersionValidation
from collections import OrderedDict
from requests.exceptions import RequestException
import CommonOperations
import traceback
from Version import Version
from DeploymentType import DeploymentType


class PluginInstaller(object):

    def __init__(self, plugin_file_path):
        assert GlobalParameters.version
        assert GlobalParameters.version != Version.V_CBIS_BVT_TMP_VERSION, 'installation of ice plugins on BVT with no cbis version is not supported yet'
        assert GlobalParameters.cbis_manager_client
        self.plugin_file_path = plugin_file_path
        self.plugin_file_name = self.plugin_file_path.split('/')[-1]
        self.plugin_name = re.sub(r'--.*|\.tar\.gz', "", self.plugin_file_name)
        self.manifest_dict = None
        self.cbis_manager_status_check_interval = None
        self.cbis_manager_up_iterating_count = None
        self.restart_retrying_count = None
        self.results = None
        self.installation_timeout_seconds = None
        self.existing_version = None
        self.plugin_version = None
        self._set_installation_timeout()
        self._set_restart_rules()

    def get_results_dict(self):
        return self.results

    def _set_installation_timeout(self):
        plugins_timeout_conf = GlobalParameters.conf_dict.get('plugins installation timeout seconds')
        assert plugins_timeout_conf
        is_specific = False
        specific_timeout_section = plugins_timeout_conf.get('specific timeout')
        if specific_timeout_section:
            plugin_specific_timeout = specific_timeout_section.get(self.plugin_name)
            if plugin_specific_timeout:
                is_specific = True
                self.installation_timeout_seconds = plugin_specific_timeout
        if not is_specific:
            self.installation_timeout_seconds = plugins_timeout_conf.get('default timeout')

    def _set_restart_rules(self):
        restart_rules = GlobalParameters.conf_dict.get('restart rules') or {}
        self.cbis_manager_status_check_interval = restart_rules.get('status check interval seconds', 2)
        self.cbis_manager_up_iterating_count = restart_rules.get('iteration count until up', 30)
        self.restart_retrying_count = restart_rules.get('restart retrying count', 2)

    def _store_manifest_as_dict(self):
        with tarfile.open(self.plugin_file_path) as tar:
            content_files_list = tar.getnames()
            manifest_tar_path = [path for path in content_files_list if 'manifest.yaml' in path][0]
            f = tar.extractfile(manifest_tar_path)
            text = f.read()
            self.manifest_dict = yaml.safe_load(text)

    def _check_compatibility(self):
        version_plugins_dict = {
            Version.V18: 18.0,
            Version.V18_5: 18.5,
            Version.V19: 19.0,
            Version.V19A: 19.1,
            Version.V20: 20.1,
            Version.V21: 21.1
            #Version.V22: 22.1

        }
        if GlobalParameters.version not in version_plugins_dict:
            raise Exception("ice plugins are not compatible to this cbis version")

        if version_plugins_dict[GlobalParameters.version] not in self.manifest_dict['version']:
            raise Exception("plugin {} is not compatible to cbis {}".
                            format(self.plugin_name, GlobalParameters.version))

    def _set_versions(self):
        self.existing_version = self._get_existing_version()
        self.plugin_version = self.manifest_dict.get('ice_version')

    def _get_existing_version(self):
        installed_plugins_dir = '/opt/install/plugins/' if self.is_cbis_20() else '/opt/install/backend/plugins/'
        manifest_file_path = '{}/{}/manifest.yaml'.format(installed_plugins_dir, self.plugin_name)
        if os.path.isfile(manifest_file_path):
            with open(manifest_file_path, 'r') as stream:
                installed_plugin_manifest = yaml.safe_load(stream)
                installed_version = installed_plugin_manifest.get('ice_version')
                return installed_version
        else:
            return None

    def _is_installed(self):
        GlobalLogging.log_and_print('check if plugin is installed')
        plugins_list = GlobalParameters.cbis_manager_client.get_plugins()
        if len([p for p in plugins_list if p['name'] == self.plugin_name]):
            return True
        return False

    def _delete_plugin(self, plugin_name):
        # Determine if we need workaround for CBIS-16477
        workaround = False
        if self.is_cbis_20():
            version = GlobalParameters.cbis_manager_client.get_version()
            parts = [x.strip() for x in version.split('+')]

            if parts[0] == '20.100.1-843':
                if len(parts) == 1:
                    workaround = True
                elif parts[-1] in ['PP1', 'PP2', 'PP3', 'SP1', 'SP2']:
                    workaround = True

        # Remove the Plugin
        res = GlobalParameters.cbis_manager_client.delete_plugin(plugin_name)

        # Apply Workaround (CBIS-16477)
        # Plugin removal flow generates invalid manager_status.yaml, which
        # causes cbis-manager api calls return 500s. Restarting cbis-manager
        # regenerates manager_status.yaml
        if workaround:
            GlobalLogging.log_and_print('restarting cbis-manager after plugin removal (CBIS-16477 workaround)...')
            docker_cmd = "sudo docker restart cbis_manager"
            CommonOperations.execute_command(docker_cmd, handle_error=True)
            self._wait_until_server_is_up()

        return res

    def _delete_if_old_version_installed(self):
        if self._is_installed():
            version_validation = VersionValidation(self.existing_version, self.plugin_version)
            version_comparison = version_validation.compare_versions()
            if version_comparison == 0:
                raise Exception('Version is already installed')
            if version_comparison == -1:
                continue_installation = version_validation.confirm_installation()
                if not continue_installation:
                    raise Exception('Keeping the currently installed newer version.')
            GlobalLogging.log_and_print('deleting the old plugin...')
            res = self._delete_plugin(self.plugin_name)
            self.results['delete old version'] = res

    def _delete_if_installed(self):
        if self._is_installed():
            res = self._delete_plugin(self.plugin_name)
            self.results['delete plugin'] = res
            self._restart_if_required()
        else:
            self.results['delete plugin'] = 'the plugin is not installed'

    def is_cbis_20(self):
        if GlobalParameters.version == Version.V20 :
            return True
        return False

    def get_installed_filetracker_plugin_dir(self):
        installed_plugins_dir = '/opt/install/plugins/filetracker' if self.is_cbis_20() else '/opt/install/backend/plugins/filetracker'
        if CommonOperations.is_dir_exist(installed_plugins_dir):
            return installed_plugins_dir
        return None

    def confirm_deprecated_file_tracker(self):
        installed_plugins_dir =self.get_installed_filetracker_plugin_dir()
        if installed_plugins_dir is None:
            return
        CommonOperations.execute_command('cp {} {}'.format('filetracker.json', installed_plugins_dir), handle_error=True)

    def _upload_and_install(self):
        # upload plugin tar file
        GlobalLogging.log_and_print('starting upload...')
        is_file_uploaded, error = GlobalParameters.cbis_manager_client.upload_file(
            self.plugin_file_name,
            self.plugin_file_path,
            'application/x-gzip',
            self.installation_timeout_seconds)
        self.results['uploading plugin_file'] = is_file_uploaded
        GlobalLogging.log_debug('is uploaded : {}'.format(is_file_uploaded))
        if not is_file_uploaded:
            raise Exception('Error in plugin file upload:{}'.format(error))
        # install uploaded plugin
        GlobalLogging.log_and_print('starting installation...')
        is_success, error = GlobalParameters.cbis_manager_client.install_plugin(
            self.plugin_file_name,
            self.installation_timeout_seconds)
        self.results['plugin installation'] = is_success
        if not is_success:
            raise Exception('Error in plugin installation:\n{}'.format(error))

    def _wait_until_server_is_up(self):
        is_server_up = False
        counter = 0
        while not is_server_up and counter < self.cbis_manager_up_iterating_count:
            counter += 1
            try:
                if not GlobalParameters.cbis_manager_client.is_require_restart():
                    is_server_up = True
                else:
                    time.sleep(self.cbis_manager_status_check_interval)
            except RequestException as e:
                time.sleep(self.cbis_manager_status_check_interval)

    def _check_no_running_process(self):
        GlobalLogging.log_and_print('checking running processes')
        if self.is_cbis_20():
            running_processes = GlobalParameters.cbis_manager_client.get_running_processes()
        else:
            with open("/opt/install/backend/conf/is_active.yaml", 'r') as stream:
                cbis_manager_processes = yaml.safe_load(stream)
                GlobalLogging.log_debug(cbis_manager_processes)
                running_processes = [p for p in cbis_manager_processes if cbis_manager_processes[p] != 'inactive']
        if len(running_processes):
            raise Exception(
                'Error : Cannot restart CBIS manager while processes are running:\n{}'.format(running_processes))

    def _restart_server(self):
        self._check_no_running_process()
        GlobalLogging.log_and_print('restarting cbis manager...')
        if self.is_cbis_20():
            GlobalParameters.cbis_manager_client.restart_server()
        else:
            CommonOperations.restart_cbis_manager()

    def _validate_installation(self):
        is_installed = self._is_installed()
        self.results['is installed'] = is_installed

    def _check_plugin(self):
        test_endpoint_response = GlobalParameters.cbis_manager_client.is_plugin_active(self.plugin_name)
        test_endpoint_response = GlobalParameters.cbis_manager_client.get_plugin_state(self.plugin_name)
        self.results['is alive'] = True

    def _restart_if_required(self):
        retry_counter = 0
        is_required_restart = GlobalParameters.cbis_manager_client.is_require_restart()
        while is_required_restart and retry_counter < self.restart_retrying_count:
            GlobalLogging.log_and_print('trying to restart...')
            retry_counter += 1
            self._restart_server()
            self._wait_until_server_is_up()
            is_required_restart = GlobalParameters.cbis_manager_client.is_require_restart()
        if is_required_restart:
            raise Exception('Error: cannot restart CBIS manager')

    def _install(self):
        self.results = OrderedDict([
            ('delete old version', 'no older version detected'),
            ('uploading plugin_file', False),
            ('plugin installation', False),
            ('is installed', False),
            ('is alive', False)
        ])
        self._store_manifest_as_dict()
        self._set_versions()
        try:
            GlobalLogging.print_plugin_header(Action.INSTALLATION, self.plugin_name)
            self._check_compatibility()
            self._delete_if_old_version_installed()
            self._restart_if_required()
            self._upload_and_install()
            self._restart_if_required()
            self._validate_installation()
            self._check_plugin()
        except Exception as e:
            self.results['message'] =e
            self.results['trace'] = traceback.format_exc()
        finally:
            GlobalLogging.log_plugin_results(Action.INSTALLATION, self.plugin_name, self.results)

    def _uninstall(self):
        self.results = OrderedDict([
            ('delete plugin', False)
        ])
        try:
            GlobalLogging.print_plugin_header(Action.UNINSTALLATION, self.plugin_name)
            self._delete_if_installed()
        except Exception as e:
            self.results['message'] = e
            self.results['trace'] = traceback.format_exc()
        finally:
            GlobalLogging.log_plugin_results(Action.UNINSTALLATION, self.plugin_name, self.results)

    def run(self, action):
        assert Action.is_supported(action)
        if action == Action.INSTALLATION:
            self._install()
        if action == Action.UNINSTALLATION:
            self._uninstall()
        GlobalParameters.dict_installation_result["{} PLUGIN {}".format(action, self.plugin_name.upper())] = not (
                'message' in self.results.keys())
