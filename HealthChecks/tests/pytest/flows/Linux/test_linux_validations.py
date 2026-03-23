from __future__ import absolute_import
import os
import warnings

import pytest
from tests.pytest.tools.versions_alignment import Mock

from flows.Linux.Linux_validations import CheckDnsResolutionCbis, SelinuxMode, NoZombiesAllowed, \
    KernelVersionValidation, VerifyNginxWorkerConnection, SystemdServicesStatus, VerifyEtcFstabDirectoryForNFS, \
    NestedNamespaceMemoryLeak, CheckDnsResolutionNcs, CheckCronJobDuplicates, ValidateProcFsNfsdAbsenceInUcVm, \
    ValidatePipVersionConsistency, ValidateGatewayBrPublic, DiskMountValidator, FstabValidator
from tests.pytest.pytest_tools.operator.test_operator import CmdOutput
from tests.pytest.pytest_tools.operator.test_validation_base import ValidationTestBase, ValidationScenarioParams
from tools.global_enums import Objectives, Version
from tools.python_versioning_alignment import read_file

class TestNestedNamespaceMemoryLeak(ValidationTestBase):
    tested_type = NestedNamespaceMemoryLeak

    validation_cmd = "dmesg  |grep -c unregister_netdevice"

    scenario_passed = [
        ValidationScenarioParams(scenario_title="ok",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out="0", return_code=1)})
    ]
    scenario_failed = [
        ValidationScenarioParams(scenario_title="not_ok",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out="145", return_code=0)}),
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestCheckDnsResolutionNcs(ValidationTestBase):
    tested_type = CheckDnsResolutionNcs

    nslookup_bcmt_out_ipv4 = """Server:         172.31.0.8
Address:        172.31.0.8#53

Name:   bcmt-registry.bcmt
Address: 172.17.4.3
Name:   bcmt-registry.bcmt
Address: 172.17.4.4
Name:   bcmt-registry.bcmt
Address: 172.17.4.5
"""
    resolv_conf_ipv4 = """search bcmt cluster.local

nameserver 172.31.0.8
nameserver 172.31.0.9
nameserver 172.31.0.10
options ndots:3 timeout:1 rotate attempts:1
"""
    nslookup_bcmt_out_grep_ipv4 = "Address:        172.31.0.8#53"

    nslookup_bcmt_out_ipv6 = """Server: fc00:8:0:5e3:ffff:ffff:ffff:cf28.
Address: fc00:8:0:5e3:ffff:ffff:ffff:cf28#53.
.
Name: bcmt-registry.bcmt.
Address: 172.17.3.5.
Name: bcmt-registry.bcmt.
Address: 172.17.3.4.
Name: bcmt-registry.bcmt.
Address: 172.17.3.6.
"""
    resolv_conf_ipv6 = """search bcmt cluster.local.
.
nameserver fc00:8:0:5e3:ffff:ffff:ffff:cf28.
nameserver fc00:8:0:5e3:ffff:ffff:ffff:cf29.
nameserver fc00:8:0:5e3:ffff:ffff:ffff:cf2a.
options ndots:3 timeout:1 rotate attempts:1.
"""
    nslookup_bcmt_out_grep_ipv6 = "Address: fc00:8:0:5e3:ffff:ffff:ffff:cf28#53"

    scenario_passed = [
        ValidationScenarioParams(
            scenario_title="ipv4",
            cmd_input_output_dict={"nslookup bcmt-registry -timeout=1": CmdOutput(out=nslookup_bcmt_out_ipv4),
                                   "nslookup bcmt-registry | grep -i 'Address' | head -1": CmdOutput(
                                       out=nslookup_bcmt_out_grep_ipv4),
                                   "sudo cat /etc/resolv.conf": CmdOutput(out=resolv_conf_ipv4),
                                   "sudo ss -tulpn | grep '172.31.0.8:53' | grep -i 'coredns' | wc -l": CmdOutput(
                                       out="2"),
                                   "sudo ss -tulpn | grep '172.31.0.9:53' | grep -i 'coredns' | wc -l": CmdOutput(
                                       out="0"),
                                   "sudo ss -tulpn | grep '172.31.0.10:53' | grep -i 'coredns' | wc -l": CmdOutput(
                                       out="0")}),
        ValidationScenarioParams(
            scenario_title="ipv6",
            cmd_input_output_dict={"nslookup bcmt-registry -timeout=1": CmdOutput(out=nslookup_bcmt_out_ipv6),
                                   "nslookup bcmt-registry | grep -i 'Address' | head -1": CmdOutput(
                                       out=nslookup_bcmt_out_grep_ipv6),
                                   "sudo cat /etc/resolv.conf": CmdOutput(out=resolv_conf_ipv6),
                                   "sudo ss -tulpn | grep '\\[fc00:8:0:5e3:ffff:ffff:ffff:cf28\\]:53' | grep -i 'coredns' | wc -l": CmdOutput(
                                       out="0"),
                                   "sudo ss -tulpn | grep '\\[fc00:8:0:5e3:ffff:ffff:ffff:cf29\\]:53' | grep -i 'coredns' | wc -l": CmdOutput(
                                       out="2"),
                                   "sudo ss -tulpn | grep '\\[fc00:8:0:5e3:ffff:ffff:ffff:cf2a\\]:53' | grep -i 'coredns' | wc -l": CmdOutput(
                                       out="0")})
    ]
    scenario_failed = [
        ValidationScenarioParams(
            scenario_title="ipv4",
            cmd_input_output_dict={"nslookup bcmt-registry -timeout=1": CmdOutput(out=nslookup_bcmt_out_ipv4),
                                   "nslookup bcmt-registry | grep -i 'Address' | head -1": CmdOutput(
                                       out=nslookup_bcmt_out_grep_ipv4),
                                   "sudo cat /etc/resolv.conf": CmdOutput(out=resolv_conf_ipv4),
                                   "sudo ss -tulpn | grep '172.31.0.8:53' | grep -i 'coredns' | wc -l": CmdOutput(
                                       out="0"),
                                   "sudo ss -tulpn | grep '172.31.0.9:53' | grep -i 'coredns' | wc -l": CmdOutput(
                                       out="0"),
                                   "sudo ss -tulpn | grep '172.31.0.10:53' | grep -i 'coredns' | wc -l": CmdOutput(
                                       out="0")}),
        ValidationScenarioParams(
            scenario_title="ipv6",
            cmd_input_output_dict={"nslookup bcmt-registry -timeout=1": CmdOutput(out=nslookup_bcmt_out_ipv6),
                                   "nslookup bcmt-registry | grep -i 'Address' | head -1": CmdOutput(
                                       out=nslookup_bcmt_out_grep_ipv6),
                                   "sudo cat /etc/resolv.conf": CmdOutput(out=resolv_conf_ipv6),
                                   "sudo ss -tulpn | grep '\\[fc00:8:0:5e3:ffff:ffff:ffff:cf28\\]:53' | grep -i 'coredns' | wc -l": CmdOutput(
                                       out="0"),
                                   "sudo ss -tulpn | grep '\\[fc00:8:0:5e3:ffff:ffff:ffff:cf29\\]:53' | grep -i 'coredns' | wc -l": CmdOutput(
                                       out="0"),
                                   "sudo ss -tulpn | grep '\\[fc00:8:0:5e3:ffff:ffff:ffff:cf2a\\]:53' | grep -i 'coredns' | wc -l": CmdOutput(
                                       out="0")}),
        ValidationScenarioParams(scenario_title="missing Server",
                                 cmd_input_output_dict={"nslookup bcmt-registry -timeout=1": CmdOutput(
                                     out=nslookup_bcmt_out_ipv4.split("Server:")[1])}),
    ]
    scenario_unexpected_system_output = [ValidationScenarioParams(scenario_title="missing:",
                                                                  cmd_input_output_dict={
                                                                      "nslookup bcmt-registry -timeout=1": CmdOutput(
                                                                          out=nslookup_bcmt_out_ipv4),
                                                                      "nslookup bcmt-registry | grep -i 'Address' | head -1": CmdOutput(
                                                                          out="")}),
                                         ValidationScenarioParams(scenario_title="missing:",
                                                                  cmd_input_output_dict={
                                                                      "nslookup bcmt-registry -timeout=1": CmdOutput(
                                                                          out=nslookup_bcmt_out_ipv4),
                                                                      "nslookup bcmt-registry | grep -i 'Address' | head -1": CmdOutput(
                                                                          out="Address:xxx")})]

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


class TestCheckDnsResolutionCbis(ValidationTestBase):
    tested_type = CheckDnsResolutionCbis
    fqdn_list = ['www.google.com', 'google.com']

    validation_cmd = "sudo dig {} +nocomments  +noadditional +noanswer"

    out_bad = '''
; <<>> DiG 9.11.4-P2-RedHat-9.11.4-16.P2.el7_8.6 <<>> {} +nocomments +noadditional +noanswer
;; global options: +cmd
;; connection timed out; no servers could be reached
    '''

    out_good_1 = """ 
; <<>> DiG 9.11.4-P2-RedHat-9.11.4-16.P2.el7_8.6 <<>> {} +nocomments +noadditional +noanswer
;; global options: +cmd
;www.google.com.                        IN      A
;; Query time: 37 msec
;; SERVER: 135.239.25.18#53(135.239.25.18)
;; WHEN: Wed Mar 15 11:40:42 UTC 2023
;; MSG SIZE  rcvd: 59

"""
    out_good_2 = """    
; <<>> DiG 9.11.4-P2-RedHat-9.11.4-16.P2.el7_8.6 <<>> {} +nocomments +noadditional +noanswer
;; global options: +cmd
;www.google.comr.               IN      A
.                       10800   IN      SOA     a.root-servers.net. nstld.verisign-grs.com. 2023031500 1800 900 604800 86400
;; Query time: 45 msec
;; SERVER: 135.239.25.18#53(135.239.25.18)
;; WHEN: Wed Mar 15 11:48:46 UTC 2023
;; MSG SIZE  rcvd: 119
"""




    scenario_passed = [
        ValidationScenarioParams(scenario_title="Has DNS",
                                 cmd_input_output_dict={validation_cmd.format(fqdn_list[0]): CmdOutput(out=out_good_1.format(fqdn_list[0])),
                                                        validation_cmd.format(fqdn_list[1]): CmdOutput(out=out_good_1.format(fqdn_list[1]))}),
        ValidationScenarioParams(scenario_title="Has DNS - no real address",
                                 cmd_input_output_dict={validation_cmd.format(fqdn_list[0]): CmdOutput(out=out_good_2.format(fqdn_list[0])),
                                                        validation_cmd.format(fqdn_list[1]): CmdOutput(out=out_good_2.format(fqdn_list[1]))}),
        ValidationScenarioParams(scenario_title="Has DNS - Only one of the dig command passed",
                                 cmd_input_output_dict={validation_cmd.format(fqdn_list[0]): CmdOutput(out=out_bad.format(fqdn_list[0])),
                                                        validation_cmd.format(fqdn_list[1]): CmdOutput(out=out_good_2.format(fqdn_list[1]))}),
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="No DNS",
                                 cmd_input_output_dict={validation_cmd.format(fqdn_list[0]): CmdOutput(out=out_bad.format(fqdn_list[0])),
                                                        validation_cmd.format(fqdn_list[1]): CmdOutput(out=out_bad.format(fqdn_list[1]))})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestSelinuxMode(ValidationTestBase):
    tested_type = SelinuxMode

    validation_cmd = "sudo /usr/sbin/getenforce"

    scenario_passed = [
        ValidationScenarioParams(scenario_title="Enforced",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out="Enforcing")})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="Permissive",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out="Permissive")}),
        ValidationScenarioParams(scenario_title="Disabled",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out="Disabled")})
    ]

    scenario_unexpected_system_output = [
        ValidationScenarioParams(scenario_title="Unexpected State",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out="Unknown")})
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


class TestNoZombiesAllowed(ValidationTestBase):
    tested_type = NoZombiesAllowed

    validation_cmd = "top -bn 1 | grep Tasks:"
    out = "Tasks: 1188 total,   2 running, 1186 sleeping,   0 stopped,   {count} {zombie}"

    scenario_passed = [
        ValidationScenarioParams(scenario_title="There are less than 100 zombie processes",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out.format(count='85',zombie='zombie'))})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="There are more than 100 zombie processes",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out.format(count='150',zombie='zombie'))})
    ]

    scenario_unexpected_system_output = [
        ValidationScenarioParams(scenario_title="Unexpected Output less",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out.format(count='85',zombie='Unknown Output'))}),
        ValidationScenarioParams(scenario_title="Unexpected Output more",
                                 cmd_input_output_dict={
                                     validation_cmd: CmdOutput(out.format(count='150', zombie='Unknown Output'))})
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


class TestKernelVersionValidation(ValidationTestBase):
    tested_type = KernelVersionValidation
    validation_cmd = "sudo uname -r"

    #not relevent issue is only for 4.18
    out_3_10_version_low =  "3.10.0-293.el7.x86_64"

    out_4_18_version_exac ="4.18.0-372.2007201736.el7_7.emrs.altmvl.x86_64"
    out_4_18_version_high = "4.18.0-789.2007201736.el7_7.emrs.altmvl.x86_64"

    out_4_18_version_low = "4.18.0-240.2007201736.el7_7.emrs.altmvl.x86_64"
    out_4_18_version_low_2 = "4.18.0-348.2007201736.el7_7.emrs.altmvl.x86_64"
    #not a number
    out_not_expected = "4.18.0-x89_64999-2007201736.el7_7.emrs.altmvl.x86_64"

    scenario_passed = [

        ValidationScenarioParams(scenario_title="Kernel version is the recommended 3.10 372.",
                                 cmd_input_output_dict={
                                     validation_cmd: CmdOutput(out=out_4_18_version_exac)}),
        ValidationScenarioParams(scenario_title="Kernel version is the recommended main version is higher.",
                                 cmd_input_output_dict={
                                     validation_cmd: CmdOutput(out=out_4_18_version_high)})
    ]
    scenario_failed = [
    ValidationScenarioParams(scenario_title="Kernel version is the recommended main version is higher sub version low.",
                         cmd_input_output_dict={
                             validation_cmd: CmdOutput(out=out_4_18_version_low)}),
    ValidationScenarioParams(
                        scenario_title="Kernel version is the recommended main version is higher sub version low.",
                        cmd_input_output_dict={
                        validation_cmd: CmdOutput(out=out_4_18_version_low_2)})
    ]
    scenario_unexpected_system_output = [
        ValidationScenarioParams(scenario_title="Kernel version is the lower recommended 3.10 low sub version",
                                 cmd_input_output_dict={
                                     validation_cmd: CmdOutput(out=out_not_expected)})
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


class TestNginxWorkerConnection(ValidationTestBase):
    tested_type = VerifyNginxWorkerConnection

    validation_cmd = "sudo grep worker_connections /data0/podman/storage/volumes/nginx_etc_vol/_data/nginx.conf"

    out = "{connection} {value};"
    scenario_passed = [
        ValidationScenarioParams(scenario_title="There are correct optimal nginx worker connection",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(
                                     out.format(connection='worker_connections', value='1024'))})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="There are less than optimal nginx worker connection",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(
                                     out.format(connection='worker_connections', value='15'))})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestSystemdServicesStatus(ValidationTestBase):
    tested_type = SystemdServicesStatus

    current_dir_path = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(current_dir_path, 'inputs', 'systemctl_list-units.out')

    out = read_file(out_path)

    scenario_passed = [
        ValidationScenarioParams("no failures",
                                 cmd_input_output_dict={
                                     "systemctl list-units | grep failed": CmdOutput("", return_code=1)
                                 },
                                 tested_object_mock_dict={
                                     "get_host_roles": Mock(Objectives.UC)
                                 })
    ]

    scenario_failed = [
        ValidationScenarioParams("critical failures",
                                 cmd_input_output_dict={
                                     "systemctl list-units | grep failed": CmdOutput(
                                         out.format("NetworkManager-wait-online.service"))
                                 },
                                 tested_object_mock_dict={
                                     "get_host_roles": Mock(Objectives.UC)
                                 },
                                 failed_msg="The following services are at failed state:\n critical: []\n warning: "
                                            "[u'sys-devices-pci0000:00-0000:00:06.0-virtio2-virtio\\\\x2dports-vport2p1"
                                            ".device loaded failed failed /sys/devices/pci0000:00/0000:00:06.0/virtio2/"
                                            "virtio-ports/vport2p1']\n notification: [] "),
        ValidationScenarioParams("no critical failures",
                                 cmd_input_output_dict={
                                     "systemctl list-units | grep failed": CmdOutput(
                                         out.format("online.service"))},
                                 tested_object_mock_dict={
                                     "get_host_roles": Mock(Objectives.UC)
                                 },
                                 failed_msg="The following services are at failed state:\n critical: []\n "
                                            "warning: [u'sys-devices-pci0000:00-0000:00:06.0-virtio2-virtio\\\\"
                                            "x2dports-vport2p1.device loaded failed failed /sys/devices/pci0000:00/"
                                            "0000:00:06.0/virtio2/virtio-ports/vport2p1', "
                                            "u'online.service loaded failed failed Network Manager Wait Online']"
                                            "\n notification: [] ")
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

class TestVerifyEtcFstabDirectoryForNFS (ValidationTestBase):
    tested_type = VerifyEtcFstabDirectoryForNFS

    validation_cmd = "sudo cat /etc/fstab"
    out_bad = """
	# cat /etc/fstab
	LABEL=img-rootfs / xfs defaults 0 1
	/dev/mapper/vg_root-_data0 /data0 xfs prjquota 0 0
	10.88.73.50:/bigpool/nfs-szalon/backup /root/backup nfs defaults 0 0
	"""
    out_good_1 = """
	# cat /etc/fstab
	LABEL=img-rootfs / xfs defaults 0 1
	/dev/mapper/vg_root-_data0 /data0 xfs prjquota 0 0
	"""

    out_good_2 = """
	"""

    scenario_passed = [
        ValidationScenarioParams(scenario_title="good data no /root/backup",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out=out_good_1)}),
        ValidationScenarioParams(scenario_title="no data",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out=out_good_2)})
    ]

    scenario_failed = [
	    ValidationScenarioParams(scenario_title="bad data",
	                            cmd_input_output_dict={validation_cmd: CmdOutput(out=out_bad)}),
	]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestCheckCronJobDuplicates(ValidationTestBase):
    tested_type = CheckCronJobDuplicates
    cmd = "sudo crontab -u myuser -l"

    no_duplicates_out = """
    0 * * * * /home/stack/bin/backup_fetcher.sh > /dev/null 2>&1.
        0 1 * * * sudo /usr/bin/find /mnt/backup/* -mtime +30 -exec  rm -rf {} \; > /dev/null 2>&1.
        0 2 * * * sudo /usr/bin/find /home/stack/salt/var/cache/salt/master/jobs/ -type f -mtime +30 -exec rm {} \;.
        30 2 * * * sudo /usr/bin/find /home/stack/salt/var/cache/salt/master/jobs/ -type d -empty -exec rm -r {} \;.
        #Ansible: check CEPH FSID mismatch.
        */10 * * * * python /usr/share/cbis/overcloud/postdeploy/templates/zabbix/templates/check_fsid_mismatch.py > /tmp/fsid-stats.
    """

    duplicates_out = """
    0 * * * * /home/stack/bin/backup_fetcher.sh > /dev/null 2>&1.
        0 1 * * * sudo /usr/bin/find /mnt/backup/* -mtime +30 -exec  rm -rf {} \; > /dev/null 2>&1.
        0 2 * * * sudo /usr/bin/find /home/stack/salt/var/cache/salt/master/jobs/ -type f -mtime +30 -exec rm {} \;.
        0 1 * * * sudo /usr/bin/find /mnt/backup/* -mtime +30 -exec  rm -rf {} \; > /dev/null 2>&1.
    """

    no_jobs_err = "no crontab for myuser"

    scenario_passed = [
        ValidationScenarioParams(scenario_title="No duplicates",
                                 cmd_input_output_dict={cmd: CmdOutput(out=no_duplicates_out)},
                                 tested_object_mock_dict={"_get_users_to_check": Mock(return_value=set(["myuser"]))}),
        ValidationScenarioParams(scenario_title="No cron jobs found",
                                 cmd_input_output_dict={cmd: CmdOutput(out="", return_code=1, err=no_jobs_err)},
                                 tested_object_mock_dict={"_get_users_to_check": Mock(return_value=set(["myuser"]))})
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="duplication found",
                                 cmd_input_output_dict={cmd: CmdOutput(out=duplicates_out)},
                                 tested_object_mock_dict={"_get_users_to_check": Mock(return_value=set(["myuser"]))})
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

class TestValidateProcFsNfsdAbsenceInUcVm (ValidationTestBase):
    tested_type = ValidateProcFsNfsdAbsenceInUcVm

    check_mount_cmd = "mount | grep '/proc/fs/nfsd'"
    out_bad = "nfsd on /proc/fs/nfsd type nfsd (rw,relatime)"
    out_pass = ""


    scenario_passed = [
        ValidationScenarioParams(scenario_title="'/proc/fs/nfsd' is not mounted",
                                 cmd_input_output_dict={check_mount_cmd: CmdOutput(out=out_pass, return_code=1)}),
    ]

    scenario_failed = [
	    ValidationScenarioParams(scenario_title="'/proc/fs/nfsd' is mounted",
	                            cmd_input_output_dict={check_mount_cmd: CmdOutput(out=out_bad, return_code=0)}),
	]
    scenario_unexpected_system_output = [
        ValidationScenarioParams(scenario_title="Unexpected Output",
                                 cmd_input_output_dict={check_mount_cmd: CmdOutput(out=out_bad, return_code=2)}),
        ValidationScenarioParams(scenario_title="Unexpected Output",
                             cmd_input_output_dict={check_mount_cmd: CmdOutput(out=out_bad, return_code=1)})]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_unexpected_system_output(self, scenario_params, tested_object)


class TestValidatePipVersionConsistency(ValidationTestBase):
    tested_type = ValidatePipVersionConsistency

    scenario_passed = [
        ValidationScenarioParams(
            "All masters have same pip version",
            tested_object_mock_dict={
                "run_data_collector": Mock(return_value={
                    "master0": "22.3.1",
                    "master1": "22.3.1",
                    "master2": "22.3.1",
                }),
            }
        )
    ]

    scenario_failed = [
        ValidationScenarioParams(
            "One of the masters have different pip version",
            tested_object_mock_dict={
                "run_data_collector": Mock(return_value={
                    "master0": "22.3.1",
                    "master1": "22.3.1",
                    "master2": "22.3.2",
                }),
            }
        ),
        ValidationScenarioParams(
            "One of the masters have don't have pip installed",
            tested_object_mock_dict={
                "run_data_collector": Mock(return_value={
                    "master0": None,
                    "master1": "22.3.1",
                    "master2": "22.3.1",
                }),
            }
        ),
        ValidationScenarioParams(
            "None of the masters have pip installed",
            tested_object_mock_dict={
                "run_data_collector": Mock(return_value={
                    "master0": None,
                    "master1": None,
                    "master2": None,
                }),
            }
        )
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

class TestValidateGatewayBrPublic(ValidationTestBase):

    tested_type = ValidateGatewayBrPublic

    check_gateway_cmd = "sudo cat /etc/sysconfig/network-scripts/route-br-public"
    output = "default via 100.78.120.1 dev br-public"
    bad_output = "10.11.166.0/24 via 10.11.166.1 dev br-public"
    unexpected_output = ""

    check_gateway_cmd_2 = "sudo cat /etc/NetworkManager/system-connections/br-public.nmconnection | grep -i route"
    output_2 = """route1=0.0.0.0/0,10.11.166.1,0
    route1=::/0,2a00:8a00:4000:4f3::1,0"""
    bad_output_2 = """route1=0.0.0.0/0,10.11.166.1,0
    route1=,2a00:8a00:4000:4f3::1,0"""
    bad_output_3 = """route1=,10.11.166.1,0
    route1=::/0,2a00:8a00:4000:4f3::1,0"""

    scenario_passed = [
        ValidationScenarioParams("IPv4 default route is present in br-public NM connection for versions below CBIS 24",
            additional_parameters_dict={'file_exist': True},
            library_mocks_dict={"gs.get_version": Mock(return_value=Version.V23_10)},
            cmd_input_output_dict={check_gateway_cmd: CmdOutput(out=output)}
        ),
        ValidationScenarioParams("IPv4 and IPv6 default routes are present in br-public NM connection for CBIS 24 onward",
                                 tested_object_mock_dict={
                                     "run_data_collector": Mock(return_value={
                                         "undercloud": "True"
                                     })
                                 },
                                 additional_parameters_dict={'file_exist': True},
                                 library_mocks_dict={"gs.get_version": Mock(return_value=Version.V25)},
                                 cmd_input_output_dict={check_gateway_cmd_2: CmdOutput(out=output_2)}
                                 )
    ]
    scenario_failed = [
        ValidationScenarioParams("IPv4 default route is not present in br-public NM connection for versions below CBIS 24",
            tested_object_mock_dict={
                "run_data_collector": Mock(return_value={
                    "undercloud": "False"
                })
            },
            library_mocks_dict={"gs.get_version": Mock(return_value=Version.V23_10)},
            cmd_input_output_dict={check_gateway_cmd: CmdOutput(out=bad_output)},
            additional_parameters_dict={'file_exist': True}
        ),
        ValidationScenarioParams("IPv4 is defined, but no IPv6 default routes are present in br-public NM connection for CBIS 24 onward",
                                 tested_object_mock_dict={
                                     "run_data_collector": Mock(return_value={
                                         "undercloud": "True"
                                     })
                                 },
                                 library_mocks_dict={"gs.get_version": Mock(return_value=Version.V25)},
                                 cmd_input_output_dict={check_gateway_cmd_2: CmdOutput(out=bad_output_2)},
                                 additional_parameters_dict={'file_exist': True}
                                 ),
        ValidationScenarioParams(
            "IPv4 is not defined, but IPv6 default routes are present in br-public NM connection for CBIS 24 onward",
            tested_object_mock_dict={
                "run_data_collector": Mock(return_value={
                    "undercloud": "True"
                })
            },
            library_mocks_dict={"gs.get_version": Mock(return_value=Version.V25)},
            cmd_input_output_dict={check_gateway_cmd_2: CmdOutput(out=bad_output_3)},
            additional_parameters_dict = {'file_exist': True}
            )
    ]

    scenario_unexpected_system_output = [
        ValidationScenarioParams(
            "Invalid Input",
            library_mocks_dict={"gs.get_version": Mock(return_value=Version.V23_10)},
            cmd_input_output_dict={check_gateway_cmd: CmdOutput(out=unexpected_output)},
            additional_parameters_dict = {'file_exist': True}
        ),
        ValidationScenarioParams(
            "Invalid Input",
            tested_object_mock_dict={
                "run_data_collector": Mock(return_value={
                    "undercloud": "True"
                })
            },
            library_mocks_dict={"gs.get_version": Mock(return_value=Version.V25)},
            cmd_input_output_dict={check_gateway_cmd_2: CmdOutput(out=unexpected_output)},
            additional_parameters_dict = {'file_exist': True}
        ),
        ValidationScenarioParams(
            "Route br-public file path does not exist",
            library_mocks_dict={"gs.get_version": Mock(return_value=Version.V23_10)},
            cmd_input_output_dict={check_gateway_cmd_2: CmdOutput(out=output)},
            additional_parameters_dict={'file_exist': False}
        ),
        ValidationScenarioParams(
            "br-public connection file path does not exist",
            tested_object_mock_dict={
                "run_data_collector": Mock(return_value={
                    "undercloud": "True"
                })
            },
            library_mocks_dict={"gs.get_version": Mock(return_value=Version.V25)},
            cmd_input_output_dict={check_gateway_cmd_2: CmdOutput(out=output_2)},
            additional_parameters_dict={'file_exist': False}
        )
    ]

    def _init_mocks(self, tested_object):
        tested_object.file_utils.is_file_exist = Mock()
        tested_object.file_utils.is_file_exist.return_value = self.additional_parameters_dict['file_exist']

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_unexpected_system_output(self, scenario_params, tested_object)


class TestDiskMountValidator(ValidationTestBase):
    tested_type = DiskMountValidator
    LSBLK_CMD = "lsblk -p -P -o NAME,MOUNTPOINT,UUID"
    GLOBAL_FAIL_MSG = (
        "One or more critical application mount points (e.g., /data0 or /data0/etcd) are missing, "
        "or the underlying file system is corrupted (missing UUID)."
    )
    BASE_SUCCESS_OUTPUT = """
    NAME="/dev/mapper/vg_data0" MOUNTPOINT="/data0" UUID="4f236d7d-1177-4c16-96a1-290b54a07226"
    NAME="/dev/mapper/vg_etcd" MOUNTPOINT="/data0/etcd" UUID="719770ec-d470-457d-95bd-0593d4660d29"
    """
    FAIL_UUID_MISSING_OUTPUT = """
    NAME="/dev/mapper/vg_data0" MOUNTPOINT="/data0" UUID=""
    NAME="/dev/mapper/vg_etcd" MOUNTPOINT="/data0/etcd" UUID="719770ec-d470-457d-95bd-0593d4660d29"
    """
    EXPECTED_FAIL_MSG = (
            GLOBAL_FAIL_MSG +
            "\n\nDetails:\nUUID missing for mounted path /data0 (Filesystem integrity issue). "
    )
    validation_cmd = LSBLK_CMD
    scenario_passed = [
        ValidationScenarioParams(
            scenario_title="All critical mount points exist with UUIDs",
            cmd_input_output_dict={
                validation_cmd: CmdOutput(BASE_SUCCESS_OUTPUT)
            }
        )
    ]
    scenario_failed = [
        ValidationScenarioParams(
            scenario_title="Critical mount /data0 exists but UUID is missing",
            cmd_input_output_dict={
                validation_cmd: CmdOutput(FAIL_UUID_MISSING_OUTPUT)
            }
        )
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        tested_object.set_document()
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        tested_object.set_document()
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestFstabValidator(ValidationTestBase):
    tested_type = FstabValidator
    CAT_FSTAB_CMD = "cat /etc/fstab"
    GLOBAL_FAIL_MSG = "Missing or incorrect entries found for mount paths in /etc/fstab."
    SUCCESS_FSTAB_CONTENT = """
    LABEL=img-rootfs / xfs defaults 1 1
    UUID="df1f267d-ee20-4db2-9761-ba83f180b8cc" /data0 ext4 defaults 0 0
    UUID="c87fa79f-7ebd-490f-b8a0-fa5482b30108" /data0/etcd ext4 defaults 0 0
    # A comment line
    tmpfs /tmp tmpfs defaults 0 0
    """
    FAIL_DATA0_MISSING_CONTENT = """
    LABEL=img-rootfs / xfs defaults 1 1
    # UUID="df1f267d-ee20-4db2-9761-ba83f180b8cc" /data0 ext4 defaults 0 0  <- Commented out
    UUID="c87fa79f-7ebd-490f-b8a0-fa5482b30108" /data0/etcd ext4 defaults 0 0
    """
    FAIL_BOTH_MISSING_CONTENT = """
    LABEL=img-rootfs / xfs defaults 1 1
    tmpfs /tmp tmpfs defaults 0 0
    """
    EXPECTED_FAIL_DATA0 = (
            GLOBAL_FAIL_MSG +
            "\nMissing entries in /etc/fstab: '/data0'"
    )
    EXPECTED_FAIL_BOTH = (
            GLOBAL_FAIL_MSG +
            "\nMissing entries in /etc/fstab: '/data0', '/data0/etcd'"
    )
    validation_cmd = CAT_FSTAB_CMD
    scenario_passed = [
        ValidationScenarioParams(
            scenario_title="Both /data0 and /data0/etcd entries are present",
            cmd_input_output_dict={
                validation_cmd: CmdOutput(SUCCESS_FSTAB_CONTENT)
            }
        )
    ]
    scenario_failed = [
        ValidationScenarioParams(
            scenario_title="FAIL: /data0 entry is missing",
            cmd_input_output_dict={
                validation_cmd: CmdOutput(FAIL_DATA0_MISSING_CONTENT)
            }
        ),
        ValidationScenarioParams(
            scenario_title="FAIL: Both /data0 and /data0/etcd entries are missing",
            cmd_input_output_dict={
                validation_cmd: CmdOutput(FAIL_BOTH_MISSING_CONTENT)
            }
        )
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        tested_object.set_document()
        tested_object.file_utils.is_file_exist = Mock(return_value=True)
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        tested_object.set_document()
        tested_object.file_utils.is_file_exist = Mock(return_value=True)
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)



