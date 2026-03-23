from __future__ import absolute_import


from tools import adapter
from HealthCheckCommon.operations import *
from HealthCheckCommon.validator import Validator
from tools.ConfigStore import ConfigStore
import re
import json
from tools.lazy_global_data_loader import *
from six.moves import range
from tools import python_versioning_alignment




class check_neutron_agents(Validator):
    objective_hosts = [Objectives.ONE_CONTROLLER]

    def set_document(self):
        self._unique_operation_name = "check_neutron_agent_status"
        self._title = "Verify neutron agent status in cases"
        self._failed_msg = ""
        self._severity = Severity.ERROR

        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM,ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    @staticmethod
    def is_agent_alive(sys_param):

        str_sys_param = str(sys_param)
        if str_sys_param == "True" or ":-)" in str_sys_param:
            return True
        return False

    def validate_nuage_agents(self):
        msg = ""
        out = self.get_output_from_run_cmd(
            "source /home/cbis-admin/overcloudrc; openstack network agent list -c Host -c Binary -c Alive -f json",
            timeout=60)
        result = True
        agent_list = json.loads(out)
        if len(agent_list) != 0:
            non_nuage_agent = ['neutron-l3-agent', 'neutron-dhcp-agent', 'neutron-metadata-agent']
            unused_agents = []
            for agent in agent_list:
                if agent['Binary'] in non_nuage_agent:
                    unused_agents.append(agent)
            for agent in unused_agents:
                msg += "{0} should be disabled and dead in {1} \n".format(agent['Binary'], agent['Host'])
                result = False
        return msg, result

    def validate_non_nuage_agents(self):
        msg = ""
        out = self.get_output_from_run_cmd(
            "source /home/cbis-admin/overcloudrc; openstack network agent list -c Host -c Binary -c Alive -f json",
            timeout=60)
        result = True
        neutron_agent_list = json.loads(out)
        for agent in neutron_agent_list:
            if not check_neutron_agents.is_agent_alive(agent['Alive']):
                msg += "{0} is not alive on {1} \n".format(agent['Binary'], agent['Host'])
                result = False
        return msg, result

    def is_validation_passed(self):
        is_nuage_enabled = ConfigStore.get_cbis_user_config()['CBIS']['openstack_deployment'].get("nuage")

        if str(is_nuage_enabled) == "True":
            nuage_agents_msg, ok = self.validate_nuage_agents()
            if not ok:
                self._failed_msg = "this is Nuage setup therefor:\n" + \
                                   nuage_agents_msg + \
                                   "If any of this agents are started and stopped manually, kindly make sure these agents are deleted from DB as well"
        else:
            non_nuage_agents_msg, ok = self.validate_non_nuage_agents()
            if not ok:
                self._failed_msg = non_nuage_agents_msg
        return ok


class CorosyncConfDataCollector(DataCollector):
    objective_hosts = [Objectives.CONTROLLERS]

    def collect_data(self):
        # output:
        # fe87a1b4abc512f8865bd46e5cfa9ceb  /etc/corosync/corosync.conf
        cmd = 'md5sum /etc/corosync/corosync.conf'
        out = self.get_output_from_run_cmd(cmd)
        return out

class CompareCorosyncNodeList(Validator):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "compare_corosync_node_list"
        self._title = "Compare that node IDs are the same in Controllers corosync.conf"
        self._failed_msg = "corosync.conf is not consist between controllers"
        self._severity = Severity.CRITICAL
        self._is_action_type_active = False
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]

    def is_validation_passed(self):
        res = self.run_data_collector(CorosyncConfDataCollector)
        if not len(res):
            raise NoSuitableHostWasFoundForRoles([Objectives.CONTROLLERS])
        self.add_to_validation_log('List of controllers: {}'.format(res))
        if len(set(res.values())) == 1:
            return True
        diff_hosts_values_dict = PythonUtils.reverse_dict(res)
        self._failed_msg = "Corosync config at /etc/corosync/corosync.conf does not match between: {}".format(
            ' and :'.join([str(value) for value in list(diff_hosts_values_dict.values())]))
        return False


class SpaceNotInAvailabilityZone(Validator):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "check_space_not_in_availability_zone"
        self._title = "Verify if availability zone names do not contain space"
        self._failed_msg = "Available Zone names contain space. Please fix it."
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.RISK_BAD_CONFIGURATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        cmd = "source {}; openstack aggregate list -f json -c 'Availability Zone'".format(self.system_utils.get_overcloudrc_file_path())
        zone_name_json = self.get_output_from_run_cmd(cmd)
        for zone_name in json.loads(zone_name_json):
            if zone_name["Availability Zone"] is None:
                pass
            elif " " in zone_name["Availability Zone"]:
                return False
        return True


class JsonFileIsValid(Validator):
    objective_hosts = [Objectives.UC, Objectives.CONTROLLERS, Objectives.COMPUTES]

    def set_document(self):
        self._unique_operation_name = "json_file_is_valid"
        self._title = "Checks that if exist, the json file in the right format and not empty"
        self._failed_msg = ""
        self._severity = Severity.NOTIFICATION
        self._is_action_type_active = False
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION, ImplicationTag.NOTE]

    def is_validation_passed(self):
        json_list = ["/var/lib/os-collect-config/ec2.json", "/var/lib/os-collect-config/request.json"]
        status = True
        for json_file in json_list:
            file_size = int(self._file_size_if_exist(json_file))
            if file_size > 1000000:
                self._failed_msg += "\n The file {} was much bigger than expected and not tested".format(json_file)
                status = False
            elif file_size > 0:
                json_content = self.get_output_from_run_cmd('sudo cat {}'.format(json_file))
                try:
                    json.loads(json_content)
                except ValueError as e:
                    self._failed_msg += "\n The file {} should be in json format ".format(json_file)
                    self._severity = Severity.CRITICAL
                    status = False
        return status

    def _file_size_if_exist(self, json_path):
        cmd = "sudo stat -c %s " + json_path
        rc, out, err = self.run_cmd(cmd)
        if rc == 0:
            return out
        return -1


class check_for_stale_allocations_in_novadb(Validator):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "check_for_stale_entries_in_nova_db"
        self._title = "Verify if there is any stale entries in nova DB"
        self._failed_msg = ""
        self._severity = Severity.ERROR

        self._implication_tags = [ImplicationTag.RISK_GARBAGE_CLEANING_RECOMMENDED]
        self._blocking_tags = []


    def is_validation_passed(self):
        get_host_id_command = "source {}; openstack server list --all-projects -f json -c ID --host".format(self.system_utils.get_overcloudrc_file_path())

        #Get compute service endpoint address
        compute_endpoint = self.get_output_from_run_cmd("source {}; openstack endpoint list --service compute --interface public -f value -c URL".
                                                        format(self.system_utils.get_overcloudrc_file_path()))

        #Get placement service endpoint address
        placement_endpoint = self.get_output_from_run_cmd("source {}; openstack endpoint list --service placement --interface public -f value -c URL".
                                                          format(self.system_utils.get_overcloudrc_file_path()))
        #Get token for authenticating APIs
        token = self.get_output_from_run_cmd("source {}; openstack token issue -f value -c id".format(self.system_utils.get_overcloudrc_file_path()))

        #Get openstack api version
        version = self.get_output_from_run_cmd('curl --max-time 30 -X GET ' + compute_endpoint.rstrip() + '/' + ' -H  X-Auth-Token:' + token.rstrip() + ' -s | jq .version.version')
        version_tag = 'OpenStack-API-Version: compute ' + str(version.replace("\"",""))
        #Get hypervisor ID list in a list
        hypervisor_ids = self.get_output_from_run_cmd('curl --max-time 30 -X GET ' + compute_endpoint.rstrip() + '/os-hypervisors ' + ' -H  X-Auth-Token:' + token.rstrip() + ' -H "' + version_tag.rstrip() + '" -s | jq .hypervisors[].id')
        #Get compute names in a list
        hypervisor_name = self.get_output_from_run_cmd('curl --max-time 30 -X GET ' + compute_endpoint.rstrip() + '/os-hypervisors ' + ' -H  X-Auth-Token:' + token.rstrip() + ' -H "' + version_tag.rstrip() + '" -s | jq .hypervisors[].hypervisor_hostname')
        host_id_list = hypervisor_ids.splitlines()
        host_name_list = hypervisor_name.splitlines()
        stale_allocations = set([])
        for host_name, host_id in python_versioning_alignment.get_zipper(host_name_list, host_id_list):
            instances = self.get_output_from_run_cmd("{} {}".format(get_host_id_command, host_name))
            instances_data = json.loads(instances)

            #Get instances list from nova DB
            #instances_list={instance_id for VM in instances_data for k,v in VM.items()}
            instances_list = []
            for instance_dict in instances_data:
              for header,uuid in list(instance_dict.items()):
                instances_list.append(uuid)
            get_allocations = self.get_output_from_run_cmd('curl --max-time 30 -X GET ' + placement_endpoint.rstrip() + '/resource_providers/'+host_id+'/allocations' + ' -H  X-Auth-Token:' + token.rstrip() + ' -H "Openstack-API-Version: placement latest" -s | jq .allocations')
            allocations = json.loads(get_allocations)

            #Get instances list from nova allocation DB
            if allocations is None:
                allocation_server_ids = []
            else:
                allocation_server_ids = list(allocations.keys())

            #Get if there are any stale entries in the DBs which is consuming resources even if the VMs are not present on the computes.
            stale_allocations = set(allocation_server_ids) ^ set(instances_list)
            self._failed_msg+= "Stale allocations are found on " + host_name + " " + str(list(stale_allocations)) + "\n"
        if len(stale_allocations) > 0:
           return False
        else:
           return True


class ValidateHttpdServiceUC (Validator):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "Validate_Httpd_Service_in_UnderCloud"
        self._title = "Validate Httpd Service in UnderCloud"
        self._failed_msg = "ERROR!! HTTPD Apache Service not Running"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.ACTIVE_PROBLEM]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        cmd = "systemctl status httpd"
        try:
            cmd_output = self.get_output_from_run_cmd(cmd)
            matched = re.search(r".*active (running)*", cmd_output)
            if (matched):
                return True
            return False
        except:
            return False

class PassthroughWhitelistInNova(Validator):
    objective_hosts = [Objectives.SRIOV_COMPUTES]

    def set_document(self):
        self._unique_operation_name = "Validate_passthrough_whitelist_in_nova_conf"
        self._title = "Validate passthrough_whitelist in nova.conf"
        self._failed_msg = "Passthrough_whitelist is not configured in nova.conf"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]
        self._blocking_tags = []

    def is_validation_passed(self):
        cmd = "sudo grep passthrough /var/lib/config-data/nova_libvirt/etc/nova/nova.conf | grep -v '#'"
        return_code, out, err = self.run_cmd(cmd)
        if not out:
            return False
        return True

######  SOUVIK DAS  |   ICET-1173   | RABBITMQ Password Validation #######
class RabbitMQUsernamePasswordDataCollector(DataCollector):
    objective_hosts = [Objectives.ONE_CONTROLLER]

    def collect_data(self):
        docker_or_podman = adapter.docker_or_podman()
        cmd = "sudo {} ps -f name=rabbitmq-bundle -q".format(docker_or_podman)
        output = self.get_output_from_run_cmd(cmd,add_bash_timeout=True)
        if output == '':
            raise UnExpectedSystemOutput(
                self.get_host_ip(), cmd, output, "Docker 'rabbitmq-bundle' isn't running on {}".format(
                    self.get_host_ip()))
        rabbitmq_container_id = output.strip()
        cmd = "sudo {} exec {} cat /etc/rabbitmq/rabbitmq.config | grep -i 'default_user,'".format(
            docker_or_podman, rabbitmq_container_id)
        output = self.get_output_from_run_cmd(cmd,add_bash_timeout=True)
        user = output.strip()
        username = user.split(",")[1]
        rabbitmq_username = PythonUtils.replace_special_chars(username)
        cmd = "sudo {} exec {} cat /etc/rabbitmq/rabbitmq.config | grep -i 'default_pass,'".format(
            docker_or_podman, rabbitmq_container_id)
        output = self.get_output_from_run_cmd(cmd,add_bash_timeout=True)
        user_pass = output.strip()
        password = user_pass.split(",")[1]
        rabbitmq_password = PythonUtils.replace_special_chars(password)
        return {"rabbitmq_username": rabbitmq_username,
                "rabbitmq_password": rabbitmq_password,
                "rabbitmq_container_id": rabbitmq_container_id}

class RabbitMQAuthenticateUserDataCollector(DataCollector):
    objective_hosts = [Objectives.ONE_CONTROLLER]

    def collect_data(self, **kwargs):
        docker_or_podman = adapter.docker_or_podman()
        cmd = "sudo {} ps -f name=rabbitmq-bundle | tail -1".format(docker_or_podman)
        output = self.get_output_from_run_cmd(cmd)
        rabbitmq_container_name = output.split()[-1]
        cmd = "sudo {} exec {} rabbitmqctl authenticate_user {} {} | grep Success | wc -l".format(
            docker_or_podman, rabbitmq_container_name, kwargs['username'], kwargs['password'])
        output = self.get_output_from_run_cmd(cmd, add_bash_timeout=True)

        return output.strip()

class RabbitMQUsernamePassword(Validator):

    def get_unique_rabbitmq_usernames_and_passwords_by_file(self, file_to_be_checked):
        all_username = []
        all_password = []
        cmd = r"sudo cat {} | grep -i 'transport_url' | grep rabbit | grep -v \#".format(file_to_be_checked)
        output_from_run_cmd = self.get_output_from_run_cmd(cmd)
        for line in output_from_run_cmd.splitlines():
            # Example of line:
            # "transport_url=rabbit://guest:4jwplQ3n6156TeEynGT46PJlq@overcloud-controller-0.internalapi.localdomain:5672/?ssl=0"
            array = line.split(":")
            user_string = array[1].strip()
            rest_string = array[2].strip()
            rabbitmq_password_neutron = rest_string.split("@")[0]
            rabbitmq_username_neutron = PythonUtils.replace_special_chars(user_string)
            all_username.append (rabbitmq_username_neutron)
            all_password.append (rabbitmq_password_neutron)
        unique_username = list(set(all_username))
        unique_pasword = list(set(all_password))
        return unique_username, unique_pasword

    def VerifyRabbitMQPasswordInNeutron(self ,rabbitmq_username, rabbitmq_password, neutron_conf_file):
        unique_username, unique_pasword = self.get_unique_rabbitmq_usernames_and_passwords_by_file(neutron_conf_file)
        failed_message = ""
        flag1 = 0
        flag2 = 0
        for i in range(0,len(unique_username)):
            if (str(unique_username[i])) == rabbitmq_username:
                if (str(unique_pasword[i])) == rabbitmq_password:
                    pass
                else:
                    flag1 = flag1 + 1
                    failed_message += " | for user: '{}' Password mismatch -> '{}' instead '{}' for file: {}".format(unique_username[i], unique_pasword[i], rabbitmq_password, neutron_conf_file)
            else:
                result, failed_message = self.ValidateMismatchUsernameRabbitMQ(unique_username[i], unique_pasword[i], neutron_conf_file)
                if result == True:
                    pass
                else:
                    flag2 = flag2 + 1
        if flag1 == 0 and flag2 == 0:
            result = True
        else:
            result = False
        return result, failed_message

    def ValidateMismatchUsernameRabbitMQ(self, username, password, neutron_conf_file):
        failed_message = ""
        message_output = self.get_first_value_from_data_collector(RabbitMQAuthenticateUserDataCollector, username=username,
                                                 password=password)
        if int(message_output) == 1:
            result = True
        else:
            result = False
            failed_message = "rabbitmqctl authenticate_user Failed for file: '{}'".format(neutron_conf_file)
        return result, failed_message

class RabbitMQPasswordNeutronValidation(RabbitMQUsernamePassword):
    objective_hosts = [Objectives.CONTROLLERS, Objectives.COMPUTES, Objectives.OVS_COMPUTES, Objectives.DPDK_COMPUTES, Objectives.SRIOV_COMPUTES, Objectives.AVRS_COMPUTES]

    def set_document(self):
        self._unique_operation_name = "RabbitMQPasswordNeutronValidation"
        self._title = "RabbitMQ Password with Neutron Validation"
        self._failed_msg = "Error!!RabbitMQ Password Mismatch in Conf | "
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]
        self._blocking_tags = []

    def is_prerequisite_fulfilled(self):
        out = self.get_output_from_run_cmd('sudo ovs-vsctl --version')
        if 'nuage' not in out:
            return True
        return False


    def is_validation_passed(self):
        rabbitmq_res_dict = self.get_first_value_from_data_collector(RabbitMQUsernamePasswordDataCollector)
        neutron_conf_file = "/var/lib/config-data/puppet-generated/neutron/etc/neutron/neutron.conf"
        result, Failed_Message = self.VerifyRabbitMQPasswordInNeutron(
            rabbitmq_res_dict['rabbitmq_username'], rabbitmq_res_dict['rabbitmq_password'], neutron_conf_file)
        self._failed_msg += '\n' + Failed_Message
        if result == True:
            return True
        else:
            return False

#####   SOUVIK DAS  |   ICET-1307   #####
#####   The stack update fails at keystone_init_tasks with ascii codec error.  #####    Validation of non-ascii character  ###

class check_project_non_ascii_chars(Validator):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "check_project_non_ascii_chars"
        self._title = "Verify if there is any non-ascii character in project description"
        self._failed_msg = ""
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]
        self._blocking_tags = []

    def is_validation_passed(self):
        ids_contains_non_ascci = []
        out = self.get_output_from_run_cmd("source /home/stack/overcloudrc; openstack project list -c ID | head -n -1 | tail -n +4").strip()
        project_id_array = []

        for line in out.splitlines():
            project_id = line.split()[1]
            project_id_array.append(project_id.strip())

        for id in project_id_array:
            cmd = "source /home/stack/overcloudrc; openstack project show " + id + " -c description -c name | head -n -1 | tail -n +4"

            out_ascii = self.get_output_from_run_cmd(cmd, get_not_ascii=False).strip()

            out_non_ascii = self.get_output_from_run_cmd(cmd, get_not_ascii=True).strip()

            if out_ascii != out_non_ascii:
                ids_contains_non_ascci.append(id)

        if ids_contains_non_ascci:
            self._failed_msg = self._failed_msg + "The following Projects contains non ascii characters in Name or Description:  " +str(ids_contains_non_ascci)
            return False
        return True

class checkOvercloudrc(Validator):
    objective_hosts = [Objectives.CONTROLLERS]

    def set_document(self):
        self._unique_operation_name = "overcloudrc_content_check"
        self._title = "Verify overcloudrc not missing content"
        self._failed_msg = "/home/cbis-admin/overcloudrc file missing content"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION, ImplicationTag.PRE_OPERATION]

    def is_validation_passed(self):
        cmd = "source /home/cbis-admin/overcloudrc && openstack endpoint list"
        return_code, out, err = self.run_cmd(cmd)
        if return_code != 0 or not out:
            return False
        return True

# https://jiradc2.ext.net.nokia.com/browse/ICET-2437
class VerifyClustercheckContainerPort(Validator):
    objective_hosts = [Objectives.CONTROLLERS]
    def set_document(self):
        self._unique_operation_name = "verify_clustercheck_cotainer_port"
        self._title = "Verify clustercheck container port"
        self._failed_msg = ""
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION, ImplicationTag.ACTIVE_PROBLEM]
        self._blocking_tags = [BlockingTag.UPGRADE]
        self._is_clean_cmd_info = True

    def is_validation_passed(self):
        port = 9200   #this is a fixed PORT for clustercheck container
        cmd = "source /home/cbis-admin/overcloudrc && sudo netstat -anp | grep ':{}'".format(port)
        return_code, out, err = self.run_cmd(cmd)
        if return_code == 0 and "LISTEN" in out:
            return True
        else:
            self._failed_msg += "Clustercheck container is not listening on port {}. \n".format(port)
            return False

#####   SOUVIK DAS  |   ICET-2423   #####
#####   Check whether metadata_workers, api_workers, rpc_workers parameters in neutron config is not ZERO
####    Relevance :  CBIS22 Onwards

class GetAllParameterValuesFromControllers(DataCollector):
    objective_hosts = [Objectives.CONTROLLERS]
    def collect_data(self, neutron_conf_file_to_be_checked, validation_function_type):
        return self.file_utils.get_value_from_file(neutron_conf_file_to_be_checked, validation_function_type, split_delimiter="=", additional_cmd=" | grep -v '#'")

class validate_metadata_RPC_Api_workers_parameter(Validator):
    objective_hosts = [Objectives.UC]

    def is_prerequisite_fulfilled(self):
        is_nuage_enabled = ConfigStore.get_cbis_user_config()['CBIS']['openstack_deployment'].get("nuage")
        if str(is_nuage_enabled) == "True":         # skip the validation in case having Nuage
            return False
        return True

    def set_document (self):
        self._unique_operation_name = "validate_metadata_RPC_Api_workers_parameter"
        self._title = "validate Metadata RPC Api workers parameter"
        self._failed_msg = ""
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]
        self._blocking_tags = []

    def read_values_from_default_Env_file (self, default_instllation_file_to_be_checked, parameter_in_default_environment_file):
        return self.file_utils.get_value_from_file(default_instllation_file_to_be_checked, parameter_in_default_environment_file, split_delimiter=":")

    def common_validation(self, validation_function_type , values_from_controllers, value_in_default_env_file, default_instllation_file_to_be_checked, neutron_conf_file):
        flag = True
        for controller_name, value in list(values_from_controllers.items()):
            is_valid_value = self._is_value_valid(value, validation_function_type, controller_name, neutron_conf_file)
            is_valid_default_value = self._is_value_valid(value_in_default_env_file, validation_function_type, controller_name, default_instllation_file_to_be_checked)
            if is_valid_value and is_valid_default_value:
                if int(value) != int(value_in_default_env_file):
                    flag = False
                    self._failed_msg += ("ERROR!! In controller: " + controller_name + " The " + validation_function_type +" Value inside " +
                                         neutron_conf_file +" file is : " +str(value) + " | But As per " + default_instllation_file_to_be_checked +
                                         " The actual Value should be : " + str(value_in_default_env_file) +"\n")
            else:
                flag = False
        return flag

    def _is_value_valid(self, value, function_type, controller_name, file_path):
        if value:
            if not value.isdigit():
                raise UnExpectedSystemOutput(self.get_host_ip(), "value.isdigit()", "", "ERROR!! Expected a digit {} value in file {}. Actual value is: '{}' from type: {}".format(function_type, file_path, value, type(value)))
        else:
            self._failed_msg += "Failed to find {} value in file {} in node {}. Value is: {}\n".format(function_type, file_path, controller_name, value)
            return False
        return True

    def is_validation_passed (self):

        #### Define all CONSTANT Variables here

        DEFAULT_INSTLLATION_FILE_TO_BE_CHECKED = "/home/stack/templates/network-environment.yaml"

        ## for metadata_workers  -> /var/lib/config-data/puppet-generated/neutron/etc/neutron/metadata_agent.ini
        ## for rpc_workers and api_workers  -> /var/lib/config-data/puppet-generated/neutron/etc/neutron/neutron.conf
        
        ## NEUTRON_CONF_FILE_TO_BE_CHECKED variable stores list of files needed for metadata_workers, rpc_workers and api_workers respectively.
        
        validation_function_netron_file_Check_mapping ={
            "metadata_workers": "/var/lib/config-data/puppet-generated/neutron/etc/neutron/metadata_agent.ini",
            "rpc_workers": "/var/lib/config-data/puppet-generated/neutron/etc/neutron/neutron.conf",
            "api_workers": "/var/lib/config-data/puppet-generated/neutron/etc/neutron/neutron.conf"
        }

        validation_function_netron_pattern_mapping = {
            "metadata_workers": "NeutronWorkers",
            "rpc_workers": "NeutronRpcWorkers",
            "api_workers": "NeutronWorkers"
        }

        assert len(validation_function_netron_file_Check_mapping) == len(validation_function_netron_pattern_mapping)

        Expected_values_in_default_environment_files = {}

        ### As per the logic Defined in CBIS22 UC, /home/stack/templates/deployment/neutron/neutron-api-container-puppet.yaml |  neutron::server::api_workers: {get_param: NeutronWorkers}
        ## api_workers will be same as metadata_worker

        for function_type in validation_function_netron_pattern_mapping:
            ### Get The metadata_worker Parameter from Default Network Environemnt file
            default_value = self.read_values_from_default_Env_file(
                DEFAULT_INSTLLATION_FILE_TO_BE_CHECKED, validation_function_netron_pattern_mapping[function_type])
            
            Expected_values_in_default_environment_files[function_type] = default_value

        All_values_from_controlers = {}

        for function_type, conf_file in list(validation_function_netron_file_Check_mapping.items()):
            values_dict = self.run_data_collector(GetAllParameterValuesFromControllers, neutron_conf_file_to_be_checked=conf_file, validation_function_type=function_type)

            All_values_from_controlers[function_type] = values_dict

        ### Sample Returned Dictionary :  
        '''
        OrderedDict(
            [
                (u'overcloud-controller-cbis22-2', u'40'),
                (u'overcloud-controller-cbis22-1', u'40'),
                (u'overcloud-controller-cbis22-0', u'40')
            ]
                )
        '''
        ## This dictionary data will be stored in each VALUE of All_values_from_controlers Dictionary where key = function_type.
        ## Valdation begins for metadata_workers
        ## FLAGs array to keep track of FALSE data.

        flags = {}
        for key in validation_function_netron_file_Check_mapping:
            flags[key] = True

        for function_type, neutron_conf_file in list(validation_function_netron_file_Check_mapping.items()):
            flags[function_type] = self.common_validation(function_type, All_values_from_controlers[function_type],
                                                          Expected_values_in_default_environment_files[function_type],
                                                          DEFAULT_INSTLLATION_FILE_TO_BE_CHECKED, neutron_conf_file)

        return all(flags.values())


class GetCPUValuesFromControllers(DataCollector):
    objective_hosts = [Objectives.CONTROLLERS]
    def collect_data(self):
        cmd = "sudo lscpu | grep -w '^CPU(s):'"
        out = (self.get_output_from_run_cmd(cmd)).strip()
        CPU_COUNT = (out.split(":")[1]).strip()
        return CPU_COUNT

class validateRPCApiCPUparameter(Validator):
    objective_hosts = [Objectives.UC]

    def is_prerequisite_fulfilled(self):
        is_nuage_enabled = ConfigStore.get_cbis_user_config()['CBIS']['openstack_deployment'].get("nuage")
        if str(is_nuage_enabled) == "True":         # skip the validation in case having Nuage
            return False
        return True

    def set_document (self):
        self._unique_operation_name = "validate_RPC_Api_CPU_parameter"
        self._title = "validate RPC Api CPU parameter"
        self._failed_msg = ""
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]
        self._blocking_tags = []

    def cpu_validation(self, validation_function_type , values_from_controllers, All_CPU_VALUES_from_controlers, neutron_conf_file):       
        flag = True
        for controller_name, value in list(values_from_controllers.items()):
            is_valid_value = self._is_value_valid(value, validation_function_type, controller_name, neutron_conf_file)
            if is_valid_value:
                cpu_val = int(All_CPU_VALUES_from_controlers[controller_name])
                if not (int(value) == int(cpu_val/2) or int(value) == 40):
                    flag = False
                    self._failed_msg += ("ERROR!! In controller: " + controller_name + " The " + validation_function_type +" Value inside " +  neutron_conf_file +" file is : " +str(value) + " | But As per CPU count on controller node : " +str(cpu_val) + " ,So The actual Value should be : " + str(int(cpu_val)/2) +"\n")
                if int(value) == 0:
                    self._failed_msg += "\nThis will impact vNF LCM activity\n"
            else:
                flag = False
        return flag

    def _is_value_valid(self, value, function_type, controller_name, file_path):
        if value:
            if not value.isdigit():
                raise UnExpectedSystemOutput(self.get_host_ip(), "value.isdigit()", "", "ERROR!! Expected a digit {} value in file {}. Actual value is: '{}' from type: {}".format(function_type, file_path, value, type(value)))
        else:
            self._failed_msg += "Failed to find {} value in file {} in node {}. Value is: {}\n".format(function_type, file_path, controller_name, value)
            return False
        return True

    def is_validation_passed (self):

        ## for metadata_workers  -> /var/lib/config-data/puppet-generated/neutron/etc/neutron/metadata_agent.ini
        ## for rpc_workers and api_workers  -> /var/lib/config-data/puppet-generated/neutron/etc/neutron/neutron.conf
        
        ## NEUTRON_CONF_FILE_TO_BE_CHECKED variable stores list of files needed for metadata_workers, rpc_workers and api_workers respectively.
        
        validation_function_netron_file_Check_mapping ={
            "metadata_workers": "/var/lib/config-data/puppet-generated/neutron/etc/neutron/metadata_agent.ini",
            "rpc_workers": "/var/lib/config-data/puppet-generated/neutron/etc/neutron/neutron.conf",
            "api_workers": "/var/lib/config-data/puppet-generated/neutron/etc/neutron/neutron.conf"
        }

        validation_function_netron_pattern_mapping = {
            "metadata_workers": "NeutronWorkers",
            "rpc_workers": "NeutronRpcWorkers",
            "api_workers": "NeutronWorkers"
        }

        assert len(validation_function_netron_file_Check_mapping) == len(validation_function_netron_pattern_mapping)

        All_values_from_controlers = {}

        for function_type, conf_file in list(validation_function_netron_file_Check_mapping.items()):
            values_dict = self.run_data_collector(GetAllParameterValuesFromControllers, neutron_conf_file_to_be_checked=conf_file, validation_function_type=function_type)

            All_values_from_controlers[function_type] = values_dict

        ### Sample Returned Dictionary :  
        '''
        OrderedDict(
            [
                (u'overcloud-controller-cbis22-2', u'40'),
                (u'overcloud-controller-cbis22-1', u'40'),
                (u'overcloud-controller-cbis22-0', u'40')
            ]
                )
        '''
        ## This dictionary data will be stored in each VALUE of All_values_from_controlers Dictionary where key = function_type.
        ## Valdation begins for metadata_workers
        ## FLAGs array to keep track of FALSE data.

        All_CPU_VALUES_from_controlers = {}

        All_CPU_VALUES_from_controlers = self.run_data_collector(GetCPUValuesFromControllers)

        flags = {}
        for key in validation_function_netron_file_Check_mapping:
            flags[key] = True

        for function_type, neutron_conf_file in list(validation_function_netron_file_Check_mapping.items()):
            #if function_type != "metadata_workers":
            flags[function_type] = self.cpu_validation(function_type, All_values_from_controlers[function_type], All_CPU_VALUES_from_controlers, neutron_conf_file)
        return all(flags.values())


class VerifyPassthroughWhitelistInNovaConf(Validator):
    objective_hosts = {Deployment_type.CBIS: [Objectives.SRIOV_COMPUTES]}

    def set_document (self):
        self._unique_operation_name = "validate_passthrough_whitelist_in_nova_conf"
        self._title = "Validate passthrough_whitelist parameter in nova.conf"
        self._failed_msg = ""
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]
        self._blocking_tags = []

    def is_validation_passed(self):
        file_path = r"/var/lib/config-data/puppet-generated/nova_libvirt/etc/nova/nova.conf"
        if not self.file_utils.is_file_exist(file_path):
            self._failed_msg = "nova.conf file not found, it is expected to be in {}".format(file_path)
            return False
        target_key = "passthrough_whitelist"
        cmd = "sudo grep '{}' '{}'".format(target_key, file_path)
        return_code, out, err = self.run_cmd(cmd)
        if return_code not in (0, 1):
            raise UnExpectedSystemOutput(self.get_host_ip(), cmd, out, message="return code {} is neither 0 nor 1, error {}".format(return_code, err))
        has_whitelist_entry = False
        pattern = re.compile(r"^\s*passthrough_whitelist\s*=\s*.+")
        for line in out.splitlines():
            if pattern.match(line):
                has_whitelist_entry = True
                break
        if not has_whitelist_entry:
            self._failed_msg = "No valid passthrough_whitelist= found in {}".format(file_path)
            return False
        return True


class VerifyCbisManagerDockerLayers(Validator):
    objective_hosts = {Deployment_type.CBIS: [Objectives.HYP]}

    def set_document(self):
        self._unique_operation_name = "verfiy_cbis_manager_image_docker_layer_count"
        self._title = "Verfiy Docker image for cbis_manager is having more than 125 layers"
        self._failed_msg = "Cbis_manager image is with more that 125 layers, Please reach out to 4ls team"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]
        self._blocking_tags = []


    def is_validation_passed(self):
        docker_or_podman = adapter.docker_or_podman()
        cmd = "sudo {} history cbis_manager|wc -l".format(docker_or_podman)
        return_code, out, err = self.run_cmd(cmd)
        if int(out) > 125:
            return False
        return True


class TripleOVolumeTypeValidation(Validator):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.UC]
    }

    def set_document(self):
        self._unique_operation_name = "tripleo_volume_type_validation"
        self._title = "Make sure tripleO volume_type does not exist"
        self._failed_msg = "TripleO volume_type exists"
        self._severity = Severity.CRITICAL
    def check_for_tripleo_volume_type(self):
        check_tripleo_volume_type_cmd = "source {}; openstack volume type list --long -f json | jq -r '.[] | select(.Name == \"tripleo\") | .Name'".format(self.system_utils.get_overcloudrc_file_path())
        tripleo_volume_type = self.get_output_from_run_cmd(check_tripleo_volume_type_cmd)
        return tripleo_volume_type
    def get_volumes_with_tripleo(self):
        volumes_cmd = "source {};  openstack volume list --all-projects --long -f json | jq -r '.[] | select(.Type == \"tripleo\") | .Name'".format(self.system_utils.get_overcloudrc_file_path())
        tripleo_volumes = self.get_output_from_run_cmd(volumes_cmd)
        return tripleo_volumes
    def is_validation_passed(self):
        if self.check_for_tripleo_volume_type():
            volumes = self.get_volumes_with_tripleo()
            if volumes:
                self._failed_msg += "\nThe following volumes use tripleo volume_type:\n{}".format(volumes)
                return False
            else:
                self._failed_msg
                return False
        return True