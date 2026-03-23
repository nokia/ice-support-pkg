from __future__ import absolute_import
import os
from datetime import datetime, timedelta
from flows_of_sys_operations.sys_data_collector.collector import FilesCollector, FilesCollectorPreFlow
from tools import sys_parameters, paths
from tools.Exceptions import NoAvailableDiskSpace
from tools.global_enums import Deployment_type, Objectives, SizeUnit
import tools.sys_parameters as gs
from tools.global_logging import log_and_print
from tools.python_utils import PythonUtils
from flows_of_sys_operations.sys_data_collector.log_collector import log_collector_params


class LogsCollectorPreFlow(FilesCollectorPreFlow):
    def init_validations(self):
        super(LogsCollectorPreFlow, self).init_validations()
        cluster_name = gs.get_cluster_name() if gs.get_cluster_name() else ""
        FilesCollector.ICE_COLLECTOR_FILE_MANE = "log_collector_{}.ice.tar".format(cluster_name)
        FilesCollector.COLLECTOR_TGZ_FILE_MANE = "{}.gz".format(FilesCollector.ICE_COLLECTOR_FILE_MANE)
        FilesCollector.collector_path = os.path.join(FilesCollector.FINAL_TAR_GZ_FOLDER,
                                                     FilesCollector.COLLECTOR_TGZ_FILE_MANE)


class AppendLogsFilesToTar(FilesCollector):
    log_of_interest = []

    objective_hosts = {
        Deployment_type.CBIS: [Objectives.ALL_HOSTS, Objectives.HYP],
        Deployment_type.NCS_OVER_BM: [Objectives.ALL_NODES, Objectives.MANAGERS],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ALL_NODES, Objectives.MANAGERS]
    }

    def set_document(self):
        self._unique_operation_name = "append_logs_files_to_tar_file"
        self._title = "Append files to tar"
        self._failed_msg = "Failed to append logs files to the tar file"
        self._run_in_parallel = True
        self._prerequisite_unique_operation_name = "create_tar_file"
        self._printable_title = 'Collecting predefined logs from each host from the last {} days'.format(
            log_collector_params.period_of_log_collecting_in_days)
        if log_collector_params.start_date_log_collecting and log_collector_params.end_date_log_collecting:
            original_end_date_datetime = datetime.strptime(log_collector_params.end_date_log_collecting,
                                                           log_collector_params.date_format) + timedelta(days=-1)
            original_end_date_str = original_end_date_datetime.strftime(log_collector_params.date_format)
            self._printable_title = 'Collecting predefined logs from each host between the {start_date} and the {end_date}'. \
                format(start_date=log_collector_params.start_date_log_collecting, end_date=original_end_date_str)

    def run_collector_operator(self):
        files_to_append = []
        host_files_size = 0
        self.safe_run_cmd("sudo mkdir -m 777 -p {}".format(FilesCollector.working_dir))
        list_of_log_template = self._get_list_of_logs_for_this_host()
        try:
            for file_template in list_of_log_template:
                files_of_interest = {}
                log_and_print('{}: Collecting logs from {}'.format(self.get_host_name(), file_template))
                start_date = log_collector_params.start_date_log_collecting
                end_date = log_collector_params.end_date_log_collecting
                if start_date and end_date:
                    find_files_of_interest_cmd = (
                        r'find {file_path} -newermt {start_date} ! -newermt {end_date} \( -type f -o -type l \)'
                        .format(file_path=file_template, start_date=start_date, end_date=end_date)
                    )
                    files_after_end_date = self._get_files_after_end_date(file_template)
                    files_of_interest.update(files_after_end_date)
                else:
                    find_files_of_interest_cmd = (
                        r'find {file_path} -mtime -{period_in_days} \( -type f -o -type l \)'
                        .format(file_path=file_template, period_in_days=str(
                        log_collector_params.period_of_log_collecting_in_days))
                    )
                return_code, out, err = self.run_sudo_cmd(find_files_of_interest_cmd)
                if 'No such file or directory' in err:
                    continue
                if out:
                    for file in out.splitlines():
                        if not files_of_interest.get(file):
                            files_of_interest[file] = "NOT SET"
                if files_of_interest:  # if this file is found on this host
                    for one_file, date_format in list(files_of_interest.items()):
                        cmd = 'ls -l {}'.format(one_file)
                        return_code, one_file, err = self.run_sudo_cmd(cmd)
                        one_file = self.file_utils.get_target_file_from_symbolic_link(one_file)
                        if one_file.startswith('total'):
                            continue  # might happen that symbolic link points on a directory
                        one_file = one_file.split()[-1]
                        if one_file in files_to_append or self.file_utils.is_file_empty(one_file):
                            continue
                        if date_format == "NOT SET":
                            first_date_in_file, full_date_format, date_format_only_date = self._find_date_from_file(one_file, is_short_date_format=True)
                            date_format = date_format_only_date
                        file_size = self.file_utils.get_file_size(one_file)
                        one_file, tmp_file_size = self._create_tmp_file_by_range(one_file, file_size, date_format)
                        if tmp_file_size:
                            file_size = tmp_file_size
                        if file_size < FilesCollector.MAX_LOG_FILE_SIZE:
                            host_files_size += file_size
                            files_to_append.append(one_file)
            self.verify_enough_space_for_files_in_path(files_size=host_files_size * 2, path=log_collector_params.base_collector_dir)
            for one_file in files_to_append:
                self._append_file_to_tar(one_file)
            return True
        finally:
            self.clean_tmp_files()

    def _create_tmp_file_by_range(self, origin_file, origin_file_size, date_format=None):
        if not date_format:
            return origin_file, None
        self._verify_enough_space_for_tmp_file(origin_file_size, FilesCollector.working_dir)
        sed_expression = self._get_sed_expression(date_format)
        file_by_range = self._get_path_of_filtered_file(origin_file)
        grep_file_by_time_range_cmd = 'sudo sh -c "sed -n \'{sed_expression}\' {origin_file_name} > ' \
                                      '{file_by_range}"'.format(sed_expression=sed_expression,
                                                                origin_file_name=origin_file,
                                                                file_by_range=file_by_range)
        if origin_file.endswith(".gz"):
            grep_file_by_time_range_cmd = 'sudo sh -c "sudo zcat {origin_file_name} | ' \
                                          'sed -n \'{sed_expression}\' | gzip > {file_by_range}"' \
                                          ''.format(origin_file_name=origin_file, sed_expression=sed_expression,
                                                    file_by_range=file_by_range)
        is_grep_cmd_successful = self.run_cmd_return_is_successful(grep_file_by_time_range_cmd, timeout=60)
        if is_grep_cmd_successful and not self.file_utils.is_file_empty(file_by_range):
            file_by_range_size = self.file_utils.get_file_size(file_by_range)
            return file_by_range, file_by_range_size
        else:
            self.run_cmd('sudo rm -rf {}'.format(file_by_range))
            return origin_file, None

    def _get_sed_expression(self, date_format):
        end_date, start_date = self._get_end_and_start_dates(date_format)
        sed_expression = r"/^{start_date}/,/^{end_date}/p; /\[{start_date}/,/\[{end_date}/p".format(
            start_date=start_date, end_date=end_date)

        if date_format == PythonUtils.TIME_FORMAT_WITH_SINGLE_DIGIT[1]:
            date_format_option2 = date_format.replace("%d", "%e")
            end_date, start_date = self._get_end_and_start_dates(date_format_option2)
            sed_expression += r"; /^{start_date}/,/^{end_date}/p; /\[{start_date}/,/\[{end_date}/p".format(
                start_date=start_date, end_date=end_date)

        return sed_expression

    def _get_end_and_start_dates(self, date_format):
        if log_collector_params.start_date_log_collecting:
            start_date_by_default_format = log_collector_params.start_date_log_collecting
            start_date = self._get_str_date_by_format(start_date_by_default_format, date_format)
            end_date_by_default_format = log_collector_params.end_date_log_collecting
            end_date = self._get_str_date_by_format(end_date_by_default_format, date_format)
        else:
            now = datetime.now() + timedelta(days=1)
            start_datetime = now - timedelta(days=(log_collector_params.period_of_log_collecting_in_days + 1))
            end_date = now.strftime(date_format)
            start_date = start_datetime.strftime(date_format)

        end_date = end_date.replace("/", "\\/")
        start_date = start_date.replace("/", "\\/")

        return end_date, start_date

    def _create_related_folder(self, file_path):
        related_folder = os.path.dirname(file_path)
        self.safe_run_cmd("sudo mkdir -m 777 -p {}".format(os.path.join(FilesCollector.filtered_dir, related_folder[1:])))
        return related_folder

    def _get_path_of_filtered_file(self, origin_file):
        related_folder = self._create_related_folder(origin_file)
        full_file_name = os.path.basename(origin_file)
        file_name, file_extension = os.path.splitext(full_file_name)
        new_file_name = file_name + '.ice_filtered' + file_extension
        filtered_file_path = os.path.join(FilesCollector.filtered_dir, related_folder[1:], new_file_name)
        return filtered_file_path

    def _append_file_to_tar(self, file_path):
        tar_name = self.get_tar_name()
        if file_path.startswith(FilesCollector.filtered_dir):
            file_path = file_path[len(FilesCollector.filtered_dir):]
            self.run_cmd('nice -n 4 sudo tar --append -v --file {} -C {} {}'.format(
                tar_name, FilesCollector.filtered_dir, file_path[1:]), timeout=300)
        else:
            self.run_cmd('nice -n 4 sudo tar --append -v --file {} {}'.format(tar_name, file_path), timeout=300)
        FilesCollector.all_added_files[self.get_host_name()].append(file_path)

    def _get_list_of_logs_for_this_host(self):
        all_logs = self._get_all_logs_from_conf()
        if isinstance(all_logs, list):
            return all_logs

        if all_logs is None:
            all_logs = dict()

        assert isinstance(all_logs, dict)
        log_set = set()

        self._verify_all_logs_roles_are_valid(all_logs)
        for role in self._host_executor.roles:
            for role_in_all_logs in list(all_logs.keys()):
                if role == eval(role_in_all_logs):
                    logs_for_this_role = set(all_logs[role_in_all_logs])
                    log_set = log_set.union(logs_for_this_role)
        return list([_f for _f in list(log_set) if _f])

    def _get_all_logs_from_conf(self):
        if not AppendLogsFilesToTar.log_of_interest:
            log_of_interest_file = self._get_path_for_log_of_interest()
            with open(log_of_interest_file, "r") as f:
                AppendLogsFilesToTar.log_of_interest = PythonUtils.yaml_safe_load(f, file_path=log_of_interest_file)
        return AppendLogsFilesToTar.log_of_interest

    def _verify_all_logs_roles_are_valid(self, all_logs):
        deployment_roles = Objectives.get_available_types(gs.get_deployment_type())
        for config_role in list(all_logs.keys()):
            assert eval(config_role) in deployment_roles, \
                "The role '{}' is not in {} roles by {}".format(config_role, deployment_roles,
                                                                self._get_path_for_log_of_interest())

    def _get_path_for_log_of_interest(self):
        if log_collector_params.path_to_specific_scenario:
            return log_collector_params.path_to_specific_scenario

        if sys_parameters.get_deployment_type() == Deployment_type.CBIS:
            return paths.LOG_COLLECTOR_CONF_FILES_DIR + paths.CBIS_LOG_OF_INTEREST

        if sys_parameters.get_deployment_type() in [Deployment_type.NCS_OVER_BM]:
            return paths.LOG_COLLECTOR_CONF_FILES_DIR + paths.NCS_LOG_OF_INTEREST
        else:
            assert 'not implemented yet !'

    def _get_files_after_end_date(self, file_path):
        files_after_end_date = {}
        find_files_after_end_date_cmd = (
            r'find {file_path} -newermt {from_date} \( -type f -o -type l \)'.format(
            file_path=file_path, from_date=log_collector_params.end_date_log_collecting)
        )
        return_code, out, err = self.run_sudo_cmd(find_files_after_end_date_cmd)
        if out:
            for file in out.splitlines():
                if self.file_utils.is_file_empty(file):
                    continue
                first_date_in_file, full_date_format, date_format_only_date = self._find_date_from_file(file, is_short_date_format=True)
                if not first_date_in_file:
                    files_after_end_date[file] = date_format_only_date
                    continue
                first_date_in_file, full_date_format = self._ensure_having_year_in_date_format(first_date_in_file, full_date_format)
                try:
                    first_date_in_file_datetime = datetime.strptime(first_date_in_file, full_date_format)
                except:
                    files_after_end_date[file] = date_format_only_date
                    continue
                end_date_datetime = datetime.strptime(log_collector_params.end_date_log_collecting,
                                                      log_collector_params.date_format)
                is_file_created_before_end_date = self._is_date_before_end_date(first_date_in_file_datetime,
                                                                                end_date_datetime)
                if is_file_created_before_end_date:
                    files_after_end_date[file] = date_format_only_date
        return files_after_end_date

    def _find_date_from_file(self, file, is_short_date_format=False):
        if os.path.splitext(file)[1] == ".gz":
            cat_cmd = "zcat"
        else:
            cat_cmd = "cat"
        cmd = "sudo {} {} | head -30 | grep -vi -E 'compiled|linux|python'".format(cat_cmd, file)  # remove lines that may contain date that is not the start date of the log
        head_out = self.get_output_from_run_cmd(cmd)
        return PythonUtils.find_dates(head_out, is_short_date_format, search_in_start_of_line=True)

    def _is_date_before_end_date(self, date, end_date):
        try:
            if date < end_date:
                return True
            return False
        except:
            raise ValueError("The dates must be from datetime type")

    def _ensure_having_year_in_date_format(self, date_string, date_format):
        if "%Y" not in date_format and "%y" not in date_format:
            current_year = datetime.now().year
            date_string = date_string + " " + str(current_year)
            date_format = date_format + " " + "%Y"
        return date_string, date_format

    def _verify_enough_space_for_tmp_file(self, origin_file_size, parent_dir_file_path):
        available_disk_space_size = self.system_utils.get_available_disk_space_size(path=parent_dir_file_path, size_unit=SizeUnit.B)
        required_disk_space = origin_file_size * 2
        if available_disk_space_size < required_disk_space:
            raise NoAvailableDiskSpace(required_disk_space, available_disk_space_size, SizeUnit.B, parent_dir_file_path)

    def clean_tmp_files(self):
        cmd = 'sudo rm -rf {}'.format(os.path.join(FilesCollector.working_dir, FilesCollector.FILTERED_DIR_NAME))
        self.run_cmd(cmd)

    def _get_str_date_by_format(self, str_date, date_format):
        datetime_date = datetime.strptime(str_date, log_collector_params.date_format)
        date_by_format = datetime_date.strftime(date_format)
        return date_by_format
