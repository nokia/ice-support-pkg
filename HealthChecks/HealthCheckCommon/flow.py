from __future__ import absolute_import
import abc
from tools.global_enums import Version


class Flow:
    '''
    The Flow classes contain some important business logic. They know how to
    perform all kinds of operations, associated with carrying out a request. In
    fact, any class may serve as a Flow.
    '''

    # todo: receivers of receivers
    # todo : add list of

    @abc.abstractmethod
    def command_name(self):
        assert False, 'please implement command_name '

    @abc.abstractmethod
    def version_list(self):
        return Version.AVAILABLE_VERSIONS

    @abc.abstractmethod
    def deployment_type_list(self):
        raise NotImplementedError('please implement deployment_type_list ')

    def is_default(self):
        return True

    def is_part_of_limited_output(self):
        return True

    def get_flow_order(self):
        return 0

    def get_dependencies(self):
        return []


class ValidationFlow(Flow):
    @abc.abstractmethod
    def verify(self, version, cmd, *args):
        '''
              abstract method -> to be inherit

              this is the main interface of the system
                #must return data type of the structure :
              :param cmd:
              :param args:
              :return: data type of the structure of dict with return code and message:
              for example:
              {'return_code': 200, 'message': 'done'}

         '''
        assert False

    def get_validations_name(self, version, deployment_type, validator_objects):
        '''
        :return: the validations details (name and etc)
        '''
        assert False


class InfoCheckFlow(Flow):
    @abc.abstractmethod
    def info_check(self, version, cmd, *args):
        '''
                      abstract method -> to be inharatent

                      this is the main interface of the system
                        #must return data type of the structure :
                      :param cmd:
                      :param args:
                      :return: data type of the structure of dict with return code and message:
                      for example:
                      {'return_code': 200, 'message': 'done'}

        '''
        assert False
