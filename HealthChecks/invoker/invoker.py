from __future__ import absolute_import
from collections import OrderedDict
from HealthCheckCommon.flow import *



class Invoker:
    '''
    The Invoker is associated with one or several commands. It sends a request
    to the command.
    '''

    '''
    Initialize commands.
    '''

    # todo unittest
    @staticmethod
    def _is_a_complementary_receiver(receiver, receivers_list):
        for my_receiver in receivers_list:
            set_up_type_intersection_list = [x for x in receiver.deployment_type_list() if
                                             x in my_receiver.deployment_type_list()]
            if len(set_up_type_intersection_list) > 0:
                version_intersection_list = [x for x in receiver.version_list if x in my_receiver.version_list]
                if len(version_intersection_list) > 0:
                    return False
        return True

    def __init__(self, version, deployment_type, flg_is_passive_type_only, flow_list_class, host_name_list=None,
                 roles=None, specific_validations=None, specific_tags=None):
        self._command_map = OrderedDict()  # mapping between command and its flow
        self._version = version
        self._deployment_type = deployment_type
        self._flg_is_passive_type_only = flg_is_passive_type_only
        self._host_name_list = host_name_list
        self._roles = roles
        self._specific_validations = specific_validations
        self._specific_tags = specific_tags

        # todo separate and unittest
        # todo refactor for simplicity
        Invoker.list_of_flows = flow_list_class.get_list_of_flows()

        for cls_flow in Invoker.list_of_flows:
            flow_receiver = cls_flow()
            cmd_mane = flow_receiver.command_name()
            # assert ( self._command_map.get(cmd_mane) is None)
            # assert if the same command for the same set up and same versions
            if self._command_map.get(cmd_mane) is None:
                self._command_map[cmd_mane] = [flow_receiver]
            else:

                # check that not stepping on other receiver tunes
                assert (self._is_a_complementary_receiver(flow_receiver, self._command_map.get(cmd_mane)))
                self._command_map[cmd_mane].append(flow_receiver)

    def _find_suitable_flow_receiver(self, command):
        assert self._command_map.get(command) is not None, \
            "Seems that a program error accrued - no matching command found. Please refer to developer "

        receiver_family = self._command_map.get(command)

        for sibling_receiver in receiver_family:
            if self._version in sibling_receiver.version_list() and \
                    self._deployment_type in sibling_receiver.deployment_type_list():
                return sibling_receiver

        return None

    # todo return documentation of all available validations

    def run(self, command, validators_list):
        '''
        The Invoker does not depend on concrete command or receiver classes. The
        Invoker passes a request to a receiver indirectly, by executing a
        command.
        '''

        if self._command_map.get(command) is None:
            to_return = {'return_code': 1, "details": "command " + command + " is not in the command list"}
            return to_return

        receiver = self._find_suitable_flow_receiver(command)
        if receiver is None:
            to_return = {'return_code': 1,
                         "details": "command " + command +
                                    " is not in the command list for the given version and deployment-type"}
            return to_return

        details = self.run_flow_receiver_verify(receiver, validators_list)

        return {'return_code': 0, "details": details}

        # if issubclass(receiver.__class__, InfoCheckFlow):
        #   print("Gathering information with the command {}".format(command))
        #   return recevier.info_check(self._version,command,arg)

        assert False, 'receiver type unknown'


    def run_flow_receiver_verify(self, receiver, validators_list):
        if issubclass(receiver.__class__, ValidationFlow):
            return receiver.verify(self._version, self._deployment_type, validators_list)

    def get_flow_object(self, command_name):
        return self._find_suitable_flow_receiver(command_name)

    def get_flow_object_if_exist(self, command_name):
        if self._command_map.get(command_name):
            return self.get_flow_object(command_name)

        return None


    def get_available_flows(self, specific_flows=None, run_only_default=False, limited_output = False):
        to_return = OrderedDict()
        for cmd_name in self._command_map:
            flow = self._find_suitable_flow_receiver(cmd_name)
            if flow is None \
                    or (run_only_default and not flow.is_default())\
                    or (limited_output and not flow.is_part_of_limited_output())\
                    or (specific_flows and cmd_name not in specific_flows):
                continue
            validator_objects = flow._get_list_of_validator_object(self._version, self._deployment_type,
                                                                   self._flg_is_passive_type_only, self._host_name_list,
                                                                   self._roles, self._specific_validations,
                                                                   self._specific_tags)
            to_return[cmd_name] = validator_objects

        return to_return

    def get_available_flows_with_titles(self, flow_dict):
        to_return = OrderedDict()
        for flow_name, validations_objects in list(flow_dict.items()):
            if validations_objects:
                flow = self._find_suitable_flow_receiver(flow_name)
                to_return[flow_name] = flow.get_validations_name(self._version, self._deployment_type, validations_objects)
        return to_return

    def get_available_flows_with_details(self, flow_dict, run_only_default=False):
        to_return = {}
        for cmd_name in self._command_map:
            flow = self._find_suitable_flow_receiver(cmd_name)
            if flow is None or (run_only_default and not flow.is_default()):
                continue
            flow_validations_with_details = []
            validations_objects = flow_dict.get(cmd_name)
            if not validations_objects:
                continue
            for validation in validations_objects:
                validation_title = flow.get_full_title(validation[0])
                blocking_tags = validation[0].get_blocking_tags()
                documentation_link = validation[0].get_documentation_link()
                validation_details_dict = OrderedDict()
                validation_details_dict['title'] = validation_title
                if blocking_tags and blocking_tags is not None:
                    validation_details_dict['blocking tags'] = blocking_tags
                if documentation_link is not None:
                    validation_details_dict['documentation link'] = documentation_link
                flow_validations_with_details.append(validation_details_dict)
            to_return[cmd_name] = flow_validations_with_details

        return to_return
