from __future__ import absolute_import
from __future__ import print_function
import inspect
import sys
import threading
import time

import tools.user_params
from HealthCheckCommon.printer import StructedPrinter
from tools.Exceptions import *
from tools.python_versioning_alignment import get_full_trace, get_default_timer
import tools.global_logging as global_logging
from tools.ExecutionModule.execution_helper import ExecutionHelper
from tools.global_enums import *
from tools.global_logging import log_and_print


class DynamicPrerequisiteFulfillness:
    @staticmethod
    def is_a_prerequisite_fulfilled(my_unique_name, my_host_ip, other_unique_operation_name, operations_list_of_a_flow,
                                    flg_is_prerequisite_on_multiple_hosts=False, flg_any=True):

        flg_prerequisite_found = False
        for operations in operations_list_of_a_flow:
            if operations[0].get_unique_name() == my_unique_name:
                break
            if operations[0].get_unique_name() == other_unique_operation_name:

                for operation in operations:

                    if not flg_is_prerequisite_on_multiple_hosts:
                        if operation.get_host_ip()==my_host_ip or \
                            DynamicPrerequisiteFulfillness.is_single_type_host(operation):
                                return  operation._get_is_passed() == True  #return False if not or if None

                    else:
                        flg_prerequisite_found = True
                        if flg_any:
                            if operation._get_is_passed():
                                return True
                        else:
                            if not operation._get_is_passed():
                                return False

        if not flg_prerequisite_found:
            assert "{} has prerequisite on {} but {} is not in this flow ".format(my_unique_name,
                                                                                other_unique_operation_name,
                                                                                other_unique_operation_name)
        if flg_any:
            return False
        else:
            return True

    @staticmethod
    def is_single_type_host(operator):
        my_roles=operator.get_host_roles()
        flg_is_single_type = PythonUtils.list_intersection(my_roles, Objectives.get_all_single_types())
        return flg_is_single_type

    @staticmethod
    def validate_prerequisite(sys_operation_per_host, operations_list_of_a_flow):

        if not sys_operation_per_host._prerequisite_unique_operation_name:
            return True

        flg_prerequisite_fulfilled = DynamicPrerequisiteFulfillness.is_a_prerequisite_fulfilled\
            (my_unique_name = sys_operation_per_host.get_unique_name(),
             my_host_ip=sys_operation_per_host.get_host_ip(),
             other_unique_operation_name=sys_operation_per_host._prerequisite_unique_operation_name,
             operations_list_of_a_flow=operations_list_of_a_flow,
             flg_is_prerequisite_on_multiple_hosts=sys_operation_per_host._is_prerequisite_on_multiple_hosts,
             flg_any=sys_operation_per_host._is_prerequisite_pass_if_any_passed)

        if sys_operation_per_host._flg_run_only_if_prerequisite_failed:
            return not flg_prerequisite_fulfilled

        if not flg_prerequisite_fulfilled:
            global_logging.log_and_print(
                "Operation {} on {} will not run, prerequisite '{}' was not fulfilled".format(
                    sys_operation_per_host.get_unique_name(),
                    sys_operation_per_host.get_host_ip(),
                    sys_operation_per_host._prerequisite_unique_operation_name))

        return flg_prerequisite_fulfilled

    @staticmethod
    def all_prerequisite_fulfilled(sys_operation_per_host, operations_list_of_a_flow):

        ok = DynamicPrerequisiteFulfillness.validate_prerequisite(sys_operation_per_host=sys_operation_per_host,
                                                                  operations_list_of_a_flow=operations_list_of_a_flow)

        return ok

class ParallelRunner:
    data_collector_db = {}

    @classmethod
    def run_data_collector_on_all_host(cls, collectors_list, printer, is_many_to_one, **kwargs):
        if is_many_to_one:
            target = ParallelRunner.run_DataCollector_many_to_one
        else:
            target = ParallelRunner.run_DataCollector_on_one_host
        ParallelRunner.run_operator_on_all_hosts(collectors_list,target, printer, **kwargs)

    @staticmethod
    def run_validation_flows_on_all_host(operations_list_of_a_flow, printer):
        target = ParallelRunner.run_validation_on_one_host
        for validators_list in operations_list_of_a_flow:
            ParallelRunner.run_operator_on_all_hosts(validators_list, target, printer)
        ParallelRunner.data_collector_db.clear()

    @staticmethod
    def run_SystemOperator_on_all_host(operations_list_of_a_flow, printer):
        target = ParallelRunner.run_validation_on_one_host
        for sys_operation in operations_list_of_a_flow:
            to_run_list = []
            for sys_operation_per_host in sys_operation:
                flg_should_run = DynamicPrerequisiteFulfillness.all_prerequisite_fulfilled(sys_operation_per_host,
                                                                                           operations_list_of_a_flow)
                if not flg_should_run:
                    pass
                else:
                    to_run_list.append(sys_operation_per_host)
            #if any operations to run
            if not to_run_list:
                pass
            else:
                if sys_operation[0]._get_printable_title():
                    log_and_print('\n===========  {}  ==========='.format(sys_operation[0]._printable_title))
                if sys_operation[0]._run_in_parallel:
                    ParallelRunner.run_operator_on_all_hosts(to_run_list, target, printer)
                else:
                    ParallelRunner.run_serial_on_all_hosts(to_run_list, target, printer)

    @staticmethod
    def run_operator_on_all_hosts(operator_list,target, printer, **kwargs):
        ParallelRunner.run_target_in_parallel(operator_list, target, printer, **kwargs)
        return 0

    @staticmethod
    def run_target_in_parallel(operator_list, target, *args, **kwargs):
        thread_list = []
        for hosted_validator_instance in operator_list:
            if kwargs:
                thread = threading.Thread(target=target,
                                          args=(hosted_validator_instance,) + args, kwargs=kwargs)
            else:
                thread = threading.Thread(target=target,
                                          args=(hosted_validator_instance,) + args)

            thread.daemon = True
            thread_list.append(thread)
            thread.start()

        for thread in thread_list:
            thread.join()
        if operator_list:
            msg = "Ice peak memory on {}: {}".format(operator_list[0].__class__.__name__,
                                                     ExecutionHelper.get_memory_used()["peak"])
            global_logging.log(msg)
            if tools.user_params.debug:
                print(msg)

    @staticmethod
    def run_serial_on_all_hosts(operator_list,target, printer, **kwargs):

        for hosted_validator_instance in operator_list:

            if kwargs:
                target(hosted_validator_instance, printer, kwargs)
            else:
                target(hosted_validator_instance, printer,)

        return 0

    @staticmethod
    def get_run_time_untill_now(start_wall_time, start_cpu_time):
        end_wall_time = time.time()
        end_cpu_time = get_default_timer()

        run_time = {"wall": (end_wall_time - start_wall_time), "clock": end_cpu_time - start_cpu_time}
        return run_time

    @classmethod
    def _load_data_collector_many_to_one(cls, hosted_collector_instance, **kwargs):
        class_name = hosted_collector_instance.__class__.__name__
        host_name = hosted_collector_instance.get_host_name()
        is_clean_cmd_info = hosted_collector_instance.is_clean_cmd_info()
        str_kwargs = PythonUtils.convert_dict_to_str_sort_keys(kwargs)
        try:
            cls.data_collector_db.setdefault(class_name, {}).setdefault(host_name, {}).setdefault(
                is_clean_cmd_info, {}).setdefault(str_kwargs, {})["data"] = \
                hosted_collector_instance.collect_data(**kwargs)
        except Exception as e:
            cls.data_collector_db.setdefault(class_name, {}).setdefault(host_name, {}).setdefault(
                is_clean_cmd_info, {}).setdefault(str_kwargs, {})["exception"] = {e: get_full_trace()}
        finally:
            cls.data_collector_db.setdefault(class_name, {}).setdefault(host_name, {}).setdefault(
                is_clean_cmd_info, {}).setdefault(str_kwargs, {})["bash_cmd_lines"] = \
                hosted_collector_instance.get_bash_cmd_lines()
            cls.data_collector_db.setdefault(class_name, {}).setdefault(host_name, {}).setdefault(
                is_clean_cmd_info, {}).setdefault(str_kwargs, {})["validation_log"] = \
                hosted_collector_instance.get_validation_log()

    @classmethod
    def run_DataCollector_many_to_one(cls, hosted_collector_instance, printer, **kwargs):
        class_name = hosted_collector_instance.__class__.__name__
        host_name = hosted_collector_instance.get_host_name()
        is_clean_cmd_info = hosted_collector_instance.is_clean_cmd_info()
        host_ip = hosted_collector_instance.get_host_ip()
        start_wall_time = ParallelRunner.get_start_wall_time(hosted_collector_instance)
        assert hasattr(hosted_collector_instance, "collect_data")
        if ParallelRunner.is_current_data_collector_db_empty(class_name, host_name, is_clean_cmd_info, **kwargs):
            with hosted_collector_instance.threadLock:
                if ParallelRunner.is_current_data_collector_db_empty(class_name, host_name, is_clean_cmd_info, **kwargs):
                    cls._load_data_collector_many_to_one(hosted_collector_instance, **kwargs)
        assert not ParallelRunner.is_current_data_collector_db_empty(class_name, host_name, is_clean_cmd_info, **kwargs)\
            , "Failed to load DataCollector_many_to_one"
        current_data_collector = cls.data_collector_db[class_name][host_name][is_clean_cmd_info][
            PythonUtils.convert_dict_to_str_sort_keys(kwargs)]
        bash_cmd_lines = current_data_collector["bash_cmd_lines"]
        if "data" in list(current_data_collector.keys()):
            printer.add_data(host_name=host_name, data=current_data_collector["data"],
                             validation_log=current_data_collector["validation_log"], bash_cmd_lines=bash_cmd_lines)
        ParallelRunner.calculate_end_wall_time(hosted_collector_instance, start_wall_time)
        if current_data_collector.get("exception"):
            ParallelRunner.handle_run_data_collector_exception(
                e=list(current_data_collector["exception"].keys())[0], class_name=class_name, host_name=host_name,
                host_ip=host_ip, data=current_data_collector.get("data", None),
                validation_log=current_data_collector["validation_log"], bash_cmd_lines=bash_cmd_lines,
                printer=printer, full_trace=list(current_data_collector["exception"].values())[0])

    @classmethod
    def is_current_data_collector_db_empty(cls, class_name, host_name, is_clean_cmd_info, **kwargs):
        data_collector_db_keys = list(cls.data_collector_db.get(class_name, {}).get(host_name, {})\
            .get(is_clean_cmd_info, {}).get(PythonUtils.convert_dict_to_str_sort_keys(kwargs), {}).keys())
        if {"data", "exception"}.intersection(set(data_collector_db_keys)):
            missing_keys_list = {"bash_cmd_lines", "validation_log"}.difference(set(data_collector_db_keys))
            assert len(missing_keys_list) == 0, "Failed to load {} for DataCollector_many_to_one".format(missing_keys_list)
            return False
        return True

    @staticmethod
    def handle_run_data_collector_exception(e, class_name, host_name, host_ip, data, validation_log,
                                            bash_cmd_lines, printer, full_trace=None):
        if not full_trace:
            full_trace = get_full_trace()
        exceptions = full_trace
        if isinstance(e, UnExpectedSystemOutput):
            caller_class_name = inspect.getouterframes(inspect.currentframe(), 2)[1][3]
            message = "UnExpectedSystemOutput raised from {} of class {} at host {} {} :" .format(
                caller_class_name, class_name, host_name, host_ip)
            exceptions = message + full_trace
        printer.add_data(host_name=host_name, data=data, validation_log=validation_log, bash_cmd_lines=bash_cmd_lines,
                         exception=exceptions)
        if tools.user_params.debug:
            raise e

    @staticmethod
    def run_DataCollector_on_one_host(hosted_collector_instance, printer, **kwargs):
        #assert isinstance(hosted_collector_instance,
        #                  DataCollector), "Error found while initializing DataCollector. Please refer to developer"

        class_name = hosted_collector_instance.__class__.__name__
        host_name = hosted_collector_instance.get_host_name()
        host_ip = hosted_collector_instance.get_host_ip()
        data = None
        try:
            start_wall_time = ParallelRunner.get_start_wall_time(hosted_collector_instance)
            assert hasattr(hosted_collector_instance, "collect_data")
            data = hosted_collector_instance.collect_data(**kwargs)
            printer.add_data(host_name=host_name, data=data,
                             validation_log=hosted_collector_instance.get_validation_log(),
                             bash_cmd_lines=hosted_collector_instance.get_bash_cmd_lines())
            ParallelRunner.calculate_end_wall_time(hosted_collector_instance, start_wall_time)

        except Exception as e:
            ParallelRunner.handle_run_data_collector_exception(
                e=e, class_name=class_name, host_name=host_name, host_ip=host_ip, data=data,
                validation_log=hosted_collector_instance.get_validation_log(),
                bash_cmd_lines=hosted_collector_instance.get_bash_cmd_lines(), printer=printer)

    @staticmethod
    def print_exception(e, printer, hosted_validator_instance, in_maintenance):
        full_trace = get_full_trace()

        if isinstance(e, UnExpectedSystemOutput):
            printer.print_basic_problem(
                problem_name=Status.SYS_PROBLEM.value,
                unique_operation_name=hosted_validator_instance.get_unique_name(),
                title_description=hosted_validator_instance.title_description(),
                severity=hosted_validator_instance.get_severity(),
                implication_tags=hosted_validator_instance.get_implication_tags(),
                describe_msg=e.message,
                exception=full_trace,
                host_ip=hosted_validator_instance.get_host_ip(),
                host_name=hosted_validator_instance.get_host_name(),
                bash_cmd_lines=hosted_validator_instance.get_bash_cmd_lines(),
                validation_log=hosted_validator_instance.get_validation_log(),
                blocking_tags=hosted_validator_instance.get_blocking_tags(),
                documentation_link=hosted_validator_instance.get_documentation_link(),
                in_maintenance=in_maintenance)

        elif isinstance(e, NotApplicable):
            printer.print_basic_problem(
                problem_name="not_applicable",
                unique_operation_name=hosted_validator_instance.get_unique_name(),
                title_description=hosted_validator_instance.title_description(),
                severity=hosted_validator_instance.get_severity(),
                implication_tags=hosted_validator_instance.get_implication_tags(),
                describe_msg="Validation is not applicable to the system - {}".format(str(e)),  # str(e),
                exception=full_trace,
                host_ip=hosted_validator_instance.get_host_ip(),
                host_name=hosted_validator_instance.get_host_name(),
                bash_cmd_lines=hosted_validator_instance.get_bash_cmd_lines(),
                validation_log=hosted_validator_instance.get_validation_log(),
                blocking_tags=hosted_validator_instance.get_blocking_tags(),
                in_maintenance=in_maintenance)

        elif isinstance(e, NoSuitableHostWasFoundForRoles):
            printer.print_basic_problem(
                problem_name="no_connected_host_was_found_for_role",
                unique_operation_name=hosted_validator_instance.get_unique_name(),
                title_description=hosted_validator_instance.title_description(),
                severity=hosted_validator_instance.get_severity(),
                implication_tags=hosted_validator_instance.get_implication_tags(),
                describe_msg="Validation cannot run- a required host is not connected - {}".format(str(e)),
                # str(e),
                exception=full_trace,
                host_ip=hosted_validator_instance.get_host_ip(),
                host_name=hosted_validator_instance.get_host_name(),
                bash_cmd_lines=hosted_validator_instance.get_bash_cmd_lines(),
                validation_log=hosted_validator_instance.get_validation_log(),
                blocking_tags=hosted_validator_instance.get_blocking_tags(),
                in_maintenance=in_maintenance)
        else:
            printer.print_not_performed(
                unique_operation_name=hosted_validator_instance.get_unique_name(),
                title_description=hosted_validator_instance.title_description(),
                severity=hosted_validator_instance.get_severity(),
                implication_tags=hosted_validator_instance.get_implication_tags(),
                exception=full_trace,
                describe_msg="Unexpected error (details in the .json file)",
                host_ip=hosted_validator_instance.get_host_ip(),
                host_name=hosted_validator_instance.get_host_name(),
                bash_cmd_lines=hosted_validator_instance.get_bash_cmd_lines(),
                validation_log=hosted_validator_instance.get_validation_log(),
                blocking_tags=hosted_validator_instance.get_blocking_tags(),
                documentation_link=hosted_validator_instance.get_documentation_link(),
                in_maintenance=in_maintenance)

    @staticmethod
    def get_start_wall_time(hosted_operator_instance):
        start_wall_time = None
        if tools.user_params.debug:
            start_wall_time = time.time()
            print("start: {} on {}".format(hosted_operator_instance.__class__.__name__,
                                           hosted_operator_instance.get_host_ip()))
        return start_wall_time


    @staticmethod
    def calculate_end_wall_time(hosted_operator_instance, start_wall_time):
        if tools.user_params.debug:
            end_wall_time = time.time()
            print("end: {} on {} time: {} ".format(hosted_operator_instance.__class__.__name__,
                                                   hosted_operator_instance.get_host_ip(),
                                                   (end_wall_time - start_wall_time)))

    @staticmethod
    def run_validation_on_one_host(hosted_validator_instance, printer):

        #assert isinstance(hosted_validator_instance,
        #                  Validator), "Error found while initializing validators. Please refer to developer"
        assert hasattr(hosted_validator_instance, "get_unique_name")
        in_maintenance = True if Objectives.MAINTENANCE in hosted_validator_instance.get_host_roles() else False

        try:
            start_wall_time = ParallelRunner.get_start_wall_time(hosted_validator_instance)

            start_wall_time = time.time()
            start_cpu_time = get_default_timer()
            flg_ok = True

            if hasattr(hosted_validator_instance, 'is_validation_passed'):
                flg_ok = hosted_validator_instance.is_validation_passed()
                if hasattr(hosted_validator_instance, 'is_pure_info'):
                    if hosted_validator_instance.is_pure_info(): # if if declared pure info no meaning to is_validation_passed
                        flg_ok = True

            if hasattr(hosted_validator_instance, 'run_system_operation'):
                flg_ok = hosted_validator_instance.run_system_operation()
                hosted_validator_instance._set_passed(flg_ok)

            run_time = ParallelRunner.get_run_time_untill_now(start_wall_time,start_cpu_time)

            flg_only_info = False

            if hasattr(hosted_validator_instance, 'get_system_info'):
            #if isinstance(hosted_validator_instance, InformatorValidator):

                # if there is system info to present in the report
                sys_info_title = hosted_validator_instance.get_system_info_title()
                sys_info = hosted_validator_instance.get_system_info()
                flg_only_info = hosted_validator_instance.is_pure_info()
                run_time = ParallelRunner.get_run_time_untill_now(start_wall_time, start_cpu_time)

                if sys_info is not None:
                    printer.print_system_info(
                        unique_operation_name="info_" + hosted_validator_instance.get_unique_name(),
                        title_description=sys_info_title,
                        host_ip=hosted_validator_instance.get_host_ip(),
                        host_name=hosted_validator_instance.get_host_name(),
                        bash_cmd_lines=hosted_validator_instance.get_bash_cmd_lines(),
                        validation_log=hosted_validator_instance.get_validation_log(),
                        system_info=sys_info,
                        implication_tags=hosted_validator_instance.get_implication_tags(),
                        table_system_info=hosted_validator_instance.get_table_system_info(),
                        is_highlighted_info=hosted_validator_instance.is_highlighted_info(),
                        run_time=run_time,
                        in_maintenance=in_maintenance,
                        documentation_link=hosted_validator_instance.get_documentation_link(),
                    )

            assert flg_ok is not None, "Forgot to return value at " + hosted_validator_instance.get_unique_name()

            assert type(flg_ok) is bool, "Return value is not boolean at " + hosted_validator_instance.get_unique_name()

        except Exception as e:
            if tools.user_params.debug:
                raise

            if hasattr(hosted_validator_instance, 'run_system_operation'):
                hosted_validator_instance._set_passed(False)

            if isinstance(e, LazyDataLoaderPreviousLoadProblem):
                e = e.previous_exception

            ParallelRunner.print_exception(e,
                                           printer,
                                           hosted_validator_instance,
                                           in_maintenance)

        else:
            if not flg_ok:
                printer.print_failed(
                    unique_operation_name=hosted_validator_instance.get_unique_name(),
                    title_description=hosted_validator_instance.title_description(),
                    severity=hosted_validator_instance.get_severity(),
                    implication_tags=hosted_validator_instance.get_implication_tags(),
                    describe_msg=hosted_validator_instance.describe_when_validation_fails(),
                    host_ip=hosted_validator_instance.get_host_ip(),
                    host_name=hosted_validator_instance.get_host_name(),
                    bash_cmd_lines=hosted_validator_instance.get_bash_cmd_lines(),
                    validation_log=hosted_validator_instance.get_validation_log(),
                    run_time=run_time,
                    documentation_link=hosted_validator_instance.get_documentation_link(),
                    blocking_tags=hosted_validator_instance.get_blocking_tags(),
                    in_maintenance=in_maintenance
                )
            else:
                # list_of_successful_validations.append(hosted_validator_instance.get_unique_name())

                if not flg_only_info:  # note that this can be true only for info types
                    printer.print_ok(
                        unique_operation_name=hosted_validator_instance.get_unique_name(),
                        title_description=hosted_validator_instance.title_description(),
                        host_ip=hosted_validator_instance.get_host_ip(),
                        host_name=hosted_validator_instance.get_host_name(),
                        bash_cmd_lines=hosted_validator_instance.get_bash_cmd_lines(),
                        severity=hosted_validator_instance.get_severity(),
                        implication_tags=hosted_validator_instance.get_implication_tags(),
                        validation_log=hosted_validator_instance.get_validation_log(),
                        run_time=run_time,
                        blocking_tags=hosted_validator_instance.get_blocking_tags(),
                        in_maintenance=in_maintenance)
        ParallelRunner.calculate_end_wall_time(hosted_validator_instance, start_wall_time)
