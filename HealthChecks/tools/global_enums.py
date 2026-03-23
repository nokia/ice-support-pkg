from __future__ import absolute_import
import re
from collections import OrderedDict
from tools.OrderedConst import *

class IP:
    LOCAL_IP = "127.0.0.1"

@ordered_consts
class Status:
    # Define the validation status
    SYS_PROBLEM = OrderedConst("sys_problem", 1)
    NA = OrderedConst("NA", 2)
    FALSE = OrderedConst("False", 3)

    @staticmethod
    def get_status_order_for_sort():
        status_order = {}
        for attr_name, attr_value in list(Status.__dict__.items()):
            if isinstance(attr_value, OrderedConst):
                status_order[attr_value.value] = attr_value.order
        return OrderedDict(sorted(list(status_order.items()), key=lambda x: x[1]))


@ordered_consts
class Severity:
    ''' define how severe is this validation'''
    CRITICAL = OrderedConst("Critical", 1)
    ERROR = OrderedConst("Error", 2)
    WARNING = OrderedConst("Warning", 3)
    NOTIFICATION = OrderedConst("Notification", 4)
    NA = OrderedConst("Not applicable", 5)

    AVAILABLE_SEVERITIES = [ERROR, WARNING, CRITICAL, NOTIFICATION, NA]

    @staticmethod
    def get_severity_order(severity_str):
        for severity_item in Severity.AVAILABLE_SEVERITIES:
            if severity_str == severity_item.value:
                return severity_item.order
        assert False, "{} is not part of {}".format(severity_str, Severity.AVAILABLE_SEVERITIES)

    @staticmethod
    def get_severity_order_for_sort():
        original_severity_dict = {}
        for attr_name, attr_value in list(Severity.__dict__.items()):
            if isinstance(attr_value, OrderedConst):
                original_severity_dict[attr_value.value] = attr_value.order
        return OrderedDict(sorted(list(original_severity_dict.items()), key=lambda x: x[1]))


@ordered_consts
class Version:
    '''NCS/CBIS version'''
    'please keep the version text as in the configuration files'
    NOT_EXIST_VERSION = OrderedConst("no_version", 101)
    Vdummy = OrderedConst("dummy_version", 100)
    V17 = OrderedConst("17", 1)
    V17_5 = OrderedConst("17.5", 2)
    V18 = OrderedConst("18", 3)
    V18_5 = OrderedConst("18.5", 4)
    V19 = OrderedConst("19", 5)
    V19A = OrderedConst("19A", 6)
    V20 = OrderedConst("20", 7)
    V20_FP1 = OrderedConst("20.6", 8)
    V20_FP2 = OrderedConst("20.12", 9)
    V22 = OrderedConst("22", 11)
    V22_FP1 = OrderedConst("22.2", 12)
    V22_7 = OrderedConst("22.7", 13)
    V22_12 = OrderedConst("22.12", 14)
    V23 = OrderedConst("23", 15)
    V23_10 = OrderedConst("23.10", 17)
    V24 = OrderedConst("24", 18)
    V24_7 = OrderedConst("24.7", 19)
    V24_11 = OrderedConst("24.11", 20)
    V25 = OrderedConst("25", 21)
    V25_7 = OrderedConst("25.7", 22)
    V25_11 = OrderedConst("25.11", 23)
    V26_7 = OrderedConst("26.7", 24)
    AVAILABLE_VERSIONS = [V26_7, V25_11, V25_7, V25, V24_11, V24_7, V24, V23_10, V23, V22_12, V22_7, V22_FP1, V22, V20_FP2, V20_FP1, V20, V19, V19A,
                          V18_5, V18]

    @staticmethod
    def get_version_name(value):
        version_naming_dict = {Version.V20_FP1.value: '20 FP1',
                               Version.V20_FP2.value: '20 FP2',
                               Version.V22_FP1.value: '22 FP1'}
        return version_naming_dict.get(str(value), str(value))

    @staticmethod
    def convert_str_to_version_const(deployment_type, version_str):
        available_versions = Version.get_available_versions(deployment_type)
        if "19.100" in version_str and Version.V19A in available_versions:
            return Version.V19A
        if version_str.startswith('21.12'):
            return Version.V22
        split_version = version_str.split(".")
        if len(split_version) == 3:
            # for future CBIS releases let say *.100.0, *.200.0, *.300.0, etc. as base version
            if split_version[1].endswith("00"):
                sub_main_version = split_version[2].replace("0", "")
                if sub_main_version == "":
                    sub_main_version = "1"
                version_str = split_version[0] + "." + sub_main_version
            else:
                sub_main_version = split_version[1].lstrip("0")

                if len(sub_main_version) and int(sub_main_version) > 12:
                    sub_main_version = sub_main_version.replace("0", "")

                version_str = split_version[0] + "." + sub_main_version
        match_version = [version for version in Version.get_available_versions(deployment_type)
                         if version.value == version_str]
        if len(match_version) < 1 and not version_str.startswith("23"):
            match_version = [version for version in Version.get_available_versions(deployment_type)
                             if version_str.startswith(version.value)]
        if len(match_version) == 0:
            return Version.NOT_EXIST_VERSION
        return match_version[0]

    @staticmethod
    def get_available_versions(deployment_type):
        if Deployment_type.is_cbis(deployment_type):
            return [Version.V25, Version.V24, Version.V22_FP1, Version.V22, Version.V20, Version.V19,
                    Version.V19A, Version.V18_5, Version.V18]
        if Deployment_type.is_ncs(deployment_type):
            return [Version.V26_7, Version.V25_11, Version.V25_7, Version.V24_11, Version.V24_7, Version.V23_10, Version.V22_12, Version.V22_7, Version.V22, Version.V20_FP2,
                    Version.V20_FP1, Version.V20]

    @staticmethod
    def is_version_in_range(version, range_version_str):
        regex_range_version = r"\[(Version\..*)-(Version\..*|unlimited)\]"
        ALL_VERSIONS = "ALL_VERSIONS"
        UNLIMITED = "unlimited"
        if range_version_str == ALL_VERSIONS:
            return True
        assert re.findall(regex_range_version, range_version_str), "Expected version in regex format: {}, actual:{}".format(
            regex_range_version, range_version_str)
        versions_range_list = range_version_str[1:-1].split('-')
        for item in versions_range_list:
            if item != UNLIMITED:
                assert hasattr(Version, item.split('Version.')[1]), "{} not found in Version class".format(item)
        if version < eval(versions_range_list[0]) or (
                versions_range_list[1] != UNLIMITED and version > eval(versions_range_list[1])):
            return False
        return True


class SubVersion:
    NO_MP = 'NO MP'
    MP1 = 'MP1'
    MP1_2 = 'MP1.2'
    MP2 = 'MP2'
    MP3 = 'MP3'
    MP4 = 'MP4'
    MP5 = 'MP5'
    MP6 = 'MP6'
    PP0 = 'PP0'
    PP1 = 'PP1'
    PP2 = 'PP2'
    PP3 = 'PP3'
    PP4 = 'PP4'
    PP5 = 'PP5'
    PP6 = 'PP6'
    PP7 = 'PP7'
    PP8 = 'PP8'
    PP9 = 'PP9'
    PP10 = 'PP10'
    PP11 = 'PP11'
    PP12 = 'PP12'
    PP13 = 'PP13'
    PP14 = 'PP14'
    PP15 = 'PP15'
    PP16 = 'PP16'
    SP1 = 'SP1'
    SP2 = 'SP2'
    SP3 = 'SP3'
    SP4 = 'SP4'
    FP1 = 'FP1'
    FP2 = 'FP2'
    SU3 = 'SU3'
    SU4 = 'SU4'
    NO_PP = 'NO PP'


class Deployment_type:
    '''please keep the deployment_type text as in the configuration files'''

    NCS_OVER_OPENSTACK = "ncs_open-stack"
    NCS_OVER_BM = "ncs_bare-metal"
    NCS_OVER_VSPHERE = "ncs_vsphere"
    CBIS = "cbis"
    DUMMY_DEPLYMENT = "dummy_deployment"
    AVAILABLE_TYPES = [CBIS, NCS_OVER_OPENSTACK, NCS_OVER_BM, NCS_OVER_VSPHERE]

    @staticmethod
    def get_ncs_types():
        return [
            Deployment_type.NCS_OVER_OPENSTACK,
            Deployment_type.NCS_OVER_BM,
            Deployment_type.NCS_OVER_VSPHERE
        ]

    @staticmethod
    def get_ncs_vsphere_openstack_types():
        return [
            Deployment_type.NCS_OVER_OPENSTACK,
            Deployment_type.NCS_OVER_VSPHERE
        ]

    # CNS CN CP CE Infra SRE Israel
    @staticmethod
    def is_ncs(deployment_type):
        return deployment_type in Deployment_type.get_ncs_types()

    @staticmethod
    def is_cbis(deployment_type):
        return deployment_type in [Deployment_type.CBIS]

    @staticmethod
    def get_deployment_type_key_from_value(deployment_type):
        for key, val in list(Deployment_type.__dict__.items()):
            if val == deployment_type:
                return "{}.{}".format(Deployment_type.__name__, key)


class Objectives():
    # cbis
    UC = "undercloud"
    HYP = "hypervisor"
    ALL_HOSTS = "all-hosts"
    # ALL_HOSTS = { COMPUTES, CONTROLLERS, STORAGE, UC }
    CONTROLLERS = "controllers"
    ONE_CONTROLLER = "one_controller"
    COMPUTES = "computes"
    SRIOV_COMPUTES = "SRIOV_computes"
    OVS_COMPUTES = "OvsCompute"
    DPDK_COMPUTES = "DpdkCompute"
    AVRS_COMPUTES = "AvrsCompute"
    ICE_CONTAINER = "ice_container"
    MAINTENANCE = "maintenance"

    # ncs
    ALL_NODES = "all-k8s-nodes"
    MASTERS = "all_k8s_master"
    ONE_MASTER = "single_k8s_master"
    MANAGERS = 'managers'
    ONE_MANAGER = 'one_manager'
    WORKERS = "workers"
    EDGES = "edges"

    # on ncs on openstack / vsphere
    DEPLOYER = 'deployer'

    # shared
    ONE_STORAGE = "one_storage"
    STORAGE = "storages"
    MONITOR = 'monitoring'

    # for the log implementation
    # logs get the objectives from the config file
    # this is just turn off the assert in that case
    NA = "not relevant to this case"

    @staticmethod
    def get_available_types(deployment_type):
        if Deployment_type.is_ncs(deployment_type):
            types =  [Objectives.ALL_NODES,
                      Objectives.ONE_MASTER,
                      Objectives.MASTERS,
                      Objectives.EDGES,
                      Objectives.WORKERS,
                      Objectives.MANAGERS,
                      Objectives.ONE_MANAGER,
                      Objectives.ONE_STORAGE,
                      Objectives.STORAGE,
                      Objectives.MONITOR
                      ]
            if deployment_type == Deployment_type.NCS_OVER_OPENSTACK or deployment_type == Deployment_type.NCS_OVER_VSPHERE:
                types.append(Objectives.DEPLOYER)
            return types

        if Deployment_type.is_cbis(deployment_type):
            return [Objectives.ALL_HOSTS,
                    Objectives.ONE_CONTROLLER,
                    Objectives.CONTROLLERS,
                    Objectives.SRIOV_COMPUTES,
                    Objectives.OVS_COMPUTES,
                    Objectives.UC,
                    Objectives.HYP,
                    Objectives.COMPUTES,
                    Objectives.ONE_STORAGE,
                    Objectives.STORAGE,
                    Objectives.DPDK_COMPUTES,
                    Objectives.AVRS_COMPUTES,
                    Objectives.MAINTENANCE,
                    Objectives.MONITOR
                    ]

    @staticmethod
    def get_all_single_types():
        return [
            Objectives.UC,
            Objectives.HYP,
            Objectives.ONE_CONTROLLER,
            Objectives.ONE_STORAGE,
            Objectives.DEPLOYER,
            Objectives.ONE_MASTER,
            Objectives.ONE_MANAGER,
            Objectives.ICE_CONTAINER
        ]

    @staticmethod
    def get_included_objectives(objective):
        if objective == Objectives.ALL_NODES:
            return [Objectives.ONE_MASTER,
                    Objectives.MASTERS,
                    Objectives.EDGES,
                    Objectives.WORKERS,
                    Objectives.ONE_MANAGER,
                    Objectives.MANAGERS,
                    Objectives.ONE_STORAGE,
                    Objectives.STORAGE,
                    Objectives.MONITOR,
                    Objectives.DEPLOYER
                    ]

        if objective == Objectives.ALL_HOSTS:
            return [Objectives.ONE_CONTROLLER,
                    Objectives.CONTROLLERS,
                    Objectives.SRIOV_COMPUTES,
                    Objectives.OVS_COMPUTES,
                    Objectives.DPDK_COMPUTES,
                    Objectives.AVRS_COMPUTES,
                    Objectives.UC,
                    Objectives.HYP,
                    Objectives.COMPUTES,
                    Objectives.ONE_STORAGE,
                    Objectives.STORAGE,
                    Objectives.MONITOR
                    ]
        if objective == Objectives.MANAGERS:
            return [Objectives.ONE_MANAGER]

        if objective == Objectives.MASTERS:
            return [Objectives.ONE_MASTER]

        if objective == Objectives.CONTROLLERS:
            return [Objectives.ONE_CONTROLLER]

        if objective == Objectives.STORAGE:
            return [Objectives.ONE_STORAGE]

        if objective == Objectives.COMPUTES:
            return [
                Objectives.SRIOV_COMPUTES,
                Objectives.OVS_COMPUTES,
                Objectives.DPDK_COMPUTES,
                Objectives.AVRS_COMPUTES
            ]

        return []

    @staticmethod
    def get_roles_list_by_deployment_type(deployment_type):
        if Deployment_type.is_ncs(deployment_type):
            return [Objectives.MASTERS, Objectives.WORKERS, Objectives.EDGES, Objectives.STORAGE, Objectives.MONITOR]

        if Deployment_type.is_cbis(deployment_type):
            return [Objectives.CONTROLLERS, Objectives.COMPUTES, Objectives.STORAGE, Objectives.MAINTENANCE]


class ImplicationTag:
    PRE_OPERATION = "#system_at_risk:do_not_run_scale_or_upgrade_before_fixing_this_issue"
    PERFORMANCE = "#performance:affect_the_system_performance"
    RISK_BAD_CONFIGURATION = "#system_at_risk:bad_configuration"
    RISK_NO_HIGH_AVAILABILITY = "#system_at_risk:no_high_availability"
    RISK_RESOURCE_CLEANING_RECOMMENDED = "#system_at_risk:resource_cleaning_is_recommended"
    RISK_GARBAGE_CLEANING_RECOMMENDED = "#system_at_risk:garbage_cleaning_is_recommended"
    RISK_EXPIRY_DATE_APPROACHING = "#system_at_risk:expiry_date_approaching"
    SYMPTOM = "#symptom_of_problematic_state:deeper_investigation_is_recommended"
    ACTIVE_PROBLEM = "#active_problem:fix_is_needed"
    NOTE = "#system_at_low_risk:notification"
    APPLICATION_DOMAIN = "#additonal_domain_risk:applications"

    @staticmethod
    def get_all_implication_tags():
        return [ImplicationTag.PRE_OPERATION, ImplicationTag.PERFORMANCE, ImplicationTag.RISK_BAD_CONFIGURATION,
                ImplicationTag.RISK_NO_HIGH_AVAILABILITY, ImplicationTag.RISK_RESOURCE_CLEANING_RECOMMENDED,
                ImplicationTag.RISK_GARBAGE_CLEANING_RECOMMENDED, ImplicationTag.RISK_EXPIRY_DATE_APPROACHING,
                ImplicationTag.SYMPTOM, ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.NOTE,
                ImplicationTag.APPLICATION_DOMAIN]


class BlockingTag:
    SCALE = "scale_blocker"
    UPGRADE = "upgrade_blocker"
    MIGRATION = "migration_blocker"
    CERT_RENEWAL = "certrenewal_blocker"

    @staticmethod
    def get_all_blocking_tags():
        return [BlockingTag.UPGRADE, BlockingTag.SCALE, BlockingTag.MIGRATION, BlockingTag.CERT_RENEWAL]


class States:
    VALID = "VALID"
    UNKNOWN = "UNKNOWN"
    INVALID = "INVALID"
    INFO = "INFO"

    @staticmethod
    def get_states_colors_dict():
        yellow_color = "#FFD700"
        return {States.VALID: "green", States.UNKNOWN: yellow_color, States.INVALID: "red", States.INFO: "black"}

    @staticmethod
    def get_states_list():
        return [States.INVALID, States.UNKNOWN, States.VALID, States.INFO]


class SizeUnit:
    B = "Bytes"
    KB = "Kilobytes"
