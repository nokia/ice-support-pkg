from __future__ import absolute_import
from collections import OrderedDict
from HealthCheckCommon.operations import DataCollector
from HealthCheckCommon.validator import InformatorValidator
from tools.global_enums import Objectives, Deployment_type, Severity
import tools.sys_parameters as gs
import json
from HealthCheckCommon.base_validation_flow import BaseValidationFlow


class FindCertificatesDataCollector(DataCollector):
    objective_hosts = [Objectives.MANAGERS, Objectives.HYP, Objectives.DEPLOYER, Objectives.ALL_HOSTS,
                       Objectives.ALL_NODES, Objectives.MONITOR]

    def collect_data(self):
        res_list = []
        all_paths = FindCertificates.get_all_paths()
        for path in all_paths:
            if self.file_utils.is_file_exist(path):
                path = self.remove_cluster_name_from_path(path)
                res_list.append(path)
        return sorted(list(set(res_list)))

    def remove_cluster_name_from_path(self, path):
        if gs.is_ncs_central() and "/{}/".format(gs.get_cluster_name()) in path:
            path = path.replace("/{}/".format(gs.get_cluster_name()), "/{cluster_name}/")
        return path


class FindCertificates(InformatorValidator):
    objective_hosts = [Objectives.ONE_MANAGER, Objectives.UC, Objectives.DEPLOYER]

    def set_document(self):
        self._unique_operation_name = "find_certificates"
        self._title = "find_certificates"
        self._failed_msg = "TBD"
        self._severity = Severity.CRITICAL
        self._info = ""
        self._is_highlighted_info = True
        self._title_of_info = "certificates found:"
        self._is_pure_info = True

    def is_validation_passed(self):
        res = self.run_data_collector(FindCertificatesDataCollector)
        path_hosts_dict = {}
        version = str(gs.get_version()) + str(gs.get_sub_version()) if gs.get_sub_version() else str(
            gs.get_version())
        system_info_dict = OrderedDict([("deployment_type", gs.get_deployment_type()), ("version", version)])
        if gs.is_ncs_central():
            system_info_dict["version"] += "Central"
        system_info_dict["cluster_name"] = gs.get_cluster_name() if gs.get_cluster_name() else ""
        missing_paths = []
        all_paths = FindCertificates.get_all_paths(ignore_cluster_name=True)
        for key, lst_value in list(res.items()):
            for item in lst_value:
                path_hosts_dict.setdefault(item, []).append(key)
        for path in all_paths:
            if not path_hosts_dict.get(path):
                missing_paths.append(path)
        paths_by_hosts_dict = FindCertificates.generate_paths_by_hosts_dict(path_hosts_dict)
        system_info_dict.update(paths_by_hosts_dict)
        system_info_dict["missing_paths"] = missing_paths
        self._system_info = system_info_dict
        return True

    @staticmethod
    def generate_paths_by_hosts_dict(path_hosts_dict):
        paths_by_hosts_dict = dict()
        available_roles = gs.get_host_executor_factory().get_roles_map_dict()
        for path, lst_hosts in list(path_hosts_dict.items()):
            roles_list = []
            hosts_roles = []
            for role, hosts in list(available_roles.items()):
                if role in [Objectives.ONE_CONTROLLER, Objectives.ONE_MASTER, Objectives.ONE_MANAGER,
                            Objectives.ONE_STORAGE, Objectives.ICE_CONTAINER]:
                    continue
                hosts_list = [x.split(' at ')[0] for x in hosts]
                if set(hosts_list).issubset(set(lst_hosts)):
                    hosts_roles.extend(hosts_list)
                    roles_list.append(role)
            res_hosts_list = list(set(lst_hosts).difference(list(set(hosts_roles)))) + roles_list
            paths_by_hosts_dict.setdefault(', '.join(sorted(res_hosts_list)), []).append(path)
        return paths_by_hosts_dict

    @staticmethod
    def get_all_paths(ignore_cluster_name=False):
        paths_list = FindCertificates.get_certificates_paths_list(ignore_cluster_name) + \
                     FindCertificates.get_public_private_keys_paths_list(ignore_cluster_name)
        return sorted(list(set(paths_list)))

    @staticmethod
    def get_public_private_keys_paths_list(ignore_cluster_name):
        public_private_keys_dict = FindCertificates.get_public_private_keys_dict()
        paths_list = []
        deployment_type_key = Deployment_type.get_deployment_type_key_from_value(gs.get_deployment_type())
        for key, value_dict in list(public_private_keys_dict.get(deployment_type_key, {}).items()):
            for version, value in list(value_dict.items()):
                if not ignore_cluster_name and ("{cluster_name}" in value['cert'] or "{cluster_name}" in value['key']):
                    if gs.is_ncs_central():
                        value['cert'] = value['cert'].format(
                            cluster_name=gs.get_cluster_name())
                        value['key'] = value['key'].format(
                            cluster_name=gs.get_cluster_name())
                    else:
                        continue
                paths_list.append(value["cert"])
                paths_list.append(value["key"])
        return paths_list

    @staticmethod
    def get_certificates_paths_list(ignore_cluster_name):
        paths_list = []
        certificate_dict = FindCertificates.get_certificate_dict()
        for cert_name, cert_dict in list(certificate_dict.items()):
            for version, cert_path_dict in list(cert_dict.items()):
                for cert_path, cert_objectives in list(cert_path_dict.items()):
                    if not ignore_cluster_name and "{cluster_name}" in list(cert_path_dict.keys())[0]:
                        if gs.is_ncs_central():
                            cert_path = cert_path.format(cluster_name=gs.get_cluster_name())
                        else:
                            continue
                    paths_list.append(cert_path)
        return paths_list

    @staticmethod
    def get_certificate_dict():
        CERTIFICATE_CONFIGURATIONS = "flows/Security/Certificate/certificate.json"
        status_dict = {}
        with open(CERTIFICATE_CONFIGURATIONS) as json_file:
            config_dict = json.load(json_file)
            if gs.get_deployment_type() == Deployment_type.NCS_OVER_BM:
                status_dict = config_dict["NCS_OVER_BM"]
            elif gs.get_deployment_type() == Deployment_type.NCS_OVER_OPENSTACK:
                status_dict = config_dict["NCS_OVER_OS"]
            elif gs.get_deployment_type() == Deployment_type.NCS_OVER_VSPHERE:
                status_dict = config_dict["NCS_OVER_VMWARE"]
            elif gs.get_deployment_type() == Deployment_type.CBIS:
                status_dict = config_dict["CBIS"]
        return status_dict

    @staticmethod
    def get_public_private_keys_dict():
        public_private_keys = "flows/Security/Certificate/public_private_keys.json"
        with open(public_private_keys) as json_file:
            certification_and_key_pairs = json.load(json_file)
        return certification_and_key_pairs


class CertificatesByRolesFlow(BaseValidationFlow):

    def _get_list_of_validator_class(self, version, deployment_type):
        check_list_class = [
            FindCertificates
        ]

        return check_list_class

    def command_name(self):
        return "certificates_by_roles"

    def deployment_type_list(self):
        return [Deployment_type.CBIS, Deployment_type.NCS_OVER_BM, Deployment_type.NCS_OVER_OPENSTACK,
                Deployment_type.NCS_OVER_VSPHERE]
