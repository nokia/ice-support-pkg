from __future__ import absolute_import
from HealthCheckCommon.operations import *
import tools.global_logging as gl
from HealthCheckCommon.validator import Validator
from tools.Exceptions import UnExpectedSystemOutput
import re


class CheckZombieNodes(Validator):
    objective_hosts = [Objectives.UC]
    pingable = []
    ipmi_list = []

    def set_document(self):
        self._unique_operation_name = "check_zombie_nodes"
        self._title = "checking for old Overcloud nodes(zombies)"
        self._failed_msg = "TBD"
        self._severity = Severity.WARNING

        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        """
        based on the cbis code
        Check for old overcloud nodes that wasn't powered off properly.
        focus on ctlplane subnet 172.31.0.0/21
        """
        dhcp_start_ip = self._get_dhcp_range_from_conf('dhcp_start')
        ctrlplane_cidr = dhcp_start_ip.split('.')
        # Get the last octet of ctrlplane dhcp allocation pool start "_._._.X"
        cidr_start = ctrlplane_cidr.pop()
        # Get the first tree octets of ctrlplane subnet "X.X.X._"
        ctrlplane_cidr = ".".join(ctrlplane_cidr)
        dhcp_dhcp_end = self._get_dhcp_range_from_conf('dhcp_end')
        temp_cidr = dhcp_dhcp_end.split('.')
        # Get the last octet of ctrlplane dhcp allocation pool end "_._._.X"
        cidr_end = temp_cidr.pop()

        port_line = "source {}; openstack port list --column 'Fixed IP Addresses' --format value".format(self.system_utils.get_stackrc_file_path())
        out = self.get_output_from_run_cmd(port_line)
        managed_list = []
        for line in out.split("\n"):
            if ctrlplane_cidr in line:
                formatted_line = line.split(',')
                for field in formatted_line:
                    if 'ip_address' in field:
                        pattern = re.compile(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})')
                        ip = "\'" + pattern.findall(field)[0] + "\'"
                        managed_list.append(ip)
        for idx, ip in enumerate(managed_list):
            # Get rid of  '"' in the start and in the end of IP
            managed_list[idx] = ip[1:-1]
        pingline = \
            'for i in {' + cidr_start + '..' + cidr_end + '} ;do (ping ' \
            + ctrlplane_cidr + '.$i -c 1 -w 5  >/dev/null && echo "' \
            + ctrlplane_cidr + '.$i" &) ;done'
        status, out, err = self.run_cmd(pingline)

        answering_list = out.split()  # list of answered IPs
        # Find the IPs that are answered but not managed by neutron
        unmanaged_set = set(answering_list) - set(managed_list)
        unmanaged_list = list(unmanaged_set)
        if not unmanaged_list:
            # No old Overcloud Nodes, continue deployment'

            return True
        else:
            # Get IPMI address of the Zombie node if exists.
            self._failed_msg = ("There are servers answering to ping on ctrplane network (possible zombies).\n"
                                "Please power off these blades before any scale out operation.\n")

            # This part may throw ssh timeout
            try:
                for ip in unmanaged_list:
                    ipmi = self._get_ipmi(ip)
                    self._failed_msg += "Host IP: {} | IPMI IP: {}\n".format(ip, ipmi)
                    self._failed_msg = self._failed_msg + ("(ctrplane = {} ipmi ={})".format(ip, ipmi))
            except UnExpectedSystemOutput as e:
                msg = "Problem fetching the ipmi of the zombie nodes: {}".format(e)
                self._failed_msg += "\n" + msg
                gl.log_and_print(msg)
            return False

    def _get_ipmi(self, ip):
        cmd = "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=2 -F /dev/null -o GlobalKnownHostsFile=/dev/null -o" \
              " UserKnownHostsFile=/dev/null -F /dev/null  heat-admin@{} 'sudo ipmitool lan print'" \
              " 2>/dev/null".format(ip)
        results = self.get_output_from_run_cmd(cmd)

        if not results:
            raise UnExpectedSystemOutput(ip=self.get_host_ip(), cmd=cmd, output=results)
        all_lines = results.splitlines()

        for line in all_lines:
            key = line.split(":")[0].strip()
            if key == "IP Address":
                to_return = line.split(":")[1].strip()
                return to_return

        raise UnExpectedSystemOutput(ip=self.get_host_ip(), cmd=cmd, output=results,
                                     message="did not find 'IP Address' in the output")

    def _get_dhcp_range_from_conf(self, param_name):
        # in some systems dhcp_start is under the DEFAULT folder and in other under ctlplane-subnet
        cmd = "grep {} /home/stack/undercloud.conf |grep -v '#'".format(param_name)
        out = self.get_output_from_run_cmd(cmd)

        if out.count(param_name) != 1:
            msg = ""
            out_lines_list = out.splitlines()
            all_same = all(elem == out_lines_list[0] for elem in out_lines_list)

            if out.count(param_name) < 1:
                msg = "expected one occurrence of {}".format(param_name)

            elif not all_same:
                msg = "expected same occurrence of {}".format(param_name)

            if msg:
                raise UnExpectedSystemOutput(ip="UC", cmd=cmd, output=out, message=msg)
        returned_ip = out.splitlines()[0].split("=")[1].strip()

        return returned_ip
