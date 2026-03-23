from __future__ import absolute_import
import subprocess
import time
from threading import Timer

from tools.Exceptions import UnExpectedSystemTimeOut, UnExpectedSystemOutput

# flg_no_psutil = None
# try:
#    import psutil
# except ImportError:
#    flg_no_psutil = True # the better way is to kill process with psutil
# in some cases psutil is not avalble in the system or not reachble
# then linuk kill will be use for killing processes that are timed out
flg_no_psutil = True


# *******************************************************************************
# run popen commands functions
# *******************************************************************************

# -----------------------------------------------------------------------------------------------------------------------

class PopenTimeOut(object):
    def __init__(self, cmd, timeout, env=None):
        self.stdout = None
        self.stderr = None
        self.timeout = timeout
        self.exit_code = None
        self.cmd = cmd
        self.env = env
        self.process = subprocess.Popen(cmd, shell=True, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.timer = Timer(self.timeout, self.kill, [])
        self.flg_was_end_by_timeout = False

    def get_children_list(self, process, recursive=False):
        if hasattr(process, "children"):
            return process.children()
        if hasattr(process, "get_children"):
            return process.get_children()
        assert False, 'unexpectes psutil attributes'

    def child_kill(self, child_pross):
        for grandchild in self.get_children_list(process=child_pross, recursive=True):  # kill all the descendants
            grandchild.kill()
        child_pross.kill()

    def kill(self):
        self.flg_was_end_by_timeout = True

        if flg_no_psutil:  # always True since version 303
            if self.process.poll() is None:
                self.process.terminate()  # NOTE! - this terminate only the process itself, if this process has children
                # they will not get kill signal
                # TODO: will be fixed when move to docker

                time.sleep(3)
                if self.process.poll() is None:
                    self.process.kill()

            return True
            # os.killpg(os.getpgid(self.process.pid), signal.SIGINT)
            # os.kill(self.process.pid), signal.SIGINT)

        # depricated ! - take off psutil
        # if self.process.poll() is None:
        # we want to kill all process and thiere descendants
        # but, unfurtuntly, when using therdes, current python process is in the descendants group
        # therefore we go over each of the children and kill them and thier descendants -
        # but not the current python tread

        #    current_process = psutil.Process()  # this current python script
        #    timed_out_prooess = psutil.Process(self.process.pid)  # the process to kill
        #    for child in self.get_children_list(timed_out_prooess):  # or parent.children()
        #        if child.pid != current_process.pid:  # in python threads, the current pid is in the children list
        #            self.child_kill(child)
        #    timed_out_prooess.kill()

        # os.killpg(os.getpgid(self.process.pid), signal.SIGINT)

    def communicate(self):
        self.stdout, self.stderr = self.process.communicate()
        self.exit_code = self.process.wait()

    def execute_command(self):
        try:
            self.timer.start()
            self.communicate()
        except:
            raise UnExpectedSystemOutput(cmd=self.cmd,
                                         ip="local host",
                                         output="",
                                         message="exception while execute_command")
        finally:
            self.timer.cancel()
            if self.flg_was_end_by_timeout:
                raise UnExpectedSystemTimeOut(cmd=self.cmd,
                                              ip="local host",
                                              message="time out while execute_command",
                                              timeout=self.timeout)

            return self.exit_code, self.stdout, self.stderr
