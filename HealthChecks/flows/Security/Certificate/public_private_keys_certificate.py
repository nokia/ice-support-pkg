from __future__ import absolute_import
from flows.Security.Certificate.allcertificate_expiry_dates import *


class CertAndKeyDataCollector(DataCollector):
    objective_hosts = []
    handle_error = False

    def collect_data(self, **kwargs):
        cert = kwargs['cert']
        cert_key = kwargs['cert_key']
        message = None
        is_cert_exist = self.file_utils.is_file_exist(cert)
        is_cert_key_exist = self.file_utils.is_file_exist(cert_key)
        if not is_cert_exist and not is_cert_key_exist:
            return {"check_flag": True, "message": ""}
        if not is_cert_exist:
            message = "Certificate: {} not found, Please find the certificate location and test it manually.".format(
                cert)
        if not is_cert_key_exist:
            message = "Certificate key: {} not found, Please find the certificate key location and test it " \
                      "manually.".format(cert_key)
        if message:
            return {"check_flag": False, "message": message}
        message = "Failed to validate certificate '{}' with key '{}'".format(cert, cert_key)
        modulus_publickey_cmd = "sudo  openssl x509 -in {} -noout -modulus"
        modulus_privatekey_cmd = "sudo openssl rsa -in {} -noout -modulus"
        return_code, modulus_publickey_out, err = self.run_cmd(modulus_publickey_cmd.format(cert))
        if return_code != 0:
            return {"check_flag": False, "message": message}
        return_code, modulus_privatekey_out, err = self.run_cmd(modulus_privatekey_cmd.format(cert_key))
        if return_code != 0:
            return {"check_flag": False, "message": message}
        if modulus_privatekey_out.strip() == modulus_publickey_out.strip():
            return {"check_flag": True, "message": ""}
        return {"check_flag": False, "message": message}

class VerifyPrivateKeyWithCertificate(Validator):
    objective_hosts = [Objectives.ONE_MANAGER, Objectives.UC]

    def _enrichment_public_private_keys_dictionary_for_cnb(self, certification_and_key_pairs, deployment_type_key):
        assert (gs.get_deployment_type() in Deployment_type.get_ncs_types())
        if gs.is_ncs_central():

            certification_and_key_pairs[deployment_type_key]["zabbix_server_crt"] = {
                "[Version.V22_12-Version.V23_10]": {
                    "cert": "/var/lib/zabbix/enc/server.crt.pem",
                    "key": "/var/lib/zabbix/enc/server.key.pem",
                    "role": "[Objectives.MANAGERS]"
                }
            }
            certification_and_key_pairs[deployment_type_key]["zabbix_node_crt"] = {
                "[Version.V22_12-Version.V23_10]": {
                    "cert": "/var/lib/zabbix/enc/node.crt.pem",
                    "key": "/var/lib/zabbix/enc/node.key.pem",
                    "role": "[Objectives.MANAGERS, Objectives.ALL_NODES, Objectives.MONITOR]"
                }
            }
            certification_and_key_pairs[deployment_type_key]["indexsearch_node"] = {
                "[Version.V23_10-unlimited]": {
                    "cert": "/etc/ssc/indexsearch/certs/node.crt.pem",
                    "key": "/etc/ssc/indexsearch/certs/node.ssc.key.pem",
                    "role": "[Objectives.MANAGERS, Objectives.MONITOR]"
                }
            }
            certification_and_key_pairs[deployment_type_key]["indexsearch_server"] = {
                "[Version.V23_10-unlimited]": {
                    "cert": "/etc/ssc/indexsearch/certs/server.crt.pem",
                    "key": "/etc/ssc/indexsearch/certs/server.ssc.key.pem",
                    "role": "[Objectives.MANAGERS, Objectives.MONITOR]"
                }
            }
            certification_and_key_pairs[deployment_type_key]["management_server"] = {
                "[Version.V22-unlimited]": {
                    "cert": "/opt/management/certs/{cluster_name}/server.crt.pem",
                    "key": "/opt/management/certs/{cluster_name}/server.key.pem",
                    "role": "[Objectives.MANAGERS]"
                }
            }
            certification_and_key_pairs[deployment_type_key]["pki_server_crt"] = {
                "[Version.V22-Version.V23_10]": {
                    "cert": "/etc/pki/tls/private/{cluster_name}/server.crt.pem",
                    "key": "/etc/pki/tls/private/{cluster_name}/server.key.pem",
                    "role": "[Objectives.MANAGERS]"
                }
            }
        return certification_and_key_pairs

    def set_document(self):
        self._unique_operation_name = "compare_certification_with_private_key"
        self._title = "Verify public private keys certificate modulus"
        self._failed_msg = ""
        self._severity = Severity.ERROR
        self._is_clean_cmd_info = True
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        public_private_keys = "flows/Security/Certificate/public_private_keys.json"
        with open(public_private_keys) as json_file:
            certification_and_key_pairs = json.load(json_file)
        deployment_type_key = Deployment_type.get_deployment_type_key_from_value(gs.get_deployment_type())
        assert certification_and_key_pairs.get(deployment_type_key), "Missing {} in {} file".format(
            deployment_type_key, public_private_keys)
        if (gs.get_deployment_type() in Deployment_type.get_ncs_types()):
            certification_and_key_pairs = self._enrichment_public_private_keys_dictionary_for_cnb(
                certification_and_key_pairs, deployment_type_key)
        for cert_name in certification_and_key_pairs[deployment_type_key]:
            for version, cert_dict in list(certification_and_key_pairs[deployment_type_key][cert_name].items()):
                if version and not Version.is_version_in_range(gs.get_version(), version):
                    continue
                if ("{cluster_name}" in cert_dict['cert'] or "{cluster_name}" in cert_dict['key']):
                    cert_dict['cert'] = cert_dict['cert'].format(cluster_name=gs.get_cluster_name())
                    cert_dict['key'] = cert_dict['key'].format(cluster_name=gs.get_cluster_name())
                CertAndKeyDataCollector.objective_hosts = eval(cert_dict['role'])
                hosts_status = self.run_data_collector(CertAndKeyDataCollector, cert=cert_dict['cert'],
                                                       cert_key=cert_dict['key'])
                for host in hosts_status:
                    if hosts_status.get(host) and hosts_status[host].get("check_flag") and \
                            hosts_status[host]["check_flag"] is False:
                        self._failed_msg += "{} - {}\n".format(host, hosts_status[host]["message"])
        self.raise_if_no_collector_passed()
        if self._failed_msg:
            self._failed_msg += ("Note: in case of external certificates are installed, this failed validation "
                                 "can be ignored")
            return False
        return True