from __future__ import absolute_import
import base64
import datetime
import os

from HealthCheckCommon.secret_filter import SecretFilter
from tools import paths
from tools.ExecutionModule.execution_helper import ExecutionHelper
from tools.SecurityHelper import encrypt_msg_by_public_key_file

class SystemCommands:
    @staticmethod
    def is_container_deployed(container):
        cmd = "sudo docker ps -a | grep {}".format(container)
        return cmd

    @staticmethod
    def get_create_ice_dir_cmd():
        # CAUTION: Similar functionality might exist elsewhere, requiring synchronization to maintain consistency across the codebase.
        return "sudo mkdir -p /usr/share/ice/; sudo chmod 775 /usr/share/ice/"

    @staticmethod
    def save_key_to_keys_file(dir_path=None, key_date=None):
        if dir_path is None:
            dir_path = paths.ENCRYPTION_OUT_FILES_KEYS_FOLDER
        keys_file_path = os.path.join(dir_path, paths.ENCRYPTION_OUT_FILES_KEYS_FILE)

        encrypted_key = encrypt_msg_by_public_key_file(SecretFilter.fernet_key, paths.PUBLIC_KEY_PATH)
        encoded_key = base64.b64encode(encrypted_key).decode('utf-8')

        if key_date is None:
            key_date = datetime.datetime.now()
            DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
            key_date = key_date.strftime(DATE_FORMAT)
        new_key = key_date + "\t" + encoded_key + "\n"

        local_operator = ExecutionHelper.get_local_operator(False)

        if not local_operator.file_utils.is_file_exist(keys_file_path):
            local_operator.get_output_from_run_cmd("sudo touch {}; sudo chmod 666 {}".format(keys_file_path,
                                                                                             keys_file_path))
        ExecutionHelper.get_hosting_operator(False).get_output_from_run_cmd("sudo chown {}:{} {}".format(
            ExecutionHelper.get_local_uid(), ExecutionHelper.get_local_gid(), keys_file_path))
        with open(keys_file_path, "a") as f:
            f.write(new_key)
