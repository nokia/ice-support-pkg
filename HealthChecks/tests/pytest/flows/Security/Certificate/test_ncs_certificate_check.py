from tests.pytest.tools.versions_alignment import Mock

import pytest

from flows.Security.Certificate.ncs_certificate_check import ValidateRootCAPositionInCRTBundle, \
    ValidateCAKeyPairCertificate, VerifyCertificateIssuerRefNotExist
from flows.Security.Certificate.ncs_allcertificate_expiry_dates import (VerifyHarborPodCertificate,
                                                                        VerifySecretCaCertMatch,
                                                                        VerifyZabbixCertOnManager,
                                                                        VerifyElasticsearchCertOnManager)
from tests.pytest.pytest_tools.operator.test_validation_base import ValidationTestBase, ValidationScenarioParams
from tools.global_enums import Version
from tools.global_enums import Objectives
from tests.pytest.pytest_tools.operator.test_operator import CmdOutput

cmd_to_get_bundle = "sudo cat /etc/pki/tls/certs/ca-bundle.crt"
out_bundle = """-----BEGIN CERTIFICATE-----
                RThFjzCCA3egAwIBAgIUG3uJjk7NLt/U3INyP1v3VZc5L7QwDQYJKoZIhvcNAQEL
                BQAwVzELMAkGA1UEBhMCRkkxEDAOBgNVBAgMB0ZpbmxhbmQxDjAMBgNVBAcMBUVz
                cG9vMQ4wDAYDVQQKDAVOb2tpYTEWMBQGA1UEAwwNZmk4NDVhLWZpODQ1YTAeFw0y
                NTAyMjcyMjU3MTZaFw0yODAyMjcyMjU3MTZaMFcxCzAJBgNVBAYTAkZJMRAwDgYD
                VQQIDAdGaW5sYW5kMQ4wDAYDVQQHDAVFc3BvbzEOMAwGA1UECgwFTm9raWExFjAU
                BgNVBAMMDWZpODQ1YS1maTg0NWEwggIiMA0GCSqGSIb3DQEBAQUAA4ICDwAwggIK
                AoICAQDm5kml1LcGkErONM9vEMTLasDUDPhMyYAMEqfQ4JQwV8dJ0ZaApJJkzaSK
                KPyFDiXXpz40oRdNzj5U1s91/dNPRtC3cGpmiixVUgTpxgL7A+QXCuxbS/TYnojx
                gbE2M5kUccAC9HAfkjatlbUjuPl9Pv453IFo/XRee4RpXuwfAk2gio8uHsGd8LWF
                0GQUhcuZqXS7PrRMOYSYdzETLOow45sFlHcFsXEl2H/atxFmJlODvn3h4USqs1Fc
                iTisBYacJ8gFrNVTaeFdcP/lTyNoyaosWmLj/45bdqx+7M6Y59rzUJHgIDJsT8CL
                RtuwNc4jjt1PiIXX74zzEJCZcF1/buN4vlJKo+XbPxX+qt26hHbR9rSLu01zr0uR
                DBgWBHoTKEyWijmHMxUF2xenrYJjOaL6icEzJ9qsQ+vuT1JlK6pKim4MLw/cOgQy
                wK4lBSFFRhwShFlNn20k1uXsP3qVBCqoJdS+JKsGoXqgDYBtKmAOVVrHK8KI7+ix
                G2I94Q9rbjDz7hdx6tFxwUawBapqfeAeY7iBvzakWDMW4jHz5MFVhiZNG0KeVraT
                Zt7XyKz3G+vBYHV9xLz0KKVICnQuMiyb/bPEWoumIA3nyBiH7wq6k3URIbWK1Bli
                EPhAaKNK3goc4EB5ImUkbV76NJKzueTkE2Xwdk7x831vZRA8ZQIDAQABo1MwUTAd
                BgNVHQ4EFgQU7yhAzUrHU7lsF5QZ5gvfHyIiUgUwHwYDVR0jBBgwFoAU7yhAzUrH
                U7lsF5QZ5gvfHyIiUgUwDwYDVR0TAQH/BAUwAwEB/zANBgkqhkiG9w0BAQsFAAOC
                AgEAc3NywAiqQ16x6kg7/V5qIjr7QHlG6F9V3E0Gg9aUVj2HZ+kjauqh9neuGGgY
                H1NbrYEQKHsKhsC7D+7RMFfTXZqZziZINcfz2p/SUSCfFrlx3JE23F/nskpo0ECI
                jRShBfQ4lwFoBjZO+tXyQGfe4OR82Ms35tTfQhebXbQ7c03PbGmrS5bXBDcUa4BX
                cdVjT3ZcSVY5jLm2eFzV7hlzHSU4H6GnhQe2V0ZcXFuvNDsxAzJuaqYl2laQfB6Q
                CQcgFUt5E1oM6yDq3OW9/vREwAdRBn4k6V050htnj875xjsa6C9OhcOCRjlhfxkM
                MNwwdkszPWHjjtnx9M5PoAB8w4jc+cRVU9OwCe7Kako16YiPmi+97Z8EhdQKAJbu
                4T7n0T4KdRkvN9M21y71B3wHwGICqR+MioEyKP13NKILNETpFBq2QUuSSGKUiAAN
                QLKUFr7DjtSDohf+xmYVKzxgyOL4l8RWG/nIDbgdgB/KB7A6z6yMbMzTLkRiy+BQ
                btGTUWEbh/SO6WeDi1Dmz1dgutlI6Oa3TaPp4K6ge0K/tvv2pHPbA2iTCWh5xSV6
                qjr2vbS7byMTm9iXdM6NKRRTMgPFe7pJDJeDFFbAqS6S51zSnN/NF9IkriJwvLdd
                jPDrEDE4cZfebFM3MFOe8haEwhhaRAYd/uhHm9tnJd7Vm6Q=
                -----END CERTIFICATE-----
                # ACCVRAIZ1
                -----BEGIN CERTIFICATE-----
                MIIH0zCCBbugAwIBAgIIXsO3pkN/pOAwDQYJKoZIhvcNAQEFBQAwQjESMBAGA1UE
                AwwJQUNDVlJBSVoxMRAwDgYDVQQLDAdQS0lBQ0NWMQ0wCwYDVQQKDARBQ0NWMQsw
                CQYDVQQGEwJFUzAeFw0xMTA1MDUwOTM3MzdaFw0zMDEyMzEwOTM3MzdaMEIxEjAQ
                BgNVBAMMCUFDQ1ZSQUlaMTEQMA4GA1UECwwHUEtJQUNDVjENMAsGA1UECgwEQUND
                VjELMAkGA1UEBhMCRVMwggIiMA0GCSqGSIb3DQEBAQUAA4ICDwAwggIKAoICAQCb
                qau/YUqXry+XZpp0X9DZlv3P4uRm7x8fRzPCRKPfmt4ftVTdFXxpNRFvu8gMjmoY
                HtiP2Ra8EEg2XPBjs5BaXCQ316PWywlxufEBcoSwfdtNgM3802/J+Nq2DoLSRYWo
                G2ioPej0RGy9ocLLA76MPhMAhN9KSMDjIgro6TenGEyxCQ0jVn8ETdkXhBilyNpA
                lHPrzg5XPAOBOp0KoVdDaaxXbXmQeOW1tDvYvEyNKKGno6e6Ak4l0Squ7a4DIrhr
                IA8wKFSVf+DuzgpmndFALW4ir50awQUZ0m/A8p/4e7MCQvtQqR0tkw8jq8bBD5L/
                0KIV9VMJcRz/RROE5iZe+OCIHAr8Fraocwa48GOEAqDGWuzndN9wrqODJerWx5eH
                k6fGioozl2A3ED6XPm4pFdahD9GILBKfb6qkxkLrQaLjlUPTAYVtjrs78yM2x/47
                4KElB0iryYl0/wiPgL/AlmXz7uxLaL2diMMxs0Dx6M/2OLuc5NF/1OVYm3z61PMO
                m3WR5LpSLhl+0fXNWhn8ugb2+1KoS5kE3fj5tItQo05iifCHJPqDQsGH+tUtKSpa
                cXpkatcnYGMN285J9Y0fkIkyF/hzQ7jSWpOGYdbhdQrqeWZ2iE9x6wQl1gpaepPl
                uUsXQA+xtrn13k/c4LOsOxFwYIRKQ26ZIMApcQrAZQIDAQABo4ICyzCCAscwfQYI
                KwYBBQUHAQEEcTBvMEwGCCsGAQUFBzAChkBodHRwOi8vd3d3LmFjY3YuZXMvZmls
                ZWFkbWluL0FyY2hpdm9zL2NlcnRpZmljYWRvcy9yYWl6YWNjdjEuY3J0MB8GCCsG
                AQUFBzABhhNodHRwOi8vb2NzcC5hY2N2LmVzMB0GA1UdDgQWBBTSh7Tj3zcnk1X2
                VuqB5TbMjB4/vTAPBgNVHRMBAf8EBTADAQH/MB8GA1UdIwQYMBaAFNKHtOPfNyeT
                VfZW6oHlNsyMHj+9MIIBcwYDVR0gBIIBajCCAWYwggFiBgRVHSAAMIIBWDCCASIG
                CCsGAQUFBwICMIIBFB6CARAAQQB1AHQAbwByAGkAZABhAGQAIABkAGUAIABDAGUA
                cgB0AGkAZgBpAGMAYQBjAGkA8wBuACAAUgBhAO0AegAgAGQAZQAgAGwAYQAgAEEA
                QwBDAFYAIAAoAEEAZwBlAG4AYwBpAGEAIABkAGUAIABUAGUAYwBuAG8AbABvAGcA
                7QBhACAAeQAgAEMAZQByAHQAaQBmAGkAYwBhAGMAaQDzAG4AIABFAGwAZQBjAHQA
                cgDzAG4AaQBjAGEALAAgAEMASQBGACAAUQA0ADYAMAAxADEANQA2AEUAKQAuACAA
                QwBQAFMAIABlAG4AIABoAHQAdABwADoALwAvAHcAdwB3AC4AYQBjAGMAdgAuAGUA
                czAwBggrBgEFBQcCARYkaHR0cDovL3d3dy5hY2N2LmVzL2xlZ2lzbGFjaW9uX2Mu
                aHRtMFUGA1UdHwROMEwwSqBIoEaGRGh0dHA6Ly93d3cuYWNjdi5lcy9maWxlYWRt
                aW4vQXJjaGl2b3MvY2VydGlmaWNhZG9zL3JhaXphY2N2MV9kZXIuY3JsMA4GA1Ud
                DwEB/wQEAwIBBjAXBgNVHREEEDAOgQxhY2N2QGFjY3YuZXMwDQYJKoZIhvcNAQEF
                BQADggIBAJcxAp/n/UNnSEQU5CmH7UwoZtCPNdpNYbdKl02125DgBS4OxnnQ8pdp
                D70ER9m+27Up2pvZrqmZ1dM8MJP1jaGo/AaNRPTKFpV8M9xii6g3+CfYCS0b78gU
                JyCpZET/LtZ1qmxNYEAZSUNUY9rizLpm5U9EelvZaoErQNV/+QEnWCzI7UiRfD+m
                AM/EKXMRNt6GGT6d7hmKG9Ww7Y49nCrADdg9ZuM8Db3VlFzi4qc1GwQA9j9ajepD
                vV+JHanBsMyZ4k0ACtrJJ1vnE5Bc5PUzolVt3OAJTS+xJlsndQAJxGJ3KQhfnlms
                tn6tn1QwIgPBHnFk/vk4CpYY3QIUrCPLBhwepH2NDd4nQeit2hW3sCPdK6jT2iWH
                7ehVRE2I9DZ+hJp4rPcOVkkO1jMl1oRQQmwgEh0q1b688nCBpHBgvgW1m54ERL5h
                I6zppSSMEYCUWqKiuUnSwdzRp+0xESyeGabu4VXhwOrPDYTkF7eifKXeVSUG7szA
                h1xA2syVP1XgNce4hL60Xc16gwFy7ofmXx2utYXGJt/mwZrpHgJHnyqobalbz+xF
                d3+YJ5oyXSrjhO7FmGYvliAd3djDJ9ew+f7Zfc3Qn48LFFhRny+Lwzgt3uiP1o2H
                pPVWQxaZLPSkVrQ0uGE3ycJYgBugl6H8WY3pEfbRD0tVNEYqi4Y7
                -----END CERTIFICATE-----"""

out_of_first_cert_in_bundle = """-----BEGIN CERTIFICATE-----
                RThFjzCCA3egAwIBAgIUG3uJjk7NLt/U3INyP1v3VZc5L7QwDQYJKoZIhvcNAQEL
                BQAwVzELMAkGA1UEBhMCRkkxEDAOBgNVBAgMB0ZpbmxhbmQxDjAMBgNVBAcMBUVz
                cG9vMQ4wDAYDVQQKDAVOb2tpYTEWMBQGA1UEAwwNZmk4NDVhLWZpODQ1YTAeFw0y
                NTAyMjcyMjU3MTZaFw0yODAyMjcyMjU3MTZaMFcxCzAJBgNVBAYTAkZJMRAwDgYD
                VQQIDAdGaW5sYW5kMQ4wDAYDVQQHDAVFc3BvbzEOMAwGA1UECgwFTm9raWExFjAU
                BgNVBAMMDWZpODQ1YS1maTg0NWEwggIiMA0GCSqGSIb3DQEBAQUAA4ICDwAwggIK
                AoICAQDm5kml1LcGkErONM9vEMTLasDUDPhMyYAMEqfQ4JQwV8dJ0ZaApJJkzaSK
                KPyFDiXXpz40oRdNzj5U1s91/dNPRtC3cGpmiixVUgTpxgL7A+QXCuxbS/TYnojx
                gbE2M5kUccAC9HAfkjatlbUjuPl9Pv453IFo/XRee4RpXuwfAk2gio8uHsGd8LWF
                0GQUhcuZqXS7PrRMOYSYdzETLOow45sFlHcFsXEl2H/atxFmJlODvn3h4USqs1Fc
                iTisBYacJ8gFrNVTaeFdcP/lTyNoyaosWmLj/45bdqx+7M6Y59rzUJHgIDJsT8CL
                RtuwNc4jjt1PiIXX74zzEJCZcF1/buN4vlJKo+XbPxX+qt26hHbR9rSLu01zr0uR
                DBgWBHoTKEyWijmHMxUF2xenrYJjOaL6icEzJ9qsQ+vuT1JlK6pKim4MLw/cOgQy
                wK4lBSFFRhwShFlNn20k1uXsP3qVBCqoJdS+JKsGoXqgDYBtKmAOVVrHK8KI7+ix
                G2I94Q9rbjDz7hdx6tFxwUawBapqfeAeY7iBvzakWDMW4jHz5MFVhiZNG0KeVraT
                Zt7XyKz3G+vBYHV9xLz0KKVICnQuMiyb/bPEWoumIA3nyBiH7wq6k3URIbWK1Bli
                EPhAaKNK3goc4EB5ImUkbV76NJKzueTkE2Xwdk7x831vZRA8ZQIDAQABo1MwUTAd
                BgNVHQ4EFgQU7yhAzUrHU7lsF5QZ5gvfHyIiUgUwHwYDVR0jBBgwFoAU7yhAzUrH
                U7lsF5QZ5gvfHyIiUgUwDwYDVR0TAQH/BAUwAwEB/zANBgkqhkiG9w0BAQsFAAOC
                AgEAc3NywAiqQ16x6kg7/V5qIjr7QHlG6F9V3E0Gg9aUVj2HZ+kjauqh9neuGGgY
                H1NbrYEQKHsKhsC7D+7RMFfTXZqZziZINcfz2p/SUSCfFrlx3JE23F/nskpo0ECI
                jRShBfQ4lwFoBjZO+tXyQGfe4OR82Ms35tTfQhebXbQ7c03PbGmrS5bXBDcUa4BX
                cdVjT3ZcSVY5jLm2eFzV7hlzHSU4H6GnhQe2V0ZcXFuvNDsxAzJuaqYl2laQfB6Q
                CQcgFUt5E1oM6yDq3OW9/vREwAdRBn4k6V050htnj875xjsa6C9OhcOCRjlhfxkM
                MNwwdkszPWHjjtnx9M5PoAB8w4jc+cRVU9OwCe7Kako16YiPmi+97Z8EhdQKAJbu
                4T7n0T4KdRkvN9M21y71B3wHwGICqR+MioEyKP13NKILNETpFBq2QUuSSGKUiAAN
                QLKUFr7DjtSDohf+xmYVKzxgyOL4l8RWG/nIDbgdgB/KB7A6z6yMbMzTLkRiy+BQ
                btGTUWEbh/SO6WeDi1Dmz1dgutlI6Oa3TaPp4K6ge0K/tvv2pHPbA2iTCWh5xSV6
                qjr2vbS7byMTm9iXdM6NKRRTMgPFe7pJDJeDFFbAqS6S51zSnN/NF9IkriJwvLdd
                jPDrEDE4cZfebFM3MFOe8haEwhhaRAYd/uhHm9tnJd7Vm6Q=
                -----END CERTIFICATE-----"""
out_of_first_cert_in_bundle_fail = """-----BEGIN CERTIFICATE-----
                MIIH0zCCBbugAwIBAgIIXsO3pkN/pOAwDQYJKoZIhvcNAQEFBQAwQjESMBAGA1UE
                AwwJQUNDVlJBSVoxMRAwDgYDVQQLDAdQS0lBQ0NWMQ0wCwYDVQQKDARBQ0NWMQsw
                CQYDVQQGEwJFUzAeFw0xMTA1MDUwOTM3MzdaFw0zMDEyMzEwOTM3MzdaMEIxEjAQ
                BgNVBAMMCUFDQ1ZSQUlaMTEQMA4GA1UECwwHUEtJQUNDVjENMAsGA1UECgwEQUND
                VjELMAkGA1UEBhMCRVMwggIiMA0GCSqGSIb3DQEBAQUAA4ICDwAwggIKAoICAQCb
                qau/YUqXry+XZpp0X9DZlv3P4uRm7x8fRzPCRKPfmt4ftVTdFXxpNRFvu8gMjmoY
                HtiP2Ra8EEg2XPBjs5BaXCQ316PWywlxufEBcoSwfdtNgM3802/J+Nq2DoLSRYWo
                G2ioPej0RGy9ocLLA76MPhMAhN9KSMDjIgro6TenGEyxCQ0jVn8ETdkXhBilyNpA
                lHPrzg5XPAOBOp0KoVdDaaxXbXmQeOW1tDvYvEyNKKGno6e6Ak4l0Squ7a4DIrhr
                IA8wKFSVf+DuzgpmndFALW4ir50awQUZ0m/A8p/4e7MCQvtQqR0tkw8jq8bBD5L/
                0KIV9VMJcRz/RROE5iZe+OCIHAr8Fraocwa48GOEAqDGWuzndN9wrqODJerWx5eH
                k6fGioozl2A3ED6XPm4pFdahD9GILBKfb6qkxkLrQaLjlUPTAYVtjrs78yM2x/47
                4KElB0iryYl0/wiPgL/AlmXz7uxLaL2diMMxs0Dx6M/2OLuc5NF/1OVYm3z61PMO
                m3WR5LpSLhl+0fXNWhn8ugb2+1KoS5kE3fj5tItQo05iifCHJPqDQsGH+tUtKSpa
                cXpkatcnYGMN285J9Y0fkIkyF/hzQ7jSWpOGYdbhdQrqeWZ2iE9x6wQl1gpaepPl
                uUsXQA+xtrn13k/c4LOsOxFwYIRKQ26ZIMApcQrAZQIDAQABo4ICyzCCAscwfQYI
                KwYBBQUHAQEEcTBvMEwGCCsGAQUFBzAChkBodHRwOi8vd3d3LmFjY3YuZXMvZmls
                ZWFkbWluL0FyY2hpdm9zL2NlcnRpZmljYWRvcy9yYWl6YWNjdjEuY3J0MB8GCCsG
                AQUFBzABhhNodHRwOi8vb2NzcC5hY2N2LmVzMB0GA1UdDgQWBBTSh7Tj3zcnk1X2
                VuqB5TbMjB4/vTAPBgNVHRMBAf8EBTADAQH/MB8GA1UdIwQYMBaAFNKHtOPfNyeT
                VfZW6oHlNsyMHj+9MIIBcwYDVR0gBIIBajCCAWYwggFiBgRVHSAAMIIBWDCCASIG
                CCsGAQUFBwICMIIBFB6CARAAQQB1AHQAbwByAGkAZABhAGQAIABkAGUAIABDAGUA
                cgB0AGkAZgBpAGMAYQBjAGkA8wBuACAAUgBhAO0AegAgAGQAZQAgAGwAYQAgAEEA
                QwBDAFYAIAAoAEEAZwBlAG4AYwBpAGEAIABkAGUAIABUAGUAYwBuAG8AbABvAGcA
                7QBhACAAeQAgAEMAZQByAHQAaQBmAGkAYwBhAGMAaQDzAG4AIABFAGwAZQBjAHQA
                cgDzAG4AaQBjAGEALAAgAEMASQBGACAAUQA0ADYAMAAxADEANQA2AEUAKQAuACAA
                QwBQAFMAIABlAG4AIABoAHQAdABwADoALwAvAHcAdwB3AC4AYQBjAGMAdgAuAGUA
                czAwBggrBgEFBQcCARYkaHR0cDovL3d3dy5hY2N2LmVzL2xlZ2lzbGFjaW9uX2Mu
                aHRtMFUGA1UdHwROMEwwSqBIoEaGRGh0dHA6Ly93d3cuYWNjdi5lcy9maWxlYWRt
                aW4vQXJjaGl2b3MvY2VydGlmaWNhZG9zL3JhaXphY2N2MV9kZXIuY3JsMA4GA1Ud
                DwEB/wQEAwIBBjAXBgNVHREEEDAOgQxhY2N2QGFjY3YuZXMwDQYJKoZIhvcNAQEF
                BQADggIBAJcxAp/n/UNnSEQU5CmH7UwoZtCPNdpNYbdKl02125DgBS4OxnnQ8pdp
                D70ER9m+27Up2pvZrqmZ1dM8MJP1jaGo/AaNRPTKFpV8M9xii6g3+CfYCS0b78gU
                JyCpZET/LtZ1qmxNYEAZSUNUY9rizLpm5U9EelvZaoErQNV/+QEnWCzI7UiRfD+m
                AM/EKXMRNt6GGT6d7hmKG9Ww7Y49nCrADdg9ZuM8Db3VlFzi4qc1GwQA9j9ajepD
                vV+JHanBsMyZ4k0ACtrJJ1vnE5Bc5PUzolVt3OAJTS+xJlsndQAJxGJ3KQhfnlms
                tn6tn1QwIgPBHnFk/vk4CpYY3QIUrCPLBhwepH2NDd4nQeit2hW3sCPdK6jT2iWH
                7ehVRE2I9DZ+hJp4rPcOVkkO1jMl1oRQQmwgEh0q1b688nCBpHBgvgW1m54ERL5h
                I6zppSSMEYCUWqKiuUnSwdzRp+0xESyeGabu4VXhwOrPDYTkF7eifKXeVSUG7szA
                h1xA2syVP1XgNce4hL60Xc16gwFy7ofmXx2utYXGJt/mwZrpHgJHnyqobalbz+xF
                d3+YJ5oyXSrjhO7FmGYvliAd3djDJ9ew+f7Zfc3Qn48LFFhRny+Lwzgt3uiP1o2H
                pPVWQxaZLPSkVrQ0uGE3ycJYgBugl6H8WY3pEfbRD0tVNEYqi4Y7
                    -----END CERTIFICATE-----"""

cmd_to_get_ca_cert = "sudo cat /etc/kubernetes/ssl/ca.pem"
out_ca_cert = """-----BEGIN CERTIFICATE-----
                RThFjzCCA3egAwIBAgIUG3uJjk7NLt/U3INyP1v3VZc5L7QwDQYJKoZIhvcNAQEL
                BQAwVzELMAkGA1UEBhMCRkkxEDAOBgNVBAgMB0ZpbmxhbmQxDjAMBgNVBAcMBUVz
                cG9vMQ4wDAYDVQQKDAVOb2tpYTEWMBQGA1UEAwwNZmk4NDVhLWZpODQ1YTAeFw0y
                NTAyMjcyMjU3MTZaFw0yODAyMjcyMjU3MTZaMFcxCzAJBgNVBAYTAkZJMRAwDgYD
                VQQIDAdGaW5sYW5kMQ4wDAYDVQQHDAVFc3BvbzEOMAwGA1UECgwFTm9raWExFjAU
                BgNVBAMMDWZpODQ1YS1maTg0NWEwggIiMA0GCSqGSIb3DQEBAQUAA4ICDwAwggIK
                AoICAQDm5kml1LcGkErONM9vEMTLasDUDPhMyYAMEqfQ4JQwV8dJ0ZaApJJkzaSK
                KPyFDiXXpz40oRdNzj5U1s91/dNPRtC3cGpmiixVUgTpxgL7A+QXCuxbS/TYnojx
                gbE2M5kUccAC9HAfkjatlbUjuPl9Pv453IFo/XRee4RpXuwfAk2gio8uHsGd8LWF
                0GQUhcuZqXS7PrRMOYSYdzETLOow45sFlHcFsXEl2H/atxFmJlODvn3h4USqs1Fc
                iTisBYacJ8gFrNVTaeFdcP/lTyNoyaosWmLj/45bdqx+7M6Y59rzUJHgIDJsT8CL
                RtuwNc4jjt1PiIXX74zzEJCZcF1/buN4vlJKo+XbPxX+qt26hHbR9rSLu01zr0uR
                DBgWBHoTKEyWijmHMxUF2xenrYJjOaL6icEzJ9qsQ+vuT1JlK6pKim4MLw/cOgQy
                wK4lBSFFRhwShFlNn20k1uXsP3qVBCqoJdS+JKsGoXqgDYBtKmAOVVrHK8KI7+ix
                G2I94Q9rbjDz7hdx6tFxwUawBapqfeAeY7iBvzakWDMW4jHz5MFVhiZNG0KeVraT
                Zt7XyKz3G+vBYHV9xLz0KKVICnQuMiyb/bPEWoumIA3nyBiH7wq6k3URIbWK1Bli
                EPhAaKNK3goc4EB5ImUkbV76NJKzueTkE2Xwdk7x831vZRA8ZQIDAQABo1MwUTAd
                BgNVHQ4EFgQU7yhAzUrHU7lsF5QZ5gvfHyIiUgUwHwYDVR0jBBgwFoAU7yhAzUrH
                U7lsF5QZ5gvfHyIiUgUwDwYDVR0TAQH/BAUwAwEB/zANBgkqhkiG9w0BAQsFAAOC
                AgEAc3NywAiqQ16x6kg7/V5qIjr7QHlG6F9V3E0Gg9aUVj2HZ+kjauqh9neuGGgY
                H1NbrYEQKHsKhsC7D+7RMFfTXZqZziZINcfz2p/SUSCfFrlx3JE23F/nskpo0ECI
                jRShBfQ4lwFoBjZO+tXyQGfe4OR82Ms35tTfQhebXbQ7c03PbGmrS5bXBDcUa4BX
                cdVjT3ZcSVY5jLm2eFzV7hlzHSU4H6GnhQe2V0ZcXFuvNDsxAzJuaqYl2laQfB6Q
                CQcgFUt5E1oM6yDq3OW9/vREwAdRBn4k6V050htnj875xjsa6C9OhcOCRjlhfxkM
                MNwwdkszPWHjjtnx9M5PoAB8w4jc+cRVU9OwCe7Kako16YiPmi+97Z8EhdQKAJbu
                4T7n0T4KdRkvN9M21y71B3wHwGICqR+MioEyKP13NKILNETpFBq2QUuSSGKUiAAN
                QLKUFr7DjtSDohf+xmYVKzxgyOL4l8RWG/nIDbgdgB/KB7A6z6yMbMzTLkRiy+BQ
                btGTUWEbh/SO6WeDi1Dmz1dgutlI6Oa3TaPp4K6ge0K/tvv2pHPbA2iTCWh5xSV6
                qjr2vbS7byMTm9iXdM6NKRRTMgPFe7pJDJeDFFbAqS6S51zSnN/NF9IkriJwvLdd
                jPDrEDE4cZfebFM3MFOe8haEwhhaRAYd/uhHm9tnJd7Vm6Q=
                -----END CERTIFICATE-----"""


class TestValidateRootCAPositionInCRTBundle(ValidationTestBase):
    tested_type = ValidateRootCAPositionInCRTBundle

    scenario_passed = [

        ValidationScenarioParams(scenario_title="check content of ca bundle and match first cert to be CA certificate",
                                 cmd_input_output_dict={cmd_to_get_bundle: CmdOutput(out_bundle),
                                                        cmd_to_get_ca_cert: CmdOutput(out_ca_cert)
                                                        },
                                 additional_parameters_dict={'file_exist': True})


    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="file not found",
                                 additional_parameters_dict={'file_exist': False}),

        ValidationScenarioParams(scenario_title="check content of ca bundle and match first cert NOT be CA certificate",
                                 cmd_input_output_dict={cmd_to_get_bundle: CmdOutput(out_bundle),
                                                        cmd_to_get_ca_cert: CmdOutput(out_ca_cert)
                                                        },
                                 additional_parameters_dict={'file_exist': False}),

        ValidationScenarioParams(scenario_title="File is empty",
                                 cmd_input_output_dict={cmd_to_get_bundle: CmdOutput(""),
                                                        cmd_to_get_ca_cert: CmdOutput("")
                                                        },
                                 additional_parameters_dict={'file_exist': True}),
    ]

    def _init_mocks(self, tested_object):
        tested_object.file_utils.is_file_exist = Mock()
        tested_object.file_utils.is_file_exist.return_value = self.additional_parameters_dict['file_exist']

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

class TestVerifyHarborPodCertificate(ValidationTestBase):
    tested_type = VerifyHarborPodCertificate

    harbor_core_pod_name = "sudo kubectl get pods -n ncms | grep harbor-harbor-core"
    harbor_core_pod_name_out = "harbor-harbor-core-859c9f958b-xf9sb"
    validate_secret_entry = ("sudo kubectl exec -it {} -n ncms -- /usr/bin/cat /etc/harbor/ssl/core/tls.crt | "
                             "openssl x509 -enddate -noout | grep 'notAfter'").format(
        harbor_core_pod_name_out)
    validate_secret_out = "notAfter=Jun 18 21:46:49 2028 GMT"
    scenario_passed = [
        ValidationScenarioParams(scenario_title="Harbor Pods are using the latest available certificate",
                                 cmd_input_output_dict={harbor_core_pod_name: CmdOutput(out=harbor_core_pod_name_out),
                                                        validate_secret_entry: CmdOutput(out=validate_secret_out)},
                                 tested_object_mock_dict={
                                     "get_certificate_expiry_date": Mock(return_value="Apr 16 00:03:46 2027 GMT")}
                                 )]
    scenario_failed = [
        ValidationScenarioParams(scenario_title="Harbor Pods did not utilize the latest available certificate",
                                 cmd_input_output_dict={harbor_core_pod_name: CmdOutput(out=harbor_core_pod_name_out),
                                                        validate_secret_entry: CmdOutput(out=validate_secret_out)},
                                 tested_object_mock_dict={
                                     "get_certificate_expiry_date": Mock(return_value="Apr 16 00:03:46 2029 GMT")}
                                 )]
    scenario_unexpected_system_output = [
        ValidationScenarioParams(scenario_title="unexpected output returned",
                                 cmd_input_output_dict={harbor_core_pod_name: CmdOutput(out=harbor_core_pod_name_out),
                                                        validate_secret_entry: CmdOutput(out="")},
                                 tested_object_mock_dict={
                                     "get_certificate_expiry_date": Mock(return_value="Apr 16 00:03:46 2029 GMT")}
                                 )]
    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_unexpected_system_output(self, scenario_params, tested_object)

class TestVerifySecretCaCertMatch(ValidationTestBase):
    tested_type = VerifySecretCaCertMatch

    system_ca_cert_cmd = "sudo cat /etc/openssl/ca.pem"

    system_ca_cert = """-----BEGIN CERTIFICATE-----
        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
        Dvm5DLS3e1YlVs4og4nOUg5iXKWu
        -----END CERTIFICATE-----"""

    system_ca_cert_invalid = """-----BEGIN CERTIFICATE-----
        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
        Dvm5DLS3e1YlVs4og4nOUg5iXKWu
        -----END CERTIFICATE-----"""

    system_ca_cert_invalid_1 = ""

    k8s_ca_cert_cmd = 'sudo kubectl get secrets -n ncms ca-key-pair -o jsonpath="{.data[\'tls\\.crt\']}" | base64 -d'

    k8s_ca_cert = """-----BEGIN CERTIFICATE-----
        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
        Dvm5DLS3e1YlVs4og4nOUg5iXKWu
        -----END CERTIFICATE-----"""

    k8s_ca_cert_invalid = ""

    scenario_passed = [
        ValidationScenarioParams(scenario_title="CA Certificate Match Successful",
                                 cmd_input_output_dict={system_ca_cert_cmd: CmdOutput(out=system_ca_cert),
                                                        k8s_ca_cert_cmd: CmdOutput(out=k8s_ca_cert)},
                                 additional_parameters_dict={'file_exist': True}
                                 )]
    scenario_failed = [
        ValidationScenarioParams(scenario_title="CA Certificate Mismatch",
                                 cmd_input_output_dict={system_ca_cert_cmd: CmdOutput(out=system_ca_cert_invalid),
                                                        k8s_ca_cert_cmd: CmdOutput(out=k8s_ca_cert)},
                                 additional_parameters_dict={'file_exist': True}
                                 )]
    scenario_unexpected_system_output = [
        ValidationScenarioParams(scenario_title="System CA Certificate File Not Found",
                                 cmd_input_output_dict={system_ca_cert_cmd: CmdOutput(out=system_ca_cert),
                                                        k8s_ca_cert_cmd: CmdOutput(out=k8s_ca_cert_cmd)},
                                 additional_parameters_dict={'file_exist': False}
                                 ),
        ValidationScenarioParams(scenario_title="System CA Certificate is empty",
                                 cmd_input_output_dict={system_ca_cert_cmd: CmdOutput(out=system_ca_cert_invalid_1),
                                                        k8s_ca_cert_cmd: CmdOutput(out=k8s_ca_cert_cmd)},
                                 additional_parameters_dict={'file_exist': True}
                                 ),
        ValidationScenarioParams(scenario_title="Kubernetes CA Secret is empty",
                                 cmd_input_output_dict={system_ca_cert_cmd: CmdOutput(out=system_ca_cert),
                                                        k8s_ca_cert_cmd: CmdOutput(out=k8s_ca_cert_invalid)},
                                 additional_parameters_dict={'file_exist': True}
                                 )
    ]

    def _init_mocks(self, tested_object):
        tested_object.file_utils.is_file_exist = Mock()
        tested_object.file_utils.is_file_exist.return_value = self.additional_parameters_dict['file_exist']

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_unexpected_system_output(self, scenario_params, tested_object)

class TestValidateCAKeyPairCertificate(ValidationTestBase):
    tested_type = ValidateCAKeyPairCertificate

    find_ca_pem_command = "sudo find /etc/openssl/ca.pem"
    ca_pem_file_path = "/etc/openssl/ca.pem"
    ca_pem_command = 'sudo cat /etc/openssl/ca.pem'
    ca_key_pair_command = '''sudo kubectl get secrets -n ncms ca-key-pair -o jsonpath="{.data['tls\\.crt']}" | base64 -d'''

    scenario_passed = [
        ValidationScenarioParams(
            "Certificate validation passed",
            cmd_input_output_dict={
                find_ca_pem_command: CmdOutput(out="path_found"),
                ca_pem_file_path: CmdOutput(out="valid_ca_pem_data"),
                ca_pem_command: CmdOutput(out="valid_ca_pem_data"),
                ca_key_pair_command: CmdOutput(out="valid_ca_pem_data"),
            },
            tested_object_mock_dict={
                "get_output_from_run_cmd": Mock(return_value="valid_ca_pem_data"),
                "file_utils.is_file_exist": Mock(return_value=True),
            }
        )
    ]

    scenario_failed = [
        ValidationScenarioParams(
            "Certificate validation failed - invalid CA PEM or key pair",
            cmd_input_output_dict={
                find_ca_pem_command: CmdOutput(out="path_found"),
                ca_pem_file_path: CmdOutput(out="invalid_ca_pem_data"),
                ca_pem_command: CmdOutput(out="invalid_ca_pem_data"),
                ca_key_pair_command: CmdOutput(out="different_ca_key_pair"),
            },
            tested_object_mock_dict={
                "get_output_from_run_cmd": Mock(side_effect=lambda
                    cmd: "invalid_ca_pem_data" if cmd == TestValidateCAKeyPairCertificate.ca_pem_command else "different_ca_key_pair"),
                "file_utils.is_file_exist": Mock(return_value=True),
            }
        )
    ]

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        self._init_validation_object(tested_object, scenario_params)
        assert tested_object.is_validation_passed() is False

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        self._init_validation_object(tested_object, scenario_params)
        assert tested_object.is_validation_passed() is True

class TestVerifyCertificateIssuerRefNotExist(ValidationTestBase):
    tested_type = VerifyCertificateIssuerRefNotExist

    clusterIssuer_cmd = "sudo kubectl get clusterissuers -o custom-columns=:.metadata.name --no-headers"
    certificate_cmd = "sudo kubectl get certificate -A -o custom-columns=:.metadata.name,:.spec.issuerRef.name --no-headers"

    ncms_issuer = "ncms-ca-issuer"
    valid_certs = "tenant-webhook ncms-ca-issuer"

    missing_issuer = "cmpv2-issuer"
    invalid_certs = "tenant-webhook ncms-ca-issuer"

    cert_without_issuer_value = "tenant-webhook"

    scenario_passed = [
      ValidationScenarioParams(
        scenario_title="ncms-ca-issuer exists and certs are linked correctly",
        cmd_input_output_dict={
          clusterIssuer_cmd: CmdOutput(out=ncms_issuer),
          certificate_cmd: CmdOutput(out=valid_certs)
        }
      )
    ]

    scenario_failed = [
      ValidationScenarioParams(
        scenario_title="Certificates uses ncms-ca-issuer but issuer does not exist",
        cmd_input_output_dict={
          clusterIssuer_cmd: CmdOutput(out=missing_issuer),
          certificate_cmd: CmdOutput(out=invalid_certs)
        }
      )
    ]

    scenario_unexpected_system_output = [
      ValidationScenarioParams(
        scenario_title="Not able to get the certificate list",
        cmd_input_output_dict={
          clusterIssuer_cmd: CmdOutput(out=ncms_issuer),
          certificate_cmd: CmdOutput(out=cert_without_issuer_value)
        }
      )
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_unexpected_system_output(self, scenario_params, tested_object)


class TestVerifyZabbixCertOnManager(ValidationTestBase):

    tested_type = VerifyZabbixCertOnManager

    # Paths
    service_ca = "/var/lib/zabbix/enc/ca.crt.pem"
    service_server = "/var/lib/zabbix/enc/server.crt.pem"
    service_node = "/var/lib/zabbix/enc/node.crt.pem"

    ncs_ca = "/etc/pki/ca-trust/source/general-cert/ca.crt.pem"
    ncs_server = "/etc/pki/tls/private/general-cert/server.crt.pem"
    ncs_node = "/etc/pki/tls/private/general-cert/node.crt.pem"

    # cat commands
    service_ca_cmd = "sudo cat {}".format(service_ca)
    service_server_cmd = "sudo cat {}".format(service_server)
    service_node_cmd = "sudo cat {}".format(service_node)

    ncs_ca_cmd = "sudo cat {}".format(ncs_ca)
    ncs_server_cmd = "sudo cat {}".format(ncs_server)
    ncs_node_cmd = "sudo cat {}".format(ncs_node)

    # openssl commands
    openssl_service_ca_cmd = "sudo openssl x509 -enddate -noout -in {}".format(service_ca)
    openssl_service_server_cmd = "sudo openssl x509 -enddate -noout -in {}".format(service_server)
    openssl_service_node_cmd = "sudo openssl x509 -enddate -noout -in {}".format(service_node)

    openssl_ncs_ca_cmd = "sudo openssl x509 -enddate -noout -in {}".format(ncs_ca)
    openssl_ncs_server_cmd = "sudo openssl x509 -enddate -noout -in {}".format(ncs_server)
    openssl_ncs_node_cmd = "sudo openssl x509 -enddate -noout -in {}".format(ncs_node)

    valid_cert = "VALID_CERT"
    invalid_cert = "INVALID_CERT"

    valid_expiry = "notAfter=Jun 20 10:00:00 2029 GMT"
    expired_expiry = "notAfter=Jun 20 10:00:00 2020 GMT"

    scenario_passed = [
        ValidationScenarioParams(
            scenario_title="All Zabbix Certificates Valid and Matching",
            cmd_input_output_dict={
                service_ca_cmd: CmdOutput(out=valid_cert),
                service_server_cmd: CmdOutput(out=valid_cert),
                service_node_cmd: CmdOutput(out=valid_cert),
                ncs_ca_cmd: CmdOutput(out=valid_cert),
                ncs_server_cmd: CmdOutput(out=valid_cert),
                ncs_node_cmd: CmdOutput(out=valid_cert),

                openssl_service_ca_cmd: CmdOutput(out=valid_expiry),
                openssl_service_server_cmd: CmdOutput(out=valid_expiry),
                openssl_service_node_cmd: CmdOutput(out=valid_expiry),
                openssl_ncs_ca_cmd: CmdOutput(out=valid_expiry),
                openssl_ncs_server_cmd: CmdOutput(out=valid_expiry),
                openssl_ncs_node_cmd: CmdOutput(out=valid_expiry),
            },
            additional_parameters_dict={'file_exist': True}
        )
    ]

    scenario_failed = [
        ValidationScenarioParams(
            scenario_title="Server Certificate Mismatch",
            cmd_input_output_dict={
                service_ca_cmd: CmdOutput(out=valid_cert),
                service_server_cmd: CmdOutput(out=invalid_cert),  # mismatch
                service_node_cmd: CmdOutput(out=valid_cert),
                ncs_ca_cmd: CmdOutput(out=valid_cert),
                ncs_server_cmd: CmdOutput(out=valid_cert),
                ncs_node_cmd: CmdOutput(out=valid_cert),

                openssl_service_ca_cmd: CmdOutput(out=valid_expiry),
                openssl_service_server_cmd: CmdOutput(out=valid_expiry),
                openssl_service_node_cmd: CmdOutput(out=valid_expiry),
                openssl_ncs_ca_cmd: CmdOutput(out=valid_expiry),
                openssl_ncs_server_cmd: CmdOutput(out=valid_expiry),
                openssl_ncs_node_cmd: CmdOutput(out=valid_expiry),
            },
            additional_parameters_dict={'file_exist': True}
        ),
        ValidationScenarioParams(
            scenario_title="Certificate Expired",
            cmd_input_output_dict={
                service_ca_cmd: CmdOutput(out=valid_cert),
                service_server_cmd: CmdOutput(out=valid_cert),
                service_node_cmd: CmdOutput(out=valid_cert),
                ncs_ca_cmd: CmdOutput(out=valid_cert),
                ncs_server_cmd: CmdOutput(out=valid_cert),
                ncs_node_cmd: CmdOutput(out=valid_cert),

                openssl_service_ca_cmd: CmdOutput(out=expired_expiry),  # expired
                openssl_service_server_cmd: CmdOutput(out=valid_expiry),
                openssl_service_node_cmd: CmdOutput(out=valid_expiry),
                openssl_ncs_ca_cmd: CmdOutput(out=valid_expiry),
                openssl_ncs_server_cmd: CmdOutput(out=valid_expiry),
                openssl_ncs_node_cmd: CmdOutput(out=valid_expiry),
            },
            additional_parameters_dict={'file_exist': True}
        )
    ]

    scenario_unexpected_system_output = [
        ValidationScenarioParams(
            scenario_title="Certificate File Missing",
            cmd_input_output_dict={},
            additional_parameters_dict={'file_exist': False}
        )
    ]

    def _init_mocks(self, tested_object):
        tested_object.file_utils.is_file_exist = Mock()
        tested_object.file_utils.is_file_exist.return_value = \
            self.additional_parameters_dict['file_exist']

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_unexpected_system_output(
            self, scenario_params, tested_object
        )


class TestVerifyElasticsearchCertOnManager(ValidationTestBase):

    tested_type = VerifyElasticsearchCertOnManager

    # Paths
    service_ca = "/etc/ssc/indexsearch/certs/ca.crt.pem"
    service_server = "/etc/ssc/indexsearch/certs/server.crt.pem"
    service_node = "/etc/ssc/indexsearch/certs/node.crt.pem"

    ncs_ca = "/etc/pki/ca-trust/source/general-cert/ca.crt.pem"
    ncs_server = "/etc/pki/tls/private/general-cert/server.crt.pem"
    ncs_node = "/etc/pki/tls/private/general-cert/node.crt.pem"

    # cat commands
    service_ca_cmd = "sudo cat {}".format(service_ca)
    service_server_cmd = "sudo cat {}".format(service_server)
    service_node_cmd = "sudo cat {}".format(service_node)

    ncs_ca_cmd = "sudo cat {}".format(ncs_ca)
    ncs_server_cmd = "sudo cat {}".format(ncs_server)
    ncs_node_cmd = "sudo cat {}".format(ncs_node)

    # openssl commands
    openssl_service_ca_cmd = "sudo openssl x509 -enddate -noout -in {}".format(service_ca)
    openssl_service_server_cmd = "sudo openssl x509 -enddate -noout -in {}".format(service_server)
    openssl_service_node_cmd = "sudo openssl x509 -enddate -noout -in {}".format(service_node)

    openssl_ncs_ca_cmd = "sudo openssl x509 -enddate -noout -in {}".format(ncs_ca)
    openssl_ncs_server_cmd = "sudo openssl x509 -enddate -noout -in {}".format(ncs_server)
    openssl_ncs_node_cmd = "sudo openssl x509 -enddate -noout -in {}".format(ncs_node)

    valid_cert = "VALID_CERT"
    invalid_cert = "INVALID_CERT"

    valid_expiry = "notAfter=Jun 20 10:00:00 2029 GMT"
    expired_expiry = "notAfter=Jun 20 10:00:00 2020 GMT"

    scenario_passed = [
        ValidationScenarioParams(
            scenario_title="All Elasticsearch Certificates Valid and Matching",
            cmd_input_output_dict={
                service_ca_cmd: CmdOutput(out=valid_cert),
                service_server_cmd: CmdOutput(out=valid_cert),
                service_node_cmd: CmdOutput(out=valid_cert),
                ncs_ca_cmd: CmdOutput(out=valid_cert),
                ncs_server_cmd: CmdOutput(out=valid_cert),
                ncs_node_cmd: CmdOutput(out=valid_cert),

                openssl_service_ca_cmd: CmdOutput(out=valid_expiry),
                openssl_service_server_cmd: CmdOutput(out=valid_expiry),
                openssl_service_node_cmd: CmdOutput(out=valid_expiry),
                openssl_ncs_ca_cmd: CmdOutput(out=valid_expiry),
                openssl_ncs_server_cmd: CmdOutput(out=valid_expiry),
                openssl_ncs_node_cmd: CmdOutput(out=valid_expiry),
            },
            additional_parameters_dict={'file_exist': True}
        )
    ]

    scenario_failed = [
        ValidationScenarioParams(
            scenario_title="Server Certificate Mismatch",
            cmd_input_output_dict={
                service_ca_cmd: CmdOutput(out=valid_cert),
                service_server_cmd: CmdOutput(out=invalid_cert),  # mismatch
                service_node_cmd: CmdOutput(out=valid_cert),
                ncs_ca_cmd: CmdOutput(out=valid_cert),
                ncs_server_cmd: CmdOutput(out=valid_cert),
                ncs_node_cmd: CmdOutput(out=valid_cert),

                openssl_service_ca_cmd: CmdOutput(out=valid_expiry),
                openssl_service_server_cmd: CmdOutput(out=valid_expiry),
                openssl_service_node_cmd: CmdOutput(out=valid_expiry),
                openssl_ncs_ca_cmd: CmdOutput(out=valid_expiry),
                openssl_ncs_server_cmd: CmdOutput(out=valid_expiry),
                openssl_ncs_node_cmd: CmdOutput(out=valid_expiry),
            },
            additional_parameters_dict={'file_exist': True}
        ),
        ValidationScenarioParams(
            scenario_title="Certificate Expired",
            cmd_input_output_dict={
                service_ca_cmd: CmdOutput(out=valid_cert),
                service_server_cmd: CmdOutput(out=valid_cert),
                service_node_cmd: CmdOutput(out=valid_cert),
                ncs_ca_cmd: CmdOutput(out=valid_cert),
                ncs_server_cmd: CmdOutput(out=valid_cert),
                ncs_node_cmd: CmdOutput(out=valid_cert),

                openssl_service_ca_cmd: CmdOutput(out=expired_expiry),  # expired
                openssl_service_server_cmd: CmdOutput(out=valid_expiry),
                openssl_service_node_cmd: CmdOutput(out=valid_expiry),
                openssl_ncs_ca_cmd: CmdOutput(out=valid_expiry),
                openssl_ncs_server_cmd: CmdOutput(out=valid_expiry),
                openssl_ncs_node_cmd: CmdOutput(out=valid_expiry),
            },
            additional_parameters_dict={'file_exist': True}
        )
    ]

    scenario_unexpected_system_output = [
        ValidationScenarioParams(
            scenario_title="Certificate File Missing",
            cmd_input_output_dict={},
            additional_parameters_dict={'file_exist': False}
        )
    ]

    def _init_mocks(self, tested_object):
        tested_object.file_utils.is_file_exist = Mock()
        tested_object.file_utils.is_file_exist.return_value = \
            self.additional_parameters_dict['file_exist']

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_unexpected_system_output(
            self, scenario_params, tested_object
        )

