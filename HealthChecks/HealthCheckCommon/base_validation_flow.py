from __future__ import absolute_import

import tools.user_params
from HealthCheckCommon.base_init_flow import BaseInitFlow
from HealthCheckCommon.flow import *
from HealthCheckCommon.operations import *
from HealthCheckCommon.printer import *
import tools.sys_parameters as sys_parameters
from HealthCheckCommon.validator import InformatorValidator
from tools.python_utils import PythonUtils
from tools.python_versioning_alignment import get_full_trace
import tools.global_logging as health_check_logger
from HealthCheckCommon.parallel_runner import ParallelRunner


class Initiator:
    def init_validations(self):
        '''
                do any system initiator at the end of the process
        '''
        assert False, 'this is an abstract method, please implement me'


class BaseValidationFlow(ValidationFlow):
    '''
    The Flow classes contain some important business logic. They know how to
    perform all kinds of operations, associated with carrying out a request. In
    fact, any class may serve as a Flow.
    '''

    def _get_list_of_validator_class(self, version, deployment_type):
        # overwrite this and put your list of validators classes here.
        # different logic can be set to different versions

        # todo add more description to all asserts
        raise NotImplementedError('this is an abstract method, please implement _get_list_of_validator_class')

    def _clean_flow(self):
        '''
        do any system clean at the end of the process - for example free chash memory
        '''
        pass

    def _get_initiator_class(self):
        '''
        :return class that have init_validations() method
        '''
        return BaseInitFlow()

    def _test_prerequisite_fulfilled(self, validation_object):

        try:
            # add try because commands is allow to run from here
            if not validation_object.is_prerequisite_fulfilled():
                health_check_logger.logger.info("validation {} is not relevant to this set up"
                                                .format(validation_object._unique_operation_name))
                return False
            return True
        except:
            prerequisite_exception = "validation {} was not run due to exception in it prerequisite check: {} ".format(
                validation_object._unique_operation_name, get_full_trace())
            if tools.user_params.debug or tools.user_params.debug_validation_flag:
                health_check_logger.log_and_print(prerequisite_exception)
            else:
                health_check_logger.logger.info(prerequisite_exception)
            return False

    def should_be_created(self, flg_is_passive_type_only, validation_object, validation_host_executor,
                          deployment_type, hosts_list=None, roles=None, specific_validations=None, specific_tags=None):
        if specific_validations is not None:
            if (validation_object._unique_operation_name not in specific_validations) and\
                    (validation_object._title not in specific_validations):
                return False
        
        # Filter by tags if provided. Validation should have at least one of the provided tags
        # Check both _implication_tags and _blocking_tags
        if specific_tags is not None:
            validation_has_matching_tag = False
            validation_implication_tags = validation_object.get_implication_tags() or []
            validation_blocking_tags = validation_object.get_blocking_tags() or []
            
            if isinstance(validation_implication_tags, str):
                validation_implication_tags = [validation_implication_tags]
            if isinstance(validation_blocking_tags, str):
                validation_blocking_tags = [validation_blocking_tags]
            
            all_validation_tags = validation_implication_tags + validation_blocking_tags
            
            for tag in specific_tags:
                if tag in all_validation_tags:
                    validation_has_matching_tag = True
                    break
            
            if not validation_has_matching_tag:
                return False
        
        if validation_object.should_add_base_hosts():
            if hosts_list:
                enriched_hosts = sys_parameters.get_host_executor_factory().get_base_hosts()
                hosts_list = list(set(hosts_list) | set(enriched_hosts))
        if not validation_host_executor.is_connected:
            return False
        # if we have roles set from the user
        if roles:
            matched_roles = PythonUtils.list_intersection(roles, validation_host_executor.roles)
            if not len(matched_roles):
                return False
            # specific host

        # validation_object.objective_hosts is what we set per validtion
        assert (validation_object.objective_hosts != Objectives.NA)
        # if we used NA. we do not want to allocate anithing

        roles_for_current_deployment_type = validation_object.get_roles_for_current_deployment(deployment_type)
        if not roles_for_current_deployment_type:
            return False

        matched_validation_roles = PythonUtils.list_intersection(
            validation_host_executor.roles,
            roles_for_current_deployment_type)
        if not len(matched_validation_roles):
            return False

        # host list is limitation of the possible hosts - set by the user
        if hosts_list:
            if validation_host_executor.host_name not in hosts_list:
                return False
        if flg_is_passive_type_only and validation_object._is_action_type_active:
            return False

        #this comes last - becouse it may take the longest running time
        if not self._test_prerequisite_fulfilled(validation_object):
            return False

        return True

    def _get_list_of_validator_object(self, version, deployment_type, flg_is_passive_type_only,
                                      only_specific_hosts_ip_list=None, roles=None, specific_validations=None,
                                      specific_tags=None):
        # if your validator need input for init - overwrite this
        class_list = self._get_list_of_validator_class(version, deployment_type)
        object_list = []
        for validation_class in class_list:
            validation_instances_list = []
            host_executors = sys_parameters.get_host_executor_factory().get_all_host_executors()
            for host_name in host_executors:
                validation_object = validation_class(host_executors[host_name])
                if self.should_be_created(flg_is_passive_type_only, validation_object, host_executors[host_name],
                                          deployment_type, only_specific_hosts_ip_list, roles, specific_validations,
                                          specific_tags):

                    validation_instances_list.append(validation_object)

            if len(validation_instances_list) > 0:
                object_list.append(validation_instances_list)
        # return list of host_executors instances for each validation
        return object_list

    def get_full_title(self, validator):
        if isinstance(validator, InformatorValidator):
            return validator._title + " : " + validator._title_of_info
        else:
            return validator._title

    def get_validations_name(self, version, deployment_type, validator_objects):
        '''
        :return: the validations details (name and if this is active checks)
        '''
        to_return = []
        for validator_object_for_hosts in validator_objects:
            to_return.append(self.get_full_title(validator_object_for_hosts[0]))
        return to_return


    def assert_no_double_unique_operation_name(self, validator_objects):
        '''
        :throw assert error if in our code there are two validation with the same name
        '''
        unique_operation_name_set = set()

        for validator_object_for_hosts in validator_objects:
            unique_operation_name = validator_object_for_hosts[0]._unique_operation_name
            if unique_operation_name in unique_operation_name_set:
                assert False, "there are two validation in this flow with the same unique name: {}".format(unique_operation_name)
            else:
                unique_operation_name_set.add(unique_operation_name)

    def _invoke_checks(self, validators_list, printer):
        return ParallelRunner.run_validation_flows_on_all_host(validators_list, printer)


    def verify(self, version, deployment_type, validators_list):
        '''
        this is the main interface of the system
        :return: data type of the structure of dict with return code and message:
        '''
        assert (version in self.version_list())
        assert (deployment_type in self.deployment_type_list())

        # initiator
        printer = StructedPrinter()
        init_class = self._get_initiator_class()
        init_class.init_validations()

        self.assert_no_double_unique_operation_name(validators_list)

        self._invoke_checks(validators_list=validators_list, printer=printer)

        self._clean_flow()

        to_return = {'command_name': self.command_name(), "details": printer.get_msg()}
        return to_return
# ----------------------------------------------------------------------------------------------------------------------
