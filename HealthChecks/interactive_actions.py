from __future__ import absolute_import
import getpass
from tools import sys_parameters as gs
from tools import global_logging as gl
from tools.popen_utils import PopenTimeOut
from tools.Exceptions import *
import os

from six import moves as six_moves  # python 2 and 3 compelents
from six.moves import range


def ssh_with_password(not_connected_hosts):
    gl.log_and_print('''
    ________________________________________________________
    
    following hosts are not authenticated:
    {}
    You can enter now for each one User name and password:
    ________________________________________________________ 
    '''.format("\n".join(not_connected_hosts)))
    for host_name in not_connected_hosts:
        is_connected = False
        trials_count = 3
        password_message = "Enter {host_name} password :\n".format(
            host_name=host_name)
        gl.logger.info("trying to connect interactively to host {}".format(host_name))
        for trial in range(trials_count):
            gl.logger.info("trial number {}".format(trial + 1))
            user_name = six_moves.input("Enter {} user name: \n<Enter empty string for aborting>\n".format(host_name))
            if user_name == "":
                gl.log_and_print("You've just cancelled the password authentication. Connection Aborted!")
                break
            password = getpass.getpass(password_message)
            is_connected = gs.get_host_executor_factory().reconnect_host_by_password(host_name, user_name,
                                                                                     password=password)
            if is_connected:
                break
            gl.log_and_print("Authentication Failed :(\n")
        if is_connected:
            gl.log_and_print("Host {} is Connected successfully!".format(host_name))
        else:
            gl.log_and_print("Connection to Host {} is aborted!".format(host_name))


# ------------------------------------------------------------------------------------------
# openstack password env set
def _get_os_anv(os_anv_name):
    echo_cmd = "echo ${}".format(os_anv_name)
    my_local_executer = PopenTimeOut(echo_cmd, timeout=3)
    retcode, out, err = my_local_executer.execute_command()
    if retcode != 0:
        raise UnExpectedSystemOutput(ip="local",
                                     cmd=echo_cmd,
                                     output=out + " " + err,
                                     message="problem with openstack env (try running .stackrc)")
    return out.strip()


def set_openstack_password_env():
    gl.log_and_print("openstack password: \n")

    os_project_name = _get_os_anv("OS_PROJECT_NAME")
    os_user_name = _get_os_anv("OS_USERNAME")

    password_message = \
        "Please enter your OpenStack Password for project {} as user {}: ".format(os_project_name, os_user_name)
    password = getpass.getpass(password_message)
    os.environ["OS_PASSWORD"] = password
