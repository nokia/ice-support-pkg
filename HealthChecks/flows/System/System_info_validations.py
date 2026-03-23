from __future__ import absolute_import
from HealthCheckCommon.operations import *
import tools.sys_parameters as gs
import tools.SubVersions as SubVersions
from HealthCheckCommon.validator import Validator
from tools.Exceptions import *
from tools.global_enums import SubVersion
from datetime import datetime
from tools.Conversion import Conversion

class LatestHotfixCheck(Validator):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.UC],
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MANAGER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.DEPLOYER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.DEPLOYER]
    }

    NO_HOTFIX = "NO-HOTFIX"

    def set_document(self):
        self._unique_operation_name = "latest hotfix installed"
        self._title = "Check if the latest hotfix for the specific version is installed"
        self._failed_msg = "TBD"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.NOTE]

    def is_validation_passed(self):
        last_pp = SubVersions.LATEST_PP_DICT.get(gs.get_deployment_type())

        if last_pp is None:  # if we forgot a version
            raise NotSupportedForThisVersion("get last subversion")
        latest_required_version = last_pp.get(gs.get_version(), {})

        if not latest_required_version:
            self._severity = Severity.ERROR
            self._failed_msg = "Unsupported version: {}".format(gs.get_version())
            return False
        hotfix_installed = gs.get_hotfix_list()
        latest_hot_fix = self.NO_HOTFIX

        if hotfix_installed:
            if len(list(hotfix_installed.keys())) == 1 and list(hotfix_installed.keys())[0] != 'None':
                latest_hot_fix = list(hotfix_installed.keys())[0]
            elif len(list(hotfix_installed.keys())) > 1:
                latest_hot_fix = self.get_latest_hot_fix_name(hotfix_installed=hotfix_installed)
        latest_hot_fix_per_version = Conversion.convert_version_to_dict(hot_fix_version=latest_hot_fix)

        if not self.is_version_supported(installed_version=latest_hot_fix_per_version,
                                         latest_hot_fix=latest_hot_fix):
            return False
        return self.is_version_updated(installed_version=latest_hot_fix_per_version,
                                       latest_required_version=latest_required_version,
                                       latest_hot_fix=latest_hot_fix)


    def get_recommended_hotfix_list(self, latest_required_version):
        recommended_hotfix_list = []
        for mp, pp_list in list(latest_required_version.items()):
            for pp in pp_list:
                hotfix_item_list = ['{}{}'.format(gs.get_deployment_type().split('_')[0].upper(), Version.get_version_name(gs.get_version()))]
                if mp != SubVersion.NO_MP:
                    hotfix_item_list.append(mp)
                if pp != SubVersion.NO_PP:
                    hotfix_item_list.append(pp)
                recommended_hotfix_list.append('-'.join(hotfix_item_list))
        return recommended_hotfix_list

    def is_version_updated(self, installed_version, latest_required_version, latest_hot_fix):
        recommended_hotfix_list = self.get_recommended_hotfix_list(latest_required_version)
        self._failed_msg = "Hotfix version {latest_hot_fix} is out of date, the recommended version is {recommended_hotfix_list}".format(
            latest_hot_fix=latest_hot_fix, recommended_hotfix_list=str(recommended_hotfix_list))
        self._severity = Severity.WARNING

        if latest_hot_fix == self.NO_HOTFIX:
            self._severity = Severity.ERROR

        if installed_version['MP_SP'] in list(latest_required_version.keys()):
            if not installed_version['PP_SU'] in latest_required_version[installed_version['MP_SP']]:
                return False
            return True
        elif self.is_newer_mp_than_latest(installed_version['MP_SP'], list(latest_required_version.keys())):
            return True
        return False

    def is_version_supported(self, installed_version, latest_hot_fix):
        supported_versions = SubVersions.HOT_FIX_DICT.get(gs.get_deployment_type()).get(gs.get_version())
        self._failed_msg = "Hotfix version {latest_hot_fix} is unsupported. supported versions:{supported_versions}".format(
            latest_hot_fix=latest_hot_fix, supported_versions=supported_versions)
        self._severity = Severity.ERROR
        if installed_version['MP_SP'] in list(supported_versions.keys()):
            if installed_version['PP_SU'] not in supported_versions.get(installed_version['MP_SP']):
                return False
            return True
        return False

    def is_newer_mp_than_latest(self, installed_mp, known_mps):
        mp_order = [
            SubVersion.NO_MP, SubVersion.MP1, SubVersion.MP1_2, SubVersion.MP2,
            SubVersion.MP3, SubVersion.MP4, SubVersion.MP5, SubVersion.MP6
        ]
        try:
            installed_idx = mp_order.index(installed_mp)
            latest_idx = max(mp_order.index(mp) for mp in known_mps)
            return installed_idx > latest_idx
        except ValueError:
            return False

    def get_latest_hot_fix_name(self, hotfix_installed):
        try:
            latest_hot_fix_date = max(
                [datetime.strptime(x, '%Y-%m-%dT%H:%M:%S.%f') for x in list(hotfix_installed.values())])
            str_latest_hot_fix_date = latest_hot_fix_date.strftime('%Y-%m-%dT%H:%M:%S.%f')
        except:
            raise UnExpectedSystemOutput(cmd="",
                                         ip="local host",
                                         output="invalid format date, expected format:'%Y-%m-%dT%H:%M:%S.%f'")
        latest_hot_fix_index = list(hotfix_installed.values()).index(str_latest_hot_fix_date)
        return list(hotfix_installed.keys())[latest_hot_fix_index]
