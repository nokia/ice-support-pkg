from __future__ import absolute_import
import pandas
import json
from tools.python_utils import PythonUtils
from tools.Exceptions import *
import re
from six.moves import range


class ExcelToJson:
    def __init__(self):
        self.excel_path = 'blueprint_spec.xlsx'
        self.role_field = ''
        self.roles = []
        self.component = ''
        self.roles_option = {}

    def get_excel_data(self, sheet_name):
        excel_data_df = pandas.read_excel(self.excel_path, sheet_name=sheet_name)
        json_str = excel_data_df.to_json(orient='records')
        return json.loads(json_str)

    def set_role(self, option):
        self.role_field = option.get('role')
        try:
            self.roles = option.get('role').strip('][').split(',')
            self.roles = [role.strip(' ') for role in self.roles]
        except:
            self.roles = [option.get('role')]
            self.roles_option[option.get('role')] = {}

    def convert_value_by_units(self, value, unit):
        value_with_unit = '{} {}'.format(value, unit)
        return PythonUtils.convert_str_with_unit_to_mega(value_with_unit)

    def get_range_value(self, option):
        max_value = 'unlimited'
        try:
            range_list = re.findall('range\((.*)-(.*\))', option['range'])
            min_value, property_unit = self.convert_value_by_units(range_list[0][0], option['units'])
            if 'unlimited' not in option.get('range'):
                max_value, property_unit = self.convert_value_by_units(range_list[0][1], option['units'])
        except Exception as e:
            raise InValidStringFormat(option['range'], 'range(min_value-max_value)')
        return 'range({}-{})'.format(min_value, max_value), property_unit

    def get_property_values(self, property, value_keys, option):
        values_list = []
        for value_key in value_keys:
            if option[value_key] is not None:
                if option.get('units'):
                    if option.get('range'):
                        option[value_key], property_unit = self.get_range_value(option)
                    else:
                        option[value_key], property_unit =self.convert_value_by_units(option[value_key], option['units'])
                    property = property + property_unit
                values_list.append(option[value_key])
        for role in self.roles:
            if len(values_list) > 1:
                values_str = str(values_list[0])
                for value in values_list[1:]:
                    values_str += " or " + str(value)
                self.roles_option[role][property] = values_str
            else:
                if values_list == []:
                    values_list = ['']
                self.roles_option[role][property] = values_list[0]

    def add_entity_info_to_json(self, blueprint_name, next_role, next_component, next_property, new_json):
        role = self.roles[0]
        if (self.role_field != next_role and next_role is not None) or (
                self.component != next_component and next_component is not None)\
                or next_property in self.roles_option[role]:
            if 'entity_amount' in self.roles_option[role]:
                counter = int(self.roles_option[role]['entity_amount'])
                for role in self.roles:
                    del self.roles_option[role]['entity_amount']
            else:
                counter = 1
            for i in range(counter):
                if not new_json.get(blueprint_name).get(role).get(self.component):
                    for role in self.roles:
                        new_json[blueprint_name][role][self.component] = self.roles_option[role]
                else:
                    for role in self.roles:
                        if isinstance(new_json[blueprint_name][role][self.component], list):
                            new_json[blueprint_name][role][self.component].append(self.roles_option[role])
                        else:
                            previous_option = new_json[blueprint_name][role][self.component]
                            new_json[blueprint_name][role][self.component] = []
                            new_json[blueprint_name][role][self.component].append(previous_option)
                            new_json[blueprint_name][role][self.component].append(self.roles_option[role])
            self.roles_option = {}



def main():
    excel_to_json = ExcelToJson()
    new_json = {}

    PythonUtils.extract_zip_file('blueprint_spec.zip', '')
    excel_data_df = pandas.ExcelFile(excel_to_json.excel_path)
    sheet_names = excel_data_df.sheet_names

    for sheet_name in sheet_names:
        json_dict = excel_to_json.get_excel_data(sheet_name)
        blueprint_name = sheet_name
        new_json[blueprint_name] = {
            'computes': {},
            'controllers': {},
            'storages': {},
            'all_k8s_master': {},
            'workers': {},
            'edges': {},
            'monitoring': {},
            'general': {}
        }
        excel_to_json.role_field = ''
        excel_to_json.roles = []
        excel_to_json.roles_option = {}
        for index, option in enumerate(json_dict):
            value_keys = [key for key in list(option.keys()) if 'value' in key]
            if option.get('role') is not None:
                excel_to_json.set_role(option)
            if excel_to_json.roles_option == {}:
                for role in excel_to_json.roles:
                    excel_to_json.roles_option[role] = {}
            if option.get('component') is not None:
                excel_to_json.component = option.get('component').split('__')[0]
            property = option['property']
            excel_to_json.get_property_values(property, value_keys, option)
            try:
                next_role = json_dict[index + 1]['role']
                next_component = json_dict[index + 1]['component']
                next_property = json_dict[index + 1]['property']
            except:
                next_property = property
            excel_to_json.add_entity_info_to_json(blueprint_name, next_role, next_component, next_property, new_json)

    with open('blueprint_spec.json', 'w') as f:
        json.dump(new_json, f, indent=2)

if __name__ == '__main__':
    main()