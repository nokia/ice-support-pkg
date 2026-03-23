from __future__ import absolute_import
from HealthCheckCommon.validator import Validator
from tools.global_enums import *
import tools.paths as paths
from tools.lazy_global_data_loader import *
import json, os
##
# Check if the pre-requisite helm applications are installed
##
class pre_installed_applications_check(Validator):
    objective_hosts = [Objectives.ONE_MASTER]
    @staticmethod
    @lazy_global_data_loader
    def get_ncd_conf_dict():
        assert os.path.isfile(paths.NCD_CONFIG_FILE)
        with open(paths.NCD_CONFIG_FILE) as f:
            return json.load(f)

    def set_document(self):
        self._unique_operation_name = "pre-requisite_applications_validator"
        self._title = "Check if pre-requisite applications are installed"
        self._failed_msg = "pre-requisite applications are not installed"
        self._severity = Severity.WARNING


    def is_validation_passed(self):
        ncd_dict = pre_installed_applications_check.get_ncd_conf_dict()
        applications_needed = ncd_dict.get('pre_installed_applications')
        if applications_needed is None:
            msg = "file: {} is expected to be set by pre-code".format(paths.NCD_CONFIG_FILE)
            raise UnExpectedSystemOutput(self.get_host_name(), "", "", message=msg)
        charts_installed = []
        charts = self.get_dict_from_command_output(
            "sudo helm list --output json --deployed", 'json', timeout=10)
        for chart in charts["Releases"]:
            chart = chart["Chart"]
            charts_installed.append(chart)
        not_installed_charts = []
        for chart in applications_needed:
            if chart not in charts_installed:
                not_installed_charts.append(chart)
        if len(not_installed_charts):
            self._failed_msg = "pre-requisite applications {} are not installed".format(",".join(not_installed_charts))
            return False
        return True

##
# Check if NCOM is accessible from the cluster
##
class ncom_access(Validator):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._unique_operation_name = "ncom_access_validator"
        self._title = "Check if NCOM is accessible from the cluster"
        self._failed_msg = "NCOM is inaccessible from the cluster"
        self._severity = Severity.WARNING


    def is_validation_passed(self):
        ncd_dict = pre_installed_applications_check.get_ncd_conf_dict()
        ncom_url = ncd_dict['ncom_url']
        return_code, curl_exit_code, err = self.run_cmd(
            'curl -k -s --max-time 5 -o /dev/null -w "%{}" {}'.format("{http_code}", ncom_url), timeout=10)

        if curl_exit_code != '200':
            self._failed_msg += '\nNCOM address {} is not reachable from the control nodes.\n'.format(ncom_url)
            return False
        return True


##
# Check if the components' fqdns (full qualified domain names) can be resolved
##
class fqdn_resolve(Validator):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._unique_operation_name = "fqdns_resolve_validator"
        self._title = "Check if the NCD components' hostnames are being resolved by a DNS server"
        self._failed_msg = "FQDNs can not be resolved"
        self._severity = Severity.WARNING


    def is_validation_passed(self):
        ncd_dict = ncd_dict = pre_installed_applications_check.get_ncd_conf_dict()
        fqdn_list = ncd_dict['fqdn_list']
        failed_fqdns = []
        for fqdn in fqdn_list:
            dns_server = self.get_output_from_run_cmd('dig {} +short'.format(fqdn), timeout=10)
            if not dns_server:
                failed_fqdns.append(fqdn)
        if failed_fqdns:
            self._failed_msg += '\nThese FQDNs cannot be resolved by any DNS server: {}.\n'.format(failed_fqdns)
            return False
        return True


##
# Check if the storageClasses in the cluster supports RWX
##
class is_sc_rwx(Validator):
    #depriceted
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._unique_operation_name = "check_if_sc_supports_rwx"
        self._title = "Check if there is a storageClass that supports RWX in the cluster"
        self._failed_msg = "There is no storageClass that supports rwx in the cluster. " \
                           "The RWX (Read Write Many) supported SCs are listed here:" \
                           "https://kubernetes.io/docs/concepts/storage/persistent-volumes/#access-modes"
        self._severity = Severity.ERROR


    def is_validation_passed(self):
        ncd_dict = pre_installed_applications_check.get_ncd_conf_dict()
        rwx_sc_list = ncd_dict['rwx_sc']  # explain!
        configured_sc = []
        is_pass = False

        sc_full_name = self.get_output_from_run_cmd("sudo kubectl get sc -o=jsonpath=\"{.items[*]['provisioner']}\"",
                                                    timeout=10)
        configured_sc_full_name = sc_full_name.split()
        for sc in configured_sc_full_name:
            configured_sc.append(sc.split(".")[0])

        for sc in configured_sc:
            if sc in rwx_sc_list:
                is_pass = True

        if not is_pass:
            return False
        return True
