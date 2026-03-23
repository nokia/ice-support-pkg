from __future__ import absolute_import
import json
from functools import total_ordering
from tools.python_utils import PythonUtils


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

    @staticmethod
    def str2OrderedConst(cls,str_const):
        ordered_const_class_variables_dict = {v.value: v for k, v in list(cls.__dict__.items()) if  isinstance(v,OrderedConst)  }
        assert str_const in ordered_const_class_variables_dict
        return ordered_const_class_variables_dict[str_const]

def ordered_consts(cls):
    ordered_const_class_variables = {k: v.order for k, v in list(cls.__dict__.items()) if isinstance(v,OrderedConst)}
    dict_keys_with_same_values = PythonUtils.get_dict_keys_with_same_values(ordered_const_class_variables)
    assert len(dict_keys_with_same_values) == 0, '\nin ordered consts, you  have to give different priorities to the' \
                                                 ' class OrderedConsts Objects. following priorities values are used' \
                                                 ' twice: \n{}'.format(json.dumps(dict_keys_with_same_values, indent=4))
    return cls
