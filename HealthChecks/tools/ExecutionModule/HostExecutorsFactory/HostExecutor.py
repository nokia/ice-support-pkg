from __future__ import absolute_import
import inspect
import json
import time

import paramiko
import select
from paramiko.ssh_exception import SSHException

from tools import python_versioning_alignment
from tools.Exceptions import HostNotReachable, UnExpectedSystemTimeOut
import atexit
from tools.popen_utils import PopenTimeOut
import tools.global_logging as gl
import re
import os
import sys
import threading
import socket
from six.moves import range


class HostExecutor(object):
    running_timeout_exceeded = False
    top_10_large_streams = {"out": {}, "err": {}}

    def __init__(self, ip, host_name, user_name, roles=None, is_local=False, key_file=None, password=None,
                 pkey_string=None, is_log_initialized=True):
        self.user_name = user_name
        self.host_name = host_name
        self.ip = ip
        self.roles = []
        self.add_roles(roles)
        self.is_local = is_local
        self.is_log_initialized = is_log_initialized
        self._threadLock = threading.Lock()
        if not is_local:
            self.is_connected = None
            self.during_connection = None
            self._connection_error_details = None
            self._client = None
            self._password = password
            self._key_file = key_file
            self._pkey = HostExecutor.get_pkey_from_string(pkey_string) if pkey_string else None
        else:
            self.is_connected = True
            self.during_connection = False

    @staticmethod
    def get_pkey_from_string(pkey_string):
        return paramiko.RSAKey.from_private_key(python_versioning_alignment.StringIO(pkey_string))

    #  unused function
    def _check_is_reachable(self):
        if self.is_local:
            return True
        else:
            ping_cmd = "ping {} -c 1 -W 1 | grep packets".format(self.ip)
            p = PopenTimeOut(ping_cmd, 5)
            exit_code, out, err = p.execute_command()
            if out and "Network is unreachable" in out or "Name or service not known" in err:
                return False
            result = re.sub(r".*transmitted,\s*|\s*received,.*", "", out)
            return True if '1' in result else False

    def add_role(self, role):
        if role not in self.roles:
            self.roles.append(role)

    def add_roles(self, roles):
        if roles:
            for role in roles:
                self.add_role(role)

    def reconnect_by_password(self, user_name, password):
        self.user_name = user_name
        self._password = password
        self._key_file = None
        self._pkey = None
        self.connect_ssh_client()
        return self.is_connected

    def connect_ssh_client(self):
        if self.is_local or (self.is_connected and not self.during_connection):
            return

        if self.is_log_initialized:
            gl.logger.info("opening connection to host {} - {} ...".format(self.ip, self.host_name))
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            self._client.connect(hostname=self.ip,
                                 username=self.user_name,
                                 key_filename=self._key_file,
                                 password=self._password,
                                 timeout=60,
                                 pkey=self._pkey)
            self.is_connected = True
            self.during_connection = False
            if self.is_log_initialized:
                gl.logger.info("connection to {} was successfully established!".format(self.host_name))

            atexit.register(self.close_connection)

            if HostExecutor.running_timeout_exceeded:
                self.close_connection()
                self.is_connected = False

        except Exception as e:
            self.handle_connect_exception(e)

    def handle_connect_exception(self, e):
        error_str = str(e)
        self._client.close()
        self.is_connected = False
        self.during_connection = False
        self._connection_error_details = error_str
        if self.is_log_initialized:
            gl.logger.info("Cannot connect to server {}-{}\n{}".format(self.ip, self.host_name, error_str))

    def reconnect_ssh_client(self):
        self.during_connection = True
        self.connect_ssh_client()

    def clean_TTY(self, err_line):
        new_err_line = err_line.replace("Unable to use a TTY - input is not a terminal or the right kind of file","")
        return new_err_line

    def modify_top_10_large_streams(self, out, err, caller_class):
        LARGE_STREAMS_LIMIT = 10
        cmd_stream_dict = {"out": out, "err": err}
        for stream in list(HostExecutor.top_10_large_streams.keys()):
            len_cmd_stream = len(cmd_stream_dict[stream])
            if len_cmd_stream == 0:
                continue
            elif not len(HostExecutor.top_10_large_streams[stream]) or \
                    (len(list(HostExecutor.top_10_large_streams[stream].keys())) < LARGE_STREAMS_LIMIT and
                     len_cmd_stream not in list(HostExecutor.top_10_large_streams[stream].keys())):
                HostExecutor.top_10_large_streams[stream][len_cmd_stream] = {self.host_name: [caller_class]}
            elif len_cmd_stream in list(HostExecutor.top_10_large_streams[stream].keys()):
                HostExecutor.top_10_large_streams[stream][len_cmd_stream].setdefault(self.host_name, [])
                if caller_class not in HostExecutor.top_10_large_streams[stream][len_cmd_stream][self.host_name]:
                    HostExecutor.top_10_large_streams[stream][len_cmd_stream][self.host_name].append(caller_class)
            elif len_cmd_stream > min(HostExecutor.top_10_large_streams[stream].keys()):
                del HostExecutor.top_10_large_streams[stream][min(HostExecutor.top_10_large_streams[stream].keys())]
                HostExecutor.top_10_large_streams[stream][len_cmd_stream] = {self.host_name: [caller_class]}

    def execute_cmd(self, cmd, timeout=120, max_iter_recv_ready=5, get_not_ascii=False):
        caller_class = inspect.stack()[1][0].f_locals["self"].__class__.__name__
        if self.is_local:
            # ICET-588: /usr/sbin missing from path when executed from CBIS Manager
            # CBIS Manager executes HealthChecks via SSH, PATH does not include /usr/sbin
            # User executes HealthCheck from an interactive login shell, PATH includes /usr/sbin
            # Remove /usr/sbin and variants from path to ensure consistent behavior
            env = os.environ.copy()

            path = [x for x in env['PATH'].split(':') if x not in ['/sbin', '/usr/sbin', '/usr/local/sbin']]
            env['PATH'] = ':'.join(path)
            exit_code, out, err = self._run_cmd_on_local(cmd, env, timeout, get_not_ascii)
            self.modify_top_10_large_streams(out, err, caller_class)
            return exit_code, out, err
        else:
            with self._threadLock:
                if self.is_connected and not self._client.get_transport().active:
                    self.reconnect_ssh_client()

                if self.is_connected is False:
                    raise HostNotReachable(self.ip, 'cannot connect to remote server',
                                           details=self._connection_error_details)
                out, err, exit_code = self._run_cmd_read_out(cmd, timeout)
        self.modify_top_10_large_streams(out, err, caller_class)

        exit_code, out, err = self._process_out(exit_code, out, err, get_not_ascii)
        err = self.clean_TTY(err)

        return exit_code, out, err

    def _run_cmd_read_out(self, cmd, timeout):
        stdin = stdout = stderr = None

        try:
            stdin, stdout, stderr = self._run_cmd_with_retry(cmd, timeout)

            out, err, exit_code = self._read_out_err_exit_code(stderr, stdout, timeout)

        except socket.timeout:
            raise UnExpectedSystemTimeOut(cmd=cmd,
                                          ip=self.ip,
                                          timeout=timeout)
        finally:
            self._clean_open_channels(stderr, stdin, stdout)

        return out, err, exit_code

    def _read_out_err_exit_code(self, stderr, stdout, timeout):
        out = b""
        err = b""
        start_time = time.time()
        out_finish = False
        err_finish = False

        while not out_finish or not err_finish:
            if time.time() - start_time > timeout:
                raise socket.timeout()

            # select.select select 1 of buffers that is ready, with timeout of 1,
            # if timeout exceeded it'll return an empty list.
            rlist, _, _ = select.select([stdout.channel, stderr.channel], [], [], 1)

            if stdout.channel in rlist:
                out_data = stdout.channel.recv(1024)
                out += out_data

                if not out_data:
                    out_finish = True

            if stderr.channel in rlist:
                err_data = stderr.channel.recv_stderr(1024)
                err += err_data

                if not err_data:
                    err_finish = True

        exit_code = stdout.channel.recv_exit_status()

        return out, err, exit_code

    def _clean_open_channels(self, stderr, stdin, stdout):
        if stdout:
            stdout.channel.shutdown_read()
            stdout.channel.close()

        if stderr:
            stderr.channel.shutdown_read()
            stderr.channel.close()

        if stdin:
            stdin.close()

    def _run_cmd_on_local(self, cmd, env, timeout, get_not_ascii):
        p = PopenTimeOut(cmd, timeout, env=env)
        exit_code, out, err = p.execute_command()

        return self._process_out(exit_code, out, err, get_not_ascii)

    def _process_out(self, exit_code, out, err, get_not_ascii):
        if get_not_ascii:
            non_ascii_behaviour = 'replace'
        else:
            non_ascii_behaviour = 'ignore'

        out = self._process_str(out, non_ascii_behaviour)
        err = self._process_str(err, non_ascii_behaviour)

        return exit_code, out, err

    def _process_str(self, s, non_ascii_behaviour):
        if type(s) is not python_versioning_alignment.get_unicode_type():
            return s.decode('ascii', non_ascii_behaviour)

        return s.encode('ascii', non_ascii_behaviour)

    #TODO - use this function in case not all outgoing/errors arrive
    # def run_cmd_over_all_buffer(self, cmd, timeout):
    #     stdin, stdout, stderr = self._run_cmd_with_retry(cmd, timeout)
    #     nbytes = 10240
    #     stdout_chunks = []
    #     stderr_chunks = []
    #     stdout_chunks.append(stdout.channel.recv(nbytes))
    #     stderr_chunks.append(stderr.channel.recv_stderr(nbytes))
    #     while not stdout.channel.closed or stdout.channel.recv_ready() or stdout.channel.recv_stderr_ready():
    #         got_chunk = False
    #         import select
    #         readq, _, _ = select.select([stdout.channel], [], [], timeout)
    #         for c in readq:
    #             if c.recv_ready():
    #                 stdout_chunks.append(stdout.channel.recv(nbytes))
    #                 got_chunk = True
    #             if c.recv_stderr_ready():
    #                 stderr_chunks.append(stderr.channel.recv_stderr(nbytes))
    #                 got_chunk = True
    #         if not got_chunk \
    #                 and stdout.channel.exit_status_ready() \
    #                 and not stderr.channel.recv_stderr_ready() \
    #                 and not stdout.channel.recv_ready():
    #             break
    #     exit_code = stdout.channel.recv_exit_status()
    #     out = "".join(stdout_chunks)
    #     err = "".join(stderr_chunks)
    #     return exit_code, out, err

    def _run_cmd_with_retry(self, cmd, timeout):
        max_retries = 3
        retry_delay = 1

        for retry_count in range(max_retries):
            try:
                return self._client.exec_command(cmd, timeout=timeout)

            except SSHException:
                if retry_count == max_retries - 1:
                    raise

                # Wait before retrying
                time.sleep(retry_delay)
                self.reconnect_ssh_client()
                if not self.is_connected:
                    raise HostNotReachable(ip=self.ip, details=self._connection_error_details)


    def close_connection(self):
        if not self.is_local:
            self._client.close()
            if self.is_log_initialized:
                gl.logger.info("closing connection to host {} - {}".format(self.ip, self.host_name))

