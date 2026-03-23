from __future__ import absolute_import
from __future__ import print_function

import inspect
import re
import json
import socket
import sys

import ipaddress
import six
import yaml
import xml.etree.ElementTree as ET

from yaml.parser import ParserError
from yaml.scanner import ScannerError

from tools.Exceptions import *
import zipfile
from collections import OrderedDict
from tools.python_versioning_alignment import StringIO, ConfigParser, get_user_input, to_unicode, Hashable, read_config
from six.moves import filter
from six.moves import range


class PythonUtils:
    TIME_FORMAT_WITH_SINGLE_DIGIT = ('%b %d %H:%M:%S', '%b %d')

    @staticmethod
    def words_in_A_missing_from_B(A_list, B_list):
        missing_words = []
        for word in A_list:
            if word not in B_list:
                missing_words.append(word)

        return missing_words

    @staticmethod
    def word_A_diffrent_than_B(A_list, B_list):
        assert (len(A_list) == len(B_list))
        diff_index = []
        for index in range(len(A_list)):
            if A_list[index] != B_list[index]:
                diff_index.append(index)
        return diff_index

    @staticmethod
    def list_intersection(list_a, list_b):
        res = [a for a in list_a if a in list_b]
        return res

    @staticmethod
    def reverse_dict_by_to_string_values(dct):
        res_dict = {}
        assert isinstance(dct, dict)

        for k, v in list(dct.items()):
            str_v = json.dumps(v,indent=2)
            res_dict.setdefault(str_v, []).append(k)
        return res_dict

    @staticmethod
    def reverse_dict(dct):
        '''
        :param dct: a dictionary with just 1 level hierarchy. e.g.: d={"a":1,"b":2}
        :return: a dict with the values as the keys. e.g. : {1:["a"],2:["b"]}
        '''
        res_dict = {}
        assert isinstance(dct, dict)
        for k, v in list(dct.items()):
            assert isinstance(v, Hashable)
            res_dict.setdefault(v, []).append(k)
        return res_dict

    @staticmethod
    def get_dict_keys_with_same_values(dct):
        assert type(dct) is dict
        reversed_dict = PythonUtils.reverse_dict(dct)
        keys_with_duplicates_values = {k: v for k, v in list(reversed_dict.items()) if len(v) > 1}
        return keys_with_duplicates_values

    @staticmethod
    def brack_cmd_pipes(cmd):
        '''given a command that have pipe - break it into pipe slide then can be run after'''
        cmd_list = cmd.split("|")

        to_return = []
        next_stage = ""

        last_cmd_index = len(cmd_list) - 1

        index = 0
        for cmd in cmd_list:
            cmdA = next_stage + cmd.strip()
            to_return.append(cmdA)

            if index != last_cmd_index:
                next_stage = cmdA + " | "
            index = +1

        return to_return

    @staticmethod
    def get_the_n_th_field(out, n, separator=None):
        '''like awk {print $1} NOTE = starting from 1 (!)'''

        if separator:
            field_list = out.split(separator)
        else:
            field_list = out.split()

        if n == -1:
            n = len(field_list)

        assert n >= 0, "n<0: out is: {}".format(out)

        assert n <= len(field_list), "in get_the_n_th_field asked for not existing field: " \
                                     "index is higher then the number of field: n is {} out is: {} ".format(n, out)
        return field_list[n - 1]

    @staticmethod
    def get_the_last_field(out, separator=None):
        '''like awk {print $NF}'''
        if separator:
            last_field = out.split(separator)[-1]
        else:
            last_field = out.split()[-1]
        return last_field

    @staticmethod
    def find_dates(text, is_short_date_format=False, search_in_start_of_line=False):
        '''
        This function is used to extract date strings from provide text.

        Symbol references:
        YYYY = four-digit year
          MM = two-digit month (01=January, etc.)
          DD = two-digit day of month (01 through 31) n|Feb|Mar|Apr|May|Jun|Jul|Aug|Sept|Oct|Nov|Dec)hh = two digits of hour (00 through 23) (am/pm NOT allowed)
          mm = two digits of minute (00 through 59)
          ss = two digits of second (00 through 59)
           s = one or more digits representing a decimal fraction of a second
         TZD = time zone designator (Z or +hh:mm or -hh:mm)

        :param text: log lineos
        :param is_short_date_format:
        :param search_in_start_of_line: bool, search date only in start of any line
        :return: date string

       '''

        date_format_dict = OrderedDict([
            # {key: date regex, value: tuple of (full date format, short date format - with the date only)}
            (r'(\d{2}\/\d{2}\/\d{4})', ('%d/%m/%Y', '%d/%m/%Y')), # dd/mm/yyyy
            (r'(\d{2}-\d{2}-\d{4})', ('%d-%m-%Y', '%d-%m-%Y')), # dd-mm-yyyy
            (r'((\d{4}-\d{2}-\d{2})\s(\d{2}:\d{2}:\d{2}))', ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d')), # yyyy-mm-dd hh:mm:ss
            (r'United (\d{1,2}\/\d{1,2}\/\d{4})', ('%d/%f/%Y', '%d/%f/%Y')), # d/m/yyyy
            (r'(\d{1,2}-\d{1,2}-\d{4})', ('%d-%f-%Y', '%d-%f-%Y')), # d-m-yyyy
            (r'\d{1,2}-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-\d{4}::(\d{2}:\d{2}:\d{2})', ('%d-%b-%Y::%H:%M:%S', '%d-%b-%Y')), # 3-Jul-2023::00:00:30
            (r'\d{1,2} (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} (\d{2}:\d{2}:\d{2})', ('%d %b %Y %H:%M:%S', '%d %b %Y')), # 3 Jul 2023 00:00:30
            (r'(January|February|March|April|May|June|July|August|September|October|November|December)(\s+\d{1,2}\W\s\d{4}|\s\d(st|nd|rd|th)\W\s\d{4})', ('%B %d, %Y', '%B %d, %Y')), # Matches full_month_name dd, YYYY or full_month_name dd[suffixes] February 21, 2018
            (r'((Sun|Mon|Tue|Wed|Thur|Fri|Sat)\s(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s(\d{2})\s+(\d{2}:\d{2}:\d{2}\.?\d{6})\s(\d{4}))', ('%a %b %d %H:%M:%S.%f %Y', '%a %b %d')), # Matches abbreviated_day_name abbreviated_month_name dd time yyyy
            (r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2} \d{2}:\d{2}:\d{2}', PythonUtils.TIME_FORMAT_WITH_SINGLE_DIGIT), # Jan 24 21:37:07, Matches abbreviated_month_name dd, YYYY or abbreviated_month_name dd[suffixes], YYYY
            (r'(?:Sun|Mon|Tue|Wed|Thur|Fri|Sat)\s(?:\d{2})\s(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s(?:\d{4})\s(?:\d{2}:\d{2}:\d{2})\s\w+\s+\w+', ('%a %d %b %Y %H:%M:%S %p %Z', '%a %d %b %Y')), # Match example : Tue 24 Sep 2019 09:32:34 AM UTC
            (r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%d')), # Matches ISO 8601 format with time and time zone, yyyy-mm-ddThh:mm:ss
            (r'\d{8}T\d{6}Z', ('%Y%m%dT%H%M%S%Z', '%Y%m%d')), # Matches ISO 8601 format Datetime with timezone, yyyymmddThhmmssZ
            (r'\d{8}T\d{6}(\+|-)\d{4}', ('%Y%m%dT%H%M%S%z', '%Y%m%d')), # Matches ISO 8601 format Datetime with timezone, yyyymmddThhmmss+|-hhmm
            (r'\d{2}\/(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\/\d{4}:(\d{2}:\d{2}:\d{2})', ('%d/%b/%Y:%H:%M:%S', '%d/%b/%Y')), # 03/Jul/2023:00:00:34
            (r'(\d{4}\d{2}\d{2})', ('%Y%m%d', '%Y%m%d')),  # Matches ISO 8601 format yyyymmdd
        ])

        for date_regex, date_format_tuple in list(date_format_dict.items()):
            if search_in_start_of_line:
                date_regex = r"^{date_regex}|\[{date_regex}".format(date_regex=date_regex)
            compiled_date_regex = re.compile(r'\b{}\b'.format(date_regex), re.IGNORECASE | re.MULTILINE)
            find_date = re.search(compiled_date_regex, text)
            if find_date:
                full_date_format = date_format_tuple[0]
                only_date = date_format_tuple[1]
                if is_short_date_format:
                    return find_date.group(0).lstrip("["), full_date_format, only_date
                else:
                    return find_date.group(0).lstrip("["), full_date_format, None
        return None, None, None

    @staticmethod
    def get_cidr_from_string(string):
        assert isinstance(string, six.string_types)
        CIDR_PATTERN = "\\d{1,3}\\.\\d{1,3}.\\d{1,3}.\\d{1,3}\\/\\d{1,2}"
        cidr_array = re.findall(CIDR_PATTERN, string)
        return cidr_array

    @staticmethod
    def key_to_list2str(title, key_to_list):
        lines = [title]
        for key in key_to_list:
            lines.append("{key}:".format(key=key))
            for element in key_to_list[key]:
                lines.append("***" + element)
        return '\n'.join(lines)

    @staticmethod
    def remap_dict_value_to_key(d, value_key_name):
        '''
        :param d: the dict for remapping
        e.g. {'a': {'aa':11}, 'b':{'aa':22}, 'c':{'cc':33}}
        :param value_key_name: the name of the key the dict will be remapped by. e.g.-'aa'
        :return: a new dict remapped by the inner key.
        e.g: {11:'a',22:'b}
        '''
        assert type(d) is dict
        result_dict = {}
        for key in d:
            inner_value = d[key].get(value_key_name)
            if inner_value:
                result_dict[inner_value] = key
        return result_dict

    @staticmethod
    def filter_dict_by_inner_key(d, value_key_name):
        '''
        :param d: the dict for filtering
        e.g. {'a': {'aa':11}, 'b':{'aa':22}, 'c':{'cc':33}}
        :param value_key_name: the name of the key the dict will be remapped by. e.g.-'aa'
        :return: a new dict remapped by the inner key.
        e.g: {'a':11,'b':22}
        '''
        assert type(d) is dict
        result_dict = {}
        for key in d:
            inner_value = d[key].get(value_key_name)
            if inner_value:
                result_dict[key] = inner_value
        return result_dict

    @staticmethod
    def filter_dict_by_values(d, value_key_name, value_filters_list):
        assert type(value_filters_list) is list

        if not len(value_filters_list):
            result = []
        elif len(value_filters_list) == 1:
            result = [item for item in d if item[value_key_name] == value_filters_list[0]]
        else:
            result = [item for item in d if item[value_key_name] in value_filters_list]
        return result

    @staticmethod
    def clear_dict_from_None_valuse(dict_to_clear):
        assert isinstance(dict_to_clear, dict)
        new_dict = {}

        for key in dict_to_clear:
            if not dict_to_clear[key] is None:
                new_dict[key] = dict_to_clear[key]

        return new_dict

    @staticmethod
    def get_object_in_secret_format(obj):
        s = str(obj)
        return s[:len(s) // 4] + "...." + s[3 * (len(s) // 4):]

    @staticmethod
    def is_64_secret(obj):
        is_64_secret = str(obj).endswith("==")
        return is_64_secret

    @staticmethod
    def get_dict_from_xml(s, is_root=True, root=None):
        if is_root:
            root = ET.fromstring(s)
        tag = re.sub(r'{.*}', '', root.tag)
        result_dict = {
            'tag': tag
        }
        val = re.sub(r'\W+', '', root.text) if root.text else None
        if val:
            result_dict['value'] = val
        if root.attrib:
            result_dict['attributes'] = root.attrib
        children = list(root)
        if children:
            result_dict['children'] = []
            for child in children:
                child_dict = PythonUtils.get_dict_from_xml(None, is_root=False, root=child)
                if child_dict:
                    result_dict['children'].append(child_dict)
        return result_dict

    @staticmethod
    def get_dict_from_ini(s):
        config = read_config(s)
        d = {}
        for section in config.sections():
            d[section] = dict(config.items(section))
        d['DEFAULT'] = dict(config.defaults())
        return d

    @staticmethod
    def get_dict_from_space_separated_file(s, custom_delimiter=None):
        '''
        :param s: str
        e.g.
            actual 8388608
            swap_in 0
            swap_out 0
            major_fault 1173
        :param custom_delimiter: str
        :return: dict
        {
           "actual": 8388608,
           "swap_in": 0,
           ...
        }
        '''
        res = {}
        delimiter = custom_delimiter or ' '
        for line in s.splitlines():
            if line and len(line.split(delimiter)) == 2:
                k, v = line.split(delimiter)
                try:
                    v = int(v)
                except:
                    v = v.strip()
                res[k.strip()] = v
        return res

    @staticmethod
    def is_table_data_line(line):
        if not line or bool(re.match(r"[+-]+", line)):
            return False
        return True

    @staticmethod
    def process_ovs_result(result, previous_header):
        if not result:
            k, v = re.split(r'[\s:]+', previous_header.strip(), 1)
            return k, v
        else:
            return previous_header.strip(), result

    @staticmethod
    def ovs_vsctl_parse(s=None, lines=None, indent=0):
        res = {}
        lines_list = s.splitlines() if s else lines
        if len(lines_list) == 0:
            return None
        indented_lines = []
        previous_header = None
        for line in lines_list:
            if bool(re.match(r"^[\s]{" + str(indent) + r"}\w+", line)):
                if previous_header:
                    result = PythonUtils.ovs_vsctl_parse(lines=indented_lines, indent=indent + 4)
                    k, v = PythonUtils.process_ovs_result(result, previous_header)
                    res[k] = v
                    indented_lines = []
                previous_header = line
            elif bool(re.match(r"^[\s]{" + str(indent + 1) + r",}\w+", line)):
                indented_lines.append(line)
        result = PythonUtils.ovs_vsctl_parse(lines=indented_lines, indent=indent + 4)
        k, v = PythonUtils.process_ovs_result(result, previous_header)
        res[k] = v
        return res

    @staticmethod
    def parse_ip_link(s):
        res_list = []
        lines = [_f for _f in re.split(r'\n\d+:\s', s) if _f]
        for line in lines:
            start, end = line.split('>')
            interface_name, interface_status = start.split(': <')
            res = {
                'name': interface_name,
                'status': interface_status
            }
            key_value_lines = list([_f for _f in re.split(r'[\s\n]+', end) if _f])
            if len(key_value_lines):
                for i in range(len(key_value_lines) / 2):
                    res[key_value_lines[i * 2]] = key_value_lines[(i * 2) + 1]
            res_list.append(res)
        return res_list

    @staticmethod
    def parse_brctl_show(s):
        result_list = []
        last_bridge_name = None
        lines = list([_f for _f in s.splitlines() if _f])
        if len(lines):
            for line in lines[1:]:
                sections = list([_f for _f in re.split(r'[\s]', line) if _f])
                if len(sections) > 1:
                    interfaces = [sections[3]] if len(sections) == 4 else []
                    stp_enabled = True if sections[2] == 'yes' else False
                    last_bridge_name = sections[0]
                    res = {
                        'name': last_bridge_name,
                        'id': sections[1],
                        'stp_enabled': stp_enabled,
                        'interfaces': interfaces
                    }
                elif len(sections) == 1:
                    res['interfaces'].append(sections[0])
                result_list.append(res)
        return result_list

    @staticmethod
    def get_dict_from_linux_table(
            s, header_line=0, custom_delimiter=None, custom_header=None):
        '''
        :param custom_header: if you want to replace the table header with yours, put an array os headers
        :param s: str
        Kernel IP routing table
        Destination     Gateway         Genmask         Flags Metric Ref    Use Iface
        169.254.169.254 172.31.0.1      255.255.255.255 UGH   0      0        0 infra-bond
        :param header_line: the number of the header-line. e.g- 1
        :param custom_delimiter: in case the table columns delimiter is not a space. e.g. - '|'
        :return: array of dicts:
        [
            {
                "Use": "0",
                "Iface": "infra-bond",
                "Metric": "0",
                "Destination": "169.254.169.254",
                "Genmask": "255.255.255.255",
                "Flags": "UGH",
                "Ref": "0",
                "Gateway": "172.31.0.1"
            }
        ]
        '''
        DELIMITER = custom_delimiter or " "
        res = []
        lines = list(filter(PythonUtils.is_table_data_line, s.splitlines()))
        if len(lines) < header_line:
            raise InValidStringFormat("string header line number {} does not exist".format(header_line))
        if len(lines) == header_line:
            return res
        headers = custom_header or list([_f for _f in lines[header_line].split(DELIMITER) if _f])
        headers = [header.strip() for header in headers]
        for line in lines[header_line + 1:]:
            d = {}
            values = list([_f for _f in line.split(DELIMITER) if _f])
            for i in range(len(headers)):
                if len(values) >= i:
                    d[headers[i]] = values[i].strip()
            res.append(d)
        return res

    @staticmethod
    def _preprocess_yaml_string(yaml_str):
        # yaml.safe_load() is sensitive for some special chars at the beginning of the value.
        # This function handles this and wraps such values in "" to prevent failures in loading the yaml.
        # For example:  admin_password: *abcd123!! --> admin_password: "*abcd123!!"
        lines = yaml_str.splitlines()
        special_chars = '*&[]%,:\\{}-|'
        modified_lines = []

        for i in range(len(lines)):
            line = lines[i]
            if ': ' in line:
                key, value = line.split(':', 1)
                value = value.strip()

                # Handle case of multi-lines value by using block scalar (|) notation.
                # This allows to include multi-line content in a YAML file while maintaining readability and structure.
                if PythonUtils._is_multiline_value(i, lines):
                    indent = PythonUtils._get_line_indentation(lines[i + 1])
                    modified_lines.append('{}: |'.format(key))
                    modified_lines.append(indent + value)
                    continue

                if value and value[0] in special_chars:
                    line = '{}: "{}"'.format(key, value)
            modified_lines.append(line)
        return '\n'.join(modified_lines)

    @staticmethod
    # Determine if a value is multi-line - by checking if the next line is not in format of key-value or a list
    # element in the Yaml.
    # Example of multi-line value:
    #       ethtool_opts: --config-ntuple $DEVICE rx-flow-hash udp4 sdfn; -G $DEVICE rx
    #         2048 tx 2048
    def _is_multiline_value(i, lines):
        if i + 1 < len(lines) and not lines[i + 1].lstrip().startswith('- '):
            if ': ' not in lines[i+1] and not lines[i + 1].endswith(':'):
                return True
        return False

    @staticmethod
    def _get_line_indentation(line):
        num_of_indent = len(line) - len(line.lstrip())
        indent = ' ' * num_of_indent
        return indent

    @staticmethod
    def yaml_safe_load(yaml_str, file_path=''):
        file_info = ''
        if file_path:
            file_info = " in path '{}'".format(file_path)
        try:
            yaml_dict = yaml.safe_load(yaml_str)
        except (ParserError, ScannerError):
            try:
                processed_str = PythonUtils._preprocess_yaml_string(yaml_str)
                yaml_dict = yaml.safe_load(processed_str)
            except (ParserError, ScannerError) as e:
                raise UnExpectedSystemOutput("", "", str(e), "Failed to load yaml{} after preprocessing its content in "
                                             "PythonUtils._preprocess_yaml_string(yaml_str) method.\nCheck if there "
                                             "is still something wrong in the yaml format after the preprocessing.".format(file_info))
        except Exception as e:
            raise UnExpectedSystemOutput("", "yaml.safe_load(yaml_str)", str(e), "Failed to run yaml.safe_load("
                                                                                 "yaml_str){} with error which is different"
                                                                                 " from ParserError and ScannerError".format(file_info))
        if type(yaml_dict) is str:
            raise Exception('Not a yaml format')
        return yaml_dict

    @staticmethod
    def get_dict_from_string(s, string_format, header_line=0, custom_delimiter=None, custom_header=None):
        try:
            if string_format == 'json':
                return json.loads(s)
            elif string_format == 'yaml':
                return PythonUtils.yaml_safe_load(s)
            elif string_format == 'ini':
                return PythonUtils.get_dict_from_ini(s)
            elif string_format == 'xml':
                return PythonUtils.get_dict_from_xml(s)
            elif string_format == 'space':
                return PythonUtils.get_dict_from_space_separated_file(s, custom_delimiter=custom_delimiter)
            elif string_format == 'linux_table':
                return PythonUtils.get_dict_from_linux_table(
                    s, header_line=header_line, custom_delimiter=custom_delimiter, custom_header=custom_header)
            else:
                return s
        except Exception as e:
            raise InValidStringFormat(
                'Cannot convert the file from the required format-{} to dict.\n{}'.format(string_format, str(e)))

    @staticmethod
    def is_string_match_pattern(s, pattern):
        return bool(re.match(pattern, s))

    @staticmethod
    def is_string_contains_pattern(s, pattern):
        return bool(re.findall(pattern, s))

    @staticmethod
    def get_value_by_path_from_nested_dict(input_dict, nested_key):
        '''
        Retrieve a value by path on nested dictionary
        :param input_dict: dictionary
        :param nested_key: key path as: ['container_limit', 'limits', 'cpu']
        :return: value of given path on dictionary
        '''
        internal_dict_value = input_dict
        for k in nested_key:
            internal_dict_value = internal_dict_value.get(k, None)
            if internal_dict_value is None:
                return None
        return internal_dict_value

    @staticmethod
    def get_value_from_nested_dict(search_dict, key):
        '''
        Takes a dict with nested lists and dicts,
        and searches all dicts for a key of the field provided.
        '''
        keys_found = []

        for k, v in list(search_dict.items()):
            if k == key:
                keys_found.append(v)

            elif isinstance(v, dict):
                results = PythonUtils.get_value_from_nested_dict(v, key)
                for result in results:
                    keys_found.append(result)

            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        more_results = PythonUtils.get_value_from_nested_dict(item, key)
                        for another_result in more_results:
                            keys_found.append(another_result)
        return keys_found

    @staticmethod
    def replace_special_chars(input_string):
        specialChars = "!#$%^&*()[]<>}{\"/,"
        processed_string = input_string
        for specialChar in specialChars:
            processed_string = processed_string.replace(specialChar, '')
            processed_string = processed_string.strip()
        return processed_string

    @staticmethod
    def get_timezone_from_date (datetimestring):
        array  = datetimestring.split()
        timezone = array[4].strip()
        return timezone

    @staticmethod
    def extract_zip_file(zip_path, extract_directory_path):
        zipref = zipfile.ZipFile(zip_path, 'r')
        zipref.extractall(extract_directory_path)
        zipref.close()

    @staticmethod
    def convert_str_with_unit_to_mega(value_with_unit):
        kb = ['KB', 'KILOBYTES', 'KHZ']
        mb = ['MB', 'MEGABYTES', 'MHZ', 'MT/S']
        gb = ['GB', 'GIGABYTES', 'GHZ', 'GB/S']
        tb = ['TB', 'TERABYTES']
        multiplication_factor = 1000
        multiplication_factor_of_1024 = 1024
        bytes_units = ['KB', 'MB', 'GB', 'TB']
        hertz_units = ['KHZ', 'MHZ', 'MT/S', 'GHZ']
        returned_unit = '_in_mb'

        splitted_value_unit = re.findall(r'(\d+\.?\d+|[A-Za-z]+\/?[A-Za-z]+)', value_with_unit)
        actual_size = float(splitted_value_unit[0])
        try:
            unit_size = splitted_value_unit[1].upper()
            multiplication_factor = multiplication_factor_of_1024 if unit_size in bytes_units else 1000
            returned_unit = '_in_mhz' if unit_size in hertz_units else '_in_mb'
        except IndexError:
            return int(round(actual_size / multiplication_factor ** 2)), returned_unit
        if unit_size in kb:
            return int(round(actual_size / multiplication_factor)), returned_unit
        elif unit_size in mb:
            return int(round(actual_size)), returned_unit
        elif unit_size in gb:
            return int(round(actual_size * multiplication_factor)), returned_unit
        elif unit_size in tb:
            return int(round(actual_size * multiplication_factor ** 2)), returned_unit

    @staticmethod
    def convert_str_with_unit_to_bytes(value_with_unit):
        units_multiplication_factor = {'B': 1, 'KiB': 1024, 'MiB': 1024**2, 'GiB': 1024**3, 'TiB': 1024**4, 'KB': 1024,
                                       'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
        actual_size_list = re.findall(r'[0-9.]+', value_with_unit)
        unit_size_list = re.findall(r'[a-zA-Z]+', value_with_unit)
        assert len(actual_size_list) == 1, "Expected 'value_with_unit contains' alphabets"
        assert len(unit_size_list) == 1, "Expected 'value_with_unit contains' numbers"
        assert units_multiplication_factor.get(unit_size_list[0]), "{} is not key in {}".format(unit_size_list[0], units_multiplication_factor)
        return float(actual_size_list[0]) * units_multiplication_factor[unit_size_list[0]]

    @staticmethod
    def std(numbers_list):
        # Standard deviation of list
        mean = sum(numbers_list) / float(len(numbers_list))
        variance = sum([((x - mean) ** 2) for x in numbers_list]) / len(numbers_list)

        return variance ** 0.5


    @staticmethod
    def get_lines_after_label(lines_str, label):
        label_index = -1
        lines_list = lines_str.splitlines()
        for index, row in enumerate(lines_list):
            if label in row:
                label_index = index
                break
        to_return = lines_list[index :] if label_index != -1 else []
        return "\n".join(to_return)

    @staticmethod
    def user_input_yes_no_query(question):
        msg = "{} [y/n]\n".format(question)
        while True:
            try:
                return PythonUtils.strtobool(get_user_input(msg).lower())
            except ValueError:
                print("Please respond with 'y' or 'n'.\n")

    @staticmethod
    def strtobool(val):
        val = val.lower()

        if val in ('y', 'yes', 't', 'true', 'on', '1'):
            return True

        elif val in ('n', 'no', 'f', 'false', 'off', '0'):
            return False

        else:
            raise ValueError("Invalid truth value: {}".format(val))


    @staticmethod
    def get_unique_entries(list1):
        unique_list = list(set(list1))
        return unique_list
    
    @staticmethod
    def get_node_list_from_selectors(output):
        nodenames = ""
        node_aray = output.splitlines()
        for line in node_aray:
            each_line = line
            nodename = each_line.split(" ")
            nodenames = str(nodenames + "|" + nodename[0]).strip()
        return nodenames

    @staticmethod
    def convert_dict_to_str_sort_keys(d):
        return json.dumps(d, sort_keys=True)

    @staticmethod
    def is_ipv6(ip):
        try:
            ipaddress.IPv6Address(to_unicode(ip))# Convert to Unicode for Python 2.7
            return True
        except ipaddress.AddressValueError:
            return False

    @staticmethod
    def set_to_ipv6_format(ip):
        # Set to IPv6 format ensure cases as like 2a00:8a00:4000:a8e:3::/119 equals to 2A00:8A00:4000:0A8E:3::/119
        return socket.inet_pton(socket.AF_INET6, ip)

    @staticmethod
    def get_class_name(func, *args):
        if hasattr(func, '__qualname__'):
            return func.__qualname__.split(".")[0]

        if hasattr(func, "im_class"):
            return func.im_class.__name__

        if isinstance(func, staticmethod):
            for cls in sys.modules[__name__].__dict__.values():
                if inspect.isclass(cls):
                    for name, m in cls.__dict__.items():
                        if isinstance(m, staticmethod) and m.__get__(None, cls) is func:
                            return cls.__name__

        if args and isinstance(args[0], (type, object)):
            return args[0].__name__ if isinstance(args[0], type) else args[0].__class__.__name__
        return None

