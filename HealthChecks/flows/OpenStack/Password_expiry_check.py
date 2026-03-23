from __future__ import absolute_import
from HealthCheckCommon.operations import *
from HealthCheckCommon.validator import Validator
from tools.Exceptions import *
from datetime import datetime, timedelta


class CheckPasswordExpiry(Validator):

    def get_objective_names(self):
        assert False

    def set_document(self):
        self._unique_operation_name = None
        self._title = "Verify if Password expires for {}".format(self.get_objective_names())
        self._failed_msg = "Password expires issue please change the 'age'."
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_nonexpired_in_two_week(self, account, date):
        if "never" in date:
            self._details += "Password of {} has not expired".format(account)
            return True
        date_expire = datetime.strptime(date[-12:], "%b %d, %Y")
        today_plus_14 = datetime.today() + timedelta(days=14)
        if date_expire > today_plus_14:
            self._details += "Password of {} has not expired".format(account)
            return True
        else:
            expiry_days = abs((date_expire - datetime.today()).days)
            if date_expire <= datetime.today():
                self._implication_tags.append(ImplicationTag.ACTIVE_PROBLEM)
                self._failed_msg += "\nPassword of {} has expired {} days ago.".format(account, expiry_days)
            else:
                self._implication_tags.append(ImplicationTag.RISK_EXPIRY_DATE_APPROACHING)
                self._failed_msg += "\nPassword of {} will expire in {} days.".format(account, expiry_days)
        return False

    def is_validation_passed(self):

        flg_valid = True
        for account in self.get_objective_names():
            cmd1 = "sudo chage -l {} | grep 'Password expires'".format(account)
            ret_code, out1, err1 = self.run_cmd(cmd1)
            if ret_code != 0:
                if 'does not exist' in err1 or 'does not exist' in out1:
                    continue
                else:
                    raise UnExpectedSystemOutput(self.get_host_ip(), cmd1, out1+err1)

            out1 = out1.strip()
            flg_valid = flg_valid and self.is_nonexpired_in_two_week(account, out1)

        return flg_valid


class CheckPasswordExpiryForOpenStack(CheckPasswordExpiry):
    objective_hosts = [Objectives.COMPUTES, Objectives.CONTROLLERS, Objectives.STORAGE]

    def get_objective_names(self):
        users = ["cbis-admin", "tripleo-admin"]
        if gs.get_version() < Version.V25:
            users.append('heat-admin')
        else:
            users.append('cbis-administrator')
        return users


    def set_document(self):
        CheckPasswordExpiry.set_document(self)
        self._unique_operation_name = "check_password_expiry_for_openstack"


class CheckPasswordExpiryForStack(CheckPasswordExpiry):
    objective_hosts = [Objectives.UC]

    def get_objective_names(self):
        return ["stack"]

    def set_document(self):
        CheckPasswordExpiry.set_document(self)
        self._unique_operation_name = "check_password_expiry_for_stack"



class CheckTenantPasswordExpiry(Validator):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "CheckTenantPasswordExpiry"
        self._title = "Verify Openstack Tenant Password Expiry"
        self._failed_msg = "Placeholder"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.RISK_EXPIRY_DATE_APPROACHING]


    def is_validation_passed(self):
        get_users_cmd = "source {}; openstack user list --format value -c ID -c Name".format(self.system_utils.get_overcloudrc_file_path())
        users_dict = self.get_dict_from_command_output(get_users_cmd, out_format='space')
        expired_users = 0
        users_about_to_expire = []
        for id, name in list(users_dict.items()):
            get_password_expiration = "source {}; openstack user show {} -f json | jq -r .password_expires_at".format(
                self.system_utils.get_overcloudrc_file_path(), id)
            password_expiration = self.get_output_from_run_cmd(get_password_expiration).strip()
            if password_expiration != "null":
                try:
                    datetime_obj = datetime.strptime(password_expiration, '%Y-%m-%dT%H:%M:%S.%f').date()
                except ValueError as e:
                    raise UnExpectedSystemOutput(self.get_host_ip(), "", "", message="Unexpected dateTime found: {}".format(str(e)))
                is_password_expired = self.is_passwordExpiring(datetime_obj)
                if is_password_expired:
                    expired_users = 1
                    users_about_to_expire.append(name)
        if expired_users == 1:
            self._failed_msg = "The following users are about to expire in the next 15 days or are already expired :\n username: {}".format(
                users_about_to_expire)
            return False
        return True


    def is_passwordExpiring(self, date_obj):
        today = datetime.now().date()
        date_15_days_from_now = today + timedelta(days=15)
        if date_obj < date_15_days_from_now:
            return True
        return False


class CheckCbisManagerNginxPodUserPasswordExpiry(Validator):
    objective_hosts = [Objectives.HYP]

    def set_document(self):
        self._unique_operation_name = "check_cbis_manager_nginx_pod_user_password_expiry"
        self._title = "Verify Cbis Manager Nginx Pod User Password Expiry"
        self._failed_msg = ""
        self._severity = Severity.WARNING
        self._is_clean_cmd_info = True
        self._implication_tags = [ImplicationTag.RISK_EXPIRY_DATE_APPROACHING]

    def is_validation_passed(self):
        flg_valid = True

        get_users_cmd = "sudo podman exec cbis-manager_nginx sh -c \"grep ':x:1[0-9][0-9][0-9]:' /etc/passwd | grep -o '^[^:]*'\""

        users = self.get_output_from_run_cmd(get_users_cmd, timeout=45, add_bash_timeout=True)
        users_list = users.splitlines()

        for username in users_list:
            username = username.rstrip('.')
            get_password_expiration = "sudo podman exec cbis-manager_nginx sh -c \"chage -l {0} | grep 'Password expires'\"".format(
                username)

            ret_code, password_expiry_details, err = self.run_cmd(get_password_expiration, timeout=45, add_bash_timeout=True)

            if ret_code != 0:
                if 'does not exist' in err or 'does not exist' in password_expiry_details:
                    continue
                else:
                    raise UnExpectedSystemOutput(self.get_host_ip(), get_password_expiration, password_expiry_details + err)

            password_expiry_details = password_expiry_details.strip()
            user_is_valid = self.is_nonexpired_in_two_week(username, password_expiry_details)
            if not user_is_valid:
                flg_valid = False

        return flg_valid

    def is_nonexpired_in_two_week(self, account, date):
        if "never" in date:
            return True

        date_expire = datetime.strptime(date[-12:], "%b %d, %Y")
        today_plus_14 = datetime.today() + timedelta(days=14)

        if date_expire > today_plus_14:
            return True
        else:
            expiry_days = abs((date_expire - datetime.today()).days)
            if date_expire <= datetime.today():
                if ImplicationTag.ACTIVE_PROBLEM not in self._implication_tags:
                    self._implication_tags.append(ImplicationTag.ACTIVE_PROBLEM)
                self._failed_msg += "\nPassword of user {0} has expired {1} days ago . Expiry Date was {2}.".format(account, expiry_days,date_expire)
            else:
                if ImplicationTag.RISK_EXPIRY_DATE_APPROACHING not in self._implication_tags:
                    self._implication_tags.append(ImplicationTag.RISK_EXPIRY_DATE_APPROACHING)
                self._failed_msg += "\nPassword of user {0} will expire in {1} days . Expiry Date is {2}.".format(account, expiry_days,date_expire)
        return False