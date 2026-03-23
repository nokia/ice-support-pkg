from __future__ import absolute_import
from __future__ import print_function
import atexit
import signal
import sys
from tools.python_versioning_alignment import get_full_trace
import tools.user_params
from HealthCheckCommon.operations import Operator
from HealthCheckCommon.printer import StructedPrinter
from HealthCheckCommon.secret_filter import SecretFilter
from tools.ExecutionModule.HostExecutorsFactory.HostExecutor import HostExecutor
from tools.ExecutionModule.execution_helper import ExecutionHelper
from tools.Info import *
from tools.lazy_global_data_loader import clean_lazy_global_data_loader
from six.moves import filter

sys.path.append('./PythonLibraries/')
try:
    import redis
except ImportError:
    from PythonLibraries import redis
import argparse
import sys
import json
import datetime
import tools.paths as paths
import tools.global_logging as log
import tools.SecurityHelper as Sec
import tools.sys_parameters as sys_parameters
import tools.DynamicPaths as DynamicPaths
from PreFlowValidations import PreFlowValidations
import interactive_actions as interactive_actions
from tools.popen_utils import PopenTimeOut
import os
import resource


class BasicMainClass(object):
    RUNNING_TIMEOUT = 60 * 60 * 24

    FILES_TO_COPY_FIRST = [
        "/etc/passwd",
        "/etc/group"
    ]

    #todo: check if all the list is realy needed
    #particularly is needed: authorized_keys ,id_rsa.pub, known_hosts
    FILES_TO_COPY = [
        "/home/stack/user_config.yaml",
        "/etc/ssl/certs/ca-bundle.crt",
        "/home/cbis-admin/.ssh/authorized_keys",
        "/home/cbis-admin/.ssh/id_rsa",
        "/home/cbis-admin/.ssh/id_rsa.pub",
        "/home/cbis-admin/.ssh/known_hosts",
        "/home/stack/.ssh/authorized_keys",
        "/home/stack/.ssh/id_rsa",
        "/home/stack/.ssh/id_rsa.pub",
        "/home/stack/.ssh/known_hosts",
        "/opt/bcmt/bcmt_config.json",
    ]

    FOLDERS_TO_COPY = [
      #  "/home/cbis-admin/.ssh/",
      #  "/home/stack/.ssh/"
    ]

    def __init__(self):
        self._no_out_files = False
        self._flg_quiet = False
        self._invoker = None

        self._set_running_timeout()

    def _set_running_timeout(self):
        signal.signal(signal.SIGALRM, BasicMainClass._timeout_handler)
        signal.alarm(self.RUNNING_TIMEOUT)

    @staticmethod
    def _timeout_handler(signum, frame):
        print("Process timed out after {} seconds and was terminated.".format(BasicMainClass.RUNNING_TIMEOUT))
        HostExecutor.running_timeout_exceeded = True
        atexit._run_exitfuncs()
        os._exit(1)

    def _set_invoker(self, version, deployment_type, only_specific_hosts_list=None, roles=None,
                     specific_validations=None, specific_tags=None):
        assert False, "implement me !"

    def _get_flows_dict(self):
        assert False, "implement me !"

    def _run_flows_dict(self, flow_dict):
        assert False, "implement me !"

    def _run_and_get_result(self):
        assert False, "implement me !"

    def _add_based_argument_for_argparse(self):
        assert False, "implement me !"

    def _add_argument_for_argparse(self):
        pass

    def _create_summary_operations(self, cluster_name=""):
        assert False

    def _get_cluster_names(self):
        str_err_format = "cmd: '{cmd}', error: '{err}'"
        failed_cmd_list = []
        cmd = ""
        try:
            cmd = "redis.Redis().get('cmdata.clusters')"
            cluster_names_out = redis.Redis().get('cmdata.clusters')
            cluster_names_list = cluster_names_out.strip('\n[]').split(", ")
        except Exception as e:
            failed_cmd_list.append(str_err_format.format(cmd=cmd, err=str(e)))
            try:
                clusters_path = paths.NCS_BM_CLUSTER_DATA_DIR
                cmd = "ls {}".format(clusters_path)
                sub_dir_clusters_list = [os.path.join(clusters_path, f) for f in os.listdir(clusters_path)]
                cluster_names_list = [f.split('/')[-1] for f in sub_dir_clusters_list if os.path.isdir(f)]
            except Exception as e:
                failed_cmd_list.append(str_err_format.format(cmd=cmd, err=str(e)))
                if self._args.debug:
                    print("No NCS clusters were found.\nNo output from the commands:\n{}"
                          .format('\n'.join(failed_cmd_list)))
                return None
        if self._args.debug:
            print("The following clusters were found: {}, by the command '{}'".format(cluster_names_list, cmd))
        return cluster_names_list

    def limit_memory(self, maxsize, free_memory):
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        if hard == -1:
            hard = free_memory
        resource.setrlimit(resource.RLIMIT_AS, (int(maxsize), int(hard)))


    def creat_arg_parser(self,parser_description):
        self._parser = self._create_parser(parser_description)
        self._add_based_argument_for_argparse()
        self._add_argument_for_argparse()
        args = self._parser.parse_args()
        self._args = args


    def run_me(self, parser_description):

        self.creat_arg_parser(parser_description)

        ExecutionHelper.init_configuration()
        self._init_local_operators()

        if ExecutionHelper.is_run_inside_container():
            self._prepare_container_for_running()
        ExecutionHelper.validate_connectivity_to_host()
        memory_free = ExecutionHelper.get_free_memory()
        GIGA_IN_BYTES = 1073741824
        THRESHOLD_IN_GIGA = 1
        memory_threshold = GIGA_IN_BYTES * THRESHOLD_IN_GIGA
        if memory_free < memory_threshold:
            print(
                "error: We are limiting Healthcheck to run on system that has at least {} GB free memory.\nAvailable free memory: {} GB".format(
                    THRESHOLD_IN_GIGA, (float(memory_free)/GIGA_IN_BYTES)))
            if self._args.ncs_manager:
                sys.exit(1)
            return
        MAXSIZE_THRESHOLD = memory_free * 0.8
        self.limit_memory(MAXSIZE_THRESHOLD, memory_free)
        # Next line is a workaround for AttributeError: _strptime when using multiple threads
        datetime_object = datetime.datetime.strptime('Sun 26 Jul 2020 12:33:09 PM', "%a %d %b %Y %H:%M:%S %p")

        only_central_clusters = True
        cluster_names_list = self._get_cluster_names()
        return_code = 0
        if self._args.ncs_bm_cluster_name and ExecutionHelper.is_central_cluster(self._args.ncs_bm_cluster_name[0]):
            print("Healthcheck can't be run on central clusters. Please provide a different cluster name")
        elif cluster_names_list and not self._args.ncs_bm_cluster_name:
            for cluster_name in cluster_names_list:
                if not ExecutionHelper.is_central_cluster(cluster_name):
                    only_central_clusters = False
                    self._args.ncs_bm_cluster_name = cluster_name.strip('"')
                    try:
                        result = self._run_and_get_result()
                        if result["return_code"] == 1:
                            self.log_and_print_result_dict(result)
                        return_code = result["return_code"] if result["return_code"] else return_code
                    except:
                        exception = get_full_trace()
                        if StructedPrinter.encrypt_out:
                            exception = SecretFilter.filter_string_array(exception)
                        log.log_and_print(exception)
                        continue
                    finally:
                        clean_lazy_global_data_loader()
            if only_central_clusters:
                print("Healthcheck can't be run as having only central clusters.\nDeployment clusters are: {}".format(
                    cluster_names_list))
        else:
            if self._args.ncs_bm_cluster_name:
                self._args.ncs_bm_cluster_name = self._args.ncs_bm_cluster_name[0]
            result = self._run_and_get_result()
            if result["return_code"] == 1:
                self.log_and_print_result_dict(result)
            return_code = result["return_code"] if result["return_code"] else return_code
        if return_code and self._args.ncs_manager:
            sys.exit(return_code)

    def log_and_print_result_dict(self, result):
        log.log_and_print("RESULT:")
        log.log_and_print(json.dumps(result["details"], indent=4))

    def _prepare_container_for_running(self):
        for file_path in self.FILES_TO_COPY_FIRST:
            ExecutionHelper.copy_single_file_to_container(file_path, file_path)

        host_operator = ExecutionHelper.get_hosting_operator(False)
        folders = list(filter(host_operator.file_utils.is_file_exist, self.FOLDERS_TO_COPY))
        files = list(filter(host_operator.file_utils.is_file_exist, self.FILES_TO_COPY))

        for folder in folders:
            files += [os.path.join(folder, file_in_folder) for file_in_folder in
                      host_operator.file_utils.get_dir_content(folder)]
        files = self._filter_mounted_files(files)

        folders_to_create = set(os.path.dirname(file_path) for file_path in files)
        folders_to_create = list([_f for _f in folders_to_create if _f])

        user_uid = ExecutionHelper.get_local_uid()
        user_gid = ExecutionHelper.get_local_gid()
        local_operator = ExecutionHelper.get_local_operator(is_log_initialized=False)

        for folder in folders_to_create:
            local_operator.get_output_from_run_cmd("sudo mkdir -p {}".format(folder))
            local_operator.get_output_from_run_cmd("sudo chown {}:{} {}".format(user_uid, user_gid,  folder))

        for path in files:
            file_path = host_operator.get_output_from_run_cmd("sudo readlink -f  {}".format(path)).strip()
            ExecutionHelper.copy_single_file_to_container(file_path, path)
            local_operator.get_output_from_run_cmd("sudo chown {}:{} {}".format(user_uid, user_gid, path))

    def _filter_mounted_files(self, files):
        return set([f for f in files if "ice_container_key" not in f])

    def _create_parser(self, parser_description):
        return argparse.ArgumentParser(description=parser_description,
                                       formatter_class=argparse.RawTextHelpFormatter)

    def _init_local_operators(self):
        host_host_executor = HostExecutor(ip="localhost", host_name="host_host_executor", is_local=False,
                                          user_name=ExecutionHelper.get_host_username(),
                                          key_file=ExecutionHelper.get_path_to_pkey_from_container_to_host(),
                                          is_log_initialized=False)
        host_host_executor.connect_ssh_client()

        local_host_executor = HostExecutor(ip="localhost", host_name="ice_container", user_name="", is_local=True)

        ExecutionHelper.init_hosting_operator(Operator(host_host_executor))
        ExecutionHelper.init_local_operator(Operator(local_host_executor))

# ------------------------------------------------------------------------------------------------------------------
class MainBase(BasicMainClass):
    def print_about_text(self):
        with open(paths.ABOUT_FILE, 'r') as about_file:
            about_text = about_file.read()
            print(about_text)

    def get_dict_result(self, return_code, message):
        return {
            "return_code": return_code,
            "details": message
        }

    def connect_to_HV_via_args(self, user_name, encrypted_pass, hypervisor_host_name):
        is_key_file_exist, message = PreFlowValidations.validate_key_file_exist(paths.ENCRYPTION_KEY)
        if not is_key_file_exist:
            return False, message
        password = Sec.decrypt_message_by_key_file(encrypted_pass, paths.ENCRYPTION_KEY)
        is_connected = sys_parameters.get_host_executor_factory().reconnect_host_by_password(
            hypervisor_host_name, user_name, password=password)
        message = "" if is_connected else "Cannot connect to hypervisor using given credentials"
        return is_connected, message

    def init_global_sys_parameters(self):
        arguments = self._args

        DynamicPaths.init_paths_by_user_args(arguments.ncs_bcmt_config_path, arguments.ncs_clcm_user_input_path)
        sys_parameters.init_globals()
        is_ok, deployment_type_msg, deployment_type = tools.user_params.initialization_factory.initialize(
            tools.user_params.debug)
        if not is_ok:
            return is_ok, None, deployment_type_msg, None

        is_ok, msg = DynamicPaths.init_run_time_paths(deployment_type, arguments.ncs_bm_cluster_name)
        if not is_ok:
            return is_ok, None, msg, None

        # is_ok, msg = sys_parameters.initialization_factory.activate(arguments.version)
        is_ok, msg = tools.user_params.initialization_factory.activate(None)
        if not is_ok:
            return is_ok, None, msg, None

        return is_ok, msg, deployment_type_msg, deployment_type

    def is_HV_connected(self):
        is_connectivity_ok, not_connected_hosts = PreFlowValidations.validate_connectivity(
            sys_parameters.get_deployment_type(),
            sys_parameters.get_host_executor_factory())
        return is_connectivity_ok

    def connect_to_HV(self):
        '''
          check if particular hosts are connected and reconnect if needed
        '''
        arguments = self._args
        is_connectivity_ok, not_connected_hosts = PreFlowValidations.validate_connectivity(
            sys_parameters.get_deployment_type(),
            sys_parameters.get_host_executor_factory())

        if not is_connectivity_ok and \
                not arguments.get_available_flows and \
                not arguments.do_not_connect_hyp and not \
                arguments.get_available_flows_with_details:
            if arguments.hyp_pass or arguments.hyp_user:
                is_connected, message = self.connect_to_HV_via_args(
                    arguments.hyp_user[0], arguments.hyp_pass[0], not_connected_hosts[0])
                if not is_connected:
                    return self.get_dict_result(1, message)
            else:
                interactive_actions.ssh_with_password(not_connected_hosts)
        return True, ""

    def get_only_specific_hosts_list(self):

        only_specific_hosts_list = None

        arguments = self._args
        if arguments.hosts:
            is_host_list_valid, invalid_hosts = sys_parameters.get_host_executor_factory().check_if_host_list_exists(
                arguments.hosts)
            if not is_host_list_valid:
                return False, "Hosts {} doesn't exist in the system".format(str(invalid_hosts)), None
            only_specific_hosts_list = sys_parameters.get_host_executor_factory().get_relevant_hosts_list(
                arguments.hosts)

        return True, "", only_specific_hosts_list

    # ------------------------------------------------------------------------------------------------------------------

    def _prepare_system(self):
        arguments = self._args
        self._deployment_type_msg = None
        self._deployment_type = None
        self._host_name_list = None
        self._ice_version = GetInfo.get_ice_version()
        self._ice_version_date = GetInfo.get_ice_version_date()
        # self._summary_operations = SummaryFilesOperations() #prepering place for output

        if arguments.quiet:
            self._flg_quiet = True
        if arguments.no_out_files:
            self._no_out_files = True

        self._summary_operations = self._create_summary_operations(cluster_name=arguments.ncs_bm_cluster_name)

        if arguments.ice_version:
            print(self._ice_version)
            return self.get_dict_result(0, "")

        if arguments.about:
            self.print_about_text()
            return self.get_dict_result(0, "")

        if arguments.debug:
            tools.user_params.debug = True

        if arguments.ncs_manager:
            tools.user_params.print_documentation_link = False

        if arguments.path_to_cbis_hosts_file:
            tools.user_params.path_to_cbis_hosts_file = arguments.path_to_cbis_hosts_file

        if arguments.limited_output:
            tools.user_params.limited_output = True

        if arguments.additional_comments:
            tools.user_params.additional_comments = arguments.additional_comments

        if self._summary_operations:  # in case of unit test it is not called
            log.init(self._summary_operations.get_logger_path(), debug=arguments.debug, quiet=self._flg_quiet or self._no_out_files)
        else:
            log.init()

        ok, msg, self._deployment_type_msg, self._deployment_type = self.init_global_sys_parameters()

        if not ok:
            log.log_and_print(msg, 'error') if self._deployment_type_msg else log.log_and_print(msg, 'error')
            return self.get_dict_result(1, self._deployment_type_msg)

        ok, msg, self._only_specific_hosts_list = self.get_only_specific_hosts_list()

        if not ok:
            if msg:
                log.log_and_print(msg, 'error')
            return self.get_dict_result(1, self._deployment_type_msg)

        self._roles_map = sys_parameters.get_host_executor_factory().get_roles_map_dict()

        if not ok:
            return self.get_dict_result(1, msg)

        flg_is_HV_connected = self.is_HV_connected()

        if arguments.is_hyp_connected:
            res = 1 if flg_is_HV_connected else 0
            result = self.get_dict_result(0, res)
            self.log_and_print_result_dict(result)
            return result

        if not flg_is_HV_connected:
            ok, msg = self.connect_to_HV()
            if not ok:
                return self.get_dict_result(1, msg)

        if arguments.ask_openstack_password:
            interactive_actions.set_openstack_password_env()

        if arguments.print_roles_hosts_map:
            result = self.get_dict_result(0, {"available hosts and roles are ": self._roles_map})
            self.log_and_print_result_dict(result)
            return result



        if not ok:
            return self.get_dict_result(1, msg)

        return True

    def _run_and_get_result(self):

        arguments = self._args

        res = self._prepare_system()

        if res is not True:
            return res
        specific_validations_list = self._get_specific_validations_list()
        specific_tags_list = self._get_specific_tags_list()
        self._set_invoker(sys_parameters.get_version(), sys_parameters.get_deployment_type(),
                          self._only_specific_hosts_list, arguments.roles,
                          specific_validations=specific_validations_list,
                          specific_tags=specific_tags_list)

        assert (self._invoker is not None)

        log.logger.info("...initializing invoker...")
        flow_dict = self._get_flows_dict()
        available_flows_with_titles = self._invoker.get_available_flows_with_titles(flow_dict)
        #  return available validation/sys_operation if requested
        if arguments.get_available_flows:
            result = self.get_dict_result(0, {
                'available flows for this system are:': available_flows_with_titles
            })
            self.log_and_print_result_dict(result)
            return result

        #  return available validations with details if requested
        if arguments.get_available_flows_with_details:
            result = self.get_dict_result(0, {
                'available flows for this system are:': self._invoker.get_available_flows_with_details(flow_dict)
            })
            self.log_and_print_result_dict(result)
            return result

        #  run validations and return result
        if not flow_dict:
            return self.get_dict_result(1, "no flows to run")

        log.logger.info("Flow list : {}".format(json.dumps(available_flows_with_titles, indent=4)))
        log.logger.info("Start running health checking")
        log.logger.info(str(arguments))
        log.log_and_print("\nHealth check version {} starting:".format(self._ice_version))
        log.log_and_print('Deployment-type: {}'.format(self._deployment_type))
        if sys_parameters.get_cluster_name():
            log.log_and_print('Cluster name: {}'.format(sys_parameters.get_cluster_name()))
        log.log_and_print('Host name: {}'.format(ExecutionHelper.get_local_host_name()))
        log.log_and_print('Deployment type detection message:\n{}'.format(self._deployment_type_msg))

        return self._run_flows_dict(flow_dict)

    def _get_specific_validations_list(self):
        return None

    def _get_specific_tags_list(self):
        return None


    # ----------------------------------------------------------------------------------------------------------------------
    def _add_based_argument_for_argparse(self):
        assert isinstance(self._parser, argparse.ArgumentParser)

        self._parser.add_argument('--about', action='store_true',
                                  help='Know more about the health checks')

        self._parser.add_argument('--ice-version', action='store_true',
                                  help='Get ice package version')

        self._parser.add_argument('--get-available-flows', action='store_true',
                                  help='List all the available flows')

        self._parser.add_argument('--get-available-flows-with-details', action='store_true',
                                  help='List all the available flows with details')

        self._parser.add_argument('--print_roles_hosts_map', action='store_true',
                                  help='Prints map of the roles and assigned hosts of each role')

        self._parser.add_argument('--hosts', type=str, nargs='+', required=False,
                                  help='Provide hosts names / ips (separated by space) to be tested. Default is all hosts')

        self._parser.add_argument('--roles', type=str, nargs='+', required=False,
                                  help='Provide roles (separated by space) to be tested. Default is all roles')

        self._parser.add_argument('--ncs-bm-cluster-name', type=str, nargs=1, required=False,
                                  help='Provide NCS BM cluster name. Default is running for all clusters')

        self._parser.add_argument('--ncs-bcmt-config-path',
                                  type=self.valid_file_path, nargs=1, required=False,
                                  help="Provide 'bcmt-config.json' path if it's not at the default path '{}'".format(
                                      paths.DEFAULT_BCMT_CONF_FILE))

        self._parser.add_argument('--ncs-clcm-user-input-path',
                                  type=self.valid_file_path, nargs=1, required=False,
                                  help="Provide 'user-input.yaml' path if it's not at the default path '{}'".format(
                                      paths.DEFAULT_NCS_CLCM_USER_INPUT))

        self._parser.add_argument('--path-to-cbis-hosts-file',
                                  type=self.valid_file_path, required=False,
                                  help="Provide cbis hosts inventory path if it's not at the default path "
                                       "'/etc/ansible/hosts'")

        self._parser.add_argument('--ask-openstack-password', action='store_true',
                                  help="For cases of which the customer doesn't want to have the openstack passwords in clear text in rc-files.\n"
                                       "Using this flag will invoke interactive password setting")

        self._parser.add_argument('--is-hyp-connected', action='store_true',
                                  help='Checks if hypervisor is connected')

        self._parser.add_argument('--hyp-pass', type=str, nargs=1, required=False,
                                  help='Provide hypervisor password')

        self._parser.add_argument('--hyp-user', type=str, nargs=1, required='hyp-pass' in " ".join(sys.argv),
                                  help='Provide hypervisor user name')

        self._parser.add_argument('--do-not-connect-hyp', action='store_true',
                                  help='Do not ask the user for hyp password')

        self._parser.add_argument('--debug', action='store_true',
                                  help='For debugging purpose - add start and end prints')

        self._parser.add_argument('--print-only-failed', action='store_true',
                                  help='Print only failed validations. Relevant only to table output. Print all by default')

        self._parser.add_argument('--quiet', action='store_true',
                                  help='Not creating out files and minimum output')

        self._parser.add_argument('--no-out-files', action='store_true',  help='Do not generate report files')

        self._parser.add_argument('--limited-output', action='store_true',
                                  help='Get out files with failed validations only')

        self._parser.add_argument('--ncs-manager', action='store_true', help=argparse.SUPPRESS)

        self._parser.add_argument('--additional-comments', type=str, help="Add comments in the bottom of HTML page.")

    @staticmethod
    def valid_file_path(file_path):
        p = PopenTimeOut("sudo find {}".format(file_path), 30)
        return_code, _, _ = p.execute_command()

        if return_code != 0:
            raise argparse.ArgumentTypeError("The file %s does not exist!" % file_path)

        return file_path
