from __future__ import absolute_import
from collections import OrderedDict
from tools.Exceptions import UnExpectedSystemOutput, UnExpectedSystemTimeOut


class FileUtils(object):

    CLOSED_PERMISSIONS = '400'
    OPENED_PERMISSIONS = '777'
    R_W_PERMISSIONS = '666'

    def __init__(self, operator):
        self.operator = operator

    def is_file_exist(self, file_path):
        return_code, _, _ = self.operator.run_cmd("sudo find {}".format(file_path))

        return return_code == 0

    def verify_file_exists(self, file_path, ip='', timeout=20):
        cmd = "sudo ls {}".format(file_path)
        return_code, out, err = self.operator.run_cmd(cmd)
        if return_code != 0:
            message = "Un-Expected output: File {} is not found".format(file_path)
            self.operator._set_cmd_info(cmd, timeout, return_code, out, err)
            raise UnExpectedSystemOutput(ip=ip, cmd=cmd, output=out + err, message=message)

    def is_file_exist_on_host_roles(self, file_path, host_role_list):
        cmd = "sudo find {}".format(file_path)
        err_msg_list = ['No such file or directory']
        return self.operator.is_run_cmd_successful_on_host_role(cmd, host_role_list, err_msg_list)

    def is_dir_exist(self, dir_path):
        return_code, out, err = self.operator.run_cmd("sudo test -d {}".format(dir_path))
        if return_code != 0:
            return False
        return True

    def find_file_in_dir(self, dir_path, file_name):
        find_file_out = self.operator.get_output_from_run_cmd(
            r"sudo find {dir_path} -maxdepth 1 \( -type f -o -type l \) -name {file_name}".format(dir_path=dir_path, file_name=file_name))
        return find_file_out

    def _get_file_status(self, status_format, file_path, is_int_output=False):
        stat_cmd = "sudo stat -c '{}' {}".format(status_format, file_path)
        if is_int_output:
            return self.operator.get_int_output_from_run_cmd(stat_cmd)
        else:
            return self.operator.get_output_from_run_cmd(stat_cmd).replace('\n', '')

    def get_file_permissions_dict(self, file_path):
        file_permissions_dict = OrderedDict()
        permission_flag_dict = OrderedDict(
            [('permission_name', '%A'), ('permission_id', '%a'), ('user_name', '%U'), ('user_id', '%u'),
             ('group_name', '%G'), ('group_id', '%g')])
        for key, value in list(permission_flag_dict.items()):
            file_permissions_dict[key] = self._get_file_status(value, file_path)
        return file_permissions_dict

    def get_file_permission_id(self, file_path):
        return self._get_file_status('%a', file_path)

    def get_file_size(self, file_path):
        return self._get_file_status('%s', file_path, is_int_output=True)

    def get_last_change_time(self, file_path):
        return self._get_file_status('%z', file_path)

    def get_last_change_int_time(self, file_path):
        return self._get_file_status('%Z', file_path, is_int_output=True)

    def change_file_owner(self, owner, file_path):
        self.operator.get_output_from_run_cmd("sudo chown {} {}".format(owner, file_path))

    def change_file_group(self, group, file_path):
        self.operator.get_output_from_run_cmd("sudo chgrp {} {}".format(group, file_path))

    def change_file_permissions(self, permissions, file_path):
        if self.get_file_permission_id(file_path) != permissions:
            self.operator.get_output_from_run_cmd("sudo chmod {} {}".format(permissions, file_path))

    def is_file_readable(self, file_path):
        return_code, out, err = self.operator.run_cmd("sudo tail -1 {}".format(file_path))
        if 'error reading' in err:
            return False
        return True

    def is_file(self, file_path):
        return_code, out, err = self.operator.run_cmd("sudo test -f {}".format(file_path))
        if return_code != 0:
            return False
        return True

    def get_lines_in_file(self, file_path):
        return_code, out, err = self.operator.run_cmd("sudo cat {}".format(file_path))
        if return_code != 0:
            return None
        return out.splitlines()

    def is_file_empty(self, file_path):
        if file_path.endswith(".gz"):
            cat_cmd = "zcat"
        else:
            cat_cmd = "cat"
        # file can be empty although  get_file_size > 0
        is_file_empty = self.operator.get_int_output_from_run_cmd("sudo {} {} | head -20 | wc -w"
                                                                  .format(cat_cmd, file_path))
        if is_file_empty == 0:
            return True
        return False

    def read_file(self, path):
        cmd = "sudo cat {}".format(path)
        try:
            return_code, out, err = self.operator.run_cmd(cmd)
        except UnExpectedSystemTimeOut as e:
            raise UnExpectedSystemOutput(self.operator.get_host_ip(), cmd,
                                         "Failed to read the file, got unexpected timeout, maybe file size is too big",
                                         e.message)
        if return_code != 0:
            error = "problem reading the file {} :\n{}\n".format(path, err)
            raise UnExpectedSystemOutput(self.operator.get_host_name(), cmd, error)
        return out

    def write_content_to_file(self, file_path, content_to_write):
        if self.is_file_exist(file_path):
            self.change_file_permissions(permissions=FileUtils.OPENED_PERMISSIONS, file_path=file_path)
        try:
            with open(file_path, "w") as f:
                f.write(content_to_write)
        finally:
            if self.is_file_exist(file_path):
                self.change_file_permissions(permissions=FileUtils.CLOSED_PERMISSIONS, file_path=file_path)
        self.change_file_owner(owner="root", file_path=file_path)
        self.change_file_group(group="root", file_path=file_path)

    def get_target_file_from_symbolic_link(self, target_file):
        while target_file[0] == 'l':
            target_file = self.operator.get_output_from_run_cmd('sudo ls -l {}'.format(target_file.split()[-1]))
        return target_file

    def symbolic_link_present_or_absent(self, target_file):
        return target_file[0] == 'l'


    def remove_file_if_exist(self, file_path):
        return_code, _, _ = self.operator.run_cmd("sudo ls {}".format(file_path))

        if return_code == 0:
            self.operator.get_output_from_run_cmd("sudo rm -f {}".format(file_path))

    def get_dir_content(self, dir_path):
        _, output, _ = self.operator.run_cmd("sudo ls {}".format(dir_path))

        return output.split()

    def copy_file(self, src, dest):
        self.operator.get_output_from_run_cmd("sudo cp {} {}".format(src, dest))

    def remove_file(self, file_path):
        self.operator.get_output_from_run_cmd("sudo rm -f {}".format(file_path))

    def with_file_permissions(self, path_to_file, required_permissions="666"):
        '''
        Context manager to temporarily change the permissions of a file and revert them afterwards.
        '''
        return FilePermissionsContextManager(path_to_file, required_permissions, self.operator)

    def is_file_modified_on_last_x_days(self, file_path, days):
        return_code, out, _ = self.operator.run_cmd("find {} -type f -mtime -{}".format(file_path, str(days)))
        if out:
            return True
        return False


    # Assuming 'searched_parameter_in_file' appears only once in the file (grep out is one line)
    # Expect the out to be in format of <key><delimiter><value> like 'key: value' or 'key=value' etc.
    def get_value_from_file (self, file_path, searched_parameter_in_file, split_delimiter=None, additional_cmd=''):
        value = None
        if self.is_file_exist(file_path):
            cmd = "sudo cat {} | grep '{}'{}".format(file_path, searched_parameter_in_file, additional_cmd)
            return_code, out, err = self.operator.run_cmd(cmd)
            if return_code == 0:
                value = out.strip()
                if split_delimiter:
                    out_parts = out.split(split_delimiter)
                    if len(out_parts) == 2:
                        value = out_parts[1].strip()
                    else:
                        raise UnExpectedSystemOutput(self.operator.get_host_ip(), cmd, out, "ERROR!! Wrong output - Expected to get output in format of 'KEY{}VALUE', but actual output is: {}".format(split_delimiter, out))
        else:
            raise UnExpectedSystemOutput(self.operator.get_host_ip(), "", "", "ERROR!! File {} does not exist".format(file_path))
        return value


class FilePermissionsContextManager:
    def __init__(self, path_to_file, required_permissions, operator):
        self.path_to_file = path_to_file
        self.operator = operator
        self.required_permissions = required_permissions
        self.original_permissions = None

    def __enter__(self):
        self.original_permissions = self.operator.file_utils.get_file_permission_id(self.path_to_file)
        self.operator.file_utils.change_file_permissions(self.required_permissions, self.path_to_file)

    def __exit__(self, exc_type, exc_value, traceback):
        self.operator.file_utils.change_file_permissions(self.original_permissions, self.path_to_file)
