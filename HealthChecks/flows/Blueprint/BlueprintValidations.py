from __future__ import absolute_import
from __future__ import print_function
# collect HW and Firmware data and:
# - use it as information
# compare with blue - show table of Blueprint values vs real values and check is uniform for each roll kind
import collections
try:
    from collections.abc import Hashable
except ImportError:
    from collections import Hashable
import os
from copy import deepcopy

import six

from HealthCheckCommon.validator import InformatorValidator
import tools.user_params
from flows.Blueprint.BlueprintDataCollectors import *
from flows.Blueprint.IPMIBlueprintDataCollectors import *
from flows.Blueprint.NUMABlueprintDataCollectors import *
from flows.Blueprint.DiskBlueprintDataCollectors import *
from flows.Blueprint.NICBlueprintDataCollectors import *
from flows.Blueprint.CsfAddOnBlueprintDataCollectors import *
from flows.Blueprint.BlueprintInventory import BlueprintInventory
from collections import OrderedDict
try:
    from collections.abc import Hashable
except ImportError:
    from collections import Hashable
import json
import tools.sys_parameters as gs
from flows.Blueprint.RaidControllerBlueprintDataCollector import RaidControllerProduct, RaidControllerFirmware
from flows.Blueprint.spec.blueprint_from_system_out_to_json import BLUEPRINT_CUSTOMERS_OUT_FOLDER_PATH
from flows.Blueprint.stable_marriage_problem import StableMarriageProblem


def get_list_of_hw_data_collectors():
    data_collectors_list = [
        NICPortsAmount,
        NICVendor,
        NICModel,
        NICPortsNames,
        NICSpeed,
        ProcessorCurrentFrequency,
        ProcessorType,
        CpuIsolated,
        MemoryTotalSize,
        MemorySize,
        MemoryType,
        MemorySpeed,
        DiskType,
        DiskModel,
        DiskVendor,
        DiskSize,
        DiskInterfaceType,
        RaidControllerProduct,
        NumaNICs,
        NumaCpus,
        NumaSizeMemory,
        OperatingSystemDiskName,
        OperatingSystemDiskType,
        OperatingSystemDiskSize,
        NICBufferCollector
            ]  # add list of HW collectors to here
    return data_collectors_list


def get_list_of_fw_data_collectors():
    data_collectors_list = [
        OperatingSystemVersion,
        KernelVersion,
        BIOSVersion,
        BIOSFirmware,
        BIOSRevision,
        BIOSReleaseDate,
        IPMIControllerManagerFirmware,
        IPMIControllerManagerVersion,
        NICVersion,
        NICFirmware,
        NICDriver,
        RedfishVersion,
        RaidControllerFirmware
    ]  # add list of FW collectors to here
    if gs.get_deployment_type() == Deployment_type.NCS_OVER_BM:
        data_collectors_list.extend([CburVersion, BtelVersion, CitmVersion, HarborVersion, IstioVersion, FalcoVersion])
    return data_collectors_list


class ValidateBlueprint(InformatorValidator):
    data_pool = {}
    objective_hosts = [Objectives.UC, Objectives.ONE_MANAGER]

    BLUEPRINT_SPEC_DIR_PATH = 'flows/Blueprint/spec'
    BLUEPRINT_JSON_PATH = os.path.join(BLUEPRINT_SPEC_DIR_PATH, 'blueprint_spec.json')
    BLUEPRINT_KNOWLEDGE_PATH = os.path.join(BLUEPRINT_SPEC_DIR_PATH, 'blueprint_knowledge.json')
    BLUEPRINT_CUSTOMERS_DIR_PATH = os.path.join(BLUEPRINT_SPEC_DIR_PATH, BLUEPRINT_CUSTOMERS_OUT_FOLDER_PATH,
                                                'Hardware')
    RANGE_REGEX = r"range\((.*)-(.*)\)"
    UNLIMITED = "unlimited"
    UNMARKED_PROPERTIES = ['ports_names', 'nic_per_numa', 'cpus_per_numa']

    def get_collected_data(self):
        return self._collected_data()

    def get_expected_blueprint(self, blueprint_name):
        with open(ValidateBlueprint.BLUEPRINT_JSON_PATH) as f:
            blueprint_json = json.load(f)

        expected_blueprint = blueprint_json.get(blueprint_name, {})

        for filename in os.listdir(ValidateBlueprint.BLUEPRINT_CUSTOMERS_DIR_PATH):
            if not filename.startswith("new_"):
                filename_without_extension = filename.split(".")[0]
                if blueprint_name == filename_without_extension:
                    with open(os.path.join(ValidateBlueprint.BLUEPRINT_CUSTOMERS_DIR_PATH, filename)) as f:
                        blueprint_customers_json = json.load(f)
                    expected_blueprint = blueprint_customers_json
                    break

        for version_range, blueprint_data in list(expected_blueprint.items()):
            if Version.is_version_in_range(gs.get_version(), version_range):
                return blueprint_data

        return {}

    def get_values_per_host_by_role(self, values_per_host, role):
        res_dict = OrderedDict()

        for host, val_dict in list(values_per_host.items()):
            _, host_executor = gs.get_host_executor_factory().get_host_executor_by_host_name(host)
            val_roles = host_executor.roles

            if role in val_roles:
                res_dict[host] = val_dict

        return res_dict

    def get_topic_and_name_from_objective_name(self, objective_name):
        objective_name = objective_name.split("@")
        assert len(objective_name) == 2 and "" not in objective_name, "Expected DataCollector with name like topic@name"
        topic, name = objective_name

        return name, topic

    def get_list_of_data_collectors(self):
        assert False, "Please implement get_list_of_data_collectors"

    def _collected_data(self):
        collector_list = self.get_list_of_data_collectors()
        data_per_blueprint_objective = OrderedDict()

        for collector in collector_list:
            if tools.user_params.debug:
                print("--- run_data_collector of {}".format(collector.__name__))
            name, res = self.run_data_collector(collector)
            name, res = self.handle_collector_exceptions(collector, name, res)
            if tools.user_params.debug:
                print(" -- done run_data_collector of {}".format(collector.__name__))
            assert data_per_blueprint_objective.get(name) is None, name + " already in the list "
            data_per_blueprint_objective[name] = res
        self.raise_if_no_collector_passed()

        return data_per_blueprint_objective


    def handle_collector_exceptions(self, collector, name, res):
        for exceptions in self.data_collectors_exceptions:
            if collector.__name__ in exceptions and len(exceptions[collector.__name__]) == len(collector()._get_host_executors()):
                name = collector().get_blueprint_objective_key_name()
                for host_executor_name in exceptions[collector.__name__]:
                    res[host_executor_name] = {
                        id_: "failed to collect data (details in the .json file)" for id_ in
                        self._get_ids_for_failed_data_collector(collector, host_executor_name)
                    }
        return name, res

    def _get_ids_for_failed_data_collector(self, collector, host_executor_name):
        try:
            host_executor = gs.get_host_executor_factory().get_all_host_executors()[host_executor_name]
            if host_executor.is_connected:
                return collector(host_executor=host_executor).get_ids()
        except Exception as e:
            self.add_to_validation_log(str(e))

        return ["failed_to_get_id"]

    def _is_the_same_for_all_hosts(self,values_per_host):
        for host, host_values in list(values_per_host.items()):
            if type(host_values) != dict:
                host_values = {}
            for key, value in list(host_values.items()):
                if isinstance(value, list):
                    value.sort()
        value_to_hosts_dict = PythonUtils.reverse_dict_by_to_string_values(values_per_host)

        if len(value_to_hosts_dict) == 1:
            return True
        return False

    def is_validation_passed(self):
        data = self.get_collected_data()
        blueprint_inventory = BlueprintInventory()
        blueprint_name = blueprint_inventory.build_actual_blueprint_name(data)
        return self._compare_with_expected_blue_print(data, blueprint_name=blueprint_name)

    def _get_roles_list(self):
        return Objectives.get_roles_list_by_deployment_type(gs.get_deployment_type())

    def _get_representatives_values(self, system_data):
        data_to_present_dict = OrderedDict()
        roles_list = self._get_roles_list()
        for role in roles_list:
            data_to_present = OrderedDict()
            for objective_name in system_data:
                name, topic = self.get_topic_and_name_from_objective_name(objective_name)
                data_to_present[topic] = data_to_present.get(topic, {})
                data_to_present[topic][name] = {}
                values_per_host = system_data[objective_name]
                values_per_host_by_role = self.get_values_per_host_by_role(values_per_host, role)
                is_the_same_for_all_hosts = self._is_the_same_for_all_hosts(values_per_host_by_role)
                data_to_present[topic][name]["is_uniform"] = is_the_same_for_all_hosts

                if not list(values_per_host_by_role.values()):
                    data_to_present[topic][name]["value"] = {}
                else:
                    if is_the_same_for_all_hosts:
                        one_of_the_values = list(values_per_host_by_role.values())[0]
                        data_to_present[topic][name]["value"] = one_of_the_values
                    else:
                        data_to_present[topic][name]["value"] = ValidateBlueprint._get_list_of_id_host_name_data(
                            values_per_host_by_role)
            data_to_present_dict[role] = data_to_present

        return data_to_present_dict

    @staticmethod
    def _get_list_of_id_host_name_data(values_per_host_by_role):
        res = []

        for host_name, id_to_data_dict in list(values_per_host_by_role.items()):
            id_to_hostname_data_dict = {}
            if id_to_data_dict is not None:
                for id_, data in list(id_to_data_dict.items()):
                    id_to_hostname_data_dict[id_] = {host_name: data}
            res.append(id_to_hostname_data_dict)

        return res

    def _compare_with_expected_blue_print(self, system_data, blueprint_name):
        expected_blueprint = self.get_expected_blueprint(blueprint_name)
        system_data_dict = self._get_representatives_values(system_data)
        knowledge_dict = self._get_knowledge_dict_by_field("blueprint_sub_names", blueprint_name)
        failed_topics, system_info = self._compare_blueprint(expected_blueprint, system_data_dict, knowledge_dict)

        self._system_info = {"blueprint_name": blueprint_name,
                             "has_match_in_blueprint_excel": expected_blueprint != {},
                             "pairs_data": system_info}

        if len(failed_topics) > 0:
            self._failed_msg = "The following values are not equal to blueprint:\n"
            for topic in failed_topics:
                self._failed_msg += topic + '\n'
            return False

        return True

    @staticmethod
    def _compare_blueprint(expected_blueprint, system_data_dict, knowledge_dict):
        system_info = OrderedDict()
        failed_topics = []
        for system_role, system_role_data in list(system_data_dict.items()):
            hosts_by_role = list(gs.get_host_executor_factory().get_host_executors_by_roles(roles=system_role).keys())
            system_info[system_role] = OrderedDict()
            role_knowledge_dict = ValidateBlueprint._get_knowledge_dict_by_field("roles", system_role,
                                                                                 deepcopy(knowledge_dict))
            system_info[system_role] = ValidateBlueprint._get_data_in_blueprint_not_in_system(
                system_role_data, expected_blueprint.get(system_role), role_knowledge_dict)
            for system_topic, system_topic_data in list(system_role_data.items()):
                system_data_by_id = ValidateBlueprint._group_dict_by_id(system_topic_data)
                expected_topic_blueprint = ValidateBlueprint._get_expected_blueprint_by_topic(
                    system_role, system_topic, expected_blueprint)
                expected_topic_blueprint = dict() if not expected_topic_blueprint else expected_topic_blueprint
                pairs_by_id = ValidateBlueprint._prepare_pairs(expected_topic_blueprint, system_data_by_id)
                pairs_by_id = ValidateBlueprint._get_id_hosts(pairs_by_id, hosts_by_role)
                for id in pairs_by_id:
                    for property in pairs_by_id[id]['system output']:
                        if not pairs_by_id[id]['system output'][property]['is equal']:
                            failed_topics.append("{} >> {} >> {} >> {}".format(system_role, system_topic, id, property))
                        if type(pairs_by_id[id]['system output'][property]['value']) is dict:
                            if len(list(pairs_by_id[id]['system output'][property]['value'].keys())) == 1:
                                pairs_by_id[id]['system output'][property]['value'] = list(pairs_by_id[id]['system output'][property]['value'].keys())[0]
                knowledge_data = role_knowledge_dict.get(system_topic, {})

                system_info[system_role][system_topic] = {"pairs_by_id": pairs_by_id, "knowledge_data": knowledge_data}

        return failed_topics, system_info

    @staticmethod
    def _get_id_hosts(pairs_by_id, hosts_by_role):
        for id in pairs_by_id:
            id_hosts = set([])
            for property in pairs_by_id[id]['system output']:
                if type(pairs_by_id[id]['system output'][property]['value']) is dict:
                    for value in list(pairs_by_id[id]['system output'][property]['value'].keys()):
                        id_hosts.update(pairs_by_id[id]['system output'][property]['value'][value])
            if id_hosts:
                if sorted(id_hosts) != sorted(hosts_by_role):
                    missing_hosts = [host for host in hosts_by_role if host not in id_hosts]
                    existing_hosts = [host for host in hosts_by_role if host not in missing_hosts]
                    pairs_by_id[id]['hosts'] = {}
                    pairs_by_id[id]['hosts']['Missing on hosts'] = missing_hosts
                    pairs_by_id[id]['hosts']['Existing on hosts'] = existing_hosts
        return pairs_by_id

    @staticmethod
    def _prepare_pairs(expected_topic_blueprint, system_data_by_id):
        pairs = ValidateBlueprint._get_pairs(expected_topic_blueprint, list(system_data_by_id.values()))
        blueprint_data_by_id = ValidateBlueprint._get_blueprint_data_by_id(pairs, system_data_by_id)
        pairs_by_id = ValidateBlueprint._get_pairs_by_id(blueprint_data_by_id, system_data_by_id)

        return pairs_by_id

    @staticmethod
    def _get_pairs_by_id(blueprint_data_by_id, system_data_by_id):
        pairs = {}
        for id_ in list(blueprint_data_by_id.keys()):
            system_data_by_id[id_] = ValidateBlueprint._validate_system_data_against_blueprint_data(system_data_by_id.get(id_, {}), blueprint_data_by_id[id_])
            pairs[id_] = {"expected blueprint": blueprint_data_by_id[id_],
                          "system output": system_data_by_id.get(id_, {})}
        return pairs

    @staticmethod
    def _get_blueprint_data_by_id(pairs, system_data_by_id):
        system_data_by_id_copy = dict(system_data_by_id)
        no_sys_data_counter = 0
        res = {}
        for blueprint_data, sys_data in pairs:
            if sys_data == {}:
                key = "missing_item_" + str(no_sys_data_counter)
                no_sys_data_counter = no_sys_data_counter + 1
            else:
                key = list(system_data_by_id_copy.keys())[list(system_data_by_id_copy.values()).index(sys_data)]

                del system_data_by_id_copy[key]
            res[key] = blueprint_data

        return res

    @staticmethod
    def _get_data_in_blueprint_not_in_system(system_data, expected_blueprint, knowledge_dict):
        if not expected_blueprint:
            return OrderedDict()

        topics_only_in_blueprint = set(expected_blueprint.keys()) - set(system_data.keys())
        data_result = OrderedDict()

        for topic in topics_only_in_blueprint:
            knowledge_data = knowledge_dict.get(topic, {})
            res = OrderedDict()
            expected_blueprint[topic] = [expected_blueprint[topic]] if type(expected_blueprint[topic]) != list \
                else expected_blueprint[topic]
            for i, data in enumerate(expected_blueprint[topic]):
                res["missing_item_" + str(i)] = {"expected blueprint": data, "system output": {}}
            data_result[topic] = {"pairs_by_id": res, "knowledge_data": knowledge_data}

        return data_result

    @staticmethod
    def _get_pairs(list_blueprint_dict, list_system_dict):
        return StableMarriageProblem().get_pairs(list_blueprint_dict, list_system_dict)

    @staticmethod
    def get_blueprint_range_from_str(range_str):
        range_list = re.findall(ValidateBlueprint.RANGE_REGEX, range_str)

        if len(range_list) != 1:
            return None

        range_list = range_list[0]
        if not (to_unicode(range_list[0]).strip().isnumeric() and
                (to_unicode(range_list[1]).strip().isnumeric() or range_list[1] == ValidateBlueprint.UNLIMITED)):
            return None

        if range_list[1] == ValidateBlueprint.UNLIMITED:
            return [int(range_list[0]), ValidateBlueprint.UNLIMITED]

        return [int(range_list[0]), int(range_list[1])]

    @staticmethod
    def _is_one_val_same(system_val, blueprint_val):
        if type(system_val) is dict:
            for value, host in list(system_val.items()):
                if not ValidateBlueprint._is_one_val_same(value, blueprint_val):
                    return False
            return True
        if blueprint_val is None:
            return True
        elif isinstance(blueprint_val, six.string_types):
            range_list = ValidateBlueprint.get_blueprint_range_from_str(blueprint_val)
            if range_list:
                return ValidateBlueprint._is_sys_val_in_range(range_list, system_val)
            if str(system_val) in blueprint_val:
                return True
        elif type(blueprint_val) == list:
            if type(system_val) == list and sorted(blueprint_val) == sorted(system_val):
                return True
            if type(blueprint_val) == list and (isinstance(system_val, six.string_types) or type(system_val) is int):
                if system_val in blueprint_val:
                    return True
        elif blueprint_val == system_val:
            return True

        return False

    @staticmethod
    def _is_sys_val_in_range(range_list, system_val):
        if type(system_val) is dict:
            for value in system_val:
                if not ValidateBlueprint._is_value_in_range(range_list, value):
                    return False
            return True
        else:
            return ValidateBlueprint._is_value_in_range(range_list, system_val)

    @staticmethod
    def _is_value_in_range(range_list, value):
        if to_unicode(value).strip().isnumeric():
            system_val = int(value)
            if range_list[0] <= system_val:
                if range_list[1] == ValidateBlueprint.UNLIMITED:
                    return True
                return system_val <= range_list[1]
        return False

    @staticmethod
    def _validate_system_data_against_blueprint_data(system_data, blueprint_data):
        system_val = {}
        for property_name, property_val in list(system_data.items()):
            system_val[property_name] = {}
            system_val[property_name]['value'] = property_val
            if property_name in ValidateBlueprint.UNMARKED_PROPERTIES:
                system_val[property_name]['is equal'] = True
                continue
            if ValidateBlueprint._is_one_val_same(property_val, blueprint_data.get(property_name)):
                system_val[property_name]['is equal'] = True
            else:
                system_val[property_name]['is equal'] = False

        return system_val

    @staticmethod
    def _group_dict_by_id(data_dict):
        ids = ValidateBlueprint._get_ids_from_collectors_values(list(data_dict.values()))
        res = {id_: {} for id_ in ids}

        for collector_name, collector_data in list(data_dict.items()):
            for id_ in list(res.keys()):
                res[id_][collector_name] = ValidateBlueprint._get_collector_data_by_id(collector_data.get("value", {}), id_)

        return res

    @staticmethod
    def _get_ids_from_collectors_values(collectors_values):
        all_ids_set = set()
        for collector in collectors_values:
            collector_data = collector["value"]
            if type(collector_data) is str or collector_data is None:
                continue

            elif type(collector_data) is list:
                for host_values in collector_data:
                    all_ids_set.update(list(host_values.keys()))

            elif type(collector_data) is dict:
                all_ids_set.update(list(collector_data.keys()))

            else:
                raise TypeError("Expected value type of 'str'/'list'/'dict'. Found type: {} for collector value: {}".format(type(collector_data), collector_data))

        return all_ids_set

    @staticmethod
    def _get_collector_data_by_id(collector_data, id_):
        if not collector_data:
            return "----"
        if type(collector_data) == dict:
            return collector_data.get(id_)
        res = {}
        if type(collector_data) is list:
            for data in collector_data:
                if data.get(id_):
                    hostname = list(data[id_].keys())[0]
                    value = list(data[id_].values())[0]

                    if not isinstance(value, Hashable):
                        value = str(value)
                    res[value] = res.get(value, []) + [hostname]

            for val in list(res.keys()):
                res[val].sort()

            return res

        raise UnExpectedSystemOutput("", "", collector_data, "Expected collector data from type list or dict or None")

    @staticmethod
    def _get_expected_blueprint_by_topic(role, topic, expected_blue_print):
        return expected_blue_print.get(role, {}).get(topic)

    @staticmethod
    def _get_knowledge_json():
        with open(ValidateBlueprint.BLUEPRINT_KNOWLEDGE_PATH) as f:
            return json.load(f)

    @staticmethod
    def _get_knowledge_dict_by_field(field_name, match_field, knowledge_dict=None):
        if not knowledge_dict:
            knowledge_dict = ValidateBlueprint._get_knowledge_json()

        for topic, topic_data in list(knowledge_dict.items()):
            for collector_name, remarks_list in list(topic_data.items()):
                topic_data[collector_name] = list([l for l in remarks_list if ValidateBlueprint._is_remarks_match_blueprint_name(
                                                             l, field_name, match_field)])

        return knowledge_dict

    @staticmethod
    def _is_remarks_match_blueprint_name(remarks, field_name, match_field):
        name_regex = "|".join(remarks[field_name])

        return re.match(name_regex, match_field) is not None


class ValidateHWBlueprint(ValidateBlueprint):
    def get_list_of_data_collectors(self):
        return get_list_of_hw_data_collectors()

    def set_document(self):
        self._unique_operation_name = "validate_is_hw_blueprint"
        self._title_of_info = "HW blueprint information"
        self._title = "Check if aligned with blueprint"
        self._failed_msg = ""
        self._severity = Severity.NOTIFICATION
        self._is_pure_info = False
        self._implication_tags = [ImplicationTag.NOTE]


class ValidateFWBlueprint(ValidateBlueprint):
    def get_list_of_data_collectors(self):
        return get_list_of_fw_data_collectors()

    def set_document(self):
        self._unique_operation_name = "validate_is_fw_blueprint"
        self._title_of_info = "FW blueprint information"
        self._title = "Show versions"
        self._failed_msg = ""
        self._severity = Severity.NOTIFICATION
        self._is_pure_info = False
        self._implication_tags = [ImplicationTag.NOTE]

    def is_validation_passed(self):
        data = self.get_collected_data()
        self._organize_data(data)

        return True

    def _organize_data(self, system_data):
        system_data_dict = self._get_representatives_values(system_data)
        system_data_by_id = self._get_data_dict_by_id(system_data_dict)
        self._system_info = system_data_by_id

    @staticmethod
    def _get_data_dict_by_id(system_data_dict):
        system_info = OrderedDict()

        for system_role, system_role_data in list(system_data_dict.items()):
            system_info[system_role] = {}
            for system_topic, system_topic_data in list(system_role_data.items()):
                system_data_by_id = ValidateBlueprint._group_dict_by_id(system_topic_data)

                system_info[system_role][system_topic] = system_data_by_id

        return system_info


class ValidateBlueprintUsingHostgroup(ValidateBlueprint):
    ''' It uses hostgroups instead of roles, by using some system data gathered with self.get_collected_data()'''

    STR_SEPARATOR = '-'

    def get_values_per_host_by_role(self, values_per_host, hostgroup):
        res_dict = OrderedDict()
        for host, val_dict in list(values_per_host.items()):
            if hostgroup and hostgroup in host:     # not empty and included in the host name
                res_dict[host] = val_dict

        return res_dict

    def get_hostgroups(self):
        '''Returns the hostgroup names like this ['fi-803-hpe-bm-masterbm-', 'fi-803-hpe-bm-workerbm-', ...]'''

        hostgroups = None
        node_names = self.get_node_names_from_system()  # used self to be able to mock it properly on pytest
        if node_names is not None:
            hostgroups = ValidateBlueprintUsingHostgroup.get_hostgroups_from_node_names(node_names)

        return hostgroups

    def _get_roles_list(self):
        hostgroup_list = self.get_hostgroups()
        return hostgroup_list

    @staticmethod
    def get_node_names_from_system():
        hosts = list(gs.get_host_executor_factory().get_all_host_executors().keys())
        node_names = [x for x in hosts if x]    # skip empty group names
        return node_names

    @staticmethod
    def get_hostgroups_from_node_names(node_names):
        node_names_without_index = [ValidateBlueprintUsingHostgroup.STR_SEPARATOR.join(
            x.split(ValidateBlueprintUsingHostgroup.STR_SEPARATOR)[:-1] + ['']) for x in node_names]
        unique_hostgroups = sorted(set(node_names_without_index))
        return unique_hostgroups


class ValidateBlueprintMatchesGroup:
    '''To be used when in need to compare blueprint results against each other in a hostgroup or role group for a
    validation'''

    def __init__(self):
        pass

    @staticmethod
    def summarize_results(values_per_host_by_group):
        '''Returns False if any node group (hostgroup or role depending on inherited class) has is_uniform: False,
        also returns failed_msg to be used to modify self._failed_msg accordingly'''

        return_flag, failed_msg = True, ""
        for group in values_per_host_by_group:
            for topic in values_per_host_by_group[group]:
                for name in values_per_host_by_group[group][topic]:
                    if values_per_host_by_group[group][topic][name]["value"]:   # there is some info for the group
                        if not values_per_host_by_group[group][topic][name]["is_uniform"] and \
                                len(values_per_host_by_group[group][topic][name]["value"]):
                            # if ["value"] is empty, group is empty as per _get_representatives_values()
                            return_flag = False
                            dict_to_show = ValidateBlueprintMatchesGroup.reorder_to_hostname_id_data(
                                values_per_host_by_group[group][topic][name]["value"])

                            failed_msg += "\nGroup: '{}', Topic: '{}', Property: '{}'\n".format(group, topic, name)
                            failed_msg += json.dumps(dict_to_show, indent=4)
                            failed_msg += "\n"

        return return_flag, failed_msg

    @staticmethod
    def reorder_to_hostname_id_data(lst):
        '''Transforms a list with each element being {id: {host_name: value_str} to a single dict
        {host_name: {id: value_str}}}'''

        res = OrderedDict()
        for elem_of_same_node in lst:   # elem_of_same_node is {id1: {host1: value1}, id2: {host1: value2}, ...}
            if len(elem_of_same_node):  # not empty dict, as per _get_list_of_id_host_name_data()
                one_id = list(elem_of_same_node.keys())[0]
                host_name = list(elem_of_same_node[one_id].keys())[0]
                # host_name always available if id_ is available as per _get_list_of_id_host_name_data()

                id_to_data_dict_of_host = PythonUtils.filter_dict_by_inner_key(elem_of_same_node, host_name)
                res[host_name] = id_to_data_dict_of_host

        return res


class ValidateOsDiskMatch(ValidateBlueprintUsingHostgroup):

    def set_document(self):
        self._unique_operation_name = "os_disk_matches_in_group"
        self._title = "OS Disk Match Checking in hostgroups"
        self._msg = "When a wrong disk is used for the OS, it might represent a problem, specially in storage nodes\n" \
                    "where an OSD might be created in a wrong disk because of this.\n" \
                    "To prevent this, this test checks if the used OS disk matches in the nodes of same hostgroup.\n"
        self._title_of_info = "OS Disk Match Checking in hostgroups"
        self._is_pure_info = False
        self._implication_tags = [ImplicationTag.NOTE]
        self._failed_msg = "Chosen Operating System disk mismatch found!\nThe following values in each property are per disk:\n"
        self._severity = Severity.WARNING
        self._blocking_tags = []

    def get_list_of_data_collectors(self):
        return [OperatingSystemDiskName, OperatingSystemDiskType, OperatingSystemDiskSize]

    def is_validation_passed(self):
        data = self.get_collected_data()
        values_per_host_by_group = self._get_representatives_values(data)
        return_flag, failed_msg = ValidateBlueprintMatchesGroup.summarize_results(values_per_host_by_group)
        self._failed_msg += failed_msg
        return return_flag
