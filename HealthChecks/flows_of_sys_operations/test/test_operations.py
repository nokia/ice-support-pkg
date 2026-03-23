from __future__ import absolute_import
from HealthCheckCommon.operations import *

TMP_FILE_PATH = '/tmp/test_operation_sys.txt'
TEST_DIR_ON_UC = "/home/stack/ice/"

data_store = {}

class TestFileCreatAtHost(SystemOperator):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.COMPUTES],
        Deployment_type.NCS_OVER_BM: [Objectives.ALL_NODES],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ALL_NODES]
    }


    def set_document(self):
        self._unique_operation_name = "create_file_at_host"
        self._title = "create tmp file"
        self._failed_msg = "problem in creating file "
        self._run_in_parallel = True
        self._prerequisite_unique_operation_name = ""

    def run_system_operation(self):

        return_code, out, err = self.run_cmd('echo "helo world" >{}'.format(TMP_FILE_PATH))

        if return_code == 0:
            data_store[self.get_host_ip()] = TMP_FILE_PATH

        return (return_code == 0)

class TestCopyFileToUC(SystemOperator):
    #if it is only for cbis/ncs you can you
    #objective_hosts = [Objectives.UC]

    # if it is needs to be computable to both NCS and cbis
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.UC],
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "test_copy_file_to_UC"
        self._title = "copy files to UC"
        self._failed_msg = "problem in copy files"
        self._run_in_parallel = False
        self._prerequisite_unique_operation_name = ""

    def any_pre_requisite_system_operator_passed(self):
        return {"create_file_at_host": Objectives.COMPUTES,
                "create_file_at_host": Objectives.ALL_NODES}

    def run_system_operation(self):

        flg_is_any_ok=False

        for ip in data_store:

            self.save_run_cmd('mkdir -p {}ip{}'.format(TEST_DIR_ON_UC, ip))
            #return_code, out, err = self.run_cmd('mkdir -p {}ip{}'.format(TEST_DIR_ON_UC, ip))

            #if return_code != 0:
            #    self._details = "could not create directory ip{} ".format(ip)
            #    return False

            return_code, out, err = self.run_cmd('scp heat-admin@{}:{} {}ip{}'.format(ip, TMP_FILE_PATH, TEST_DIR_ON_UC, ip))
            if return_code != 0:
                self._details = "filed to copy files from {} ".format(ip)
            else:
                flg_is_any_ok = True
        return flg_is_any_ok


class TestFailedCommand(SystemOperator):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "test_non_exist_cmd"
        self._title = "run non-exist command"
        self._failed_msg = "expected to fail with sys_problem"
        self._run_in_parallel = False
        self._prerequisite_unique_operation_name = ""

    def run_system_operation(self):
        #if you just wont to run command but keep output of case of returning code not 0
        #example of command that fails
        self.save_run_cmd('djdfj')
