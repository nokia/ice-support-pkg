from __future__ import absolute_import
# base class for blue print data collectors

import re
from tools.python_versioning_alignment import to_unicode
from HealthCheckCommon.operations import *
from six.moves import range
from six.moves import zip



class BlueprintDataCollector(DataCollector):

    objective_hosts = {Deployment_type.CBIS: [Objectives.COMPUTES,
                                              Objectives.CONTROLLERS,
                                              Objectives.STORAGE,
                                              Objectives.MONITOR,
                                              Objectives.MAINTENANCE],

                       Deployment_type.NCS_OVER_BM: [Objectives.ALL_NODES]}
    cached_data_pool = {}
    _cached_ids = None
    handle_error = False

    def get_blueprint_objective_key_name(self):
        'return the name in the blue print table'
        assert False, 'please implement get_blueprint_objective_name'

    def get_ids(self):
        if not self._cached_ids:
            self._cached_ids = self.get_system_ids()

        return self._cached_ids

    def get_system_ids(self):
        assert False, 'please implement get_system_ids'

    def collect_blueprint_data(self):
        assert False, 'please implement collect_blueprint_data'

    def collect_all_data(self, hosts=None, **kwargs):
        data = DataCollector.collect_all_data(self, **kwargs)
        return self.get_blueprint_objective_key_name(), data

    def collect_data(self, **kwargs):
        data = self.collect_blueprint_data()
        assert type(data) is dict, "Blueprint DataCollector must return a dict."
        ids = sorted(list(self.get_ids()))
        data_keys = sorted(list(data.keys()))

        assert ids == data_keys, \
            "Blueprint DataCollector must return a dict with keys like what get_ids method returns, " \
            "data keys are: {}, get_ids return value is {}.".format(data_keys, ids)

        return data

    @staticmethod
    def group_by(values_list, group_name, starting_index=1):
        group_members = ["{}_{}".format(group_name, i) for i in range(starting_index, len(values_list) + starting_index)]
        to_return = dict(list(zip(group_members, values_list)))
        return to_return

    @staticmethod
    def group_by_keys_list(values_list, group_key_list):
        to_return = dict(list(zip(group_key_list, values_list)))
        return to_return

    def split_result_from_output(self, cmd, out, separator=':', is_number=False):
        out_list = out.splitlines()
        values_list = []
        for line in out_list:
            if len(line.split(separator)) != 2:
                raise UnExpectedSystemOutput(self.get_host_ip(), cmd, out, "expected format of 'caption{} value'".format(separator))
            value = line.split(separator)[1].strip()
            if is_number and not value.isnumeric():
                raise UnExpectedSystemOutput(self.get_host_ip(), cmd, out, "expected numeric value ")
            values_list.append(value)
        return values_list

    def get_key_from_json(self, json_object, key, cmd):
        res = json_object.get(key)
        if not res:
            raise UnExpectedSystemOutput(self.get_host_ip(), cmd, json_object,
                                         "key {} not in json object.".format(key))

        return res

    def get_lshw_json(self, classes_name_list=None):
        if classes_name_list:
            classes_name_str = " -class ".join(classes_name_list)
            cmd = "sudo lshw -class {} -json".format(classes_name_str)
        else:
            cmd = "sudo lshw -json"
        out = self.get_output_from_run_cmd(cmd, hosts_cached_pool=BlueprintDataCollector.cached_data_pool)
        if not out.strip()[0] == "[":
            out = "[ " + out + " ]"
        out_without_comma_before_close_parentheses = re.sub(r",(\n\s+[\}\]])", r"\1", out)
        out_with_fixed_json = re.sub(r'\}(\s*)\{', "},{", out_without_comma_before_close_parentheses,
                                     flags=re.MULTILINE | re.DOTALL)

        return json.loads(out_with_fixed_json)

    def get_dmidecode_json_by_type(self, specific_type, type_in_dmidecode_out):
        cmd = "sudo dmidecode -t {}".format(specific_type)
        out = self.get_output_from_run_cmd(cmd,hosts_cached_pool=BlueprintDataCollector.cached_data_pool)
        dmidecode_types_list = self._create_yaml_list_from_dmidecode_output(out, type_in_dmidecode_out)

        return [PythonUtils.get_dict_from_string(dmidecode_type, 'yaml')
                for dmidecode_type in dmidecode_types_list]

    def get_id_val_from_lshw_json_by_property(self, property_name, class_name=None):
        out_json = self.get_lshw_json(classes_name_list=[class_name])

        return self.get_id_val_from_json_by_property(out_json, "id", property_name,
                                                     "sudo lshw -class {}".format(class_name))

    def get_id_val_from_json_by_property(self, json_object, id_name, property_name, cmd):
        res_dict = {}

        for info in json_object:
            property_id = self.get_key_from_json(info, id_name, cmd)
            res_dict[property_id] = info.get(property_name, "no {}".format(property_name))

        return res_dict

    def _create_yaml_list_from_dmidecode_output(self, dmidecode_out, title_in_out):
        dmidecode_out = dmidecode_out.replace("\t", " ")
        objects_list = dmidecode_out.split("\n\n")
        objects_list_no_comments = list([dmidecode_item for dmidecode_item in objects_list if not dmidecode_item.strip().startswith("#")])
        relevant_objects_list = list([dmidecode_item for dmidecode_item in objects_list_no_comments if title_in_out in dmidecode_item])
        objects_list_without_handle_titles = [re.sub("(?m)^Handle.*\n?", "", out) for out in relevant_objects_list]
        objects_list_without_titles = [out.replace(title_in_out, "") for out in objects_list_without_handle_titles]

        return objects_list_without_titles

    def set_dict_values_to_numeric(self, info, validated_item, unit, cmd, is_unicode=False):
        res = {}

        for id_, value in list(info.items()):
            if is_unicode:
                is_numeric = value.strip().split()[0].isnumeric()
            else:
                is_numeric = to_unicode(value.strip().split()[0], 'utf-8').isnumeric()

            if len(value.split()) != 2 \
                    or not is_numeric:
                raise UnExpectedSystemOutput(self.get_host_ip(), cmd, value, "Expected {item} in format: '<num> {unit}'".format(item=validated_item, unit=unit))
            num_in_int, size_unit = PythonUtils.convert_str_with_unit_to_mega(value)
            try:
                res[id_] = num_in_int
            except ValueError:
                raise UnExpectedSystemOutput(ip=self._host_executor.ip, cmd=cmd, output="expected int found '{}'".format(str(num_in_int)))

        return res

    def get_objective_value_by_cmd(self, cmd, objective_id, is_split_out=True):
        objective_value = self.get_output_from_run_cmd(cmd, hosts_cached_pool=BlueprintDataCollector.cached_data_pool)
        if is_split_out:
            objective_list = self.split_result_from_output(cmd, objective_value)
            if len(set(objective_list)) > 1:
                raise NonIdenticalValues(self.get_host_ip(), cmd, objective_list,
                                             "There should be only one value - {} has the values {}".format(
                                                 objective_id, objective_list))
            objective_value = objective_list[0]
        return objective_value
