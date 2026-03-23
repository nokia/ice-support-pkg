from __future__ import absolute_import
from HealthCheckCommon.operations import *
from HealthCheckCommon.validator import Validator, InformatorValidator
from flows.Blueprint.CsfAddOnBlueprintDataCollectors import IstioVersion
from tools.python_utils import PythonUtils
import base64


class GetCertificate(DataCollector):
    objective_hosts = [Objectives.MASTERS]

    def collect_data(self):
        self._is_clean_cmd_info = True
        out = self.get_output_from_run_cmd('sudo cat /etc/kubernetes/ssl/ca.pem')
        return out


class VerifyRootCA(Validator):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._unique_operation_name = "verify_rootCA_certificate"
        self._title = "Verify if RootCA Certificate is same across all master modes"
        self._failed_msg = "Placeholder"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]
        self._is_clean_cmd_info = True

    def is_validation_passed(self):
        out = self.run_data_collector(GetCertificate)
        return self.is_values_equal(out)


    def is_values_equal(self, dict_obj):
        # Extract the values from the dictionary
        values = list(dict_obj.values())

        # Check if all values are the same
        unique_values = set(values)

        if len(unique_values) == 1:
            return True
        if None not in values:
            unique_stripped = set(v.strip() for v in values)
            if len(unique_stripped) == 1:
                first_value = values[0]
                different_keys = [key for key, value in dict_obj.items() if value.strip() != first_value.strip()]
                self._failed_msg = "RootCA Certificate Content does not match across all master nodes, leading or trailing unmatched white spaces found" + " ".join(different_keys)
                return False

        # Find the key(s) with values that are not the same as the first value
        first_value = values[0]
        different_keys = [key for key, value in dict_obj.items() if value != first_value]
        self._failed_msg = "RootCA Certificate Content does not match across all master nodes " + " ".join(different_keys)
        return False


class GetCACertificate(DataCollector):
    objective_hosts = [Objectives.ONE_MASTER]

    def collect_data(self):
        self._is_clean_cmd_info = True
        out = self.get_output_from_run_cmd('sudo cat /etc/kubernetes/ssl/ca.pem')
        return out


def _is_istio_used(self):
    _, istio_version_res = self.run_data_collector(IstioVersion)
    if len(list(istio_version_res.values())) >= 1 and len(list(list(istio_version_res.values())[0].values())) >= 1:
        istio_version = list(list(istio_version_res.values())[0].values())[
            0]  # for first node (master), first and only id
    else:
        raise UnExpectedSystemOutput(ip=self._host_executor.ip, cmd='', output='',
                                     message='Failed to obtain istio version from data collector\n')

    if '---' not in istio_version:  # if not '----', then valid version, it is installed!
        return True
    return False


def _is_istio_cni_node_present(self):
    helmre = self.get_output_from_run_cmd('sudo helm list --output json -A')
    helm_releases_unicode = json.loads(helmre)
    flag = False
    for release in helm_releases_unicode:
        if 'istio-cni-node' in release['name']:
            flag = True
    return flag


class VerifyRootCAandIstiofileContent(Validator):
    objective_hosts = [Objectives.MASTERS, Objectives.EDGES, Objectives.WORKERS]

    def is_prerequisite_fulfilled(self):
        return _is_istio_used(self) and _is_istio_cni_node_present(self)

    def set_document(self):
        self._unique_operation_name = "verify_RootCA_and_Istio_file_Content"
        self._title = "Verify if RootCA Certificate and Istio file Content matches"
        self._failed_msg = "RootCA Certificate and Istio file Content does not match"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]
        self._is_clean_cmd_info = True

    def is_validation_passed(self):
        filepath = "/etc/kubernetes/cni/net.d/ZZZ-istio-cni-kubeconfig"
        if not self.file_utils.is_file_exist(filepath):
            self._failed_msg = "File not found /etc/kubernetes/cni/net.d/ZZZ-istio-cni-kubeconfig"
            return False
        istio_cert = self.get_output_from_run_cmd('sudo cat /etc/kubernetes/cni/net.d/ZZZ-istio-cni-kubeconfig')
        cert_auth = re.search(r'certificate-authority-data:\s*(\S+)', istio_cert)
        if cert_auth:
            cert_auth_data = cert_auth.group(1)
        else:
            self._failed_msg = ("Certificate authority data not found in "
                                "/etc/kubernetes/cni/net.d/ZZZ-istio-cni-kubeconfig")
            return False
        out = self.run_data_collector(GetCACertificate)
        if not out:
            self._failed_msg = ("Certificate not found : /etc/kubernetes/ssl/ca.pem")
            return False
        else:
            for key, value in list(out.items()):
                if base64.b64encode(value).decode('utf-8') != cert_auth_data:
                    return False
            return True


class ValidateRootCAPositionInCRTBundle(Validator):
    objective_hosts = [Objectives.MASTERS]

    def set_document(self):
        self._unique_operation_name = "verify_RootCA_position_in_crt_bundle"
        self._title = "Verify if content of RootCA Certificate is at first position of Bundle CRT or not"
        self._failed_msg = ""
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.ACTIVE_PROBLEM]

    def find_certificate_section(self, content, begin_marker, end_marker):
        begin_index = content.find(begin_marker)
        end_index_local = content.find(end_marker, begin_index) if begin_index != -1 else -1
        return begin_index, end_index_local

    def get_first_cert_from_bundle(self, ca_bundle_path):
        return_code, file_content, err = self.run_cmd("sudo cat {}".format(ca_bundle_path))
        if return_code != 0:
            self._failed_msg = "Unable to read Bundle certificate content {} having error: {}".format(ca_bundle_path,err)
            return ""

        # Using the helper function to find start and end indexes
        start_index, end_index = self.find_certificate_section(file_content, "-----BEGIN CERTIFICATE-----", "-----END CERTIFICATE-----")

        if start_index == -1 and end_index == -1:
            self._failed_msg = "No '-----BEGIN CERTIFICATE-----' and '-----END CERTIFICATE-----' found in CA bundle: {}".format(ca_bundle_path)
            return ""
        elif start_index == -1:
            self._failed_msg = "No '-----BEGIN CERTIFICATE-----' found in CA bundle: {}".format(ca_bundle_path)
            return ""
        elif end_index == -1:
            self._failed_msg = ("Incomplete certificate in CA bundle: {}. "
                                "No '-----END CERTIFICATE-----' found after '-----BEGIN CERTIFICATE-----'").format(ca_bundle_path)
            return ""
        # Returns full certificate including END line
        return file_content[start_index:end_index + len("-----END CERTIFICATE-----")]

    def get_ca_cert(self, root_ca_path):
        return_code, ca_cert, err = self.run_cmd("sudo cat {}".format(root_ca_path))
        if return_code != 0:
            self._failed_msg = "Unable to read root CA certificate content {} having error: {}".format(root_ca_path, err)
            return ""
        else:
            return ca_cert

    def is_validation_passed(self):
        ca_bundle_path = "/etc/pki/tls/certs/ca-bundle.crt"
        root_ca_path = "/etc/kubernetes/ssl/ca.pem"
        missing_paths = []
        for path in [ca_bundle_path, root_ca_path]:
            if not self.file_utils.is_file_exist(path):
                missing_paths.append(path)
        if missing_paths:
            self._failed_msg = "Certificate file(s) not found: {}".format(", ".join(missing_paths))
            return False
        first_cert_from_bundle = self.get_first_cert_from_bundle(ca_bundle_path)
        ca_cert = self.get_ca_cert(root_ca_path)
        if first_cert_from_bundle and ca_cert:
            if first_cert_from_bundle.strip() == ca_cert.strip():
                return True
            else:
                self._failed_msg = ("The First certificate in CA crt bundle -'{}' is not ROOT CA certificate -'{}'"
                                    .format(ca_bundle_path, root_ca_path))
                return False
        else:
            self._failed_msg = "One or both certificates could not be retrieved."
            return False


class VerifyAnchorCAPemAbsent(Validator):
    objective_hosts = {Deployment_type.NCS_OVER_BM: [Objectives.MANAGERS, Objectives.STORAGE]}
    def set_document(self):
        self._unique_operation_name = "verify_anchor_ca_pem_file_absent"
        self._title = "Verify anchor CA pem file is absent"
        self._failed_msg = ""
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]
        self._is_clean_cmd_info = True

    def is_validation_passed(self):
        filepath = ['/etc/pki/ca-trust/source/anchors/ca.pem','/etc/openssl/ca.pem']
        unwanted_files = []
        for item in filepath:
            if self.file_utils.is_file_exist(item):
                unwanted_files.append(item)
        if unwanted_files:
            self._failed_msg += "Following ca pem file present , but it should be absent\n{}".format("\n".join(unwanted_files))
            return False
        return True


class ValidateCAKeyPairCertificate(Validator):
    objective_hosts = [Objectives.MASTERS, Objectives.EDGES, Objectives.WORKERS]

    def set_document(self):
        self._unique_operation_name = "validate_ca_key_pair_certificate"
        self._title = "Verify if ca-key-pair secret is same as /etc/openssl/ca.pem "
        self._failed_msg = "ca-key-pair secret and/etc/openssl/ca.pem do not match"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]
        self._is_clean_cmd_info = True

    def is_validation_passed(self):
        filepath = "/etc/openssl/ca.pem"
        if not self.file_utils.is_file_exist(filepath):
            self._failed_msg = "Certificate /etc/openssl/ca.pem not found"
            return False
        ca_pem = self.get_output_from_run_cmd('sudo cat /etc/openssl/ca.pem').strip()
        get_ca_key_pair = '''sudo kubectl get secrets -n ncms ca-key-pair -o jsonpath="{.data['tls\\.crt']}" | base64 -d'''
        ca_key_pair = self.get_output_from_run_cmd(get_ca_key_pair).strip()
        if ca_key_pair == ca_pem:
            return True
        else:
            return False

class VerifyCertificateIssuerRefNotExist(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER]
    }
    def set_document(self):
        self._unique_operation_name = "verify_certificate_issuer_ref"
        self._title = "Verify Certificate Issuer Ref"
        self._failed_msg = "Below Certificates are having IssuerRef to ncms-ca-issuer ClusterIssuer which doesn't exist"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        clusterIssuer_cmd = "sudo kubectl get clusterissuers -o custom-columns=:.metadata.name --no-headers"
        clusterIssuer_list = self.get_output_from_run_cmd(clusterIssuer_cmd).splitlines()

        certificate_cmd = "sudo kubectl get certificate -A -o custom-columns=:.metadata.name,:.spec.issuerRef.name --no-headers"
        certificate_list = self.get_output_from_run_cmd(certificate_cmd).splitlines()

        certs_with_issuer_not_exist = []

        has_ncms_ca_issuer = any(issuer.lower() == 'ncms-ca-issuer' for issuer in clusterIssuer_list)

        for each_cert in certificate_list:
            try:
                cert, issuer_ref = each_cert.split()
            except ValueError:
                raise UnExpectedSystemOutput(cmd=certificate_cmd,
                                             ip=self.get_host_ip(),
                                             output=certificate_list,
                                             message="Certificate output is not in the expected format"
                                             )
            if not has_ncms_ca_issuer and issuer_ref.lower() == 'ncms-ca-issuer':
                certs_with_issuer_not_exist.append(cert)

        if len(certs_with_issuer_not_exist) > 0:
            self._failed_msg += "\n" + "\n".join(certs_with_issuer_not_exist)
            return False
        return True
