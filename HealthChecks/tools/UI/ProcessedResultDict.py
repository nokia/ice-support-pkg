from __future__ import absolute_import
import copy
import json
import re

#from __builtin__ import enumerate
from tools.python_versioning_alignment import enumerate


from collections import OrderedDict
import tools.user_params
from tools.global_enums import Objectives
from six.moves import range


class ResultKeys:
    HEADERS = "headers"
    SEVERITY = "severity"
    REMARKS = "remarks"
    EXCEPTION = "exception"
    VALIDATION_LOG = "validation_log"
    TIME = "time"
    DESCRIPTION_TITLE = "description_title"
    HOST_IP = "host_ip"
    BLOCKING_TAGS = "blocking_tags"
    SYSTEM_INFO = "system_info"
    IS_HIGHLIGHTED_INFO = "is_highlighted_info"
    RUN_TIME = "run_time"
    PASS = "pass"
    BASH_CMD_LINES = "bash_cmd_lines"
    TABLE_SYSTEM_INFO = "table_system_info"
    TABLE = "table"
    PRINT_HOST_AS_TITLE = 'print_host_as_title'
    DOCUMENTATION_LINK = "documentation_link"
    CMD_INFO = "cmd_info"
    DESCRIBE_MSG = "describe_msg"


class SectionDomain:
    SYSTEM_INFO = 'System info'
    DEEP_INFO = 'Deep info'
    ZABBIX_VALIDATIONS = 'Zabbix Validations'
    VICTORIA_VALIDATIONS = 'Victoria Metrix Validations'
    ALL_VALIDATIONS = 'All Validations'
    FAILED_VALIDATIONS_BY_HOST = 'Failed Validations By Host'
    FAILED_VALIDATIONS_BY_ISSUE = 'Failed Validations By Issue'
    FILE_TRACKER = 'File tracker'
    OPERATIONS_TIMELINE = 'Operations timeline'
    BLUEPRINT = 'Blueprint'
    VMS = 'vms'

    @staticmethod
    def is_informator(domain):
        return domain == SectionDomain.DEEP_INFO

    @staticmethod
    def is_zabbix_validation(domain):
        return domain == SectionDomain.ZABBIX_VALIDATIONS

    @staticmethod
    def is_system_info(domain):
        return domain == SectionDomain.SYSTEM_INFO

    @staticmethod
    def is_file_tracker(domain):
        return domain == SectionDomain.FILE_TRACKER

    @staticmethod
    def is_operation_timeline(domain):
        return domain == SectionDomain.OPERATIONS_TIMELINE

    @staticmethod
    def is_blueprint(domain):
        return domain == SectionDomain.BLUEPRINT

    @staticmethod
    def is_vms(domain):
        return domain == SectionDomain.VMS

    @staticmethod
    def is_validator(domain):
        return domain in [SectionDomain.ALL_VALIDATIONS,
                          SectionDomain.FAILED_VALIDATIONS_BY_HOST,
                          SectionDomain.FAILED_VALIDATIONS_BY_ISSUE]

    @staticmethod
    def is_failed(domain):
        return domain in [
            SectionDomain.FAILED_VALIDATIONS_BY_HOST,
            SectionDomain.FAILED_VALIDATIONS_BY_ISSUE,
        ]

    @staticmethod
    def get_all():
        if tools.user_params.limited_output:
            return [SectionDomain.SYSTEM_INFO,
                    SectionDomain.FAILED_VALIDATIONS_BY_ISSUE]

        return [SectionDomain.SYSTEM_INFO,
                SectionDomain.FAILED_VALIDATIONS_BY_ISSUE,
                SectionDomain.FAILED_VALIDATIONS_BY_HOST,
                SectionDomain.ZABBIX_VALIDATIONS,
                SectionDomain.VICTORIA_VALIDATIONS,
                SectionDomain.ALL_VALIDATIONS,
                SectionDomain.DEEP_INFO,
                SectionDomain.FILE_TRACKER,
                SectionDomain.OPERATIONS_TIMELINE,
                SectionDomain.BLUEPRINT,
                SectionDomain.VMS]

    @staticmethod
    def get_info_section_domains():
        return [SectionDomain.SYSTEM_INFO,
                SectionDomain.DEEP_INFO,
                SectionDomain.ZABBIX_VALIDATIONS,
                SectionDomain.VICTORIA_VALIDATIONS,
                SectionDomain.BLUEPRINT]


class ProcessedResultDict:
    def __init__(self, results_dict):
        self.results_dict = copy.deepcopy(results_dict)
        self.sections_dict = {
            SectionDomain.SYSTEM_INFO: {},
            SectionDomain.DEEP_INFO: {},
            SectionDomain.ALL_VALIDATIONS: {},
            SectionDomain.FAILED_VALIDATIONS_BY_HOST: {},
            SectionDomain.ZABBIX_VALIDATIONS: {},
            SectionDomain.VICTORIA_VALIDATIONS: {},
            SectionDomain.FAILED_VALIDATIONS_BY_ISSUE: {},
            SectionDomain.FILE_TRACKER: {},
            SectionDomain.OPERATIONS_TIMELINE: {},
            SectionDomain.BLUEPRINT: {},
            SectionDomain.VMS: {}
        }
        self.result_count_per_section = {}
        self.process_result()

    # ----------------------------------

    def _find_operation_data(self, unique_name):

        to_return = {}
        for flow in self.results_dict:
            details = flow["details"]
            for host_name in details:
                if details[host_name].get(unique_name):
                    # print '----found---'
                    result = details[host_name].get(unique_name)
                    to_return[host_name] = result
        return to_return

    def get_specific_table_info(self, unique_name):
        host_to_results_dict = self._find_operation_data(unique_name)
        # print 'host_to_results_dict',host_to_results_dict
        expiry_table_row_Per_host = {}
        expiry_table_headers = []
        for host in host_to_results_dict:
            expiry_table_row_Per_host[host] = host_to_results_dict[host].get(ResultKeys.TABLE_SYSTEM_INFO, {}).get(ResultKeys.TABLE)
            expiry_table_headers = host_to_results_dict[host].get(ResultKeys.TABLE_SYSTEM_INFO, {}).get(ResultKeys.HEADERS)
        return expiry_table_headers, expiry_table_row_Per_host

    # ----------------------------------

    def process_result(self):
        self.pre_process_dict()
        for flow in self.results_dict:
            flow_name = flow.get("command_name")
            details = flow["details"]
            for host_name in details:
                for item in details[host_name]:
                    result = details[host_name][item]
                    validation_title = result.get(ResultKeys.DESCRIPTION_TITLE)
                    result_domain_sections_list = ProcessedResultDict.get_result_domain_sections(result, item)
                    for result_domain_section in result_domain_sections_list:
                        section, sub_section = ProcessedResultDict.get_section_and_sub_section_keys(
                            result_domain_section, validation_title, host_name, flow_name)
                        row = ProcessedResultDict.get_result_domain_section_row(
                            result, host_name, result_domain_section)
                        self.add_row_to_section_sub_section(
                            result_domain_section, section, sub_section, row)
                        self.update_results_count(
                            result_domain_section, section, result)

    def get_information_validation_to_link_list(self, section_domain, section, sub_section, rows_list):
        information_validation_to_link_list = []
        unique_names_list = self.get_unique_names_list(section_domain, section, sub_section, rows_list)
        for i, unique_name in enumerate(unique_names_list):
            information_validation_unique_name = None
            inner_tab = False
            if not section_domain in SectionDomain.get_info_section_domains():
                host_name = self.get_host_name(section_domain, section, sub_section, rows_list[i])
                information_validation = self.get_information_validator(
                    validator_unique_name=unique_name, host_name=host_name)

                if information_validation:
                    information_validation_key = list(information_validation.keys())[0]
                    information_validation_value = list(information_validation.values())[0][host_name]
                    information_validation_unique_name = information_validation_key
                    domain_sections = self.get_result_domain_sections(information_validation_value,
                                                                      information_validation_key)
                    if SectionDomain.ZABBIX_VALIDATIONS in domain_sections \
                            or SectionDomain.VICTORIA_VALIDATIONS in domain_sections:
                        inner_tab = True
            information_validation_to_link_list.append((information_validation_unique_name, inner_tab))
        return information_validation_to_link_list

    def get_unique_names_list(self, section_domain, section, sub_section, rows_list, concatenate_host_name=False):
        unique_names_list = []
        for i, row_cells in enumerate(rows_list):
            unique_name = self.get_unique_name(section_domain=section_domain, section=section, row_cells=row_cells)
            if concatenate_host_name:
                unique_name += "_{}".format(self.get_host_name(section_domain, section, sub_section, rows_list[i]))
            unique_names_list.append(unique_name)
        return unique_names_list


    def get_information_validator(self, validator_unique_name, host_name):
        dict_info = {}
        for flow in self.results_dict:
            details = flow["details"]
            if details.get(host_name):
                for unique_name in details[host_name]:
                    if unique_name == "info_" + validator_unique_name:
                        domain_sections_list = self.get_result_domain_sections(details[host_name][unique_name],
                                                                               unique_name)
                        if domain_sections_list and \
                                set(domain_sections_list).issubset(set(SectionDomain.get_info_section_domains())):
                            dict_info.setdefault(unique_name, {})
                            dict_info[unique_name].setdefault(host_name, details[host_name][unique_name])
        return dict_info

    def get_host_name(self, section_domain, section, sub_section, row):
        if section_domain == SectionDomain.FAILED_VALIDATIONS_BY_HOST:
            return section
        if section_domain in [SectionDomain.FAILED_VALIDATIONS_BY_ISSUE]:
            return row[0]
        return sub_section

    def get_unique_name(self, section_domain, section, row_cells):
        if section_domain in [SectionDomain.FAILED_VALIDATIONS_BY_ISSUE]:
            validation_description = section
        else:
            validation_description = row_cells[0]
        for flow in self.results_dict:
            details = flow["details"]
            for host_name in details:
                for unique_name in details[host_name]:
                    result = details[host_name][unique_name]
                    if result.get(ResultKeys.DESCRIPTION_TITLE) == validation_description:
                        if (not SectionDomain.is_validator(section_domain) and unique_name.startswith("info_")) or \
                                (SectionDomain.is_validator(section_domain) and (not unique_name.startswith("info_"))):
                            return unique_name
        assert False, "Unknown unique name for:{}, section:{}".format(validation_description, section_domain)

    @staticmethod
    def get_section_and_sub_section_keys(result_domain_section, validation_title, host_name, flow_name):
        if result_domain_section == SectionDomain.FAILED_VALIDATIONS_BY_HOST:
            return host_name, flow_name
        if result_domain_section in [SectionDomain.FAILED_VALIDATIONS_BY_ISSUE]:
            return validation_title, ""
        else:
            return flow_name, host_name

    @staticmethod
    def get_result_domain_section_row(result, host_name, domain_section):
        assert domain_section in SectionDomain.get_all()
        if SectionDomain.is_validator(domain_section):
            return ProcessedResultDict.get_validation_row(result, host_name, domain_section)
        else:
            return ProcessedResultDict.get_informator_row(result)

    @staticmethod
    def get_result_domain_sections(result, result_key):
        domain_sections = []
        if ResultKeys.SYSTEM_INFO in result or ResultKeys.TABLE_SYSTEM_INFO in result:
            table_system_info = result.get(ResultKeys.TABLE_SYSTEM_INFO, {})
            if result.get(ResultKeys.SYSTEM_INFO) or table_system_info.get(ResultKeys.TABLE)\
                    or table_system_info.get(ResultKeys.REMARKS):
                if result.get(ResultKeys.IS_HIGHLIGHTED_INFO) is True:
                    domain_sections.append(SectionDomain.SYSTEM_INFO)
                elif 'zabbix' in result_key:
                    domain_sections.append(SectionDomain.ZABBIX_VALIDATIONS)
                elif 'validate_victoria_metrics_does_not_have_alarms' in result_key:
                    domain_sections.append(SectionDomain.VICTORIA_VALIDATIONS)
                elif 'file_tracker' in result_key:
                    domain_sections.append(SectionDomain.FILE_TRACKER)
                elif 'timing' in result_key:
                    domain_sections.append(SectionDomain.OPERATIONS_TIMELINE)
                elif 'blueprint' in result_key:
                    domain_sections.append(SectionDomain.BLUEPRINT)
                elif 'vms' in result_key:
                    domain_sections.append(SectionDomain.VMS)
                else:
                    domain_sections.append(SectionDomain.DEEP_INFO)
        else:
            domain_sections.append(SectionDomain.ALL_VALIDATIONS)
            if result.get(ResultKeys.PASS) not in [True, 'True']:
                domain_sections.append(SectionDomain.FAILED_VALIDATIONS_BY_HOST)
                domain_sections.append(SectionDomain.FAILED_VALIDATIONS_BY_ISSUE)
        return list(set(domain_sections).intersection(set(SectionDomain.get_all())))

    def pre_process_dict(self):
        flow_count = len(self.results_dict)
        for i in range(flow_count):
            for host_name in self.results_dict[i]["details"]:
                for item in self.results_dict[i]["details"][host_name]:
                    if 'zabbix' in item:
                        del self.results_dict[i]["details"][host_name][item][ResultKeys.BASH_CMD_LINES]

    def add_row_to_section_sub_section(self, section_domain, section, sub_section, row):
        assert section_domain in self.sections_dict
        if not self.sections_dict[section_domain].get(section):
            self.sections_dict[section_domain][section] = {}
        if not self.sections_dict[section_domain][section].get(sub_section):
            self.sections_dict[section_domain][section][sub_section] = []
        self.sections_dict[section_domain][section][sub_section].append(row)

    def update_results_count(self, section_domain, section, result_row):
        is_passed = result_row.get(ResultKeys.PASS)
        if not self.result_count_per_section.get(section_domain):
            self.result_count_per_section[section_domain] = {}
        if not self.result_count_per_section[section_domain].get(section):
            self.result_count_per_section[section_domain][section] = {
                "Succeeded": 0,
                "Failed": 0,
                "No Data": 0
            }
        if is_passed in [True, 'True']:
            self.result_count_per_section[section_domain][section]["Succeeded"] += 1
        elif is_passed in [False, 'False']:
            self.result_count_per_section[section_domain][section]["Failed"] += 1
        else:
            self.result_count_per_section[section_domain][section]["No Data"] += 1

    @staticmethod
    def get_role_host_map_rows_list(role_host_map_dict):
        rows_list = []
        for role in role_host_map_dict:
            if role in [Objectives.ONE_CONTROLLER, Objectives.ONE_MASTER, Objectives.ONE_MANAGER,
                        Objectives.ONE_STORAGE, Objectives.ICE_CONTAINER]:
                continue
            role_members_list = "\n".join(role_host_map_dict[role])
            role_members_count = len(role_host_map_dict[role])
            connected_members = [host for host in role_host_map_dict[role] if 'Not Connected' not in host]
            connected_count = len(connected_members)
            statistics_str = "{connected}/{all}".format(connected=connected_count, all=role_members_count)
            rows_list.append([role, role_members_count, statistics_str, role_members_list])
        return rows_list

    @staticmethod
    def get_cmd_lines_str(cmd_lines):
        if cmd_lines and len(cmd_lines):
            out = ['Cmd Lines:']
            for line in cmd_lines:
                out.append('$ {}'.format(line))
            return "\n".join(out)
        return ""

    @staticmethod
    def get_validation_row(result, host_name, domain_section):
        details = "Time : {}\n".format(result.get(ResultKeys.TIME))
        if result.get(ResultKeys.DOCUMENTATION_LINK):
            details += "Description link : {}\n".format(result.get(ResultKeys.DOCUMENTATION_LINK))
        if result.get(ResultKeys.CMD_INFO):
            details += "Info : {}\n".format(result.get(ResultKeys.CMD_INFO))
        if result.get(ResultKeys.DESCRIBE_MSG):
            details += "Message : {}\n".format(result.get(ResultKeys.DESCRIBE_MSG))
        details += ProcessedResultDict.get_cmd_lines_str(result.get(ResultKeys.BASH_CMD_LINES))
        if domain_section in [SectionDomain.FAILED_VALIDATIONS_BY_ISSUE]:
            left_column = host_name
        else:
            left_column = result.get(ResultKeys.DESCRIPTION_TITLE)
        row = [
            left_column,
            result.get(ResultKeys.PASS),
            result.get(ResultKeys.SEVERITY),
            details
        ]
        return row

    @staticmethod
    def get_informator_row(result):
        details = ""
        if result.get(ResultKeys.CMD_INFO):
            details += "Cmd Info : {}\n".format(result.get(ResultKeys.CMD_INFO))
        if result.get(ResultKeys.DOCUMENTATION_LINK):
            details += "Description link : {}\n".format(result.get(ResultKeys.DOCUMENTATION_LINK))
        if result.get(ResultKeys.EXCEPTION):
            details += "informator was not completed"
        try:
            info = json.dumps(result.get(ResultKeys.SYSTEM_INFO), indent=4)
        except:
            info = result.get(ResultKeys.SYSTEM_INFO)
        if len(info) > 300:
            details += "\nSystem Info : {} ".format(info)
            info = "information is too long. click details section to read it"
        row = [
            result.get(ResultKeys.DESCRIPTION_TITLE),
            info,
            details
        ]
        return row

    @staticmethod
    def get_header(section_domain, tab_name=""):
        if SectionDomain.is_informator(section_domain) or SectionDomain.is_zabbix_validation(section_domain):
            return ['informator Title', 'Information', 'More Details']
        if SectionDomain.is_system_info(section_domain):
            return []
        if SectionDomain.is_file_tracker(section_domain):
            if tab_name == 'Kubernetes resources':
                return ['estimated modify timestamp', 'resource name', 'resource type', 'namespace',
                        'is resource exist', 'changes']
            if tab_name == "folders":
                return ['modify timestamp', 'host name', 'folder path', 'file name', 'added / deleted']
            if tab_name == 'commands':
                return ['estimated modify timestamp', 'host name', 'command', 'changes']
            return ['modify timestamp', 'host name', 'full path', 'is file exist', 'changes']
        if SectionDomain.is_operation_timeline(section_domain):
            return ['start_time', 'end_time', 'name', 'status', 'host_name', 'log_path']
        if SectionDomain.is_blueprint(section_domain):
            return ['start_time', 'end_time', 'name', 'status', 'host_name', 'log_path']
        if SectionDomain.is_vms(section_domain):
            return ['start_time', 'end_time', 'name', 'status', 'host_name', 'log_path']
        if SectionDomain.is_validator(section_domain):
            if section_domain in [SectionDomain.FAILED_VALIDATIONS_BY_ISSUE]:
                left_column_name = 'Host Name'
            else:
                left_column_name = 'Validation Title'
            return [left_column_name, 'Is Passed', 'Severity', 'More Details']
        assert False, "No header for {} result type".format(section_domain)

    def get_rows_list(self, section_domain):
        assert section_domain in self.sections_dict, "no result dict implementation for section domain {}".format(
            section_domain)
        return self.sections_dict.get(section_domain)

    def create_info_dict(self, info_section, predefined_unique_names_list=None):
        info_dict = OrderedDict()
        predefined_info_unique_names_list = None
        if predefined_unique_names_list:
            predefined_info_unique_names_list = ["info_{}".format(item) for item in predefined_unique_names_list]
        for flow in self.results_dict:
            details = flow["details"]
            for host_name in details:
                for unique_name in details[host_name]:
                    result = details[host_name][unique_name]
                    if info_section in ProcessedResultDict.get_result_domain_sections(result, unique_name):
                        info_dict = self.insert_into_info_dict(info_dict, unique_name, host_name, result)
        if predefined_info_unique_names_list:
            ordered_info_dict = OrderedDict([(unique_name, info_dict.pop(unique_name))
                                             for unique_name in predefined_info_unique_names_list
                                             if info_dict.get(unique_name)])
            ordered_info_dict.update(info_dict)
        else:
            ordered_info_dict = info_dict
        return ordered_info_dict

    def insert_into_info_dict(self, info_dict, unique_name, host_name, result):
        info_dict.setdefault(unique_name, {})
        info_dict[unique_name].setdefault(host_name, {})
        info_dict[unique_name][host_name][ResultKeys.SYSTEM_INFO] = result.get(ResultKeys.SYSTEM_INFO)
        info_dict[unique_name][host_name][ResultKeys.DESCRIPTION_TITLE] = result.get(ResultKeys.DESCRIPTION_TITLE)
        info_dict[unique_name][host_name][ResultKeys.DOCUMENTATION_LINK] = result.get(ResultKeys.DOCUMENTATION_LINK)
        table_system_info = result.get(ResultKeys.TABLE_SYSTEM_INFO, {})
        info_dict[unique_name][host_name][ResultKeys.PRINT_HOST_AS_TITLE] = table_system_info.get(ResultKeys.PRINT_HOST_AS_TITLE)
        if table_system_info.get(ResultKeys.TABLE):
            info_dict[unique_name][host_name][ResultKeys.TABLE_SYSTEM_INFO] = {}
            info_dict[unique_name][host_name][ResultKeys.TABLE_SYSTEM_INFO][ResultKeys.TABLE] = \
                table_system_info.get(ResultKeys.TABLE)
            info_dict[unique_name][host_name][ResultKeys.TABLE_SYSTEM_INFO][ResultKeys.HEADERS] = \
                table_system_info.get(ResultKeys.HEADERS)
            if table_system_info.get(ResultKeys.REMARKS):
                info_dict[unique_name][host_name][ResultKeys.TABLE_SYSTEM_INFO][ResultKeys.REMARKS] = \
                    table_system_info.get(ResultKeys.REMARKS)
        else:
            if table_system_info.get(ResultKeys.REMARKS):
                info_dict[unique_name][host_name][ResultKeys.SYSTEM_INFO] += \
                    "\n{}".format(table_system_info.get(ResultKeys.REMARKS))
        return info_dict

    @staticmethod
    def get_product_info_row_and_header(version, sub_version, build, bcmt_build, deployment_type, installed_hotfix, cluster_name):
        header = ['Product', 'Version']
        version_str = str(version) + sub_version if sub_version else version
        version_str = version_str + '\nbuild {}'.format(build) if build else version_str
        version_str = version_str + '\nBCMT build {}'.format(bcmt_build) if bcmt_build else version_str
        row = [deployment_type, version_str]
        if cluster_name:
            header.append('Cluster Name')
            row.append(cluster_name)

        if installed_hotfix is not None:
            header.append('Hotfix')
            if installed_hotfix == {}:
                row.append('No hotfix is installed')
                return header, row
            installed_hotfix_str = ""
            for hotfix_name in installed_hotfix:
                date = re.sub(r'[T]|\.\d{3,}', " ", installed_hotfix.get(hotfix_name, ""))
                # regex example : 21-07-2020T12:30.09865 -> 21-07-2020 12:30
                # removes the character "T" or dot+three or more digits
                if date:
                    installed_hotfix_str += "{}:\n{}\n\n".format(hotfix_name, date)
                else:
                    installed_hotfix_str += "{}\n\n".format(hotfix_name)
            row.append(installed_hotfix_str)
        return header, row
