from __future__ import absolute_import
from datetime import datetime as dt

from HealthCheckCommon.operations import *
from HealthCheckCommon.validator import InformatorValidator
from flows.Security.Certificate.allcertificate_expiry_dates import *
from tools import adapter
import tools.sys_parameters as sys_param


class CertificateExpiryVerifyBareMetal(InformatorValidator, CertificateExpiryDates):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ALL_NODES, Objectives.MANAGERS, Objectives.MONITOR]}

    def set_document(self):
        self._unique_operation_name = "verify_certificate_expiry_ncs_baremetal"
        self._title = "Verify Certificate Expiry BM"
        self._failed_msg = "Please check the certificate dates and renew manually if no autorenewal option for them"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.RISK_EXPIRY_DATE_APPROACHING]
        self._system_info = ""
        self._is_pure_info = False
        self._is_highlighted_info = True
        self._title_of_info = "Verify Certificate Expiry BM"
        self._is_clean_cmd_info = True

    def is_validation_passed(self):
        cert_testing_dict = self.load_certificate_dictionary()
        return self._test_certificates(cert_testing_dict)


class CertificateExpiryVerifyCNA(InformatorValidator, CertificateExpiryDates):
    objective_hosts = {
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ALL_NODES, Objectives.MANAGERS, Objectives.MONITOR,
                                             Objectives.DEPLOYER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ALL_NODES, Objectives.MANAGERS, Objectives.MONITOR,
                                           Objectives.DEPLOYER]}

    def set_document(self):
        self._unique_operation_name = "verify_certificate_expiry_cna"
        self._title = "Verify Certificate Expiry CNA"
        self._failed_msg = "Please check the certificate dates and renew manually if no auto-renewal option for them"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.RISK_EXPIRY_DATE_APPROACHING]
        self._system_info = ""
        self._is_highlighted_info = True
        self._is_pure_info = False
        self._title_of_info = "Verify Certificate Expiry CNA"
        self._is_clean_cmd_info = True

    def is_validation_passed(self):
        cert_testing_dict = self.load_certificate_dictionary()

        return self._test_certificates(cert_testing_dict)


# --------------------------------------

class CheckCaCertificateModulus(Validator):
    objective_hosts = Objectives.ONE_MASTER
    modulus_check_harbor_crt_out = None

    def get_CA_collector_class(self):
        assert False

    def get_harbor_secret(self):
        self._is_clean_cmd_info = True
        modulus_check_harbor_crt_cmd = "sudo kubectl get secrets -n ncms harbor-harbor-cert-srt -o jsonpath=\"{.data['ca\\.crt']}\" | base64 -d | openssl x509 -noout -modulus"
        if CheckCaCertificateModulus.modulus_check_harbor_crt_out is None:
            CheckCaCertificateModulus.modulus_check_harbor_crt_out = self.get_output_from_run_cmd(
                modulus_check_harbor_crt_cmd).strip()
        return CheckCaCertificateModulus.modulus_check_harbor_crt_out

    def is_validation_passed(self):
        modulus_check_harbor_crt_out = self.get_harbor_secret().strip()
        collector_class = self.get_CA_collector_class()
        status_per_host = self.run_data_collector(collector_class,
                                                  modulus_check_harbor_crt_out=modulus_check_harbor_crt_out)
        fail_hosts = []
        exception_hosts = []

        for host in status_per_host:
            if status_per_host[host] is None:
                exception_hosts.append(host)
            if status_per_host[host] is False:
                fail_hosts.append(host)

        if len(fail_hosts) > 0:
            self._failed_msg = "at hosts {}:{} ".format(fail_hosts, self._failed_msg)
            return False

        if len(exception_hosts):
            raise UnExpectedSystemOutput(", ".join(exception_hosts), "", "", str(self._validation_log))

        return True


class CollectingCaCHKStatues(DataCollector):
    objective_hosts = [Objectives.MASTERS, Objectives.WORKERS, Objectives.EDGES]

    def collect_data(self, modulus_check_harbor_crt_out):
        self._is_clean_cmd_info = True
        if gs.is_central_cluster():
            return True

        k8_ca = "/etc/kubernetes/ssl/ca.pem"
        modulus_chk_k8_ca_cmd = " sudo openssl x509 -in " + k8_ca + " -noout -modulus"
        k8_ca_out_flg = False

        modulus_chk_k8_ca_out = self.get_output_from_run_cmd(modulus_chk_k8_ca_cmd).strip()
        if modulus_chk_k8_ca_out == modulus_check_harbor_crt_out:
            k8_ca_out_flg = True

        return k8_ca_out_flg


class CollectingCaPublicPrivateStatues(DataCollector):
    objective_hosts = [Objectives.MASTERS, Objectives.WORKERS, Objectives.EDGES]

    def collect_data(self, modulus_check_harbor_crt_out):
        self._is_clean_cmd_info = True
        if gs.is_central_cluster():
            return True

        openssl_cert = "/etc/openssl/ca.pem"
        openssl_key = "/etc/openssl/ca-key.pem"
        anchor_ca = "/etc/pki/ca-trust/source/anchors/ca.pem"
        modulus_chk_publickey_cmd = "sudo  openssl x509 -in " + openssl_cert + " -noout -modulus"
        modulus_chk_privatekey_cmd = "sudo openssl rsa -in " + openssl_key + " -noout -modulus"
        modulus_chk_anchor_ca_cmd = " sudo openssl x509 -in " + anchor_ca + " -noout -modulus"

        ca_check_flag = False

        modulus_chk_publickey_out = self.get_output_from_run_cmd(modulus_chk_publickey_cmd).strip()
        modulus_chk_privatekey_out = self.get_output_from_run_cmd(modulus_chk_privatekey_cmd).strip()
        modulus_chk_anchor_ca_out = self.get_output_from_run_cmd(modulus_chk_anchor_ca_cmd).strip()
        if modulus_chk_privatekey_out == modulus_chk_publickey_out:
            if modulus_chk_anchor_ca_out == modulus_chk_publickey_out:
                if modulus_check_harbor_crt_out == modulus_chk_publickey_out:
                    ca_check_flag = True

        return ca_check_flag


class CollectingCaTrustedStoreStatues(DataCollector):
    objective_hosts = [Objectives.MASTERS, Objectives.WORKERS, Objectives.EDGES]

    def collect_data(self, modulus_check_harbor_crt_out):
        self._is_clean_cmd_info = True
        if gs.is_central_cluster():
            return True

        openssl_cert = "/etc/openssl/ca.pem"
        k8_ca = "/etc/kubernetes/ssl/ca.pem"
        openssl_trusted_store_cmd = "sudo openssl verify -CApath /etc/pki/ca-trust/extracted/pem/ -purpose sslserver " + openssl_cert
        k8_trusted_store_cmd = " sudo openssl verify -CApath /etc/pki/ca-trust/extracted/pem/ -purpose sslserver " + k8_ca
        trusted_store_flag = False

        openssl_trusted_store_out = self.get_output_from_run_cmd(openssl_trusted_store_cmd).strip()
        k8_trusted_store_out = self.get_output_from_run_cmd(k8_trusted_store_cmd).strip()
        if str("OK") in openssl_trusted_store_out and str("OK") in k8_trusted_store_out:
            trusted_store_flag = True

        return trusted_store_flag

################### SOUVIK CODE STARTS #####################
###     ICET-2812 | Bug fix | ExternalCA Check for NCS CNA
###     Author :   SOUVIK DAS |     11-03-2025 
############################################################

class CaIssuer_CNB(DataCollector):
    objective_hosts = [Objectives.ONE_MANAGER]

    def collect_data(self):
        ca_issuer_values = {}
        docker_or_podman = adapter.docker_or_podman()
        # This command used to detect EXTERNALLY SIGNED CERT IS USED OR NOT in CLUSTER. The command takes the data from REDIS DB | By default when default NCS BCMT CA used then the value is NULL. If any external CA is used then the value is "true"
        redis_externally_signed_value_command = "sudo {} exec redis redis-cli " \
                                                "-n 7 get general:IsExternallySigned".format(docker_or_podman)
        ca_issuer_values['is_externally_signed'] = self.get_output_from_run_cmd(redis_externally_signed_value_command, add_bash_timeout=True).strip()

        # This command used to detect CA TYPE in CLUSTER. The command takes the data from REDIS DB | By default when default NCS BCMT CA used then the value is NULL. If any external CA is used then the value becomes the external CA ISSUER NAME like "CMPv2"
        redis_ca_type_value_command = "sudo {} exec redis redis-cli -n 7 get general:ca_type".format(docker_or_podman)
        ca_issuer_values['ca_type'] = self.get_output_from_run_cmd(redis_ca_type_value_command, add_bash_timeout=True).strip()

        if ca_issuer_values['ca_type'] == "" and ca_issuer_values['is_externally_signed'] == "":
            ca_issuer_values['is_external_ca'] = False   ##  Default BCMT CA used
        elif ca_issuer_values['ca_type'].upper() == "INTERNAL_CA" and ca_issuer_values['is_externally_signed'].upper() == "FALSE":
            ca_issuer_values['is_external_ca'] = False    ##  INTERNAL_CA used means CA provider integration with internal issuer
        else:
            ca_issuer_values['is_external_ca'] = True     ##  External CA used

        return ca_issuer_values

class CaIssuer_CNA_23_10(DataCollector):
    objective_hosts = [Objectives.ONE_MASTER]

    def get_etcd_command(self, command_body):
        PATH_CLIENT_CERT = "/etc/etcd/ssl/etcd-client.pem"
        PATH_CLIENT_KEY = "/etc/etcd/ssl/etcd-client-key.pem"
        PATH_CA_CERT = "/etc/etcd/ssl/ca.pem"
        PATH_ETCD_ENDPOINTS = "/etc/etcd/etcd_endpoints.yml"
        
        cmd = "sudo cat {}".format(PATH_ETCD_ENDPOINTS)
        endpoints = self.get_output_from_run_cmd(cmd)
        endpoints_after_strip = re.findall('etcd_endpoints: "(.*)"', endpoints)
        endpoints = endpoints_after_strip[0]
        
        ETCD_BASE_CMD_PATTERN = "sudo ETCDCTL_API=3 bash -c 'etcdctl --endpoints={} --cacert={} --cert={} --key={} {}'".format(endpoints, PATH_CA_CERT, PATH_CLIENT_CERT, PATH_CLIENT_KEY, command_body)

        return ETCD_BASE_CMD_PATTERN

    def collect_data(self):
        ca_issuer_values = {}
        # This command used to detect EXTERNALLY SIGNED CERT IS USED OR NOT in CLUSTER. The command takes the data from ETCD Database | By default when default NCS BCMT CA used then "IsExternallySigned" is FALSE. If any external CA is used then the value is "TRUE"

        cmd = self.get_etcd_command(' get /BCMTClusterManager/bcmt_config/cluster_config/certificates/IsExternallySigned')
        out = self.get_output_from_run_cmd(cmd).strip()
        result = out.split("\n")
        ca_issuer_values['is_externally_signed'] = result[1].replace("\"","")

        # This command used to detect CA TYPE in CLUSTER. The command takes the data from ETCD Database | By default when default NCS BCMT CA used then the value of "IssuerCA" is NULL. If any external CA is used then the value becomes the external CA ISSUER NAME like "CMPv2"

        cmd = self.get_etcd_command(' get /BCMTClusterManager/bcmt_config/cluster_config/certificates/issuerRef/issuerName')
        out = self.get_output_from_run_cmd(cmd).strip()
        result = out.splitlines()
        ca_issuer_values['ca_type'] =  result[1].replace("\"","")

        cmd = self.get_etcd_command(' get /BCMTClusterManager/bcmt_config/cluster_config/certificates/IsCrossSigned')
        out = self.get_output_from_run_cmd(cmd).strip()
        if out:
            result = out.splitlines()
            if len(result) >= 2:
                ca_issuer_values['cross_signed'] =  result[1].replace("\"","")
            else:
                ca_issuer_values['cross_signed'] =  "false"
        else:
            ca_issuer_values['cross_signed'] =  "false"

        if ca_issuer_values['ca_type'] == "ncms-ca-issuer" and ca_issuer_values['is_externally_signed'].upper() == "FALSE":
            ca_issuer_values['is_external_ca'] = False   ##  Default BCMT CA used
        elif ca_issuer_values['ca_type'].upper() == "INTERNAL_CA" and ca_issuer_values['is_externally_signed'].upper() == "FALSE":
            ca_issuer_values['is_external_ca'] = False    ##  INTERNAL_CA used means CA provider integration with internal issuer
        else:
            ca_issuer_values['is_external_ca'] = True     ##  External CA used

        return ca_issuer_values

################### SOUVIK CODE ENDS #############################

class CheckCaCHKCertificateModulus(CheckCaCertificateModulus):
    objective_hosts = Objectives.ONE_MASTER

    def set_document(self):
        self._unique_operation_name = "verify_ca_CHK_certificate_modulus"
        self._title = "Verify ca CHK certificate modulus"
        self._failed_msg = "Please check the ca modulus"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]
        self._is_clean_cmd_info = True

    def get_CA_collector_class(self):
        return CollectingCaCHKStatues


class CheckCaPublicPrivateCertificateModulus(CheckCaCertificateModulus):
    objective_hosts = [Objectives.ONE_MASTER]

    def is_prerequisite_fulfilled(self):
        if gs.get_version() < Version.V23_10:
            return False
        
        ca_issuer_dict = self.run_data_collector(CaIssuer_CNA_23_10)
        ca_issuer_data = list(ca_issuer_dict.values())[0]

        if (not ca_issuer_data['is_external_ca']) and (ca_issuer_data['cross_signed'] == "false"):
            return True

    def set_document(self):
        self._unique_operation_name = "verify_ca_public_private_certificate_modulus"
        self._title = "Verify ca private and public keys have different modulus"
        self._failed_msg = "private and public keys have different modulus"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]
        self._is_clean_cmd_info = True

    def get_CA_collector_class(self):
        return CollectingCaPublicPrivateStatues


class CheckCaTrustedStoreCertificateModulus(CheckCaCertificateModulus):
    objective_hosts = Objectives.ONE_MASTER

    def set_document(self):
        self._unique_operation_name = "verify_ca_trusred_store_certificate_modulus"
        self._title = "Verify ca trusted store certificate modulus"
        self._failed_msg = "CA is not trusted store "
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]
        self._is_clean_cmd_info = True

    def get_CA_collector_class(self):
        return CollectingCaTrustedStoreStatues


class CheckEphemeralWebhook(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "check_ephemeral_webhook"
        self._title = "check ephemeral webhook certificate is expired or not"
        self._failed_msg = "Ephemeral webhook certificate has been expired"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.SYMPTOM]
        self._is_clean_cmd_info = True

    def is_chart_installed(self):
        chart_list = self.get_output_from_run_cmd("sudo helm list --all-namespaces --output json --deployed")
        helm_data = json.loads(chart_list)
        if int(len(helm_data)) == 0:
            raise UnExpectedSystemOutput(self.get_host_ip(), chart_list, "Helm list is empty ")
            # self._failed_msg = "Helm list is empty!!"
            # return False
        for data in helm_data:
            if data["name"] == "bcmt-ephemeral-webhook":
                return True
        return False

    def check_secret_expiry(self):
        validate_secret = self.get_output_from_run_cmd(
            "sudo kubectl get secret ephemeral-webhook-certs -n kube-system -o jsonpath=\"{.data['cert\\.pem']}\" "
            "| base64 -d | openssl x509 -enddate -noout")
        end_date_str = validate_secret[len("notAfter="):].strip()
        end_date = dt.strptime(end_date_str, "%b %d %H:%M:%S %Y %Z")
        current_date = dt.now()
        if end_date >= current_date:
            return True
        else:
            self._failed_msg = self._failed_msg + " | " + "Expiration Date: " + str(end_date_str)
            return False

    def is_validation_passed(self):
        chart_installed = self.is_chart_installed()
        if not chart_installed:
            return True
        else:
            certificate_valid = self.check_secret_expiry()
            if not certificate_valid:
                self._failed_msg = self._failed_msg + "\nPlease un-install bcmt-ephemeral-webhook chart!!\n"
                return False
            else:
                return True


#######################################################
#   ICET-2815 | If external CA used in 23.10 CNA then the file
#   /etc/kubernetes/ssl/serviceaccount.pem will not be there
#   SOUVIK DAS | 12-03-2025
#######################################################

class VerifyServiceAccountCertificate(Validator):
    objective_hosts = [Objectives.MASTERS]

    def set_document(self):
        self._unique_operation_name = "verify_service_account_certificate"
        self._title = "verify service account certificate - check if pem file exists"
        self._failed_msg = "TBD"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]
        self._is_clean_cmd_info = True

    def file_check(self):
        file_path = "/etc/kubernetes/ssl/serviceaccount.pem"
        if not self.file_utils.is_file_exist(file_path):
            self._failed_msg = "{} is missing on {}".format(file_path, self.get_host_name())
            return False
        else:
            return True

    def is_validation_passed(self):
        CNA_setup = False
        if not(gs.get_deployment_type() == Deployment_type.NCS_OVER_BM):
            CNA_setup = True
            is_external_CA_issuer_used_dict = self.run_data_collector(CaIssuer_CNA_23_10)
            is_external_CA_issuer_data = list(is_external_CA_issuer_used_dict.values())[0]
            is_external_CA_issuer_used = is_external_CA_issuer_data['is_external_ca']

        ##  CNB - all -applicable internal and external CA
        if CNA_setup == False:
            result = self.file_check()
            return result

        ## CNA - 23.10 onward, if only inetrnal CA applicable. External CA not applicable
        ## If External CA used and CNA . In case of ExternalCA this file will NOT exist for CNA.
        if CNA_setup == True and not(is_external_CA_issuer_used):
            result = self.file_check()
            return result
        else:
            return True

class VerifyHarborPodCertificate(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "verify_harbor_pods_latest_cert"
        self._title = "Verify if Harbor Pods are utilizing the latest available certificate"
        self._failed_msg = ("Harbor pods haven't been restarted since the Harbor certificates were auto-renewed by cert-manager, "
                            "and they are not using the latest available certificate.\n")
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):

        cmd_output = self.get_output_from_run_cmd(
            "sudo kubectl get pods -n ncms | grep harbor-harbor-core").strip()

        harbor_core_pod_name = cmd_output.split()[0]
        if harbor_core_pod_name:
            self.add_to_validation_log("Manually check if the Harbor pod '{}' is running.".format(harbor_core_pod_name))
        validate_secret_entry = self.get_output_from_run_cmd(
            "sudo kubectl exec -it {} -n ncms -- /usr/bin/cat /etc/harbor/ssl/core/tls.crt | "
            "openssl x509 -enddate -noout | grep 'notAfter'".format(
                harbor_core_pod_name)
        )
        if not validate_secret_entry:
            raise UnExpectedSystemOutput(self.get_host_ip(), validate_secret_entry, "The secret entry does not exist.")

        validate_secret_end_str_date = validate_secret_entry.split('=')[1].strip()
        validate_secret_date = dt.strptime(validate_secret_end_str_date, "%b %d %H:%M:%S %Y GMT")
        certificate_expiry_str_date = self.get_certificate_expiry_date()
        certificate_expiry_date = dt.strptime(certificate_expiry_str_date,"%b %d %H:%M:%S %Y GMT")

        if certificate_expiry_date <= validate_secret_date:
            return True
        else:
            self._failed_msg += " | Expiration Date Mismatch: Expected: {} | Actual: {}".format(
                str(validate_secret_date), str(certificate_expiry_date))
            return False

    def get_certificate_expiry_date(self):
        certificate_expiry_entry = self.get_output_from_run_cmd("sudo kubectl get secret harbor-harbor-cert-srt -n ncms -o jsonpath='{.data.tls\\.crt}' "
                                    "| base64 -d | openssl x509 -enddate -noout | grep 'notAfter'").strip()
        certificate_expiry_str_date = certificate_expiry_entry.split('=')[1].strip()
        return certificate_expiry_str_date


class VerifySecretCaCertMatch(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "verify_k8s_secret_ca_cert_match"
        self._title = "Verify Kubernetes CA Secret Matches System CA"
        self._failed_msg = "The CA certificate in the Kubernetes secret 'ca-key-pair' does not match the system CA certificate at '/etc/openssl/ca.pem'."
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]
        self._blocking_tags = [BlockingTag.CERT_RENEWAL]

    def is_validation_passed(self):

        system_ca_file = "/etc/openssl/ca.pem"
        if not self.file_utils.is_file_exist(system_ca_file):
            raise UnExpectedSystemOutput(self.get_host_ip(), "",
                                         "", "System CA certificate file {} does not exist".format(system_ca_file))

        system_ca_cert_cmd = "sudo cat {}".format(system_ca_file)
        system_ca_cert = self.get_output_from_run_cmd(system_ca_cert_cmd)

        if not system_ca_cert.strip():
            raise UnExpectedSystemOutput(self.get_host_ip(),system_ca_cert_cmd, system_ca_cert,"The system CA certificate file {} does not exist or is empty.".format(system_ca_file))

        k8s_ca_cert_cmd = 'sudo kubectl get secrets -n ncms ca-key-pair -o jsonpath="{.data[\'tls\\.crt\']}" | base64 -d'
        k8s_ca_cert = self.get_output_from_run_cmd(k8s_ca_cert_cmd)

        if not k8s_ca_cert.strip():
            raise UnExpectedSystemOutput(self.get_host_ip(),k8s_ca_cert_cmd, k8s_ca_cert, "The Kubernetes secret 'ca-key-pair' does not exist or is empty.")

        if k8s_ca_cert == system_ca_cert:
            return True
        else:
            return False


class BaseCertificateValidator(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.MANAGERS]
    }

    def validate_certificates(self, cert_map, service_name):
        errors = []

        for cert_file in cert_map.values():
            if not self.file_utils.is_file_exist(cert_file):
                raise UnExpectedSystemOutput(
                    self.get_host_ip(),
                    "",
                    "",
                    "Certificate file does not exist: {}".format(cert_file),
                )
            is_valid, expiry_date_string = self.is_cert_not_expired(cert_file)

            if not is_valid:
                errors.append(
                    "Certificate expired for : '{}' | Expiration Date: {}".format(cert_file, expiry_date_string)
                )

        if self.read_content(cert_map["service_ca"]) != \
                self.read_content(cert_map["ncs_ca"]):
            errors.append(
                "Certificate content mismatch! {} CA certificate '{}' does not match NCS CA certificate '{}' "
                .format(service_name, cert_map["service_ca"], cert_map["ncs_ca"])
            )

        if self.read_content(cert_map["service_server"]) != \
                self.read_content(cert_map["ncs_server"]):
            errors.append(
                "Certificate content mismatch! {} Server certificate '{}' does not match NCS Server certificate '{}'"
                .format(service_name, cert_map["service_server"], cert_map["ncs_server"])
            )

        if self.read_content(cert_map["service_node"]) != \
                self.read_content(cert_map["ncs_node"]):
            errors.append(
                "Certificate content mismatch! {} Node certificate '{}' does not match NCS Node certificate '{}'".
                format(service_name, cert_map["service_node"], cert_map["ncs_node"])
            )

        if errors:
            self._failed_msg += "\n" + "\n".join(errors)
            return False

        return True

    def read_content(self, file_path):
        return self.get_output_from_run_cmd(
            "sudo cat {}".format(file_path)
        ).strip()

    # Returns bool(is_cert_not_expired) and str values(expiry date string)
    def is_cert_not_expired(self, cert_path):
        cmd = "sudo openssl x509 -enddate -noout -in {}".format(cert_path)
        output = self.get_output_from_run_cmd(cmd).strip()

        # expected: notAfter=Jun 20 10:00:00 2029 GMT
        if not output.startswith("notAfter="):
            raise UnExpectedSystemOutput(
                self.get_host_ip(),
                "",
                output,
                "Unexpected openssl output for cert: {}".format(cert_path),
            )

        expiry_date_string = output[len("notAfter="):].strip()
        end_date = dt.strptime(expiry_date_string, "%b %d %H:%M:%S %Y %Z")
        current_date = dt.utcnow()

        if end_date >= current_date:
            return True, expiry_date_string
        return False, expiry_date_string


class VerifyZabbixCertOnManager(BaseCertificateValidator):
    def set_document(self):
        self._unique_operation_name = "verify_zabbix_cert_on_ncs_manager"
        self._title = "Verify Zabbix certs on manager"
        self._failed_msg = "Zabbix certificate validation failed."
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]
        self._blocking_tags = [BlockingTag.CERT_RENEWAL]

    def is_validation_passed(self):
        cert_map = {
            "service_ca": "/var/lib/zabbix/enc/ca.crt.pem",
            "service_server": "/var/lib/zabbix/enc/server.crt.pem",
            "service_node": "/var/lib/zabbix/enc/node.crt.pem",
            "ncs_ca": "/etc/pki/ca-trust/source/general-cert/ca.crt.pem",
            "ncs_server": "/etc/pki/tls/private/general-cert/server.crt.pem",
            "ncs_node": "/etc/pki/tls/private/general-cert/node.crt.pem",
        }

        return self.validate_certificates(cert_map, "Zabbix")


class VerifyElasticsearchCertOnManager(BaseCertificateValidator):
    def set_document(self):
        self._unique_operation_name = "verify_elasticsearch_cert_on_ncs_manager"
        self._title = "Verify Elasticsearch certs on manager"
        self._failed_msg = "Elasticsearch certificate validation failed."
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]
        self._blocking_tags = [BlockingTag.CERT_RENEWAL]

    def is_validation_passed(self):
        cert_map = {
            "service_ca": "/etc/ssc/indexsearch/certs/ca.crt.pem",
            "service_server": "/etc/ssc/indexsearch/certs/server.crt.pem",
            "service_node": "/etc/ssc/indexsearch/certs/node.crt.pem",
            "ncs_ca": "/etc/pki/ca-trust/source/general-cert/ca.crt.pem",
            "ncs_server": "/etc/pki/tls/private/general-cert/server.crt.pem",
            "ncs_node": "/etc/pki/tls/private/general-cert/node.crt.pem",
        }

        return self.validate_certificates(cert_map, "Elasticsearch")

