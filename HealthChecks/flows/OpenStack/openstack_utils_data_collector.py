from __future__ import absolute_import
from HealthCheckCommon.operations import DataCollector
from tools import sys_parameters
from tools.global_enums import Version, Objectives
from tools.python_utils import PythonUtils


class OpenstackUtilsDataCollector(DataCollector):
    objective_hosts = [Objectives.ONE_CONTROLLER]

    def collect_data(self, **kwargs):
        base_mariadb_cmd = self.get_base_mariadb_cmd()
        timeout = 30
        out = self.get_output_from_run_cmd("{}'{}'".format(base_mariadb_cmd, kwargs['mysql_command']), timeout=timeout)
        custom_delimiter = self.get_table_delimiter(out)

        if custom_delimiter == "\t":
            out = out.replace("\t", "\t ")
        return PythonUtils.get_dict_from_string(out, 'linux_table', custom_delimiter=custom_delimiter)

    def get_base_mariadb_cmd(self):
        mysql_password = self.get_output_from_run_cmd(
            "sudo /bin/hiera -c /etc/puppet/hiera.yaml mysql::server::root_password")
        password = mysql_password.strip()
        if password == 'nil':
            cmd = 'sudo mysql -u root -e '
        else:
            cmd = 'sudo mysql -u root -p{} -e '.format(password)
            if sys_parameters.get_version() >= Version.V22:
                mysql_cmd = cmd.partition(' ')[2]
                cmd = "sudo podman exec -it $(sudo podman ps -f name=galera-bundle -q) {}".format(mysql_cmd)
        return cmd

    def get_table_delimiter(self, out):
        delimiters_list = ['|', '\t']
        for delimiter in delimiters_list:
            if delimiter in out:
                return delimiter
        return None
