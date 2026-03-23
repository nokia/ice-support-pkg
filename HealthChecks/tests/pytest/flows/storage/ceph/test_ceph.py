from __future__ import absolute_import
import warnings

import pytest
from tests.pytest.tools.versions_alignment import Mock
from tests.pytest.tools.versions_alignment import nested
from flows.Storage.ceph.Ceph import *
from flows.Storage.ceph.CephInfo import CephPaths
from tests.pytest.pytest_tools.operator.test_operator import CmdOutput
from tests.pytest.pytest_tools.operator.test_validation_base import ValidationTestBase, ValidationScenarioParams
import os
from tools import sys_parameters
from tools.global_enums import Deployment_type, Objectives, Version


def get_data_from_file(file_name):
    current_dir_path = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(current_dir_path, 'inputs', file_name)
    with open(path, 'r') as f:
        return f.read()


class CephValidationTestBase(ValidationTestBase):
    scenario_io_error = []
    scenario_prerequisite_not_fulfilled = [ValidationScenarioParams("prerequisite_not_fulfilled",
                                                                    library_mocks_dict={
                                                                        "CephInfo.is_ceph_used": Mock(
                                                                            return_value=False)
                                                                    })]
    scenario_prerequisite_fulfilled = [ValidationScenarioParams("prerequisite_fulfilled",
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
        self._init_validation_object(tested_object, scenario_params)

        context_managers = self._prepare_patches_list(tested_object)

        # python 3 not support nested
        with nested(*context_managers):
            with pytest.raises(IOError):
                tested_object.is_validation_passed()


class TestIsOSDsWeightOK(CephValidationTestBase):
    tested_type = IsOSDsWeightOK
    validation_cmd = "sudo ceph osd df -f json"
    out_templete = get_data_from_file('ceph_osd_df.txt')

    scenario_passed = [
        ValidationScenarioParams(scenario_title="OSD weight are ok",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(
                                     out=out_templete.format(kb='803442688'))})
    ]
    scenario_failed = [
        ValidationScenarioParams(scenario_title="OSD weight not in acceptable range",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(
                                     out=out_templete.format(kb='854442688'))}),
        ValidationScenarioParams(scenario_title="OSD size is 0",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(
                                     out=out_templete.format(kb='0'))}),
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    def _init_mocks(self, tested_object):
        sys_parameters.get_deployment_type = Mock(return_value=Deployment_type.CBIS)


class TestCephHasConfFile(CephValidationTestBase):
    tested_type = CephHasConfFile

    scenario_passed = [ValidationScenarioParams(scenario_title="conf exists",
                                                additional_parameters_dict={"file_exist": True},
                                                library_mocks_dict={
                                                    "CephInfo.is_ceph_used": Mock(return_value=True)})]

    scenario_failed = [ValidationScenarioParams(scenario_title="conf doesn't exit",
                                                additional_parameters_dict={"file_exist": False},
                                                library_mocks_dict={
                                                    "CephInfo.is_ceph_used": Mock(return_value=True)}
                                                )]

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

    def _init_mocks(self, tested_object):
        super(TestCephHasConfFile, self)._init_mocks(tested_object)
        CephValidationTestBase._init_mocks(self, tested_object)
        if not self.additional_parameters_dict:
            return
        tested_object.file_utils.is_file_exist = Mock()
        tested_object.file_utils.is_file_exist.return_value = self.additional_parameters_dict['file_exist']


class TestCephOsdTreeWorks(CephValidationTestBase):
    tested_type = CephOsdTreeWorks

    scenario_passed = [
        ValidationScenarioParams("cmd works",
                                 cmd_input_output_dict={"sudo ceph osd tree": CmdOutput("", return_code=0)})
    ]

    scenario_failed = [
        ValidationScenarioParams("cmd doesn't work",
                                 cmd_input_output_dict={"sudo ceph osd tree": CmdOutput("", return_code=1)})
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


class TestIsCephHealthOk(CephValidationTestBase):
    tested_type = IsCephHealthOk

    scenario_passed = [
        ValidationScenarioParams("passed",
                                 cmd_input_output_dict={
                                     "sudo ceph health -f json": CmdOutput('{"checks":{},"status":"HEALTH_OK"}')
                                 }),
        ValidationScenarioParams("passed with summary",
                                 cmd_input_output_dict={
                                     "sudo ceph health -f json": CmdOutput('{"summary":{},"status":"HEALTH_OK"}')
                                 })
    ]

    scenario_failed = [
        ValidationScenarioParams("failed",
                                 cmd_input_output_dict={
                                     "sudo ceph health -f json": CmdOutput('{"checks":{},"status":"HEALTH_NOT_OK"}')
                                 }),
        ValidationScenarioParams("failed with summary",
                                 cmd_input_output_dict={
                                     "sudo ceph health -f json": CmdOutput('{"summary":{},"status":"HEALTH_NOT_OK"}')
                                 })
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


class TestCheckVarLibCephDir(CephValidationTestBase):
    tested_type = CheckVarLibCephDir

    scenario_passed = [ValidationScenarioParams("Directory exists",
                                                additional_parameters_dict={"dir_exist": True},
                                                library_mocks_dict={"CephInfo.is_ceph_used": Mock(return_value=True)})]

    scenario_failed = [ValidationScenarioParams("Directory doesn't exit",
                                                additional_parameters_dict={"dir_exist": False},
                                                library_mocks_dict={"CephInfo.is_ceph_used": Mock(return_value=True)})]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    def _init_mocks(self, tested_object):
        super(TestCheckVarLibCephDir, self)._init_mocks(tested_object)
        CephValidationTestBase._init_mocks(self, tested_object)
        if not self.additional_parameters_dict:
            return
        tested_object.file_utils.is_dir_exist = Mock()
        tested_object.file_utils.is_dir_exist.return_value = self.additional_parameters_dict['dir_exist']


class TestIsCephOSDsNearFull(CephValidationTestBase):
    tested_type = IsCephOSDsNearFull

    osd_df = """{{
    "nodes": [{{
            "id": 3,
            "name": "osd.3",
            "kb_used": 172745344,
            "kb_avail": 631745920,
            "utilization": 25,
            "var": 0.989641,
            "pgs": 193
        }}, {{
            "id": 7,
            "name": "osd.7",
            "kb_used": 161592452,
            "kb_avail": 705824384,
            "utilization": {},
            "var": 0.858590,
            "pgs": 175
        }}, {{
            "id": 2,
            "name": "osd.2",
            "kb_used": 205028864,
            "kb_avail": 599462400,
            "utilization": {},
            "var": 1.174590,
            "pgs": 193
        }}, {{
            "id": 6,
            "name": "osd.6",
            "kb_used": 193240196,
            "kb_avail": 674176640,
            "utilization": 20,
            "var": 1.026744,
            "pgs": 196
        }}
    ],
    "stray": [],
    "summary": {{
        "total_kb": 6687632400,
        "total_kb_used": 1451041424,
        "total_kb_avail": 5236590976,
        "average_utilization": 21.697386,
        "min_var": 0.858590,
        "max_var": 1.174590,
        "dev": 1.868692
    }}
}}"""

    scenario_passed = [
        ValidationScenarioParams("passed",
                                 cmd_input_output_dict={
                                     "sudo ceph osd df -f json ": CmdOutput(
                                         osd_df.format(20, 20))
                                 })
    ]

    scenario_failed = [
        ValidationScenarioParams("failed warning",
                                 cmd_input_output_dict={
                                     "sudo ceph osd df -f json ": CmdOutput(
                                         osd_df.format(82, 20))
                                 },
                                 failed_msg="There are OSDs disk usage near or already over the limit.\n"
                                            "This indiciates there is a risk ahead or already materialized, "
                                            "so need to react fast for ceph storage.\n"
                                            "Here is a list of problematic osds in this environment "
                                            "currently over limit: \n 80% : WARNING\n"
                                            "osd.7     82"),
        ValidationScenarioParams("failed criticat",
                                 cmd_input_output_dict={
                                     "sudo ceph osd df -f json ": CmdOutput(
                                         osd_df.format(82, 95))
                                 },
                                 failed_msg="There are OSDs disk usage near or already over the limit.\n"
                                            "This indiciates there is a risk ahead or already materialized, "
                                            "so need to react fast for ceph storage.\n"
                                            "Here is a list of problematic osds in this environment currently "
                                            "over limit: \n 90% : CRITICAL\n"
                                            "osd.7     82        \nosd.2     95")
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestMonitorsCount(CephValidationTestBase):
    tested_type = MonitorsCount

    ceph_mon_passed = """epoch 1
fsid cb6e12f1-cff1-4623-bb8a-9b9450b98f43
last_changed 2023-05-02T14:49:07.071304+0000
created 2023-05-02T14:49:07.071304+0000
min_mon_release 17 (quincy)
election_strategy: 1
0: [v2:172.17.4.2:3300/0,v1:172.17.4.2:6789/0] mon.controller-0
1: [v2:172.17.4.5:3300/0,v1:172.17.4.5:6789/0] mon.controller-1
2: [v2:172.17.4.6:3300/0,v1:172.17.4.6:6789/0] mon.controller-2
dumped monmap epoch 1"""

    ceph_mon_status = """{{
    "name": "overcloud-controller-pl-8004-i14-0",
    "monmap": {{
        "mons": [{{
                "rank": 0,
                "name": "overcloud-controller-pl-8004-i14-1"
            }}, {{
                "rank": 1,
                "name": "overcloud-controller-pl-8004-i14-0"
            }}{}
        ]
    }}
}}"""

    ceph_mon_status_newer_version_pass = """[{
    "daemon_name": "mon.osaka-config4-masterbm-0",
    "daemon_type": "mon",
    "service_name": "mon"
    }, 
    {
    "daemon_name": "mon.osaka-config4-masterbm-1",
    "daemon_type": "mon",
    "service_name": "mon"
    }, 
    {
    "daemon_name": "mon.osaka-config4-masterbm-2",
    "daemon_type": "mon",
    "service_name": "mon"
}]"""

    ceph_mon_status_newer_version_fail = """[{
        "daemon_name": "mon.osaka-config4-masterbm-0",
        "daemon_type": "mon",
        "service_name": "mon"
        }, 
        {
        "daemon_name": "mon.osaka-config4-masterbm-1",
        "daemon_type": "mon",
        "service_name": "mon"
        }]"""

    ceph_mon_status_passed = ceph_mon_status.format(', {"rank": 2, "name": "overcloud-controller-pl-8004-i14-2"}')
    ceph_mon_status_failed = ceph_mon_status.format("")

    scenario_passed = [
        ValidationScenarioParams("passed for version < 24.11",
                                 cmd_input_output_dict={
                                     "sudo ls /var/lib/ceph/mon": CmdOutput("ceph-controller-0"),
                                     "sudo ceph mon dump": CmdOutput(ceph_mon_passed),
                                     "sudo ceph daemon mon.controller-0 mon_status": CmdOutput(ceph_mon_status_passed)
                                 },
                                 library_mocks_dict={"gs.get_deployment_type": Mock(return_value=Deployment_type.NCS_OVER_BM)},
                                 version=Version.V24_7),
        ValidationScenarioParams("passed for version >= 24.11",
                                 cmd_input_output_dict={
                                     "sudo ceph orch ps --daemon_type mon -f json-pretty": CmdOutput(ceph_mon_status_newer_version_pass)
                                 },
                                 library_mocks_dict={"gs.get_deployment_type": Mock(return_value=Deployment_type.NCS_OVER_BM)},
                                 version=Version.V24_11)
    ]

    scenario_failed = [
        ValidationScenarioParams("failed for version < 24.11",
                                 cmd_input_output_dict={
                                     "sudo ls /var/lib/ceph/mon": CmdOutput("ceph-controller-0"),
                                     "sudo ceph mon dump": CmdOutput(ceph_mon_passed),
                                     "sudo ceph daemon mon.controller-0 mon_status": CmdOutput(ceph_mon_status_failed)
                                 },
                                 library_mocks_dict={"gs.get_deployment_type": Mock(return_value=Deployment_type.NCS_OVER_BM)},
                                 version=Version.V24_7),
        ValidationScenarioParams("failed for version >= 24.11",
                                 cmd_input_output_dict={
                                     "sudo ceph orch ps --daemon_type mon -f json-pretty": CmdOutput(ceph_mon_status_newer_version_fail)
                                 },
                                 library_mocks_dict={"gs.get_deployment_type": Mock(return_value=Deployment_type.NCS_OVER_BM)},
                                 version=Version.V24_11)
    ]

    scenario_unexpected_system_output = [
        ValidationScenarioParams("empty mon list",
                                 cmd_input_output_dict={
                                     "sudo ls /var/lib/ceph/mon": CmdOutput(""),
                                     "sudo ceph mon dump": CmdOutput(ceph_mon_passed)
                                 },
                                 library_mocks_dict={"gs.get_deployment_type": Mock(return_value=Deployment_type.NCS_OVER_BM)},
                                 version=Version.V24_7)
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_unexpected_system_output(self, scenario_params, tested_object)

    def test_has_confluence(self, tested_object):
        # Override the func since this val doesn't have a confluence.
        # pls do not copy it! it's only for old validations that do not have a confluence page.
        warnings.warn("No confluence page")


class TestCheckVarLibCephDirOwner(CephValidationTestBase):
    tested_type = CheckVarLibCephDirOwner

    scenario_passed = [
        ValidationScenarioParams("passed",
                                 cmd_input_output_dict={
                                     "sudo stat -c '%U %G' /var/lib/ceph/": CmdOutput("ceph ceph")})
    ]

    scenario_failed = [
        ValidationScenarioParams("passed",
                                 cmd_input_output_dict={
                                     "sudo stat -c '%U %G' /var/lib/ceph/": CmdOutput("not_ceph not_ceph")})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestOsdHostsVsCephHosts(CephValidationTestBase):
    tested_type = OsdHostsVsCephHosts

    ceph_hosts = """-9       1.55698     host overcloud-ovscompute-0
-7       1.55698     host overcloud-ovscompute-1
-5       1.55698     host overcloud-sriovperformancecompute-0
-3       1.55698     host overcloud-sriovperformancecompute-{}"""

    ceph_fast_hosts = """-28        2.78204     host fast-overcloud-storage-pl-8004-i14-0
-30        2.78204     host fast-overcloud-storage-pl-8004-i14-1
-29        2.78204     host fast-overcloud-storage-pl-8004-i14-{}
 -5       20.96399     host common-overcloud-storage-pl-8004-i14-0
 -7       20.96399     host common-overcloud-storage-pl-8004-i14-1
 -3       20.96399     host common-overcloud-storage-pl-8004-i14-2"""

    ceph_common_host = """ -5       20.96399     host common-overcloud-storage-pl-8004-i14-0
 -7       20.96399     host common-overcloud-storage-pl-8004-i14-1
 -3       20.96399     host common-overcloud-storage-pl-8004-i14-{}"""

    scenario_passed = [
        ValidationScenarioParams("passed",
                                 cmd_input_output_dict={
                                     "sudo ceph osd tree | grep \"root fast\"": {"manager-0": CmdOutput("")},
                                     "sudo ceph osd tree | grep \"root common\"": {"manager-0": CmdOutput("")},
                                     "sudo ceph osd tree | grep -i host": CmdOutput(ceph_hosts.format(1))
                                 },
                                 library_mocks_dict={
                                     "CephInfo.get_relevant_roles": Mock([Objectives.ONE_MANAGER])
                                 },
                                 additional_parameters_dict={"common": False}),
        ValidationScenarioParams("passed fast common",
                                 cmd_input_output_dict={
                                     "sudo ceph osd tree | grep \"root fast\"": {"manager-0": CmdOutput(
                                         "echo -13          5.56403  root fast")},
                                     "sudo ceph osd tree | grep \"root common\"": {"manager-0": CmdOutput(
                                         "echo -13          5.56403  root common")},
                                     "sudo ceph osd tree | grep -i host": CmdOutput(ceph_fast_hosts.format(2))
                                 },
                                 library_mocks_dict={
                                     "CephInfo.get_relevant_roles": Mock([Objectives.ONE_MANAGER])
                                 },
                                 additional_parameters_dict={"common": True}),
        ValidationScenarioParams("passed common",
                                 cmd_input_output_dict={
                                     "sudo ceph osd tree | grep \"root fast\"": {"manager-0": CmdOutput("")},
                                     "sudo ceph osd tree | grep \"root common\"": {"manager-0": CmdOutput(
                                         "echo -13          5.56403  root common")},
                                     "sudo ceph osd tree | grep -i host": CmdOutput(ceph_common_host.format(2))
                                 },
                                 library_mocks_dict={
                                     "CephInfo.get_relevant_roles": Mock([Objectives.ONE_MANAGER])
                                 },
                                 additional_parameters_dict={"common": True})
    ]

    scenario_failed = [
        ValidationScenarioParams("failed",
                                 cmd_input_output_dict={
                                     "sudo ceph osd tree | grep \"root fast\"": {"manager-0": CmdOutput("")},
                                     "sudo ceph osd tree | grep \"root common\"": {"manager-0": CmdOutput("")},
                                     "sudo ceph osd tree | grep -i host": CmdOutput(ceph_hosts.format(2))
                                 },
                                 library_mocks_dict={
                                     "CephInfo.get_relevant_roles": Mock([Objectives.ONE_MANAGER])
                                 },
                                 additional_parameters_dict={"common": False}),
        ValidationScenarioParams("not passed fast common",
                                 cmd_input_output_dict={
                                     "sudo ceph osd tree | grep \"root fast\"": {"manager-0": CmdOutput(
                                         "echo -13          5.56403  root fast")},
                                     "sudo ceph osd tree | grep \"root common\"": {"manager-0": CmdOutput(
                                         "echo -13          5.56403  root common")},
                                     "sudo ceph osd tree | grep -i host": CmdOutput(ceph_fast_hosts.format(3))
                                 },
                                 library_mocks_dict={
                                     "CephInfo.get_relevant_roles": Mock([Objectives.ONE_MANAGER])
                                 },
                                 additional_parameters_dict={"common": True}),
        ValidationScenarioParams("failed common",
                                 cmd_input_output_dict={
                                     "sudo ceph osd tree | grep \"root fast\"": {"manager-0": CmdOutput("")},
                                     "sudo ceph osd tree | grep \"root common\"": {"manager-0": CmdOutput(
                                         "echo -13          5.56403  root common")},
                                     "sudo ceph osd tree | grep -i host": CmdOutput(ceph_common_host.format(3))
                                 },
                                 library_mocks_dict={
                                     "CephInfo.get_relevant_roles": Mock([Objectives.ONE_MANAGER])
                                 },
                                 additional_parameters_dict={"common": True})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    def _init_mocks(self, tested_object):
        super(TestOsdHostsVsCephHosts, self)._init_mocks(tested_object)
        CephValidationTestBase._init_mocks(self, tested_object)
        if not self.additional_parameters_dict:
            return
        if not self.additional_parameters_dict["common"]:
            sys_parameters.get_host_executor_factory.return_value.get_host_executors_by_roles.return_value = {
                'overcloud-ovscompute-0': [], 'overcloud-ovscompute-1': [], 'overcloud-sriovperformancecompute-0': [],
                'overcloud-sriovperformancecompute-1': []}
        else:
            sys_parameters.get_host_executor_factory.return_value.get_host_executors_by_roles.return_value = {
                'overcloud-storage-pl-8004-i14-0': [], 'overcloud-storage-pl-8004-i14-1': [],
                'overcloud-storage-pl-8004-i14-2': []}


class TestMonitorsHealth(CephValidationTestBase):
    tested_type = MonitorsHealth

    ceph_mon_status = """ ceph-mon@overcloud-controller-0.service - Ceph Monitor
   Loaded: loaded (/etc/systemd/system/ceph-mon@.service; enabled; vendor preset: disabled)
   Active: active ({}) since Thu 2022-05-26 12:52:00 UTC; 1 months 14 days ago
 Main PID: 84755 (docker-current)
   CGroup: /system.slice/system-ceph-mon.slice/ceph-mon@overcloud-controller-0.service
           -84755 /usr/bin/docker-current run --rm --name ceph-mon-overcloud-controller-0 --memory=3...

Warning: Journal has been rotated since unit was started. Log output is incomplete or unavailable.
"""

    scenario_passed = [
        ValidationScenarioParams("passed",
                                 tested_object_mock_dict={"get_host_name": Mock(return_value="dummy_host_1")},
                                 cmd_input_output_dict={
                                     "systemctl status ceph-mon@dummy_host_1.service": CmdOutput(
                                         ceph_mon_status.format("running"))
                                 })
    ]

    scenario_failed = [
        ValidationScenarioParams("failed",
                                 tested_object_mock_dict={"get_host_name": Mock(return_value="dummy_host_1")},
                                 cmd_input_output_dict={
                                     "systemctl status ceph-mon@dummy_host_1.service": CmdOutput(
                                         ceph_mon_status.format("exited"))
                                 })
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestMonitorsHealthCephAdm(CephValidationTestBase):
    tested_type = MonitorsHealthCephAdm

    ceph_mon_status = """[{{
    "container_id": "5f290273bdbb",
    "container_image_digests": [
      "172.32.40.1:8787/ceph/daemon@sha256:7a0587d3e8ca91378c827bb5c6ea666f51d2ec571d25b6035816b58579824c00"
    ],
    "container_image_id": "6a1af4930b07261c2f5474e8d21d424d017a1369d060f6796adb329390567f0b",
    "container_image_name": "172.32.40.1:8787/ceph/daemon:reef-rockylinux-8-x86_64",
    "cpu_percentage": "1.19%",
    "created": "2024-06-26T09:35:03.997589Z",
    "daemon_id": "osaka-config4-masterbm-2",
    "daemon_name": "mon.osaka-config4-masterbm-2",
    "daemon_type": "mon",
    "hostname": "osaka-config4-masterbm-2",
    "is_active": false,
    "last_refresh": "2024-07-09T12:09:38.624410Z",
    "memory_request": 2147483648,
    "memory_usage": 458647142,
    "ports": [],
    "service_name": "mon",
    "started": "2024-06-27T10:31:24.556163Z",
    "status": 1,
    "status_desc": "{}",
    "version": "18.2.2"
    }}]"""

    get_host_executor_factory_mock = Mock()
    get_host_executor_factory_mock.return_value.get_host_executors_by_roles = Mock(return_value={'osaka-config4-masterbm-2': []})

    scenario_passed = [
        ValidationScenarioParams("passed",
                                 library_mocks_dict={"gs.get_host_executor_factory": get_host_executor_factory_mock},
                                 cmd_input_output_dict={
                                     "sudo ceph orch ps --daemon_type mon -f json-pretty": CmdOutput(ceph_mon_status.format('running'))
                                 },
                                 version=Version.V24_11)
    ]

    scenario_failed = [
        ValidationScenarioParams("failed",
                                 library_mocks_dict={"gs.get_host_executor_factory": get_host_executor_factory_mock},
                                 cmd_input_output_dict={"sudo ceph orch ps --daemon_type mon -f json-pretty": CmdOutput(
                                         ceph_mon_status.format("pending"))
                                 },
                                 version=Version.V24_11)
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestValidateCephTempFilesCount(CephValidationTestBase):
    tested_type = ValidateCephTempFilesCount

    scenario_passed = [
        ValidationScenarioParams("passed",
                                 cmd_input_output_dict={
                                     "sudo find /var/lib/ceph/tmp/ -type d -empty | wc -l": CmdOutput("100")
                                 })
    ]

    scenario_failed = [
        ValidationScenarioParams("failed",
                                 cmd_input_output_dict={
                                     "sudo find /var/lib/ceph/tmp/ -type d -empty | wc -l": CmdOutput("905")
                                 })
    ]

    scenario_unexpected_system_output = [
        ValidationScenarioParams("unexpected",
                                 cmd_input_output_dict={
                                     "sudo find /var/lib/ceph/tmp/ -type d -empty | wc -l": CmdOutput("905 h")
                                 })
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_unexpected_system_output(self, scenario_params, tested_object)

    def test_has_confluence(self, tested_object):
        # Override the func since this val doesn't have a confluence.
        # pls do not copy it! it's only for old validations that do not have a confluence page.
        warnings.warn("No confluence page")


class TestCheckMultipleMondirs(CephValidationTestBase):
    tested_type = CheckMultipleMondirs

    scenario_passed = [
        ValidationScenarioParams("passed for version < 24.11",
                                 cmd_input_output_dict={
                                     "sudo ls /var/lib/ceph/mon/": CmdOutput("ceph-overcloud-controller-0")
                                 },
                                 version=Version.V22),
        ValidationScenarioParams("passed for version >= 24.11",
                                 cmd_input_output_dict={
                                     "sudo ls /var/lib/ceph/6ae21dfe-dd69-472b-bdff-1532d8bce82a/ | grep mon.$(hostname)": CmdOutput("mon.cluster-masterbm-2")
                                 },
                                 library_mocks_dict={"CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")},
                                 version=Version.V24_11)
    ]

    scenario_failed = [
        ValidationScenarioParams("failed for version < 24.11 - multiple mon dirs",
                                 cmd_input_output_dict={
                                     "sudo ls /var/lib/ceph/mon/": CmdOutput("ceph-overcloud-controller-0 "
                                                                             "ceph-overcloud-controller-0")
                                 },
                                 version=Version.V22),
        ValidationScenarioParams("failed for version >= 24.11 - multiple mon dirs",
                                 cmd_input_output_dict={
                                     "sudo ls /var/lib/ceph/6ae21dfe-dd69-472b-bdff-1532d8bce82a/ | grep mon.$(hostname)": CmdOutput("mon.cluster-masterbm-1 "
                                                                                                                                     "mon.cluster-masterbm-2")
                                 },
                                 library_mocks_dict={"CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")},
                                 version=Version.V24_11)
    ]

    scenario_unexpected_system_output = [
        ValidationScenarioParams("unexpected for version < 24.11 - multiple mon dirs",
                                 cmd_input_output_dict={
                                     "sudo ls /var/lib/ceph/mon/": CmdOutput("")
                                 },
                                 version=Version.V22),
        ValidationScenarioParams("unexpected for version >= 24.11 - no mon dirs",
                                 cmd_input_output_dict={
                                     "sudo ls /var/lib/ceph/6ae21dfe-dd69-472b-bdff-1532d8bce82a/ | grep mon.$(hostname)": CmdOutput("")
                                 },
                                 library_mocks_dict={"CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")},
                                 version=Version.V24_11)
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_unexpected_system_output(self, scenario_params, tested_object)


class TestCephMgrStandbyCheck(CephValidationTestBase):
    tested_type = CephMgrStandbyCheck

    ceph_json_2_standbys = """{
        "mgrmap": {
            "standbys": [
                {
                    "gid": 8567,
                    "name": "overcloud-controller-pl-8004-i14-2"
                },
                {
                    "gid": 18535,
                    "name": "overcloud-controller-pl-8004-i14-0"
                }
            ]
        }
    }"""

    ceph_json_1_standby = """{
        "mgrmap": {
            "standbys": [
                {
                    "gid": 8567,
                    "name": "overcloud-controller-pl-8004-i14-2"
                }
            ]
        }
    }"""

    scenario_passed = [
        ValidationScenarioParams("passed standbys",
                                 cmd_input_output_dict={
                                     "sudo ceph -s -f json": CmdOutput(ceph_json_2_standbys)
                                 },
                                 tested_object_mock_dict={"get_host_roles": Mock(return_value=[Objectives.MASTERS])}),
        ValidationScenarioParams("passed num_standbys",
                                 cmd_input_output_dict={
                                     "sudo ceph -s -f json": CmdOutput('{"mgrmap": {"num_standbys": 2}}')
                                 },
                                 tested_object_mock_dict={"get_host_roles": Mock(return_value=[Objectives.MASTERS])})
    ]

    scenario_failed = [
        ValidationScenarioParams("failed standbys",
                                 cmd_input_output_dict={
                                     "sudo ceph -s -f json": CmdOutput(ceph_json_1_standby)
                                 },
                                 tested_object_mock_dict={"get_host_roles": Mock(return_value=[Objectives.MASTERS])}),
        ValidationScenarioParams("failed num_standbys",
                                 cmd_input_output_dict={
                                     "sudo ceph -s -f json": CmdOutput('{"mgrmap": {"num_standbys": 1}}')
                                 },
                                 tested_object_mock_dict={"get_host_roles": Mock(return_value=[Objectives.MASTERS])})
    ]

    scenario_prerequisite_fulfilled = [ValidationScenarioParams("prerequisite_fulfilled master",
                                                                library_mocks_dict={
                                                                    "gs.is_ncs_central": Mock(return_value=False),
                                                                    "gs.get_deployment_type": Mock(
                                                                        return_value=Deployment_type.NCS_OVER_BM),
                                                                    "CephInfo.is_ceph_used": Mock(
                                                                        return_value=True)
                                                                },
                                                                tested_object_mock_dict={"get_host_roles": Mock(
                                                                    return_value=[Objectives.MASTERS])}),
                                       ValidationScenarioParams("prerequisite_fulfilled cbis",
                                                                library_mocks_dict={
                                                                    "gs.is_ncs_central": Mock(return_value=False),
                                                                    "gs.get_deployment_type": Mock(
                                                                        return_value=Deployment_type.CBIS),
                                                                    "CephInfo.is_ceph_used": Mock(
                                                                        return_value=True)
                                                                },
                                                                tested_object_mock_dict={"get_host_roles": Mock(
                                                                    return_value=[Objectives.CONTROLLERS])}),
                                       ValidationScenarioParams("prerequisite_fulfilled manager+master",
                                                                library_mocks_dict={
                                                                    "gs.is_ncs_central": Mock(return_value=False),
                                                                    "gs.get_deployment_type": Mock(
                                                                        return_value=Deployment_type.NCS_OVER_BM),
                                                                    "CephInfo.is_ceph_used": Mock(
                                                                        return_value=True)
                                                                },
                                                                tested_object_mock_dict={"get_host_roles": Mock(
                                                                    return_value=[Objectives.MASTERS,
                                                                                  Objectives.MANAGERS])}),
                                       ValidationScenarioParams("prerequisite_fulfilled central and manager",
                                                                library_mocks_dict={
                                                                    "gs.get_deployment_type": Mock(
                                                                        return_value=Deployment_type.NCS_OVER_BM),
                                                                    "gs.is_ncs_central": Mock(return_value=True),
                                                                    "CephInfo.is_ceph_used": Mock(
                                                                        return_value=True)
                                                                },
                                                                tested_object_mock_dict={"get_host_roles": Mock(
                                                                    return_value=[Objectives.MANAGERS])}),
                                       ValidationScenarioParams("prerequisite_fulfilled central and master",
                                                                library_mocks_dict={
                                                                    "gs.get_deployment_type": Mock(
                                                                        return_value=Deployment_type.NCS_OVER_BM),
                                                                    "gs.is_ncs_central": Mock(return_value=True),
                                                                    "CephInfo.is_ceph_used": Mock(
                                                                        return_value=True)
                                                                },
                                                                tested_object_mock_dict={"get_host_roles": Mock(
                                                                    return_value=[Objectives.MASTERS])}),
                                       ValidationScenarioParams("prerequisite_fulfilled not central and master",
                                                                library_mocks_dict={
                                                                    "gs.get_deployment_type": Mock(
                                                                        return_value=Deployment_type.NCS_OVER_BM),
                                                                    "gs.is_ncs_central": Mock(return_value=False),
                                                                    "CephInfo.is_ceph_used": Mock(
                                                                        return_value=True)
                                                                },
                                                                tested_object_mock_dict={"get_host_roles": Mock(
                                                                    return_value=[Objectives.MASTERS])})]

    scenario_prerequisite_not_fulfilled = [ValidationScenarioParams("prerequisite_not_fulfilled ceph not used",
                                                                    library_mocks_dict={
                                                                        "gs.get_deployment_type": Mock(
                                                                            return_value=Deployment_type.NCS_OVER_BM),
                                                                        "CephInfo.is_ceph_used": Mock(
                                                                            return_value=False),
                                                                        "gs.is_ncs_central": Mock(return_value=False)},
                                                                    tested_object_mock_dict={"get_host_roles": Mock(
                                                                        return_value=[Objectives.MASTERS])}),
                                           ValidationScenarioParams("prerequisite_not_fulfilled manager not centrar",
                                                                    library_mocks_dict={
                                                                        "gs.get_deployment_type": Mock(
                                                                            return_value=Deployment_type.NCS_OVER_BM),
                                                                        "gs.is_ncs_central": Mock(return_value=False),
                                                                        "CephInfo.is_ceph_used": Mock(
                                                                            return_value=True)
                                                                    },
                                                                    tested_object_mock_dict={"get_host_roles": Mock(
                                                                        return_value=[Objectives.MANAGERS])})]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_prerequisite_not_fulfilled)
    def test_prerequisite_not_fulfilled(self, scenario_params, tested_object):
        CephValidationTestBase.test_prerequisite_not_fulfilled(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_prerequisite_fulfilled)
    def test_prerequisite_fulfilled(self, scenario_params, tested_object):
        CephValidationTestBase.test_prerequisite_fulfilled(self, scenario_params, tested_object)


class TestAreAllOSDsRunningOnNCS(CephValidationTestBase):
    tested_type = AreAllOSDsRunningOnNCS

    docker_ps = """a29d3d85fb56  172.31.0.2:8787/ceph/daemon  2 weeks ago  Up 2 weeks ago  ceph-osd-1
2fc966d0d5d5  172.31.0.2:8787/ceph/daemon   2 weeks ago  Up 2 weeks ago  ceph-osd-2"""

    ceph_orch_ps = """osd.1   hawaii-cluster-storagebm-0         running (18h)    10m ago  18h     529M    29.2G  18.2.2   f3e4fc32e0d7  e2786c2b7b84  .
osd.2   hawaii-cluster-storagebm-0         running (18h)    10m ago  18h     298M    29.2G  18.2.2   f3e4fc32e0d7  1714f5ae6008  ."""

    scenario_passed = [
        ValidationScenarioParams("passed on NCS < 24.11",
                                 cmd_input_output_dict={
                                     "sudo ceph-volume lvm list --format json": CmdOutput('{"1": [], "2": []}'),
                                     "sudo docker ps | grep ceph-osd": CmdOutput(docker_ps)
                                 },
                                 version=Version.V24_7),
        ValidationScenarioParams("passed on NCS == 24.11",
                                 cmd_input_output_dict={
                                     "sudo ceph-volume lvm list --format json": CmdOutput('{"1": [], "2": []}'),
                                     "sudo ceph orch ps --daemon_type osd | grep running | grep hawaii-cluster-storagebm-0": CmdOutput(ceph_orch_ps)
                                 },
                                 tested_object_mock_dict={"get_ceph_host_name": Mock(return_value="hawaii-cluster-storagebm-0")},
                                 version=Version.V24_11)
    ]

    scenario_failed = [
        ValidationScenarioParams("failed on NCS < 24.11",
                                 cmd_input_output_dict={
                                     "sudo ceph-volume lvm list --format json": CmdOutput(
                                         '{"1": [], "2": [], "3": []}'),
                                     "sudo docker ps | grep ceph-osd": CmdOutput(docker_ps)
                                 },
                                 version=Version.V24_7),
        ValidationScenarioParams("passed on NCS == 24.11",
                                 cmd_input_output_dict={
                                     "sudo ceph-volume lvm list --format json": CmdOutput(
                                         '{"1": [], "2": [], "3": []}'),
                                     "sudo ceph orch ps --daemon_type osd | grep running | grep hawaii-cluster-storagebm-0": CmdOutput(ceph_orch_ps)
                                 },
                                 tested_object_mock_dict={"get_ceph_host_name": Mock(return_value="hawaii-cluster-storagebm-0")},
                                 version=Version.V24_11)
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


class TestAreInstalledOSDsMatchCephConfigOnNCS(CephValidationTestBase):
    tested_type = AreInstalledOSDsMatchCephConfigOnNCS

    scenario_passed = [
        ValidationScenarioParams("empty json",
                                 cmd_input_output_dict={
                                     "sudo ceph-volume lvm list --format json": CmdOutput("{}")
                                 }),
        ValidationScenarioParams("passed",
                                 cmd_input_output_dict={
                                     "sudo ceph-volume lvm list --format json": CmdOutput(
                                         '{"24":[{"devices": ["/dev/sdk"], "type": "block"}]}')
                                 },
                                 version=Version.V19,
                                 tested_object_mock_dict={"get_host_osd_conf_value": Mock(return_value="sdk")})
    ]

    scenario_failed = [
        ValidationScenarioParams("failed",
                                 cmd_input_output_dict={
                                     "sudo ceph-volume lvm list --format json": CmdOutput(
                                         '{"24":[{"devices": ["/dev/sdb"], "type": "block"}]}')
                                 },
                                 version=Version.V19,
                                 tested_object_mock_dict={"get_host_osd_conf_value": Mock(return_value="sdk")})
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


class TestCephSlowRequests(CephValidationTestBase):
    tested_type = CephSlowRequests

    scenario_passed = [
        ValidationScenarioParams("passed",
                                 cmd_input_output_dict={
                                     "sudo cat /var/log/ceph/ceph_mon.log | grep REQUEST_SLOW": CmdOutput("",
                                                                                                          return_code=1)
                                 })
    ]

    scenario_failed = [
        ValidationScenarioParams("failed",
                                 cmd_input_output_dict={
                                     "sudo cat /var/log/ceph/ceph_mon.log | grep REQUEST_SLOW": CmdOutput("",
                                                                                                          return_code=0)
                                 })
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


class TestCephOsdMemoryAllocation(CephValidationTestBase):
    tested_type = CephOsdMemoryAllocation

    scenario_passed = [
        ValidationScenarioParams("Version 22: passed no memory",
                                 library_mocks_dict={
                                     "gs.get_deployment_type": Mock(return_value=Deployment_type.NCS_OVER_BM)},
                                 version=Version.V22,
                                 cmd_input_output_dict={
                                     "sudo ls /var/lib/ceph/osd/ceph-*/run": CmdOutput(out="", return_code=1),
                                     "sudo cat /usr/share/ceph-osd-run.sh | grep '\--memory'": CmdOutput("")
                                 }),
        ValidationScenarioParams("Version 22: passed",
                                 version=Version.V22,
                                 library_mocks_dict={
                                     "gs.get_deployment_type": Mock(return_value=Deployment_type.NCS_OVER_BM)},
                                 cmd_input_output_dict={
                                     "sudo ls /var/lib/ceph/osd/ceph-*/run": CmdOutput(out="", return_code=1),
                                     "sudo cat /usr/share/ceph-osd-run.sh | grep '\--memory'": CmdOutput("--memory=10g")
                                 }),
        ValidationScenarioParams("Version 24.7: passed no memory",
                                 version=Version.V24_7,
                                 library_mocks_dict={
                                     "gs.get_base_conf": Mock(return_value={"all": {"vars": {}}}),
                                     "gs.get_deployment_type": Mock(return_value=Deployment_type.NCS_OVER_BM)},
                                 cmd_input_output_dict={
                                     "sudo ls /var/lib/ceph/osd/ceph-*/run": CmdOutput(out="/var/lib/ceph/osd/ceph-0/run   /var/lib/ceph/osd/ceph-16/run", return_code=0),
                                    "sudo cat /var/lib/ceph/osd/ceph-0/run | grep '\--memory'": CmdOutput("")}),
        ValidationScenarioParams("Version 24.7: passed",
                                 version=Version.V24_7,
                                 library_mocks_dict={
                                     "gs.get_deployment_type": Mock(return_value=Deployment_type.NCS_OVER_BM)},
                                 cmd_input_output_dict={
                                     "sudo ls /var/lib/ceph/osd/ceph-*/run": CmdOutput(out="/var/lib/ceph/osd/ceph-0/run   /var/lib/ceph/osd/ceph-16/run", return_code=0),
                                     "sudo cat /var/lib/ceph/osd/ceph-0/run | grep '\--memory'": CmdOutput("--memory=10g")}
                                 )
    ]

    scenario_failed = [
        ValidationScenarioParams("Version 22: failed - memory is smaller than expected",
                                 version=Version.V22,
                                 library_mocks_dict={
                                     "gs.get_deployment_type": Mock(return_value=Deployment_type.NCS_OVER_BM)},
                                 cmd_input_output_dict={
                                     "sudo ls /var/lib/ceph/osd/ceph-*/run": CmdOutput(out="", return_code=1),
                                     "sudo cat /usr/share/ceph-osd-run.sh | grep '\--memory'": CmdOutput("--memory=4g")
                                 }),
        ValidationScenarioParams("Version 22: failed - memory not in expected unit size",
                                 version=Version.V22,
                                 library_mocks_dict={
                                     "gs.get_deployment_type": Mock(return_value=Deployment_type.NCS_OVER_BM)},
                                 cmd_input_output_dict={
                                     "sudo ls /var/lib/ceph/osd/ceph-*/run": CmdOutput(out="", return_code=1),
                                     "sudo cat /usr/share/ceph-osd-run.sh | grep '\--memory'": CmdOutput("--memory=4048m")
                                 }),
        ValidationScenarioParams("Version 24.7: failed - memory is smaller than expected",
                                 version=Version.V24_7,
                                 library_mocks_dict={
                                     "gs.get_deployment_type": Mock(return_value=Deployment_type.NCS_OVER_BM)},
                                 cmd_input_output_dict={
                                     "sudo ls /var/lib/ceph/osd/ceph-*/run": CmdOutput(out="/var/lib/ceph/osd/ceph-0/run   /var/lib/ceph/osd/ceph-16/run", return_code=0),
                                     "sudo cat /var/lib/ceph/osd/ceph-0/run | grep '\--memory'": CmdOutput("--memory=2g")}
                                 ),
        ValidationScenarioParams("Version 24.7: failed - memory not in expected unit size",
                                 version=Version.V24_7,
                                 library_mocks_dict={
                                     "gs.get_deployment_type": Mock(return_value=Deployment_type.NCS_OVER_BM)},
                                cmd_input_output_dict={
                                    "sudo ls /var/lib/ceph/osd/ceph-*/run": CmdOutput(out="/var/lib/ceph/osd/ceph-0/run   /var/lib/ceph/osd/ceph-16/run", return_code=0),
                                    "sudo cat /var/lib/ceph/osd/ceph-0/run | grep '\--memory'": CmdOutput("--memory=4048m")}
                                 )
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


class TestCephCpuQuotaCheck(CephValidationTestBase):
    tested_type = CephCpuQuotaCheck

    scenario_passed = [
        ValidationScenarioParams("Passed - NCS version < 24.7",
                                 tested_object_mock_dict={
                                     "get_first_ceph_osd_file": Mock(return_value="/usr/share/ceph-osd-run.sh"),
                                     "file_utils.is_file_exist": Mock(return_value=True)
                                 },
                                 cmd_input_output_dict={
                                     "cat /usr/share/ceph-osd-run.sh | grep cpu-quota": CmdOutput("", return_code=1)
                                 }),
        ValidationScenarioParams("Passed - NCS version >= 24.7",
                                 tested_object_mock_dict={
                                     "get_first_ceph_osd_file": Mock(return_value="/var/lib/ceph/osd/ceph-10/run"),
                                     "file_utils.is_file_exist": Mock(return_value=True)
                                 },
                                 cmd_input_output_dict={
                                     "cat /var/lib/ceph/osd/ceph-10/run | grep cpu-quota": CmdOutput("", return_code=1)
                                 })
    ]

    scenario_failed = [
        ValidationScenarioParams("Failed - 'cpu-quota' is defined",
                                 tested_object_mock_dict={
                                     "get_first_ceph_osd_file": Mock(return_value="/usr/share/ceph-osd-run.sh"),
                                     "file_utils.is_file_exist": Mock(return_value=True)
                                 },
                                 cmd_input_output_dict={
                                     "cat /usr/share/ceph-osd-run.sh | grep cpu-quota": CmdOutput("cpu-quota: 12345", return_code=0)
                                 }),
        ValidationScenarioParams("Failed - file /usr/share/ceph-osd-run.sh not exists",
                                 tested_object_mock_dict={
                                     "get_first_ceph_osd_file": Mock(return_value="/usr/share/ceph-osd-run.sh"),
                                     "file_utils.is_file_exist": Mock(return_value=False)
                                 },
                                 cmd_input_output_dict={
                                     "cat /usr/share/ceph-osd-run.sh | grep cpu-quota": CmdOutput("cpu-quota: 12345",
                                                                                                  return_code=0)
                                 })
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    def _init_mocks(self, tested_object):
        tested_object.file_utils.is_file_exist = Mock(return_value=True)


class TestVerifyOsdOpNumThreadsPerShardSSD(CephValidationTestBase):
    tested_type = VerifyOsdOpNumThreadsPerShardSSD

    cmd = "for i in `sudo ls /var/run/ceph/`;do sudo ceph daemon /var/run/ceph/$i config show | " \
          "grep -e osd_op_num_threads_per_shard_ssd| cut -d'\"' -f4; done"

    scenario_passed = [
        ValidationScenarioParams("passed",
                                 cmd_input_output_dict={
                                     cmd: CmdOutput("2\n2")
                                 },
                                 version=Version.V22_12)
    ]

    scenario_failed = [
        ValidationScenarioParams("failed",
                                 cmd_input_output_dict={
                                     cmd: CmdOutput("2\n1\n2")
                                 },
                                 version=Version.V24_7)
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


class TestCheckMinOsdNodes(CephValidationTestBase):
    tested_type = CheckMinOsdNodes

    out = """-9       1.55698     host overcloud-ovscompute-0
-7       1.55698     host overcloud-ovscompute-1"""

    out_passed = out + """-5       1.55698     host overcloud-sriovperformancecompute-0
-3       1.55698     host overcloud-sriovperformancecompute-1"""

    scenario_passed = [
        ValidationScenarioParams("passed",
                                 cmd_input_output_dict={
                                     "sudo ceph osd tree | grep -i host": CmdOutput(out_passed)
                                 })
    ]

    scenario_failed = [
        ValidationScenarioParams("failed",
                                 cmd_input_output_dict={
                                     "sudo ceph osd tree | grep -i host": CmdOutput(out)
                                 })
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestCheckMdsCount(CephValidationTestBase):
    tested_type = CheckMdsCount

    scenario_passed = [
        ValidationScenarioParams("passed",
                                 tested_object_mock_dict={
                                     "get_host_name": Mock(return_value="overcloud-controller-fi856-0")
                                 },
                                 cmd_input_output_dict={
                                     "sudo ls /var/run/ceph/ | egrep -w 'overcloud-controller-fi856-0.asok'": CmdOutput(
                                         "ceph-client.admin.asok  ceph-client.rgw.overcloud-controller-fi856-0.asok  "
                                         "ceph-mds.overcloud-controller-fi856-0.asok  "
                                         "ceph-mgr.overcloud-controller-fi856-0.asok  "
                                         "ceph-mon.overcloud-controller-fi856-0.asok")
                                 },
                                 version=Version.V24_7)
    ]

    scenario_failed = [
        ValidationScenarioParams("failed",
                                 tested_object_mock_dict={
                                     "get_host_name": Mock(return_value="overcloud-controller-fi856-0")},
                                 cmd_input_output_dict={
                                     "sudo ls /var/run/ceph/ | egrep -w 'overcloud-controller-fi856-0.asok'": CmdOutput(
                                         "ceph-client.admin.asok  ceph-client.rgw.overcloud-controller-fi856-0.asok  "
                                         "ceph-mgr.overcloud-controller-fi856-0.asok  "
                                         "ceph-mon.overcloud-controller-fi856-0.asok")
                                 },
                                 version=Version.V20_FP2)
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestCheckPoolSize(CephValidationTestBase):
    tested_type = CheckPoolSize

    scenario_passed = [
        ValidationScenarioParams("passed",
                                 cmd_input_output_dict={
                                     "sudo ceph osd pool ls detail -f json": CmdOutput(
                                         '[{"size": 2, "pool_name": "name1"}]')
                                 })
    ]

    scenario_failed = [
        ValidationScenarioParams("failed",
                                 cmd_input_output_dict={
                                     "sudo ceph osd pool ls detail -f json": CmdOutput(
                                         '[{"size": 2, "pool_name": "name1"},'
                                         '{"size": 1, "pool_name": "name2"}]')
                                 },
                                 failed_msg="ceph replication factor is less than 2 in following pools:name2")
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestIsOSDsUp(CephValidationTestBase):
    tested_type = IsOSDsUp

    scenario_passed = [
        ValidationScenarioParams("passed",
                                 tested_object_mock_dict={
                                     "get_host_osds": Mock(return_value={"1": {"status": "ok"}})
                                 })
    ]

    scenario_failed = [
        ValidationScenarioParams("command failed",
                                 tested_object_mock_dict={
                                     "get_host_osds": Mock(return_value={
                                         'is_passed': False, 'failed_msg': 'some failed'})
                                 },
                                 failed_msg="some failed"),
        ValidationScenarioParams("status down",
                                 tested_object_mock_dict={
                                     "get_host_osds": Mock(return_value={"1": {"status": "ok"},
                                                                         "2": {"status": "down"}})
                                 },
                                 failed_msg="The following osds are in down state: [2]")
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


def get_host_osd_conf_value_side_effect(osd_name, key_name):
    if osd_name == "6":
        return "sdb1"
    return "sda2"


class TestIsOsdDiskConfApplied(CephValidationTestBase):
    tested_type = IsOsdDiskConfApplied
    sdb_cmd = "sudo docker exec --user=root ceph-osd-overcloud-ovscompute-fi856-2-sdb mount | grep '/osd/ceph-[0-9]' "
    sdb_out = "/dev/sdb{} on /var/lib/ceph/osd/ceph-6 type xfs (rw,noatime,seclabel,attr2,inode64,logbsize=256k)"
    cmd_input_output_dict = {
        "sudo docker ps | grep ceph | awk '{print $NF}'": CmdOutput(
            "ceph-osd-overcloud-ovscompute-fi856-2-sdb\nceph-osd-overcloud-ovscompute-fi856-2-sda2"),
        sdb_cmd: CmdOutput(sdb_out.format(1)),
        "sudo docker exec --user=root ceph-osd-overcloud-ovscompute-fi856-2-sda2 mount | grep '/osd/ceph-[0-9]' ": CmdOutput(
            "/dev/sda2 on /var/lib/ceph/osd/ceph-2 type xfs (rw,noatime,seclabel,attr2,inode64,logbsize=256)")}
    cmd_input_output_dict_device_conf_not_applied = cmd_input_output_dict.copy()
    cmd_input_output_dict_device_conf_not_applied[sdb_cmd] = CmdOutput(sdb_out.format(3))
    cmd_input_output_dict_containers_not_running = cmd_input_output_dict.copy()
    cmd_input_output_dict_containers_not_running[sdb_cmd] = CmdOutput(sdb_out.format(4))

    scenario_passed = [
        ValidationScenarioParams("passed",
                                 tested_object_mock_dict={
                                     "get_host_osds": Mock(return_value={"6": {"status": "ok"}, "2": {"status": "ok"}}),
                                     "get_host_osd_conf_value": Mock(side_effect=get_host_osd_conf_value_side_effect),
                                     "get_host_osd_conf_section": Mock(return_value={"same data"})
                                 },
                                 cmd_input_output_dict=cmd_input_output_dict),
        ValidationScenarioParams("passed no conf section",
                                 tested_object_mock_dict={
                                     "get_host_osds": Mock(return_value={"6": {"status": "ok"}, "2": {"status": "ok"}}),
                                     "get_host_osd_conf_section": Mock(return_value=None)
                                 },
                                 cmd_input_output_dict=cmd_input_output_dict)
    ]

    scenario_failed = [
        ValidationScenarioParams("failed - device conf is not applied",
                                 tested_object_mock_dict={
                                     "get_host_osds": Mock(return_value={"6": {"status": "ok"}, "2": {"status": "ok"}}),
                                     "get_host_osd_conf_value": Mock(side_effect=get_host_osd_conf_value_side_effect),
                                     "get_host_osd_conf_section": Mock(return_value={"same data"})
                                 },
                                 cmd_input_output_dict=cmd_input_output_dict_device_conf_not_applied,
                                 failed_msg="following osds device conf is not applied:\nosd.6 : "
                                            "conf : sdb1, mount: sdb3\n"),
        ValidationScenarioParams("failed - containers are not running",
                                 tested_object_mock_dict={
                                     "get_host_osds": Mock(return_value={"6": {"status": "ok"}, "3": {"status": "ok"}}),
                                     "get_host_osd_conf_value": Mock(side_effect=get_host_osd_conf_value_side_effect),
                                     "get_host_osd_conf_section": Mock(return_value={"same data"})
                                 },
                                 cmd_input_output_dict=cmd_input_output_dict,
                                 failed_msg="following osds containers are not running:\n3\n"),
        ValidationScenarioParams("failed - device conf is not applied & containers are not running",
                                 tested_object_mock_dict={
                                     "get_host_osds": Mock(return_value={"6": {"status": "ok"}, "3": {"status": "ok"}}),
                                     "get_host_osd_conf_value": Mock(side_effect=get_host_osd_conf_value_side_effect),
                                     "get_host_osd_conf_section": Mock(return_value={"same data"})
                                 },
                                 cmd_input_output_dict=cmd_input_output_dict_containers_not_running,
                                 failed_msg="following osds device conf is not applied:\n"
                                            "osd.6 : conf : sdb1, mount: sdb4\n"
                                            "following osds containers are not running:\n3\n")
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


def get_host_osd_conf_value2_side_effect(osd_name, key_name):
    if key_name == "OSD_DEVICE":
        return "sdb1"
    if key_name == "BLOCK_DEVICE":
        return "/dev/sdb2"
    if key_name == "OSD_BLUESTORE_BLOCK_DB":
        return "/dev/sdb3"
    if key_name == "OSD_BLUESTORE_BLOCK_WAL":
        return "/dev/sdb4"
    if osd_name == "67" and key_name == "SERVICE_NAME":
        return "ceph-osd@sdb"
    elif osd_name == "0" and key_name == "SERVICE_NAME":
        return "ceph-osd@sda2.service"
    if key_name == "SERVICE_NAME":
        return "ceph-osd@sdb.service"


def get_host_osd_conf_value_nvme_side_effect(osd_name, key_name):
    if key_name == "OSD_DEVICE":
        return "nvme0n1p1"
    if key_name == "BLOCK_DEVICE":
        return "/dev/nvme0n1p2"
    if key_name == "OSD_BLUESTORE_BLOCK_DB":
        return "/dev/nvme0n1p3"
    if key_name == "OSD_BLUESTORE_BLOCK_WAL":
        return "/dev/nvme0n1p4"
    if key_name == "SERVICE_NAME":
        return "ceph-osd@nvme0n1.service"


class TestIsOsdInContainerSameAsInConf(CephValidationTestBase):
    tested_type = IsOsdInContainerSameAsInConf

    docker_ps_out = """CONTAINER ID  IMAGE  COMMAND  CREATED  STATUS  PORTS  NAMES
15afb7ee2d24  centos-7  "/entrypoint.sh"  7 weeks ago  Up 7 weeks  ceph-osd-sdb"""

    docker_ps_nvme_out = """CONTAINER ID  IMAGE  COMMAND  CREATED  STATUS  PORTS  NAMES
15afb7ee2d24  172.31.0.1:8787/ceph/daemon:tag-build-master-luminous-centos-7   "/entrypoint.sh"         2 weeks ago         Up 2 weeks                                 ceph-osd-storage_dummy-nvme0n1"""

    ls_out = """total 56
-rw-r--r--. 1 ceph ceph 234 May 26 12:56 activate.monmap
-rw-r--r--. 1 ceph ceph   3 May 26 12:56 active
lrwxrwxrwx. 1 ceph ceph  58 May 26 12:55 block -> {}
lrwxrwxrwx. 1 ceph ceph  58 May 26 12:55 block.db -> {}
lrwxrwxrwx. 1 ceph ceph  58 May 26 12:55 block.wal -> {}
-rw-r--r--. 1 ceph ceph  37 May 26 12:55 block.wal_uuid"""

    ls_out_v19 = ls_out.format("/dev/disk/by-partuuid/3f4d1a14", "/dev/disk/by-partuuid/e9d6fe03",
                               "/dev/disk/by-partuuid/661e7585")
    ls_out_v22 = ls_out.format("/dev/sdb2", "/dev/disk/by-partuuid/e9d6fe03",
                               "/dev/disk/by-partuuid/661e7585")

    scenario_passed = [
        ValidationScenarioParams("pass v19",
                                 version=Version.V19,
                                 tested_object_mock_dict={
                                     "get_host_osds": Mock(return_value={"6": {"status": "ok"}, "2": {"status": "ok"}}),
                                     "get_host_osd_conf_value": Mock(side_effect=get_host_osd_conf_value2_side_effect),
                                     "get_host_osd_conf_section": Mock()
                                 },
                                 cmd_input_output_dict={
                                     "sudo docker ps --filter name=sdb": CmdOutput(docker_ps_out),
                                     "sudo docker exec 15afb7ee2d24 ls -l /var/lib/ceph/osd/ceph-6": CmdOutput(
                                         ls_out_v19),
                                     "sudo docker exec 15afb7ee2d24 ls -l /var/lib/ceph/osd/ceph-2": CmdOutput(
                                         ls_out_v19),
                                     "sudo readlink -f /dev/disk/by-partuuid/e9d6fe03": CmdOutput("/dev/sdb3"),
                                     "sudo readlink -f /dev/disk/by-partuuid/3f4d1a14": CmdOutput("/dev/sdb2"),
                                     "sudo readlink -f /dev/disk/by-partuuid/661e7585": CmdOutput("/dev/sdb4")
                                 }),
        ValidationScenarioParams("pass v19 nvme",
                                 version=Version.V19,
                                 tested_object_mock_dict={
                                     "get_host_osds": Mock(return_value={"6": {"status": "ok"}, "2": {"status": "ok"}}),
                                     "get_host_osd_conf_value": Mock(side_effect=get_host_osd_conf_value_nvme_side_effect),
                                     "get_host_osd_conf_section": Mock(),
                                     "get_host_name": Mock(return_value="storage_dummy")
                                 },
                                 cmd_input_output_dict={
                                     "sudo docker ps --filter name=ceph-osd-storage_dummy-nvme0n1": CmdOutput(docker_ps_nvme_out),
                                     "sudo docker exec 15afb7ee2d24 ls -l /var/lib/ceph/osd/ceph-6": CmdOutput(
                                         ls_out_v19),
                                     "sudo docker exec 15afb7ee2d24 ls -l /var/lib/ceph/osd/ceph-2": CmdOutput(
                                         ls_out_v19),
                                     "sudo readlink -f /dev/disk/by-partuuid/e9d6fe03": CmdOutput("/dev/nvme0n1p3"),
                                     "sudo readlink -f /dev/disk/by-partuuid/3f4d1a14": CmdOutput("/dev/nvme0n1p2"),
                                     "sudo readlink -f /dev/disk/by-partuuid/661e7585": CmdOutput("/dev/nvme0n1p4")
                                 }),
        ValidationScenarioParams("pass v22",
                                 version=Version.V22_7,
                                 tested_object_mock_dict={
                                     "get_host_osds": Mock(return_value={"6": {"status": "ok"}, "2": {"status": "ok"}}),
                                     "get_host_osd_conf_value": Mock(side_effect=get_host_osd_conf_value2_side_effect),
                                     "get_host_osd_conf_section": Mock()
                                 },
                                 cmd_input_output_dict={
                                     "sudo docker ps --filter name=^ceph-osd-sdb$": CmdOutput(docker_ps_out),
                                     "sudo docker exec 15afb7ee2d24 ls -l /var/lib/ceph/osd/ceph-6": CmdOutput(
                                         ls_out_v22),
                                     "sudo docker exec 15afb7ee2d24 ls -l /var/lib/ceph/osd/ceph-2": CmdOutput(
                                         ls_out_v22),
                                     "sudo readlink -f /dev/disk/by-partuuid/e9d6fe03": CmdOutput("/dev/sdb3"),
                                     "sudo readlink -f /dev/disk/by-partuuid/661e7585": CmdOutput("/dev/sdb4")
                                 })
    ]

    scenario_failed = [
        ValidationScenarioParams("scenario_not_passed_block",
                                 version=Version.V19,
                                 tested_object_mock_dict={
                                     "get_host_osds": Mock(return_value={"6": {"status": "ok"}, "2": {"status": "ok"}}),
                                     "get_host_osd_conf_value": Mock(side_effect=get_host_osd_conf_value2_side_effect),
                                     "get_host_osd_conf_section": Mock()
                                 },
                                 cmd_input_output_dict={
                                     "sudo docker ps --filter name=sdb": CmdOutput(docker_ps_out),
                                     "sudo docker exec 15afb7ee2d24 ls -l /var/lib/ceph/osd/ceph-6": CmdOutput(
                                         ls_out_v19),
                                     "sudo docker exec 15afb7ee2d24 ls -l /var/lib/ceph/osd/ceph-2": CmdOutput(
                                         ls_out_v19),
                                     "sudo readlink -f /dev/disk/by-partuuid/e9d6fe03": CmdOutput("/dev/sdb3"),
                                     "sudo readlink -f /dev/disk/by-partuuid/3f4d1a14": CmdOutput("/dev/sdb3"),
                                     "sudo readlink -f /dev/disk/by-partuuid/661e7585": CmdOutput("/dev/sdb4")
                                 }),
        ValidationScenarioParams("scenario_not_passed_block_db",
                                 version=Version.V19,
                                 tested_object_mock_dict={
                                     "get_host_osds": Mock(return_value={"6": {"status": "ok"}, "2": {"status": "ok"}}),
                                     "get_host_osd_conf_value": Mock(side_effect=get_host_osd_conf_value2_side_effect),
                                     "get_host_osd_conf_section": Mock()
                                 },
                                 cmd_input_output_dict={
                                     "sudo docker ps --filter name=sdb": CmdOutput(docker_ps_out),
                                     "sudo docker exec 15afb7ee2d24 ls -l /var/lib/ceph/osd/ceph-6": CmdOutput(
                                         ls_out_v19),
                                     "sudo docker exec 15afb7ee2d24 ls -l /var/lib/ceph/osd/ceph-2": CmdOutput(
                                         ls_out_v19),
                                     "sudo readlink -f /dev/disk/by-partuuid/e9d6fe03": CmdOutput("/dev/sdb10"),
                                     "sudo readlink -f /dev/disk/by-partuuid/3f4d1a14": CmdOutput("/dev/sdb2"),
                                     "sudo readlink -f /dev/disk/by-partuuid/661e7585": CmdOutput("/dev/sdb4")
                                 }),
        ValidationScenarioParams("scenario_not_passed_block_wall",
                                 version=Version.V19,
                                 tested_object_mock_dict={
                                     "get_host_osds": Mock(return_value={"6": {"status": "ok"}, "2": {"status": "ok"}}),
                                     "get_host_osd_conf_value": Mock(side_effect=get_host_osd_conf_value2_side_effect),
                                     "get_host_osd_conf_section": Mock()
                                 },
                                 cmd_input_output_dict={
                                     "sudo docker ps --filter name=sdb": CmdOutput(docker_ps_out),
                                     "sudo docker exec 15afb7ee2d24 ls -l /var/lib/ceph/osd/ceph-6": CmdOutput(
                                         ls_out_v19),
                                     "sudo docker exec 15afb7ee2d24 ls -l /var/lib/ceph/osd/ceph-2": CmdOutput(
                                         ls_out_v19),
                                     "sudo readlink -f /dev/disk/by-partuuid/e9d6fe03": CmdOutput("/dev/sdb3"),
                                     "sudo readlink -f /dev/disk/by-partuuid/3f4d1a14": CmdOutput("/dev/sdb2"),
                                     "sudo readlink -f /dev/disk/by-partuuid/661e7585": CmdOutput("/dev/sdb6")
                                 })
    ]

    scenario_unexpected_system_output = [
        ValidationScenarioParams("not have SERVICE_NAME in conf keys",
                                 version=Version.V22,
                                 tested_object_mock_dict={
                                     "get_host_osds": Mock(return_value={"6": {"status": "ok"}, "2": {"status": "ok"}}),
                                     "get_host_osd_conf_value": Mock(return_value=None),
                                     "get_host_osd_conf_section": Mock()
                                 }),
        ValidationScenarioParams("no osd container id",
                                 version=Version.V19,
                                 tested_object_mock_dict={
                                     "get_host_osds": Mock(return_value={"6": {"status": "ok"}, "2": {"status": "ok"}}),
                                     "get_host_osd_conf_value": Mock(side_effect=get_host_osd_conf_value2_side_effect),
                                     "get_host_osd_conf_section": Mock()
                                 },
                                 cmd_input_output_dict={
                                     "sudo docker ps --filter name=sdb": CmdOutput("")
                                 }),
        ValidationScenarioParams("block without link",
                                 version=Version.V19,
                                 tested_object_mock_dict={
                                     "get_host_osds": Mock(return_value={"6": {"status": "ok"}, "2": {"status": "ok"}}),
                                     "get_host_osd_conf_value": Mock(side_effect=get_host_osd_conf_value2_side_effect),
                                     "get_host_osd_conf_section": Mock()
                                 },
                                 cmd_input_output_dict={
                                     "sudo docker ps --filter name=sdb": CmdOutput(docker_ps_out),
                                     "sudo docker exec 15afb7ee2d24 ls -l /var/lib/ceph/osd/ceph-6": CmdOutput(
                                         ls_out_v19),
                                     "sudo docker exec 15afb7ee2d24 ls -l /var/lib/ceph/osd/ceph-2": CmdOutput(
                                         "lrwxrwxrwx. 1 ceph ceph  58 May 26 12:55 block ll"),
                                     "sudo readlink -f /dev/disk/by-partuuid/e9d6fe03": CmdOutput("/dev/sdb3"),
                                     "sudo readlink -f /dev/disk/by-partuuid/3f4d1a14": CmdOutput("/dev/sdb2"),
                                     "sudo readlink -f /dev/disk/by-partuuid/661e7585": CmdOutput("/dev/sdb4")
                                 })
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_unexpected_system_output(self, scenario_params, tested_object)

    def test_has_confluence(self, tested_object):
        # Override the func since this val doesn't have a confluence.
        # pls do not copy it! it's only for old validations that do not have a confluence page.
        warnings.warn("No confluence page")


class TestCephConfServiceNameValid(CephValidationTestBase):
    tested_type = CephConfServiceNameValid

    scenario_passed = [
        ValidationScenarioParams("Passed - Valid OSD 'SERVICE_NAME'",
                                 tested_object_mock_dict={
                                     "get_host_osds_conf": Mock(return_value=True),
                                     "get_host_osds": Mock(return_value={"0": {"status": "up"}, "2": {"status": "up"}}),
                                     "get_host_osd_conf_value": Mock(side_effect=get_host_osd_conf_value2_side_effect),
                                 }),
        ValidationScenarioParams("Passed - OSD with no 'SERVICE_NAME' in conf keys",
                                 tested_object_mock_dict={
                                     "get_host_osds_conf": Mock(return_value=True),
                                     "get_host_osds": Mock(return_value={"0": {"status": "up"}, "2": {"status": "up"}}),
                                     "get_host_osd_conf_value": Mock(return_value=None),
                                 }),
    ]

    scenario_failed = [
        ValidationScenarioParams("Failed - OSD with 'SERVICE_NAME' with invalid name",
                                 tested_object_mock_dict={
                                     "get_host_osds_conf": Mock(return_value=True),
                                     "get_host_osds": Mock(
                                         return_value={"0": {"status": "ok"}, "67": {"status": "ok"}}),
                                     "get_host_osd_conf_value": Mock(side_effect=get_host_osd_conf_value2_side_effect),
                                 }),
        ValidationScenarioParams("Failed - Failed to get host OSD",
                                 tested_object_mock_dict={
                                     "get_host_osds_conf": Mock(return_value=True),
                                     "get_host_osds": Mock(
                                         return_value={'is_passed': False, 'failed_msg': 'some failed'})
                                 }),
        ValidationScenarioParams("Failed - Missing host OSDs",
                                 tested_object_mock_dict={
                                     "get_host_osds_conf": Mock(return_value=False),
                                     "get_host_osds": Mock(return_value={"0": {"status": "up"}, "2": {"status": "up"}}),
                                     "get_host_osd_conf_value": Mock(return_value=None),
                                 }),
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


class TestIsOsdSystemctlValid(CephValidationTestBase):
    tested_type = IsOsdSystemctlValid

    valid_systemctl_list_units = '''
    ceph-osd@sda2.service   loaded active running   Ceph OSD
    ceph-osd@sdb.service    loaded active running   Ceph OSD
    '''

    invalid_systemctl_list_missing_units = '''
    ceph-osd@sda2.service   loaded active running   Ceph OSD
    '''

    scenario_passed = [
        ValidationScenarioParams("Passed - OSD systemctl processes are valid",
                                 tested_object_mock_dict={
                                     "get_host_osds_conf": Mock(return_value=True),
                                     "get_host_osds": Mock(return_value={"0": {"status": "up"}, "2": {"status": "up"}}),
                                     "get_host_osd_conf_value": Mock(side_effect=get_host_osd_conf_value2_side_effect),
                                 },
                                 cmd_input_output_dict={
                                     r"systemctl list-units | grep -E 'ceph-osd@\w+'": CmdOutput(
                                         valid_systemctl_list_units)
                                 })
    ]

    scenario_failed = [
        ValidationScenarioParams("Failed - OSD is configured but not run",
                                 tested_object_mock_dict={
                                     "get_host_osds_conf": Mock(return_value=True),
                                     "get_host_osds": Mock(
                                         return_value={"0": {"status": "ok"}, "67": {"status": "ok"}}),
                                     "get_host_osd_conf_value": Mock(side_effect=get_host_osd_conf_value2_side_effect),
                                 },
                                 cmd_input_output_dict={
                                     r"systemctl list-units | grep -E 'ceph-osd@\w+'": CmdOutput(
                                         invalid_systemctl_list_missing_units)
                                 }),
        ValidationScenarioParams("Failed - OSD is running but not configured",
                                 tested_object_mock_dict={
                                     "get_host_osds_conf": Mock(return_value=True),
                                     "get_host_osds": Mock(return_value={"0": {"status": "ok"}}),
                                     "get_host_osd_conf_value": Mock(side_effect=get_host_osd_conf_value2_side_effect),
                                 },
                                 cmd_input_output_dict={
                                     r"systemctl list-units | grep -E 'ceph-osd@\w+'": CmdOutput(
                                         valid_systemctl_list_units)
                                 }),
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


class TestOsdJournalError(CephValidationTestBase):
    tested_type = OsdJournalError

    jurnal_out_with_errors_old_version = 'ceph-osd@sda2.service entered failed'
    jurnal_out_with_errors_new_version = 'ceph-3b231527-a47a-4f0d-947a-04c9c52640c9@osd.0.service entered failed'

    scenario_passed = [
        ValidationScenarioParams("Version < 24.11 Passed - no jurnal errors from the last 1 hour",
                                 version=Version.V22,
                                 tested_object_mock_dict={
                                     "get_host_osds": Mock(return_value={"0": {"status": "up"}, "2": {"status": "up"}}),
                                     "get_host_osd_conf_value": Mock(side_effect=get_host_osd_conf_value2_side_effect),
                                 },
                                 cmd_input_output_dict={
                                     "sudo journalctl --since '1 hour ago' | grep -Ei '(fail|error).*ceph-osd@\\w+.service|ceph-osd@\\w+.service.*(fail|error)'":
                                         CmdOutput(''),
                                     "sudo journalctl -u 'ceph-osd@sda2.service' --since '1 hour ago' -n 15": CmdOutput('')
                                 }),
        ValidationScenarioParams("Version >= 24.11 Passed - no jurnal errors from the last 1 hour",
                                 version=Version.V24_11,
                                 tested_object_mock_dict={
                                     "get_host_osds": Mock(return_value={"0": {"status": "up"}, "2": {"status": "up"}}),
                                     "get_host_osd_conf_value": Mock(return_value=''),
                                 },
                                 library_mocks_dict={
                                     "CephInfo.get_fsid": Mock(return_value='3b231527-a47a-4f0d-947a-04c9c52640c9')
                                 },
                                 cmd_input_output_dict={
                                     "sudo journalctl --since '1 hour ago' | grep -Ei '(fail|error).*ceph-3b231527-a47a-4f0d-947a-04c9c52640c9@osd.\\w+.service|"
                                     "ceph-3b231527-a47a-4f0d-947a-04c9c52640c9@osd.\\w+.service.*(fail|error)'":
                                         CmdOutput(''),
                                     "sudo journalctl -u 'ceph-3b231527-a47a-4f0d-947a-04c9c52640c9@osd.0.service' --since '1 hour ago' -n 15": CmdOutput('')
                                 })
    ]

    scenario_failed = [
        ValidationScenarioParams("Failed - OSD has journal errors from last hour",
                                 version=Version.V22,
                                 tested_object_mock_dict={
                                     "get_host_osds": Mock(return_value={"0": {"status": "ok"}, "2": {"status": "ok"}}),
                                     "get_host_osd_conf_value": Mock(side_effect=get_host_osd_conf_value2_side_effect),
                                 },
                                 cmd_input_output_dict={
                                     "sudo journalctl --since '1 hour ago' | grep -Ei '(fail|error).*ceph-osd@\\w+.service|ceph-osd@\\w+.service.*(fail|error)'":
                                         CmdOutput(jurnal_out_with_errors_old_version),
                                     "sudo journalctl -u 'ceph-osd@sda2.service' --since '1 hour ago' -n 15":
                                         CmdOutput('some failures')
                                 }),
        ValidationScenarioParams("Version >= 24.11, Failed - OSD has journal errors from last hour",
                                 version=Version.V25,
                                 tested_object_mock_dict={
                                     "get_host_osds": Mock(return_value={"0": {"status": "ok"}, "2": {"status": "ok"}}),
                                     "get_host_osd_conf_value": Mock(return_value=''),
                                 },
                                 library_mocks_dict={
                                     "CephInfo.get_fsid": Mock(return_value='3b231527-a47a-4f0d-947a-04c9c52640c9')
                                 },
                                 cmd_input_output_dict={
                                     "sudo journalctl --since '1 hour ago' | grep -Ei '(fail|error).*ceph-3b231527-a47a-4f0d-947a-04c9c52640c9@osd.\\w+.service|"
                                     "ceph-3b231527-a47a-4f0d-947a-04c9c52640c9@osd.\\w+.service.*(fail|error)'":
                                         CmdOutput(jurnal_out_with_errors_new_version),
                                     "sudo journalctl -u 'ceph-3b231527-a47a-4f0d-947a-04c9c52640c9@osd.0.service' --since '1 hour ago' -n 15":
                                         CmdOutput('some failures')
                                 })
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    #
    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    def test_has_confluence(self, tested_object):
        # Override the func since this val doesn't have a confluence.
        # pls do not copy it! it's only for old validations that do not have a confluence page.
        warnings.warn("No confluence page")


class TestIsCephConfExist(CephValidationTestBase):
    tested_type = IsCephConfExist
    get_host_osds = {
        '2': {'status': 'up', 'dev_class': 'hdd', 'root': 'default',
              'weight': 0.76933},
        '6': {'status': 'up', 'dev_class': 'hdd', 'root': 'default',
              'weight': 0.807785}}
    get_host_osds_conf = {
        '2': {'block_device': '/dev/sda3',
              'osd_bluestore_block_db': '/dev/sda4',
              'hostname': 'overcloud-ovscompute-1',
              'osd_device': 'sda2',
              'osd_bluestore_block_wal': '/dev/sda5',
              'service_name': 'ceph-osd@sda2.service'},
        '6': {'block_device': '/dev/sdb2',
              'osd_bluestore_block_db': '/dev/sdb3',
              'hostname': 'overcloud-ovscompute-1',
              'osd_device': 'sdb1',
              'osd_bluestore_block_wal': '/dev/sdb4',
              'service_name': 'ceph-osd@sdb.service'}}
    get_host_osds_conf_failed = get_host_osds_conf.copy()
    get_host_osds_conf_failed.pop('2')
    scenario_passed = [ValidationScenarioParams("scenario_passed",
                                                tested_object_mock_dict={
                                                    "get_host_osds": Mock(return_value=get_host_osds),
                                                    "get_host_osds_conf": Mock(return_value=get_host_osds_conf)
                                                }),
                       ValidationScenarioParams("scenario_passed_wrong_host",
                                                tested_object_mock_dict={
                                                    "get_host_osds": Mock(return_value=None)}
                                                )]

    scenario_failed = [
        ValidationScenarioParams("scenario_get_host_osds_failed",
                                 tested_object_mock_dict={
                                     "get_host_osds": Mock(return_value={
                                         'is_passed': False, 'failed_msg': 'some failed'})
                                 },
                                 failed_msg="some failed"),
        ValidationScenarioParams("scenario_failed",
                                 tested_object_mock_dict={
                                     "get_host_osds": Mock(return_value=get_host_osds),
                                     "get_host_osds_conf": Mock(return_value=get_host_osds_conf_failed)
                                 },
                                 failed_msg="conf section of following osds is missing : [2].\nThis is a known bug in CBIS 19MP2 - fixed in 19MP4")]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestIsOsdAuthSameAsOsdTree(CephValidationTestBase):
    tested_type = IsOsdAuthSameAsOsdTree
    ceph_osd_tree = get_data_from_file('ceph_osd_tree.txt')
    ceph_auth_list = get_data_from_file('ceph_auth_list.txt')
    scenario_passed = [ValidationScenarioParams(
        scenario_title="scenario_passed", cmd_input_output_dict={
            "sudo ceph osd tree -f json": CmdOutput(ceph_osd_tree),
            'sudo ceph auth list -f json': CmdOutput(ceph_auth_list.format("mds.overcloud-controller-0"))})]

    scenario_failed = [ValidationScenarioParams(
        scenario_title="scenario_failed", cmd_input_output_dict={
            "sudo ceph osd tree -f json": CmdOutput(ceph_osd_tree),
            "sudo ceph auth list -f json": CmdOutput(ceph_auth_list.format("osd.50"))},
        failed_msg="Ceph auth list is not same to ceph osd tree.\n"
                   "osd_tree_list:\n"
                   "osd.0 osd.1 osd.2 osd.3 osd.4 osd.5 osd.6 osd.7.\n\n"
                   "auth_list:\n"
                   "osd.0 osd.1 osd.2 osd.3 osd.4 osd.5 osd.50 osd.6 osd.7")]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestCheckMonCount(CephValidationTestBase):
    tested_type = CheckMonCount
    out = """ceph-client.rgw.overcloud-controller-cbismon01-0.asok
ceph-mds.overcloud-controller-cbismon01-0.asok
ceph-mgr.overcloud-controller-cbismon01-0.asok
ceph-mon.overcloud-controller-cbismon01-0.asok"""

    out_newer_version_pass = """ceph-client.rgw.rgw.bvt-multi1-allinone-0.mhonel.7.94370984499360.asok  
    ceph-mon.bvt-multi1-allinone-0.asok
    ceph-mds.cephfs.bvt-multi1-allinone-0.lpnsyo.asok
    ceph-osd.0.asok
    ceph-mgr.bvt-multi1-allinone-0.kqjpqf.asok
    """
    failed_out_multiple_mon = out + "\n{}".format("ceph-mon.overcloud-controller-cbismon01-0.asok")
    failed_out_no_mon = re.sub(".*" + "ceph-mon" + ".*\n?", "", out)
    scenario_passed = [
        ValidationScenarioParams(scenario_title="scenario pass - version < 24.11", cmd_input_output_dict={
            "sudo ls /var/run/ceph/ | egrep -w 'overcloud-controller-cbismon01-0.asok'": CmdOutput(out)},
                                 tested_object_mock_dict={
                                     "get_host_name": Mock(return_value="overcloud-controller-cbismon01-0")},
                                 version=Version.V24_7),
        ValidationScenarioParams(scenario_title="scenario pass - version >= 24.11", cmd_input_output_dict={
            "sudo ls /var/run/ceph/cdc8c162-96a7-4fe0-8bd6-c624cce13c5f | egrep -w 'bvt-multi1-allinone-0.*\.asok'": CmdOutput(out_newer_version_pass)},
                                 tested_object_mock_dict={
                                     "get_host_name": Mock(return_value="bvt-multi1-allinone-0")},
                                 library_mocks_dict={
                                     "CephInfo.get_fsid": Mock(return_value="cdc8c162-96a7-4fe0-8bd6-c624cce13c5f")},
                                 version=Version.V24_11)
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="scenario failed multiple mon", cmd_input_output_dict={
            "sudo ls /var/run/ceph/ | egrep -w 'overcloud-controller-cbismon01-0.asok'": CmdOutput(
                failed_out_multiple_mon)},
                                 tested_object_mock_dict={
                                     "get_host_name": Mock(return_value="overcloud-controller-cbismon01-0")},
                                 failed_msg="we expect 1 socket exists for the mon ",
                                 version=Version.V22_12),

        ValidationScenarioParams(scenario_title="scenario_failed no mon", cmd_input_output_dict={
            "sudo ls /var/run/ceph/ | egrep -w 'overcloud-controller-cbismon01-0.asok'": CmdOutput(failed_out_no_mon)},
                                 tested_object_mock_dict={
                                     "get_host_name": Mock(return_value="overcloud-controller-cbismon01-0")},
                                 failed_msg="we expect 1 socket exists for the mon ",
                                 version=Version.V20_FP2)]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestCephConfCrushLocationExists(CephValidationTestBase):
    tested_type = CephConfCrushLocationExists
    host_osds = {'11': {'status': 'up', 'dev_class': 'ssd', 'root': 'common', 'weight': 1.7469940185546875}}
    host_osd_conf_section = {
        'block_device': '/dev/ceph-7209379a-a270-46bb-870f-14aaaa10d8f3/osd-block-a7c02b6f-8431-46ab-9dc1-02855cf0422a',
        'osd_bluestore_block_db': '/dev/nvme0n1p7', 'hostname': 'common-overcloud-storage-pl-8004-i14-0',
        'osd_device': 'sdf', 'crush_location': 'root=common host=common-overcloud-storage-pl-8004-i14-0',
        'osd_bluestore_block_wal': '/dev/nvme0n1p8', 'service_name': 'ceph-osd@11.service'}
    crush_location_root_wrong_configured = host_osd_conf_section.copy()
    host_osd_conf_section_missing_crush_location_key = host_osd_conf_section.copy()
    host_osd_conf_section_missing_crush_location_key.pop('crush_location')
    crush_location_root_wrong_configured['crush_location'] = 'root=default host=common-overcloud-storage-pl-8004-i14-0'
    multiple_crush_location_configured = host_osd_conf_section.copy()
    conf_section_unexpected_system_output = host_osd_conf_section.copy()
    conf_section_unexpected_system_output['crush_location'] = "xxx"
    multiple_crush_location_configured['"crush_location"'] = 'root=common'
    ceph_osd_tree = """ID CLASS WEIGHT  TYPE NAME                                    STATUS REWEIGHT PRI-AFF
-1       6.22791 root default
-9       1.55698     host overcloud-ovscompute-0
 3   hdd 0.74919         osd.3                                    up  1.00000 1.00000
 7   hdd 0.80779         osd.7                                    up  1.00000 1.00000
-7       1.55698     host overcloud-ovscompute-1
 2   hdd 0.74919         osd.2                                    up  1.00000 1.00000
 6   hdd 0.80779         osd.6                                    up  1.00000 1.00000
-5       1.55698     host overcloud-sriovperformancecompute-0
 0   hdd 0.74919         osd.0                                    up  1.00000 1.00000
 5   hdd 0.80779         osd.5                                    up  1.00000 1.00000
-3       1.55698     host overcloud-sriovperformancecompute-1
 1   hdd 0.74919         osd.1                                    up  1.00000 1.00000
 4   hdd 0.80779         osd.4                                    up  1.00000 1.00000"""
    lspool_fast = "\n1 vms\n2 volumes\n3 images\n4 metrics\n5 backups\n6 volumes-fast\n7 manila_data\n8 manila_metadata\n9 .rgw.root\n10 default.rgw.control\n11 default.rgw.meta\n12 default.rgw.log\n"
    scenario_passed = [ValidationScenarioParams(scenario_title="scenario_pass", cmd_input_output_dict={
        "sudo ceph osd lspools": CmdOutput(
            "1 images,2 metrics,3 backups,4 vms,5 volumes,6 manila_data,7 manila_metadata,8 .rgw.root,9 default.rgw.control,10 default.rgw.meta,11 default.rgw.log")}),
                       ValidationScenarioParams(scenario_title="scenario_pass_fast", cmd_input_output_dict={
                           "sudo ceph osd lspools": CmdOutput(lspool_fast),
                           "sudo ceph osd tree": CmdOutput(get_data_from_file("ceph_osd_tree_fast_passed.out"))},
                                                tested_object_mock_dict={"get_host_osds": Mock(return_value=host_osds),
                                                                         "get_host_osd_conf_section": Mock(
                                                                             return_value=host_osd_conf_section)}),
                       ValidationScenarioParams(scenario_title="scenario_pass_fast missing conf section",
                                                cmd_input_output_dict={
                                                    "sudo ceph osd lspools": CmdOutput(lspool_fast),
                                                    "sudo ceph osd tree": CmdOutput(
                                                        get_data_from_file("ceph_osd_tree_fast_passed.out"))},
                                                tested_object_mock_dict={"get_host_osds": Mock(return_value=host_osds),
                                                                         "get_host_osd_conf_section": Mock(
                                                                             return_value={})})]
    scenario_unexpected_system_output = [
        ValidationScenarioParams(scenario_title="scenario_unexpected_system_output", cmd_input_output_dict={
            "sudo ceph osd lspools": CmdOutput(lspool_fast),
            "sudo ceph osd tree": CmdOutput(get_data_from_file("ceph_osd_tree_fast_passed.out"))},
                                 tested_object_mock_dict={"get_host_osds": Mock(return_value=host_osds),
                                                          "get_host_osd_conf_section": Mock(
                                                              return_value=conf_section_unexpected_system_output)})]
    scenario_failed = [ValidationScenarioParams("command failed",
                                                tested_object_mock_dict={"get_host_osds": Mock(return_value={
                                                    'is_passed': False, 'failed_msg': 'some failed'})},
                                                cmd_input_output_dict={"sudo ceph osd lspools": CmdOutput(lspool_fast)},
                                                failed_msg="some failed"),
                       ValidationScenarioParams(
                           scenario_title="scenario_failed_fast multiple crush_location",
                           cmd_input_output_dict={"sudo ceph osd lspools": CmdOutput(lspool_fast),
                                                  "sudo ceph osd tree": CmdOutput(
                                                      get_data_from_file("ceph_osd_tree_fast_passed.out"))},
                           tested_object_mock_dict={"get_host_osds": Mock(return_value=host_osds),
                                                    "get_host_osd_conf_section": Mock(
                                                        return_value=multiple_crush_location_configured)}),
                       ValidationScenarioParams(
                           scenario_title="scenario_failed_fast crush_location root wrong configured",
                           cmd_input_output_dict={"sudo ceph osd lspools": CmdOutput(lspool_fast),
                                                  "sudo ceph osd tree": CmdOutput(
                                                      get_data_from_file("ceph_osd_tree_fast_passed.out"))},
                           tested_object_mock_dict={"get_host_osds": Mock(return_value=host_osds),
                                                    "get_host_osd_conf_section": Mock(
                                                        return_value=crush_location_root_wrong_configured)}),
                       ValidationScenarioParams(
                           scenario_title="scenario_failed_default_fast", cmd_input_output_dict={
                               "sudo ceph osd lspools": CmdOutput(lspool_fast),
                               "sudo ceph osd tree": CmdOutput(ceph_osd_tree)},
                           tested_object_mock_dict={"get_host_osds": Mock(return_value=host_osds),
                                                    "get_host_osd_conf_section": Mock(
                                                        return_value=host_osd_conf_section)}),
                       ValidationScenarioParams(
                           scenario_title="scenario_failed len(crush_location_key_list) == 0", cmd_input_output_dict={
                               "sudo ceph osd lspools": CmdOutput(lspool_fast)},
                           tested_object_mock_dict={"get_host_osds": Mock(return_value=host_osds),
                                                    "get_host_osd_conf_section": Mock(
                                                        return_value=host_osd_conf_section_missing_crush_location_key)})
                       ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_unexpected_system_output(self, scenario_params, tested_object)


class TestCheckOsdPGLogTuning(CephValidationTestBase):
    tested_type = CheckOsdPGLogTuning
    scenario_passed = [
        ValidationScenarioParams(
            scenario_title="scenario_pass < 10", cmd_input_output_dict={
                "sudo ceph daemon osd.2 config get osd_max_pg_log_entries": CmdOutput(
                    '{"osd_max_pg_log_entries": "1"}'),
                "sudo ceph daemon osd.2 config get osd_min_pg_log_entries": CmdOutput(
                    '{"osd_min_pg_log_entries": "2"}')},
            tested_object_mock_dict={"get_host_osds": Mock(return_value={"2": {"status": "ok"}})},
            version=Version.V24_7
        ),
        ValidationScenarioParams(
            scenario_title="scenario_pass", cmd_input_output_dict={
                "sudo ceph daemon osd.2 config get osd_max_pg_log_entries": CmdOutput(
                    '{"osd_max_pg_log_entries": "500"}'),
                "sudo ceph daemon osd.2 config get osd_min_pg_log_entries": CmdOutput(
                    '{"osd_min_pg_log_entries": "250"}')},
            tested_object_mock_dict={"get_host_osds": Mock(return_value={"2": {"status": "ok"}})},
            version=Version.V20_FP2
        ),
        ValidationScenarioParams(
            scenario_title="scenario_pass version >= 24.11", cmd_input_output_dict={
                "sudo ceph daemon /var/run/ceph/6ae21dfe-dd69-472b-bdff-1532d8bce82a/ceph-osd.2.asok config get "
                "osd_max_pg_log_entries": CmdOutput('{"osd_max_pg_log_entries": "500"}'),
                "sudo ceph daemon /var/run/ceph/6ae21dfe-dd69-472b-bdff-1532d8bce82a/ceph-osd.2.asok config get "
                "osd_min_pg_log_entries": CmdOutput('{"osd_min_pg_log_entries": "250"}')},
            tested_object_mock_dict={
                "get_host_osds": Mock(return_value={"2": {"status": "ok"}})},
            library_mocks_dict={"CephInfo.get_fsid": Mock(return_value="6ae21dfe-dd69-472b-bdff-1532d8bce82a")},
            version=Version.V24_11
        )]

    scenario_failed = [
        ValidationScenarioParams(
            scenario_title="scenario_failed No OSDs were found",
            tested_object_mock_dict={"get_host_osds": Mock(return_value={}),
                                     "get_host_name": Mock(return_value="overcloud-controller-cbismon01-0")},
            failed_msg="No OSDs were found on overcloud-controller-cbismon01-0",
            version=Version.V20_FP2),
        ValidationScenarioParams(
            scenario_title="scenario_failed osd_min!=250", cmd_input_output_dict={
                "sudo ceph daemon osd.6 config get osd_max_pg_log_entries": CmdOutput(
                    '{"osd_max_pg_log_entries": "500"}'),
                "sudo ceph daemon osd.6 config get osd_min_pg_log_entries": CmdOutput(
                    '{"osd_min_pg_log_entries": "100"}')},
            tested_object_mock_dict={"get_host_osds": Mock(return_value={"6": {"status": "ok"}})},
            failed_msg="Min pg log entries is set with 100, while it should be set with 250 - Tune the values in "
                       "ceph.conf in all the storage nodes",
            version=Version.V23_10),
        ValidationScenarioParams(
            scenario_title="scenario_failed osd_max!=500", cmd_input_output_dict={
                "sudo ceph daemon osd.6 config get osd_max_pg_log_entries": CmdOutput(
                    '{"osd_max_pg_log_entries": "3000"}'),
                "sudo ceph daemon osd.6 config get osd_min_pg_log_entries": CmdOutput(
                    '{"osd_min_pg_log_entries": "3000"}')},
            tested_object_mock_dict={"get_host_osds": Mock(return_value={"6": {"status": "ok"}})},
            failed_msg="Max pg log entries is set with 3000, while it should be set with 500 - Tune the values in "
                       "ceph.conf in all the storage nodes",
            version=Version.V24_7),
        ValidationScenarioParams(
            scenario_title="scenario_failed osd_min>10", cmd_input_output_dict={
                "sudo ceph daemon osd.6 config get osd_max_pg_log_entries": CmdOutput(
                    '{"osd_max_pg_log_entries": "2"}'),
                "sudo ceph daemon osd.6 config get osd_min_pg_log_entries": CmdOutput(
                    '{"osd_min_pg_log_entries": "15"}')},
            tested_object_mock_dict={"get_host_osds": Mock(return_value={"6": {"status": "ok"}})},
            failed_msg="Max pg log entries is set with 2, while it should be set with 500 - Tune the values in "
                       "ceph.conf in all the storage nodes",
            version=Version.V20_FP2),
        ValidationScenarioParams(
            scenario_title="scenario_failed osd_min>10 osd_max=500", cmd_input_output_dict={
                "sudo ceph daemon osd.6 config get osd_max_pg_log_entries": CmdOutput(
                    '{"osd_max_pg_log_entries": "500"}'),
                "sudo ceph daemon osd.6 config get osd_min_pg_log_entries": CmdOutput(
                    '{"osd_min_pg_log_entries": "15"}')},
            tested_object_mock_dict={"get_host_osds": Mock(return_value={"6": {"status": "ok"}})},
            failed_msg="Min pg log entries is set with 15, while it should be set with 250 - Tune the values in "
                       "ceph.conf in all the storage nodes",
            version=Version.V20_FP2),
        ValidationScenarioParams(
            scenario_title="scenario_failed osd_max>10", cmd_input_output_dict={
                "sudo ceph daemon osd.6 config get osd_max_pg_log_entries": CmdOutput(
                    '{"osd_max_pg_log_entries": "30"}'),
                "sudo ceph daemon osd.6 config get osd_min_pg_log_entries": CmdOutput(
                    '{"osd_min_pg_log_entries": "2"}')},
            tested_object_mock_dict={"get_host_osds": Mock(return_value={"6": {"status": "ok"}})},
            failed_msg="Max pg log entries is set with 30, while it should be set with 500 - Tune the values in "
                       "ceph.conf in all the storage nodes",
            version=Version.V20_FP2)]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestIOErrorCephFSMount(ValidationTestBase):
    tested_type = IOErrorCephFSMount

    validation_cmd = "sudo find /opt/bcmt/storage/docker-registry/ -type f -name link | shuf -n 10"
    out = "/opt/bcmt/storage/docker-registry/docker/registry/v2/repositories/scheduler-extender/_manifests/tags/v1.0" \
          ".0-0/current/link"

    scenario_passed = [
        ValidationScenarioParams(scenario_title="link file exist and is readable",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out=out)},
                                 additional_parameters_dict={"file_readable": True})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="link file exist but is not readable",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out=out)},
                                 additional_parameters_dict={"file_readable": False}),
        ValidationScenarioParams(scenario_title="link files not found",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out="")},
                                 additional_parameters_dict={"file_readable": {}})
    ]

    def _init_mocks(self, tested_object):
        tested_object.file_utils.is_file_readable = Mock()
        tested_object.file_utils.is_file_readable.return_value = self.additional_parameters_dict['file_readable']

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestCheckCephfsShareExist(CephValidationTestBase):
    tested_type = CheckCephfsShareExist

    scenario_passed = [ValidationScenarioParams("Mount path exists",
                                                additional_parameters_dict={"mount_exist": True},
                                                library_mocks_dict={"CephInfo.is_ceph_used": Mock(return_value=True)})]

    scenario_failed = [ValidationScenarioParams("Mount path doesn't exists",
                                                additional_parameters_dict={"mount_exist": False},
                                                library_mocks_dict={"CephInfo.is_ceph_used": Mock(return_value=True)})]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    def _init_mocks(self, tested_object):
        super(TestCheckCephfsShareExist, self)._init_mocks(tested_object)
        CephValidationTestBase._init_mocks(self, tested_object)
        if not self.additional_parameters_dict:
            return
        tested_object.file_utils.is_dir_exist = Mock()
        tested_object.file_utils.is_dir_exist.return_value = self.additional_parameters_dict['mount_exist']


class TestCephMultipoolSameNodeMemberCheck(ValidationTestBase):
    tested_type = CephMultipoolSameNodeMemberCheck

    pool_check_command = "sudo ceph osd tree -f json |  jq -r '.nodes[]|select(.type == \"root\").name'"
    nodes_list_command = "sudo ceph osd tree -f json | jq -r '.nodes[]|select(.type == \"host\").name'"
    out_bad = """
    default
    pool1
    pool2
    """
    out_good_1 = """
	default
	"""

    out_good_2 = """
    fast
    default
	"""
    host_out = """
    # sudo ceph osd tree -f json | jq -r '.nodes[]|select(.type == "host").name'
    pool1-overcloud-storage-uaqnfv-0
    pool1-overcloud-storage-uaqnfv-1
    pool2-overcloud-storage-uaqnfv-0
    pool2-overcloud-storage-uaqnfv-1
    """


    scenario_passed = [
        ValidationScenarioParams(scenario_title="good pool data",
                                 cmd_input_output_dict={
                                     pool_check_command: CmdOutput(out=out_good_1),
                                     nodes_list_command: CmdOutput(out=host_out)
                                 }),
        ValidationScenarioParams(scenario_title="good fast pool data",
                                 cmd_input_output_dict={
                                     pool_check_command: CmdOutput(out=out_good_2),
                                     nodes_list_command: CmdOutput(out=host_out)
                                 })
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="bad pool data",
                                 cmd_input_output_dict={
                                     pool_check_command: CmdOutput(out=out_bad),
                                     nodes_list_command: CmdOutput(out=host_out)
                                 })
    ]


class TestCephCheckPGsPerOSD(ValidationTestBase):
    tested_type = CephCheckPGsPerOSD
    cmd = "sudo ceph osd df"
    valid_out = """ID CLASS WEIGHT  REWEIGHT SIZE    RAW USE DATA   OMAP   META     AVAIL   %USE VAR  PGS STATUS .
 1   hdd 0.74919  1.00000 767 GiB 1.0 GiB 15 MiB    0 B    1 GiB 766 GiB 0.13 1.23 140     up .
 3   hdd 1.09160  1.00000 1.1 TiB 1.0 GiB 16 MiB  7 KiB 1024 MiB 1.1 TiB 0.09 0.84 212     up .
 0   hdd 0.74919  1.00000 767 GiB 1.0 GiB 15 MiB  7 KiB 1024 MiB 766 GiB 0.13 1.23 152     up .
 2   hdd 1.09160  1.00000 1.1 TiB 1.0 GiB 15 MiB 20 KiB 1024 MiB 1.1 TiB 0.09 0.84 200     up .
                TOTAL 3.7 TiB 4.1 GiB 61 MiB 36 KiB  4.0 GiB 3.7 TiB 0.11                 .
MIN/MAX VAR: 0.84/1.23  STDDEV: 0.02.
================================================"""

    too_high_out = """ID CLASS WEIGHT  REWEIGHT SIZE    RAW USE DATA   OMAP   META     AVAIL   %USE VAR  PGS STATUS .
 1   hdd 0.74919  1.00000 767 GiB 1.0 GiB 15 MiB    0 B    1 GiB 766 GiB 0.13 1.23 350     up .
 3   hdd 1.09160  1.00000 1.1 TiB 1.0 GiB 16 MiB  7 KiB 1024 MiB 1.1 TiB 0.09 0.84 212     up .
 0   hdd 0.74919  1.00000 767 GiB 1.0 GiB 15 MiB  7 KiB 1024 MiB 766 GiB 0.13 1.23 152     up .
 2   hdd 1.09160  1.00000 1.1 TiB 1.0 GiB 15 MiB 20 KiB 1024 MiB 1.1 TiB 0.09 0.84 200     up .
                TOTAL 3.7 TiB 4.1 GiB 61 MiB 36 KiB  4.0 GiB 3.7 TiB 0.11                 .
MIN/MAX VAR: 0.84/1.23  STDDEV: 0.02.
================================================"""

    too_low_out = """ID CLASS WEIGHT  REWEIGHT SIZE    RAW USE DATA   OMAP   META     AVAIL   %USE VAR  PGS STATUS .
 1   hdd 0.74919  1.00000 767 GiB 1.0 GiB 15 MiB    0 B    1 GiB 766 GiB 0.13 1.23 140     up .
 3   hdd 1.09160  1.00000 1.1 TiB 1.0 GiB 16 MiB  7 KiB 1024 MiB 1.1 TiB 0.09 0.84 212     up .
 0   hdd 0.74919  1.00000 767 GiB 1.0 GiB 15 MiB  7 KiB 1024 MiB 766 GiB 0.13 1.23 152     up .
 2   hdd 1.09160  1.00000 1.1 TiB 1.0 GiB 15 MiB 20 KiB 1024 MiB 1.1 TiB 0.09 0.84 40     up .
                TOTAL 3.7 TiB 4.1 GiB 61 MiB 36 KiB  4.0 GiB 3.7 TiB 0.11                 .
MIN/MAX VAR: 0.84/1.23  STDDEV: 0.02.
================================================"""

    unexpected_out = """ID CLASS WEIGHT  REWEIGHT SIZE    RAW USE DATA   OMAP   META     AVAIL   %USE VAR  PGS STATUS .
 1   hdd 0.74919  1.00000 767 GiB 1.0 GiB 15 MiB    0 B    1 GiB 766 GiB 0.13 1.23 140     up .
 3   hdd 1.09160  1.00000 1.1 TiB 1.0 GiB 16 MiB  7 KiB 1024 MiB 1.1 TiB 0.09 0.84 212     up .
 0   hdd 0.74919  1.00000 767 GiB 1.0 GiB 15 MiB  7 KiB 1024 MiB 766 GiB 0.13 1.23 152up .
 2   hdd 1.09160  1.00000 1.1 TiB 1.0 GiB 15 MiB 20 KiB 1024 MiB 1.1 TiB 0.09 0.84 40     up .
                TOTAL 3.7 TiB 4.1 GiB 61 MiB 36 KiB  4.0 GiB 3.7 TiB 0.11                 .
MIN/MAX VAR: 0.84/1.23  STDDEV: 0.02.
================================================"""
    scenario_passed = [
        ValidationScenarioParams(scenario_title="pgs in range",
                                 cmd_input_output_dict={cmd: CmdOutput(out=valid_out)}
                                 )
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="number of pgs too high",
                                 cmd_input_output_dict={cmd: CmdOutput(out=too_high_out)}
                                 ),
        ValidationScenarioParams(scenario_title="number of pgs too low",
                                 cmd_input_output_dict={cmd: CmdOutput(out=too_low_out)}
                                 )
    ]

    scenario_unexpected_system_output = [
        ValidationScenarioParams(scenario_title="invalid output format",
                                 cmd_input_output_dict={cmd: CmdOutput(out=unexpected_out)}
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
        ValidationTestBase.test_scenario_unexpected_system_output(self, scenario_params, tested_object)


class TestValidateCephBlockDBSize(ValidationTestBase):
    tested_type = ValidateCephBlockDBSize

    ceph_osd_cmd = "sudo ceph osd df -f json"
    jq_filter = '.nodes[] | (.id|tostring) + " " + ((.kb/1024/1024)|tostring) + " " + (.device_class // "unknown")'
    full_ceph_osd_cmd = "{} | jq -r '{}'".format(ceph_osd_cmd, jq_filter)

    # osd_out_1000gb = "0 1000.0"
    osd_out = """36 1370.41015625 nvme
39 1370.41015625 nvme
37 1370.41015625 nvme
41 1370.41015625 nvme
38 1370.41015625 nvme
40 1370.41015625 nvme
0 1797.9648361206055 ssd
3 1797.9648361206055 ssd
7 1797.9648361206055 ssd
9 1797.9648361206055 ssd
"""


    db_size_30gb = "ceph_block_db_size: 30720"
    db_size_1gb = "ceph_block_db_size: 1024"

    scenario_passed = [
        ValidationScenarioParams(
            scenario_title="Block DB size is in range",
            data_collector_dict={GetBlockDBSize: {Objectives.UC: db_size_30gb} },
            cmd_input_output_dict={
                full_ceph_osd_cmd: CmdOutput(out=osd_out)
            }
        )
    ]

    scenario_failed = [
        ValidationScenarioParams(
            scenario_title="Block DB size is too small",
            data_collector_dict={GetBlockDBSize: {Objectives.UC: db_size_1gb}},
            cmd_input_output_dict={
                full_ceph_osd_cmd: CmdOutput(out=osd_out)
            }
        )
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)
