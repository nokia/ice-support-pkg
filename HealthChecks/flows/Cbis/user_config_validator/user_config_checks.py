from __future__ import absolute_import
from HealthCheckCommon.operations import *
from HealthCheckCommon.validator import Validator
from tools.ConfigStore import ConfigStore
from tools.python_utils import PythonUtils
import tools.sys_parameters as gs
import tools.paths as paths
import re
import socket
from six.moves import range



class base_config_validator(Validator):
    def __init__(self, ip):

        Validator.__init__(self, ip)
        self._conf_dict = None

    def _set_conf_name(self):
        raise NotImplementedError

    def _set_conf_path(self):
        raise NotImplementedError

    def _set_document_config_validator(self):
        raise NotImplementedError

    def _read_conf(self, conf_format=None):
        raise NotImplementedError

    def _get_unique_operation_name(self):
        return "is_runtime_{}_match_configured_{}".format(self.objective, self.objective)

    def set_document(self):
        self.objective = self._set_document_config_validator()
        self.conf_name = self._set_conf_name()

        self._title = "Is the runtime {} matches the configured {} in the {} file".format(self.objective,
                                                                                          self.objective,
                                                                                          self.conf_name)

        # self._unique_operation_name = "is_runtime_{}_match_configured_{}".format(self.objective, self.objective)
        self._unique_operation_name = self._get_unique_operation_name()
        self._failed_msg = "The {} configured is {{}} but the runtime value is {{}}".format(self.objective)
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.NOTE]

    def _set_faild_msg(self, config_obj, real_obj):
        if not config_obj:
            self._failed_msg = "{} is not configured in {}".format(self.objective, self.conf_name)
        else:
            if PythonUtils.is_64_secret(config_obj):
                config_obj = PythonUtils.get_object_in_secret_format(config_obj)
            if PythonUtils.is_64_secret(real_obj):
                real_obj = PythonUtils.get_object_in_secret_format(real_obj)
            self._failed_msg = self._failed_msg.format(str(config_obj).strip(), str(real_obj).strip())

    def _get_conf(self, conf_format=None):
        if not self._conf_dict:
            self._conf_dict = self._read_conf(conf_format=conf_format)
        return self._conf_dict

    def _get_value_from_config(self):
        raise NotImplementedError

    def _get_value_from_system(self):
        raise NotImplementedError

    def is_validation_passed(self):
        real_val = self._get_value_from_system()
        config_val = self._get_value_from_config()
        if real_val == "":
            raise IOError

        if real_val == config_val:
            return True
        else:
            self._set_faild_msg(config_val, real_val)
            return False


class FormattedConfigValidator(base_config_validator):
    def _set_conf_name(self):
        path = self._set_conf_path()
        return path.split("/")[-1]

    def _read_conf(self, conf_format=None):
        file_path = self._set_conf_path()
        return self.get_dict_from_file(file_path, file_format=conf_format)


class BaseUserConfigValidator(base_config_validator):
    def _read_conf(self, conf_format=None):
        # todo - make sure can read the user conf from everywhere
        # change for One file open for all
        # user_input_file = CBIS_USER_CONFIG
        # with open(user_input_file) as file:
        #    self._user_dict = yaml.safe_load(file)
        return ConfigStore.get_cbis_user_config()

    def _set_conf_name(self):
        return "user_config.yaml"


###
# The Validations:
###

class is_cloud_name_in_user_config_correct(BaseUserConfigValidator):
    objective_hosts = [Objectives.UC]

    def __init__(self, ip):
        BaseUserConfigValidator.__init__(self, ip)

    def _set_document_config_validator(self):
        objective = 'cloud_name'
        self._severity = Severity.CRITICAL
        return objective

    def _get_value_from_config(self):
        to_return = self._get_conf()['CBIS']['common']['cloud_name']
        return to_return

    def is_validation_passed(self):
        config_val = self._get_value_from_config()
        if config_val == '' or config_val == 'cbis':
            return True
        self._set_faild_msg("cbis", config_val)
        return False


class IsDnsCorrect(BaseUserConfigValidator):
    objective_hosts = [Objectives.CONTROLLERS]

    def __init__(self, ip):
        BaseUserConfigValidator.__init__(self, ip)

    def _set_document_config_validator(self):
        objective = 'dns'
        return objective

    def _set_faild_msg(self, config_obj, real_obj):
        if not real_obj:
            self._failed_msg = "No DNS is configured"
            self._severity = Severity.ERROR
        else:
            if PythonUtils.is_64_secret(config_obj):
                config_obj = PythonUtils.get_object_in_secret_format(config_obj)
            if PythonUtils.is_64_secret(real_obj):
                real_obj = PythonUtils.get_object_in_secret_format(real_obj)
            self._failed_msg = self._failed_msg.format(str(config_obj).strip(), str(real_obj).strip())

    def _get_value_from_config(self):
        to_return = self._get_conf()['CBIS']['common']['dns_servers']
        return to_return

    def _get_value_from_system(self):
        # Get nameserver in IPV4 or IPv6
        ip_pattern = r"(?:nameserver\s+)((?:\d{1,3}\.){3}\d{1,3}|(?:[a-fA-F0-9:]+))"
        out = self.get_output_from_run_cmd("cat /etc/resolv.conf | grep 'nameserver '", timeout=60)
        matches = re.findall(ip_pattern, out)
        return matches

    def is_validation_passed(self):
        real_val = self._get_value_from_system()
        config_val = self._get_value_from_config()
        self._set_faild_msg(config_val, real_val)
        if real_val == config_val:
            return True
        else:
            if all(item in config_val for item in real_val):
                self._severity = Severity.WARNING
            self._set_faild_msg(config_val, real_val)
            return False


class IsNtpCorrect(BaseUserConfigValidator):
    objective_hosts = [Objectives.CONTROLLERS]

    def __init__(self, ip):
        BaseUserConfigValidator.__init__(self, ip)

    def _set_document_config_validator(self):
        objective = 'ntp'
        self._severity = Severity.NOTIFICATION
        return objective

    def _get_value_from_config(self):
        to_return = self._get_conf()['CBIS']['common']['ntp_servers']
        return to_return

    def _get_value_from_system(self):
        ntp_ips = []
        if gs.get_version() >= Version.V22:
            conf_file = '/etc/chrony.conf'
        else:
            conf_file = '/etc/ntp.conf'
        file_lines = self.file_utils.get_lines_in_file(conf_file)
        if file_lines:
            for line in file_lines:
                if line.startswith('#'):
                    continue
                line_matches = re.search(r"(server [\w.,-_]+)", line)
                if line_matches:
                    for item in line_matches.groups():
                        ntp_ips.append(item.strip('server '))
        return ntp_ips


class IsBackupNfsMountpointCorrect(BaseUserConfigValidator):
    objective_hosts = [Objectives.CONTROLLERS]

    def __init__(self, ip):
        BaseUserConfigValidator.__init__(self, ip)

    def _set_document_config_validator(self):
        objective = 'backup_nfs_mountpoint'
        self._severity = Severity.ERROR
        return objective

    def _get_value_from_config(self):
        to_return = self._get_conf()['CBIS']['openstack_deployment']['backup_nfs_mountpoint']
        return to_return

    def _get_value_from_system(self):
        cmd = "sudo crontab -l | grep 'CbisOvercloudDatabaseBackup' | cut -d' ' -f7"
        data_file = self.get_output_from_run_cmd(cmd, timeout=60)
        if data_file == "":
            raise UnExpectedSystemOutput(ip=self.get_host_ip(), cmd=cmd, output="No file returned from the command")
        out = self.get_output_from_run_cmd("dirname {}".format(data_file), timeout=60)
        return out.strip()


class IsBackupMinuteCorrect(BaseUserConfigValidator):
    objective_hosts = [Objectives.CONTROLLERS]

    def __init__(self, ip):
        BaseUserConfigValidator.__init__(self, ip)

    def _set_document_config_validator(self):
        objective = 'backup_minute'
        self._severity = Severity.ERROR
        return objective

    def _get_value_from_config(self):
        to_return = self._get_conf()['CBIS']['openstack_deployment']['backup_minute']
        return to_return

    def _get_value_from_system(self):
        cmd = "sudo crontab -l | grep 'CbisOvercloudDatabaseBackup' | cut -d' ' -f1"
        timeout = 60
        out = self.get_output_from_run_cmd(cmd, timeout=timeout)
        if out == "":
            raise UnExpectedSystemOutput(ip=self.get_host_ip(), cmd=cmd,
                                         output="CbisOvercloudDatabaseBackup not found in crontab")
        else:
            try:
                return int(out)
            except ValueError:
                self._set_cmd_info(cmd, timeout, 1, out, "")
                raise UnExpectedSystemOutput(ip=self._host_executor.ip,
                                             cmd=cmd,
                                             output="expected int found '{}'".format(out))


class IsBackupHourCorrect(BaseUserConfigValidator):
    objective_hosts = [Objectives.CONTROLLERS]

    def __init__(self, ip):
        BaseUserConfigValidator.__init__(self, ip)

    def _set_document_config_validator(self):
        objective = 'backup_hour'
        self._severity = Severity.ERROR
        return objective

    def _get_value_from_config(self):
        to_return = self._get_conf()['CBIS']['openstack_deployment']['backup_hour']
        return to_return

    def _get_value_from_system(self):
        cmd = "sudo crontab -l | grep 'CbisOvercloudDatabaseBackup' | cut -d' ' -f2"
        timeout = 60
        out = self.get_output_from_run_cmd(cmd, timeout=timeout)
        if out == "":
            raise UnExpectedSystemOutput(ip=self.get_host_ip(), cmd=cmd,
                                         output="CbisOvercloudDatabaseBackup not found in crontab")
        else:
            try:
                return int(out)
            except ValueError:
                self._set_cmd_info(cmd, timeout, 1, out, "")
                raise UnExpectedSystemOutput(ip=self._host_executor.ip,
                                             cmd=cmd,
                                             output="expected int found '{}'".format(out))


class IsTimeZoneCorrect(BaseUserConfigValidator):
    objective_hosts = [Objectives.UC]

    def __init__(self, ip):
        BaseUserConfigValidator.__init__(self, ip)

    def _set_document_config_validator(self):
        objective = 'time_zone'
        self._severity = Severity.NOTIFICATION
        return objective

    def _get_value_from_config(self):
        to_return = self._get_conf()['CBIS']['common']['time_zone']
        return to_return

    def _get_value_from_system(self):
        out = self.get_output_from_run_cmd("timedatectl status |grep zone", timeout=60)
        return out.strip()

    def is_validation_passed(self):
        real_val = self._get_value_from_system()
        conf_val = self._get_value_from_config()

        if conf_val in real_val:
            return True
        else:
            # print 'The config time zone: {} is different than the actual time zone value: {}'.format(conf_val, real_val)
            self._set_faild_msg(real_val, conf_val)
        return False


class IsHypervisorCidrCorrect(BaseUserConfigValidator):
    objective_hosts = [Objectives.HYP]

    def __init__(self, ip):
        BaseUserConfigValidator.__init__(self, ip)

    def _set_document_config_validator(self):
        objective = 'hypervisor_cidr'
        self._severity = Severity.CRITICAL
        return objective

    def _get_value_from_config(self):
        to_return = self._get_conf()['CBIS']['undercloud']['hypervisor_cidr']
        return to_return

    def _get_value_from_system(self):
        # out = self.get_output_from_run_cmd("sudo /sbin/ip a l br-public | awk '/inet / {print $2}'", timeout=60)
        out = self.run_and_get_the_nth_field("sudo /sbin/ip a l br-public |grep 'inet '", n=2, timeout=60)
        return out.strip()


class IsUndercloudCidrCorrect(BaseUserConfigValidator):
    objective_hosts = [Objectives.UC]

    def __init__(self, ip):
        BaseUserConfigValidator.__init__(self, ip)

    def _set_document_config_validator(self):
        objective = 'undercloud_cidr'
        self._severity = Severity.CRITICAL
        return objective

    def _get_value_from_config(self):
        to_return = self._get_conf()['CBIS']['undercloud']['undercloud_cidr']
        return to_return

    def _get_value_from_system(self):
        out = self.run_and_get_the_nth_field("/sbin/ip a l eth1 | grep 'inet '", n=2, timeout=60)
        return out.strip()


class IsGuestsMtuCorrect(BaseUserConfigValidator):
    objective_hosts = [Objectives.UC]

    def __init__(self, ip):
        BaseUserConfigValidator.__init__(self, ip)

    def _set_document_config_validator(self):
        objective = 'guests_mtu'
        self._severity = Severity.WARNING
        return objective

    def _get_value_from_config(self):
        to_return = self._get_conf()['CBIS']['common']['guests_mtu']
        return to_return

    def _get_value_from_system(self):
        return self.get_int_output_from_run_cmd("cat /sys/class/net/eth0/mtu", timeout=60)

    def is_validation_passed(self):
        real_val = self._get_value_from_system()
        config_val = self._get_value_from_config()
        if real_val == "":
            raise IOError

        # it can be vlan or xvlan
        if real_val == config_val or (config_val + 50) == real_val:
            return True
        else:
            self._set_faild_msg(config_val, real_val)
            return False


class IsHostUnderlayMtuCorrect(BaseUserConfigValidator):
    objective_hosts = [Objectives.HYP]

    def __init__(self, ip):
        BaseUserConfigValidator.__init__(self, ip)

    def _set_document_config_validator(self):
        objective = 'host_underlay_mtu'
        self._severity = Severity.WARNING
        return objective

    def _get_value_from_config(self):
        to_return = self._get_conf()['CBIS']['common']['host_underlay_mtu']
        return to_return

    def _get_value_from_system(self):
        return self.get_int_output_from_run_cmd("cat /sys/class/net/br-public/mtu", timeout=60)


class IsConfiguredVlansCorrect(BaseUserConfigValidator):
    #comment out du to false positive
    objective_hosts = [Objectives.CONTROLLERS]

    def __init__(self, ip):
        BaseUserConfigValidator.__init__(self, ip)

    def _set_document_config_validator(self):
        objective = 'vlans'
        self._severity = Severity.ERROR
        return objective

    def _get_value_from_config(self):
        configured_vlans = []
        subnets = self._get_conf()['CBIS']['subnets']
        for subnet, value in list(subnets.items()):
            if subnet == 'provisioning' and gs.get_version() >= Version.V22:
                continue
            if subnet.find("__", 0, 2) == -1:
                if 'vlan' in value:
                    vlan = value['vlan']
                    configured_vlans.append(vlan)
        return configured_vlans

    def _get_value_from_system(self):
        exist_vlans = []
        vlan_lines = self.get_output_from_run_cmd("sudo ifconfig -a | grep vlan", timeout=60).splitlines()

        for vlans_output in vlan_lines:
            vlan = vlans_output.split()[0].replace('vlan', '').replace(':', '')
            exist_vlans.append(int(vlan))

        return exist_vlans

    def is_validation_passed(self):
        real_val = set(self._get_value_from_system())
        conf_val = set(self._get_value_from_config())

        if real_val != conf_val:
            # in some cases (where Nuage is configured) having another extra vlan is ok.
            vlan_in_real_not_config = real_val - conf_val
            self._severity = Severity.NOTIFICATION
            if len(vlan_in_real_not_config) == 1:
                self._failed_msg = \
                    'The vlans that were configured in {} file are: {} but the runtime vlans are: {} note there is extara vlan {} Nuage network? '. \
                        format(paths.CBIS_USER_CONFIG, list(conf_val), list(real_val), vlan_in_real_not_config)
                return False

            self._failed_msg = \
                'The vlans that were configured in {} file are: {} but the runtime vlans are: {}'. \
                    format(paths.CBIS_USER_CONFIG, list(conf_val), list(real_val))
            return False
        return True


class IsConfiguredNetworkAddressCorrect(BaseUserConfigValidator):
    objective_hosts = [Objectives.CONTROLLERS]

    def __init__(self, ip):
        BaseUserConfigValidator.__init__(self, ip)

    def _set_document_config_validator(self):
        objective = 'network_addresses'
        self._severity = Severity.ERROR
        return objective

    def _get_value_from_config(self):
        configured_network_address = {}
        subnets = self._get_conf()['CBIS']['subnets']
        for subnet, value in list(subnets.items()):
            if subnet.find("__", 0, 2) == -1:
                if 'network_address' in value:
                    network_address = value['network_address']
                    if not isinstance(network_address, dict) and 'ctlplane_ip' not in network_address:
                        vlan_id = 'vlan{}'.format(value['vlan'])
                        if not configured_network_address.get(vlan_id):
                            configured_network_address[vlan_id] = []
                        configured_network_address[vlan_id].append(network_address)
        return configured_network_address

    def _get_value_from_system(self):
        exist_net_addresses = {}
        ip_commmands = ["sudo ip route  | grep '.*vlan.*proto kernel scope link src' | grep -v docker",
                        "sudo ip -6 route  | grep '.*vlan.*proto kernel' | grep -v docker | grep -v fe80"]
        for ip_commmand in ip_commmands:
            addresses_amount = self.get_output_from_run_cmd("{} | wc -l".format(ip_commmand), timeout=60)
            for i in range(1, int(addresses_amount) + 1):
                addresses_output = self.get_output_from_run_cmd("{} | sed -n {}p ".format(ip_commmand, i), timeout=60)
                vlan_id = re.search(r'(vlan\d+)', addresses_output).group(1)
                if not exist_net_addresses.get(vlan_id):
                    exist_net_addresses[vlan_id] = []
                exist_net_addresses[vlan_id].append(str(addresses_output.split()[0]))
        return exist_net_addresses

    def are_ipv6_cidrs_equal(self, real_val_vlan, conf_val_vlan):
        status = False
        for ip_cidr1 in real_val_vlan:
            for ip_cidr2 in conf_val_vlan:
                try:
                    ip1, ip1_prefix = ip_cidr1.split("/")
                    ip2, ip2_prefix = ip_cidr2.split("/")
                except ValueError:
                    continue
                # vlan might having more than one IP (as like including VIP), once there's a match function will return True
                if PythonUtils.set_to_ipv6_format(ip1) == PythonUtils.set_to_ipv6_format(ip2) and ip1_prefix == ip2_prefix:
                    status = True
                    break
            if status:
                break
        return status

    def is_having_ipv6(self, vlan_ips):
        if any(':' in ip for ip in vlan_ips):
            return True
        return False

    def compare_vlan_dict(self, real_val_dict, conf_val_dict):
        if real_val_dict == conf_val_dict:
            return True

        if set(real_val_dict.keys()) != set(conf_val_dict.keys()):
            return False

        for vlan in list(real_val_dict.keys()):
            status = False
            if real_val_dict[vlan] == conf_val_dict[vlan]:
                continue
            # check if there's common IP
            if set(real_val_dict[vlan]) & set(conf_val_dict[vlan]):
                continue
            if self.is_having_ipv6(real_val_dict[vlan]) and self.is_having_ipv6(conf_val_dict[vlan]):
                status = self.are_ipv6_cidrs_equal(real_val_dict[vlan], conf_val_dict[vlan])
            if status == False:
                return False
        return True


    def is_validation_passed(self):
        real_val_dict = self._get_value_from_system()
        conf_val_dict = self._get_value_from_config()

        if not self.compare_vlan_dict(real_val_dict, conf_val_dict):
            self._failed_msg = \
                ("The configured network addresses doesn't match with the actual ones.\n"
                 "Configured network addresses from user_config.yaml file are:\n{}\n"
                 "Actual network addresses are:\n{}").format(conf_val_dict, real_val_dict)
            return False
        return True
###
# Tests that were written but not in use
###

# class is_message_of_the_day_correct(BaseUserConfigValidator):
#     objective_hosts = [Objectives.CONTROLLERS]
#
#     def __init__(self, ip):
#         BaseUserConfigValidator.__init__(self, ip)
#
#     def _set_document_config_validator(self):
#         objective = 'message_of_the_day'
#         self._severity = Severity.WARNING
#         return objective
#
#     def _get_value_from_config(self):
#         to_return = self._get_conf()['CBIS']['openstack_deployment']['message_of_the_day']
#         return to_return
#
#     def _get_value_from_system(self):
#         out = self.get_output_from_run_cmd("cat /etc/motd", timeout=60)
#         return out.strip()


# class is_keyboard_correct(BaseUserConfigValidator):
#     objective_hosts = [Objectives.UC]
#
#     def __init__(self, ip):
#         BaseUserConfigValidator.__init__(self, ip)
#
#     def _set_document_config_validator(self):
#         objective = 'keyboard'
#         self._severity = Severity.ERROR
#         return objective
#
#     def _get_value_from_config(self):
#         to_return = self._get_conf()['CBIS']['common']['keyboard']
#         return to_return
#
#     def _get_value_from_system(self):
#         out = self.get_output_from_run_cmd("localectl | grep -oP 'Keymap: .*' |cut -d' ' -f2", timeout=60)
#         return out.strip()
# class is_cloud_name_correct(BaseUserConfigValidator):
#     objective_hosts = [Objectives.HYP]
#
#     def __init__(self, ip):
#         BaseUserConfigValidator.__init__(self, ip)
#
#     def _set_document_config_validator(self):
#         objective = 'cloud_name'
#         self._severity = Severity.WARNING
#         return objective
#
#     def _get_value_from_config(self):
#         to_return = self._get_conf()['CBIS']['common']['cloud_name']
#         return to_return
#
#     def _get_value_from_system(self):
#         out = self.get_output_from_run_cmd("cat /etc/hostname", timeout=60)
#         return out.strip()

# commented out this healthcheck due to positives - ICET-2450
class CheckWhetherHostGroupRootDeviceIsNull(Validator):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "hostgroup_rootdevice"
        self._title = "Validate that the rootdevice on all hostgroup is not null in cbis-config"
        self._failed_msg = "Please check the user_config.yaml in the undercloud. The following hostgroups :{} has issue with root device value"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.UPGRADE]

    def get_root_device_value(self):
        final_hostgroup = gs.get_hostgroup_name()
        bad_hostgroup = []
        count = 0
        for hostgroup in final_hostgroup:
            root_device_value = ConfigStore.get_cbis_user_config()['CBIS']['host_group_config'][hostgroup]['root_device']
            if root_device_value is None or root_device_value == "null":
                bad_hostgroup.append(hostgroup)
            else:
                count += 1
        return count, bad_hostgroup

    def is_validation_passed(self):
        hostgroup_count = len(gs.get_hostgroup_name())
        root_device_count, bad_hostgroup = self.get_root_device_value()
        if hostgroup_count == root_device_count:
            return True
        else:
            self._failed_msg = self._failed_msg.format(bad_hostgroup)
            return False