from __future__ import absolute_import
import json
import os

import pytest
from tests.pytest.tools.versions_alignment import Mock, patch
from flows.Storage.ceph.CephInfo import CephInfo
from tests.pytest.flows.storage.ceph.test_ceph import get_data_from_file
from tools import sys_parameters
from tools.Exceptions import UnExpectedSystemOutput
from tools.global_enums import Deployment_type, Objectives, Version
import tools.global_logging as log
from tools.lazy_global_data_loader import LazyDataLoader


class TestCephInfo:
    tested_type = CephInfo
    storage_dict_passed = {
        'overcloud-ovscompute-1': [], 'overcloud-ovscompute-0': [],
        'overcloud-sriovperformancecompute-0': [],
        'overcloud-sriovperformancecompute-1': []}
    storage_dict_failed = {
        'overcloud-storage-pl-8004-i14-0': [], 'overcloud-storage-pl-8004-i14-1': [],
        'overcloud-storage-pl-8004-i14-2': []}

    ceph_host_names_failed = [
        {"name": "overcloud-ovscompute-0", "type_id": 1, "id": -9, "pool_weights": {}, "type": "host",
         "children": [7, 3]},
        {"name": "overcloud-ovscompute-1", "type_id": 1, "id": -7, "pool_weights": {}, "type": "host",
         "children": [6, 2]}
        ]
    ceph_host_names_passed = list(ceph_host_names_failed)
    ceph_host_names_passed.extend(
        [{"name": "overcloud-sriovperformancecompute-0", "type_id": 1, "id": -5, "pool_weights": {}, "type": "host",
          "children": [5, 0]},
         {"name": "overcloud-sriovperformancecompute-1", "type_id": 1, "id": -3, "pool_weights": {}, "type": "host",
          "children": [4, 1]}])

    @pytest.mark.parametrize("title, ceph_host_names, osd_tree_path, storage_dict",
                             [('host_not_analog_to_ceph', ceph_host_names_failed, "osd_tree_failed.json",
                               storage_dict_failed),
                              ('scenario_passed', ceph_host_names_passed, "osd_tree_passed.json",
                               storage_dict_passed)])
    def test_map_cbis_host_name_to_ceph_name(self, title, ceph_host_names, osd_tree_path, storage_dict):
        tested_object = self.tested_type()
        sys_parameters.get_host_executor_factory = Mock()
        sys_parameters.get_host_executor_factory.return_value.get_host_executors_by_roles.return_value = storage_dict
        osd_tree = json.loads(get_data_from_file(osd_tree_path))
        return_dict = tested_object.map_cbis_host_name_to_ceph_name(ceph_host_names, osd_tree)
        if title == 'host_not_analog_to_ceph':
            ceph_host_name = "overcloud-ovscompute-0"
            assert (return_dict['is_passed'] == False)

        if title == 'scenario_passed':
            assert (return_dict == {key: key for key in list(storage_dict.keys())})

    @pytest.mark.parametrize("deployment_type, is_used",
                             [(Deployment_type.NCS_OVER_BM, True), (Deployment_type.NCS_OVER_BM, False),
                              (Deployment_type.CBIS, True), (Deployment_type.CBIS, False)])
    def test_is_ceph_used(self, deployment_type, is_used):
        cbis_base_conf = {
            "CBIS": {
                "storage": {"ceph_backend_enabled": False},
                "host_group_config": {
                    "AvrsCompute": {"enable_ceph_storage": False}
                }

            }
        }
        cnb_base_conf = {"ceph_configured": False}
        tested_object = self.tested_type()
        sys_parameters.get_deployment_type = Mock()
        sys_parameters.get_deployment_type.return_value = deployment_type

        sys_parameters.get_base_conf = Mock()
        if deployment_type == Deployment_type.NCS_OVER_BM:
            if is_used:
                cnb_base_conf["ceph_configured"] = True
            sys_parameters.get_base_conf.return_value = cnb_base_conf
            assert (tested_object.is_ceph_used() == is_used)
        else:
            sys_parameters.get_base_conf.return_value = cbis_base_conf
            if is_used:
                sys_parameters.get_base_conf.return_value["CBIS"]["storage"]["ceph_backend_enabled"] = True
                sys_parameters.get_base_conf.return_value["CBIS"]["host_group_config"]["AvrsCompute"][
                    "enable_ceph_storage"] = True
                assert (tested_object.is_ceph_used() == is_used)
                sys_parameters.get_base_conf.return_value["CBIS"]["storage"]["ceph_backend_enabled"] = True
                sys_parameters.get_base_conf.return_value["CBIS"]["host_group_config"]["AvrsCompute"][
                    "enable_ceph_storage"] = False
                assert (tested_object.is_ceph_used() == is_used)
                sys_parameters.get_base_conf.return_value["CBIS"]["storage"]["ceph_backend_enabled"] = False
                sys_parameters.get_base_conf.return_value["CBIS"]["host_group_config"]["AvrsCompute"][
                    "enable_ceph_storage"] = True
                assert (tested_object.is_ceph_used() == is_used)
            else:
                assert (tested_object.is_ceph_used() == is_used)

    @pytest.mark.parametrize("title", [('exception'), ("passed"), ("empty_dict")])
    def test_is_multiple_pools_enable(self, title):
        tested_object = self.tested_type()
        sys_parameters.get_host_executor_factory = Mock()
        if title == "exception":
            sys_parameters.get_host_executor_factory.return_value.run_command_on_first_host_from_selected_roles.return_value.status_code = 1
            assert tested_object.is_multiple_pools_enable() is False
        if title == "passed":
            sys_parameters.get_host_executor_factory.return_value.run_command_on_first_host_from_selected_roles.return_value = '{"ovs": "1eef0798-5679-4a20-b565-2e7a7557b803", "sriov": "8dacbd13-f368-4f20-aaf3-bdcbdc3c6a14", "dpdk": "8a9ffdd6-1385-41e4-b1d2-c856cf48a0b7"}'
            assert tested_object.is_multiple_pools_enable()
        if title == "empty_dict":
            sys_parameters.get_host_executor_factory.return_value.run_command_on_first_host_from_selected_roles.return_value = '{}'
            assert tested_object.is_multiple_pools_enable() is False

    @pytest.mark.parametrize("deployment_type, uuid_pools, key_value, expected_out_dict",
                             [(Deployment_type.CBIS, '{}', 'xxx', {'admin': 'xxx', 'openstack': 'xxx'}),
                              (Deployment_type.NCS_OVER_VSPHERE, '{}', 'xxx', {'admin': 'xxx', 'openstack': 'xxx'}),
                              (Deployment_type.CBIS, '{"ovs": "xxx", "sriov": "xxx"}', 'xxx',
                               {'admin': 'xxx', 'openstack': 'xxx', 'ovs': 'xxx', 'sriov': 'xxx'}),
                              (Deployment_type.NCS_OVER_BM, '{}', 'xxx',
                               {'cephfs': 'xxx', 'baremetal.cephfs': 'xxx', 'cephrbd': 'xxx', 'radosgw': 'xxx'})])
    def test_set_and_get_ceph_clients_keyring(self, deployment_type, uuid_pools, key_value, expected_out_dict):
        tested_object = self.tested_type()
        LazyDataLoader.my_data_db = {}
        sys_parameters.get_deployment_type = Mock(return_value=deployment_type)
        sys_parameters.is_ncs_central = Mock(return_value=False)
        sys_parameters.is_central_cluster = Mock(return_value=False)
        log.init()
        if deployment_type is Deployment_type.NCS_OVER_VSPHERE:
            with pytest.raises(AssertionError) as excinfo:
                tested_object._set_and_get_ceph_clients_keyring()
            assert str(excinfo.value) == "'_set_and_get_ceph_clients_keyring' is not supported yet to ncs_vsphere"
        else:
            self.uuid_pools = uuid_pools
            self.key_value = key_value
            sys_parameters.get_host_executor_factory = Mock()
            sys_parameters.get_host_executor_factory.return_value.run_command_on_first_host_from_selected_roles = Mock(
                side_effect=self._run_command_on_first_host_from_selected_roles_side_effects)
            actual_out_dict = tested_object._set_and_get_ceph_clients_keyring()
            assert set(actual_out_dict.keys()) == set(expected_out_dict.keys())
            for key in expected_out_dict:
                assert expected_out_dict[key] == actual_out_dict[key]

    def _run_command_on_first_host_from_selected_roles_side_effects(self, cmd, roles, timeout=60):
        if "sudo ceph auth get-key client." in cmd:
            return self.key_value
        else:
            return self.uuid_pools

    def test_get_uuid_pools(self):
        tested_object = self.tested_type()
        sys_parameters.get_host_executor_factory = Mock()
        expected_dict = {"ovs": "xxx", "sriov": "xxx"}
        sys_parameters.get_host_executor_factory.return_value.run_command_on_first_host_from_selected_roles.return_value = json.dumps(
            expected_dict)
        actual_dict = tested_object.get_uuid_pools()
        assert set(actual_dict.keys()) == set(expected_dict.keys())
        for key in actual_dict:
            assert expected_dict[key] == actual_dict[key]

    @pytest.mark.parametrize("is_ncs_central, is_central_cluster",
                             [(True, True), (True, False), (False, True), (False, False)])
    def test_get_relevant_roles(self, is_ncs_central, is_central_cluster):
        tested_object = self.tested_type()
        sys_parameters.is_ncs_central = Mock(return_value=is_ncs_central)
        sys_parameters.is_central_cluster = Mock(return_value=is_central_cluster)
        actual_roles = tested_object.get_relevant_roles()
        if not is_ncs_central or not is_central_cluster:
            assert actual_roles == [Objectives.ONE_CONTROLLER, Objectives.ONE_MASTER]
        else:
            assert actual_roles == [Objectives.ONE_MANAGER]

    client_keyring = {'admin': 'xxx', 'openstack': 'yyy', 'ovs': 'zzz'}

    @pytest.mark.parametrize("client_name, client_keyring, expected_res",
                             [("openstack", client_keyring, "yyy"), (None, client_keyring, client_keyring),
                              ("wrong_client", client_keyring, None)])
    def test_get_clients_keys_map(self, client_name, client_keyring, expected_res):
        tested_object = self.tested_type()
        with patch(
                'flows.Storage.ceph.CephInfo.CephInfo._set_and_get_ceph_clients_keyring') as mock_set_and_get_ceph_clients_keyring:
            mock_set_and_get_ceph_clients_keyring.return_value = client_keyring
            actual_res = tested_object.get_clients_keys_map(client_name)
        assert actual_res == expected_res

    @pytest.mark.parametrize("fsid", [("xxx")])
    def test_get_fsid(self, fsid):
        tested_object = self.tested_type()
        with patch('flows.Storage.ceph.CephInfo.CephInfo.get_fsid') as mock_set_and_get_ceph_fsid:
            mock_set_and_get_ceph_fsid.return_value = fsid
            actual_res = tested_object.get_fsid()
        assert actual_res == fsid

    @pytest.mark.parametrize("ceph_osd_conf", [
        ({'osds': {'2': {'block_device': '/dev/sda3', 'hostname': 'overcloud-ovscompute-1'}}})])
    def test_get_osd_conf(self, ceph_osd_conf):
        tested_object = self.tested_type()
        with patch('flows.Storage.ceph.CephInfo.CephInfo._set_and_get_ceph_osd_conf') as mock_set_and_get_ceph_osd_conf:
            mock_set_and_get_ceph_osd_conf.return_value = ceph_osd_conf
            actual_res = tested_object.get_osd_conf()
        assert actual_res == ceph_osd_conf

    @pytest.mark.parametrize("hosts_osds_dict", [({"0": {"status": "ok"}, "67": {"status": "ok"}})])
    def test_get_osd_tree(self, hosts_osds_dict):
        tested_object = self.tested_type()
        with patch('flows.Storage.ceph.CephInfo.CephInfo._set_and_get_ceph_osd_dict') as mock_set_and_get_ceph_osd_dict:
            mock_set_and_get_ceph_osd_dict.return_value = hosts_osds_dict
            actual_res = tested_object.get_osd_tree()
        assert actual_res == hosts_osds_dict

    ceph_osd_tree_json = {'nodes': [{"id": -1, "name": "fast", "type": "root", "type_id": 10, "children": [-5]},
                                    {"id": -2, "name": "common", "type": "root", "type_id": 10, "children": [-3]},
                                    {"id": -3, "name": "overcloud-ovscompute-fi857-0", "type": "host", "type_id": 1,
                                     "pool_weights": {},
                                     "children": [2, 0]},
                                    {"id": 0, "device_class": "hdd", "name": "osd.0", "type": "osd", "type_id": 0,
                                     "crush_weight": 0.7491912841796875, "depth": 2, "pool_weights": {},
                                     "exists": 1,
                                     "status": "up", "reweight": 1, "primary_affinity": 1},
                                    {"id": 2, "device_class": "hdd", "name": "osd.2", "type": "osd", "type_id": 0,
                                     "crush_weight": 1.0915985107421875, "depth": 2, "pool_weights": {}, "exists": 1,
                                     "status": "up",
                                     "reweight": 1, "primary_affinity": 1},
                                    {"id": -5, "name": "overcloud-ovscompute-fi857-1", "type": "host", "type_id": 1,
                                     "pool_weights": {},
                                     "children": [3, 1]},
                                    {"id": 1, "device_class": "hdd", "name": "osd.1", "type": "osd", "type_id": 0,
                                     "crush_weight": 0.7491912841796875, "depth": 2, "pool_weights": {},
                                     "exists": 1,
                                     "status": "up", "reweight": 1, "primary_affinity": 1},
                                    {"id": 3, "device_class": "hdd", "name": "osd.3", "type": "osd", "type_id": 0,
                                     "crush_weight": 1.0915985107421875, "depth": 2, "pool_weights": {}, "exists": 1,
                                     "status": "up",
                                     "reweight": 1, "primary_affinity": 1}]}

    @pytest.mark.parametrize("ceph_objects_dict, current_root, expected_res", [
        (ceph_osd_tree_json["nodes"], {"id": -1, "name": "fast", "type": "root", "type_id": 10, "children": [-5]}, [
            {'name': 'overcloud-ovscompute-fi857-1', 'type_id': 1, 'id': -5, 'pool_weights': {}, 'type': 'host',
             'children': [3, 1]}]),
        ([], {"id": -1, "name": "fast", "type": "root", "type_id": 10},
         "\n-IP: controller\n -Command: \n -Output: unexpected osd output. expecting this root to have children: ceph_objects_dict is[] current_root is {'type_id': 10, 'type': 'root', 'id': -1, 'name': 'fast'} \n -Message: Un-Expected output \n -Trace: "),
        ([{"id": -5, "name": "overcloud-ovscompute-fi857-1", "type": "osd", "type_id": 1, "pool_weights": {},
           "children": [3, 1]}], {"id": -1, "name": "fast", "type": "root", "type_id": 10, "children": [-5]},
         "\n-IP: controller\n -Command: \n -Output: unexpected osd output. not expecting osd type here: ceph_objects_dict is[{'name': 'overcloud-ovscompute-fi857-1', 'type_id': 1, 'id': -5, 'pool_weights': {}, 'type': 'osd', 'children': [3, 1]}] \n current_root is {'children': [-5], 'type_id': 10, 'type': 'root', 'id': -1, 'name': 'fast'}\n \n -Message: Un-Expected output \n -Trace: ")])
    def test_get_my_children_from_ceph_crush_map(self, ceph_objects_dict, current_root, expected_res):
        tested_object = self.tested_type()
        if "unexpected" in expected_res:
            with pytest.raises(UnExpectedSystemOutput) as excinfo:
                tested_object._get_my_children_from_ceph_crush_map(ceph_objects_dict, current_root)
        else:
            actual_res = tested_object._get_my_children_from_ceph_crush_map(ceph_objects_dict, current_root)
            assert actual_res == expected_res

    @pytest.mark.parametrize("version, expected_res", [
        (Version.V22_7,
        {"storage_0": {"osds": {"1": {"hostname": "overcloud-ovscompute-fi857-0", "osd_device": "sda2"},
                                "3": {"hostname": "overcloud-ovscompute-fi857-0", "osd_device": "sdb"}},
                       "conf": {"DEFAULT": {},
                                "global": {"bluestore_block_wal_size": "10240", "bluestore_block_db_size": "1024"},
                                "osd": {"osd_deep_scrub_stride": "1048576", "osd_map_cache_size": "100"}}}}),
        (Version.V24_11,
        {"storage_0": {"osds": {"0": {"crush_location": "root=common rack=Rack-A-common host=common-tignes-cluster-storagebm-0", "osd_mclock_max_capacity_iops_ssd": "59718.093573"},
                                "1": {"crush_location": "root=common rack=Rack-A-common host=common-tignes-cluster-storagebm-1", "osd_mclock_max_capacity_iops_ssd": "61217.197453"}},
                       "conf": {"global": {"bluestore_block_db_size": "187286", "bluestore_block_wal_size": "10240"},
                                "mon": {"auth_allow_insecure_global_id_reclaim": "false", "mgr/crash/warn_recent_interval": "0"},
                                "osd": {"osd_max_pg_log_entries": "500", "osd_memory_target": "4294967296"}}}})
    ])

    def test_set_and_get_ceph_osd_conf(self, version, expected_res):
        LazyDataLoader.my_data_db = {}
        sys_parameters.get_deployment_type = Mock(return_value=Deployment_type.CBIS)
        sys_parameters.is_ncs_central = Mock(return_value=False)
        sys_parameters.is_central_cluster = Mock(return_value=False)
        sys_parameters.get_version = Mock(return_value=version)
        log.init()
        ceph_file_conf = """[global]
bluestore_block_db_size = 1024
bluestore_block_wal_size = 10240

[osd]
osd_deep_scrub_stride = 1048576
osd_map_cache_size = 100

[osd.1]
OSD_DEVICE = sda2
HOSTNAME = overcloud-ovscompute-fi857-0

[osd.3]
OSD_DEVICE = sdb
HOSTNAME = overcloud-ovscompute-fi857-0"""

        ceph_dump_conf = """
        [
            {
                "section": "global",
                "name": "bluestore_block_db_size",
                "value": "187286",
                "level": "dev",
                "can_update_at_runtime": false,
                "mask": ""
            },
            {
                "section": "global",
                "name": "bluestore_block_wal_size",
                "value": "10240",
                "level": "dev",
                "can_update_at_runtime": false,
                "mask": ""
            },
            {
                "section": "mon",
                "name": "auth_allow_insecure_global_id_reclaim",
                "value": "false",
                "level": "advanced",
                "can_update_at_runtime": true,
                "mask": ""
            },
            {
                "section": "mon",
                "name": "mgr/crash/warn_recent_interval",
                "value": "0",
                "level": "advanced",
                "can_update_at_runtime": true,
                "mask": ""
            },
            {
                "section": "osd",
                "name": "osd_max_pg_log_entries",
                "value": "500",
                "level": "dev",
                "can_update_at_runtime": true,
                "mask": ""
            },
            {
                "section": "osd",
                "name": "osd_memory_target",
                "value": "4294967296",
                "level": "basic",
                "can_update_at_runtime": true,
                "mask": "host:tignes-cluster-storagebm-0",
                "location_type": "host",
                "location_value": "tignes-cluster-storagebm-0"
            },
            {
                "section": "osd.0",
                "name": "crush_location",
                "value": "root=common rack=Rack-A-common host=common-tignes-cluster-storagebm-0",
                "level": "advanced",
                "can_update_at_runtime": false,
                "mask": ""
            },
            {
                "section": "osd.0",
                "name": "osd_mclock_max_capacity_iops_ssd",
                "value": "59718.093573",
                "level": "basic",
                "can_update_at_runtime": true,
                "mask": ""
            },
            {
                "section": "osd.1",
                "name": "crush_location",
                "value": "root=common rack=Rack-A-common host=common-tignes-cluster-storagebm-1",
                "level": "advanced",
                "can_update_at_runtime": false,
                "mask": ""
            },
            {
                "section": "osd.1",
                "name": "osd_mclock_max_capacity_iops_ssd",
                "value": "61217.197453",
                "level": "basic",
                "can_update_at_runtime": true,
                "mask": ""
            }
        ]
        """

        if version < Version.V24_11:
            ceph_conf = ceph_file_conf
        else:
            ceph_conf = ceph_dump_conf


        tested_object = self.tested_type()
        sys_parameters.get_host_executor_factory = Mock()
        sys_parameters.get_host_executor_factory.return_value.execute_cmd_by_roles.return_value = {
            "storage_0": {"out": ceph_conf, "err": "", "exit_code": 0, "ip": "xxxx.x.x.x",
                          "roles": [Objectives.STORAGE]}}
        actual_res = tested_object._set_and_get_ceph_osd_conf()
        assert actual_res == expected_res

    @pytest.mark.parametrize("ceph_objects_dict, expected_res", [
        (ceph_osd_tree_json['nodes'],
         {"fast": [{"id": -5, "name": "overcloud-ovscompute-fi857-1", "type": "host", "type_id": 1, "pool_weights": {},
                    "children": [3, 1]}], "common": [
             {"id": -3, "name": "overcloud-ovscompute-fi857-0", "type": "host", "type_id": 1, "pool_weights": {},
              "children": [2, 0]}]}),
        ([{"type": "xxx"}], {})
    ])
    def test_get_root_hosts_dict(self, ceph_objects_dict, expected_res):
        tested_object = self.tested_type()
        actual_res = tested_object.get_root_hosts_dict(ceph_objects_dict)
        assert actual_res == expected_res

    @pytest.mark.parametrize("ceph_osd_tree_json, storage_host_name_list, expected_res", [
        (ceph_osd_tree_json, {}, {'is_passed': False,
                                  'failed_msg': 'Mismatch between ceph hostnames: [u\'overcloud-ovscompute-fi857-0\'] and storage hostnames: []\nWe could not find cbis host name that is analog to ceph host name overcloud-ovscompute-fi857-0.\nCeph osd tree is {"nodes": [{"children": [-5], "type_id": 10, "type": "root", "id": -1, "name": "fast"}, {"children": [-3], "type_id": 10, "type": "root", "id": -2, "name": "common"}, {"name": "overcloud-ovscompute-fi857-0", "type_id": 1, "id": -3, "pool_weights": {}, "type": "host", "children": [2, 0]}, {"status": "up", "exists": 1, "type_id": 0, "crush_weight": 0.7491912841796875, "pool_weights": {}, "device_class": "hdd", "id": 0, "name": "osd.0", "reweight": 1, "primary_affinity": 1, "depth": 2, "type": "osd"}, {"status": "up", "exists": 1, "type_id": 0, "crush_weight": 1.0915985107421875, "pool_weights": {}, "device_class": "hdd", "id": 2, "name": "osd.2", "reweight": 1, "primary_affinity": 1, "depth": 2, "type": "osd"}, {"name": "overcloud-ovscompute-fi857-1", "type_id": 1, "id": -5, "pool_weights": {}, "type": "host", "children": [3, 1]}, {"status": "up", "exists": 1, "type_id": 0, "crush_weight": 0.7491912841796875, "pool_weights": {}, "device_class": "hdd", "id": 1, "name": "osd.1", "reweight": 1, "primary_affinity": 1, "depth": 2, "type": "osd"}, {"status": "up", "exists": 1, "type_id": 0, "crush_weight": 1.0915985107421875, "pool_weights": {}, "device_class": "hdd", "id": 3, "name": "osd.3", "reweight": 1, "primary_affinity": 1, "depth": 2, "type": "osd"}]}'}),
        (ceph_osd_tree_json, {"wrong_host": ""}, {'is_passed': False,
                                                  'failed_msg': 'Mismatch between ceph hostnames: [u\'overcloud-ovscompute-fi857-0\'] and storage hostnames: [\'wrong_host\']\nWe could not find cbis host name that is analog to ceph host name overcloud-ovscompute-fi857-0.\nCeph osd tree is {"nodes": [{"children": [-5], "type_id": 10, "type": "root", "id": -1, "name": "fast"}, {"children": [-3], "type_id": 10, "type": "root", "id": -2, "name": "common"}, {"name": "overcloud-ovscompute-fi857-0", "type_id": 1, "id": -3, "pool_weights": {}, "type": "host", "children": [2, 0]}, {"status": "up", "exists": 1, "type_id": 0, "crush_weight": 0.7491912841796875, "pool_weights": {}, "device_class": "hdd", "id": 0, "name": "osd.0", "reweight": 1, "primary_affinity": 1, "depth": 2, "type": "osd"}, {"status": "up", "exists": 1, "type_id": 0, "crush_weight": 1.0915985107421875, "pool_weights": {}, "device_class": "hdd", "id": 2, "name": "osd.2", "reweight": 1, "primary_affinity": 1, "depth": 2, "type": "osd"}, {"name": "overcloud-ovscompute-fi857-1", "type_id": 1, "id": -5, "pool_weights": {}, "type": "host", "children": [3, 1]}, {"status": "up", "exists": 1, "type_id": 0, "crush_weight": 0.7491912841796875, "pool_weights": {}, "device_class": "hdd", "id": 1, "name": "osd.1", "reweight": 1, "primary_affinity": 1, "depth": 2, "type": "osd"}, {"status": "up", "exists": 1, "type_id": 0, "crush_weight": 1.0915985107421875, "pool_weights": {}, "device_class": "hdd", "id": 3, "name": "osd.3", "reweight": 1, "primary_affinity": 1, "depth": 2, "type": "osd"}]}'}),
        (ceph_osd_tree_json, {"overcloud-ovscompute-fi857-0": [], "overcloud-ovscompute-fi857-1": []},
         {'overcloud-ovscompute-fi857-0': {
             '0': {'status': u'up', 'dev_class': u'hdd', 'root': u'common', 'weight': 0.7491912841796875},
             '2': {'status': u'up', 'dev_class': u'hdd', 'root': u'common', 'weight': 1.0915985107421875}},
             'overcloud-ovscompute-fi857-1': {
                 '1': {'status': u'up', 'dev_class': u'hdd', 'root': u'fast', 'weight': 0.7491912841796875},
                 '3': {'status': u'up', 'dev_class': u'hdd', 'root': u'fast', 'weight': 1.0915985107421875}}})
    ])
    def test_set_and_get_ceph_osd_dict(self, ceph_osd_tree_json, storage_host_name_list, expected_res):
        tested_object = self.tested_type()
        LazyDataLoader.my_data_db = {}
        sys_parameters.get_deployment_type = Mock(return_value=Deployment_type.CBIS)
        sys_parameters.is_ncs_central = Mock(return_value=False)
        sys_parameters.is_central_cluster = Mock(return_value=False)
        log.init()
        sys_parameters.get_host_executor_factory = Mock()
        sys_parameters.get_host_executor_factory.return_value.run_command_on_first_host_from_selected_roles.return_value = json.dumps(
            ceph_osd_tree_json)
        sys_parameters.get_host_executor_factory.return_value.get_host_executors_by_roles.return_value = storage_host_name_list
        actual_res = tested_object._set_and_get_ceph_osd_dict()

        if actual_res.get("is_passed") is not None:
            assert actual_res["is_passed"] == expected_res["is_passed"]
        else:
            assert actual_res == expected_res

    @pytest.mark.parametrize("root_name, host_osds, expected_res", [
        ("root_value",
         [{"id": 1, "status": "status_value1", "crush_weight": 111,
           "device_class": "device_class_value1"},
          {"id": 2, "status": "status_value2", "crush_weight": 222,
           "device_class": "device_class_value2"}],
         {"1": {"status": "status_value1", "root": "root_value", "weight": 111.0,
                "dev_class": "device_class_value1"},
          "2": {"status": "status_value2", "root": "root_value", "weight": 222.0,
                "dev_class": "device_class_value2"}}),
        ("root_value", [], {})])
    def test_get_host_osds_dict(self, root_name, host_osds, expected_res):
        tested_object = self.tested_type()
        actual_res = tested_object.get_host_osds_dict(root_name, host_osds)
        assert actual_res == expected_res

    @pytest.mark.parametrize("fsid", [("xxx")])
    def test_set_and_get_ceph_fsid(self, fsid):
        tested_object = self.tested_type()
        LazyDataLoader.my_data_db = {}
        sys_parameters.get_deployment_type = Mock(return_value=Deployment_type.CBIS)
        sys_parameters.is_ncs_central = Mock(return_value=False)
        sys_parameters.is_central_cluster = Mock(return_value=False)
        log.init()
        sys_parameters.get_host_executor_factory = Mock()
        sys_parameters.get_host_executor_factory.return_value.run_command_on_first_host_from_selected_roles.return_value = fsid
        actual_res = tested_object._set_and_get_ceph_fsid()
        assert actual_res == fsid
