import subprocess
import psutil
import signal
import os
from threading import Timer


class PopenTimeOut(object):
    def __init__(self, cmd, timeout):
        self.stdout = None
        self.stderr = None
        self.timeout = timeout
        self.exit_code = None
        self.cmd = cmd
        self.process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.timer = Timer(self.timeout, self.kill, [])
        self.flg_was_end_by_timeout = False

    def get_children_list(self, process, recursive=False):
        if hasattr(process, "children"):
            return process.children()
        if hasattr(process, "get_children"):
            return process.get_children()
        assert False, 'un-expected psutil attributes'

    def child_kill(self, child_pross):
        for grandchild in self.get_children_list(process=child_pross, recursive=True):  # kill all the desendence
            grandchild.kill()
        child_pross.kill()

    def kill(self):
        self.flg_was_end_by_timeout = True

        if self.process.poll() is None:
            # we want to kill all process and their descendants
            # but, unfortunately, when using threads, current python process is in the descendants group
            # therefore we go over each of the children and kill them and their
            # descendants - but not the current python tread

            current_process = psutil.Process()  # this current python script
            timed_out_prooess = psutil.Process(self.process.pid)  # the procces to kill
            for child in self.get_children_list(timed_out_prooess):  # or parent.children()
                if child.pid != current_process.pid:  # in python threds, the current pid is in the children list
                    self.child_kill(child)
            timed_out_prooess.kill()

    def communicate(self):
        self.stdout, self.stderr = self.process.communicate()
        self.exit_code = self.process.wait()

    def execute_command(self):
        try:
            self.timer.start()
            self.communicate()
        except:
            return 1, "", "timeout expired"
        finally:
            self.timer.cancel()
            if self.flg_was_end_by_timeout:
                return 1, "", "timeout expired"

            return self.exit_code, self.stdout, self.stderr
