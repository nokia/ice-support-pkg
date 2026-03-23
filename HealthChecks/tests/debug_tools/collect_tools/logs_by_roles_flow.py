from __future__ import absolute_import
from HealthCheckCommon.operations import DataCollector
from HealthCheckCommon.validator import InformatorValidator
from tools.global_enums import Objectives, Deployment_type
from HealthCheckCommon.base_validation_flow import BaseValidationFlow


class CheckLogs(DataCollector):
    objective_hosts = {Deployment_type.CBIS: [Objectives.ALL_HOSTS, Objectives.HYP]}

    def collect_data(self):
        logs_dict = [
            "/var/log/containers/aodh/*",
            "/var/log/containers/httpd/*/*access.log*",
            "/var/log/auditd/*.log*",
            "/var/log/authpriv*",
            "/var/log/auth.log*",
            "/var/log/boot.log*",
            "/var/log/ceilometer/*.log*",
            "/var/log/containers/ceilometer/*.log*",
            "/var/log/ceph/*.log*",
            "/var/log/containers/ceph/*.log*",
            "/var/log/cinder/*.log*",
            "/var/log/containers/cinder/*.log*",
            "/sos_strings/openstack_cinder/*",
            "/var/log/cloud-init.log*",
            "/var/log/cloud-init-output.log*",
            "/var/log/cluster/*.log*",
            "/var/log/containers/cluster/*.log*",
            "/var/log/cron*",
            "/var/log/daemon",
            "/var/log/dmesg",
            "/var/log/glance/*.log*",
            "/var/log/containers/glance/*.log*",
            "/var/log/glusterfs/*.log*",
            "/var/log/containers/glusterfs/*.log*",
            "/var/log/gnocchi/*.log*",
            "/var/log/containers/gnocchi/*.log*",
            "/var/log/heat/*.log*",
            "/var/log/containers/heat/*.log*",
            "/var/log/horizon/*.log*",
            "/var/log/containers/horizon/*.log*",
            "/var/log/keystone/*.log*",
            "/var/log/containers/keystone/*.log*",
            "/var/log/maillog",
            "/var/log/containers/manila/*.log*",
            "/var/log/mariadb/*.log*",
            "/var/log/messages*",
            "/sos_strings/logs/var.log.messages.tailed*",
            "/var/log/containers/mysql/*.log*",
            "/var/log/containers/neutron/*.log*",
            "/var/log/neutron/*.log*",
            "/var/log/nova/*.log*",
            "/var/log/nova/**",
            "/var/log/containers/nova/*.log*",
            "/sos_strings/openstack_nova/*",
            "/var/log/openvswitch/*.log*",
            "/var/log/pacemaker/*/pacemaker.log*",
            "/var/log/pacemaker/bundles/galera-bundle-0/*.log*",
            "/var/log/pacemaker/bundles/rabbitmq-bundle-0/*.log*",
            "/var/log/pcsd/*.log*",
            "/var/log/libvirt/qemu/*.log*",
            "/var/log/rabbitmq/*.log*",
            "/var/log/containers/rabbitmq/*.log*",
            "/var/log/containers/rabbitmq/startup_log*",
            "/var/log/containers/rabbitmq/startup_err*",
            "/var/log/redis/*.log*",
            "/var/log/containers/redis/*.log*",
            "/var/log/secure*",
            "/sos_strings/logs/*secure*.log*",
            "/var/log/spooler",
            "/var/log/swift/*.log*",
            "/var/log/containers/swift/*.log*",
            "/sos_strings/openstack_swift/*.log*",
            "/var/log/tuned/*.log*",
            "/var/log/yum.log*",
            "/var/log/zabbix/*.log*",
            "/var/log/cbis/add_node.log*",
            "/var/log/cbis/remove_node.log*",
            "/var/log/cbis/deployment.log*",
            "/var/log/cbis/*.log*",
            "/var/log/cbis/ansible/*.log",
            "/var/log/cbis/cbis-upgrade/*.log"
        ]
        res = []

        for log_regex in logs_dict:
            return_code, out, err = self.run_cmd("ls {}".format(log_regex))

            if out:
                res.append(log_regex)

        return {"roles": self.get_host_roles(), "log_files": res}


class LogsVal(InformatorValidator):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.UC]
    }

    def set_document(self):
        self._unique_operation_name = 'LogsVal'
        self._title = 'LogsVal'
        self._is_pure_info = True

        self._title_of_info = 'LogsVal'

    def get_system_info(self):
        return self.run_data_collector(CheckLogs)


class LogsByRolesFlow(BaseValidationFlow):

    def _get_list_of_validator_class(self, version, deployment_type):
        check_list_class = [
            LogsVal
        ]

        return check_list_class

    def command_name(self):
        return "logs_by_roles"

    def deployment_type_list(self):
        return [Deployment_type.CBIS]
