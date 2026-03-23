from __future__ import absolute_import

import os.path
import re
from tools.lazy_global_data_loader import *
from tools.Exceptions import UnExpectedSystemOutput
from tools.global_enums import SizeUnit

class SystemUtils(object):

    VAULT_PASSWORD_FILES = ("/usr/local/bin/dec-pass", "/usr/bin/dec-pass")
    def __init__(self, operator):
        self.operator = operator
        pass

    def get_available_disk_space_size(self, path="/", size_unit=SizeUnit.KB):
        if size_unit == SizeUnit.B:
            available_disk_space_out = self.operator.get_output_from_run_cmd("sudo df  -B1 {} --output='avail'".format(path))
        else:
            available_disk_space_out = self.operator.get_output_from_run_cmd("df {} --output='avail'".format(path))
        available_disk_space_out = re.sub("[^0-9]", "", available_disk_space_out)
        available_disk_space_size = self.operator.parse_to_int(available_disk_space_out)
        return available_disk_space_size

    def get_operating_system_type(self):
        return self.operator.get_output_from_run_cmd("hostnamectl | grep -i 'operating system'").split(':')[1]

    def get_ip_from_ss(self, port, component=None):
        ipv4_pattern = r"((?:\d{1,3}\.){3}\d{1,3})"
        ipv6_pattern = r"(\[[0-9a-fA-F:]+\])"
        ipv4_ipv6_with_port = r"(?:{}|{})\:{}".format(ipv4_pattern, ipv6_pattern, port)
        cmd = "sudo ss -ltnp | grep {}".format(port)

        if component:
            cmd = "{} | grep {}".format(cmd, component)
        out = self.operator.get_output_from_run_cmd(cmd)
        match = re.search(ipv4_ipv6_with_port, out)

        if not match:
            raise UnExpectedSystemOutput(self.operator.get_host_ip(), cmd, out,
                                         "Expected to have IPV4 or IPV6 IP in out.")
        ip = match.group(1) or match.group(2)

        return ip

    def get_ansible_vault_decrypted_password(self, section, password_key, file_path):
        self.operator._is_clean_cmd_info = True
        cmd = "yq .{}.{} {}".format(section, password_key, file_path)
        out = self.operator.get_output_from_run_cmd(cmd)
        decrypted_password = self.decrypt_password(out)
        return decrypted_password

    def decrypt_password(self, encrypted_password):
        vault_password_file = ""
        for file_path in self.VAULT_PASSWORD_FILES:
            if self.operator.file_utils.is_file_exist(file_path):
                vault_password_file = file_path
                break
        if not vault_password_file:
            raise UnExpectedSystemOutput(self.operator.get_host_ip(),
                                         "",
                                         "",
                                         "Unexpected output: none of the vault files {} were found.".format(self.VAULT_PASSWORD_FILES))

        self.operator._is_clean_cmd_info = True
        cmd = "echo '{}' | sudo ansible-vault decrypt --vault-password-file {}".format(encrypted_password, vault_password_file)
        out = self.operator.get_output_from_run_cmd(cmd)
        return out

    def is_system_armed(self):
        # when system is armed all passwords in all CBIS configuration files are encrypted
        locked_files = ['stackrc_locked', 'overcloudrc_locked']
        for rcfile in locked_files:
            if not self.operator.file_utils.is_file_exist(os.path.join('/home/stack/', rcfile)):
                return False
        return True

    @lazy_global_data_loader
    def get_stackrc_file_path(self):
        default_path = '/home/stack/'
        if self.is_system_armed():
            return os.path.join(default_path, 'stackrc_locked')
        return os.path.join(default_path, 'stackrc')

    @lazy_global_data_loader
    def get_overcloudrc_file_path(self):
        default_path = '/home/stack/'
        if self.is_system_armed():
            return os.path.join(default_path, 'overcloudrc_locked')
        return os.path.join(default_path, 'overcloudrc')