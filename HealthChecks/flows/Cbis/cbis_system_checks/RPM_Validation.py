from __future__ import absolute_import
from datetime import timedelta
from HealthCheckCommon.operations import *
from HealthCheckCommon.validator import Validator
from tools.python_utils import PythonUtils
from flows.Chain_of_events.operation_timing_info import Operation_timing_info
from tools.date_and_time_utils import DateAndTimeUtils

host = None


# todo Need more testing
class CheckRpmList(Validator):

    def get_expected_rpm_list(self, rpm_system_file):
        out = self.get_output_from_run_cmd('sudo cat {}'.format(rpm_system_file))
        data = PythonUtils.yaml_safe_load(out, file_path=rpm_system_file)
        rpm_list = list(data.keys())
        rpm_list = [item.replace(".(none)", "") for item in rpm_list]
        return rpm_list

    def get_installed_rpms_and_dates_dict(self):
        out = self.get_output_from_run_cmd(
            'sudo rpm -qa --qf "%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH},%{INSTALLTIME:date}\n"',
            timeout=90,
            add_bash_timeout=True)
        installed_rpms_and_dates_dict = {}
        data = out.split('\n')[1:-1]
        for line in data:
            if line != "":
                lines = line.split(",")
                key = lines[0]
                key = key.replace(".(none)", "")
                val = lines[1]
                installed_rpms_and_dates_dict[key] = val

        return installed_rpms_and_dates_dict

    def convert_installed_rpms_datetime_format(self, installed_rpms_datetime_dict):
        operation_timing = Operation_timing_info(self)
        for rpm, rpm_datetime in list(installed_rpms_datetime_dict.items()):
            installed_rpms_datetime_dict[rpm] = DateAndTimeUtils.convert_str_list_to_datetime([rpm_datetime], "%a %d %b %Y %H:%M:%S %p %Z")[0]
        return installed_rpms_datetime_dict

    def cal_threshold(self, installation_dates, post_install_datetime_list):
        'allow the rpm if its date before the last installation +delta_time'
        last_cbis_installation_date = max(
            installation_dates)  # we can't differentiate between image that was created last month
        # and rpm installation

        threshold = None
        if len(post_install_datetime_list) > 0:
            post_install_datetime_max = max(post_install_datetime_list)
            if post_install_datetime_max > last_cbis_installation_date:
                threshold = post_install_datetime_max  # todo - make sure no need for +1 hour

        if threshold is None:
            MAX_TIME_FOR_CBIS_INSTALLATION = 7
            hours_added = timedelta(hours=MAX_TIME_FOR_CBIS_INSTALLATION)
            threshold = last_cbis_installation_date + hours_added

        # t_delta = post_install_datetime_max - last_cbis_installation_date
        # threshold = last_cbis_installation_date+t_delta #todo - refinement (use post install date (?))

        return threshold

    def is_allowed_rpm(self, rpm_date, threshold):
        return (rpm_date <= threshold)

    def is_date_in_range(self, given_dates_list, date_rpm_dict, post_install_datetime_list):
        flg_date_in_range = True
        not_in_range_list = []
        threshold = self.cal_threshold(given_dates_list, post_install_datetime_list)
        for rpm_name, rpm_date in list(date_rpm_dict.items()):
            if self.is_allowed_rpm(rpm_date, threshold):
                pass
            else:
                flg_date_in_range = False
                not_in_range_list.append(rpm_name + " " + rpm_date.strftime('%Y/%m/%d %H:%M:%S'))
        return not_in_range_list, flg_date_in_range


class RPMInstalledDatesCheck(CheckRpmList):
    # Running validation on executed role
    objective_hosts = [Objectives.CONTROLLERS, Objectives.COMPUTES, Objectives.STORAGE]

    def set_document(self):
        self._unique_operation_name = "rpm_installed_dates_verification"
        self._title = "Verify all installed RPMs were installed by CBIS operations"
        self._failed_msg = "TBD"
        self._severity = Severity.WARNING


    def is_validation_passed(self):
        installed_rpm_datetime_dict = self.get_installed_rpms_and_dates_dict()
        installed_rpm_datetime_dict = self.convert_installed_rpms_datetime_format(installed_rpm_datetime_dict)

        operation_timing = Operation_timing_info(self)
        res = operation_timing.get_operations_datetime()
        cbis_deploy_datetime_list = res['overcloud_installation']
        assert cbis_deploy_datetime_list, "cbis have at least one deployment date is expected in the timing info part"
        self.add_to_validation_log("CBIS operations: {}".format(res))
        post_install_datetime_list = res['post_install']

        if 'hotfix' in res:
            cbis_hotfixes_datetime_list = res['hotfix']
            cbis_deploy_datetime_list = cbis_deploy_datetime_list + cbis_hotfixes_datetime_list
        cbis_deploy_start_datetime_list = operation_timing.get_start_operation_times_as_datetime(cbis_deploy_datetime_list)
        post_install_end_datetime_list = operation_timing.get_end_operation_times_as_datetime(post_install_datetime_list)
        rpms_not_in_range_list, flg_is_date_in_range = self.is_date_in_range(cbis_deploy_start_datetime_list,
                                                                             installed_rpm_datetime_dict,
                                                                             post_install_end_datetime_list
                                                                             )
        if flg_is_date_in_range:
            return True
        else:
            self._failed_msg = "The following rpms were not installed by CBIS deploy operation: \n {}".format(
                rpms_not_in_range_list)
            return False


class uc_rpm_list_check(CheckRpmList):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "rpm_list_verification"
        self._title = "Verify all rpm's are installed on UC"
        self._failed_msg = "TBD"
        self._severity = Severity.WARNING

    def is_validation_passed(self):
        uc_rpm_list = self.get_expected_rpm_list("/usr/share/cbis/undercloud_rpm_list.yaml")
        uc_installed_rpms_and_dates_dict = self.get_installed_rpms_and_dates_dict()
        uc_installed_rpm_list = list(uc_installed_rpms_and_dates_dict.keys())
        diff_list = PythonUtils.words_in_A_missing_from_B(uc_rpm_list, uc_installed_rpm_list)
        # check when those rpm was updated

        if len(diff_list) > 0:
            self._failed_msg = "The following rpms are missing: " + str(diff_list)
            return False
        return True


class overcloud_rpm_list_check(CheckRpmList):
    objective_hosts = [Objectives.CONTROLLERS, Objectives.COMPUTES]

    def set_document(self):
        self._unique_operation_name = "overcloud_rpm_list_verification"
        self._title = "Verify all rpm's are installed on the controllers"
        self._failed_msg = "TBD"
        self._msg = "TBD"
        self._severity = Severity.WARNING


    def is_validation_passed(self):
        oc_rpm_list = self.get_expected_rpm_list("/usr/share/cbis/overcloud_rpm_list.yaml")
        oc_installed_rpms_and_dates_dict = self.get_installed_rpms_and_dates_dict()
        oc_installed_rpm_list = list(oc_installed_rpms_and_dates_dict.keys())
        diff_list = PythonUtils.words_in_A_missing_from_B(oc_rpm_list, oc_installed_rpm_list)
        if len(diff_list) > 0:
            self._failed_msg = "The following rpms are missing: " + str(diff_list)
            return False
        return True

class VerifyOldRPMs(CheckRpmList):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "check_old_rpms"
        self._title = "Verify Kernel RPMs from older releases of CBIS are deleted"
        self._failed_msg = "Kernel RPMs from old releases of CBIS should be deleted, please check point 17 in the confluence page"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]
        self._blocking_tags = [BlockingTag.UPGRADE]

    def get_current_old_rpms(self):
        installed_rpm_datetime_dict = self.get_installed_rpms_and_dates_dict()
        old_rpms = ['kernel-devel-3.10.0-1160.66.1.el7.x86_64', 'kernel-debug-3.10.0-1160.66.1.el7.x86_64',
                    'kernel-debug-3.10.0-1127.13.1.el7.x86_64', 'kernel-debug-3.10.0-957.27.2.el7.x86_64']
        current_old_rpms = []
        for rpms in old_rpms:
            if rpms in installed_rpm_datetime_dict:
                current_old_rpms.append(rpms)
        return current_old_rpms

    def is_validation_passed(self):
        if len(self.get_current_old_rpms()) > 0:
            self._failed_msg = "The following rpms should be deleted: " + ", ".join(self.get_current_old_rpms()) + ". Please check point 17 in the Confluence page."
            return False
        return True