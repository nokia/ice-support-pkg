from __future__ import absolute_import
from HealthCheckCommon.operations import DataCollector
from HealthCheckCommon.validator import Validator
from flows_of_sys_operations.FileTracker.FileTrackerPaths import FileTrackerPaths, FileTrackerPathsInitiator
from tools.global_enums import Objectives, Severity, Deployment_type,ImplicationTag
from tools.Info import GetInfo
from datetime import datetime, timedelta
from tools import adapter


class IsFileTrackerInstalled(Validator):
    objective_hosts = {
                        Deployment_type.CBIS: [Objectives.UC],
                        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MANAGER],
                        Deployment_type.NCS_OVER_VSPHERE: [Objectives.DEPLOYER],
                        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.DEPLOYER]
    }

    def set_document(self):
        self._unique_operation_name = "is_file_tracker_installed"
        self._title = "Check if ICE File Tracker is installed and run daily"
        self._failed_msg = "The File Tracker tool is not installed and run on the system:\n"
        self._severity = Severity.NOTIFICATION
        self._implication_tags = [ImplicationTag.NOTE]

    def is_validation_passed(self):
        res = self.get_first_value_from_data_collector(IsFileTrackerInstalledDataCollector)
        self._failed_msg += res['failed_msg']
        return res['is_installed']


class IsFileTrackerInstalledDataCollector(DataCollector):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.UC],
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MANAGER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.DEPLOYER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.DEPLOYER]
    }

    def collect_data(self):
        failed_msg = ""
        is_installed = False
        file_tracker_cron_job = '/etc/cron.daily/ice_file_tracker.sh'
        FileTrackerPathsInitiator()
        file_tracker_log = FileTrackerPaths.FILE_TRACKER_LOG_PATH
        is_cron_file_exist = self.file_utils.is_file_exist(file_tracker_cron_job)
        is_file_tracker_log_exist = self.file_utils.is_file_exist(file_tracker_log)
        if is_cron_file_exist and is_file_tracker_log_exist:
            is_installed = True
        else:
            if not is_cron_file_exist:
                failed_msg += "The File Tracker cron job file '{}' is not exist\n".format(file_tracker_cron_job)
            if not is_file_tracker_log_exist:
                failed_msg += "The File Tracker log is not exist\n"
            failed_msg += "\n**** Note: The File Tracker is not a mandatory tool, but is very recommended ****\n\n"
        res = {'is_installed': is_installed, 'failed_msg': failed_msg}
        return res


class FileTrackerMemoryUsage(Validator):
    objective_hosts = [Objectives.ALL_HOSTS, Objectives.HYP, Objectives.ALL_NODES, Objectives.MANAGERS,
                       Objectives.DEPLOYER]

    def set_document(self):
        self._unique_operation_name = "file_tracker_memory_usage_validation"
        self._title = "FileTracker memory usage validation"
        self._failed_msg = "TBD"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.NOTE, ImplicationTag.RISK_RESOURCE_CLEANING_RECOMMENDED]

    def is_prerequisite_fulfilled(self):
        FileTrackerPathsInitiator()
        return self.file_utils.is_dir_exist(FileTrackerPaths.FILE_TRACKER_DIR_PATH_ON_HOST)

    def is_validation_passed(self):
        failed_msg_list = []
        if Objectives.ONE_MANAGER in self.get_host_roles() and self.file_utils.is_dir_exist(FileTrackerPaths.MAIN_FILE_TRACKER_DIR_PATH):
            failed_msg_list = self.verify_memory_usage(FileTrackerPaths.MAIN_FILE_TRACKER_DIR_PATH, failed_msg_list)
        failed_msg_list = self.verify_memory_usage(FileTrackerPaths.FILE_TRACKER_DIR_PATH_ON_HOST, failed_msg_list)
        if failed_msg_list:
            self._failed_msg = "\n".join(failed_msg_list)
            return False
        return True

    def verify_memory_usage(self, path, failed_msg_list):
        MEMORY_THRESHOLD = 2147483648 #2G
        base_failed_msg = "The File Tracker tool is exceeding the memory limit of {MEMORY_THRESHOLD} bytes. " \
                           "The File Tracker directory:{path} has a memory footprint of {memory_in_use} bytes."
        cmd = "sudo du -hs {} --block-size=1".format(path)
        memory_in_use = int(self.get_output_from_run_cmd(cmd, timeout=60, add_bash_timeout=True).split()[0])
        if memory_in_use > MEMORY_THRESHOLD:
            failed_msg_list.append(base_failed_msg.format(MEMORY_THRESHOLD=MEMORY_THRESHOLD, path=path,
                                                          memory_in_use=memory_in_use))
        return failed_msg_list


class IsFileTrackerLocked(Validator):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.UC],
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MANAGER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.DEPLOYER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.DEPLOYER]
    }

    def set_document(self):
        self._unique_operation_name = "is_file_tracker_locked"
        self._title = "Check if File Tracker is locked"
        self._failed_msg = "File Tracker is locked for the next runs"
        self._severity = Severity.NOTIFICATION
        self._implication_tags = [ImplicationTag.NOTE]

    def is_prerequisite_fulfilled(self):
        FileTrackerPathsInitiator()
        return self.file_utils.is_dir_exist(FileTrackerPaths.MAIN_FILE_TRACKER_DIR_PATH)

    def is_validation_passed(self):
        if self.file_utils.is_file_exist(FileTrackerPaths.FILE_TRACKER_LOCKER):
            return False
        return True

class IsFileTrackerRunLastNight(Validator):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.UC],
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MANAGER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.DEPLOYER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.DEPLOYER]
    }

    def set_document(self):
        self._unique_operation_name = "is_file_tracker_run_last_night"
        self._title = "Check if the File Tracker was running last night"
        self._failed_msg = "The File Tracker was not running last night. Last run was on {}."
        self._severity = Severity.NOTIFICATION
        self._implication_tags = ImplicationTag.NOTE

    def is_prerequisite_fulfilled(self):
        FileTrackerPathsInitiator()
        return self.file_utils.is_dir_exist(FileTrackerPaths.MAIN_FILE_TRACKER_DIR_PATH)

    def is_validation_passed(self):
        today_date = datetime.today().date()
        ft_log_last_line = self.get_output_from_run_cmd("sudo tail -1 {}".format(FileTrackerPaths.FILE_TRACKER_LOG_PATH))
        date_str = ft_log_last_line.split()[0]
        last_ft_run_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        if last_ft_run_date < today_date:
            self._failed_msg = self._failed_msg.format(last_ft_run_date)
            return False
        return True


class IsICEVersionDateRecent(Validator):
    objective_hosts = {Deployment_type.CBIS: [Objectives.UC],
                       Deployment_type.NCS_OVER_BM: [Objectives.ONE_MANAGER]}

    DAYS_THRESHOLD = 80

    def set_document(self):
        self._unique_operation_name = "is_ice_version_date_recent_enough"
        self._title = "Check if the ICE version is from the last {} days".format(IsICEVersionDateRecent.DAYS_THRESHOLD)
        self._failed_msg = "The current ICE version {} is over {} days old.\nPlease install the latest ICE version, as it includes wider coverage of validations, fixes and improvements.".format(GetInfo.get_ice_version(), IsICEVersionDateRecent.DAYS_THRESHOLD)
        self._severity = Severity.NOTIFICATION
        self._implication_tags = [ImplicationTag.NOTE, ImplicationTag.APPLICATION_DOMAIN]

    def is_validation_passed(self):
        ice_version_str_date = GetInfo.get_ice_version_date()
        current_ice_version_datetime = datetime.strptime(ice_version_str_date, "%d-%m-%Y")
        ice_version_date_threshold = datetime.today() - timedelta(days=IsICEVersionDateRecent.DAYS_THRESHOLD)
        if current_ice_version_datetime < ice_version_date_threshold:
            return False
        return True


class VerifyIceContainerRuntime(Validator):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.UC],
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MANAGER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.DEPLOYER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.DEPLOYER]
    }

    def set_document(self):
        self._unique_operation_name = "Verify_ice_container_runtime"
        self._title = "Verify ice container runtime"
        self._failed_msg = "Some containers are running for too much time:\n"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.NOTE]

    def is_validation_passed(self):
        docker_or_podman = adapter.docker_or_podman()
        expected_time_units = ["second", "minute", "hour"]
        ice_containers_statuses = self.get_output_from_run_cmd('sudo {} ps --format "{{{{.Status}}}} {{{{.Names}}}}"| grep ice-'.format(
            docker_or_podman)).splitlines()
        failed_msg_list = []
        for container in ice_containers_statuses:
            container_status = ' '.join(container.split()[:-1])
            container_name = container.split()[-1]

            if not any(time_unit in container_status for time_unit in expected_time_units):
                container_start_time = self.get_output_from_run_cmd(
                    "sudo {} inspect -f '{{{{ .State.StartedAt }}}}' {}".format(docker_or_podman, container_name)).strip()
                failed_msg_list.append("container: {}, status: {}, start_time: {}".format(
                    container_name, container_status, container_start_time))
        if len(failed_msg_list):
            self._failed_msg += "\n".join(failed_msg_list)
            return False
        return True
