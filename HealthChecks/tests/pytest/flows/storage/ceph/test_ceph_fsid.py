from __future__ import absolute_import
import warnings

import pytest
from tests.pytest.tools.versions_alignment import Mock
from flows.Storage.ceph.CephFSID import *
from flows.Storage.ceph.CephInfo import CephPaths
from tests.pytest.flows.storage.ceph.test_ceph import CephValidationTestBase, get_data_from_file
from tests.pytest.pytest_tools.operator.test_informator_validator import InformatorValidatorTestBase, \
    InformatorValidatorScenarioParams
from tests.pytest.pytest_tools.operator.test_data_collector import DataCollectorTestBase, DataCollectorScenarioParams
from tests.pytest.pytest_tools.operator.test_operator import CmdOutput
from tests.pytest.pytest_tools.operator.test_validation_base import ValidationTestBase, ValidationScenarioParams
from tools import sys_parameters


class TestKeyringMultiplePoolConfigCheck(CephValidationTestBase):
    tested_type = KeyringMultiplePoolConfigCheck
    uuid_pools = {"ovs": "1eef0798-5679-4a20-b565-2e7a7557b803", "sriov": "6ae21dfe-dd69-472b-bdff-1532d8bce82a",
                  "dpdk": "8a9ffdd6-1385-41e4-b1d2-c856cf48a0b7"}
    scenario_passed = [ValidationScenarioParams(
        scenario_title="scenario_passed compute",
        tested_object_mock_dict={"get_ip_address": Mock(return_value="10.75.243.84"),
                                 "get_vm_pool_by_pm_addr": Mock(return_value="sriov"),
                                 "get_host_name": Mock(return_value="compute_dummy")},
        cmd_input_output_dict={"sudo cat {}".format(CephPaths.KEYRING_PATH_TEMPLATE.format(client)): CmdOutput(
            get_data_from_file("ceph.client.kerying").format(client)) for client in list(uuid_pools.keys())},
        library_mocks_dict={"CephInfo.get_uuid_pools": Mock(return_value=uuid_pools),
                            "CephInfo.get_clients_keys_map": Mock(
                                return_value="AQC+a49iTFD0HhAA/Umd1Cb18lNCbogO7imaeA==")}),
        ValidationScenarioParams(
            scenario_title="scenario_passed controller",
            tested_object_mock_dict={"get_ip_address": Mock(return_value="10.75.243.84"),
                                     "get_vm_pool_by_pm_addr": Mock(return_value=None),
                                     "get_host_name": Mock(return_value="controller_dummy")},
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.KEYRING_PATH_TEMPLATE.format(client)): CmdOutput(
                get_data_from_file("ceph.client.kerying").format(client)) for client in list(uuid_pools.keys())},
            library_mocks_dict={"CephInfo.get_uuid_pools": Mock(return_value=uuid_pools),
                                "CephInfo.get_clients_keys_map": Mock(
                                    return_value="AQC+a49iTFD0HhAA/Umd1Cb18lNCbogO7imaeA==")})]

    scenario_failed = [ValidationScenarioParams(
        scenario_title="scenario failed compute",
        tested_object_mock_dict={"get_ip_address": Mock(return_value="10.75.243.84"),
                                 "get_vm_pool_by_pm_addr": Mock(return_value="sriov"),
                                 "get_host_name": Mock(return_value="compute_dummy")},
        cmd_input_output_dict={"sudo cat {}".format(CephPaths.KEYRING_PATH_TEMPLATE.format(client)): CmdOutput(
            get_data_from_file("ceph.client.kerying").format(client)) for client in list(uuid_pools.keys())},
        library_mocks_dict={"CephInfo.get_uuid_pools": Mock(return_value=uuid_pools),
                            "CephInfo.get_clients_keys_map": Mock(
                                return_value="AQC+a49iTFD0HhAA/Umd1Cb18lNCbogO7imae2==")},
        failed_msg="some keys not match: ['/etc/ceph/ceph.client.sriov.keyring']"),
        ValidationScenarioParams(
            scenario_title="scenario failed controller",
            tested_object_mock_dict={"get_ip_address": Mock(return_value="10.75.243.84"),
                                     "get_vm_pool_by_pm_addr": Mock(return_value=None),
                                     "get_host_name": Mock(return_value="controller_dummy")},
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.KEYRING_PATH_TEMPLATE.format(client)): CmdOutput(
                get_data_from_file("ceph.client.kerying").format(client)) for client in list(uuid_pools.keys())},
            library_mocks_dict={"CephInfo.get_uuid_pools": Mock(return_value=uuid_pools),
                                "CephInfo.get_clients_keys_map": Mock(
                                    return_value="AQC+a49iTFD0HhAA/Umd1Cb18lNCbogO7imae2==")},
            failed_msg="some keys not match: ['/etc/ceph/ceph.client.ovs.keyring', '/etc/ceph/ceph.client.sriov.keyring', '/etc/ceph/ceph.client.dpdk.keyring']")]

    scenario_prerequisite_not_fulfilled = [ValidationScenarioParams("prerequisite_not_fulfilled",
                                                                    library_mocks_dict={
                                                                        "CephInfo.is_ceph_used": Mock(
                                                                            return_value=False)
                                                                    }),
                                           ValidationScenarioParams("prerequisite_not_fulfilled missing pool_uuid",
                                                                    library_mocks_dict={
                                                                        "CephInfo.is_ceph_used": Mock(
                                                                            return_value=True),
                                                                        "CephInfo.is_multiple_pools_enable": Mock(
                                                                            return_value=False)})]
    scenario_prerequisite_fulfilled = [ValidationScenarioParams("prerequisite_fulfilled",
                                                                library_mocks_dict={
                                                                    "CephInfo.is_ceph_used": Mock(return_value=True),
                                                                    "CephInfo.is_multiple_pools_enable": Mock(
                                                                        return_value=True)})]

    @pytest.mark.parametrize("scenario_params", scenario_prerequisite_not_fulfilled)
    def test_prerequisite_not_fulfilled(self, scenario_params, tested_object):
        ValidationTestBase.test_prerequisite_not_fulfilled(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_prerequisite_fulfilled)
    def test_prerequisite_fulfilled(self, scenario_params, tested_object):
        ValidationTestBase.test_prerequisite_fulfilled(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestFSIdNovaSecretMultiplePoolsValidator(CephValidationTestBase):
    tested_type = FSIdNovaSecretMultiplePoolsValidator
    nova_secret_multiple_pool_xml = """<secret ephemeral='no' private='no'>
    <usage type='ceph'>
        <name>client.openstack secret</name>
    </usage>
    <uuid>6ae21dfe-dd69-472b-bdff-1532d8bce82a</uuid>
</secret>"""
    scenario_passed = [
        ValidationScenarioParams(
        scenario_title="scenario_passed", version=Version.V22,
        tested_object_mock_dict={"get_pool_uuid_if_exist": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a"),
                                 "_get_conf_path": Mock(return_value="file_path")},
        cmd_input_output_dict={"sudo cat file_path": CmdOutput(nova_secret_multiple_pool_xml)},),
        ValidationScenarioParams(
            scenario_title="scenario_passed v25", version=Version.V25,
            tested_object_mock_dict={"get_pool_uuid_if_exist": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a"),
                                     "_get_conf_path": Mock(return_value="file_path")},
            cmd_input_output_dict={"sudo podman exec nova_compute cat file_path": CmdOutput(nova_secret_multiple_pool_xml)})
        ]
    scenario_unexpected_system_output = [
        ValidationScenarioParams(
            scenario_title="unexpected_system_output v25", version=Version.V25,
            tested_object_mock_dict={"get_pool_uuid_if_exist": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a"),
                                     "_get_conf_path": Mock(return_value="file_path")},
            cmd_input_output_dict={"sudo podman exec nova_compute cat file_path": CmdOutput("")})
    ]
    scenario_io_error = [ValidationScenarioParams(
        scenario_title="scenario_io_error", version=Version.V22,
        tested_object_mock_dict={"get_pool_uuid_if_exist": Mock(return_value=""),
                                 "_get_conf_dict": Mock(return_value=nova_secret_multiple_pool_xml),
                                 "_get_conf_path": Mock(return_value="file_path")})]

    scenario_failed = [ValidationScenarioParams(
        scenario_title="scenario failed", version=Version.V22,
        tested_object_mock_dict={"get_pool_uuid_if_exist": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce821"),
                                 "_get_conf_dict": Mock(return_value=nova_secret_multiple_pool_xml),
                                 "_get_conf_path": Mock(return_value="file_path")},
        failed_msg="The nova_secret_multiple_pool configured is 6ae21dfe-dd69-472b-bdff-1532d8bce82a but the runtime value is 6ae21dfe-dd69-472b-bdff-1532d8bce821"),
        ValidationScenarioParams(
            scenario_title="scenario failed v25_7", version=Version.V25_7,
            tested_object_mock_dict={"get_pool_uuid_if_exist": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce821"),
                                     "_get_conf_path": Mock(return_value="file_path")},
            cmd_input_output_dict={"sudo podman exec nova_compute cat file_path": CmdOutput(nova_secret_multiple_pool_xml)},
            failed_msg="The nova_secret_multiple_pool configured is 6ae21dfe-dd69-472b-bdff-1532d8bce82a but the runtime value is 6ae21dfe-dd69-472b-bdff-1532d8bce821")]

    scenario_prerequisite_not_fulfilled = [ValidationScenarioParams("prerequisite_not_fulfilled",
                                                                    library_mocks_dict={
                                                                        "CephInfo.is_ceph_used": Mock(
                                                                            return_value=False)
                                                                    }),
                                           ValidationScenarioParams("prerequisite_not_fulfilled missing pool_uuid",
                                                                    tested_object_mock_dict={
                                                                        "get_pool_uuid_if_exist": Mock(
                                                                            return_value=None)},
                                                                    library_mocks_dict={"CephInfo.is_ceph_used": Mock(
                                                                        return_value=True)})]
    scenario_prerequisite_fulfilled = [ValidationScenarioParams("prerequisite_fulfilled",
                                                                tested_object_mock_dict={"get_pool_uuid_if_exist": Mock(
                                                                    return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")},
                                                                library_mocks_dict={
                                                                    "CephInfo.is_ceph_used": Mock(return_value=True)})]

    @pytest.mark.parametrize("scenario_params", scenario_prerequisite_not_fulfilled)
    def test_prerequisite_not_fulfilled(self, scenario_params, tested_object):
        ValidationTestBase.test_prerequisite_not_fulfilled(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_prerequisite_fulfilled)
    def test_prerequisite_fulfilled(self, scenario_params, tested_object):
        ValidationTestBase.test_prerequisite_fulfilled(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_io_error)
    def test_scenario_io_error(self, scenario_params, tested_object):
        CephValidationTestBase.test_scenario_io_error(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_unexpected_system_output(self, scenario_params, tested_object)


class TestCephJournalSizeConfCheck(CephValidationTestBase):
    tested_type = CephJournalSizeConfCheck

    scenario_passed = [
        ValidationScenarioParams(scenario_title="scenario_passed - global field",
        tested_object_mock_dict={"is_prerequisite_fulfilled": Mock(return_value=True),
                                 "_get_conf_dict": Mock(return_value={"CBIS": {"storage": {"ceph_journal_size": 2}}}),
                                 "get_dict_from_file": Mock(return_value={"global": {"osd_journal_size": 2}})}),
        ValidationScenarioParams(
            scenario_title="scenario_passed - osd field",
            tested_object_mock_dict={"is_prerequisite_fulfilled": Mock(return_value=True),
                                     "_get_conf_dict": Mock(return_value={"CBIS": {"storage": {"ceph_journal_size": 2}}}),
                                     "get_dict_from_file": Mock(return_value={"osd": {"osd_journal_size": 2}})})]

    scenario_io_error = [ValidationScenarioParams(
        scenario_title="scenario_io_error",
        tested_object_mock_dict={"is_prerequisite_fulfilled": Mock(return_value=True),
                                 "_get_conf_dict": Mock(return_value={"CBIS": {"storage": {"ceph_journal_size": 2}}}),
                                 "get_dict_from_file": Mock(return_value={"osd": {"osd_journal_size": ""}})})]

    scenario_unexpected_system_output = [ValidationScenarioParams(
        scenario_title="scenario_unexpected_system_output - get_value_from_config",
        tested_object_mock_dict={"is_prerequisite_fulfilled": Mock(return_value=True),
                                 "_get_conf_dict": Mock(return_value={"xxx": "yyy"}),
                                 "get_dict_from_file": Mock(return_value={"osd": {"osd_journal_size": 2}})})]

    scenario_failed = [ValidationScenarioParams(
        scenario_title="scenario failed - osd field",
        tested_object_mock_dict={"is_prerequisite_fulfilled": Mock(return_value=True),
                                 "_get_conf_dict": Mock(return_value={"CBIS": {"storage": {"ceph_journal_size": 2}}}),
                                 "get_dict_from_file": Mock(return_value={"osd": {"osd_journal_size": 3}})},
        failed_msg="The ceph_journal_size configured is 2 but the runtime value is 3"),
        ValidationScenarioParams(
            scenario_title="scenario failed - missing field",
            tested_object_mock_dict={"is_prerequisite_fulfilled": Mock(return_value=True),
                                     "_get_conf_dict": Mock(return_value={"CBIS": {"storage": {"ceph_journal_size": 2}}}),
                                     "get_dict_from_file": Mock(return_value={"global": {"xxx": 3}})},
            failed_msg="The ceph_journal_size configured is 2 but the runtime value is None"),
        ValidationScenarioParams(
            scenario_title="scenario failed - global field",
            tested_object_mock_dict={"is_prerequisite_fulfilled": Mock(return_value=True),
                                     "_get_conf_dict": Mock(return_value={"CBIS": {"storage": {"ceph_journal_size": 2}}}),
                                     "get_dict_from_file": Mock(return_value={"global": {"osd_journal_size": 3}})},
            failed_msg="The ceph_journal_size configured is 2 but the runtime value is 3")
    ]

    @pytest.mark.parametrize("scenario_params", scenario_io_error)
    def test_scenario_io_error(self, scenario_params, tested_object):
        CephValidationTestBase.test_scenario_io_error(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_unexpected_system_output(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestCephPoolSizeConfigCheck(CephValidationTestBase):
    tested_type = CephPoolSizeConfigCheck
    sys_parameters.get_base_conf = Mock(return_value={})
    ceph_conf = """
[client.libvirt]
admin socket = /var/run/ceph/$cluster-$type.$id.$pid.$cctid.asok # must be writable by QEMU and allowed by SELinux or AppArmor

# Please do not change this file directly since it is managed by Ansible and will be overwritten
[global]
# let's force the admin socket the way it was so we can properly check for existing instances
# also the line $cluster-$name.$pid.$cctid.asok is only needed when running multiple instances
# of the same daemon, thing ceph-ansible cannot do at the time of writing
cluster network = 172.17.4.0/24
osd_pool_default_size = {}
log file = /var/log/ceph/ceph.log
mon host = 172.17.3.18"""
    ceph_conf_unexpected_system_output = re.sub(".*" + "osd_pool_default_size" + ".*\n?", "", ceph_conf)

    scenario_passed = [ValidationScenarioParams(
        scenario_title="scenario_passed",
        tested_object_mock_dict={"_get_conf_dict": Mock(return_value={"CBIS": {"storage": {"ceph_pool_size": 2}}})},
        cmd_input_output_dict={"sudo cat {}".format(CephPaths.CEPH_CONF): CmdOutput(ceph_conf.format(2))})]
    scenario_unexpected_system_output = [ValidationScenarioParams(
        scenario_title="scenario_unexpected_system_output - get_value_from_system",
        cmd_input_output_dict={
            "sudo cat {}".format(CephPaths.CEPH_CONF): CmdOutput(ceph_conf_unexpected_system_output)}),
        ValidationScenarioParams(
            scenario_title="scenario_unexpected_system_output - get_value_from_config",
            tested_object_mock_dict={"_get_conf_dict": Mock(return_value={"xxx": "yyy"})},
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.CEPH_CONF): CmdOutput(ceph_conf)})]
    scenario_failed = [ValidationScenarioParams(
        scenario_title="scenario failed",
        tested_object_mock_dict={"_get_conf_dict": Mock(return_value={"CBIS": {"storage": {"ceph_pool_size": 2}}})},
        cmd_input_output_dict={"sudo cat {}".format(CephPaths.CEPH_CONF): CmdOutput(ceph_conf.format(3))},
        failed_msg="The ceph_pool_size configured is 2 but the runtime value is 3")]

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_unexpected_system_output(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestFSIDCephConfValidator(CephValidationTestBase):
    tested_type = FSIDCephConfValidator
    ceph_conf_fsid = """
[client.libvirt]
admin socket = /var/run/ceph/$cluster-$type.$id.$pid.$cctid.asok # must be writable by QEMU and allowed by SELinux or AppArmor

# Please do not change this file directly since it is managed by Ansible and will be overwritten
[global]
# let's force the admin socket the way it was so we can properly check for existing instances
# also the line $cluster-$name.$pid.$cctid.asok is only needed when running multiple instances
# of the same daemon, thing ceph-ansible cannot do at the time of writing
cluster network = 172.17.4.0/24
fsid = 6ae21dfe-dd69-472b-bdff-1532d8bce82a
log file = /var/log/ceph/ceph.log
mon host = 172.17.3.18"""
    scenario_passed = [ValidationScenarioParams(
        scenario_title="scenario_passed",
        library_mocks_dict={"CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")},
        cmd_input_output_dict={"sudo cat {}".format(CephPaths.CEPH_CONF): CmdOutput(ceph_conf_fsid)})]

    scenario_io_error = [ValidationScenarioParams(
        scenario_title="scenario_io_error",
        library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                            "CephInfo.get_fsid": Mock(return_value="")},
        cmd_input_output_dict={"sudo cat {}".format(CephPaths.CEPH_CONF): CmdOutput(ceph_conf_fsid)})]

    scenario_failed = [ValidationScenarioParams(
        scenario_title="scenario failed",
        library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                            "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce821")},
        cmd_input_output_dict={"sudo cat {}".format(CephPaths.CEPH_CONF): CmdOutput(ceph_conf_fsid)},
        failed_msg="The ceph_conf_fsid configured is 6ae21dfe-dd69-472b-bdff-1532d8bce82a but the runtime value is 6ae21dfe-dd69-472b-bdff-1532d8bce821")]

    @pytest.mark.parametrize("scenario_params", scenario_io_error)
    def test_scenario_io_error(self, scenario_params, tested_object):
        CephValidationTestBase.test_scenario_io_error(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestVmsFSIDCheck(CephValidationTestBase):
    tested_type = VmsFSIDCheck
    out_secret = "<secret type='ceph' uuid='6ae21dfe-dd69-472b-bdff-1532d8bce82a'/>\n" \
                 "<secret type='ceph' uuid='6ae21dfe-dd69-472b-bdff-1532d8bce82a'/>"
    instances_list = ["instance-00000019.xml", "instance-0000004f.xml", "instance-00000058.xml"]
    active_vms_cmd_dict = {
        'sudo virsh list --all --name': CmdOutput("instance-00000019\ninstance-0000004f\ninstance-00000058"),
        'sudo virsh list --inactive --name': CmdOutput("\n"),
        'sudo find /etc/libvirt/qemu/ -name "inst*.xml"': CmdOutput(
            "/etc/libvirt/qemu/instance-00000019.xml\n/etc/libvirt/qemu/instance-0000004f.xml\n"
            "/etc/libvirt/qemu/instance-00000058.xml"),
        'sudo find /var/run/libvirt/qemu/ -name "inst*.xml"': CmdOutput(
            "/var/run/libvirt/qemu/instance-00000019.xml\n/var/run/libvirt/qemu/instance-0000004f.xml\n"
            "/var/run/libvirt/qemu/instance-00000058.xml")
    }

    inactive_vms_cmd_dict = {
        'sudo virsh list --all --name': CmdOutput("instance-00000019\ninstance-0000004f\ninstance-00000058"),
        'sudo virsh list --inactive --name': CmdOutput("instance-00000019\ninstance-0000004f\ninstance-00000058"),
        'sudo find /etc/libvirt/qemu/ -name "inst*.xml"': CmdOutput(
            "/etc/libvirt/qemu/instance-00000019.xml\n/etc/libvirt/qemu/instance-0000004f.xml\n"
            "/etc/libvirt/qemu/instance-00000058.xml"),
        'sudo find /var/run/libvirt/qemu/ -name "inst*.xml"': CmdOutput("\n")
    }

    active_inactive_vms_cmd_dict = {
        'sudo virsh list --all --name': CmdOutput("instance-00000019\ninstance-0000004f\ninstance-00000058"),
        'sudo virsh list --inactive --name': CmdOutput("instance-0000004f\ninstance-00000058"),
        'sudo find /etc/libvirt/qemu/ -name "inst*.xml"': CmdOutput("/etc/libvirt/qemu/instance-00000019.xml\n"
                                                                    "/etc/libvirt/qemu/instance-0000004f.xml\n"
                                                                    "/etc/libvirt/qemu/instance-00000058.xml"),
        'sudo find /var/run/libvirt/qemu/ -name "inst*.xml"': CmdOutput(
            "/var/run/libvirt/qemu/instance-00000019.xml\n"),
        'sudo grep -oP "<secret.*ceph.*>" /var/run/libvirt/qemu/instance-00000019.xml': CmdOutput(out_secret)
    }

    shared_commands = {}

    for instance in instances_list:
        shared_commands['sudo grep -oP "<secret.*ceph.*>" /etc/libvirt/qemu/{}'.format(instance)] = CmdOutput(
            out_secret)

        active_vms_cmd_dict['sudo grep -oP "<secret.*ceph.*>" /var/run/libvirt/qemu/{}'.format(instance)] = CmdOutput(
            out_secret)

        shared_commands['sudo grep -i "<disk type=\'network\'" /var/run/libvirt/qemu/{}'.format(instance)] = \
            CmdOutput(out_secret)

        shared_commands['sudo grep -i "<disk type=\'network\'" /etc/libvirt/qemu/{}'.format(instance)] = \
            CmdOutput(out_secret)

    active_vms_cmd_dict.update(shared_commands)
    inactive_vms_cmd_dict.update(shared_commands)
    active_inactive_vms_cmd_dict.update(shared_commands)

    scenario_passed = [ValidationScenarioParams(
        scenario_title="scenario_passed active vms",
        library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                            "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")},
        cmd_input_output_dict=active_vms_cmd_dict),
        ValidationScenarioParams(
            scenario_title="scenario_passed inactive vms",
            library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                                "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")},
            cmd_input_output_dict=inactive_vms_cmd_dict),
        ValidationScenarioParams(
            scenario_title="scenario_passed no vm",
            library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                                "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")},
            cmd_input_output_dict={'sudo virsh list --all --name': CmdOutput("\n"),
                                   'sudo virsh list --inactive --name': CmdOutput("\n"),
                                   'sudo find /etc/libvirt/qemu/ -name "inst*.xml"': CmdOutput("\n"),
                                   'sudo find /var/run/libvirt/qemu/ -name "inst*.xml"': CmdOutput("\n")}),
        ValidationScenarioParams(
            scenario_title="scenario_passed inactive & active vms",
            library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                                "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")},
            cmd_input_output_dict=active_inactive_vms_cmd_dict),
        ValidationScenarioParams(
            scenario_title="scenario_passed multiple pool",
            tested_object_mock_dict={
                "get_pool_uuid_if_exist": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")},
            cmd_input_output_dict=active_inactive_vms_cmd_dict)]

    scenario_failed = [ValidationScenarioParams(
        scenario_title="scenario failed active vms",
        library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                            "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce821")},
        cmd_input_output_dict=active_vms_cmd_dict),
        ValidationScenarioParams(
            scenario_title="scenario failed inactive vms",
            library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                                "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce821")},
            cmd_input_output_dict=inactive_vms_cmd_dict),
        ValidationScenarioParams(
            scenario_title="scenario failed active & inactive vms",
            library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                                "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce821")},
            cmd_input_output_dict=active_inactive_vms_cmd_dict),
        ValidationScenarioParams(
            scenario_title="scenario failed multiple pool",
            tested_object_mock_dict={
                "get_pool_uuid_if_exist": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce821")},
            cmd_input_output_dict=active_inactive_vms_cmd_dict)]

    mismatch_instance_for_active_vms = {
        'sudo virsh list --all --name': CmdOutput("instance-00000019\ninstance-0000004f\ninstance-00000058"),
        'sudo virsh list --inactive --name': CmdOutput("\n"),
        'sudo find /var/run/libvirt/qemu/ -name "inst*.xml"': CmdOutput(
            "/var/run/libvirt/qemu/instance-00000019.xml"),
        'sudo grep -oP "<secret.*ceph.*>" /var/run/libvirt/qemu/instance-00000019.xml': CmdOutput(out_secret)
    }
    mismatch_instance_for_active_vms.update(shared_commands)

    mismatch_inactive_vms = {
        'sudo virsh list --all --name': CmdOutput("instance-00000019\ninstance-0000004f\ninstance-00000058"),
        'sudo virsh list --inactive --name': CmdOutput(
            "instance-00000019\ninstance-0000004f\ninstance-00000058"),
        'sudo find /var/run/libvirt/qemu/ -name "inst*.xml"': CmdOutput("\n"),
        'sudo find /etc/libvirt/qemu/ -name "inst*.xml"': CmdOutput("/etc/libvirt/qemu/instance-00000019.xml"),
        'sudo grep -oP "<secret.*ceph.*>" /etc/libvirt/qemu/instance-00000019.xml': CmdOutput(out_secret)}
    mismatch_inactive_vms.update(shared_commands)

    active_inactive_mismatch = {
        'sudo virsh list --all --name': CmdOutput("instance-00000019\ninstance-0000004f\ninstance-00000058"),
        'sudo virsh list --inactive --name': CmdOutput("instance-00000019"),
        'sudo find /var/run/libvirt/qemu/ -name "inst*.xml"': CmdOutput(
            "/var/run/libvirt/qemu/instance-00000019.xml"),
        'sudo grep -oP "<secret.*ceph.*>" /var/run/libvirt/qemu/instance-00000019.xml': CmdOutput(out_secret)}
    active_inactive_mismatch.update(shared_commands)

    active_inactive_mismatch_for_inactive = {
        'sudo virsh list --all --name': CmdOutput("instance-00000019\ninstance-0000004f\ninstance-00000058"),
        'sudo virsh list --inactive --name': CmdOutput("instance-0000004f\ninstance-00000058"),
        'sudo find /var/run/libvirt/qemu/ -name "inst*.xml"': CmdOutput(
            "/var/run/libvirt/qemu/instance-00000019.xml"),
        'sudo find /etc/libvirt/qemu/ -name "inst*.xml"': CmdOutput(
            "/var/run/libvirt/qemu/instance-00000019.xml"),
        'sudo grep -oP "<secret.*ceph.*>" /var/run/libvirt/qemu/instance-00000019.xml': CmdOutput(out_secret),
        'sudo grep -oP "<secret.*ceph.*>" /etc/libvirt/qemu/instance-00000019.xml': CmdOutput(out_secret)}
    active_inactive_mismatch_for_inactive.update(shared_commands)

    scenario_unexpected_system_output = [ValidationScenarioParams(
        scenario_title="scenario_unexpected_system_output - no instance.xml for active vms ",
        library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                            "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")},
        cmd_input_output_dict={
            'sudo virsh list --all --name': CmdOutput("instance-00000019\ninstance-0000004f\ninstance-00000058"),
            'sudo virsh list --inactive --name': CmdOutput("\n"),
            'sudo find /var/run/libvirt/qemu/ -name "inst*.xml"': CmdOutput("\n")}),
        ValidationScenarioParams(
            scenario_title="scenario_unexpected_system_output - mismatch instance.xml for active vms ",
            library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                                "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")},
            cmd_input_output_dict=mismatch_instance_for_active_vms),
        ValidationScenarioParams(
            scenario_title="scenario_unexpected_system_output - no instance.xml for inactive vms ",
            library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                                "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")},
            cmd_input_output_dict={
                'sudo virsh list --all --name': CmdOutput("instance-00000019\ninstance-0000004f\ninstance-00000058"),
                'sudo virsh list --inactive --name': CmdOutput(
                    "instance-00000019\ninstance-0000004f\ninstance-00000058"),
                'sudo find /var/run/libvirt/qemu/ -name "inst*.xml"': CmdOutput("\n"),
                'sudo find /etc/libvirt/qemu/ -name "inst*.xml"': CmdOutput("\n")}),
        ValidationScenarioParams(
            scenario_title="scenario_unexpected_system_output - mismatch instance.xml for inactive vms ",
            library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                                "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")},
            cmd_input_output_dict=mismatch_inactive_vms),
        ValidationScenarioParams(
            scenario_title="scenario_unexpected_system_output active & inactive- no instance.xml for active vms ",
            library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                                "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")},
            cmd_input_output_dict={
                'sudo virsh list --all --name': CmdOutput("instance-00000019\ninstance-0000004f\ninstance-00000058"),
                'sudo virsh list --inactive --name': CmdOutput("instance-00000019"),
                'sudo find /var/run/libvirt/qemu/ -name "inst*.xml"': CmdOutput("\n")}),
        ValidationScenarioParams(
            scenario_title="scenario_unexpected_system_output active & inactive- mismatch instance.xml for active vms ",
            library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                                "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")},
            cmd_input_output_dict=active_inactive_mismatch),
        ValidationScenarioParams(
            scenario_title="scenario_unexpected_system_output active & inactive- mismatch for inactive vms ",
            library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                                "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")},
            cmd_input_output_dict=active_inactive_mismatch_for_inactive)]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_unexpected_system_output(self, scenario_params, tested_object)


class TestFSIDCinderConfValidator(CephValidationTestBase):
    tested_type = FSIDCinderConfValidator
    cinder_conf = """[DEFAULT]
backup_ceph_conf=/etc/ceph/ceph.conf
[tripleo_ceph]
backend_host=hostgroup
volume_backend_name=tripleo_ceph
volume_driver=cinder.volume.drivers.rbd.RBDDriver
rbd_ceph_conf=/etc/ceph/ceph.conf
rbd_user=openstack
rbd_pool=volumes
rbd_secret_uuid=6ae21dfe-dd69-472b-bdff-1532d8bce82a
rbd_exclusive_cinder_pool=True
image_volume_cache_enabled = True"""
    multiple_pool_cinder_conf = re.sub(".*" + "rbd_secret_uuid" + ".*\n?", "", cinder_conf)

    scenario_passed = [ValidationScenarioParams(
        scenario_title="scenario_passed", version=Version.V20,
        library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                            "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")},
        cmd_input_output_dict={"sudo cat {}".format(CephPaths.CINDER_CONF): CmdOutput(cinder_conf)}),
        ValidationScenarioParams(
            scenario_title="scenario_passed v18", version=Version.V18,
            library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                                "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")},
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.CINDER_CONF_18): CmdOutput(cinder_conf)}),
        ValidationScenarioParams(
            scenario_title="scenario_passed multiple pool", version=Version.V22,
            library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=True)},
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.CINDER_CONF): CmdOutput(multiple_pool_cinder_conf)}),
        ValidationScenarioParams(
            scenario_title="scenario_passed multiple pool v18", version=Version.V18_5,
            library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=True)},
            cmd_input_output_dict={
                "sudo cat {}".format(CephPaths.CINDER_CONF_18): CmdOutput(multiple_pool_cinder_conf)})]

    scenario_failed = [ValidationScenarioParams(
        scenario_title="scenario failed v18", version=Version.V18,
        library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                            "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce821")},
        cmd_input_output_dict={"sudo cat {}".format(CephPaths.CINDER_CONF_18): CmdOutput(cinder_conf)},
        failed_msg="conf file: {} \nrbd_secret_uuid value/s is/are not equal to fsid runtime value -6ae21dfe-dd69-472b-bdff-1532d8bce821 .\nconf sections: \ntripleo_ceph:rbd_secret_uuid - 6ae21dfe-dd69-472b-bdff-1532d8bce82a".format(
            CephPaths.CINDER_CONF_18)),
        ValidationScenarioParams(
            scenario_title="scenario failed", version=Version.V19,
            library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                                "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce821")},
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.CINDER_CONF): CmdOutput(cinder_conf)},
            failed_msg="conf file: {} \nrbd_secret_uuid value/s is/are not equal to fsid runtime value -6ae21dfe-dd69-472b-bdff-1532d8bce821 .\nconf sections: \ntripleo_ceph:rbd_secret_uuid - 6ae21dfe-dd69-472b-bdff-1532d8bce82a".format(
                CephPaths.CINDER_CONF)),
        ValidationScenarioParams(
            scenario_title="scenario failed missing conf value", version=Version.V19,
            library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                                "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce821")},
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.CINDER_CONF): CmdOutput(multiple_pool_cinder_conf)},
            failed_msg="rbd_secret_uuid is not defined in conf file: {}".format(CephPaths.CINDER_CONF)),
        ValidationScenarioParams(
            scenario_title="scenario failed missing conf value v18", version=Version.V18,
            library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                                "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce821")},
            cmd_input_output_dict={
                "sudo cat {}".format(CephPaths.CINDER_CONF_18): CmdOutput(multiple_pool_cinder_conf)},
            failed_msg="rbd_secret_uuid is not defined in conf file: {}".format(CephPaths.CINDER_CONF_18)),
        ValidationScenarioParams(
            scenario_title="scenario failed multiple pool v18", version=Version.V18,
            library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=True)},
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.CINDER_CONF_18): CmdOutput(cinder_conf)},
            failed_msg="conf file: {} \nrbd_secret_uuid value/s is/are not equal to fsid runtime value -None .\nconf sections: \ntripleo_ceph:rbd_secret_uuid - 6ae21dfe-dd69-472b-bdff-1532d8bce82a".format(
                CephPaths.CINDER_CONF_18)),
        ValidationScenarioParams(
            scenario_title="scenario failed multiple pool", version=Version.V22,
            library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=True)},
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.CINDER_CONF): CmdOutput(cinder_conf)},
            failed_msg="conf file: {} \nrbd_secret_uuid value/s is/are not equal to fsid runtime value -None .\nconf sections: \ntripleo_ceph:rbd_secret_uuid - 6ae21dfe-dd69-472b-bdff-1532d8bce82a".format(
                CephPaths.CINDER_CONF))]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestFSIdNovaSecretValidator(CephValidationTestBase):
    tested_type = FSIdNovaSecretValidator
    nova_secret = """<secret ephemeral='no' private='no'>
    <usage type='ceph'>
        <name>client.openstack secret</name>
    </usage>
    <uuid>6ae21dfe-dd69-472b-bdff-1532d8bce82a</uuid>
</secret>"""
    scenario_passed = [ValidationScenarioParams(
        scenario_title="scenario_passed", version=Version.V20,
        library_mocks_dict={"CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")},
        cmd_input_output_dict={"sudo cat {}".format(CephPaths.NOVA_SECRET): CmdOutput(nova_secret)}),
        ValidationScenarioParams(
            scenario_title="scenario_passed v18", version=Version.V18,
            library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                                "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")},
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.NOVA_SECRET_18): CmdOutput(nova_secret)})]

    scenario_io_error = [ValidationScenarioParams(
        scenario_title="scenario_io_error", version=Version.V20,
        library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                            "CephInfo.get_fsid": Mock(return_value="")},
        cmd_input_output_dict={"sudo cat {}".format(CephPaths.NOVA_SECRET): CmdOutput(nova_secret)}),
        ValidationScenarioParams(
            scenario_title="scenario_io_error v18", version=Version.V18,
            library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                                "CephInfo.get_fsid": Mock(return_value="")},
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.NOVA_SECRET_18): CmdOutput(nova_secret)})]

    scenario_failed = [ValidationScenarioParams(
        scenario_title="scenario failed v18", version=Version.V18,
        library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                            "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce821")},
        cmd_input_output_dict={"sudo cat {}".format(CephPaths.NOVA_SECRET_18): CmdOutput(nova_secret)},
        failed_msg="The nova_secret configured is 6ae21dfe-dd69-472b-bdff-1532d8bce82a but the runtime value is 6ae21dfe-dd69-472b-bdff-1532d8bce821"),
        ValidationScenarioParams(
            scenario_title="scenario failed", version=Version.V19,
            library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                                "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce821")},
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.NOVA_SECRET): CmdOutput(nova_secret)},
            failed_msg="The nova_secret configured is 6ae21dfe-dd69-472b-bdff-1532d8bce82a but the runtime value is 6ae21dfe-dd69-472b-bdff-1532d8bce821")]

    @pytest.mark.parametrize("scenario_params", scenario_io_error)
    def test_scenario_io_error(self, scenario_params, tested_object):
        CephValidationTestBase.test_scenario_io_error(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestFsidNovaConfValidator(CephValidationTestBase):
    tested_type = FsidNovaConfValidator
    nova_conf = """[libvirt]
rbd_secret_uuid=6ae21dfe-dd69-472b-bdff-1532d8bce82a"""
    scenario_passed = [ValidationScenarioParams(
        scenario_title="scenario_passed", version=Version.V20,
        library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                            "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")},
        cmd_input_output_dict={"sudo cat {}".format(CephPaths.NOVA_CONF): CmdOutput(nova_conf)}),
        ValidationScenarioParams(
            scenario_title="scenario_passed v18", version=Version.V18,
            library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                                "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")},
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.NOVA_CONF_18): CmdOutput(nova_conf)}),
        ValidationScenarioParams(
            scenario_title="scenario_passed multiple pool", version=Version.V22,
            tested_object_mock_dict={
                "get_pool_uuid_if_exist": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")},
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.NOVA_CONF): CmdOutput(nova_conf)}),
        ValidationScenarioParams(
            scenario_title="scenario_passed multiple pool v18", version=Version.V18_5,
            tested_object_mock_dict={
                "get_pool_uuid_if_exist": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")},
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.NOVA_CONF_18): CmdOutput(nova_conf)})]

    scenario_io_error = [ValidationScenarioParams(
        scenario_title="scenario_io_error multiple pool", version=Version.V22,
        tested_object_mock_dict={"get_pool_uuid_if_exist": Mock(return_value="")},
        cmd_input_output_dict={"sudo cat {}".format(CephPaths.NOVA_CONF): CmdOutput(nova_conf)}),
        ValidationScenarioParams(
            scenario_title="scenario_io_error multiple pool v18", version=Version.V18_5,
            tested_object_mock_dict={"get_pool_uuid_if_exist": Mock(return_value="")},
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.NOVA_CONF_18): CmdOutput(nova_conf)}),
        ValidationScenarioParams(
            scenario_title="scenario_io_error", version=Version.V20,
            library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                                "CephInfo.get_fsid": Mock(return_value="")},
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.NOVA_CONF): CmdOutput(nova_conf)}),
        ValidationScenarioParams(
            scenario_title="scenario_io_error v18", version=Version.V18,
            library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                                "CephInfo.get_fsid": Mock(return_value="")},
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.NOVA_CONF_18): CmdOutput(nova_conf)})]

    scenario_failed = [ValidationScenarioParams(
        scenario_title="scenario failed v18", version=Version.V18,
        library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                            "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce821")},
        cmd_input_output_dict={"sudo cat {}".format(CephPaths.NOVA_CONF_18): CmdOutput(nova_conf)},
        failed_msg="The nova_fsid configured is 6ae21dfe-dd69-472b-bdff-1532d8bce82a but the runtime value is 6ae21dfe-dd69-472b-bdff-1532d8bce821"),
        ValidationScenarioParams(
            scenario_title="scenario failed", version=Version.V19,
            library_mocks_dict={"CephInfo.is_multiple_pools_enable": Mock(return_value=False),
                                "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce821")},
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.NOVA_CONF): CmdOutput(nova_conf)},
            failed_msg="The nova_fsid configured is 6ae21dfe-dd69-472b-bdff-1532d8bce82a but the runtime value is 6ae21dfe-dd69-472b-bdff-1532d8bce821"),
        ValidationScenarioParams(
            scenario_title="scenario failed multiple pool v18", version=Version.V18,
            tested_object_mock_dict={
                "get_pool_uuid_if_exist": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce821")},
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.NOVA_CONF_18): CmdOutput(nova_conf)},
            failed_msg="The nova_fsid configured is 6ae21dfe-dd69-472b-bdff-1532d8bce82a but the runtime value is 6ae21dfe-dd69-472b-bdff-1532d8bce821"),
        ValidationScenarioParams(
            scenario_title="scenario failed multiple pool", version=Version.V22,
            tested_object_mock_dict={
                "get_pool_uuid_if_exist": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce821")},
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.NOVA_CONF): CmdOutput(nova_conf)},
            failed_msg="The nova_fsid configured is 6ae21dfe-dd69-472b-bdff-1532d8bce82a but the runtime value is 6ae21dfe-dd69-472b-bdff-1532d8bce821")]

    @pytest.mark.parametrize("scenario_params", scenario_io_error)
    def test_scenario_io_error(self, scenario_params, tested_object):
        CephValidationTestBase.test_scenario_io_error(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestCephKeysConfigValidator(CephValidationTestBase):
    tested_type = CephKeysConfigValidator
    DynamicPaths.ncs_bm_config_dir_path = '/opt/install/data/cbis-clusters'

    scenario_passed = [ValidationScenarioParams(
        scenario_title="scenario_passed",
        library_mocks_dict={"CephInfo.get_fsid": Mock(return_value="fa850264-d3b2-45ff-9f7c-973bb6edbfe4"),
                            "CephInfo.get_clients_keys_map": Mock(
                                return_value="AQCaJYZlBkEWNBAAg5ao5D246AX7jJMkSx9iug==")},
        tested_object_mock_dict={"get_dict_from_file": Mock(
            return_value={'fsid': 'fa850264-d3b2-45ff-9f7c-973bb6edbfe4',
                          "cephrbd_key": 'AQCaJYZlBkEWNBAAg5ao5D246AX7jJMkSx9iug=='})})]

    scenario_failed = [
        ValidationScenarioParams(
            scenario_title="scenario_failed_different_fsid",
            library_mocks_dict={"CephInfo.get_fsid": Mock(return_value="fa850264-d3b2-45ff-9f7c-973bb6edbfe4")},
            tested_object_mock_dict={
                "get_dict_from_file": Mock(return_value={'fsid': '6ae21dfe-dd69-472b-bdff-1532d8bce821'})},
            failed_msg="Following keys configured value is not as runtime:\n"
                       "FSID: configured - 6ae21dfe-dd69-472b-bdff-1532d8bce821 . "
                       "runtime - fa850264-d3b2-45ff-9f7c-973bb6edbfe4".format(DynamicPaths.ncs_bm_config_dir_path)
        ),
        ValidationScenarioParams(
            scenario_title="scenario_failed_different_key",
            library_mocks_dict={"CephInfo.get_fsid": Mock(return_value="fa850264-d3b2-45ff-9f7c-973bb6edbfe4"),
                                "CephInfo.get_clients_keys_map": Mock(
                                    return_value="BAQCaJYZlBkEWNBAAg5ao5D246AX7jJMkSx9iug==")},
            tested_object_mock_dict={
                "get_dict_from_file": Mock(return_value={'cephfs_key': 'AQCaJYZlMQ4jMRAAgqlKmKMub0xFtBYgucc7pA=='})},
            failed_msg="Following keys configured value is not as runtime:\n"
                       "Client cephfs key : configured - AQCaJYZlMQ4jMRAAgqlKmKMub0xFtBYgucc7pA==, "
                       "runtime - BAQCaJYZlBkEWNBAAg5ao5D246AX7jJMkSx9iug==".format(
                DynamicPaths.ncs_bm_config_dir_path))
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    def test_has_confluence(self, tested_object):
        # Override the func since this val doesn't have a confluence.
        # pls do not copy it! it's only for old validations that do not have a confluence page.
        warnings.warn("No confluence page")


class TestVirshSecretFsidCheck(CephValidationTestBase):
    tested_type = VirshSecretFsidCheck
    cmd_out = """
             UUID                                  Usage.
        --------------------------------------------------------------------------------.
         a1e3eda3-b2a2-4451-8adf-f79383fc5941  ceph client.openstack secret.
        .
    """

    scenario_passed = [
        ValidationScenarioParams(
            scenario_title="scenario_passed",
            cmd_input_output_dict={"sudo virsh secret-list": CmdOutput(cmd_out)},
            library_mocks_dict={"CephInfo.get_fsid": Mock(return_value="a1e3eda3-b2a2-4451-8adf-f79383fc5941")},
            tested_object_mock_dict={
                "get_pool_uuid_if_exist": Mock(return_value="a1e3eda3-b2a2-4451-8adf-f79383fc5941")}),

        ValidationScenarioParams(
            scenario_title="scenario_passed_uuid_none",
            cmd_input_output_dict={"sudo virsh secret-list": CmdOutput(cmd_out)},
            library_mocks_dict={"CephInfo.get_fsid": Mock(return_value="a1e3eda3-b2a2-4451-8adf-f79383fc5941")},
            tested_object_mock_dict={"get_pool_uuid_if_exist": Mock(return_value=None)})
    ]

    scenario_failed = [
        ValidationScenarioParams(
            scenario_title="scenario_failed_fsid_not_in_out",
            cmd_input_output_dict={"sudo virsh secret-list": CmdOutput(cmd_out)},
            library_mocks_dict={"CephInfo.get_fsid": Mock(return_value="fa850264-d3b2-45ff-9f7c-973bb6edbfe4")},
            failed_msg="cluster fsid is not in the virsh secrets list"),

        ValidationScenarioParams(
            scenario_title="scenario_failed_uuid_not_in_out",
            cmd_input_output_dict={"sudo virsh secret-list": CmdOutput(cmd_out)},
            library_mocks_dict={"CephInfo.get_fsid": Mock(return_value="a1e3eda3-b2a2-4451-8adf-f79383fc5941")},
            tested_object_mock_dict={
                "get_pool_uuid_if_exist": Mock(return_value="fa850264-d3b2-45ff-9f7c-973bb6edbfe4")},
            failed_msg="uuid is not in the virsh secrets list")
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    def test_has_confluence(self, tested_object):
        # Override the func since this val doesn't have a confluence.
        # pls do not copy it! it's only for old validations that do not have a confluence page.
        warnings.warn("No confluence page")


class TestFsidInfo(InformatorValidatorTestBase, CephValidationTestBase):
    tested_type = FsidInfo
    scenario_passed = [
        InformatorValidatorScenarioParams(scenario_title="scenario_passed",
                                          expected_system_info="6ae21dfe-dd69-472b-bdff-1532d8bce82a",
                                          library_mocks_dict={"CephInfo.get_fsid": Mock(
                                              return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")})]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        InformatorValidatorTestBase.test_scenario_passed(self, scenario_params, tested_object)

    def test_has_confluence(self, tested_object):
        # Override the func since this val doesn't have a confluence.
        # pls do not copy it! it's only for old validations that do not have a confluence page.
        warnings.warn("No confluence page")


class TestTemplateFSIDCheck(CephValidationTestBase):
    tested_type = TemplateFSIDCheck
    scenario_passed = [ValidationScenarioParams(
        scenario_title="scenario_passed",
        cmd_input_output_dict={"sudo cat {}".format(CephPaths.STORAGE_TEMPLATE_CONF): CmdOutput(
            get_data_from_file("storage-environment.yaml"))},
        library_mocks_dict={"CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")})]

    scenario_io_error = [ValidationScenarioParams(
        scenario_title="scenario_io_error",
        cmd_input_output_dict={"sudo cat {}".format(CephPaths.STORAGE_TEMPLATE_CONF): CmdOutput(
            get_data_from_file("storage-environment.yaml"))},
        library_mocks_dict={"CephInfo.get_fsid": Mock(return_value="")})]

    scenario_failed = [ValidationScenarioParams(
        scenario_title="scenario_failed",
        cmd_input_output_dict={"sudo cat {}".format(CephPaths.STORAGE_TEMPLATE_CONF): CmdOutput(
            get_data_from_file("storage-environment.yaml"))},
        library_mocks_dict={"CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce821")},
        failed_msg="The CephClusterFSID configured is 6ae21dfe-dd69-472b-bdff-1532d8bce82a but the runtime value is "
                   "6ae21dfe-dd69-472b-bdff-1532d8bce821"),
        ValidationScenarioParams(
            scenario_title="scenario_failed missing config_value",
            tested_object_mock_dict={"_get_conf_dict": Mock(return_value={'key': 'value'})},
            library_mocks_dict={"CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce821")},
            failed_msg="CephClusterFSID is not configured in storage-environment.yaml")]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_io_error)
    def test_scenario_io_error(self, scenario_params, tested_object):
        CephValidationTestBase.test_scenario_io_error(self, scenario_params, tested_object)


class TestTemplateOpenStackKeyringCheck(CephValidationTestBase):
    tested_type = TemplateOpenStackKeyringCheck
    scenario_passed = [ValidationScenarioParams(
        scenario_title="scenario_passed",
        cmd_input_output_dict={"sudo cat {}".format(CephPaths.STORAGE_TEMPLATE_CONF): CmdOutput(
            get_data_from_file("storage-environment.yaml"))},
        library_mocks_dict={
            "CephInfo.get_clients_keys_map": Mock(return_value="AQC+a49iTFD0HhAA/Umd1Cb18lNCbogO7imaeA==")})]

    scenario_io_error = [ValidationScenarioParams(
        scenario_title="scenario_io_error",
        cmd_input_output_dict={"sudo cat {}".format(CephPaths.STORAGE_TEMPLATE_CONF): CmdOutput(
            get_data_from_file("storage-environment.yaml"))},
        library_mocks_dict={
            "CephInfo.get_clients_keys_map": Mock(return_value="")})]

    scenario_failed = [
        ValidationScenarioParams(
            scenario_title="scenario_failed",
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.STORAGE_TEMPLATE_CONF): CmdOutput(
                get_data_from_file("storage-environment.yaml"))},
            library_mocks_dict={
                "CephInfo.get_clients_keys_map": Mock(return_value="AQC+a49iTFD0HhAA/Umd1Cb18lNCbogO7imae1==")},
            failed_msg="The CephClientKey configured is AQC+a49iTF....gO7imaeA== but the runtime value is "
                       "AQC+a49iTF....gO7imae1=="),
        ValidationScenarioParams(
            scenario_title="scenario_failed missing config_value",
            tested_object_mock_dict={"_get_conf_dict": Mock(return_value={'key': 'value'})},
            library_mocks_dict={
                "CephInfo.get_clients_keys_map": Mock(return_value="AQC+a49iTFD0HhAA/Umd1Cb18lNCbogO7imaeA==")},
            failed_msg="CephClientKey is not configured in storage-environment.yaml")]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestFSIDPuppetConfValidator(CephValidationTestBase):
    tested_type = FSIDPuppetConfValidator

    service_configs_yaml = """ceph::params::packages: [
    "ceph-base",
    "ceph-mon",
    "ceph-osd"
]
ceph::profile::params::authentication_type: cephx
ceph::profile::params::client_keys: { client.admin: { secret: 'AQCzn49i4jyaGhAAxzLw3fVGDtnhW+xJN5lY1g==', mode: '0600', cap_mon: 'allow *', cap_osd: 'allow *', cap_mds: 'allow *' }, client.bootstrap-osd: { secret: 'AQCzn49i4jyaGhAAxzLw3fVGDtnhW+xJN5lY1g==', keyring_path: '/var/lib/ceph/bootstrap-osd/ceph.keyring', cap_mon: 'allow profile bootstrap-osd' }, client.openstack: { secret: 'AQCzn49i4xWJHBAAET0sX8mjy1i8W5EzteunpA==', mode: '0644', cap_mon: 'allow r', cap_osd: 'allow class-read object_prefix rbd_children, allow rwx pool=volumes, allow rwx pool=backups, allow rwx pool=vms, allow rwx pool=images, allow rwx pool=metrics' } }
ceph::profile::params::cluster_network: 172.17.4.14/24
ceph::profile::params::fsid: 6ae21dfe-dd69-472b-bdff-1532d8bce82a"""

    scenario_passed = [ValidationScenarioParams(
        scenario_title="scenario_passed V.18_5", version=Version.V18_5,
        cmd_input_output_dict={"sudo cat {}".format(CephPaths.PUPPET_CONF_18): CmdOutput(service_configs_yaml)},
        library_mocks_dict={
            "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")}),
        ValidationScenarioParams(
            scenario_title="scenario_passed V.19 tripleo field", version=Version.V19,
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.PUPPET_CONF): CmdOutput(
                '{"tripleo::profile::base::cinder::volume::rbd::cinder_rbd_secret_uuid": "6ae21dfe-dd69-472b-bdff-1532d8bce82a"}')},
            library_mocks_dict={
                "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")}),
        ValidationScenarioParams(
            scenario_title="scenario_passed V.19 nova field", version=Version.V19,
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.PUPPET_CONF): CmdOutput(
                '{"nova::compute::rbd::libvirt_rbd_secret_uuid": "6ae21dfe-dd69-472b-bdff-1532d8bce82a"}')},
            library_mocks_dict={
                "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")}),
        ValidationScenarioParams(
            scenario_title="scenario_passed V.19 ceph_mds field", version=Version.V19,
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.PUPPET_CONF): CmdOutput(
                '{"ceph_mds_ansible_vars": {"fsid":"6ae21dfe-dd69-472b-bdff-1532d8bce82a"}}')},
            library_mocks_dict={
                "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")}),
        ValidationScenarioParams(
            scenario_title="scenario_passed V.19 ceph_mgr field", version=Version.V19,
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.PUPPET_CONF): CmdOutput(
                '{"ceph_mgr_ansible_vars": {"fsid":"6ae21dfe-dd69-472b-bdff-1532d8bce82a"}}')},
            library_mocks_dict={
                "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")}),
        ValidationScenarioParams(
            scenario_title="scenario_passed V.19 ceph_mon field", version=Version.V19,
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.PUPPET_CONF): CmdOutput(
                '{"ceph_mon_ansible_vars": {"fsid":"6ae21dfe-dd69-472b-bdff-1532d8bce82a"}}')},
            library_mocks_dict={
                "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")})]
    scenario_io_error = [ValidationScenarioParams(
        scenario_title="scenario_io_error V.18_5", version=Version.V18_5,
        cmd_input_output_dict={"sudo cat {}".format(CephPaths.PUPPET_CONF_18): CmdOutput(service_configs_yaml)},
        library_mocks_dict={
            "CephInfo.get_fsid": Mock(return_value="")},
        failed_msg="The puppet_fsid configured is 6ae21dfe-dd69-472b-bdff-1532d8bce82a but the runtime value is 6ae21dfe-dd69-472b-bdff-1532d8bce821")]
    scenario_failed = [
        ValidationScenarioParams(
            scenario_title="scenario_failed V.18_5", version=Version.V18_5,
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.PUPPET_CONF_18): CmdOutput(service_configs_yaml)},
            library_mocks_dict={
                "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce821")},
            failed_msg="The puppet_fsid configured is 6ae21dfe-dd69-472b-bdff-1532d8bce82a but the runtime value is 6ae21dfe-dd69-472b-bdff-1532d8bce821"),
        ValidationScenarioParams(
            scenario_title="scenario_failed V.19 tripleo", version=Version.V19,
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.PUPPET_CONF): CmdOutput(
                '{"tripleo::profile::base::cinder::volume::rbd::cinder_rbd_secret_uuid": "6ae21dfe-dd69-472b-bdff-1532d8bce82a"}')},
            library_mocks_dict={
                "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce821")},
            failed_msg="The puppet_fsid configured is 6ae21dfe-dd69-472b-bdff-1532d8bce82a but the runtime value is 6ae21dfe-dd69-472b-bdff-1532d8bce821"),
        ValidationScenarioParams(
            scenario_title="scenario_failed V.19 nova field", version=Version.V19,
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.PUPPET_CONF): CmdOutput(
                '{"nova::compute::rbd::libvirt_rbd_secret_uuid": "6ae21dfe-dd69-472b-bdff-1532d8bce82a"}')},
            library_mocks_dict={
                "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce821")},
            failed_msg="The puppet_fsid configured is 6ae21dfe-dd69-472b-bdff-1532d8bce82a but the runtime value is 6ae21dfe-dd69-472b-bdff-1532d8bce821"),
        ValidationScenarioParams(
            scenario_title="scenario_failed V.19 ceph_mds field", version=Version.V19,
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.PUPPET_CONF): CmdOutput(
                '{"ceph_mds_ansible_vars": {"fsid":"6ae21dfe-dd69-472b-bdff-1532d8bce82a"}}')},
            library_mocks_dict={
                "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce821")},
            failed_msg="The puppet_fsid configured is 6ae21dfe-dd69-472b-bdff-1532d8bce82a but the runtime value is 6ae21dfe-dd69-472b-bdff-1532d8bce821"),
        ValidationScenarioParams(
            scenario_title="scenario_failed V.19 ceph_mgr field", version=Version.V19,
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.PUPPET_CONF): CmdOutput(
                '{"ceph_mgr_ansible_vars": {"fsid":"6ae21dfe-dd69-472b-bdff-1532d8bce82a"}}')},
            library_mocks_dict={
                "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce821")},
            failed_msg="The puppet_fsid configured is 6ae21dfe-dd69-472b-bdff-1532d8bce82a but the runtime value is 6ae21dfe-dd69-472b-bdff-1532d8bce821"),
        ValidationScenarioParams(
            scenario_title="scenario_failed V.19 ceph_mon field", version=Version.V19,
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.PUPPET_CONF): CmdOutput(
                '{"ceph_mon_ansible_vars": {"fsid":"6ae21dfe-dd69-472b-bdff-1532d8bce82a"}}')},
            library_mocks_dict={
                "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce821")},
            failed_msg="The puppet_fsid configured is 6ae21dfe-dd69-472b-bdff-1532d8bce82a but the runtime value is 6ae21dfe-dd69-472b-bdff-1532d8bce821"),
        ValidationScenarioParams(
            scenario_title="scenario_failed V.19 missing field", version=Version.V19,
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.PUPPET_CONF): CmdOutput('{"key": "value"}')},
            library_mocks_dict={
                "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce821")},
            failed_msg="puppet_fsid is not configured in file_name")]
    CephFSIDValidation._get_conf_name = Mock(return_value="file_name")

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_io_error)
    def test_scenario_io_error(self, scenario_params, tested_object):
        CephValidationTestBase.test_scenario_io_error(self, scenario_params, tested_object)


class BaseKeyringConfigCheck(CephValidationTestBase):
    def __init__(self, client):
        self.client = client

    def get_scenario_passed(self):
        return [ValidationScenarioParams(
            scenario_title="scenario_passed",
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.KEYRING_PATH_TEMPLATE.format(self.client)): CmdOutput(
                get_data_from_file("ceph.client.kerying").format(self.client))},
            library_mocks_dict={
                "CephInfo.get_clients_keys_map": Mock(return_value="AQC+a49iTFD0HhAA/Umd1Cb18lNCbogO7imaeA==")})]

    def get_scenario_io_error(self):
        return [ValidationScenarioParams(
            scenario_title="scenario_passed",
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.KEYRING_PATH_TEMPLATE.format(self.client)): CmdOutput(
                get_data_from_file("ceph.client.kerying").format(self.client))},
            library_mocks_dict={
                "CephInfo.get_clients_keys_map": Mock(return_value="")})]

    def get_scenario_failed(self):
        return [ValidationScenarioParams(
            scenario_title="scenario_failed",
            cmd_input_output_dict={"sudo cat {}".format(CephPaths.KEYRING_PATH_TEMPLATE.format(self.client)): CmdOutput(
                get_data_from_file("ceph.client.kerying").format(self.client))},
            library_mocks_dict={
                "CephInfo.get_clients_keys_map": Mock(return_value="AQC+a49iTFD0HhAA/Umd1Cb18lNCbogO7imae1==")},
            failed_msg="The {}_keyring configured is AQC+a49iTF....gO7imaeA== but the runtime value is "
                       "AQC+a49iTF....gO7imae1==".format(self.client))]

    @staticmethod
    def get_scenario_not_fulfilled():
        return [ValidationScenarioParams(
            scenario_title="prerequisite_not_fulfilled",
            library_mocks_dict={
                "CephInfo.is_ceph_used": Mock(return_value=True),
                "KeyringConfigCheck._keyring_file_exists": Mock(return_value=False)
            })]

    @staticmethod
    def get_scenario_fulfilled():
        return [ValidationScenarioParams(
            scenario_title="prerequisite_fulfilled",
            library_mocks_dict={
                "CephInfo.is_ceph_used": Mock(return_value=True),
                "KeyringConfigCheck._keyring_file_exists": Mock(return_value=True)
            })]


class TestKeyringOpenstackConfigCheck(CephValidationTestBase):
    tested_type = KeyringOpenstackConfigCheck
    client = "openstack"

    @pytest.mark.parametrize("scenario_params", BaseKeyringConfigCheck(client).get_scenario_passed())
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", BaseKeyringConfigCheck(client).get_scenario_io_error())
    def test_scenario_io_error(self, scenario_params, tested_object):
        CephValidationTestBase.test_scenario_io_error(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", BaseKeyringConfigCheck(client).get_scenario_failed())
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", BaseKeyringConfigCheck(client).get_scenario_not_fulfilled())
    def test_prerequisite_not_fulfilled(self, scenario_params, tested_object):
        ValidationTestBase.test_prerequisite_not_fulfilled(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", BaseKeyringConfigCheck(client).get_scenario_fulfilled())
    def test_prerequisite_fulfilled(self, scenario_params, tested_object):
        ValidationTestBase.test_prerequisite_fulfilled(self, scenario_params, tested_object)


class TestKeyringAdminConfigCheck(CephValidationTestBase):
    tested_type = KeyringAdminConfigCheck
    client = "admin"

    @pytest.mark.parametrize("scenario_params", BaseKeyringConfigCheck(client).get_scenario_passed())
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", BaseKeyringConfigCheck(client).get_scenario_io_error())
    def test_scenario_io_error(self, scenario_params, tested_object):
        CephValidationTestBase.test_scenario_io_error(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", BaseKeyringConfigCheck(client).get_scenario_failed())
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", BaseKeyringConfigCheck(client).get_scenario_not_fulfilled())
    def test_prerequisite_not_fulfilled(self, scenario_params, tested_object):
        ValidationTestBase.test_prerequisite_not_fulfilled(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", BaseKeyringConfigCheck(client).get_scenario_fulfilled())
    def test_prerequisite_fulfilled(self, scenario_params, tested_object):
        ValidationTestBase.test_prerequisite_fulfilled(self, scenario_params, tested_object)


class TestKeyringCephFSConfigCheck(CephValidationTestBase):
    tested_type = KeyringCephFSConfigCheck
    client = "cephfs"

    @pytest.mark.parametrize("scenario_params", BaseKeyringConfigCheck(client).get_scenario_passed())
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", BaseKeyringConfigCheck(client).get_scenario_io_error())
    def test_scenario_io_error(self, scenario_params, tested_object):
        CephValidationTestBase.test_scenario_io_error(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", BaseKeyringConfigCheck(client).get_scenario_failed())
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", BaseKeyringConfigCheck(client).get_scenario_not_fulfilled())
    def test_prerequisite_not_fulfilled(self, scenario_params, tested_object):
        ValidationTestBase.test_prerequisite_not_fulfilled(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", BaseKeyringConfigCheck(client).get_scenario_fulfilled())
    def test_prerequisite_fulfilled(self, scenario_params, tested_object):
        ValidationTestBase.test_prerequisite_fulfilled(self, scenario_params, tested_object)


class TestKeyringBareMetalConfigCheck(CephValidationTestBase):
    tested_type = KeyringBareMetalConfigCheck
    client = "baremetal.cephfs"

    @pytest.mark.parametrize("scenario_params", BaseKeyringConfigCheck(client).get_scenario_passed())
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", BaseKeyringConfigCheck(client).get_scenario_io_error())
    def test_scenario_io_error(self, scenario_params, tested_object):
        CephValidationTestBase.test_scenario_io_error(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", BaseKeyringConfigCheck(client).get_scenario_failed())
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", BaseKeyringConfigCheck(client).get_scenario_not_fulfilled())
    def test_prerequisite_not_fulfilled(self, scenario_params, tested_object):
        ValidationTestBase.test_prerequisite_not_fulfilled(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", BaseKeyringConfigCheck(client).get_scenario_fulfilled())
    def test_prerequisite_fulfilled(self, scenario_params, tested_object):
        ValidationTestBase.test_prerequisite_fulfilled(self, scenario_params, tested_object)


class TestKeyringCephRBDConfigCheck(CephValidationTestBase):
    tested_type = KeyringCephRBDConfigCheck
    client = "cephrbd"

    @pytest.mark.parametrize("scenario_params", BaseKeyringConfigCheck(client).get_scenario_passed())
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", BaseKeyringConfigCheck(client).get_scenario_io_error())
    def test_scenario_io_error(self, scenario_params, tested_object):
        CephValidationTestBase.test_scenario_io_error(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", BaseKeyringConfigCheck(client).get_scenario_failed())
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", BaseKeyringConfigCheck(client).get_scenario_not_fulfilled())
    def test_prerequisite_not_fulfilled(self, scenario_params, tested_object):
        ValidationTestBase.test_prerequisite_not_fulfilled(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", BaseKeyringConfigCheck(client).get_scenario_fulfilled())
    def test_prerequisite_fulfilled(self, scenario_params, tested_object):
        ValidationTestBase.test_prerequisite_fulfilled(self, scenario_params, tested_object)


class TestKeyringRadosGWConfigCheck(CephValidationTestBase):
    tested_type = KeyringRadosGWConfigCheck
    client = "radosgw"

    @pytest.mark.parametrize("scenario_params", BaseKeyringConfigCheck(client).get_scenario_passed())
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", BaseKeyringConfigCheck(client).get_scenario_io_error())
    def test_scenario_io_error(self, scenario_params, tested_object):
        CephValidationTestBase.test_scenario_io_error(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", BaseKeyringConfigCheck(client).get_scenario_failed())
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", BaseKeyringConfigCheck(client).get_scenario_not_fulfilled())
    def test_prerequisite_not_fulfilled(self, scenario_params, tested_object):
        ValidationTestBase.test_prerequisite_not_fulfilled(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", BaseKeyringConfigCheck(client).get_scenario_fulfilled())
    def test_prerequisite_fulfilled(self, scenario_params, tested_object):
        ValidationTestBase.test_prerequisite_fulfilled(self, scenario_params, tested_object)

class TestCheckCEPHStoreDBSize(CephValidationTestBase):

    tested_type = CheckCEPHStoreDBSize

    cmd = "sudo du -s --block-size=1G /var/lib/ceph/"
    cmd_fsid = "sudo du -s --block-size=1G /var/lib/ceph/6ae21dfe-dd69-472b-bdff-1532d8bce82a"
    out = "1       /var/lib/ceph/"
    failed_out = "41       /var/lib/ceph/"
    unexpected__out = "/var/lib/ceph/"
    version_cbis = "cbis"
    version_ncs = "ncs_bare-metal"

    scenario_passed = [
        ValidationScenarioParams(scenario_title="scenario passed when deployment_type is cbis and the version is 25",
                                 cmd_input_output_dict={cmd_fsid: CmdOutput(out=out)},
                                 library_mocks_dict={
                                     "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a"),
                                     "gs.get_deployment_type": Mock(return_value=version_cbis),
                                     "gs.get_version": Mock(return_value=Version.V25)}
                                 ),
        ValidationScenarioParams(
            scenario_title="scenario passed when deployment_type is ncs and the version is 24.11",
            cmd_input_output_dict={cmd_fsid: CmdOutput(out=out)},
            library_mocks_dict={
                "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a"),
                "gs.get_deployment_type": Mock(return_value=version_ncs),
                "gs.get_version": Mock(return_value=Version.V24_11)}
        ),
        ValidationScenarioParams(scenario_title="scenario passed when deployment_type is cbis and the version below 25",
                                 cmd_input_output_dict={cmd: CmdOutput(out=out)},
                                 library_mocks_dict={
                                     "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a"),
                                     "gs.get_deployment_type": Mock(return_value=version_cbis),
                                     "gs.get_version": Mock(return_value=Version.V24_11)}
                                 ),
        ValidationScenarioParams(scenario_title="scenario passed when deployment_type is ncs and the version below 24.11",
                                 cmd_input_output_dict={cmd: CmdOutput(out=out)},
                                 library_mocks_dict={
                                     "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a"),
                                     "gs.get_deployment_type": Mock(return_value=version_ncs),
                                     "gs.get_version": Mock(return_value=Version.V22)}
                                 )
    ]
    scenario_failed = [
        ValidationScenarioParams(scenario_title="scenario failed",
                                 cmd_input_output_dict={cmd: CmdOutput(out=failed_out)},
                                 library_mocks_dict={
                                     "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a"),
                                     "gs.get_deployment_type": Mock(return_value=version_cbis),
                                     "gs.get_version": Mock(return_value=Version.V24_11)}
                                 )]
    scenario_unexpected_system_output = [
        ValidationScenarioParams(scenario_title="unexpected output returned",
                                 cmd_input_output_dict={cmd: CmdOutput(out=unexpected__out)},
                                 library_mocks_dict={
                                     "CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a"),
                                     "gs.get_deployment_type": Mock(return_value=version_cbis),
                                     "gs.get_version": Mock(return_value=Version.V24_11)}
                                 )
                                 ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        CephValidationTestBase.test_scenario_unexpected_system_output(self, scenario_params, tested_object)
