import collections


class PythonUtils:
    @staticmethod
    def reverse_dict(dct):
        res_dict = {}
        assert type(dct) is dict
        for k, v in dct.items():
            assert isinstance(v, collections.Hashable)
            res_dict.setdefault(v, []).append(k)
        return res_dict

    @staticmethod
    def get_dict_keys_with_same_values(dct):
        assert type(dct) is dict
        reversed_dict = PythonUtils.reverse_dict(dct)
        keys_with_duplicates_values = {k: v for k, v in reversed_dict.items() if len(v) > 1}
        return keys_with_duplicates_values