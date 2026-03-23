from functools import total_ordering
from DeploymentType import DeploymentType
from PythonUtils import PythonUtils
import json


@total_ordering
class OrderedConst:
    def __init__(self, value, order):
        assert type(order) is int
        self.value = value
        self.order = order

    def __eq__(self, other):
        assert type(other) is type(self), "Cannot compare types : {}, {}".format(type(other), type(self))
        return self.order == other.order

    def __lt__(self, other):
        assert type(other) is type(self)
        return self.order < other.order

    def __str__(self):
        return str(self.value)

    def __hash__(self):
        return hash(str(self))


def ordered_consts(cls):
    ordered_const_class_variables = {k: v.order for k, v in cls.__dict__.items() if type(v) is OrderedConst}
    dict_keys_with_same_values = PythonUtils.get_dict_keys_with_same_values(ordered_const_class_variables)
    assert len(dict_keys_with_same_values) == 0, '\nin ordered consts, you  have to give different priorities to the' \
                                                 ' class OrderedConsts Objects. following priorities values are used' \
                                                 ' twice: \n{}'.format(json.dumps(dict_keys_with_same_values, indent=4))
    return cls


@ordered_consts
class Version:
    """NCS/CBIS version"""
    'please keep the version text as in the configuration files'
    V17 = OrderedConst("17", 0)
    V17_5 = OrderedConst("17.5", 1)
    V18 = OrderedConst("18", 2)
    V18_5 = OrderedConst("18.5", 3)
    V19 = OrderedConst("19", 4)
    V19A = OrderedConst("19A", 5)
    V20 = OrderedConst("20", 6)
    V21 = OrderedConst("21", 7)
    V22 = OrderedConst("22", 8)
    V23 = OrderedConst("23", 9)
    V24 = OrderedConst("24", 10)
    V25 = OrderedConst("25", 11)
    V25MP = OrderedConst("25.2", 12)
    V_CBIS_BVT_TMP_VERSION = OrderedConst("binary",100)
    AVAILABLE_VERSIONS = [V_CBIS_BVT_TMP_VERSION, V25, V25MP, V24, V23, V22, V21, V20, V19, V19A, V18_5, V18]
    AVAILABLE_VERSIONS_STR = [str(version) for version in AVAILABLE_VERSIONS]

    @staticmethod
    def convert_str_to_version_const(deployment_type, version_str):
        match_version = [version for version in Version.get_available_versions(deployment_type)
                         if version.value == version_str]

        assert len(match_version), "{} doesn't support version {}".format(deployment_type, version_str)
        return match_version[0]

    @staticmethod
    def get_available_versions(deployment_type):
        if DeploymentType.is_cbis(deployment_type):
            return [Version.V_CBIS_BVT_TMP_VERSION, Version.V25, Version.V25MP, Version.V24, Version.V23, Version.V22, Version.V21, Version.V20, Version.V19, Version.V19A, Version.V18_5, Version.V18]
        return []

