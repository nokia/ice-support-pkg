from __future__ import absolute_import
from __future__ import print_function
import os.path
from HealthCheckCommon.base_init_flow import BaseInitFlow
from HealthCheckCommon.operations import *
import tools.sys_parameters as sys_parameters
from tools.global_logging import log_and_print, log_and_print_with_frame
from flows_of_sys_operations.sys_data_collector.log_collector import log_collector_params


class FilesCollectorPreFlow(BaseInitFlow):
    def init_validations(self):
        FilesCollector.tmp_file_path = os.path.join(log_collector_params.base_collector_dir, FilesCollector.TMP_FILE_NAME)
        FilesCollector.working_dir = os.path.join(log_collector_params.base_collector_dir, FilesCollector.WORKING_DIR_NAME)
        FilesCollector.filtered_dir = os.path.join(FilesCollector.working_dir, FilesCollector.FILTERED_DIR_NAME)
        FilesCollector.tar_base_dir = os.path.join(log_collector_params.base_collector_dir, FilesCollector.TAR_DIR_NAME)
        FilesCollector.FINAL_TAR_GZ_FOLDER = "/root/collector"

        FilesCollector.DISK_SPACE_THRESHOLD = 10485760  # 10GB (in megabytes)
        FilesCollector.MAX_LOG_FILE_SIZE = 419430400  # 400MB (in bytes)

        FilesCollector.data_store = {}
        FilesCollector.all_added_files = {}
        FilesCollector.files_size_list = []

        FilesCollector.host_with_collected_files = 'Hypervisor'
        FilesCollector.collector_permissions = ""


class FilesCollector(SystemOperator):
    TMP_FILE_NAME = 'test_operation_sys.txt'
    tmp_file_path = None
    WORKING_DIR_NAME = 'collector'
    working_dir = None
    FILTERED_DIR_NAME = 'filtered'
    filtered_dir = None
    TAR_DIR_NAME = 'ICE'
    tar_base_dir = None
    ICE_COLLECTOR_FILE_MANE = None
    COLLECTOR_TGZ_FILE_MANE = None
    FINAL_TAR_GZ_FOLDER = None

    DISK_SPACE_THRESHOLD = None
    MAX_LOG_FILE_SIZE = None

    data_store = None
    all_added_files = None
    files_size_list = None

    host_with_collected_files = None
    collector_path = None
    collector_permissions = None

    def run_system_operation(self):
        try:
            return self.run_collector_operator()
        except Exception as e:
            print("\nERROR: Caught an exception of type '{}' on {}:\n{}\n".format(type(e).__name__, self.get_host_name(), str(e)))
            raise e

    def run_collector_operator(self):
        raise NotImplementedError

    def get_tar_name(self):
        tar_name = os.path.join(FilesCollector.tar_base_dir, 'ICE-{}.tar'.format(self.get_host_name()))
        return tar_name

    def get_gz_name(self):
        return self.get_tar_name() + ".gz"

    def get_scp_cmd(self):
        if sys_parameters.get_deployment_type() == Deployment_type.CBIS:
            scp_cmd = 'nice -n 4 scp -o StrictHostKeyChecking=no cbis-admin@{}:{} {}'
        elif sys_parameters.get_deployment_type() in [Deployment_type.NCS_OVER_BM]:
            scp_cmd = 'nice -n 4 sudo scp -o StrictHostKeyChecking=no -i /home/cbis-admin/.ssh/id_rsa cbis-admin@{}:{} {}'
        else:
            assert False, 'not implemented yet !'
        return scp_cmd

    def verify_enough_space_for_files_in_path(self, files_size, path):
        available_disk_space_size = self.system_utils.get_available_disk_space_size(path=path, size_unit=SizeUnit.B)
        if files_size >= available_disk_space_size:
            raise NoAvailableDiskSpace(files_size, available_disk_space_size, SizeUnit.B, path)

    def get_hosts_tgz_files_list(self):
        hosts_tgz_files_list = []
        for ip in FilesCollector.data_store:
            zip_name = FilesCollector.data_store[ip]
            file_name_with_no_path = zip_name.split('/')[-1]
            file_name_in_new_dir = os.path.join(FilesCollector.working_dir, file_name_with_no_path)
            return_code, out, err = self.run_cmd('ls {}'.format(file_name_in_new_dir))
            if return_code == 0:
                hosts_tgz_files_list.append(file_name_with_no_path)
        return hosts_tgz_files_list


class CreateTarFile(FilesCollector):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.ALL_HOSTS, Objectives.HYP],
        Deployment_type.NCS_OVER_BM: [Objectives.ALL_NODES, Objectives.MANAGERS],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ALL_NODES, Objectives.MANAGERS]
    }

    def set_document(self):
        self._unique_operation_name = "create_tar_file"
        self._title = "Creating a tar file to add the data to"
        self._failed_msg = "Creating tar file was failed"
        self._run_in_parallel = True
        self._prerequisite_unique_operation_name = ""
        self._printable_title = 'Creating *.tar at {} for each host'.format(FilesCollector.tar_base_dir)

    def run_collector_operator(self):
        self.verify_free_disk_space_before_run()
        tar_name = self.get_tar_name()
        return_code, out, err = self.run_cmd(
            'sudo mkdir -m 777 -p {} ; sudo tar -cf {} -T /dev/null'.format(FilesCollector.tar_base_dir, tar_name))
        if return_code == 0:
            self.file_utils.change_file_permissions("777", tar_name)
            log_and_print('{}: File {} was created'.format(self.get_host_name(), tar_name))
            FilesCollector.data_store[self.get_host_ip()] = tar_name
            FilesCollector.all_added_files[self.get_host_name()] = []
        return (return_code == 0)

    def verify_free_disk_space_before_run(self):
        available_disk_space_size = self.system_utils.get_available_disk_space_size()
        if available_disk_space_size < FilesCollector.DISK_SPACE_THRESHOLD:
            raise NoAvailableDiskSpace(FilesCollector.DISK_SPACE_THRESHOLD, available_disk_space_size, SizeUnit.KB)


class ZipTarFile(FilesCollector):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.ALL_HOSTS, Objectives.HYP],
        Deployment_type.NCS_OVER_BM: [Objectives.ALL_NODES, Objectives.MANAGERS],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ALL_NODES, Objectives.MANAGERS]
    }

    def set_document(self):
        self._unique_operation_name = "gzip_the_tar_files"
        self._title = "Tar files gzip"
        self._failed_msg = "Failed to compress the tar files using gzip"
        self._run_in_parallel = True
        self._prerequisite_unique_operation_name = "append_logs_files_to_tar_file"
        self._printable_title = 'Zip *.tar file at {} for each host'.format(FilesCollector.tar_base_dir)

    def run_collector_operator(self):
        tar_name = self.get_tar_name()
        gz_name = self.get_gz_name()
        # TODO add comment why --force
        self.safe_run_cmd("nice -n 4 sudo gzip -1 --force {}".format(tar_name), timeout=180)
        FilesCollector.files_size_list.append(self.file_utils.get_file_size(gz_name))
        FilesCollector.data_store[self.get_host_ip()] = gz_name
        log_and_print('{}: Zip {} file and creating {}'.format(self.get_host_name(), tar_name, gz_name))
        return True


class ScpToManager(FilesCollector):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.UC],
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MANAGER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MANAGER]
    }

    def set_document(self):
        self._unique_operation_name = "copy file to UC/Manager"
        self._title = "Copy files to UC/Manager"
        self._failed_msg = "Failed to copy files to UC/Manager"
        self._run_in_parallel = False
        self._prerequisite_unique_operation_name = "gzip_the_tar_files"
        self._is_prerequisite_on_multiple_hosts = True
        self._is_prerequisite_pass_if_any_passed = True
        self._printable_title = 'Copy *.tar.gz of each host to {} on undercloud / manager'.format(
            FilesCollector.working_dir)

    def should_add_base_hosts(self):
        return True

    def run_collector_operator(self):
        self.safe_run_cmd("sudo mkdir -m 777 -p {}".format(FilesCollector.working_dir))
        local_copy_cmd = "sudo cp {} {}"
        scp_cmd = self.get_scp_cmd()
        local_ip = self.get_host_ip()  # this is were we run from ie UC or master
        self.verify_enough_space_for_files_in_path(files_size=sum(FilesCollector.files_size_list) * 2,
            path=log_collector_params.base_collector_dir)
        for ip in FilesCollector.data_store:
            zip_name = FilesCollector.data_store[ip]
            log_and_print('{}: Copy {} from {} to {} on {}'.format(
                self.get_host_name(), zip_name, ip, FilesCollector.working_dir,
                self.objective_hosts.get(gs.get_deployment_type())[0]))
            if ip == local_ip:
                return_code, out, err = self.run_cmd(local_copy_cmd.format(zip_name, FilesCollector.working_dir),
                                                     timeout=180)
            else:
                return_code, out, err = self.run_cmd(scp_cmd.format(ip, zip_name, FilesCollector.working_dir),
                                                     timeout=180)
            if return_code != 0:
                self._details += "copy files failed on {}".format(ip)
                log_and_print("Failed to copy files failed from {}:\n{}".format(ip, err))
                return False
        return True


class TgzHostsTgzFilesOnManager(FilesCollector):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.UC],
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MANAGER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MANAGER]
    }

    def set_document(self):
        self._unique_operation_name = "tgz_hosts_tgz_files_on_manager"
        self._title = "Tar and zip hosts tgz files into a single final tgz file"
        self._failed_msg = "Failed to taring and zipping hosts tgz files into a single tgz file"
        self._run_in_parallel = False
        self._prerequisite_unique_operation_name = "copy file to UC/Manager"

    def should_add_base_hosts(self):
        return True

        # TODO add prerequest

    def run_collector_operator(self):
        flg_is_any_ok = False
        hosts_tgz_files_list = self.get_hosts_tgz_files_list()
        hosts_tgz_files_total_size = self._get_total_size_of_hosts_tgz_files(hosts_tgz_files_list)
        self.verify_enough_space_for_files_in_path(files_size=hosts_tgz_files_total_size * 2, path=FilesCollector.working_dir)
        return_code, out, err = self.run_cmd('cd {} ; sudo tar -cf {} {}'.format(
            FilesCollector.working_dir, FilesCollector.ICE_COLLECTOR_FILE_MANE, ' '.join(hosts_tgz_files_list)),
            timeout=180)

        if return_code != 0:
            self._details = "Failed to tar the tgz files on {}".format(self.get_host_name())
        else:
            collector_tar_path = os.path.join(FilesCollector.working_dir, FilesCollector.ICE_COLLECTOR_FILE_MANE)
            FilesCollector.collector_permissions = self.file_utils.get_file_permission_id(collector_tar_path)
            self.file_utils.change_file_permissions("777", collector_tar_path)
            self.safe_run_cmd("nice -n 4 sudo gzip -1 --force {}".format(collector_tar_path), timeout=180)
            flg_is_any_ok = True
            FilesCollector.host_with_collected_files = self.get_host_name()
            FilesCollector.collector_path = os.path.join(FilesCollector.working_dir, FilesCollector.COLLECTOR_TGZ_FILE_MANE)
            log_and_print("\n===========  Collector files can be found on: {} at {}  ===========".
                          format(FilesCollector.host_with_collected_files, FilesCollector.collector_path))

        return (flg_is_any_ok)

    def _get_total_size_of_hosts_tgz_files(self, hosts_tgz_files_list):
        hosts_tgz_files_total_size = 0
        if hosts_tgz_files_list:
            for tgz_name in hosts_tgz_files_list:
                tgz_path = os.path.join(FilesCollector.working_dir, tgz_name)
                tgz_size = self.file_utils.get_file_size(tgz_path)
                hosts_tgz_files_total_size += tgz_size
        return hosts_tgz_files_total_size


class CleanHosts(FilesCollector):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.ALL_HOSTS, Objectives.HYP],
        Deployment_type.NCS_OVER_BM: [Objectives.ALL_NODES, Objectives.MANAGERS],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ALL_NODES, Objectives.MANAGERS]
    }

    def set_document(self):
        self._unique_operation_name = "cleaning_gz_files_from_hosts"
        self._title = "Deleting tar.gz files from all the hosts"
        self._failed_msg = "Failed in cleaning gz files"
        self._run_in_parallel = True
        self._prerequisite_unique_operation_name = ""
        self._printable_title = 'Deleting *.tar.gz from {} on all hosts'.format(FilesCollector.tar_base_dir)

    def run_collector_operator(self):
        gz_name = self.get_gz_name()
        return_code, out, err = self.run_cmd('ls {}'.format(gz_name))
        if return_code == 0:
            self.safe_run_cmd('sudo rm -f {}'.format(gz_name))
            log_and_print('{}: Delete {}'.format(self.get_host_name(), gz_name))
        return True


class PrintFilesList(FilesCollector):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.UC],
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MANAGER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MANAGER]
    }

    def set_document(self):
        self._unique_operation_name = "printing_list_of_collected_files"
        self._title = "Printing list of collected files"
        self._failed_msg = "Failed printing"
        self._run_in_parallel = False
        self._prerequisite_unique_operation_name = "copy file to UC/Manager"
        self._printable_title = 'List of collected files:'

    def should_add_base_hosts(self):
        return True

    def run_collector_operator(self):
        log_and_print(json.dumps(FilesCollector.all_added_files, indent=4))
        return True


class CleanManager(FilesCollector):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.UC],
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MANAGER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MANAGER]
    }

    def set_document(self):
        self._unique_operation_name = "cleaning_gz_files_from_manager"
        self._title = "Deleting tar.gz files from UC/manager"
        self._failed_msg = "Failed in cleaning gz files from UC/manager"
        self._run_in_parallel = True
        self._prerequisite_unique_operation_name = ""
        self._printable_title = 'Deleting *.tar.gz hosts files from undercloud / manager'

    def should_add_base_hosts(self):
        return True

    def run_collector_operator(self):
        for file_name_with_no_path in self.get_hosts_tgz_files_list():
            self.safe_run_cmd("sudo rm -f " + os.path.join(FilesCollector.working_dir, file_name_with_no_path))
            log_and_print('{}: Delete {}'.format(self.get_host_name(), os.path.join(FilesCollector.working_dir,
                                                                                    file_name_with_no_path)))
        return True


class TgzSizeDataCollector(DataCollector):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.UC],
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MANAGER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MANAGER]
    }

    def collect_data(self, **kwargs):
        collector_tgz_path = kwargs['collector_tgz_path']
        return self.file_utils.get_file_size(collector_tgz_path)


class CopyToFinalFolder(FilesCollector):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.HYP],
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MANAGER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MANAGER]
    }

    def set_document(self):
        self._unique_operation_name = "copy_to_final_folder"
        self._title = "Copy final tar.gz file with all the collected logs to Hypervisor / Manager"
        self._failed_msg = "Failed to copy tar.gz file to final directory on Hypervisor / Manager"
        self._run_in_parallel = True
        self._prerequisite_unique_operation_name = "tgz_hosts_tgz_files_on_manager"

    def should_add_base_hosts(self):
        return True

    def run_collector_operator(self):
        collector_tgz_path = os.path.join(FilesCollector.working_dir, FilesCollector.COLLECTOR_TGZ_FILE_MANE)
        res = self.run_data_collector(TgzSizeDataCollector, collector_tgz_path=collector_tgz_path)
        main_host = list(res.keys())[0]
        file_size_in_bytes = res[main_host]
        self.verify_enough_space_for_files_in_path(files_size=file_size_in_bytes * 2, path="/")
        self.safe_run_cmd('sudo mkdir -m 777 -p {}'.format(FilesCollector.FINAL_TAR_GZ_FOLDER))
        if gs.get_deployment_type() is Deployment_type.CBIS:
            self.safe_run_cmd('nice -n 4 sudo scp -q -o "StrictHostKeyChecking no" stack@uc:{uc_path} {hv_path}'.format(
                uc_path=collector_tgz_path, hv_path=FilesCollector.FINAL_TAR_GZ_FOLDER), timeout=60)
            cmd = "sudo rm -f {}".format(FilesCollector.collector_path)
            gs.get_host_executor_factory().run_command_on_first_host_from_selected_roles(
                cmd, roles=[FilesCollector.host_with_collected_files])
            FilesCollector.host_with_collected_files = 'Hypervisor'
        else:
            self.safe_run_cmd('nice -n 4 sudo mv {} {}'.format(collector_tgz_path, FilesCollector.FINAL_TAR_GZ_FOLDER),
                              timeout=60)
        FilesCollector.collector_path = os.path.join(FilesCollector.FINAL_TAR_GZ_FOLDER,
                                                     FilesCollector.COLLECTOR_TGZ_FILE_MANE)
        log_and_print("\n===========  Collector Files were copied successfully to {} at {}  ===========\n".format(
            FilesCollector.host_with_collected_files, FilesCollector.collector_path))

        return True


class ChangePermissionsOnManager(FilesCollector):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MANAGER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MANAGER]
    }

    def set_document(self):
        self._unique_operation_name = "change_permissions_on_manager"
        self._title = "Change permissions on manager"
        self._failed_msg = "Change permissions on manager was failed"
        self._run_in_parallel = False
        self._prerequisite_unique_operation_name = "tgz_hosts_tgz_files_on_manager"

    def should_add_base_hosts(self):
        return True

    def run_collector_operator(self):
        collector_tgz_path = os.path.join(FilesCollector.working_dir, FilesCollector.COLLECTOR_TGZ_FILE_MANE)
        self.file_utils.change_file_permissions(FilesCollector.collector_permissions, collector_tgz_path)
        return True


class PrintFinalFilesLocation(FilesCollector):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.UC],
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MANAGER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MANAGER]
    }

    def set_document(self):
        self._unique_operation_name = "print_final_collected_files_location"
        self._title = "Print the final collected files location"
        self._failed_msg = "Failed printing of final collected files location"
        self._run_in_parallel = False
        self._prerequisite_unique_operation_name = "copy_to_final_folder"

    def should_add_base_hosts(self):
        return True

    def run_collector_operator(self):
        print_msg = 'Collector Files are located on {} at {}'.format(FilesCollector.host_with_collected_files,
                                                                     FilesCollector.collector_path)
        log_and_print_with_frame(print_msg)
        return True
