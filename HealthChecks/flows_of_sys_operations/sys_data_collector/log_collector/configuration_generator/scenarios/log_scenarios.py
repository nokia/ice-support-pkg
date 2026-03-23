from __future__ import absolute_import
from flows_of_sys_operations.sys_data_collector.log_collector.configuration_generator.scenarios.base_log_scenario \
    import CompositeLogGroup
from tools.global_enums import Objectives, Deployment_type
import tools.sys_parameters as gs


class MessagesStorageGroup(CompositeLogGroup):
    def get_logs_of_interest(self):
        if Deployment_type.is_cbis(gs.get_deployment_type()):
            return {Objectives.STORAGE: ["/var/log/messages*"]}
        if Deployment_type.is_ncs(gs.get_deployment_type()):
            return {
                Objectives.MASTERS: ["/var/log/messages*"],
                Objectives.STORAGE: ["/var/log/messages*"]
            }
        return {}


class Messages(CompositeLogGroup):
    def get_sub_groups(self):
        return [MessagesStorageGroup(self._host_executor)]

    def get_logs_of_interest(self):
        return {role: ["/var/log/messages*"] for role in self._get_roles_for_json_keys()}


class Storage(CompositeLogGroup):
    def get_sub_groups(self):
        return [MessagesStorageGroup(self._host_executor), Manila(self._host_executor)]

    def get_logs_of_interest(self):
        if Deployment_type.is_ncs(gs.get_deployment_type()):
            return {
                Objectives.MASTERS: ["/var/log/ceph/*"],
                Objectives.STORAGE: ["/var/log/ceph/*"]
            }
        if Deployment_type.is_cbis(gs.get_deployment_type()):
            return {
                Objectives.STORAGE: ["/var/log/ceph/*.log*",
                                     "/sos_strings/openstack_cinder/*"],
                Objectives.CONTROLLERS: ["/var/log/ceph/*.log*",
                                         "/var/log/containers/ceph/*.log*",
                                         "/var/log/containers/ceph/*.log*",
                                         "/var/log/cinder/*.log*",
                                         "/var/log/containers/cinder/*.log*"],
                Objectives.COMPUTES: ["/var/log/ceph/*.log*",
                                      "/var/log/containers/ceph/*.log*"]
            }
        return {}


class Manila(CompositeLogGroup):
    def get_logs_of_interest(self):
        if Deployment_type.is_cbis(gs.get_deployment_type()):
            return {
                Objectives.CONTROLLERS: ["/var/log/containers/manila/*.log*"]
            }
        return {}


class AnsibleLogs(CompositeLogGroup):
    def get_logs_of_interest(self):
        if Deployment_type.is_ncs(gs.get_deployment_type()):
            return {
                Objectives.MANAGERS: ["/openstack/log/ansible-logging/ansible.log*"]
            }
        if Deployment_type.is_cbis(gs.get_deployment_type()):
            return {role: ["/var/log/cbis/ansible/*.log*"] for role in self._get_roles_for_json_keys()}
        return {}


class Operations(CompositeLogGroup):
    def get_logs_of_interest(self):
        if Deployment_type.is_ncs(gs.get_deployment_type()):
            return {
                Objectives.MANAGERS: ["/var/log/cbis/",  # need to add to central , what is it?
                                      "/opt/management/bcmt/*/log/",
                                      "/opt/bcmt/log/"]
            }
        if Deployment_type.is_cbis(gs.get_deployment_type()):
            return {role: ["/var/log/cbis/"] for role in self._get_roles_for_json_keys()}

        return {}


class Installation(CompositeLogGroup):
    objective_hosts = [Objectives.ONE_MANAGER]

    def get_sub_groups(self):
        return [AnsibleLogs(self._host_executor), Operations(self._host_executor)]

    def get_logs_of_interest(self):
        return {
            Objectives.MANAGERS: ["/var/log/ironic/"]
        }


class Upgrade(CompositeLogGroup):
    objective_hosts = [Objectives.ONE_MANAGER]

    def get_sub_groups(self):
        return [Operations(self._host_executor)]

    def get_logs_of_interest(self):
        return {
            Objectives.MANAGERS: ["/root/cbis/nohup.out*",
                                  "/var/log/cbis/*/ncs_upgrade.log*",  # management is manager?
                                  "/var/log/upgrade-service.log*"]
        }


class Horizon(CompositeLogGroup):
    objective_hosts = [Objectives.UC]

    def get_logs_of_interest(self):
        if Deployment_type.is_cbis(gs.get_deployment_type()):
            return {
                Objectives.CONTROLLERS: ["/var/log/horizon/*.log*",
                                         "/var/log/containers/horizon/*.log*"]
            }
        return {}


class Dmesg(CompositeLogGroup):
    def get_logs_of_interest(self):
        return {role: ["/var/log/dmesg*"] for role in self._get_roles_for_json_keys()}


class Yum(CompositeLogGroup):
    def get_logs_of_interest(self):
        return {role: ["/var/log/yum.log*"] for role in self._get_roles_for_json_keys()}


class Boot(CompositeLogGroup):
    def get_logs_of_interest(self):
        return {role: ["/var/log/boot.log*"] for role in self._get_roles_for_json_keys()}


class General(CompositeLogGroup):
    objective_hosts = [Objectives.UC]

    def get_sub_groups(self):
        return [Horizon(self._host_executor), Messages(self._host_executor), Yum(self._host_executor),
                Dmesg(self._host_executor), Boot(self._host_executor), Mellanox(self._host_executor)]


class AccessAndAuthentication(CompositeLogGroup):
    objective_hosts = [Objectives.UC]

    def get_sub_groups(self):
        return [Audit(self._host_executor), Auth(self._host_executor)]

    def get_logs_of_interest(self):
        res = {
            role: [
                "/var/log/containers/httpd/*/*access.log*",
                "/var/log/authpriv*"
            ]
            for role in self._get_roles_for_json_keys()}

        if Deployment_type.is_cbis(gs.get_deployment_type()):
            res[Objectives.CONTROLLERS].append("/var/log/containers/aodh/*")

        return res


class Auth(CompositeLogGroup):
    def get_logs_of_interest(self):
        return {
            role: ["/var/log/auth.log*"] for role in self._get_roles_for_json_keys()}


class Audit(CompositeLogGroup):
    def get_logs_of_interest(self):
        return {role: ["/var/log/auditd/*.log*"] for role in self._get_roles_for_json_keys()}


class BackupAndRestore(CompositeLogGroup):
    def get_sub_groups(self):
        return [Operations(self._host_executor)]

    def get_logs_of_interest(self):
        return {role: ["/var/log/cron*"] for role in self._get_roles_for_json_keys()}


class NovaCompute(CompositeLogGroup):
    def get_logs_of_interest(self):
        if Deployment_type.is_cbis(gs.get_deployment_type()):
            return {
                Objectives.COMPUTES: ["/var/log/containers/nova/nova-compute*.log*",
                                      "/var/log/nova/nova-compute*.log*"]
            }
        return {}


class NovaConductor(CompositeLogGroup):
    def get_logs_of_interest(self):
        if Deployment_type.is_cbis(gs.get_deployment_type()):
            return {
                Objectives.CONTROLLERS: ["/var/log/containers/nova/nova-conductor*.log*",
                                         "/var/log/nova/nova-conductor*.log*"],
                Objectives.COMPUTES: ["/var/log/containers/nova/nova-conductor*.log*",
                                      "/var/log/nova/nova-conductor*.log*"]
            }
        return {}


class NovaApi(CompositeLogGroup):
    def get_logs_of_interest(self):
        if Deployment_type.is_cbis(gs.get_deployment_type()):
            return {
                Objectives.CONTROLLERS: ["/var/log/containers/nova/nova-api*.log*",
                                         "/var/log/nova/nova-api*.log*"],
                Objectives.COMPUTES: ["/var/log/containers/nova/nova-api*.log*",
                                      "/var/log/nova/nova-api*.log*"]
            }
        return {}


class NovaScheduler(CompositeLogGroup):
    def get_logs_of_interest(self):
        if Deployment_type.is_cbis(gs.get_deployment_type()):
            return {
                Objectives.CONTROLLERS: ["/var/log/containers/nova/nova-api*.log*",
                                         "/var/log/nova/nova-scheduler*.log*"]
            }
        return {}


class IronicConductor(CompositeLogGroup):
    def get_logs_of_interest(self):
        if Deployment_type.is_cbis(gs.get_deployment_type()):
            return {
                Objectives.UC: ["/var/log/containers/ironic/ironic-conductor.log*"]
            }
        return {}


class Ironic(CompositeLogGroup):
    def get_sub_groups(self):
        return [IronicConductor(self._host_executor)]

    def get_logs_of_interest(self):
        if Deployment_type.is_cbis(gs.get_deployment_type()):
            return {
                Objectives.UC: ["/var/log/containers/ironic/ironic-dbsync.log*",
                                "/var/log/containers/ironic-inspector/ironic-inspector.log*",
                                "/var/log/containers/neutron/ironic-neutron-agent.log*"]
            }
        return {}


class CloudInit(CompositeLogGroup):
    def get_logs_of_interest(self):
        if Deployment_type.is_cbis(gs.get_deployment_type()):
            return {
                Objectives.CONTROLLERS: ["/var/log/cloud-init.log*",
                                         "/var/log/cloud-init-output.log*"],
                Objectives.COMPUTES: ["/var/log/cloud-init.log*",
                                      "/var/log/cloud-init-output.log*"],
                Objectives.STORAGE: ["/var/log/cloud-init.log*",
                                     "/var/log/cloud-init-output.log*"]
            }
        return {}


class ScaleIn(CompositeLogGroup):
    objective_hosts = [Objectives.UC]

    def get_sub_groups(self):
        return [AnsibleLogs(self._host_executor), NovaCompute(self._host_executor), NovaConductor(self._host_executor),
                NovaApi(self._host_executor), IronicConductor(self._host_executor), CloudInit(self._host_executor)]


class ScaleOut(CompositeLogGroup):
    objective_hosts = [Objectives.UC]

    def get_sub_groups(self):
        return [NovaCompute(self._host_executor), NovaApi(self._host_executor), NovaConductor(self._host_executor),
                Ironic(self._host_executor), CloudInit(self._host_executor), AnsibleLogs(self._host_executor)]

    def get_logs_of_interest(self):
        if Deployment_type.is_cbis(gs.get_deployment_type()):
            return {
                Objectives.UC: ["/var/lib/mistral/overcloud/ansible.log*"]
            }
        return {}


class Migration(CompositeLogGroup):
    objective_hosts = [Objectives.UC]

    def get_sub_groups(self):
        return [NovaCompute(self._host_executor), NovaConductor(self._host_executor),
                NovaScheduler(self._host_executor)]


class Evacuation(CompositeLogGroup):
    objective_hosts = [Objectives.UC]

    def get_sub_groups(self):
        return [NovaCompute(self._host_executor), NovaConductor(self._host_executor),
                NovaScheduler(self._host_executor)]


class NeutronOnly(CompositeLogGroup):
    def get_logs_of_interest(self):
        if Deployment_type.is_cbis(gs.get_deployment_type()):
            return {
                Objectives.HYP: ["/var/log/containers/neutron/*.log*",
                                 "/var/log/neutron/*.log*"],
                Objectives.COMPUTES: ["/var/log/containers/neutron/*.log*",
                                      "/var/log/neutron/*.log*"],
                Objectives.CONTROLLERS: ["/var/log/containers/neutron/*.log*",
                                         "/var/log/neutron/*.log*"]
            }
        return {}


class Neutron(CompositeLogGroup):
    objective_hosts = [Objectives.UC]

    def get_sub_groups(self):
        return [NeutronOnly(self._host_executor)]

    def get_logs_of_interest(self):
        if Deployment_type.is_cbis(gs.get_deployment_type()):
            return {
                Objectives.HYP: ["/var/log/containers/mysql/*.log*"],
                Objectives.CONTROLLERS: ["/var/log/containers/mysql/*.log*"]
            }
        return {}


class Glance(CompositeLogGroup):
    def get_logs_of_interest(self):
        if Deployment_type.is_cbis(gs.get_deployment_type()):
            return {
                Objectives.HYP: ["/var/log/containers/glance/*.log*",
                                 "/var/log/glance/*.log*"],
                Objectives.CONTROLLERS: ["/var/log/containers/glance/*.log*",
                                         "/var/log/glance/*.log*"]
            }
        return {}


class VmNotLoading(CompositeLogGroup):
    objective_hosts = [Objectives.UC]

    def get_sub_groups(self):
        return [NovaCompute(self._host_executor), NovaScheduler(self._host_executor), Messages(self._host_executor),
                NeutronOnly(self._host_executor), Glance(self._host_executor)]

    def get_logs_of_interest(self):
        if Deployment_type.is_cbis(gs.get_deployment_type()):
            return {
                Objectives.HYP: ["/var/log/libvirt/qemu/*.log*"]
            }
        return {}


class Gluster(CompositeLogGroup):
    objective_hosts = [Objectives.UC]

    def get_logs_of_interest(self):
        if Deployment_type.is_cbis(gs.get_deployment_type()):
            return {
                Objectives.COMPUTES: ["/var/log/glusterfs/*.log*",
                                      "/var/log/containers/glusterfs/*.log*"],
                Objectives.CONTROLLERS: ["/var/log/containers/gnocchi/*.log*",
                                         "/var/log/gnocchi/*.log*"]
            }
        return {}


class Zabbix(CompositeLogGroup):
    objective_hosts = [Objectives.UC]

    def get_sub_groups(self):
        return [Messages(self._host_executor)]

    def get_logs_of_interest(self):
        if Deployment_type.is_cbis(gs.get_deployment_type()):
            return {
                Objectives.CONTROLLERS: ["/var/log/zabbix/*.log*"],
                Objectives.COMPUTES: ["/var/log/zabbix/*.log*"],
                Objectives.HYP: ["/var/log/zabbix/*.log*"],
                Objectives.STORAGE: ["/var/log/zabbix/*.log*"]
            }
        return {}


class NodesFailures(CompositeLogGroup):
    objective_hosts = [Objectives.UC]

    def get_sub_groups(self):
        return [Zabbix(self._host_executor), Dmesg(self._host_executor), Boot(self._host_executor),
                Manila(self._host_executor)]

    def get_logs_of_interest(self):
        if Deployment_type.is_cbis(gs.get_deployment_type()):
            return {
                Objectives.CONTROLLERS: ["/var/log/pcsd/*.log*"]
            }
        return {}


class KernelAndHw(CompositeLogGroup):
    def get_sub_groups(self):
        return [Messages(self._host_executor), Dmesg(self._host_executor), Audit(self._host_executor)]


class Hardening(CompositeLogGroup):
    objective_hosts = [Objectives.UC]

    def get_sub_groups(self):
        return [AnsibleLogs(self._host_executor)]


class Nova(CompositeLogGroup):
    objective_hosts = [Objectives.UC]

    def get_sub_groups(self):
        return [NovaCompute(self._host_executor), NovaConductor(self._host_executor),
                NovaScheduler(self._host_executor), NovaApi(self._host_executor)]


class Mellanox(CompositeLogGroup):

    def get_sub_groups(self):
        return [OpenVswitch(self._host_executor)]

    def get_logs_of_interest(self):
        if Deployment_type.is_cbis(gs.get_deployment_type()):
            return {
                Objectives.CONTROLLERS: ["/var/log/containers/ceilometer/*.log*",
                                         "/var/log/ceilometer/*.log*"]
            }

        return {}


class Networking(CompositeLogGroup):
    objective_hosts = [Objectives.UC]

    def get_sub_groups(self):
        return [Mellanox(self._host_executor), Neutron(self._host_executor)]


class OpenVswitch(CompositeLogGroup):
    def get_logs_of_interest(self):
        if Deployment_type.is_cbis(gs.get_deployment_type()):
            return {
                Objectives.HYP: ["/var/log/openvswitch/*.log*"],
                Objectives.UC: ["/var/log/openvswitch/*.log*"]
            }

        return {}


class RabbitMq(CompositeLogGroup):
    objective_hosts = [Objectives.UC]

    def get_sub_groups(self):
        return [OpenVswitch(self._host_executor)]

    def get_logs_of_interest(self):
        if Deployment_type.is_cbis(gs.get_deployment_type()):
            return {
                Objectives.CONTROLLERS: ["/var/log/rabbitmq/*.log*",
                                         "/var/log/containers/rabbitmq/startup_log*",
                                         "/var/log/containers/rabbitmq/startup_err*",
                                         "/var/log/pacemaker/bundles/galera-bundle-0/*.log*",
                                         "/var/log/pacemaker/bundles/rabbitmq-bundle-0/*.log*"]
            }

        return {}


class Redis(CompositeLogGroup):
    objective_hosts = [Objectives.UC]

    def get_logs_of_interest(self):
        if Deployment_type.is_cbis(gs.get_deployment_type()):
            return {
                Objectives.CONTROLLERS: ["/var/log/containers/redis/*.log*",
                                         "/var/log/redis/*.log*"],
                Objectives.UC: ["/var/log/containers/redis/*.log*",
                                "/var/log/redis/*.log*"]
            }

        return {}


class Swift(CompositeLogGroup):
    objective_hosts = [Objectives.UC]

    def get_logs_of_interest(self):
        if Deployment_type.is_cbis(gs.get_deployment_type()):
            return {
                Objectives.CONTROLLERS: ["/var/log/swift/*.log*",
                                         "/var/log/containers/swift/*.log*"],
                Objectives.HYP: ["/var/log/swift/*.log*",
                                 "/var/log/containers/swift/*.log*"]

            }

        return {}


class Security(CompositeLogGroup):
    objective_hosts = [Objectives.UC]

    def get_sub_groups(self):
        return [AnsibleLogs(self._host_executor), Auth(self._host_executor)]

    def get_logs_of_interest(self):
        if Deployment_type.is_cbis(gs.get_deployment_type()):
            return {
                Objectives.CONTROLLERS: ["/var/log/secure*",
                                         "/var/log/containers/keystone/*.log*",
                                         "/var/log/keystone/*.log*"],
                Objectives.COMPUTES: ["/var/log/secure*"],
                Objectives.UC: ["/var/log/secure*"],
                Objectives.HYP: ["/var/log/secure*",
                                 "/var/log/containers/keystone/*.log*",
                                 "/var/log/keystone/*.log*"],
                Objectives.STORAGE: ["/var/log/secure*"]

            }

        return {}
