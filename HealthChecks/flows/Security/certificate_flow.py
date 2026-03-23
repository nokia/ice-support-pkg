from __future__ import absolute_import
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
from flows.Security.Certificate.ncs_allcertificate_expiry_dates import *
from flows.Security.Certificate.cbis_allcertificate_expiry_dates import *
from flows.Security.Certificate.public_private_keys_certificate import *
from flows.Security.Certificate.ncs_certificate_check import *
from tools.global_enums import *
import tools.paths
import json


class certificate_flow(BaseValidationFlow):

    def _get_list_of_validator_class(self, version, deployment_type):

        check_list_class = [
            CertificateExpiryVerifyBareMetal,
            CertificateExpiryVerifyCNA,
            VerifyValidBundleCACert,
            CbisCertificateExpiryVerify,
            CheckCaPublicPrivateCertificateModulus,
            VerifyPrivateKeyWithCertificate,
            VerifyRootCA,
            VerifyRootCAandIstiofileContent,
            VerifyHarborPodCertificate,
            VerifySecretCaCertMatch,
            ValidateCAKeyPairCertificate,
            VerifyCertificateIssuerRefNotExist
        ]

        if version < Version.V23_10:
            check_list_class.append(CheckCaCHKCertificateModulus)
            check_list_class.append(CheckCaTrustedStoreCertificateModulus)

        if version >= Version.V22:
            check_list_class.append(CheckEphemeralWebhook)
        if version >= Version.V23_10:
            check_list_class.append(VerifyServiceAccountCertificate)
        if version <= Version.V23_10:
            check_list_class.append(ValidateRootCAPositionInCRTBundle)
            check_list_class.append(VerifyZabbixCertOnManager)
            check_list_class.append(VerifyElasticsearchCertOnManager)
        if version > Version.V23_10 and deployment_type == Deployment_type.NCS_OVER_BM and gs.is_ncs_central():
            check_list_class.append(VerifyAnchorCAPemAbsent)
        return check_list_class

    def command_name(self):
        return "certificate_validations"

    def deployment_type_list(self):
        return [Deployment_type.NCS_OVER_OPENSTACK, Deployment_type.NCS_OVER_BM, Deployment_type.NCS_OVER_VSPHERE, Deployment_type.CBIS]
