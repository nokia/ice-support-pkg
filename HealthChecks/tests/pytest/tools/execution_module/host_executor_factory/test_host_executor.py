from __future__ import absolute_import
import platform

import pytest

from tests.pytest.tools.versions_alignment import patch
from tools.Exceptions import UnExpectedSystemTimeOut
from tools.ExecutionModule.HostExecutorsFactory.HostExecutor import HostExecutor


class TestHostExecutor(object):
    @pytest.fixture
    def local_host_executor(self):
        return HostExecutor("localhost",
                            "localhost",
                            "",
                            is_local=True)

    @pytest.fixture
    @patch("tools.ExecutionModule.HostExecutorsFactory.HostExecutor.gl")
    def ssh_host_executor(self, logger_mock):
        host_executor = HostExecutor("localhost",
                                     "localhost",
                                     "root",
                                     password="Mc10vin!!",
                                     is_local=False)
        host_executor.connect_ssh_client()
        host_executor.is_log_initialized = False

        return host_executor

    @pytest.mark.skip_in_jenkins
    def test_execute_cmd_timeout_local(self, local_host_executor):
        if platform.system() != 'Linux':
            pytest.skip("Test only runs on Linux")

        cmd = "sleep 5"

        with pytest.raises(UnExpectedSystemTimeOut):
            local_host_executor.execute_cmd(cmd, timeout=1)

    @pytest.mark.skip_in_jenkins
    def test_execute_cmd_timeout_ssh(self, ssh_host_executor):
        if platform.system() != 'Linux':
            pytest.skip("Test only runs on Linux")

        cmd = "sleep 5"

        with pytest.raises(UnExpectedSystemTimeOut):
            ssh_host_executor.execute_cmd(cmd, timeout=1)
