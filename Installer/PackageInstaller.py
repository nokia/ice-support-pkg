import json
import os
import sys
import re
import GlobalLogging
import GlobalParameters
from Action import Action
import CommonOperations
import traceback
from cryptography.fernet import Fernet
import Paths
from DeploymentType import DeploymentType
from Version import Version
from global_enums import Objectives

sys.path.append(os.path.join(os.getcwd(), "../ice/lib"))
from global_configurations import ICE_KEY_NAME, ICE_IMAGE_NAME_IN_REGISTRY


class PackageInstaller:
    main_host = None
    home_path = None
    podman_or_docker = None
    FILE_TRACKER_CRON_CMD = "sudo -u {} bash -c 'cd; source icerc; ice filetracker runOnce --detach --security-opt;'"
    PRODUCT_FULL_VERSION = None

    def __init__(self):
        self.supported_actions = self._set_supported_actions()
        if DeploymentType.is_cbis(GlobalParameters.deployment_type):
            PackageInstaller.main_host = Objectives.UC
            PackageInstaller.home_path = '/home/stack'
        elif DeploymentType.is_ncs(GlobalParameters.deployment_type):
            PackageInstaller.main_host = Objectives.ONE_MANAGER
            PackageInstaller.home_path = os.environ['HOME']
        PackageInstaller.podman_or_docker = CommonOperations.podman_or_docker()

    def _set_supported_actions(self):
        raise NotImplementedError

    def create_ice_share_dir(self):
        raise NotImplementedError

    def copy_ice_files(self):
        raise NotImplementedError

    def install(self):
        raise NotImplementedError

    def create_key(self):
        raise NotImplementedError

    def load_docker(self):
        pass

    def unload_docker(self):
        pass

    def is_supported(self, action):
        container_actions = [Action.UNLOAD_ICE_PYTHON_CONTAINER, Action.LOAD_ICE_PYTHON_CONTAINER]

        if action in container_actions and self.podman_or_docker is None:
            return False
        return action in self.supported_actions

    def is_action_match_environment(self, action):
        raise NotImplementedError

    def _set_ice_file_tracker_cron_file(self):
        user = GlobalParameters.env_configuration["user"]
        ft_cron_cmd = self.FILE_TRACKER_CRON_CMD.format(user)

        if DeploymentType.is_ncs_over_bm(GlobalParameters.deployment_type):
            ft_cron_cmd = CommonOperations.build_command_run_if_manager_active(ft_cron_cmd)

        full_cron_command = "#!/bin/bash\n{}".format(ft_cron_cmd)
        target_path = "{home}/{file_tracker_flow_dir}/{ice_file_tracker}".format(
            home=PackageInstaller.home_path,
            file_tracker_flow_dir=Paths.FILE_TRACKER_FLOW_DIR,
            ice_file_tracker=Paths.ICE_FILE_TRACKER
        )
        cmd = "cat <<'EOF' | sudo tee {target_path} >/dev/null\n{content}\nEOF".format(
            target_path=target_path,
            content=full_cron_command
        )
        CommonOperations.execute_command_on_host(cmd=cmd, host=PackageInstaller.main_host)

    def install_file_tracker(self):
        raise NotImplementedError

    def get_product_full_version(self):
        raise NotImplementedError

    @staticmethod
    def _get_product_version_parts(fetched_version):
        if not fetched_version:
            return None
        major, middle, minor = map(int, fetched_version[0])

        if middle == 100:
            middle = minor
        return (major, middle, minor)

    @staticmethod
    def create_file_tracker_cron_job():
        CommonOperations.execute_command_on_host(
            'sudo cp {home}/{file_tracker_flow_dir}/{ice_file_tracker} {cron_daily_dir}'.format(
                home=PackageInstaller.home_path, file_tracker_flow_dir=Paths.FILE_TRACKER_FLOW_DIR, ice_file_tracker=Paths.ICE_FILE_TRACKER,
                cron_daily_dir=Paths.CRON_DAILY_DIR), host=PackageInstaller.main_host, handle_error=True)
        CommonOperations.execute_command_on_host('sudo chmod +x {cron_daily_dir}/{ice_file_tracker}'.format
                                                 (cron_daily_dir=Paths.CRON_DAILY_DIR,
                                                  ice_file_tracker=Paths.ICE_FILE_TRACKER),
                                                 host=PackageInstaller.main_host,
                                                 handle_error=True)
        GlobalLogging.log_and_print('File tracker cron job was created successfully')

    @staticmethod
    def delete_file_tracker_cron_job():
        file_tracker_cron_job_file = os.path.join(Paths.CRON_DAILY_DIR, Paths.ICE_FILE_TRACKER)
        if CommonOperations.is_file_exist(file_tracker_cron_job_file, host=PackageInstaller.main_host):
            CommonOperations.execute_command_on_host('sudo rm -f {file_tracker_cron_job_file}'.format(
                file_tracker_cron_job_file=file_tracker_cron_job_file), host=PackageInstaller.main_host,
                handle_error=True)
            GlobalLogging.log_and_print('Delete file tracker cron job if exist')

    @staticmethod
    def restore_from_backup():
        if not CommonOperations.is_file_exist(Paths.BACK_UP_PATH_NAME, host=PackageInstaller.main_host):
            raise Exception("copy back up files failed - {} doesn't exist on {}".format(Paths.BACK_UP_PATH_NAME,
                                                                                        PackageInstaller.main_host))
        PackageInstaller.handle_cron_file_backup(source_dir=Paths.BACK_UP_PATH_NAME, dest_dir=Paths.CRON_DAILY_DIR)
        cmd = "sudo rsync -a --delete {back_up}/ice {home}".format(home=PackageInstaller.home_path, back_up=Paths.BACK_UP_PATH_NAME)
        GlobalLogging.log_and_print('>> {}'.format(cmd))
        CommonOperations.execute_command_on_host(cmd=cmd, host=PackageInstaller.main_host)
        if CommonOperations.is_file_exist(os.path.join(Paths.BACK_UP_PATH_NAME, 'icerc'),
                                              PackageInstaller.main_host):
            cmd = "sudo rsync -a --delete {back_up}/icerc {home}/icerc".format(home=PackageInstaller.home_path,
                                                               back_up=Paths.BACK_UP_PATH_NAME)
            GlobalLogging.log_and_print('>> {}'.format(cmd))
            CommonOperations.execute_command_on_host(cmd=cmd, host=PackageInstaller.main_host)
        GlobalLogging.log_and_print('Copy back up files from {} to {}'.format(Paths.BACK_UP_PATH_NAME,
                                                                              PackageInstaller.home_path))

    @staticmethod
    def back_up_previous_version():
        # if back up of this version already exist  - no need to re-backup
        GlobalLogging.log_and_print('Running the following commands from {}:'.format(PackageInstaller.main_host))
        cmd = 'cat {}/ice/ice_version'.format(PackageInstaller.home_path)
        GlobalLogging.log_and_print('>> {}'.format(cmd))
        exit_codeA, ice_versionA, errA = CommonOperations.execute_command_on_host(cmd=cmd,
                                                                                  host=PackageInstaller.main_host,
                                                                                  return_exit_code=True, handle_error=False)
        if exit_codeA != 0:
            GlobalLogging.log_and_print('No back up ice files to save')
            return
        back_up_ice_version_path = '{}/ice/ice_version'.format(Paths.BACK_UP_PATH_NAME)
        cmd = 'sudo cat {back_up_ice_version_path}'.format(back_up_ice_version_path=back_up_ice_version_path)
        GlobalLogging.log_and_print('>> {}'.format(cmd))
        exit_codeB, ice_versionB, errB = CommonOperations.execute_command_on_host(cmd=cmd,
                                                                                  host=PackageInstaller.main_host,
                                                                                  return_exit_code=True, handle_error=False)
        is_icerc_exist = CommonOperations.is_file_exist(os.path.join(PackageInstaller.home_path, 'icerc'),
                                                        PackageInstaller.main_host)
        ice_versionA = ice_versionA.strip()
        ice_versionB = ice_versionB.strip()
        if exit_codeB != 0:
            if not CommonOperations.is_file_exist(Paths.BACK_UP_PATH_NAME, PackageInstaller.main_host):
                cmd = 'sudo mkdir -p {}'.format(Paths.BACK_UP_PATH_NAME)
                GlobalLogging.log_and_print('>> {}'.format(cmd))
                CommonOperations.execute_command_on_host(cmd=cmd, host=PackageInstaller.main_host)
            elif CommonOperations.is_file_exist(back_up_ice_version_path, PackageInstaller.main_host):
                raise Exception(errB)
        PackageInstaller.handle_cron_file_backup(source_dir=Paths.CRON_DAILY_DIR, dest_dir=Paths.BACK_UP_PATH_NAME)
        if exit_codeB == 0 and ice_versionA == ice_versionB:
            is_backup_icerc_exist = CommonOperations.is_file_exist(os.path.join(Paths.BACK_UP_PATH_NAME, 'icerc'),
                                                                   PackageInstaller.main_host)
            if is_icerc_exist and not is_backup_icerc_exist:
                cmd = 'sudo rsync -a --delete {home}/icerc {back_up}'.format(home=PackageInstaller.home_path, back_up=Paths.BACK_UP_PATH_NAME)
                GlobalLogging.log_and_print('>> {}'.format(cmd))
                CommonOperations.execute_command_on_host(cmd=cmd, host=PackageInstaller.main_host)
                GlobalLogging.log_and_print('Back up ice files to {}\n'.format(Paths.BACK_UP_PATH_NAME))
                return
            GlobalLogging.log_and_print(
                'Back up version {} already exist at {}\n'.format(ice_versionA, Paths.BACK_UP_PATH_NAME))
            return

        cmd = 'sudo rsync -a --delete {home}/ice {back_up}'.format(home=PackageInstaller.home_path, back_up=Paths.BACK_UP_PATH_NAME)
        GlobalLogging.log_and_print('>> {}'.format(cmd))
        CommonOperations.execute_command_on_host(cmd=cmd, host=PackageInstaller.main_host)
        if is_icerc_exist:
            cmd = 'sudo rsync -a --delete {home}/icerc {back_up}'.format(home=PackageInstaller.home_path, back_up=Paths.BACK_UP_PATH_NAME)
            GlobalLogging.log_and_print('>> {}'.format(cmd))
            CommonOperations.execute_command_on_host(cmd=cmd, host=PackageInstaller.main_host)
        GlobalLogging.log_and_print('Back up ice files to {}\n'.format(Paths.BACK_UP_PATH_NAME))

    @staticmethod
    def handle_cron_file_backup(source_dir, dest_dir):
        source_file = os.path.join(source_dir, Paths.ICE_FILE_TRACKER)
        dest_file = os.path.join(dest_dir, Paths.ICE_FILE_TRACKER)
        if CommonOperations.is_file_exist(source_file, host=PackageInstaller.main_host):
            cmd = "sudo scp -p {source_file} {dest_file}".format(source_file=source_file, dest_file=dest_file)
        else:
            cmd = 'sudo rm -f {dest_file}'.format(dest_file=dest_file)
        GlobalLogging.log_and_print('>> {}'.format(cmd))
        CommonOperations.execute_command_on_host(cmd=cmd, host=PackageInstaller.main_host)

    @staticmethod
    def delete_ice_files():
        GlobalLogging.log_and_print('Running the following commands from {}:'.format(PackageInstaller.main_host))
        cmd = 'sudo rm -rf {home}/ice'.format(home=PackageInstaller.home_path)
        GlobalLogging.log_and_print('>> {}'.format(cmd))
        CommonOperations.execute_command_on_host(cmd=cmd, host=PackageInstaller.main_host, handle_error=True)
        cmd = 'rm -f {home}/icerc'.format(home=PackageInstaller.home_path)
        GlobalLogging.log_and_print('>> {}'.format(cmd))
        CommonOperations.execute_command_on_host(cmd=cmd, host=PackageInstaller.main_host, handle_error=True)
        GlobalLogging.log_and_print('Delete ice files if exist\n')

    def uninstall(self):
        PackageInstaller.delete_file_tracker_cron_job()
        PackageInstaller.delete_ice_files()

    def rollback(self):
        PackageInstaller.delete_ice_files()
        PackageInstaller.restore_from_backup()
        self.load_ice_healthcheck_container()

    def should_ice_image_exists_on_registry(self):
        PRODUCT_VERSION_ICE_ON_REGISTRY = (25, 7)

        if DeploymentType.is_ncs_over_bm(GlobalParameters.deployment_type) and self.get_product_full_version():
            GlobalLogging.log_and_print("Product Version : {}".format(self.get_product_full_version()))
            if PRODUCT_VERSION_ICE_ON_REGISTRY <= (self.get_product_full_version()[0], self.get_product_full_version()[1]):
                return True
        return False


    def load_ice_healthcheck_container(self):
        ICE_IMAGE_REGISTRY_TAG_DICT = {
            (25, 7, 0): '0.3',
            (25, 11, 0): '0.5',
            (26, 7, 0): '0.5'
        }
        REGISTRY = '127.0.0.1:8787'

        self.unload_ice_healthcheck_container()
        container_filenames_list = self.get_container_file_names_list()

        assert len(container_filenames_list) <= 1, "except only 1 file that starts with {} in healthcheck dir".format(
            Paths.ICE_PYTHON_CONTAINER_SUB_NAME)

        if self.should_ice_image_exists_on_registry():
            ICE_IMAGE_TAG = ICE_IMAGE_REGISTRY_TAG_DICT.get(self.get_product_full_version(), None)
            assert ICE_IMAGE_TAG, ("ICE image tag couldn't be found in ICE_IMAGE_REGISTRY_TAG_DICT for this version {}."
                                   "\nPlease add this version to the dictionary with the suitable image tag").format(self.get_product_full_version())
            cmd = "sudo {} pull {}/{}:{}".format(self.podman_or_docker, REGISTRY, ICE_IMAGE_NAME_IN_REGISTRY,
                                                 ICE_IMAGE_TAG)
            exit_code, out, err = CommonOperations.execute_command_on_host(cmd=cmd, host=PackageInstaller.main_host,
                                                                           return_exit_code=True)
            GlobalLogging.log_and_print('>> {}'.format(cmd))
            if exit_code != 0:
                raise Exception("\nFailed to pull ICE image '{}' from registry"
                                "\n\tCommand:{}\n\tOutput:{}\n\tError:{}".format(ICE_IMAGE_NAME_IN_REGISTRY, cmd, out,
                                                                                 err))
        else:
            if len(container_filenames_list):
                container_file_name = container_filenames_list[0]
                container_full_path = os.path.join(PackageInstaller.home_path,
                                                   Paths.ICE_PYTHON_CONTAINER_PARENT_DIR, container_file_name)

                cmd = "sudo {} load < {}".format(self.podman_or_docker, container_full_path)
                GlobalLogging.log_and_print('>> {}'.format(cmd))
                out, err = CommonOperations.execute_command_on_host(cmd=cmd, host=PackageInstaller.main_host,
                                                                               handle_error=True, timeout=60)
                match = re.search(r'Loaded image(?:\(s\))?: (\S+)', out)
                if match:
                    loaded_image = match.group(1)
                    get_manifest_cmd =  "tar -xOf {} manifest.json".format(container_full_path)
                    GlobalLogging.log_and_print('>> {}'.format(get_manifest_cmd))
                    maniest_out, err = CommonOperations.execute_command_on_host(cmd=get_manifest_cmd, host=PackageInstaller.main_host)
                    repo_tag = json.loads(maniest_out)[0]['RepoTags'][0]
                    tag_cmd = "sudo {} tag {} {}".format(self.podman_or_docker, loaded_image, repo_tag)
                    GlobalLogging.log_and_print('>> {}'.format(tag_cmd))
                    CommonOperations.execute_command_on_host(cmd=tag_cmd, host=PackageInstaller.main_host, handle_error=True)
                else:
                    GlobalLogging.log_and_print("Failed to load ICE image",is_error=True)

    @staticmethod
    def get_container_file_names_list():
        container_parent_dir = os.path.join(PackageInstaller.home_path, Paths.ICE_PYTHON_CONTAINER_PARENT_DIR)
        cmd = "sudo ls {}".format(container_parent_dir)
        exit_code, out, err = CommonOperations.execute_command_on_host(cmd=cmd, host=PackageInstaller.main_host,
                                                                       return_exit_code=True)
        if exit_code != 0:
            return []

        GlobalLogging.log_and_print('>> {}'.format(cmd))
        container_parent_dir_content = out.split()

        return list(filter(lambda file_name: file_name.startswith(Paths.ICE_PYTHON_CONTAINER_SUB_NAME),
                           container_parent_dir_content))

    def unload_ice_healthcheck_container(self):
        GlobalLogging.log_and_print('Running the following commands from {}:'.format(PackageInstaller.main_host))
        images_cmd = "sudo {} images".format(self.podman_or_docker)
        GlobalLogging.log_and_print('>> {}'.format(images_cmd))
        out, err = CommonOperations.execute_command_on_host(cmd=images_cmd, host=PackageInstaller.main_host,
                                                            handle_error=True)
        images_list = out.splitlines()

        healthcheck_images = list(filter(lambda l: "ice-python-container" in l, images_list))

        images_ids_list = []

        for image in healthcheck_images:
            images_ids_list.append(image.split()[2])

        for image_id in images_ids_list:
            cmd = "sudo {} rmi -f {}".format(self.podman_or_docker, image_id)
            GlobalLogging.log_and_print('>> {}'.format(cmd))
            exit_code, out, err = CommonOperations.execute_command_on_host(cmd=cmd,
                                                                           host=PackageInstaller.main_host,
                                                                           return_exit_code=True,
                                                                           timeout=60)

            if exit_code != 0:
                raise Exception('\nPlease verify no container with ice-healthcheck prefix is running, '
                                'if a container with this prefix is running, stop it and only then try to '
                                'install / unistall ice-support-package again.'
                                '\n\tcommand:{}\n\tOutput:{}\n\tError:{}'.format(cmd, out, err))

    def remove_old_ice_key(self):
        GlobalLogging.log_and_print('Running the following commands from {}:'.format(PackageInstaller.main_host))
        user_home_dir = GlobalParameters.env_configuration["user_home_dir"]
        key_path = os.path.join(user_home_dir, ".ssh", ICE_KEY_NAME)
        cmd = "sudo ls {}".format(key_path)
        exit_code, _, _ = CommonOperations.execute_command_on_host(cmd=cmd, host=PackageInstaller.main_host,
                                                                   return_exit_code=True)
        GlobalLogging.log_and_print('>> {}'.format(cmd))
        if exit_code == 0:
            cmd = "sudo rm -f {}".format(key_path)
            CommonOperations.execute_command_on_host(cmd=cmd, host=PackageInstaller.main_host, handle_error=True)
            GlobalLogging.log_and_print('>> {}'.format(cmd))
            cmd = "sudo cat {}.pub".format(key_path)
            exit_code, pub_key, err = CommonOperations.execute_command_on_host(cmd=cmd, host=PackageInstaller.main_host,
                                                                               return_exit_code=True)
            GlobalLogging.log_and_print('>> {}'.format(cmd))

            if exit_code == 0:
                pub_key = pub_key.strip()
                authorized_keys_path = os.path.join(user_home_dir, ".ssh", "authorized_keys")

                if self._is_authorized_file_exist(authorized_keys_path):
                    self._remove_public_key_from_authorized_keys(authorized_keys_path, pub_key)
                    self._remove_public_key(key_path)

    def _is_authorized_file_exist(self, authorized_keys_path):
        cmd = "sudo ls {}".format(authorized_keys_path)
        exit_code, _, _ = CommonOperations.execute_command_on_host(cmd=cmd, host=PackageInstaller.main_host,
                                                                   return_exit_code=True)
        GlobalLogging.log_and_print('>> {}'.format(cmd))
        is_authorized_file_exist = exit_code == 0
        return is_authorized_file_exist

    def _remove_public_key(self, key_path):
        cmd = "sudo rm -f {}.pub".format(key_path)
        CommonOperations.execute_command_on_host(cmd=cmd, host=PackageInstaller.main_host,
                                                 handle_error=True)
        GlobalLogging.log_and_print('>> {}'.format(cmd))

    def _remove_public_key_from_authorized_keys(self, authorized_keys_path, pub_key):
        cmd = "sudo grep -v '{}' {}".format(pub_key, authorized_keys_path)
        out, _ = CommonOperations.execute_command_on_host(cmd=cmd, host=PackageInstaller.main_host,
                                                          handle_error=True)
        GlobalLogging.log_and_print('>> {}'.format(cmd))
        if PackageInstaller.main_host is Objectives.UC:
            cmd = "sudo bash -c 'echo \\\"{}\\\" > {}'".format(out.strip(), authorized_keys_path)
        else:
            cmd = "sudo bash -c \"echo '{}' > {}\"".format(out.strip(), authorized_keys_path)
        CommonOperations.execute_command_on_host(cmd=cmd, host=PackageInstaller.main_host,
                                                 handle_error=True)

    def run(self, action):
        if self.is_supported(action):
            try:
                if not self.is_action_match_environment(action):
                    return True, ''
                GlobalParameters.dict_installation_result[action] = True
                GlobalLogging.print_header(action)
                if action == Action.INSTALLATION:
                    self.install()
                if action == Action.INSTALLATION_FILE_TRACKER:
                    self.install_file_tracker()
                elif action == Action.UNINSTALLATION:
                    self.uninstall()
                elif action == Action.KEY_RECREATION:
                    self.create_key()
                elif action == Action.LOAD_DOCKER:
                    self.load_docker()
                elif action == Action.UNLOAD_DOCKER:
                    self.unload_docker()
                elif action == Action.ROLLBACK:
                    self.rollback()
                elif action == Action.LOAD_ICE_PYTHON_CONTAINER:
                    self.load_ice_healthcheck_container()
                elif action == Action.UNLOAD_ICE_PYTHON_CONTAINER:
                    self.unload_ice_healthcheck_container()
                elif action == Action.REMOVE_OLD_ICE_KEY:
                    self.remove_old_ice_key()
                elif action == Action.GENERATE_LOG_SCENARIOS_FILES:
                    self.run_generate_log_scenarios()

                successes_message = "{} -- SUCCESS".format(action)
                GlobalLogging.log_and_print(successes_message)
                return True, successes_message
            except Exception as e:
                GlobalLogging.log_debug('{} failed.\n{}\nTrace:{}\n'.format(action, e, traceback.format_exc()))
                return False, '{} -- FAILED.\n{}'.format(action, e)
        return True, ""

    @staticmethod
    def create_ice_share_dir_on_all_hosts():
        salt_cmd = 'su - cbis-admin -c "/usr/bin/salt-ssh -c /home/cbis-admin/salt/etc/salt/ --log-file /home/cbis-admin/salt/var/log/salt/ssh --no-host-keys'
        create_ice_dir_cmd = "{} '*' cmd.run '{}'{}".format(salt_cmd, CommonOperations.get_create_ice_dir_cmd(), '"')
        GlobalLogging.log_and_print(">> {}".format(create_ice_dir_cmd))
        CommonOperations.execute_command(cmd=create_ice_dir_cmd, timeout=60, handle_error=False)
        cmd = "{} '*' cmd.run 'sudo mkdir -p {}'{}".format(salt_cmd, Paths.ICE_UTILS_DIR, '"')
        GlobalLogging.log_and_print(">> {}".format(cmd))
        CommonOperations.execute_command(cmd=cmd, timeout=60, handle_error=False)
        cmd = "{} '*' cmd.run 'sudo find {} -type d | xargs --no-run-if-empty sudo chmod 775'{}".format(salt_cmd,
                                                                                                        Paths.ICE_SHARE_DIR,
                                                                                                        '"')
        GlobalLogging.log_and_print(">> {}".format(cmd))
        CommonOperations.execute_command(cmd=cmd, timeout=60, handle_error=False)

        GlobalLogging.log_and_print('ICE share dir was created successfully on all hosts\n')

    @staticmethod
    def create_ice_share_dir_on_local_host():
        create_ice_dir_cmd = CommonOperations.get_create_ice_dir_cmd()
        GlobalLogging.log_and_print(">> {}".format(create_ice_dir_cmd))
        CommonOperations.execute_command(cmd=create_ice_dir_cmd, timeout=60, handle_error=False)
        cmd = 'sudo find {} -type d | xargs --no-run-if-empty sudo chmod 775'.format(Paths.ICE_SHARE_DIR)
        GlobalLogging.log_and_print('>> {}\n'.format(cmd))
        CommonOperations.execute_command(cmd=cmd, handle_error=True)

    @staticmethod
    def run_file_tracker():
        cmd = "cd; source ./icerc; ice filetracker runOnce {detach_flag}"

        if DeploymentType.is_ncs_over_bm(GlobalParameters.deployment_type):
            cmd = CommonOperations.build_command_run_if_manager_active(cmd)
        if PackageInstaller.should_run_on_container():
            CommonOperations.execute_command_on_host(cmd=cmd.format(detach_flag="--detach"),
                                                     host=PackageInstaller.main_host, handle_error=False)
        else:
            CommonOperations.execute_background_command_on_host(cmd=cmd.format(detach_flag=""),
                                                                host=PackageInstaller.main_host)

    @staticmethod
    def run_generate_log_scenarios():
        cmd = "cd; source ./icerc; ice collector logs scenarios-generator --quiet {detach_flag}"
        if PackageInstaller.should_run_on_container():
            CommonOperations.execute_command_on_host(cmd=cmd.format(detach_flag="--detach"),
                                                     host=PackageInstaller.main_host)
        else:
            CommonOperations.execute_background_command_on_host(cmd=cmd.format(detach_flag=""),
                                                                host=PackageInstaller.main_host)

    @staticmethod
    def should_run_on_container():
        for item in ['podman', 'docker']:
            exit_code, out, err = CommonOperations.execute_command_on_host(
                "which {}".format(item), handle_error=False, return_exit_code=True, host=PackageInstaller.main_host)
            if exit_code == 0:
                return True
        return False


class CBISPackageInstaller(PackageInstaller):

    def get_product_full_version(self):
        if not self.PRODUCT_FULL_VERSION:
            cmd = 'openstack cbis version'
            exit_code, out, err = CommonOperations.execute_command_on_host(cmd=cmd, host=PackageInstaller.main_host,
                                                                           return_exit_code=True)
            if exit_code == 0:
                fetched_version = re.findall(r"build\s+\|\s+cbis-([0-9]+)\.([0-9]+)\.([0-9]+)-", out)
                self.PRODUCT_FULL_VERSION = self._get_product_version_parts(fetched_version)

        return self.PRODUCT_FULL_VERSION

    def is_action_match_environment(self, action):
        if action in [Action.LOAD_DOCKER, Action.UNLOAD_DOCKER]:
            if GlobalParameters.version < Version.V19A:
                return False
            images_paths = [
                '../docker_images/httpd_latest.tar.gz',
                '../docker_images/redis_latest.tar.gz'
            ]
            for image_path in images_paths:
                if not os.path.isfile(image_path):
                    return False
        if action == Action.KEY_RECREATION:
            if GlobalParameters.version > Version.V20:
                return False

        return True

    @staticmethod
    def create_ice_share_dir():
        GlobalLogging.log_and_print('Running the following commands from hypervisor:')
        PackageInstaller.create_ice_share_dir_on_local_host()


        GlobalLogging.log_and_print('Running the following commands from undercloud:')
        create_ice_dir_cmd = CommonOperations.get_create_ice_dir_cmd()
        GlobalLogging.log_and_print(">> {}".format(create_ice_dir_cmd))
        CommonOperations.execute_command_on_undercloud(cmd=create_ice_dir_cmd, timeout=60, handle_error=False)
        create_ice_dir_cmd = "sudo mkdir -p {}".format(Paths.ICE_UTILS_DIR)
        GlobalLogging.log_and_print(">> {}".format(create_ice_dir_cmd))
        CommonOperations.execute_command_on_undercloud(cmd=create_ice_dir_cmd, timeout=60, handle_error=False)
        cmd = "sudo find {} -type d | sed 's/\\\\/\\\\\\\\/g' | xargs --no-run-if-empty sudo chmod 775".format(
            Paths.ICE_SHARE_DIR)
        GlobalLogging.log_and_print('>> {}\n'.format(cmd))
        CommonOperations.execute_command_on_undercloud(cmd=cmd, handle_error=True, run_on_bkg='')

        cmd = "ansible all --limit '!hypervisor, !localhost' --timeout 59 -b -m shell -a 'sudo mkdir -p {}'".format(
            Paths.ICE_UTILS_DIR)
        GlobalLogging.log_and_print(">> {}".format(cmd))
        CommonOperations.execute_command_on_undercloud(cmd=cmd, timeout=60)
        cmd = "ansible all --limit '!hypervisor, !localhost' --timeout 59 -b -m shell -a 'sudo chmod 775 {}'".format(
            Paths.ICE_SHARE_DIR)
        GlobalLogging.log_and_print(">> {}".format(cmd))
        CommonOperations.execute_command_on_undercloud(cmd=cmd, timeout=60)
        cmd = "ansible all --limit '!hypervisor, !localhost' --timeout 59 -b -m shell -a 'sudo find {} -type d | xargs --no-run-if-empty sudo chmod 775'".format(
            Paths.ICE_SHARE_DIR)
        GlobalLogging.log_and_print(">> {}".format(cmd))
        CommonOperations.execute_command_on_undercloud(cmd=cmd, timeout=60)

        GlobalLogging.log_and_print('ICE share dir was created successfully\n')

    @staticmethod
    def copy_ice_files():
        GlobalLogging.log_and_print('Running the following commands from hypervisor:')
        cmd = 'scp -o StrictHostKeyChecking=no -q -p -r ../ice stack@uc:/home/stack/.'
        GlobalLogging.log_and_print('>> {}'.format(cmd))
        CommonOperations.execute_command(cmd=cmd, handle_error=True, timeout=60)
        cmd = 'scp -o StrictHostKeyChecking=no -q -p ../icerc stack@uc:/home/stack/.'
        GlobalLogging.log_and_print('>> {}'.format(cmd))
        CommonOperations.execute_command(cmd=cmd, handle_error=True)
        #cmd = 'chmod +x ../cb-report.py'
        #GlobalLogging.log_and_print('>> {}'.format(cmd))
        #CommonOperations.execute_command(cmd=cmd, handle_error=True)
        #cmd = 'scp -q -p ../cb-report.py stack@uc:/home/stack'
        #GlobalLogging.log_and_print('>> {}'.format(cmd))
        #CommonOperations.execute_command(cmd=cmd, handle_error=True)
        GlobalLogging.log_and_print('ICE files were copied\n')

    @staticmethod
    def load_docker():
        CommonOperations.execute_command(
            'scp -o StrictHostKeyChecking=no -q -r ../docker_images stack@uc:/home/stack/.', handle_error=True)
        CommonOperations.execute_command_on_undercloud('gzip -d /home/stack/docker_images/httpd_latest.tar.gz',
                                                       handle_error=True)
        CommonOperations.execute_command_on_undercloud('docker load < /home/stack/docker_images/httpd_latest.tar',
                                                       handle_error=True)
        CommonOperations.execute_command_on_undercloud('gzip -d /home/stack/docker_images/redis_latest.tar.gz',
                                                       handle_error=True)
        CommonOperations.execute_command_on_undercloud('docker load < /home/stack/docker_images/redis_latest.tar',
                                                       handle_error=True)
        CommonOperations.execute_command_on_undercloud(
            'docker run -d --restart always --name ice-osprofiler-redis -p 16380:6379 docker.repo.cci.nokia.net/redis:3.0.0',
            handle_error=True)
        CommonOperations.execute_command_on_undercloud(
            'docker run -d --restart always --name ice-osprofiler-httpd -v "/home/stack/ice/osprofiler_output/":/usr/local/apache2/htdocs/ -p 18080:443 csf-docker-delivered.repo.cci.nokia.net/httpd:latest',
            handle_error=True)
        GlobalLogging.log_and_print('Docker images loaded and running successfully')

    @staticmethod
    def unload_docker():
        CommonOperations.execute_command_on_undercloud('rm -rf /home/stack/docker_images', handle_error=True)
        CommonOperations.execute_command_on_undercloud('docker rm -f ice-osprofiler-redis', handle_error=True)
        CommonOperations.execute_command_on_undercloud('docker rm -f ice-osprofiler-httpd', handle_error=True)
        CommonOperations.execute_command_on_undercloud(
            'docker image rm docker.repo.cci.nokia.net/redis:3.0.0', handle_error=True)
        CommonOperations.execute_command_on_undercloud(
            'docker image rm csf-docker-delivered.repo.cci.nokia.net/httpd:latest', handle_error=True)
        GlobalLogging.log_and_print('Delete container and image from registry')

    def install(self):
        GlobalLogging.log_and_print('Creating ice share dir')
        GlobalLogging.log_and_print('======================')
        CBISPackageInstaller.create_ice_share_dir()
        GlobalLogging.log_and_print('Backup ice files to {}'.format(Paths.BACK_UP_PATH_NAME))
        GlobalLogging.log_and_print('========================================')
        PackageInstaller.back_up_previous_version()
        GlobalLogging.log_and_print('Deleting ice files if exist')
        GlobalLogging.log_and_print('===========================')
        PackageInstaller.delete_ice_files()
        GlobalLogging.log_and_print('Copying ice files')
        GlobalLogging.log_and_print('=================')
        CBISPackageInstaller.copy_ice_files()
        GlobalLogging.log_and_print('Setting ice File Tracker cron job')
        GlobalLogging.log_and_print('=================')
        self._set_ice_file_tracker_cron_file()

    def install_file_tracker(self):
        CBISPackageInstaller.create_file_tracker_cron_job()
        CBISPackageInstaller.add_readme_to_old_file_tracker_dir()
        CBISPackageInstaller.run_file_tracker()

    def create_key(self):
        # create ice key file
        key = Fernet.generate_key()
        with open(Paths.ICE_KEY_FILE, "wb") as key_file:
            key_file.write(key)
        # delete key from UC
        CommonOperations.execute_command_on_undercloud(
            'sudo rm -f {}'.format(Paths.ICE_KEY_FILE), handle_error=True)
        CommonOperations.execute_command_on_undercloud(
            'sudo chown stack {}'.format(Paths.ICE_SHARE_DIR), handle_error=True)
        # copy key to UC
        try:
            CommonOperations.execute_command(
                'sudo scp -o StrictHostKeyChecking=no -q {} stack@uc:{}'.format(Paths.ICE_KEY_FILE,
                                                                                Paths.ICE_SHARE_DIR), handle_error=True)
        finally:
            CommonOperations.execute_command_on_undercloud(
                'sudo chown root {}'.format(Paths.ICE_SHARE_DIR), handle_error=True)
        GlobalLogging.log_and_print('Ice key was created successfully')

    def _set_supported_actions(self):
        return [Action.INSTALLATION, Action.INSTALLATION_FILE_TRACKER, Action.UNINSTALLATION, Action.KEY_RECREATION,
                Action.LOAD_DOCKER, Action.UNLOAD_DOCKER, Action.ROLLBACK, Action.UNLOAD_ICE_PYTHON_CONTAINER,
                Action.LOAD_ICE_PYTHON_CONTAINER, Action.GENERATE_LOG_SCENARIOS_FILES, Action.REMOVE_OLD_ICE_KEY]

    @staticmethod
    def add_readme_to_old_file_tracker_dir():
        if CommonOperations.is_dir_exist_on_undercloud(Paths.OLD_FILE_TRACKER_DIR):
            if not CommonOperations.is_file_exist(Paths.README_PATH, host=Objectives.UC):
                file_content = "This directory is an old version of the File Tracker tool.\nThe outputs of the new " \
                               "version are located in '/usr/share/ice/file_tracker/.'"
                CommonOperations.execute_command_on_undercloud("echo '{file_content}' > {readme_path}".format
                                                               (file_content=file_content,
                                                                readme_path=Paths.README_PATH))


class NCSPackageInstaller(PackageInstaller):

    def get_product_full_version(self):
        if not self.PRODUCT_FULL_VERSION:
            cmd = 'openstack cbis version --ncs'
            exit_code, out, err = CommonOperations.execute_command_on_host(cmd=cmd, host=PackageInstaller.main_host,
                                                                           return_exit_code=True)
            if exit_code == 0:
                fetched_version = re.findall(r"BCMT\s+\|\s+([0-9]+)\.([0-9]+)\.([0-9]+)-", out)
                if not fetched_version:
                    fetched_version = re.findall(r"build\s+\|\s+cbis-([0-9]+)\.([0-9]+)\.([0-9]+)-", out)
                self.PRODUCT_FULL_VERSION = self._get_product_version_parts(fetched_version)

        return self.PRODUCT_FULL_VERSION

    def _set_supported_actions(self):
        ### TODO - add 'Action.INSTALLATION_FILE_TRACKER' when we want NCS to be included in the release
        return [Action.INSTALLATION, Action.INSTALLATION_FILE_TRACKER, Action.UNINSTALLATION, Action.ROLLBACK,
                Action.UNLOAD_ICE_PYTHON_CONTAINER, Action.LOAD_ICE_PYTHON_CONTAINER,
                Action.GENERATE_LOG_SCENARIOS_FILES, Action.REMOVE_OLD_ICE_KEY]
        # return [Action.INSTALLATION, Action.UNINSTALLATION, Action.ROLLBACK, Action.UNLOAD_ICE_PYTHON_CONTAINER,
        #         Action.LOAD_ICE_PYTHON_CONTAINER]

    @staticmethod
    def create_ice_share_dir():
        GlobalLogging.log_and_print('Running the following commands from deployer:')
        PackageInstaller.create_ice_share_dir_on_local_host()
        PackageInstaller.create_ice_share_dir_on_all_hosts()

    @staticmethod
    def copy_ice_files():
        user = GlobalParameters.env_configuration["user"]
        CommonOperations.execute_command('cp -r ../ice ~/', handle_error=True)
        CommonOperations.execute_command("sudo chown -R {}:{} ~/ice".format(user, user))
        CommonOperations.execute_command('cp ../ncs_icerc ~/icerc', handle_error=True)
        CommonOperations.execute_command("sudo chown {}:{} ~/icerc".format(user, user))
        GlobalLogging.log_and_print('ICE files were copied\n')

    def is_action_match_environment(self, action):
        return True

    def install(self):
        GlobalLogging.log_and_print('Creating ice share dir')
        GlobalLogging.log_and_print('======================')
        NCSPackageInstaller.create_ice_share_dir()
        GlobalLogging.log_and_print('Backup ice files to {}'.format(Paths.BACK_UP_PATH_NAME))
        GlobalLogging.log_and_print('========================================')
        PackageInstaller.back_up_previous_version()
        GlobalLogging.log_and_print('Deleting ice files if exist')
        GlobalLogging.log_and_print('===========================')
        PackageInstaller.delete_ice_files()
        GlobalLogging.log_and_print('Copying ice files')
        GlobalLogging.log_and_print('=================')
        NCSPackageInstaller.copy_ice_files()
        GlobalLogging.log_and_print('Setting ice File Tracker cron job')
        GlobalLogging.log_and_print('=================')
        self._set_ice_file_tracker_cron_file()

    def install_file_tracker(self):
        NCSPackageInstaller.create_file_tracker_cron_job()
        NCSPackageInstaller.run_file_tracker()

    def create_key(self):
        pass