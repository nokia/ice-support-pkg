from __future__ import absolute_import
from operator import itemgetter

from tools import adapter

from HealthCheckCommon.validator import InformatorValidator
from flows.Storage.ceph.CephInfo import *
from flows.Cbis.user_config_validator.user_config_checks import *
from six.moves import range


class CephValidation(Validator):
    def is_prerequisite_fulfilled(self):
        self.append_domain_tags()
        return CephInfo.is_ceph_used()

    def append_domain_tags(self):
        self._implication_tags.append(ImplicationTag.APPLICATION_DOMAIN)

    def get_ceph_host_name(self):
        return self.get_host_name().lower()

    def get_host_osds(self):
        result_dict = CephInfo.get_osd_tree()
        if not result_dict.get('is_passed', True):
            return result_dict
        return result_dict.get(self.get_ceph_host_name())

    def get_host_osds_conf(self):
        return CephInfo.get_osd_conf().get(self.get_ceph_host_name())['osds']

    def get_first_ceph_osd_file(self):
        # for ncs version >= 24.7
        return_code, ceph_osd_files, err = self.run_cmd('sudo ls /var/lib/ceph/osd/ceph-*/run')
        if return_code == 0:
            return ceph_osd_files.split()[0]
        # for ncs version < 24.7
        return '/usr/share/ceph-osd-run.sh'

    def get_host_ceph_conf(self):
        return CephInfo.get_osd_conf().get(self.get_ceph_host_name())['conf']

    def get_host_osd_conf_section(self, osd_name):
        host_conf = self.get_host_osds_conf()
        return host_conf.get(osd_name)

    def get_host_osd_conf_value(self, osd_name, key_name):
        osd_conf_section = self.get_host_osd_conf_section(osd_name) or {}
        k = key_name.lower()
        return osd_conf_section.get(k)


class CephHasConfFile(CephValidation):
    objective_hosts = [Objectives.STORAGE]

    def set_document(self):
        self._unique_operation_name = "is_ceph_has_conf"
        self._title = "Check if ceph has a configuration file"
        self._failed_msg = "No ceph configuration file: {}".format(CephPaths.CEPH_CONF)
        self._severity = Severity.CRITICAL

        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.ACTIVE_PROBLEM]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        return self.file_utils.is_file_exist(CephPaths.CEPH_CONF)


class CephHasOnlyOneConfFile(CephValidation):
    objective_hosts = [Objectives.STORAGE]

    def set_document(self):
        self._unique_operation_name = "ceph_has_only_one_conf"
        self._title = "Check if ceph has only one configuration file"
        self._failed_msg = "Ceph has more than one file"
        self._severity = Severity.CRITICAL

        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.ACTIVE_PROBLEM]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        ceph_conf_files_cmd = "sudo ls /etc/ceph/*.conf"
        out = self.get_output_from_run_cmd(ceph_conf_files_cmd, timeout=30).strip()
        out_list = out.splitlines()
        if len(out_list) > 1:
            self._failed_msg = "Ceph has more than one file"
            return False
        return True


class CephOsdTreeWorks(CephValidation):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.CONTROLLERS],
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "ceph_osd_tree_valid"
        self._title = "Check if ceph osd tree working"
        self._failed_msg = "ceph osd tree is not working"
        self._severity = Severity.CRITICAL

        self._implication_tags = [ImplicationTag.SYMPTOM, ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        cmd = "sudo ceph osd tree"
        return self.run_cmd_return_is_successful(cmd, timeout=30)


class CephConfServiceNameValid(CephValidation):
    objective_hosts = [Objectives.STORAGE]

    def set_document(self):
        self._unique_operation_name = "ceph_conf_service_name_valid"
        self._title = "Check if ceph osd configured service name is valid"
        self._failed_msg = "TBD"
        self._severity = Severity.CRITICAL

        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.RISK_BAD_CONFIGURATION,
                                  ImplicationTag.SYMPTOM]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        if ImplicationTag.APPLICATION_DOMAIN in self.get_implication_tags():
            self._implication_tags.remove(ImplicationTag.APPLICATION_DOMAIN)
        if not self.get_host_osds_conf():
            self._failed_msg = "Failed to get host {} OSDs".format(self.get_ceph_host_name())
            return False
        result = []
        host_osds = self.get_host_osds()
        if host_osds and not host_osds.get('is_passed', True):
            self._failed_msg = host_osds.get('failed_msg', '')
            return False
        if self.get_host_osds_conf():
            for osd_name in host_osds:
                service_name = self.get_host_osd_conf_value(osd_name, 'SERVICE_NAME') or ""
                if service_name and not PythonUtils.is_string_match_pattern(service_name, r"ceph-osd@\w+.service"):
                    result.append("{} - {}".format(osd_name, service_name))
            if len(result):
                self._failed_msg = "following osds service name is not valid:\n{}".format("\n".join(result))
                return False
        return True


class CephConfCrushLocationExists(CephValidation):
    objective_hosts = [Objectives.STORAGE]

    def set_document(self):
        self._unique_operation_name = "ceph_conf_crush_location_exists"
        self._title = "Check if each OSD is configured with crush_location"
        self._failed_msg = "TBD"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.RISK_BAD_CONFIGURATION,
                                  ImplicationTag.SYMPTOM]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        if ImplicationTag.APPLICATION_DOMAIN in self.get_implication_tags():
            self._implication_tags.remove(ImplicationTag.APPLICATION_DOMAIN)
        osd_pool_options = ['fast', 'common']
        self.add_to_validation_log(
            ("Validation will run only if {} pools are configured - checking if fast pool is enabled".format(
                osd_pool_options)))
        ceph_osd_cmd = "sudo ceph osd lspools"
        out = self.get_output_from_run_cmd(ceph_osd_cmd)
        if 'volumes-fast' in out:
            self.add_to_validation_log(("Fast pool is configured"))
            host_osds = self.get_host_osds()
            if host_osds and not host_osds.get('is_passed', True):
                self._failed_msg = host_osds.get('failed_msg', '')
                return False
            for osd in host_osds:
                osd_conf_section = self.get_host_osd_conf_section(osd)
                if not osd_conf_section:
                    continue
                try:
                    crush_location_key_list = [key for key in list(osd_conf_section.keys()) if 'crush' in key]
                    if len(crush_location_key_list) == 0:
                        self._failed_msg = "Ceph OSD {} isn't configured with crush_location key:\n" \
                                           "OSD {} configuration:\n{}".format(osd, osd,
                                                                              json.dumps(osd_conf_section, indent=4))
                        return False
                    if len(crush_location_key_list) > 1:
                        self._failed_msg = "Ceph OSD {} is configured with more than one 'crush_location' key.\n" \
                                           "OSD {} configuration:\n{}".format(osd, osd,
                                                                              json.dumps(osd_conf_section, indent=4))
                        return False
                    crush_location_key = crush_location_key_list[0]
                    crush_location_value = osd_conf_section.get(crush_location_key)
                    crush_location_dict = self.convert_string_to_dict(str_to_dict=crush_location_value)
                    osd_pool = crush_location_dict['root']
                    if any(osd_pool == pool for pool in osd_pool_options):
                        continue
                    else:
                        self.add_to_validation_log(
                            'Ceph OSD {} configuration section: {}'.format(osd, osd_conf_section))
                        self._failed_msg = "Ceph OSD {} '{}' is configured with {} pool, while it should be configured with 'fast' / 'common' option". \
                            format(osd, crush_location_key, osd_pool)
                        return False
                except:
                    raise UnExpectedSystemOutput(self.get_host_name(), ceph_osd_cmd, out,
                                                 message="problem in getting OSD {} crush location:\n {}".format(osd,
                                                                                                                 osd_conf_section))
            self.add_to_validation_log(("Verify 'ceph osd tree' isn't set with 'default' pool"))
            out = self.get_output_from_run_cmd("sudo ceph osd tree")
            if 'default' in out:
                self._failed_msg = "Ceph osd tree is set with 'default' pool, while it should be configured with 'fast' / 'common' option"
                return False
        else:
            self.add_to_validation_log(("Fast pool isn't configued"))
        return True

    def convert_string_to_dict(self, str_to_dict):
        return dict(item.split('=') for item in str_to_dict.split(' '))


class IsCephHealthOk(CephValidation):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.ONE_CONTROLLER],
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "is_ceph_health_ok"
        self._title = "Check if ceph health is ok"
        self._failed_msg = "Ceph health is not ok.\n"
        self._severity = Severity.CRITICAL

        self._implication_tags = [ImplicationTag.PERFORMANCE, ImplicationTag.ACTIVE_PROBLEM,
                                  ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        checks = {}
        get_ceph_health_cmd = "sudo ceph health -f json"
        out = self.get_output_from_run_cmd(get_ceph_health_cmd, timeout=30)
        health_dict = json.loads(out)
        status = health_dict.get("status") or health_dict.get("overall_status")
        if "HEALTH_OK" in status:
            return True

        if health_dict.get("checks"):
            for check in health_dict["checks"]:
                checks[check] = {
                    "severity": health_dict["checks"][check]["severity"],
                    "message": health_dict["checks"][check]["summary"]["message"]
                }
        elif health_dict.get("summary"):
            for check in health_dict["summary"]:
                checks[check["summary"]] = {
                    "severity": check["severity"]
                }

        self._failed_msg += json.dumps(checks, indent=4)

        return False


class IsCephOSDsNearFull(CephValidation):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.ONE_CONTROLLER],
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER]
    }
    threshold_warning = 80
    threshold_critical = 90

    def set_document(self):
        self._unique_operation_name = "is_ceph_osds_near_full"
        self._title = "Check if ceph osds disk usage near full"
        self._failed_msg = ('There are OSDs disk usage near or already over the limit.\n'
                            'This indiciates there is a risk ahead or already materialized, so need to react fast for ceph storage.\n'
                            'Here is a list of problematic osds in this environment currently over limit: \n ')
        self._severity = Severity.WARNING

        self._implication_tags = [ImplicationTag.RISK_RESOURCE_CLEANING_RECOMMENDED, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def set_failed_msg(self):
        if self._severity == Severity.CRITICAL:
            self._failed_msg += ('90% : CRITICAL\n')
        else:
            self._failed_msg += ('80% : WARNING\n')

    def is_validation_passed(self):
        empty_list = ""
        get_ceph_osd_df = "sudo ceph osd df -f json "
        out = self.get_output_from_run_cmd(get_ceph_osd_df, timeout=30)
        if out:
            osd_df = json.loads(out)
            nodes = sorted(osd_df.get("nodes"), key=itemgetter('utilization'))
            for node in nodes:
                usage = float(node['utilization'])
                if usage <= self.threshold_warning:
                    continue
                elif usage > self.threshold_critical:
                    # Severty.WARNING is the defult
                    self._severity = Severity.CRITICAL
                empty_list += "%-10s%-10s\n" % (node['name'], str(node['utilization']))
            is_passed = bool(not empty_list)
            if not is_passed:
                self.set_failed_msg()
                self._failed_msg += empty_list[:-1]
        else:
            self._failed_msg = "empty results"
            is_passed = False
        return is_passed


class MonitorsCount(CephValidation):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.ONE_CONTROLLER],
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER, Objectives.ONE_MANAGER]
    }

    def set_document(self):
        self._unique_operation_name = "monitor_count"
        self._title = "Check if monitors count is ok"
        self._failed_msg = "There are only {mon_count} ceph monitors. Required count is 3"
        self._severity = Severity.CRITICAL

        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PRE_OPERATION,
                                  ImplicationTag.PERFORMANCE]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        if gs.get_version() >= Version.V24_11:
            get_ceph_mon_service_status = "sudo ceph orch ps --daemon_type mon -f json-pretty"
            ceph_mon_service_status = self.get_output_from_run_cmd(get_ceph_mon_service_status,
                                                                   message="Failed to get the status of ceph mon services")
            ceph_mon_service_status = json.loads(ceph_mon_service_status)
            mon_count = len(ceph_mon_service_status)
            if mon_count != 3:
                self._failed_msg = self._failed_msg.format(mon_count=mon_count)
                return False
        else:
            mon_list = self.get_mon_list()
            for mon_name in mon_list:
                get_ceph_mon_cmd = "sudo ceph daemon {} mon_status".format(mon_name)
                out = self.get_output_from_run_cmd(get_ceph_mon_cmd, timeout=30, add_bash_timeout=True)
                mon_dict = json.loads(out)
                mons_array = mon_dict.get("monmap").get('mons')
                mon_count = len(mons_array)
                if mon_count != 3:
                    self._failed_msg = self._failed_msg.format(mon_count=mon_count)
                    return False
        return True

    def get_mon_list(self):
        mon_prefix = "mon."
        mon_list = []
        ls_ceph_mon_cmd = "sudo ls /var/lib/ceph/mon"
        ceph_mon_dump_cmd = "sudo ceph mon dump"
        ceph_mon_files_list = self.get_output_from_run_cmd(ls_ceph_mon_cmd, add_bash_timeout=True).split()
        mon_dump_res_list = self.get_output_from_run_cmd(ceph_mon_dump_cmd, add_bash_timeout=True).splitlines()
        for mon_dump_line in mon_dump_res_list:
            if mon_prefix in mon_dump_line:
                mon_name = mon_dump_line[mon_dump_line.index(mon_prefix):]
                for mon_file in ceph_mon_files_list:
                    if mon_name.split(mon_prefix)[1] in mon_file:
                        mon_list.append(mon_name)
        if not len(mon_list):
            raise UnExpectedSystemOutput(
                ip=self.get_host_ip(), cmd="{};\n{};".format(ls_ceph_mon_cmd, ceph_mon_dump_cmd), output=mon_list,
                message="mon daemon list is empty,a mismatch between{} and {}".format(ceph_mon_files_list,
                                                                                      mon_dump_res_list))
        return mon_list


class MonitorsHealth(CephValidation):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.CONTROLLERS],
        Deployment_type.NCS_OVER_BM: [Objectives.MASTERS]
    }

    def set_document(self):
        self._unique_operation_name = "monitor_health"
        self._title = "Check if monitors service is running"
        self._failed_msg = "Check if monitors service is running failed."
        self._severity = Severity.CRITICAL

        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PRE_OPERATION,
                                  ImplicationTag.PERFORMANCE]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        get_ceph_mon_service_status = "systemctl status ceph-mon@{}.service".format(self.get_host_name().lower())
        return_code, out, err = self.run_cmd(get_ceph_mon_service_status)
        active_state = re.findall("Active: (.*)", out)

        if len(active_state) != 1:
            raise UnExpectedSystemOutput(self.get_host_ip(), get_ceph_mon_service_status, out,
                                         "Expected to have only 1 Active: in out.")
        res = True
        active_state = active_state[0]

        if 'running' not in active_state:
            self._failed_msg = 'ceph mon is not running on {}, active state: {}'.format(self.get_host_name(),
                                                                                        active_state)
            res = False

        if return_code != 0:
            self._failed_msg += "\nThe command {} failed, return code: {}, error: {}".format(
                get_ceph_mon_service_status, return_code, err)
            res = False

        return res


class MonitorsHealthCephAdm(CephValidation):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "monitors_health_ceph_adm"
        self._title = "Check if monitor services are running"
        self._failed_msg = "Check if monitor services are running failed:\n"
        self._severity = Severity.CRITICAL

        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PRE_OPERATION,
                                  ImplicationTag.PERFORMANCE]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        missing_or_invalid = []

        get_ceph_mon_service_status = "sudo ceph orch ps --daemon_type mon -f json-pretty"
        ceph_mon_service_status = self.get_output_from_run_cmd(get_ceph_mon_service_status,
                                                               message="Failed to get the status of ceph mon services").strip()

        ceph_mon_service_status = json.loads(ceph_mon_service_status)
        ceph_mon_services = {entry['hostname']: entry['status_desc'] for entry in ceph_mon_service_status}

        master_nodes = list(gs.get_host_executor_factory().get_host_executors_by_roles(Objectives.MASTERS).keys())

        for hostname in master_nodes:
            if hostname not in ceph_mon_services:
                missing_or_invalid.append("{} is missing on mon services".format(hostname))
            elif ceph_mon_services[hostname] != "running":
                missing_or_invalid.append(
                    "{} status is {}, expected 'running'".format(hostname, ceph_mon_services[hostname]))

        if missing_or_invalid:
            self._failed_msg += '\n'.join(missing_or_invalid)
            return False

        return True


class IsCephConfExist(CephValidation):
    objective_hosts = [Objectives.STORAGE]

    def set_document(self):
        self._unique_operation_name = "is_ceph_conf_exist"
        self._title = "Check if each ceph osd from ceph osd tree has a configuration section"
        self._failed_msg = "TBD"
        self._severity = Severity.CRITICAL

        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.SYMPTOM]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        if ImplicationTag.APPLICATION_DOMAIN in self.get_implication_tags():
            self._implication_tags.remove(ImplicationTag.APPLICATION_DOMAIN)
        host_osds = self.get_host_osds()
        if host_osds:
            if not host_osds.get('is_passed', True):
                self._failed_msg = host_osds.get('failed_msg', '')
                return False
            missing_conf_osd = [osd for osd in host_osds if not self.get_host_osd_conf_section(osd)]
            if len(missing_conf_osd):
                self._failed_msg = \
                    "conf section of following osds is missing : [{}].\n" \
                    "This is a known bug in CBIS 19MP2 - fixed in 19MP4".format(",".join(missing_conf_osd))
                return False
        return True


class IsOSDsUp(CephValidation):
    objective_hosts = [Objectives.STORAGE]

    def set_document(self):
        self._unique_operation_name = "is_osds_up"
        self._title = "Check if all osds in the host are up"
        self._failed_msg = "TBD"
        self._severity = Severity.CRITICAL

        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PERFORMANCE]

    def is_validation_passed(self):
        host_osds = self.get_host_osds()
        if host_osds:
            if not host_osds.get('is_passed', True):
                self._failed_msg = host_osds.get('failed_msg', '')
                return False
            down_osds = [osd for osd in host_osds if host_osds[osd]["status"] == "down"]
            if len(down_osds):
                self._failed_msg = "The following osds are in down state: [{}]".format(",".join(down_osds))
                return False
        return True


class OsdHostsVsCephHosts(CephValidation):
    objective_hosts = [Objectives.STORAGE]

    def set_document(self):
        self._unique_operation_name = "osd_hosts_same_as_ceph_hosts"
        self._title = "Verify hosts from OSD tree are the same as Ceph hosts from ansible"
        self._failed_msg = "There is a difference between hosts from OSD tree and hosts from ansible storage."
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PERFORMANCE]

    def is_validation_passed(self):
        storage_hosts_by_osd = []
        pool_name_list = self.get_enabled_pools()
        cmd = "sudo ceph osd tree | grep -i host"
        out = gs.get_host_executor_factory().run_command_on_first_host_from_selected_roles(cmd,
                                                                                           roles=CephInfo.get_relevant_roles())
        for line in out.splitlines():
            if line == "":
                continue
            host_name = line.split()[3]
            if pool_name_list:
                for pool_name in pool_name_list:
                    if pool_name in host_name:
                        host_name = host_name.replace('{}-'.format(pool_name), '')
                    else:
                        continue
            storage_hosts_by_osd.append(host_name)
        storage_hosts_by_role = list(gs.get_host_executor_factory().get_host_executors_by_roles(
            roles=[Objectives.STORAGE]).keys())
        storage_hosts_diff = set(storage_hosts_by_osd) ^ set(storage_hosts_by_role)
        if storage_hosts_diff:
            self._failed_msg += '\nHosts from OSD tree are: {}.\nHosts from ansible storage are: {}'.format(
                storage_hosts_by_osd, storage_hosts_by_role)
            return False
        self.add_to_validation_log('Hosts from OSD tree are the same as hosts from ansible storage')
        return True

    def get_enabled_pools(self):
        pool_name_list = []
        for pool_name in ["fast", "common"]:
            cmd = 'sudo ceph osd tree | grep "root {}"'.format(pool_name)
            result_dict = gs.get_host_executor_factory().execute_cmd_by_roles(cmd=cmd,
                                                                              roles=CephInfo.get_relevant_roles())
            if result_dict[list(result_dict.keys())[0]]["out"]:
                pool_name_list.append(pool_name)
        return pool_name_list


class IsOSDsWeightOK(CephValidation):
    objective_hosts = [Objectives.ONE_STORAGE]

    ACCEPTABLE_RANGE = 0.05  # in percent

    def set_document(self):
        self._unique_operation_name = "is_osds_weight_ok"
        self._title = "Check if osds weight are within the ceph recommendation margins"
        self._failed_msg = "The following OSDs weight not in acceptable range:\n"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.PERFORMANCE]

    def is_validation_passed(self):
        if ImplicationTag.APPLICATION_DOMAIN in self.get_implication_tags():
            self._implication_tags.remove(ImplicationTag.APPLICATION_DOMAIN)
        ceph_osd_df = self.get_ceph_osd_df_info()
        problematic_osds = self.get_problematic_osds_weight(ceph_osd_df)
        if problematic_osds:
            for osd_id in problematic_osds:
                if problematic_osds[osd_id]['min_acceptable'] == 0 and problematic_osds[osd_id]['max_acceptable'] == 0:
                    self._failed_msg += "OSD '{}' - current weight is {}, but OSD size is 0\n".format(osd_id,
                                                                                                      problematic_osds[
                                                                                                          osd_id][
                                                                                                          'current_weight'])
                else:
                    self._failed_msg += "OSD '{}' - current weight is {}, while it should be greater than {} and smaller than {}\n". \
                        format(osd_id, problematic_osds[osd_id]['current_weight'],
                               problematic_osds[osd_id]['min_acceptable'], problematic_osds[osd_id]['max_acceptable'])
            return False
        return True

    def get_problematic_osds_weight(self, ceph_osd_df):
        problematic_osds = {}
        for osd_id in ceph_osd_df:
            current_weight = ceph_osd_df[osd_id]['current_weight']
            max_acceptable = ceph_osd_df[osd_id]['max_acceptable']
            min_acceptable = ceph_osd_df[osd_id]['min_acceptable']
            if not (current_weight < max_acceptable and current_weight > min_acceptable):
                problematic_osds[osd_id] = {}
                problematic_osds[osd_id]['current_weight'] = current_weight
                problematic_osds[osd_id]['max_acceptable'] = float(max_acceptable)
                problematic_osds[osd_id]['min_acceptable'] = float(min_acceptable)
        return problematic_osds

    def get_ceph_osd_df_info(self):
        ceph_osd_df_info = {}
        get_ceph_osd_df = "sudo ceph osd df -f json"
        out = self.get_output_from_run_cmd(get_ceph_osd_df)
        if out:
            osd_df = json.loads(out)
            nodes = osd_df.get('nodes')
            for node in nodes:
                osd_id = str(node['id'])
                ceph_osd_df_info[osd_id] = {}
                ceph_osd_df_info[osd_id]['osd_size'] = osd_size = int(node['kb'])
                ceph_osd_df_info[osd_id]['calculated_weight'] = calculated_weight = self.convert_kb_to_tb(osd_size)
                ceph_osd_df_info[osd_id]['current_weight'] = float(node['crush_weight'])
                ceph_osd_df_info[osd_id].update(self.get_accetble_range_for_osd(calculated_weight))
        return ceph_osd_df_info

    def convert_kb_to_tb(self, kb_value):
        return float(float(float(kb_value / 1024) / 1024) / 1024)

    def get_accetble_range_for_osd(self, calculated_weight):
        # calculation taken from /usr/share/cbis/undercloud/tools/ceph-create-osd.sh
        osd_range = {}
        osd_range['max_acceptable'] = calculated_weight * (1 + self.ACCEPTABLE_RANGE)
        osd_range['min_acceptable'] = calculated_weight * (1 - self.ACCEPTABLE_RANGE)
        return osd_range


class IsOsdDiskConfApplied(CephValidation):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.STORAGE]
    }

    def set_document(self):
        self._unique_operation_name = "is_osd_disk_conf_applied"
        self._title = "check if configured osd disk is applied"
        self._failed_msg = "TBD"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.SYMPTOM, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def get_device_osd_map(self):
        osd_dev_lines = []
        docker_or_podman = adapter.docker_or_podman()
        containers_list = self.get_output_from_run_cmd(
            "sudo {docker_or_podman} ps | grep ceph | awk '{{print $NF}}'".format(
                docker_or_podman=docker_or_podman)).splitlines()
        for container in containers_list:
            out = self.get_output_from_run_cmd(
                "sudo {docker_or_podman} exec --user=root {container} mount | grep '/osd/ceph-[0-9]' ".format(
                    docker_or_podman=docker_or_podman, container=container), add_bash_timeout=True)
            osd_dev_lines.extend(out.splitlines())
        return osd_dev_lines

    def is_validation_passed(self):
        result_dict = {
            'device conf is not applied': [],
            'containers are not running': []
        }
        host_osds = self.get_host_osds()
        if host_osds:
            if not host_osds.get('is_passed', True):
                self._failed_msg = host_osds.get('failed_msg', '')
                return False
            osd_dev_dict = {}
            osd_dev_lines = self.get_device_osd_map()
            for line in osd_dev_lines:
                dev, osd_str = re.findall(r"/dev/\w+|ceph-\d+", line)
                osd_number = re.findall(r"\d+", osd_str)[0]
                osd_dev_dict[osd_number] = dev.replace("/dev/", "")
            for osd in host_osds:
                if not self.get_host_osd_conf_section(osd):
                    continue
                conf_dev = self.get_host_osd_conf_value(osd, "OSD_DEVICE")
                if osd in osd_dev_dict:
                    real_dev = osd_dev_dict[osd]
                    if conf_dev != real_dev:
                        result_dict['device conf is not applied'].append(
                            "osd.{} : conf : {}, mount: {}".format(osd, conf_dev, real_dev))
                else:
                    result_dict['containers are not running'].append(osd)
        message = ""
        for problem_description in result_dict:
            osds_list = result_dict[problem_description]
            if len(osds_list):
                message += "following osds {problem_description}:\n{osds_list}\n".format(
                    problem_description=problem_description, osds_list="\n".join(osds_list))
        if message:
            self._failed_msg = message
            return False
        return True


class IsOsdSystemctlValid(CephValidation):
    objective_hosts = [Objectives.STORAGE]

    def set_document(self):
        self._unique_operation_name = "is_osd_systemctl_valid"
        self._title = "check if osd systemctl processes are valid"
        self._failed_msg = "TBD"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        result = {
            "not configured": [],
            "configured but does not run": []
        }
        host_osds = self.get_host_osds()
        if host_osds and not host_osds.get('is_passed', True):
            self._failed_msg = host_osds.get('failed_msg', '')
            return False
        passed = True
        if host_osds and self.get_host_osds_conf():
            get_osd_systemctl_processes = r"systemctl list-units | grep -E 'ceph-osd@\w+'"
            out = self.get_output_from_run_cmd(get_osd_systemctl_processes)
            running_osds_services = re.findall(r"ceph-osd@\w+.service", out)
            conf_service_osd_map = {}
            for osd in host_osds:
                configured_service = self.get_host_osd_conf_value(osd, "SERVICE_NAME")
                if configured_service:
                    conf_service_osd_map[configured_service] = osd
                    if configured_service not in running_osds_services:
                        result["configured but does not run"].append(osd)
            result["not configured"] = [service for service in running_osds_services
                                        if service not in conf_service_osd_map]
            self._failed_msg = ""
            for res in result:
                if len(result[res]):
                    passed = False
                    self._failed_msg += "Following osd services are {}:\n{}\n".format(res, "\n".join(result[res]))
        return passed


class OsdJournalError(CephValidation):
    objective_hosts = [Objectives.STORAGE]

    def set_document(self):
        self._unique_operation_name = "osd_journal_errors_last_hour"
        self._title = "Check if osds had journal errors 1 hour ago"
        self._failed_msg = "TBD"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PERFORMANCE,
                                  ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        host_osds = self.get_host_osds()
        if not host_osds:
            return True
        if not host_osds.get('is_passed', True):
            self._failed_msg = host_osds.get('failed_msg', '')
            return False
        osd_service_pattern = CephInfo.get_osd_service(osd_id='', pattern=True)
        problematic_osd_cmd = ("sudo journalctl --since '1 hour ago' | grep -Ei '(fail|error).*{}|{}.*(fail|error)'".
                               format(osd_service_pattern, osd_service_pattern))
        return_code, problematic_osd_out, err = self.run_cmd(problematic_osd_cmd, timeout=120)
        if problematic_osd_out:
            res_list = []
            for osd in host_osds:
                osd_service_name = self.get_host_osd_conf_value(osd, "SERVICE_NAME")
                if not osd_service_name:
                    osd_service_name = CephInfo.get_osd_service(osd_id=osd)
                if osd_service_name in problematic_osd_out:
                    info_str = "Service Name: {}\n".format(osd_service_name)
                    osd_journal_info = self.get_output_from_run_cmd(
                        "sudo journalctl -u '{}' --since '1 hour ago' -n 15".format(osd_service_name))
                    info_str += "Journal Messages:\n{}\n".format(osd_journal_info)
                    res_list.append(info_str)
            if res_list:
                self._failed_msg = "\n\n".join(res_list)
                return False
        return True


class ValidateCephTempFilesCount(CephValidation):
    objective_hosts = [Objectives.STORAGE, Objectives.CONTROLLERS]

    def set_document(self):
        self._unique_operation_name = "validate_ceph_temp_files_count"
        self._title = "Check if /var/lib/ceph/tmp contains too many empty directories"
        self._failed_msg = "TBD"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        find_empty_dirs_count_cmd = "sudo find /var/lib/ceph/tmp/ -type d -empty | wc -l"
        exit_code, out, err = self.run_cmd(find_empty_dirs_count_cmd, timeout=100)
        if not PythonUtils.is_string_match_pattern(out, r"^\d+$"):
            raise UnExpectedSystemOutput(self.get_host_name(), find_empty_dirs_count_cmd, out)
        empty_dir_count = int(out)
        if empty_dir_count > 800:
            self._failed_msg = \
                "You have more than 800 empty directories in /var/lib/ceph/tmp/ ({})\n" \
                "you can list them by : sudo find /var/lib/ceph/tmp/ -type d -empty\n" \
                "This may cause OSD recreation failure, or existing OSDs start failures.\n" \
                "These directories should be deleted.\n".format(empty_dir_count)
            return False
        return True


class CephMgrStandbyCheck(CephValidation):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.CONTROLLERS],
        Deployment_type.NCS_OVER_BM: [Objectives.MASTERS, Objectives.MANAGERS]
    }

    def set_document(self):
        self._unique_operation_name = "Ceph_Manager_Standby_Validation"
        self._title = "Ceph Manager Standby Validation"
        self._failed_msg = "Make sure two ceph-mgr standby's exist"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.SYMPTOM]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_prerequisite_fulfilled(self):
        if CephValidation.is_prerequisite_fulfilled(self):
            if gs.get_deployment_type() is Deployment_type.NCS_OVER_BM and not gs.is_ncs_central() and \
                    Objectives.MASTERS not in self.get_host_roles():
                return False
            return True
        return False

    def is_validation_passed(self):
        status = True
        ceph_s_mgr = "sudo ceph -s -f json"
        out = self.get_output_from_run_cmd(ceph_s_mgr, timeout=10)
        ceph_s_mgr_dict = json.loads(out)["mgrmap"]
        if ceph_s_mgr_dict.get("standbys"):
            if len(ceph_s_mgr_dict.get("standbys")) != 2:
                status = False
            return status
        elif ceph_s_mgr_dict.get("num_standbys"):
            if ceph_s_mgr_dict.get("num_standbys") != 2:
                status = False
            return status
        if status == False:
            self._failed_msg = "Make sure two ceph-mgr standby's exist"
            return status
        return False


class CheckVarLibCephDir(CephValidation):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.STORAGE, Objectives.CONTROLLERS],
        Deployment_type.NCS_OVER_BM: [Objectives.MASTERS, Objectives.STORAGE]
    }

    def set_document(self):
        self._unique_operation_name = "is_var_lib_ceph_dir_exists"
        self._title = "Check if /var/lib/ceph dir exists"
        self._failed_msg = "/var/lib/ceph directory doesn't exist"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.RISK_BAD_CONFIGURATION,
                                  ImplicationTag.SYMPTOM]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        return self.file_utils.is_dir_exist("/var/lib/ceph")


class IsOsdInContainerSameAsInConf(CephValidation):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.STORAGE]
    }

    def set_document(self):
        self._unique_operation_name = "is_container_osd_same_as_in_conf"
        self._title = "check if containerized osd same as in conf"
        self._failed_msg = "Dockerized ceph osd is not the same as in the ceph.conf"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.SYMPTOM]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        host_osds = self.get_host_osds()
        if host_osds and not host_osds.get('is_passed', True):
            self._failed_msg = host_osds.get('failed_msg', '')
            return False
        for osd in host_osds:
            if not self.get_host_osd_conf_section(osd):
                continue
            conf_dev = self.get_host_osd_conf_value(osd, "OSD_DEVICE")
            osd_conf_block_dev = self.get_host_osd_conf_value(osd, "BLOCK_DEVICE")
            osd_conf_block_db = self.get_host_osd_conf_value(osd, "OSD_BLUESTORE_BLOCK_DB")
            osd_conf_block_wal = self.get_host_osd_conf_value(osd, "OSD_BLUESTORE_BLOCK_WAL")
            osd_conf_service_name = self.get_host_osd_conf_value(osd, "SERVICE_NAME")
            device = self.get_device_from_ceph_conf(osd_conf_service_name, conf_dev, osd)
            docker_or_podman = adapter.docker_or_podman()
            cmd = 'sudo {docker_or_podman} ps --filter name={device}'.format(docker_or_podman=docker_or_podman,
                                                                             device=device)
            out = self.get_output_from_run_cmd(cmd)
            osd_container_id_list = self.get_osd_containers_id(device_name=device, osd_containers_list=out.splitlines())

            if len(osd_container_id_list) != 1:
                raise UnExpectedSystemOutput(self.get_host_name(), cmd, osd_container_id_list,
                                             'There are: {} osd device containers, expected to have one. osd:{}'.format(
                                                 len(osd_container_id_list), osd))
            osd_container_id = osd_container_id_list[0].replace('\n', '')
            container_osd_dev = self.get_output_from_run_cmd(
                'sudo {docker_or_podman} exec {osd_container_id} ls -l /var/lib/ceph/osd/ceph-{osd}'.
                format(docker_or_podman=docker_or_podman, osd_container_id=osd_container_id, osd=osd),
                add_bash_timeout=True)
            splitted = container_osd_dev.split()
            for i, w in enumerate(splitted):
                if w in ['block', 'block.db', 'block.wal'] and splitted[i + 1] != "->":
                    raise UnExpectedSystemOutput(self.get_host_name(), cmd, "", 'osd:{} as no {} link'.format(osd, w))
                if w == 'block':
                    block_dev = splitted[i + 2]
                    if gs.get_version() >= Version.V22:
                        docker_block_dev = block_dev
                    else:
                        docker_block_dev = self.get_output_from_run_cmd('sudo readlink -f {}'.format(block_dev))
                    if docker_block_dev.split() != osd_conf_block_dev.split():
                        self._failed_msg = 'Dockerized ceph osd {} is not the same as in the ceph.conf {}'.format(
                            docker_block_dev, osd_conf_block_dev)
                        return False
                elif w == 'block.db':
                    block_db = splitted[i + 2]
                    docker_block_db = self.get_output_from_run_cmd('sudo readlink -f {}'.format(block_db))
                    if docker_block_db.split() != osd_conf_block_db.split():
                        self._failed_msg = 'Dockerized ceph osd {} is not the same as in the ceph.conf {}'.format(
                            docker_block_db, osd_conf_block_db)
                        return False
                elif w == 'block.wal':
                    block_wal = splitted[i + 2]
                    docker_block_wal = self.get_output_from_run_cmd('sudo readlink -f {}'.format(block_wal))
                    if docker_block_wal.split() != osd_conf_block_wal.split():
                        self._failed_msg = 'Dockerized ceph osd {} is not the same as in the ceph.conf {}'.format(
                            docker_block_wal, osd_conf_block_wal)
                        return False

        return True

    def get_osd_containers_id(self, device_name, osd_containers_list):
        osd_containers_id = []
        str_format = "{device_name}$".format(device_name=device_name)
        if device_name == "sda":
            str_format = "sda2$"
        for container in osd_containers_list:
            container_name = container.split()[-1]
            container_id = container.split()[0]
            if re.search(str_format, container_name):
                osd_containers_id.append(container_id)

        if device_name == "sda" and len(osd_containers_id) == 0:
            raise UnExpectedSystemOutput(self.get_host_ip(), "sudo cat {}".format(CephPaths.CEPH_CONF), "",
                                         "Bad partition! /sda shall be on root partition not for osd, "
                                         "osds should start from /sdc, only in hci setups it should be sda2")
        return osd_containers_id

    def get_device_from_ceph_conf(self, osd_conf_service_name, conf_dev, osd):
        if gs.get_version() < Version.V22 and conf_dev and 'nvme' not in conf_dev:
            return conf_dev[:-1]
        else:
            if osd_conf_service_name is None:
                raise UnExpectedSystemOutput(self.get_host_ip(), "sudo cat {}".format(CephPaths.CEPH_CONF), "",
                                             "not have SERVICE_NAME in conf keys for osd: {}".format(osd))
            splitted_name = osd_conf_service_name.split('@')
            device_prefix = splitted_name[0]
            device_suffix = splitted_name[1].split('.')[0]
            if gs.get_version() < Version.V22:
                return "-".join([device_prefix, self.get_host_name(), device_suffix])
            return "^{}-{}$".format(device_prefix, device_suffix)


class IsOsdAuthSameAsOsdTree(CephValidation):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.ONE_CONTROLLER],
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "is_osd_auth_same_as_osd_tree"
        self._title = "Validate if ceph auth list is same to ceph osd tree"
        self._failed_msg = "Ceph auth list is not same to ceph osd tree.\n"
        self._severity = Severity.CRITICAL

        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.SYMPTOM]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        cmd = "sudo ceph osd tree -f json"
        get_ceph_osd_tree = self.get_output_from_run_cmd(cmd, timeout=10)
        cmd = "sudo ceph auth list -f json"
        get_ceph_auth_list = self.get_output_from_run_cmd(cmd, timeout=10)

        osd_tree_dict = json.loads(get_ceph_osd_tree)
        auth_list_dict = json.loads(get_ceph_auth_list)

        osd_tree_list = [str(i['name']) for i in osd_tree_dict['nodes'] if str(i['type']) == 'osd']
        osd_tree_list.sort()
        auth_list = [str(i['entity']) for i in auth_list_dict['auth_dump'] if 'osd.' in str(i['entity'])]
        auth_list.sort()

        if osd_tree_list != auth_list:
            self._failed_msg += "osd_tree_list:\n{}.\n\nauth_list:\n{}".format(" ".join(osd_tree_list),
                                                                               " ".join(auth_list))
            return False
        return True


class CheckMultipleMondirs(CephValidation):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.CONTROLLERS],
        Deployment_type.NCS_OVER_BM: [Objectives.MASTERS]
    }

    def set_document(self):
        self._unique_operation_name = "Check_whether_multiple_mon_dir_exists_on_the_same_host"
        self._title = "Check whether multiple mon dir exist on the same host"
        self._failed_msg = "Multiple monitor directories exist on the same host"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.SYMPTOM]

    def is_validation_passed(self):
        mon_dir_path = "/var/lib/ceph/mon/"
        list_dir_cmd = "sudo ls {}".format(mon_dir_path)
        if gs.get_version() >= Version.V24_11:
            fsid = CephInfo.get_fsid()
            mon_dir_path = "/var/lib/ceph/{}/".format(fsid)
            list_dir_cmd = "sudo ls {} | grep mon.$(hostname)".format(mon_dir_path)
        out = self.get_output_from_run_cmd(list_dir_cmd, timeout=10)
        if not out:
            raise UnExpectedSystemOutput(self.get_host_ip(), list_dir_cmd, out,
                                         "There is no mon directory in {}".format(mon_dir_path))
        out_split = out.split()
        if len(out_split) > 1:
            self._failed_msg = "Multiple monitor directories exist on the same host (in {})".format(mon_dir_path)
            return False
        return True


class CheckPoolSize(CephValidation):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.CONTROLLERS],
        Deployment_type.NCS_OVER_BM: [Objectives.MASTERS]

    }

    # TODO: check rep-factor in the use storage-environment.yaml and compare that CephPoolDefaultSize
    #  is same as runtime
    def set_document(self):
        self._unique_operation_name = "check_ceph_replication_factor_is_at_least_2"
        self._title = "check ceph replication factor is at least 2"
        self._failed_msg = "TBD"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.RISK_NO_HIGH_AVAILABILITY, ImplicationTag.ACTIVE_PROBLEM]

    # ceph-medic validation
    def is_validation_passed(self):
        cmd = "sudo ceph osd pool ls detail -f json"
        pools_dict = self.get_dict_from_command_output(cmd, out_format='json')
        problematic_pools = []
        for pool in pools_dict:
            if pool['size'] < 2:
                problematic_pools.append(pool['pool_name'])
        if len(problematic_pools):
            self._failed_msg = 'ceph replication factor is less than 2 in following pools:{}'.format(
                '\n'.join(problematic_pools))
            return False
        return True


class CheckVarLibCephDirOwner(CephValidation):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.CONTROLLERS, Objectives.STORAGE],
        Deployment_type.NCS_OVER_BM: [Objectives.MASTERS, Objectives.STORAGE]
    }

    def set_document(self):
        # ceph-medic validation
        self._unique_operation_name = "is_var_lib_ceph_dir_owned_by_ceph_user_or_not"
        self._title = "is var lib ceph directory owned by ceph user or not"
        self._failed_msg = "/var/lib/ceph dir should be owned by ceph user and should be part of ceph group"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.SYMPTOM]

    def is_validation_passed(self):
        cmd = "sudo stat -c '%U %G' /var/lib/ceph/"
        out = self.get_output_from_run_cmd(cmd, timeout=10)
        out_split = out.split()
        if out_split[0] != 'ceph' or out_split[1] != 'ceph':
            self._failed_msg = "/var/lib/ceph dir should be owned by ceph user and should be part of ceph group"
            return False
        return True


class CheckRightSocketNum(CephValidation):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.CONTROLLERS],
        Deployment_type.NCS_OVER_BM: [Objectives.MASTERS]
    }

    def __init__(self, ip):
        CephValidation.__init__(self, ip)
        self.set_param()

    def set_param(self):
        self._expected_number_of_sockets = None
        self._socket_phrase_name_to_grep = None

    def base_document(self):
        self._failed_msg = ""
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.ACTIVE_PROBLEM,
                                  ImplicationTag.PERFORMANCE]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def return_socket_number(self, socket_type):
        host_out = self.get_host_name()
        socket_path = '/var/run/ceph/'
        if gs.get_version() >= Version.V24_11:
            socket_path += CephInfo.get_fsid()
            hosts = r'{}.*\.asok'.format(host_out)
        else:
            hosts = '{}.asok'.format(host_out)
        cmd = "sudo ls {} | egrep -w '{}'".format(socket_path, hosts)
        _, out, _ = self.run_cmd(cmd=cmd, timeout=10)
        out_split = out.split()
        socket_type_out_lines = list([l for l in out_split if "ceph-{}.".format(socket_type) in l])

        return len(socket_type_out_lines)

    def is_validation_passed(self):
        flg_has_monitor = self.return_socket_number(
            self._socket_phrase_name_to_grep) == self._expected_number_of_sockets
        self._failed_msg = "we expect {} socket exists for the {} ".format(self._expected_number_of_sockets,
                                                                           self._socket_phrase_name_to_grep)
        return flg_has_monitor


class CheckMonCount(CheckRightSocketNum):

    def set_param(self):
        self._expected_number_of_sockets = 1
        self._socket_phrase_name_to_grep = 'mon'

    def set_document(self):
        self.base_document()
        self._unique_operation_name = "Check_whether_mon_socket_exits_or_not"
        self._title = "Check whether mon socket exists or not"


class CheckMgrCount(CheckRightSocketNum):

    def set_param(self):
        self._expected_number_of_sockets = 1
        self._socket_phrase_name_to_grep = 'mgr'

    def set_document(self):
        self.base_document()
        self._unique_operation_name = "Check_whether_mgr_socket_exists_or_not"
        self._title = "Check whether mgr socket exists or not"


class CheckMdsCount(CheckRightSocketNum):

    def set_param(self):
        self._expected_number_of_sockets = 1
        self._socket_phrase_name_to_grep = 'mds'

    def set_document(self):
        self.base_document()
        self._unique_operation_name = "Check_whether_mds_socket_exists_or_not"
        self._title = "Check whether mds socket exists or not"


# TODO: refactor
class CheckMinOsdNodes(CephValidation):
    objective_hosts = [Objectives.ONE_CONTROLLER, Objectives.ONE_MASTER]

    def set_document(self):
        self._unique_operation_name = "Check_min_osd_nodes_in_the_cluster"
        self._title = "Check min osd nodes in the cluster"
        self._failed_msg = "Less than three osd nodes present in the cluster"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION, ImplicationTag.PERFORMANCE,
                                  ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        cmd = "sudo ceph osd tree | grep -i host"
        out = self.get_output_from_run_cmd(cmd, timeout=10)
        out_split = out.split()
        counter = 0
        for i in range(3, len(out_split), 4):
            counter += 1
        if counter < 3:
            self._failed_msg += " - Having only {} osd nodes".format(counter)
            return False
        return True


class CephCpuQuotaCheck(CephValidation):
    objective_hosts = [Objectives.STORAGE]

    def set_document(self):
        self._unique_operation_name = "validate_ceph_cpu_quota_if_configured"
        self._title = "Check if cpu-quota is configured on storage nodes"
        self._failed_msg = "TBD"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.PERFORMANCE]

    def is_validation_passed(self):
        ceph_osd_file = self.get_first_ceph_osd_file()
        if not self.file_utils.is_file_exist(ceph_osd_file):
            self._failed_msg = "File {} not found".format(ceph_osd_file)
            return False
        find_cpu_quota_cmd = "cat {} | grep cpu-quota".format(ceph_osd_file)
        exit_code, out, err = self.run_cmd(find_cpu_quota_cmd, timeout=100)
        if exit_code == 0:
            self._failed_msg = "Limiting CPU quota on ceph OSDs leads to performance issues.\n" \
                               "FIX for CBIS19: available in SP3-PP1."
            return False
        return True


class CephOsdMemoryAllocation(CephValidation):
    objective_hosts = [Objectives.STORAGE]
    OSD_MEMORY_THRESHOLD = 5

    def set_document(self):
        self._unique_operation_name = "validate_ceph_osd_memory_allocation"
        self._title = "Check if sufficient memory limit is set to the OSDs"
        self._failed_msg = "Failed to fetch Ceph OSD memory limit"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.PERFORMANCE]

    def get_ceph_osd_memory_value(self):
        ceph_osd_file = self.get_first_ceph_osd_file()
        find_memory_quota_cmd = r"sudo cat {} | grep '\--memory'".format(ceph_osd_file)
        out = self.get_output_from_run_cmd(find_memory_quota_cmd, timeout=100)
        if out:
            memory_limit = self.verify_memory_in_gb(out, ceph_osd_file)
        else:
            memory_limit = self.OSD_MEMORY_THRESHOLD + 1
        return memory_limit

    def verify_memory_in_gb(self, memory_value, ceph_osd_file):
        if re.findall(r'(\d+)[g]', memory_value):
            memory_limit = int(re.findall(r'(\d+)[g]', memory_value)[0])
        else:
            self._failed_msg = "Failed to find Ceph OSD memory limit from {} - memory should be in 'g' unit size".format(
                ceph_osd_file)
            memory_limit = None
        return memory_limit

    def is_validation_passed(self):
        memory_limit = self.get_ceph_osd_memory_value()
        if memory_limit:
            if memory_limit < 5:
                self._failed_msg = "Memory limit defined for OSDs is less than 5gb - It leads to performance issues.\n" \
                                   "Fix for CBIS19: available in SP3 PP3"
                return False
            return True
        return False


class VerifyOsdOpNumThreadsPerShardSSD(CephValidation):
    objective_hosts = [Objectives.STORAGE]

    def set_document(self):
        self._unique_operation_name = "validate_osd_op_num_threads_per_shard_ssd_value"
        self._title = "Check if osd_op_num_threads_per_shard_ssd is configured with right value"
        self._failed_msg = "TBD"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.PERFORMANCE]

    def is_validation_passed(self):
        fsid = ''
        if gs.get_version() >= Version.V24_11:
            fsid = '{}/'.format(CephInfo.get_fsid())
        get_conf_cmd = "for i in `sudo ls /var/run/ceph/{fsid}`;do sudo ceph daemon /var/run/ceph/{fsid}$i " \
                       "config show | grep -e osd_op_num_threads_per_shard_ssd| cut -d'\"' -f4; done".format(fsid=fsid)
        out = self.get_output_from_run_cmd(get_conf_cmd, timeout=100)
        out = str(out)
        osd_lines = out.splitlines()
        for i in osd_lines:
            if int(i) != 2:
                self._failed_msg = \
                    "Value of osd_op_num_threads_per_shard_ssd should be set to 2 for ssd/nvme disks.\n" \
                    "If it is set to higher values, it increases the latency causing slow write speed."
                return False
        return True


class CephSlowRequests(CephValidation):
    objective_hosts = [Objectives.CONTROLLERS]

    def set_document(self):
        self._unique_operation_name = "check_if_ceph_had_slow_requests_recently"
        self._title = "Check if ceph has slow requests"
        self._failed_msg = "TBD"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.PERFORMANCE]

    def is_validation_passed(self):
        cmd = "sudo cat /var/log/ceph/ceph_mon.log | grep REQUEST_SLOW"
        exit_code, out, err = self.run_cmd(cmd, timeout=100)
        if exit_code == 0:
            self._failed_msg = \
                "There are slow requests observed recently on this cluster. " \
                "Blocked/Slow requests can have numerous possible root causes from bad media, " \
                "cluster saturation and networking issues."
            return False
        return True


class BaseCephMethodsOnNCS(CephValidation):

    def get_ceph_volume_lvm_dict(self):
        shell_command = "sudo ceph-volume lvm list --format json"
        shell_command_output = self.get_output_from_run_cmd(shell_command)
        ceph_volume_lvm_list_dict = json.loads(shell_command_output)
        return ceph_volume_lvm_list_dict

    def get_running_osd_containers_list(self):
        running_osd_list = []
        if gs.get_version() >= Version.V24_11:
            shell_command = "sudo ceph orch ps --daemon_type osd | grep running | grep {}".format(
                self.get_ceph_host_name())
            field_index = 1
        else:
            docker_or_podman = adapter.docker_or_podman()
            shell_command = "sudo {} ps | grep ceph-osd".format(docker_or_podman)
            field_index = -1

        exit_code, out, err = self.run_cmd(shell_command)
        if not out:
            return running_osd_list

        for line in out.splitlines():
            running_osd_list.append((PythonUtils.get_the_n_th_field(line, field_index)))

        return running_osd_list


class AreAllOSDsRunningOnNCS(BaseCephMethodsOnNCS):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.STORAGE]
    }

    def set_document(self):
        self._unique_operation_name = "are_all_osds_running_on_ncs"
        self._title = "check if all osds are running on NCS"
        self._failed_msg = "TBD"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.SYMPTOM, ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        if gs.get_version() >= Version.V24_11:
            ceph_osd_prefix = 'osd.'
        else:
            ceph_osd_prefix = 'ceph-osd-'
        ceph_volume_lvm_dict = self.get_ceph_volume_lvm_dict()
        running_osd_containers_list = self.get_running_osd_containers_list()
        not_running_osd_containers_list = []
        for key in ceph_volume_lvm_dict:
            if '{}{}'.format(ceph_osd_prefix, key) not in running_osd_containers_list:
                not_running_osd_containers_list.append('ceph-osd-{}'.format(key))
        if len(not_running_osd_containers_list):
            self._failed_msg = "Following OSDs are not running: {}".format(not_running_osd_containers_list)
            return False
        return True


class AreInstalledOSDsMatchCephConfigOnNCS(BaseCephMethodsOnNCS):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.STORAGE]
    }

    def set_document(self):
        self._unique_operation_name = "are_installed_osds_match_ceph_config_on_ncs"
        self._title = "Check if installed OSDs match Ceph config on NCS"
        self._failed_msg = ""
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.SYMPTOM, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        ceph_volume_lvm_dict = self.get_ceph_volume_lvm_dict()
        not_matching_osd_to_config_list = []
        for key in ceph_volume_lvm_dict:
            configured_device = self.get_host_osd_conf_value(key, "OSD_DEVICE")
            if configured_device and gs.get_version() < Version.V23:
                runtime_device = self.get_runtime_device_from_osd_device(ceph_volume_lvm_dict[key])
            else:
                configured_device = self.get_host_osd_conf_value(key, "BLOCK_DEVICE")
                runtime_device = self.get_runtime_device_from_block_device(ceph_volume_lvm_dict[key])
            if runtime_device is None:
                self._failed_msg += "No block device for ceph-osd-{}. ".format(key)
            if configured_device is None:
                configured_device = "this osd has no configuration section in ceph.conf"
            if runtime_device != configured_device:
                not_matching_osd_to_config_list.append('ceph-osd-{}, runtime device: {}, config device: {}'.format(
                    key, runtime_device, configured_device))
        if len(not_matching_osd_to_config_list):
            self._failed_msg += "Following OSDs are having runtime to configuration file ({}) issues:\n{}".format(
                CephPaths.CEPH_CONF, '\n'.join(not_matching_osd_to_config_list))
            return False
        return True

    def get_runtime_device_from_osd_device(self, osd_info):
        runtime_device = None
        for device_section in osd_info:
            if device_section["type"] == "block":
                runtime_device = device_section["devices"][0].split("/")[-1]
                break
        return runtime_device

    def get_runtime_device_from_block_device(self, osd_info):
        runtime_device = None
        for device_section in osd_info:
            if device_section["type"] == "block":
                runtime_device = device_section["devices"][0]
                break
        return runtime_device


class ValidateNcsCephKeyring(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.MASTERS]  # all masters since keyring could be different on any
    }

    @staticmethod
    def _get_keyring_file_path():
        raise NotImplementedError

    def get_keyring(self, keyring_file):
        get_keyring_cmd = 'sudo grep "key" {}'.format(keyring_file)
        keyring = self.get_output_from_run_cmd(get_keyring_cmd)
        return keyring.split(' ')[2]

    def get_secret_decode(self, secret_name, search_value):
        get_secret_cmd = 'sudo kubectl get secret {} -nncms -o json | jq {}'.format(secret_name, search_value)
        secret_value = self.get_output_from_run_cmd(get_secret_cmd).strip('\n')
        decode_secret_cmd = "echo {} | base64 -d".format(secret_value)
        decoded_secret = self.get_output_from_run_cmd(decode_secret_cmd)
        return decoded_secret.strip('\n')

    def get_auth_client(self, client_name):
        auth_client_cmd = 'sudo ceph auth get {} -f json | jq .[0].key'.format(client_name)
        auth_client_value = self.get_output_from_run_cmd(auth_client_cmd).strip('"')
        return auth_client_value.strip('"\n')

    def _keyring_file_exists(self):
        return self.file_utils.is_file_exist(file_path=self._get_keyring_file_path())

    def is_prerequisite_fulfilled(self):
        return self._keyring_file_exists()


class ValidateCephRbdKeyringConfigOnNCS(ValidateNcsCephKeyring):

    def set_document(self):
        self._unique_operation_name = "is_ceph_rbd_keyring_equals_userkey_in_secret"
        self._title = "Validate ceph rbd keyring equals with secret"
        self._failed_msg = "ceph.client.cephrbd.keyring is not matching with csf-charts/csi-cephrbd/all-values.yml"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.SYMPTOM, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    @staticmethod
    def _get_keyring_file_path():
        return '/etc/ceph/ceph.client.cephrbd.keyring'

    def is_validation_passed(self):
        keyring_file = self._get_keyring_file_path()
        secret_name = 'csi-cephrbd'
        search_value = '.data.userKey'
        client_key_name = 'client.cephrbd'
        keyring_value = self.get_keyring(keyring_file)
        decoded_secret = self.get_secret_decode(secret_name, search_value)
        client_key_value = self.get_auth_client(client_key_name)
        if str(keyring_value).strip('\n') == str(decoded_secret) and str(decoded_secret) == str(client_key_value):
            return True
        return False


class ValidateCephFsKeyringConfigOnNCS(ValidateNcsCephKeyring):

    def set_document(self):
        self._unique_operation_name = "is_cephfs_keyring_equals_userkey_in_secret"
        self._title = "Validate ceph fs keyring equals with secret"
        self._failed_msg = "ceph.client.cephfs.keyring is not matching with secret "
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.SYMPTOM, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    @staticmethod
    def _get_keyring_file_path():
        return '/etc/ceph/ceph.client.cephfs.keyring'

    def is_validation_passed(self):
        keyring_file = self._get_keyring_file_path()
        secret_name = 'csi-cephfs'
        search_value = '.data.adminKey'
        client_key_name = 'client.cephfs'
        client_key_value = self.get_auth_client(client_key_name)
        keyring_value = self.get_keyring(keyring_file)
        decoded_secret = self.get_secret_decode(secret_name, search_value)
        if str(keyring_value).strip('\n') == str(decoded_secret) and str(decoded_secret) == str(client_key_value):
            return True
        return False


class CheckOsdPGLogTuning(CephValidation):
    objective_hosts = [Objectives.STORAGE]

    def set_document(self):
        self._unique_operation_name = "check_osd_pg_log_tuning"
        self._title = "is osd_max_pg_log_entries and osd_min_pg_log_entries set to 500 and 250 respectively"
        self._severity = Severity.WARNING
        self._failed_msg = ""
        self._implication_tags = [ImplicationTag.PERFORMANCE]

    def is_validation_passed(self):
        if ImplicationTag.APPLICATION_DOMAIN in self.get_implication_tags():
            self._implication_tags.remove(ImplicationTag.APPLICATION_DOMAIN)
        OSD_MAX_PG_LOG_ENTRIES = 500
        OSD_MIN_PG_LOG_ENTRIES = 250
        host_osds = self.get_host_osds()
        if host_osds and not host_osds.get('is_passed', True):
            self._failed_msg = host_osds.get('failed_msg', '')
            return False
        host_osd_ids = list(host_osds.keys())
        if not host_osd_ids:
            self._failed_msg = "No OSDs were found on {}".format(self.get_ceph_host_name())
            return False
        # 0 index below is to pick any osd from the host_osd_ids list, ceph.conf exist per host
        # so any osd from the host works for ceph daemon command
        if gs.get_version() >= Version.V24_11:
            osd = '/var/run/ceph/{}/ceph-osd.{}.asok'.format(CephInfo.get_fsid(), host_osd_ids[0])
        else:
            osd = 'osd.{}'.format(host_osd_ids[0])
        cmd_max = "sudo ceph daemon {} config get osd_max_pg_log_entries".format(osd)
        cmd_min = "sudo ceph daemon {} config get osd_min_pg_log_entries".format(osd)
        out_max = self.get_output_from_run_cmd(cmd_max)
        out_min = self.get_output_from_run_cmd(cmd_min)
        out_max = json.loads(out_max)
        out_min = json.loads(out_min)
        if int(out_max["osd_max_pg_log_entries"]) < 10 and int(out_min["osd_min_pg_log_entries"]) < 10:
            return True
        if int(out_max["osd_max_pg_log_entries"]) != OSD_MAX_PG_LOG_ENTRIES:
            self._failed_msg = "Max pg log entries is set with {}, while it should be set with {} - Tune the values in ceph.conf in all the storage nodes". \
                format(out_max["osd_max_pg_log_entries"], str(OSD_MAX_PG_LOG_ENTRIES))
            return False
        if int(out_min["osd_min_pg_log_entries"]) != OSD_MIN_PG_LOG_ENTRIES:
            self._failed_msg = "Min pg log entries is set with {}, while it should be set with {} - Tune the values in ceph.conf in all the storage nodes". \
                format(out_min["osd_min_pg_log_entries"], str(OSD_MIN_PG_LOG_ENTRIES))
            return False
        return True


class IsCephEncryption(InformatorValidator, CephValidation):
    objective_hosts = [Objectives.UC, Objectives.ONE_MANAGER]

    def set_document(self):
        self._is_pure_info = True
        self._unique_operation_name = "is_ceph_encryption"
        self._title_of_info = "is ceph encryption enabled"
        self._system_info = ""

    def get_system_info(self):
        is_encryption = False
        if gs.get_deployment_type() == Deployment_type.NCS_OVER_BM:
            is_encryption = gs.get_base_conf()['storage'].get('ceph_encryption', False)
        if gs.get_deployment_type() == Deployment_type.CBIS:
            is_encryption = gs.get_base_conf()['CBIS']['storage'].get('ceph_encryption', False)
        return str(is_encryption)


class IOErrorCephFSMount(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.MASTERS]
    }

    def set_document(self):
        self._unique_operation_name = "verify_cephfsmount_accesible"
        self._title = "Verify no input/output errors are occurring on CephFS mount /opt/bcmt/storage"
        self._failed_msg = "CephFS /opt/bcmt/storage is not accessible. The following files were found but are not readable:"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        # The next command aims to randomly read some files in a specific folder.
        # The shuf command writes a random permutation of the input lines to standard output.
        find_cmd = "sudo find /opt/bcmt/storage/docker-registry/ -type f -name link | shuf -n 10"
        find_cmd_out = self.get_output_from_run_cmd(find_cmd)
        files_to_check = find_cmd_out.splitlines()
        if not files_to_check:
            self._failed_msg = "CephFS /opt/bcmt/storage is not accessible."
            return False
        for link in files_to_check:
            if not self.file_utils.is_file_readable(link):
                self._failed_msg += '\n {}'.format(link)
                return False
        return True


class CheckCephServiceStatus(Validator):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.ONE_CONTROLLER],
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER, Objectives.ONE_MANAGER]
    }

    def set_document(self):
        self._unique_operation_name = "check_ceph_orch_status"
        self._title = "Check services status using ceph orch"
        self._failed_msg = "The current number of running instances does not align with the expected count for the following Ceph services:\n"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        get_ceph_service_orch_status = "sudo ceph orch ls -f json-pretty"
        ceph_service_status = self.get_output_from_run_cmd(get_ceph_service_orch_status,
                                                           message="Failed to get the service status of ceph using 'ceph orch' commands")
        ceph_service_status = json.loads(ceph_service_status)
        if ceph_service_status is None:
            raise UnExpectedSystemOutput(self.get_host_ip(), get_ceph_service_orch_status,
                                         output=ceph_service_status,
                                         message="Unable to parse the JSON data")
        flag = 0
        for service in ceph_service_status:
            running = service['status']['running']
            size = service['status']['size']
            if running != size:
                flag = 1
                self._failed_msg += (
                    "{} - actual running {}, while expected {}\n".format(service['service_name'], running, size))
        if flag == 1:
            return False
        else:
            return True


class CheckCephfsShareExist(CephValidation):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.CONTROLLERS, Objectives.COMPUTES, Objectives.STORAGE]
    }

    def set_document(self):
        self._unique_operation_name = "verify_common_nodes_cehpfs_share"
        self._title = "Verify '/mnt/common_nodes_cehpfs_share' is accessible"
        self._failed_msg = ""
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.ACTIVE_PROBLEM]
        self._blocking_tags = [BlockingTag.SCALE]
        self._is_clean_cmd_info = True

    def is_validation_passed(self):
        common_nodes_cehpfs_share_options = ['/mnt/common_nodes_cehpfs_share', '/mnt/common_nodes_cephfs_share']
        for common_nodes_cehpfs_share in common_nodes_cehpfs_share_options:
            if self.file_utils.is_dir_exist(common_nodes_cehpfs_share):
                self._title = "Verify '{}' is accessible".format(common_nodes_cehpfs_share)
                return True
        self._failed_msg = ("The mount path '/mnt/common_nodes_cehpfs_share' or '/mnt/common_nodes_cephfs_share' "
                            "either does not exist or is inaccessible.")
        return False


class CephMultipoolSameNodeMemberCheck(Validator):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.ONE_CONTROLLER]
        #Deployment_type.CBIS: [Objectives.HYP]
    }

    def set_document(self):
        self._unique_operation_name = "verify_cephmultipool_member_check"
        self._title = "Verify if same node is configured for multiple pool"
        self._failed_msg = "Same node configured for multiple pools, please perform the WA"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):

        pool_check_command = "sudo ceph osd tree -f json |  jq -r '.nodes[]|select(.type == \"root\").name'"

        pool_check_cmd_out = self.get_output_from_run_cmd(pool_check_command)

        nodes_list_command = "sudo ceph osd tree -f json | jq -r '.nodes[]|select(.type == \"host\").name'"

        nodes_check_cmd_out = self.get_output_from_run_cmd(nodes_list_command)
        nodes_to_be_checked = nodes_check_cmd_out.splitlines()

        if 'common' in pool_check_cmd_out.splitlines() or 'fast' in pool_check_cmd_out.splitlines():
            return True
        pools_to_be_checked = pool_check_cmd_out.splitlines()
        filtered_list = [item for item in pools_to_be_checked if item]
        if 'default' in filtered_list:
            filtered_list.remove(u'default')

        sorted_pools = {pool: [] for pool in filtered_list}
        for string in nodes_to_be_checked:
            for pool in filtered_list:
                if string.startswith(pool):
                    sorted_pools[pool].append(string)
        for pool, sorted_list in sorted_pools.items():
            sorted_pools[pool] = [string.replace(pool + '-', '') for string in sorted_list]

        common_elements = None
        for pool1, list1 in sorted_pools.items():
            for pool2, list2 in sorted_pools.items():
                if pool1 != pool2:
                    common = set(list1).intersection(set(list2))
                    if common:
                        if common_elements is None:
                            common_elements = common
                        else:
                            common_elements.update(common)

        if common_elements:
            return False
        return True




class VerifyLostVolumesCephK8sPV(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "verify_lost_volumes_ceph_k8s_pv"
        self._title = "Verify Lost Volumes in Ceph and K8s PV"
        self._failed_msg = "ERROR!!!\n"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def all_k8s_pvs_dict_list (self):
        cmd = "sudo kubectl get pv -o json"
        return_code, out, err = self.run_cmd(cmd)
        if return_code != 0:
            raise UnExpectedSystemOutput(self.get_host_name(), cmd, out,'Failed to Retrieve The PVs from K8s | {} | {}'.format(err, out))
        if out:
            all_k8s_pvs_dict = json.loads(out)
        return all_k8s_pvs_dict["items"]

    def get_k8s_PV_ceph_volumes(self, all_k8s_pvs_dict_list):
        ceph_rbd_volumes_k8s_PV = []
        ceph_fs_volumes_k8s_PV = []

        for pv_dict in all_k8s_pvs_dict_list:
            spec = pv_dict.get("spec")
            if not spec or not spec.get("storageClassName"):
                continue
            volume_attr = spec.get("csi", {}).get("volumeAttributes", {})
            if not volume_attr:
                continue

            storage_class = spec["storageClassName"]
            if storage_class == "csi-cephrbd":
                vol = volume_attr.get("imageName")
                if vol:
                    ceph_rbd_volumes_k8s_PV.append(vol)

            elif storage_class == "csi-cephfs":
                vol = volume_attr.get("subvolumeName")
                if vol:
                    ceph_fs_volumes_k8s_PV.append(vol)

        return ceph_rbd_volumes_k8s_PV, ceph_fs_volumes_k8s_PV

    def get_ceph_rbd_pool_volumes(self):
        volumes = []
        cmd = "sudo rbd ls volumes"
        return_code, out, err = self.run_cmd(cmd)
        if return_code != 0:
            raise UnExpectedSystemOutput(self.get_host_name(), cmd, out,'Failed to Retrieve Ceph RBD Pool volumes | {} | {}'.format(err, out))
        if out:
            volumes.extend(out.splitlines())
        return volumes

    def get_ceph_fs_subvolume_csi_volumes(self):
        cmd = "sudo ceph fs subvolume ls cephfs csi -f json"
        return_code, out, err = self.run_cmd(cmd)
        if return_code != 0:
            raise UnExpectedSystemOutput(self.get_host_name(), cmd, out,'Failed to Retrieve Ceph-FS subvolume csi volumes {}'.format(err, out))

        if out:
            array_of_volumes_keypair = json.loads(out)
        volumes = []
        for cephfs_volume_dict in array_of_volumes_keypair:
            if not cephfs_volume_dict or not cephfs_volume_dict.get("name"):
                continue
            volumes.append(cephfs_volume_dict["name"])
        return volumes

    def ceph_volume_compare (self, ceph_k8s_PV, ceph_volumes, category_flag):
        vol_not_found_flag = 0
        for vol in ceph_volumes:
            if vol not in ceph_k8s_PV:
                vol_not_found_flag = 1
                self._failed_msg += "{} Volume Lost | Volume : {} does ont Exist in K8s PV\n".format(category_flag, vol)
        if vol_not_found_flag:
            return False
        else:
            return True

    def is_validation_passed(self):

        ##### First Get ALL The PVs from K8s cluster
        all_k8s_pvs_dict_list = self.all_k8s_pvs_dict_list()

        ##### Get The PVs from K8s with csi-cephrbd Storage Class and see the CEPH RBD Volume images and store it in "ceph_rbd_volumes_k8s_PV" List

        ##### Get The PVs from K8s with csi-cephfs Storage Class and see the CEPH FS Sub volumes and store it in "ceph_fs_volumes_k8s_PV" List

        ceph_rbd_volumes_k8s_PV, ceph_fs_volumes_k8s_PV = self.get_k8s_PV_ceph_volumes(all_k8s_pvs_dict_list)

        ##### storage class csi-cephrbd - backend volumes are stored in the pool volumes so Retrieve CEPH RBD volumes from ceph
        ceph_rbd_pool_volumes = self.get_ceph_rbd_pool_volumes()

        ##### storage class csi-cephfs - backend volumes are ceph fs subvolumes in the subvolumegroup csi
        ceph_fs_subvolume_csi_volumes = self.get_ceph_fs_subvolume_csi_volumes()

        ##  Compare Ceph RBD Pool volumes and CEPF_FS Subvolumes with K8s CEPH PVs
        #   Category FLAG = RBD For CEPH-RBD Checking
        #   Category FLAG = FS for CEPH-FS Checking

        #   "ceph_rbd_volume_match" = True and "ceph_fs_volume_match" = True Boolean variables used to verify Volume mismatch is there or not.

        ceph_rbd_volume_match = True
        ceph_fs_volume_match = True

        category_flag = "CEPH-RBD"
        if ceph_rbd_volumes_k8s_PV and ceph_rbd_pool_volumes:
            ceph_rbd_volume_match = self.ceph_volume_compare(ceph_rbd_volumes_k8s_PV, ceph_rbd_pool_volumes, category_flag)

        category_flag = "CEPH-FS"
        if ceph_fs_volumes_k8s_PV and ceph_fs_subvolume_csi_volumes:
            ceph_fs_volume_match = self.ceph_volume_compare(ceph_fs_volumes_k8s_PV, ceph_fs_subvolume_csi_volumes, category_flag)

        ## IF "ceph_rbd_volume_match" and "ceph_fs_volume_match" both Boolean variables return TRUE then VALIDATION PAssed Else FAILS
        if ceph_rbd_volume_match and ceph_fs_volume_match:
            return True
        else:
            return False


class CephCheckPGsPerOSD(Validator):
    objective_hosts = [
        Objectives.ONE_CONTROLLER,
        Objectives.ONE_MASTER
    ]

    MIN_PGS_PER_OSD = 50
    MAX_PGS_PER_OSD = 320

    def set_document(self):
        self._unique_operation_name = "ceph_check_pgs_per_osd"
        self._title = "Ceph check PGS per OSD is between {} and {}".format(self.MIN_PGS_PER_OSD, self.MAX_PGS_PER_OSD)
        self._failed_msg = "Warning: the following osd have pgs count outside the {}-{} recommended range, this could affect performance:\n".format(self.MIN_PGS_PER_OSD, self.MAX_PGS_PER_OSD)
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.NOTE, ImplicationTag.PERFORMANCE]

    def is_validation_passed(self):
        cmd = "sudo ceph osd df"
        out = self.get_output_from_run_cmd(cmd)
        lines = out.split('\n')
        try:
            header = lines[0]
            pgs_index = header.index("PGS")
            id_index = header.index("ID")
            class_index = header.index("CLASS")
        except (ValueError, IndexError):
            raise UnExpectedSystemOutput(self.get_host_name(), cmd, out,"failed to parse the output")
        is_passed = True
        for line in lines[1:]:
            if not line:
                continue
            if "TOTAL" in line:
                break
            try:
                pgs = int(line[pgs_index:].strip().split()[0])
                id_ = line[id_index:].strip().split()[0]
                class_ = line[class_index:].strip().split()[0]
            except (ValueError, IndexError):
                raise UnExpectedSystemOutput(self.get_host_name(), cmd, out, "failed to extract id, class, or pgs from line {}".format(line))
            if pgs < self.MIN_PGS_PER_OSD or pgs > self.MAX_PGS_PER_OSD:
                is_passed = False
                self._failed_msg+= "id: {} , class: {} , pgs: {} \n".format(id_, class_, pgs)
        return is_passed

class GetBlockDBSize(DataCollector):
    objective_hosts = [Objectives.UC]

    def collect_data(self):
        self._is_clean_cmd_info = True
        out = self.get_output_from_run_cmd('sudo cat /home/stack/user_config.yaml |grep -i ceph_block_db_size')
        return out

class ValidateCephBlockDBSize(Validator):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.ONE_CONTROLLER]
    }

    HDD_BLOCK_DB_RATIO = 0.04
    SSD_BLOCK_DB_RATIO = 0.01

    def set_document(self):
        self._unique_operation_name = "validate_ceph_block_db_size"
        self._title = "Validate Ceph Block DB size"
        self._failed_msg = ""
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        ceph_block_db_size = self.get_first_value_from_data_collector(GetBlockDBSize)
        ceph_block_db_size_value = ceph_block_db_size.split(":")[-1].strip()
        ceph_block_db_size_value_in_gb = int(ceph_block_db_size_value)/1024.0

        ceph_osd_cmd = "sudo ceph osd df -f json"
        jq_filter = '.nodes[] | (.id|tostring) + " " + ((.kb/1024/1024)|tostring) + " " + (.device_class // "unknown")'
        full_ceph_osd_cmd = "{} | jq -r '{}'".format(ceph_osd_cmd, jq_filter)

        ceph_osd_df_cmd_out = self.get_output_from_run_cmd(full_ceph_osd_cmd).splitlines()
        osd_info = []
        for each_osd in ceph_osd_df_cmd_out:
            osd_id, size, device = each_osd.split(" ")
            size = float(size)

            if device.upper() == 'HDD':
                ratio = ValidateCephBlockDBSize.HDD_BLOCK_DB_RATIO
            elif device.upper() in ('SSD', 'NVME'):
                ratio = ValidateCephBlockDBSize.SSD_BLOCK_DB_RATIO
            else:
                continue

            if size * ratio >= int(ceph_block_db_size_value_in_gb):
                osd_info.append('OSD-{}->of size {} GB'.format(osd_id, round(size, 3)))

        if len(osd_info) > 0:
            self._failed_msg += "Ceph Block DB size {} GB is not in recommended range of 1% (SSD,NVME), 4%(HDD) for below OSD's".format(ceph_block_db_size_value_in_gb)
            self._failed_msg += "\n" + "\n".join(osd_info)
            return False
        return True
