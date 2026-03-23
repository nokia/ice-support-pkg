from __future__ import absolute_import
from tools.global_enums import Objectives


class ServicesRequirements:

  def get_services_requirements(self):
    return {
        "haproxy_vitrage": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": False,
            "container_name": None,  # can be null if this service is not containerized
            "service_name": "haproxy_vitrage"
        },
        "haproxy_zabbix": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": False,
            "container_name": None,  # can be null if this service is not containerized
            "service_name": "haproxy_zabbix"
        },
        "zabbix-agent": {
            "roles": [
                Objectives.CONTROLLERS,
                Objectives.COMPUTES,
                Objectives.SRIOV_COMPUTES ,
                Objectives.STORAGE
            ],
            "is_containerized": False,
            "container_name": None,  # can be null if this service is not containerized
            "service_name": "zabbix-agent"
        },
        "cron": {
            "roles": [
                Objectives.CONTROLLERS,
                Objectives.COMPUTES,
                Objectives.SRIOV_COMPUTES,
                Objectives.STORAGE
            ],
            "is_containerized": False,
            "container_name": None,  # can be null if this service is not containerized
            "service_name": "crond"
        },
        "mongod": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": False,
            "container_name": None,  # can be null if this service is not containerized
            "service_name": "mongod"
        },
        "httpd": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": False,
            "container_name": None,  # can be null if this service is not containerized
            "service_name": "httpd"
        },
        "cbis-vitrage-graph": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "cbis-vitrage-graph",  # can be null if this service is not containerized
            "service_name": None
        },
        "openvswitch": {
            "roles": [
                Objectives.COMPUTES,
                Objectives.SRIOV_COMPUTES,
                Objectives.CONTROLLERS,
                Objectives.STORAGE
            ],
            "is_containerized": False,
            "container_name": None,
            "service_name": "openvswitch"
        },
        "rabbitmq-bundle": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "rabbitmq-bundle-docker-0",
            "service_name": None
        },
        "haproxy-bundle": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "haproxy-bundle-docker-0",
            "service_name": None
        },
        "vitrage-api": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "vitrage-api",
            "service_name": None
        },
        "vitrage-notifier": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "vitrage-notifier",
            "service_name": None
        },
        "neutron_ovs_agent": {
            "roles": [
                Objectives.CONTROLLERS,
                Objectives.COMPUTES,
                Objectives.SRIOV_COMPUTES
            ],
            "is_containerized": True,
            "container_name": "neutron_ovs_agent",
            "service_name": "neutron-openvswitch-agent"
        },
        "neutron_l3_agent": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "neutron_l3_agent",
            "service_name": "neutron-l3-agent"
        },
        "neutron_metadata_agent": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "neutron_metadata_agent",
            "service_name": "neutron-metadata-agent"
        },
        "neutron_dhcp": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "neutron_dhcp",
            "service_name": None
        },
        "neutron_api": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "neutron_api",
            "service_name": None
        },
        "neutron_server": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": False,
            "container_name": None,
            "service_name": "neutron-server"
        },
        "neutron-ovs-cleanup": {
            "roles": [
                Objectives.CONTROLLERS,
                Objectives.SRIOV_COMPUTES,
                Objectives.COMPUTES
            ],
            "is_containerized": False,
            "container_name": None,
            "service_name": "neutron-ovs-cleanup"
        },
        "neutron_dhcp_agent": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "neutron-dhcp-agent",
            "service_name": "neutron-dhcp-agent"
        },
        "nova_COMPUTES": {
            "roles": [
                Objectives.COMPUTES,
                Objectives.SRIOV_COMPUTES
            ],
            "is_containerized": True,
            "container_name": "nova_COMPUTES",  # can be null if this service is not containerized
            "service_name": "openstack-nova-COMPUTES"
        },
        "nova_libvirt": {
            "roles": [
                Objectives.COMPUTES,
                Objectives.SRIOV_COMPUTES
            ],
            "is_containerized": True,
            "container_name": "nova_libvirt",  # can be null if this service is not containerized
            "service_name": None
        },
        "nova_virtlogd": {

            "roles": [
                Objectives.COMPUTES,
                Objectives.SRIOV_COMPUTES
            ],
            "is_containerized": True,
            "container_name": "nova_virtlogd",  # can be null if this service is not containerized
            "service_name": None
        },
        "nova_api": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "nova_api",
            "service_name": "openstack-nova-api"
        },
        "nova_vnc_proxy": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "nova_vnc_proxy",
            "service_name": "openstack-nova-novncproxy"
        },
        "nova_consoleauth": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "nova_consoleauth",
            "service_name": "openstack-nova-consoleauth"
        },
        "nova_api_cron": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "nova_api_cron",
            "service_name": None
        },
        "nova_conductor": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "nova_conductor",
            "service_name": "openstack-nova-conductor"
        },
        "nova_scheduler": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "nova_scheduler",
            "service_name": "openstack-nova-scheduler"
        },
        "nova_placement": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "nova_placement",
            "service_name": None
        },
        "heat_api_cron": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "heat_api_cron",
            "service_name": None
        },
        "heat_api_cfn": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "heat_api_cfn",
            "service_name": "openstack-heat-api-cfn"
        },
        "heat_engine": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "heat_engine",
            "service_name": "openstack-heat-engine"
        },
        "heat_api": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "heat_api",
            "service_name": "openstack-heat-api"
        },
        "heat_api_cloudwatch": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": False,
            "container_name": None,
            "service_name": "openstack-heat-api-cloudwatch"
        },
        "cinder_api_cron": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "cinder_api_cron",
            "service_name": None
        },
        "cinder_scheduler": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "cinder_scheduler",
            "service_name": "openstack-cinder-scheduler"
        },
        "cinder_api": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "cinder_api",
            "service_name": "openstack-cinder-api"
        },
        "openstack-cinder-volume": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "openstack-cinder-volume-docker-0",
            "service_name": "openstack-cinder-volume"
        },
        "cbis-nginx-kibana": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "cbis-nginx-kibana",
            "service_name": None
        },
        "elk-logstash": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "elk-logstash",
            "service_name": None
        },
        "elk-kibana": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "elk-kibana",
            "service_name": None
        },
        "elk-elasticsearch": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "elk-elasticsearch",
            "service_name": None
        },
        "barbican_worker": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "barbican_worker",
            "service_name": None
        },
        "barbican_api": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "barbican_api",
            "service_name": None
        },
        "barbican_keystone_listener": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "barbican_keystone_listener",
            "service_name": None
        },
        "keystone_cron": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "keystone_cron",
            "service_name": None
        },
        "keystone": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "keystone",
            "service_name": None
        },
        "cbis-haproxy": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "cbis-haproxy",
            "service_name": "haproxy"
        },
        "openstack-manila-share": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "openstack-manila-share-docker-0",
            "service_name": None
        },
        "manila_api": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "manila_api",
            "service_name": None
        },
        "manila_scheduler": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "manila_scheduler",
            "service_name": None
        },
        "gnocchi_api": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "gnocchi_api",
            "service_name": None
        },
        "gnocchi_metricd": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "gnocchi_metricd",
            "service_name": None
        },
        "gnocchi_statsd": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "gnocchi_statsd",
            "service_name": None
        },
        "glance_api": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "glance_api",
            "service_name": "openstack-glance-api"
        },
        "glance_registry": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": False,
            "container_name": False,
            "service_name": "openstack-glance-registry"
        },
        "panko_api": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "panko_api",
            "service_name": None
        },
        "swift_proxy": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "swift_proxy",
            "service_name": "openstack-swift-proxy"
        },
        "swift_container_auditor": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "swift_container_auditor",
            "service_name": "openstack-swift-container-auditor"
        },
        "swift_container_server": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "swift_container_server",
            "service_name": "openstack-swift-container"
        },
        "swift_container_replicator": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "swift_container_replicator",
            "service_name": "openstack-swift-container-replicator"
        },
        "swift_container_updater": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "swift_container_updater",
            "service_name": "openstack-swift-container-updater"
        },
        "swift_account_auditor": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "swift_account_auditor",
            "service_name": "openstack-swift-account-auditor"
        },
        "swift_account_replicator": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "swift_account_replicator",
            "service_name": "openstack-swift-account-replicator"
        },
        "swift_account_reaper": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "swift_account_reaper",
            "service_name": "openstack-swift-account-reaper"
        },
        "swift_account_server": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "swift_account_server",
            "service_name": "openstack-swift-account"
        },
        "swift_object_replicator": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "swift_object_replicator",
            "service_name": "openstack-swift-object-replicator"
        },
        "swift_object_expirer": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "swift_object_expirer",
            "service_name": "openstack-swift-object-expirer"
        },
        "swift_object_updater": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "swift_object_updater",
            "service_name": "openstack-swift-object-updater"
        },
        "swift_object_auditor": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "swift_object_auditor",
            "service_name": "openstack-swift-object-auditor"
        },
        "swift_object_server": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "swift_object_server",
            "service_name": "openstack-swift-object"
        },
        "swift_rsync": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "swift_rsync",
            "service_name": None
        },
        "aodh_listener": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "aodh_listener",
            "service_name": None
        },
        "aodh_api": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "aodh_api",
            "service_name": None
        },
        "aodh_evaluator": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "aodh_evaluator",
            "service_name": None
        },
        "aodh_notifier": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "aodh_notifier",
            "service_name": None
        },
        "ceilometer_agent_notification": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "ceilometer_agent_notification",
            "service_name": "openstack-ceilometer-notification"
        },
        "ceilometer_agent_central": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "ceilometer_agent_central",
            "service_name": None
        },
        "ceilometer_agent_COMPUTES": {
            "roles": [
                Objectives.COMPUTES,
                Objectives.SRIOV_COMPUTES
            ],
            "is_containerized": True,
            "container_name": "ceilometer_agent_COMPUTES",
            "service_name": None
        },
        "iscsid": {
            "roles": [
                Objectives.CONTROLLERS,
                Objectives.SRIOV_COMPUTES,
                Objectives.COMPUTES,
                Objectives.STORAGE
            ],
            "is_containerized": True,
            "container_name": "iscsid",
            "service_name": None
        },
        "multipathd": {
            "roles": [
                Objectives.CONTROLLERS,
                Objectives.COMPUTES,
                Objectives.SRIOV_COMPUTES,
                Objectives.STORAGE
            ],
            "is_containerized": True,
            "container_name": "multipathd",
            "service_name": None
        },
        "horizon": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "horizon",
            "service_name": None
        },
        "redis-bundle": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "redis-bundle-docker-0",
            "service_name": None
        },
        "clustercheck": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "clustercheck",
            "service_name": None
        },
        "galera-bundle": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "galera-bundle-docker-0",
            "service_name": None
        },
        "memcached": {
            "roles": [
                Objectives.CONTROLLERS
            ],
            "is_containerized": True,
            "container_name": "memcached",
            "service_name": "memcached"
        },
         "iptables-cbis":{
           "roles": [
                Objectives.COMPUTES
            ],
            "is_containerized": False,
            "container_name": None,
            "service_name": "iptables-cbis"
        },
        "libvirtd": {
            "roles": [
                Objectives.COMPUTES
            ],
            "is_containerized": False,
            "container_name": None,
            "service_name": "libvirtd"
        },
        "sshd": {
            "roles": [
                Objectives.CONTROLLERS,
                Objectives.COMPUTES,
                Objectives.SRIOV_COMPUTES,
                Objectives.STORAGE
            ],
            "is_containerized": True,
            "container_name": "memcached",
            "service_name": None
        }
    }


