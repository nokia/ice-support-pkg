from __future__ import absolute_import
import tools.sys_parameters as gs
from tools.global_enums import Objectives, Deployment_type, Version
from tools.lazy_global_data_loader import *
from tools.Exceptions import UnExpectedSystemOutput
from tools.python_utils import PythonUtils
import json

class CephPaths:
    CINDER_CONF_18 = "/etc/cinder/cinder.conf"
    CINDER_CONF = "/var/lib/config-data/puppet-generated/cinder/etc/cinder/cinder.conf"
    NOVA_CONF_18 = "/etc/nova/nova.conf"
    NOVA_CONF = "/var/lib/config-data/puppet-generated/nova_libvirt/etc/nova/nova.conf"
    NOVA_SECRET_18 = "/etc/nova/secret.xml"
    NOVA_SECRET_MULTIPLE_POOL = "/etc/nova/secret_{}.xml"
    NOVA_SECRET = "/var/lib/config-data/puppet-generated/nova_libvirt/etc/nova/secret.xml"
    PUPPET_CONF_18 = "/etc/puppet/hieradata/service_configs.yaml"
    PUPPET_CONF = "/etc/puppet/hieradata/service_configs.json"
    CEPH_CONF = "/etc/ceph/ceph.conf"
    KEYRING_PATH_TEMPLATE = "/etc/ceph/ceph.client.{}.keyring"
    STORAGE_TEMPLATE_CONF = "/home/stack/templates/storage-environment.yaml"
    UUID_POOL_JSON = "/usr/share/cbis/uuid_pool.json"
    HOST_CONF = "/usr/share/cbis/data/hosts_config.yaml"



class CephInfo:

    @staticmethod
    def _get_my_children_from_ceph_crush_map(ceph_objects_dict, current_root):
        # print '**current_root[name]',current_root['name']
        root_hosts_dict_to_return = []

        if current_root.get('children') is None:
            raise UnExpectedSystemOutput('controller', '',
                                         'unexpected osd output. expecting this root to have children: ceph_objects_dict is{} current_root is {} '.format(
                                             ceph_objects_dict, current_root))

        list_of_children_ids = current_root['children']
        children_dict = PythonUtils.filter_dict_by_values(ceph_objects_dict, 'id', list_of_children_ids)

        # check if the childrens are hosts - if not (pools or rack) - get there children
        for child in children_dict:
            # print '***child[name]' , child['name']
            # print '***child[type]' , child['type']

            if child['type'] == "osd":
                raise UnExpectedSystemOutput('controller', '',
                                             'unexpected osd output. not expecting osd type here: ceph_objects_dict is{} \n current_root is {}\n '.format(
                                                 ceph_objects_dict, current_root))

            if child['type'] == "host":
                root_hosts_dict_to_return.append(child)
            else:
                grandchildren = CephInfo._get_my_children_from_ceph_crush_map(ceph_objects_dict, child)
                root_hosts_dict_to_return.extend(grandchildren)
        return root_hosts_dict_to_return


    @staticmethod
    def get_root_hosts_dict(ceph_objects_dict):
        '''return dictinary of all the rootes and there hosts (host full name)
        sometimes there is rack and/or zoon in the hierchy - we flattening rack and zoons as it is not of our interest
        example of hierchys can be found at ICET-836
        '''

        root_hosts_dict = {}
        roots_list = PythonUtils.filter_dict_by_values(ceph_objects_dict, 'type', ['root'])
        for root in roots_list:
            root_name=root['name']
            root_hosts_dict[root_name] = CephInfo._get_my_children_from_ceph_crush_map(ceph_objects_dict,root)
        return root_hosts_dict

    @staticmethod
    def get_host_osds_dict(root_name, host_osds):
        host_osds_dict = {}
        for osd in host_osds:
            osd_name = str(osd["id"])
            host_osds_dict[osd_name] = {
                "status": osd["status"],
                "root": root_name,
                "weight": float(osd["crush_weight"]),
                "dev_class": osd.get("device_class")
            }
        return host_osds_dict

    @staticmethod
    def map_cbis_host_name_to_ceph_name(ceph_host_names, osd_tree):
        storage_host_name_list = list(gs.get_host_executor_factory().get_host_executors_by_roles(
            roles=[Objectives.STORAGE]).keys())
        ceph_host_2_cbis_host={}

        for ceph_host_name in ceph_host_names:
            ceph_host_name=ceph_host_name['name'].lower()
            flg_found=False
            for our_host in storage_host_name_list:
                our_host=our_host.lower()
                if  our_host==ceph_host_name:
                    ceph_host_2_cbis_host[ceph_host_name] = our_host
                    flg_found=True

            if flg_found:
                continue
            #else
            # check if ends with the host name
            #sometimes the host names at ceph ends with common-|^fast- and etc.
            for our_host in storage_host_name_list:
                our_host = our_host.lower()
                if ceph_host_name.endswith(our_host.lower()):
                    ceph_host_2_cbis_host[ceph_host_name] = our_host
                    flg_found = True
            if not flg_found:

                return {
                    'is_passed': False,
                    'failed_msg': 'Mismatch between ceph hostnames: {} and storage hostnames: {}\nWe could not find '
                                  'cbis host name that is analog to ceph host name {}.\nCeph osd tree is {}'.format(
                                    [name['name'].lower() for name in ceph_host_names],
                                    [name.lower() for name in storage_host_name_list], ceph_host_name, osd_tree)}
        return ceph_host_2_cbis_host

    @staticmethod
    def get_relevant_roles():
        roles = [Objectives.ONE_CONTROLLER, Objectives.ONE_MASTER]
        if gs.is_ncs_central() and gs.is_central_cluster():
            roles = [Objectives.ONE_MANAGER]
        return roles

    @staticmethod
    @lazy_global_data_loader
    def _set_and_get_ceph_osd_dict():
        cmd = "sudo ceph osd tree -f json"
        out = gs.get_host_executor_factory().run_command_on_first_host_from_selected_roles(cmd, roles=CephInfo.get_relevant_roles())
        ceph_objects_dict = json.loads(out)['nodes']

        hosts_osds_dict = {}
        storage_host_name_list = list(gs.get_host_executor_factory().get_host_executors_by_roles(roles=[Objectives.STORAGE]).keys())
        for host in storage_host_name_list:
            hosts_osds_dict[host.lower()] = {}
        root_hosts_dict = CephInfo.get_root_hosts_dict(ceph_objects_dict)
        for root_name in root_hosts_dict:
            ceph_host_2_cbis_host_map = CephInfo.map_cbis_host_name_to_ceph_name(
                                                                            ceph_host_names=root_hosts_dict[root_name],
                                                                            osd_tree=out)
            if not ceph_host_2_cbis_host_map.get('is_passed', True):
                return ceph_host_2_cbis_host_map
            for host_dict in root_hosts_dict[root_name]:

                host_osds = PythonUtils.filter_dict_by_values(ceph_objects_dict, 'id', host_dict['children'])
                host_dict_name=host_dict['name'].lower()

                assert ceph_host_2_cbis_host_map.get(host_dict_name) #the use case of not finding analog host is coverd in map_cbis_host_name_to_ceph_name
                host_name = ceph_host_2_cbis_host_map[host_dict_name]
                hosts_osds_dict[host_name].update(CephInfo.get_host_osds_dict(root_name, host_osds))

        return hosts_osds_dict

    @staticmethod
    @lazy_global_data_loader
    def _set_and_get_ceph_osd_conf():
        osd_conf_dict = {}
        if gs.get_version() < Version.V24_11:
            cmd = 'sudo cat {}'.format(CephPaths.CEPH_CONF)
        else:
            cmd = 'sudo ceph config dump -f json'
        result = gs.get_host_executor_factory().execute_cmd_by_roles([Objectives.STORAGE], cmd, 10)
        for host_name_from_result in result:
            host_name = host_name_from_result.lower()
            osd_conf_dict[host_name] = {
                'osds': {},
                'conf': {}
            }
            out = result[host_name_from_result].get("out")
            if out:
                if gs.get_version() < Version.V24_11:
                    ceph_conf = PythonUtils.get_dict_from_string(out, 'ini')
                    for section_name in ceph_conf:
                        if section_name.startswith('osd.'):
                            osd_name = section_name.replace('osd.', '')
                            osd_conf_dict[host_name]['osds'][osd_name] = ceph_conf[section_name]
                        else:
                            osd_conf_dict[host_name]['conf'][section_name] = ceph_conf[section_name]
                else:
                    ceph_conf = PythonUtils.get_dict_from_string(out, 'json')
                    for option in ceph_conf:
                        if option['section'].startswith('osd.'):
                            osd_name = option['section'].replace('osd.', '')
                            if osd_name not in osd_conf_dict[host_name]['osds']:
                                osd_conf_dict[host_name]['osds'][osd_name] = {}
                            osd_conf_dict[host_name]['osds'][osd_name][option['name']] = option['value']
                        else:
                            if option['section'] not in osd_conf_dict[host_name]['conf']:
                                osd_conf_dict[host_name]['conf'][option['section']] = {}
                            osd_conf_dict[host_name]['conf'][option['section']][option['name']] = option['value']
        return osd_conf_dict

    @staticmethod
    @lazy_global_data_loader
    def _set_and_get_ceph_fsid():
        cmd = "sudo ceph fsid"
        out = gs.get_host_executor_factory().run_command_on_first_host_from_selected_roles(
            cmd, roles=CephInfo.get_relevant_roles(), timeout=30)
        fsid = out.strip()
        return fsid

    @staticmethod
    def is_multiple_pools_enable():
        try:
            cmd = "sudo cat {}".format(CephPaths.UUID_POOL_JSON)
            out = gs.get_host_executor_factory().run_command_on_first_host_from_selected_roles(cmd, [Objectives.UC], 30)
            if not len(json.loads(out)):
                return False
            return True
        except:
            return False

    @staticmethod
    def get_uuid_pools():
        cmd = "sudo cat {}".format(CephPaths.UUID_POOL_JSON)
        out = gs.get_host_executor_factory().run_command_on_first_host_from_selected_roles(
            cmd, [Objectives.UC], 30)
        return json.loads(out)

    @staticmethod
    @lazy_global_data_loader
    def _set_and_get_ceph_clients_keyring():
        clients_list = {
            Deployment_type.CBIS: [
                "admin",
                "openstack"
            ],
            Deployment_type.NCS_OVER_BM: [
                "cephfs",
                "baremetal.cephfs",
                "cephrbd",
                "radosgw"
            ]
        }
        client_key_map = {}
        assert gs.get_deployment_type() in list(clients_list.keys()), \
            "'_set_and_get_ceph_clients_keyring' is not supported yet to {}".format(gs.get_deployment_type())
        client_list_deploy = clients_list.get(gs.get_deployment_type())
        if gs.get_deployment_type() == Deployment_type.CBIS:
            if CephInfo.is_multiple_pools_enable():
                uuid_pools = CephInfo.get_uuid_pools()
                for key in list(uuid_pools.keys()):
                    client_list_deploy.append(key)
        for client in client_list_deploy:
            cmd = "sudo ceph auth get-key client.{}".format(client)
            key = gs.get_host_executor_factory().run_command_on_first_host_from_selected_roles(
                cmd, roles=CephInfo.get_relevant_roles(), timeout=30)
            client_key_map[client] = key
        return client_key_map

    @staticmethod
    def get_osd_tree():
        return CephInfo._set_and_get_ceph_osd_dict()

    @staticmethod
    def get_osd_conf():
        return CephInfo._set_and_get_ceph_osd_conf()

    @staticmethod
    def get_fsid():
        return CephInfo._set_and_get_ceph_fsid()

    @staticmethod
    def get_clients_keys_map(client_name=None):
        if client_name:
            return CephInfo._set_and_get_ceph_clients_keyring().get(client_name)
        return CephInfo._set_and_get_ceph_clients_keyring()

    @staticmethod
    def is_ceph_used():
        if gs.get_deployment_type() == Deployment_type.NCS_OVER_BM:
            return gs.get_base_conf()['ceph_configured']
        if gs.get_deployment_type() == Deployment_type.CBIS:
            return gs.get_base_conf()['CBIS']['storage'].get('ceph_backend_enabled') or \
                   any(PythonUtils.get_value_from_nested_dict(gs.get_base_conf()['CBIS'], 'enable_ceph_storage'))
        return True

    @staticmethod
    def get_osd_service(osd_id='', pattern=False):
        assert not (osd_id and pattern), "'osd_id' and 'pattern' cannot both be set at the same time"
        assert osd_id or pattern, "Either 'osd_id' must have a value or 'pattern' must be True"

        if osd_id:
            value = osd_id
        elif pattern:
            value = '\\w+'

        if gs.get_version() < Version.V24_11:
            return 'ceph-osd@{}.service'.format(value)
        else:
            fsid = CephInfo.get_fsid()
            return 'ceph-{}@osd.{}.service'.format(fsid, value)