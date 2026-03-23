from __future__ import absolute_import
from flows.Cbis.user_config_validator.user_config_checks import *
from HealthCheckCommon.base_validation_flow import BaseValidationFlow
from tools.global_enums import *


class CBIS_user_config_validation_flow(BaseValidationFlow):

    def _get_list_of_validator_class(self, version, deployment_type):
        # if version in [Version.V19,Version.V19A]: those checks are general and should work on all Cbis versions
        check_list_class = [
                            IsDnsCorrect,
                            IsNtpCorrect,
                            IsTimeZoneCorrect,
                            IsUndercloudCidrCorrect,
                            IsHypervisorCidrCorrect,
                            IsGuestsMtuCorrect,
                            IsHostUnderlayMtuCorrect,
                            #IsConfiguredVlansCorrect, #comment out due to many false positive (and no impact)
                            IsConfiguredNetworkAddressCorrect
                            ]

        if version <= Version.V19:
            check_list_class.append(is_cloud_name_in_user_config_correct)

        #if version >= Version.V20:
        #    check_list_class.append(CheckWhetherHostGroupRootDeviceIsNull)

        if version < Version.V24:
            check_list_class.extend([IsBackupNfsMountpointCorrect,
                                     IsBackupMinuteCorrect,
                                     IsBackupHourCorrect,])


        # is_cloud_name_correct, IsTimeZoneCorrect,is_message_of_the_day_correct

        return check_list_class

    def command_name(self):
        return "test_user_config_parameters_runtime"

    def deployment_type_list(self):
        return [Deployment_type.CBIS]
