from __future__ import absolute_import
from HealthCheckCommon.operations import *
from HealthCheckCommon.validator import Validator


class CheckMariadbConnectTimeout(Validator):

    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "check-mariadb-connect-timeout-for-large-setup"
        self._title = "Verify if mariadb connect_timeout is valid for large setup"
        self._failed_msg = "Mariadb connect_timeout is not valid for large setup. Please increase it to 60"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        cmd1 = "sudo mysql --execute=\"SHOW VARIABLES LIKE \'%connect_timeout%\';\" | grep connect_timeout"
        out1 = self.get_output_from_run_cmd(cmd1).strip()
        # cmd2 = "docker exec -it mysql mysql --execute=\"SHOW VARIABLES LIKE \'%connect_timeout%\';\" |grep connect_timeout"
        out1 = out1.split()
        if int(out1[-1]) < 60:
            return False        
        self._details = "Mariadb connect_timeout is good for large setup"
        return True

class CheckKeystoneRequest(Validator):

    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "check-keystone-request-for-large-setup"
        self._title = "Verify if keystone request handler is valid for large setup"
        self._failed_msg = "Keystone request handler is not valid for large setup. Please increase it."
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        cmd1 = "cat /etc/httpd/conf.d/10-keystone_wsgi_admin.conf | grep processes"
        out1 = self.get_output_from_run_cmd(cmd1).strip()
        # cmd2 = "cat /var/lib/config-data/puppet-generated/keystone/etc/httpd/conf.d/10-keystone_wsgi_admin.conf | grep processes"
        out1 = out1.split()
        proc_value = out1[-3].split("=")[-1]
        thread_value = out1[-2].split("=")[-1]
        if int(proc_value)*int(thread_value) < 50:
            return False        
        self._details = "Keystone request handler is good for large setup."
        return True