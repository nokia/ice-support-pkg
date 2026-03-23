from __future__ import absolute_import
from HealthCheckCommon.validator import InformatorValidator
from flows.Security.Certificate.allcertificate_expiry_dates import *

class CbisCertificateExpiryVerify(InformatorValidator, CertificateExpiryDates):
    objective_hosts = {Deployment_type.CBIS: [Objectives.HYP, Objectives.UC, Objectives.CONTROLLERS,Objectives.COMPUTES,Objectives.STORAGE]}

    def set_document(self):
        self._unique_operation_name = "verify_certificate_expiry_cbis"
        self._title = "Verify Certificate Expiry CBIS"
        self._failed_msg = "Please check the certificate dates and renew manually if no autorenewal option for them"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.RISK_EXPIRY_DATE_APPROACHING]
        self._system_info = ""
        self._is_pure_info = False
        self._title_of_info = "Verify Certificate Expiry CBIS"
        self._is_highlighted_info = True
        self._is_clean_cmd_info = True

    def is_validation_passed(self):
        cert_testing_dict = self.load_certificate_dictionary()
        return self._test_certificates(cert_testing_dict)

class VerifyValidBundleCACert(Validator):

    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "verify_valid_bundle_ca_cert_present"
        self._title = "Verify for valid bundle ca cert present"
        self._failed_msg = "Bundle CA cert not matching with CA cert"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]
        self._blocking_tags = []
        self._is_clean_cmd_info = True

    def is_validation_passed(self):
        #This validation is to validate the current CA cert cert id present in CABundle
        ca_cert_path = "/home/stack/ca.crt.pem"
        if not self.file_utils.is_file_exist(ca_cert_path):
            self._failed_msg = "Failed to find {}".format(ca_cert_path)
            return False
        bundle_ca_path = "/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem"

        if not self.file_utils.is_file_exist(bundle_ca_path):
            self._failed_msg = "Failed to find {}".format(bundle_ca_path)
            return False

        cmd = "sudo openssl x509 -in {} -noout -text |grep -i 'Serial Number' -A1".format(ca_cert_path)
        cmd_output = self.get_output_from_run_cmd(cmd).strip().split('\n')
        serial_no = cmd_output[0].strip().split(" ")
        if len(serial_no) > 3:
            cert_id = serial_no[2]
        else:
            cert_id = cmd_output[1].strip()
        bundle_cmd = "sudo openssl crl2pkcs7 -nocrl -certfile {path} \
        |openssl pkcs7 -print_certs -text -noout | grep -i '{cert_id}'".format(path=bundle_ca_path,cert_id=cert_id)
        return_code, out, err = self.run_cmd(bundle_cmd)
        bundle_cmd_output = out.strip()

        if bundle_cmd_output == cert_id:
            return True
        else:
            return False
