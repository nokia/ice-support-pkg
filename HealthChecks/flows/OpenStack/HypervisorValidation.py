from __future__ import absolute_import
from HealthCheckCommon.operations import *
import tools.sys_parameters as gs
from HealthCheckCommon.validator import Validator


class HypervisorFreeDiskSpaceCheck(Validator):

    objective_hosts = [Objectives.HYP]

    def set_document(self):

        self._unique_operation_name = "check_free_space_in_hypervisor_sufficient_for_operations"
        self._title = "Verify if hypervisor has enough free space to perform operations"
        self._failed_msg = "Free Space in hypervisor is low, Scale operations will be failed"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        backup_dir = gs.get_base_conf()['CBIS']['openstack_deployment'].get('backup_nfs_mountpoint')
        self._validation_log.append("backup directory is {}".format(backup_dir))
        space_avail = self.get_free_space(backup_dir)
        self._validation_log.append("space_avail={}".format(space_avail))
        size_of_xml = self.get_size_by_path("/root/undercloud.xml")
        size_of_qcow = self.get_size_by_path("/var/lib/libvirt/images/undercloud.qcow2")
        size_of_ssh = self.get_size_by_path("/root/.ssh")
        total_size_bk = float(size_of_ssh + size_of_qcow + size_of_xml)
        self._validation_log.append("total_size_bk={} = size_of_xml={} + size_of_qcow={} + size_of_ssh={} ".format(total_size_bk, size_of_xml,size_of_qcow, size_of_ssh))
        self._validation_log.append("space_avail={}".format(space_avail))
        if total_size_bk >= space_avail:
            self._validation_log.append("Available Disk space {}KB is lower than Total Backup size: {}KB".format(space_avail,total_size_bk))
            self._failed_msg += '\nAvailable Disk space {}KB is lower than Total Backup size: {}KB\n'.format(space_avail, total_size_bk)
            return False
        self._validation_log.append("Available Disk space {}KB is higher than Total Backup size: {}KB as expected".format(space_avail,total_size_bk))
        return True

    def get_size_by_path(self, path):
        if self.file_utils.is_file_exist(path):
            find_usage_cmd = "sudo du -s " + path
            find_usage = self.run_and_get_the_nth_field(find_usage_cmd, 1, add_bash_timeout=True)
            return float(find_usage)

        return 0

    def get_free_space(self, path):
        if not self.file_utils.is_dir_exist(path):
            raise UnExpectedSystemOutput(self.get_host_ip(), "", path, "The backup directory path doesn't exist.")
        find_freespace_cmd = "sudo df " + path + "| tail -n1"
        find_freespace = self.run_and_get_the_nth_field(find_freespace_cmd, 4)
        return float(find_freespace)
