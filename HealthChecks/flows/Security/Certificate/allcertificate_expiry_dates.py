from __future__ import absolute_import
from HealthCheckCommon.operations import *
from tools.date_and_time_utils import parse
import datetime
import tools.sys_parameters as gs
from HealthCheckCommon.table_system_info import TableSystemInfo
from HealthCheckCommon.validator import Validator
from tools.ConfigStore import ConfigStore
from tools.python_versioning_alignment import get_unicode_type


class ProvisioningVipDataCollector(DataCollector):
    objective_hosts = [Objectives.ONE_MANAGER]

    def collect_data(self):
        conf_info = gs.get_base_conf()
        return PythonUtils.get_value_from_nested_dict(conf_info, 'internal_management_vip')[0]

class IsClcmEmbededDataCollector(DataCollector):
    objective_hosts = [Objectives.ONE_MASTER]

    def collect_data(self):
        return self.run_cmd_return_is_successful("sudo kubectl get pods -A | grep clcm")


class CertificateExpiryDates(Validator):
    # List of non NCS certificates to be excluded from validity checks
    NON_NCS_MANAGED_CERTS = ['cnpg-webhook-cert']

    def validate_end_date(self, cert):
        cmd = "sudo openssl x509 -enddate -noout -in " + cert
        ret, out, err = self.run_cmd(cmd)
        if ret == 0:
            return ret, out.split("=")[1],err
        else:
            return ret, out, err

    def get_ncs_tls_cert(self):
        base_cmd = r"sudo kubectl get secret  --field-selector type=kubernetes.io/tls -A  --no-headers -o=custom-columns='NAME:.metadata.name,NAMESPACE:.metadata.namespace,CERT:.data.tls\.crt'"
        if gs.get_version() >= Version.V25_11:
            grep_exclusion_string = "|".join(self.NON_NCS_MANAGED_CERTS)
            final_cmd = "{} | grep -E -v '{}'".format(base_cmd, grep_exclusion_string)
        else:
            final_cmd = base_cmd
        out = self.get_output_from_run_cmd(final_cmd)
        return out

    def get_cert_manager_cert(self):
        cmd = r"sudo kubectl get secrets -A -o=custom-columns='NAME:.metadata.name,CERTNAME:.metadata.annotations.cert-manager\.io/certificate-name' --no-headers | grep -v '<none>' | awk '{print $1}'"
        out = self.get_output_from_run_cmd(cmd)
        return out

    def get_ncs_opaque_cert(self):
        cmd = r"sudo kubectl get secret --field-selector type=Opaque  -A  --no-headers -o=custom-columns='NAME:.metadata.name,NAMESPACE:.metadata.namespace,CERT:.data.tls\.crt' | grep -v none"
        ok = self.get_output_from_run_cmd(cmd)
        return ok

    def get_ncs_opaque_cert_pem(self):
        cmd = r"sudo kubectl get secret --field-selector type=Opaque  -A  --no-headers -o=custom-columns='NAME:.metadata.name,NAMESPACE:.metadata.namespace,CERT:.data.cert\.pem' | grep -v none"
        out = self.get_output_from_run_cmd(cmd)
        return out

    def decode_openssl(self, cert):
        cmd = " echo " + cert + " | base64 -d | openssl x509 -enddate -noout "
        ret, out, err = self.run_cmd(cmd)
        return ret, out, err

    def calculate_dates(self, end_date):
        formatted_end_date = parse(end_date)
        t1 = str(formatted_end_date).split(' ')[0]
        t2 = str(datetime.datetime.now().date())
        delta = parse(t1) - parse(t2)
        rem_days = delta.days

        return rem_days

    def is_expiring(self, end_date, rem_days, expiration_days):
        td = datetime.timedelta(days=expiration_days)
        check_date = datetime.datetime.now() + td
        formatted_end_date = parse(end_date)
        ret = True
        if formatted_end_date.replace(tzinfo=None) < check_date and int(rem_days) > 0:
            status = "Yes, will expire in {} days".format(rem_days)
            self._severity = Severity.ERROR
        elif formatted_end_date.replace(tzinfo=None) < check_date and int(rem_days) <= 0:
            status = "Expiry date over"
            self._severity = Severity.CRITICAL
        else:
            status = "No"
            ret = False
        return status, ret

    def calculate_for_tls_opaque_secret_certificates(self):
        expiration_days = 90
        not_ready_list = []
        error_list = []
        test1 = self.get_ncs_tls_cert()

        test2 = self.get_ncs_opaque_cert()
        test3 = self.get_ncs_opaque_cert_pem()
        test = test1 + test2 + test3
        cert_value = []
        for line in test.splitlines():
            words = line.split()
            if len(words) < 3:
                error_list.append(words[0])
            else:
                secret_name = words[0]
                namespace = words[1]
                encoded_openssl = words[2]
                return_code, out, err = self.decode_openssl(encoded_openssl)
                infra_namespace_list = ['kube-system', 'node-feature-discovery', 'ncms', 'citm', 'istio-system',
                                        'rook-ceph', 'gatekeeper-system', 'cosign-system', 'kube-node-lease', 'kube-public']
                renewed_automatically = "No"
                cbis_ncs_certificate = "Yes"
                cert_manager_certs_list = self.get_cert_manager_cert()
                cert_manager_certs_list = cert_manager_certs_list.split("\n")
                if secret_name in cert_manager_certs_list and namespace in infra_namespace_list:
                    renewed_automatically = "Yes"
                if namespace not in infra_namespace_list:
                    cbis_ncs_certificate = "No"
                if return_code == 0:
                    end_date = out.split("=")[1]
                    days_to_end = self.calculate_dates(end_date)
                    if secret_name == 'kubesetting-webhook-server-cert':
                        expiration_days = 28
                    status_str, ret = self.is_expiring(end_date, days_to_end, expiration_days=expiration_days)
                    cert_value.append([secret_name, namespace, end_date, days_to_end, status_str, renewed_automatically,cbis_ncs_certificate])
                    if ret:
                        not_ready_list.append(secret_name)
                else:
                    cert_value.append([secret_name, namespace, "could not fetch end date", "--", "sys_problem",renewed_automatically,cbis_ncs_certificate])
                    not_ready_list.append(secret_name)

        return cert_value, not_ready_list, error_list

    def calculate_for_infra_certificates(self, cert_testing_dict):
        not_ready_list = []
        not_found_list = []
        cert_matrix = []
        renewed_automatically = "No"
        cbis_ncs_certificate = "Yes"
        for cert_name, cert_path_list in list(cert_testing_dict.items()):
            for cert_path in cert_path_list:
                if self.file_utils.is_file_exist(cert_path):
                    ret, out, err = self.validate_end_date(cert_path)
                    if ret == 0:
                        days_to_end = self.calculate_dates(out)
                        status_str, is_expiring = self.is_expiring(out, days_to_end, 90)
                        cert_matrix.append([cert_name, cert_path, out, days_to_end, status_str, renewed_automatically,cbis_ncs_certificate])
                        if is_expiring:
                            not_ready_list.append(cert_name)
                    else:
                        cert_matrix.append([cert_name, cert_path, "Unknown", "Unknown",
                                           "Certificate was found, but dates could not be calculate "
                                           "Please find the certificate location and test it manually.","Unknown","Unknown"])
                        not_ready_list.append(cert_name)
                else:
                    cert_matrix.append([cert_name, cert_path, "Unknown", "Unknown",
                                        "Certificate wasn't found, "
                                        "Please find the certificate location and test it manually.","Unknown","Unknown"])
                    not_found_list.append(cert_name)
        return cert_matrix, not_ready_list, not_found_list

    def _remove_keys(self, status_dict, keys_to_remove):
        for key in keys_to_remove:
            if key in status_dict:
                del status_dict[key]
        return status_dict

    def _enrichment_certificate_dictionary_using_barbican(self, status_dict):
        status_dict["ca_internal"] = {
            "[Version.V24-unlimited]": {
                "/etc/pki/ca-trust/source/anchors/ca-internal.crt.pem": "[Objectives.UC, Objectives.CONTROLLERS, Objectives.COMPUTES]"
            }
        }
        status_dict["babican"] = {
            "[Version.V24-unlimited]": {
                "/var/lib/config-data/puppet-generated/barbican/etc/barbican/barbican-server.pem": "[Objectives.CONTROLLERS]"
            }
        }
        status_dict["security_admin"] = {
            "[Version.V24-unlimited]": {
                "/home/cbis-admin/secadmin.pem": "[Objectives.CONTROLLERS, Objectives.COMPUTES]"
            }
        }
        status_dict["cinder"] = {
            "[Version.V24-unlimited]": {
                "/var/lib/config-data/puppet-generated/cinder/etc/cinder/cinder-server.pem": "[Objectives.CONTROLLERS]"
            }
        }
        status_dict["nova"] = {
            "[Version.V24-unlimited]": {
                "/var/lib/config-data/puppet-generated/nova_libvirt/etc/nova/nova-server.pem": "[Objectives.COMPUTES]"
            }
        }
        return status_dict

    def _enrichment_certificate_dictionary_for_cna(self, status_dict):
        is_clcm_embeded = self.get_first_value_from_data_collector(IsClcmEmbededDataCollector)
        if is_clcm_embeded:
            status_dict = self._remove_keys(status_dict, ["openstack_ca_crt"])
        return status_dict

    def _enrichment_certificate_dictionary_for_ncs(self, status_dict):
        assert (gs.get_deployment_type() == Deployment_type.NCS_OVER_BM)
        if gs.get_version() >= Version.V22:
            management_ip = self.get_first_value_from_data_collector(ProvisioningVipDataCollector)
            status_dict["registry_podman_management_ip"] = {
                "[Version.V22-unlimited]": {
                    "/etc/containers/certs.d/{management_ip}:8787/ca.crt".format(management_ip=management_ip):
                        "[Objectives.MANAGERS, Objectives.MASTERS, Objectives.EDGES, Objectives.WORKERS, "
                        "Objectives.MONITOR, Objectives.STORAGE]"
                }
            }
        if gs.is_ncs_central():
            status_dict = self._remove_keys(status_dict, ["anchor_ca_crt", "rabbitmq"])
            status_dict["anchor_ca_crt"] = {
                "[Version.V22-unlimited]": {
                    "/etc/pki/ca-trust/source/anchors/ca.crt.pem": "[Objectives.MANAGERS, Objectives.MASTERS, Objectives.MONITOR]"
                }
            }
            status_dict["management_server"] = {
                "[Version.V22-unlimited]": {
                    "/opt/management/certs/{cluster_name}/server.crt.pem": "[Objectives.MANAGERS]"
                }
            }
            status_dict["zabbix_server_crt"] = {
                "[Version.V22_12-Version.V23_10]": {
                    "/var/lib/zabbix/enc/server.crt.pem": "[Objectives.MANAGERS]"
                }
            }
            status_dict["zabbix_node_crt"] = {
                "[Version.V22_12-Version.V23_10]": {
                    "/var/lib/zabbix/enc/node.crt.pem": "[Objectives.ALL_NODES]"
                }
            }
            status_dict["zabbix_ca_crt"] = {
                "[Version.V22_12-Version.V23_10]": {
                    "/var/lib/zabbix/enc/ca.crt.pem": "[Objectives.MANAGERS]"
                }
            }

            deploy_ssc = self.get_output_from_run_cmd(
                "sudo hiera -c /usr/share/cbis/data/cbis_hiera.yaml cbis::openstack_deployment::deploy_ssc"
            ).strip()

            deployment_type = self.get_output_from_run_cmd(
                "sudo hiera -c /usr/share/cbis/data/cbis_hiera.yaml cbis::openstack_deployment::ssc_deployment_type"
            ).strip()

            if deploy_ssc == "true" and deployment_type == "local":

                status_dict["indexsearch_ca"] = {
                    "[Version.V23_10-unlimited]": {
                        "/etc/ssc/indexsearch/certs/ca.crt.pem": "[Objectives.MANAGERS, Objectives.MONITOR]"
                    }
                }
                status_dict["indexsearch_node"] = {
                    "[Version.V23_10-unlimited]": {
                        "/etc/ssc/indexsearch/certs/node.crt.pem": "[Objectives.MANAGERS, Objectives.MONITOR]"
                    }
                }
                status_dict["indexsearch_server"] = {
                    "[Version.V23_10-unlimited]": {
                        "/etc/ssc/indexsearch/certs/server.crt.pem": "[Objectives.MANAGERS, Objectives.MONITOR]"
                    }
                }
            status_dict["pki_server_crt"] = {
                "[Version.V22-Version.V23_10]": {
                    "/etc/pki/tls/private/{cluster_name}/server.crt.pem": "[Objectives.MANAGERS]"
                }
            }
        hotfix_list = gs.get_hotfix_list().keys()
        if gs.get_version() > Version.V23_10 or (gs.get_version() == Version.V23_10 and len(hotfix_list) > 0):
            status_dict = self._remove_keys(status_dict, ["rabbitmq"])
        return status_dict

    def get_status_dict_by_deployment_type(self):
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
        if Deployment_type.is_cbis(gs.get_deployment_type()) and \
                ConfigStore.get_cbis_user_config()['CBIS']['openstack_deployment'].get("barbican_backend") == "p11_crypto":
            status_dict = self._enrichment_certificate_dictionary_using_barbican(status_dict)
        if gs.get_deployment_type() == Deployment_type.NCS_OVER_BM:
            status_dict = self._enrichment_certificate_dictionary_for_ncs(status_dict)
        if gs.get_deployment_type() in Deployment_type.get_ncs_vsphere_openstack_types():
            status_dict = self._enrichment_certificate_dictionary_for_cna(status_dict)
        return status_dict

    def load_certificate_dictionary(self):
        status_dict = self.get_status_dict_by_deployment_type()
        cert_testing_dict = {}
        host_roles = self._host_executor.roles
        for cert_name, cert_version_dict in list(status_dict.items()):
            cert_testing_dict[cert_name] = []
            for cert_version, cert_path_dict in list(cert_version_dict.items()):
                assert type(cert_path_dict) is dict, "Expected: {} of type dict, actual: {}".format(
                    cert_path_dict, type(cert_path_dict))
                for cert_path, cert_objectives in list(cert_path_dict.items()):
                    if not Version.is_version_in_range(gs.get_version(), cert_version):
                        continue
                    if set(eval(cert_objectives)).intersection(set(host_roles)):
                        if "{cluster_name}" not in cert_path:
                            cert_testing_dict[cert_name].append(cert_path)
                        else:
                            cert_testing_dict[cert_name].append(cert_path.format(cluster_name=gs.get_cluster_name()))
            if cert_testing_dict[cert_name] == []:
                del cert_testing_dict[cert_name]
        return cert_testing_dict

    def _test_certificates(self, cert_testing_dict):
        self._table_system_info = TableSystemInfo(table=[], headers=["Certification name", "Details", "End date", "Days to end",
                                                                     "Will end in 90 days", "Renewed Automatically", "CBIS/NCS Certificate"])
        self._table_system_info.set_expected_column_values(
            column_header="Will end in 90 days", valid_value=["No"],
            invalid_value=[r".+\sPlease find the certificate location and test it manually.$",
                           r"^Yes, will expire in \d+ days$", r"Expiry date over", r"sys_problem"])
        self._is_clean_cmd_info = True
        error_list = []
        value, not_ready_list, not_found_list = self.calculate_for_infra_certificates(cert_testing_dict)
        self._table_system_info.table.extend(value)

        if Objectives.ONE_MASTER in self.get_host_roles():
            value2, not_ready_list2, error_list2 = self.calculate_for_tls_opaque_secret_certificates()
            not_ready_list.extend(not_ready_list2)
            error_list.extend(error_list2)
            self._table_system_info.table.extend(value2)
        res = True
        self._table_system_info.table = sorted(self._table_system_info.table, key=self.sort_key)
        if len(not_ready_list) > 0:
            path = self.get_paths_list_from_names_list(cert_testing_dict, not_ready_list)
            self._failed_msg += "\nCertificate will expire for:\n{}\nPlease check\n".format(
                "\n".join(path))
            res = False

        if len(error_list) > 0:
            self._failed_msg += "\nCertificate data missing for:\n{}\nPlease check\n".format(
                "\n".join(self.get_paths_list_from_names_list(cert_testing_dict, error_list)))
            res = False

        if len(not_found_list) > 0:
            self._failed_msg += "\nCouldn't find certificates:\n{}\nPlease test them manually.\n".format(
                "\n".join(self.get_paths_list_from_names_list(cert_testing_dict, not_found_list)))
            self._severity = Severity.NOTIFICATION
            res = False

        if not self._table_system_info.table:
            self._table_system_info.table = None

        return res

    def get_paths_list_from_names_list(self, cert_dict, cert_names_list):
        paths_list = []
        for cert_name in cert_names_list:
            if cert_name in cert_dict:
                for cert_path in cert_dict[cert_name]:
                    paths_list.append(cert_path)
            else:
                paths_list.append(cert_name)
        return paths_list

    def sort_key(self, element):
        value = element[3]
        if (type(value) is get_unicode_type() and value.isdigit()) or type(value) is int:
            return int(value)
        else:
            return float("-inf")
