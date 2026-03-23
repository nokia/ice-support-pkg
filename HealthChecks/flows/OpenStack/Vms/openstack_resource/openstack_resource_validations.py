from __future__ import absolute_import
import json
import time
from collections import defaultdict

from HealthCheckCommon.operations import DataCollector
from HealthCheckCommon.validator import Validator
from flows.OpenStack.Vms.VmsInfo import VmsInfo
from flows.OpenStack.openstack_utils_data_collector import OpenstackUtilsDataCollector
from tools import user_params, sys_parameters
from tools.Exceptions import UnExpectedSystemOutput
from tools.global_enums import Objectives, Severity, ImplicationTag, BlockingTag, Version
from tools.lazy_global_data_loader import lazy_global_data_loader
from tools.python_utils import PythonUtils
from tools import adapter


class VirshInstanceNameDataCollector(DataCollector):
    objective_hosts = [Objectives.COMPUTES]

    def collect_data(self):
        ret, out, err = self.run_cmd('sudo virsh list --all|grep instance')
        if 'instance' not in out:
            # no instance on this set up
            return None
        else:
            vm_ids_list = list(out.strip().split('\n'))
            vm_instance_list = []
            for i in vm_ids_list:
                x = i.split()
                vm_instance_list.append(x[1])
            return vm_instance_list


class OpenstackResourceValidation(Validator):
    @lazy_global_data_loader
    def get_vm_details_for_user_params_vm(self):
        assert user_params.vm
        return VmsInfo.get_vm_details(user_params.vm)

    @lazy_global_data_loader
    def get_instances_per_compute(self):
        return self.run_data_collector(VirshInstanceNameDataCollector)

    @lazy_global_data_loader
    def get_resource_provider_list(self):
        host = Objectives.ONE_CONTROLLER
        if sys_parameters.get_version() >= Version.V25:
            host = Objectives.UC
        resource_providers_list_cmd = "openstack resource provider list"
        return VmsInfo.get_openstack_command_output(resource_providers_list_cmd, host=host)

    @lazy_global_data_loader
    def get_vms_list(self):
        resource_providers_list_cmd = "openstack server list"
        return VmsInfo.get_openstack_command_output(resource_providers_list_cmd)

    @lazy_global_data_loader
    def get_vms_long_list(self):
        resource_providers_list_cmd = "openstack server list --long --all-projects"
        return VmsInfo.get_openstack_command_output(resource_providers_list_cmd)

    def get_provider_id_from_uuid(self, vm_provider_uuid):
        db = VmsInfo.get_placement_db()
        maria_db_cmd = 'use {};  select * from resource_providers where uuid="{}"'.format(db, vm_provider_uuid)
        compute_details = self.get_first_value_from_data_collector(OpenstackUtilsDataCollector,
                                                                   mysql_command=maria_db_cmd)

        if not len(compute_details):
            return None

        compute_id = compute_details[0]["id"]
        return compute_id

    def get_local_domain_hostname(self, hostname):
        return hostname + ".localdomain"


class DuplicateInstanceCheck(OpenstackResourceValidation):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "duplicate_instance_check"
        self._title = "Validate if there are duplicate instances across computes"
        self._failed_msg = "test not completed:"
        self._severity = Severity.CRITICAL
        self._blocking_tags = [BlockingTag.MIGRATION]
        self._implication_tags = [ImplicationTag.RISK_GARBAGE_CLEANING_RECOMMENDED]
        self._title_of_info = "Check if there are duplicate instances in openstack"
        self._is_pure_info = False

    def is_validation_passed(self):
        compute_instance_dict = self.get_instances_per_compute()
        compute_instance_dict = PythonUtils.clear_dict_from_None_valuse(compute_instance_dict)

        # Reverse dictionary. Create dictionary of instance -> list of computes with that instance
        instance_compute_dict = defaultdict(set)
        failed_messages = []
        for compute, instance_list in list(compute_instance_dict.items()):
            for instance in instance_list:
                instance_compute_dict[instance].add(compute)
        # For each instance, if there are multiple computes print error message
        for instance, compute_list in list(instance_compute_dict.items()):
            if len(compute_list) > 1:
                failed_messages.append("Instance " + str(instance) + " has duplicates in Computes " + str(compute_list))

        if len(failed_messages) == 0:
            return True

        self._failed_msg = "List of duplicate instances are found on " + str(failed_messages)
        self._severity = Severity.ERROR
        return False


class DuplicatePortRecords(OpenstackResourceValidation):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "duplicate_port_record"
        self._title = "Validate if there are duplicate port records for specific vm"
        self._failed_msg = "test not completed:"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.RISK_GARBAGE_CLEANING_RECOMMENDED]
        self._blocking_tags = [BlockingTag.MIGRATION]

    def is_validation_passed(self):
        cmd = "source {}; openstack port list --server {}".format(self.system_utils.get_stackrc_file_path(),
                                                                  user_params.vm)
        vm_ports_list = VmsInfo.get_openstack_command_output(cmd, handle_cbis_18_out=True)
        duplicate_list = []

        for vm_port_data in vm_ports_list:
            if "ID" not in list(vm_port_data.keys()):
                raise UnExpectedSystemOutput(self.get_host_ip(), cmd + " -f json", vm_ports_list,
                                             "Expected to have 'ID' in keys.")
            port_id = vm_port_data["ID"]
            maria_db_cmd = 'use ovs_neutron; select * from ml2_port_bindings where port_id="{}"'.format(port_id)
            port_records_list = self.get_first_value_from_data_collector(OpenstackUtilsDataCollector,
                                                                         mysql_command=maria_db_cmd)
            if len(port_records_list) > 1:
                duplicate_list.append(json.dumps(port_records_list, indent=2))

        if len(duplicate_list) > 0:
            self._failed_msg = "There are duplicate port records for vm: {}\n" \
                               "{}".format(user_params.vm, "\n".join(duplicate_list))
            return False

        return True


class VmResourceAllocationOnRightCompute(OpenstackResourceValidation):
    """
    This validation is included by ResourceAllocationsCheck
    But in case that the VM provider isn't connected the ResourceAllocationsCheck won't run so need also this.
    """
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "vm_resource_allocations_on_right_compute"
        self._title = "Verify that the VM has resource allocations (from openstack command) on the right compute"
        self._failed_msg = ""
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.RISK_GARBAGE_CLEANING_RECOMMENDED]
        self._blocking_tags = [BlockingTag.MIGRATION]

    def is_validation_passed(self):
        resource_providers_list_cmd = "openstack resource provider list"
        resource_providers_list = self.get_resource_provider_list()
        vm_provider_cmd = "openstack resource provider allocation show {}".format(user_params.vm)
        vm_provider_list = VmsInfo.get_openstack_command_output(vm_provider_cmd, host=Objectives.ONE_CONTROLLER)

        if len(vm_provider_list) != 1:
            raise UnExpectedSystemOutput("controller", vm_provider_cmd, vm_provider_list,
                                         "Expected to have only 1 provider")
        vm_provider_uuid = vm_provider_list[0]["resource_provider"]
        vm_provider = list([provider for provider in resource_providers_list if provider["uuid"] == vm_provider_uuid])

        if len(vm_provider) != 1:
            raise UnExpectedSystemOutput("controller", resource_providers_list_cmd + ", " + vm_provider_cmd,
                                         "resource_providers_list: {}, vm_provider_uuid: {}".format(
                                             resource_providers_list, vm_provider_uuid))

        compute_id = self.get_provider_id_from_uuid(vm_provider_uuid)

        if compute_id is None:
            raise UnExpectedSystemOutput("one controller",
                                         'use nova_api;  select * from resource_providers where uuid="{}"'.format(
                                             vm_provider_uuid), "", "Expected to have the provider in DB")

        db = VmsInfo.get_placement_db()
        maria_db_cmd = 'use {};  select * from allocations where resource_provider_id={} ' \
                       'and consumer_id="{}"'.format(db, compute_id, user_params.vm)
        compute_allocations = self.get_first_value_from_data_collector(OpenstackUtilsDataCollector,
                                                                       mysql_command=maria_db_cmd)

        if not len(compute_allocations):
            self._failed_msg = "No allocation between compute: {} and vm: {}".format(compute_id, user_params.vm)
            return False

        return True


class ResourceAllocationsCheck(OpenstackResourceValidation):
    objective_hosts = [Objectives.COMPUTES]

    def set_document(self):
        self._unique_operation_name = "resource_allocation_in_db_check"
        self._title = "Verify that the resource allocations (from db) of compute really run on it"
        self._failed_msg = ""
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.RISK_GARBAGE_CLEANING_RECOMMENDED]
        self._blocking_tags = [BlockingTag.MIGRATION]

    def is_validation_passed(self):
        resource_providers_list = self.get_resource_provider_list()
        compute_provider = list([provider for provider in resource_providers_list if
                                 self.get_local_domain_hostname(self.get_host_name()) == provider["name"]])

        if not len(compute_provider):
            return True

        compute_uuid = compute_provider[0]["uuid"]
        compute_id = self.get_provider_id_from_uuid(compute_uuid)

        if compute_id is None:
            return True

        allocations, compute_allocations_consumer_ids = self._get_compute_allocations_consumer_ids(compute_id)
        vms_uuids = self._get_compute_vms_uuids()
        res = True

        in_db_not_in_nova_list = set(compute_allocations_consumer_ids) - set(vms_uuids)
        in_nova_list_not_in_db = set(vms_uuids) - set(compute_allocations_consumer_ids)

        if len(in_db_not_in_nova_list):
            res = False
            self._failed_msg += "The vms: {} are not running on compute although they have allocation to the vms: " \
                                "{}\n".format(", ".join(in_db_not_in_nova_list), allocations)

        if len(in_nova_list_not_in_db):
            res = False
            self._failed_msg += "The vms: {} are running on compute although they don't have allocation to the vms: " \
                                "{}\n".format(", ".join(in_nova_list_not_in_db), allocations)

        return res

    def _get_compute_allocations_consumer_ids(self, compute_id):
        maria_db_cmd = 'use {};  select consumer_id, resource_provider_id from allocations'.format(
            VmsInfo.get_placement_db())
        allocations = self.get_first_value_from_data_collector(OpenstackUtilsDataCollector, mysql_command=maria_db_cmd)
        compute_allocations = list([l for l in allocations if l["resource_provider_id"] == compute_id])
        compute_allocations_consumer_ids = [compute_allocation["consumer_id"]
                                            for compute_allocation in compute_allocations]
        return compute_allocations, compute_allocations_consumer_ids

    def _get_compute_vms_uuids(self):
        vms_table = VmsInfo.run_command_on_selected_host("nova list --all --fields name,host,id")
        vms_list = PythonUtils.get_dict_from_linux_table(vms_table, custom_delimiter="|")

        res = []

        for vm in vms_list:
            if self.get_local_domain_hostname(self.get_host_name()) == vm["Host"]:
                res.append(vm["ID"])

        return res


# ---------------- Bodam's code start ----------------

class OpenstackServerListDataCollector(DataCollector):
    objective_hosts = [Objectives.UC]

    def collect_data(self):
        # getting only active VM's list through Openstack command
        op_vm_list_cmd = 'source {}; openstack server list --all --long -c ID  --status ACTIVE -f json'.format(
            self.system_utils.get_overcloudrc_file_path())
        openstac_vm_list = self.get_output_from_run_cmd(op_vm_list_cmd)
        return openstac_vm_list


class NetworkInfoForInstanceInInstanceInfoCaches(Validator):  # This validation was written by Bodam
    objective_hosts = [Objectives.ONE_CONTROLLER]

    def set_document(self):
        self._unique_operation_name = "validate_networkinfo_for_instance_in_instance_info_caches"
        self._title = "Verify network info for instances in instance_info_cache of nova database"
        self._failed_msg = "Below Instances network info is empty/[] in instance_info_caches of nova db and VMs are active: "
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.RISK_GARBAGE_CLEANING_RECOMMENDED]

    def is_validation_passed(self):
        cbis_version = sys_parameters.get_version()
        if cbis_version <= Version.V20:
            mysql_cmd = "sudo mysql nova -s -e 'select instance_uuid from instance_info_caches where network_info like  \"[]\" and deleted_at is  NULL;'"
        elif cbis_version >= Version.V22:
            mysql_cmd = "sudo podman exec $(sudo podman ps -f name=galera-bundle -q) mysql nova -s -e 'select instance_uuid from instance_info_caches where network_info like  \"[]\" and deleted_at is  NULL;'"
        instances_with_no_network = self.get_output_from_run_cmd(mysql_cmd)
        vmlist_from_nova_cache = [vm_name.strip() for vm_name in instances_with_no_network.split("\n") if
                                  len(vm_name) != 0]
        op_vms_list = self.run_data_collector(OpenstackServerListDataCollector)
        problamtic_vm_uuid_list = []
        for vm_uuid in vmlist_from_nova_cache:
            if vm_uuid in op_vms_list['undercloud']:
                problamtic_vm_uuid_list.append(vm_uuid)
        if len(problamtic_vm_uuid_list) == 0:
            return True
        else:
            self._failed_msg = self._failed_msg + "\n" + instances_with_no_network
            return False


# ---------------- Bodam's code end ----------------

class InterVMCommunicationHost(Validator):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "Inter_VM_communication_host"
        self._is_clean_cmd_info = True
        self._title = "InterVMCommunicationHost"
        self._failed_msg = "Inter-VM Communication loss due to error in host"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.SYMPTOM]

    def is_validation_passed(self):
        cmd = "openstack server list --format json | jq -r '.[].ID'"
        out = str(self.get_output_from_run_cmd(cmd).strip())
        server_list = out.split('\n')
        for server in server_list:
            cmd = "openstack server event list " + server + " --long -c 'Message' --format json | jq -r '.[].Message'"
            out = str(self.get_output_from_run_cmd(cmd).strip())
            time.sleep(2)  #make sure we are not deducing the system
            if out == "Error":
                return False
        return True


class InterVMCommunicationPort(Validator):
    objective_hosts = [Objectives.ONE_CONTROLLER]

    def set_document(self):
        self._unique_operation_name = "Inter_VM_communication_port"
        self._is_clean_cmd_info = True
        self._title = "test for possible Inter VM communication due to inactive port"
        self._failed_msg = "Inter-VM Communication loss due to inactive port: "
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.RISK_GARBAGE_CLEANING_RECOMMENDED]

    def is_validation_passed(self):
        mysql_password = self.get_output_from_run_cmd(
            "sudo /bin/hiera -c /etc/puppet/hiera.yaml mysql::server::root_password")
        mysql_password = mysql_password.strip()
        command = 'select port_id,status from ovs_neutron.ml2_port_bindings WHERE status = "INACTIVE";'
        container_name = 'galera-bundle'
        if sys_parameters.get_version() >= Version.V22:
            maria_db_cmd = "sudo podman exec $(sudo podman ps -f name={} -q)  mysql -uroot --password={} -e '{}'".format(
                container_name, mysql_password, command)
        else:
            maria_db_cmd = "sudo docker exec $(sudo docker ps -f name={} -q)  mysql -uroot --password={} -e '{}'".format(
                container_name, mysql_password, command)
        out = str(self.get_output_from_run_cmd(maria_db_cmd).strip())
        if len(out) > 0:
            self._failed_msg = self._failed_msg + out
            return False
        return True


class VolumeDeviceNotFound(OpenstackResourceValidation):
    objective_hosts = [Objectives.ONE_CONTROLLER]

    def set_document(self):
        self._unique_operation_name = "volume_device_not_found"
        self._title = "Validate if Instance fails to start with VolumeDeviceNotFound on external storage"
        self._failed_msg = "Instance fails to start with VolumeDeviceNotFound or the instance id provided is not present "
        self._severity = Severity.ERROR
        self._is_clean_cmd_info = True

    def is_validation_passed(self):
        cmd = "sudo /bin/hiera -c /etc/puppet/hiera.yaml mysql::server::root_password"
        failure_message = "Un-Expected output: Password not able to retrieve"
        mysql_password = self.get_output_from_run_cmd(cmd, message=failure_message)
        mysql_password = mysql_password.strip()
        command = 'SELECT CASE WHEN COUNT(*) > 1 THEN "False" ELSE "True" END AS result FROM cinder.volume_attachment WHERE attach_status = "attached" AND instance_uuid = "{}" GROUP BY instance_uuid, mountpoint;'.format(
            user_params.vm)

        maria_db_cmd = "sudo mysql -uroot --password={password} -e '{cmd}'".format(password=mysql_password, cmd=command)
        out = str(self.get_output_from_run_cmd(maria_db_cmd).strip())
        if len(out) >= 4:
            out1 = out[-4:]
            if out1 == "True":
                return True
            else:
                self._failed_msg = "Instance fails to start with VolumeDeviceNotFound"
                return False
        else:
            self._failed_msg = " The instance id provided is not present"
            return False


class GetAllBadVMSFromComputes(DataCollector):
    objective_hosts = [Objectives.COMPUTES]

    def collect_data(self, filtered_inactive_instances):
        vm_status_in_compute_array = []
        for instance_info in filtered_inactive_instances:
            virsh_name = instance_info["virsh_name"]
            cmd = "sudo virsh list --all | grep {}".format(virsh_name)
            return_code, vm_status_in_compute, err = self.run_cmd(cmd)
            if return_code == 0:
                vm_status_in_compute_array.append(vm_status_in_compute)
        return vm_status_in_compute_array


class CheckInstanceStatus(OpenstackResourceValidation):
    objective_hosts = [Objectives.UC]

    def set_document(self):
        self._unique_operation_name = "check_instance_mismatch"
        self._title = "Validate if Instance(s) are in mismatch state in Openstack & Compute"
        self._failed_msg = "There can be one or more VM in openstack which is in not 'running' state," \
                           " But same VM is in 'running' state in Compute host."
        self._severity = Severity.ERROR
        self._implication_tags = ImplicationTag.RISK_RESOURCE_CLEANING_RECOMMENDED

    def get_inactive_instance_from_openstack(self):
        instances = self.get_vms_long_list()
        inactive_instances = []
        for instance in instances:
            if instance['Status'] != 'ACTIVE' or instance['Power State'] != 'Running':
                inactive_instances.append(instance['ID'])
        return inactive_instances

    def get_inactive_instance_virsh_names(self):
        filtered_instances = []
        inactive_instances = self.get_inactive_instance_from_openstack()
        for vm_id in inactive_instances:
            vm_dict = VmsInfo.get_vm_details(vm_id)
            filtered_instances.append({
                'virsh_name': vm_dict.get('virsh_name'),
                'vm_name': vm_dict.get('vm_name')
            })
        return filtered_instances

    def is_validation_passed(self):
        filtered_inactive_instances = self.get_inactive_instance_virsh_names()
        if not filtered_inactive_instances:
            return True
        returned_array_from_datacollector = self.run_data_collector(GetAllBadVMSFromComputes,
                                                                    filtered_inactive_instances=filtered_inactive_instances)
        '''Sample output of returned_array :
        ({'overcloud-ovscompute-fi860-1': [' 32    instance-0000005c              running\\n'], 
        'overcloud-ovscompute-fi860-0': [' 34    instance-0000005b              running\\n', ' 32    instance-00000059   running\\n']
        })
        '''
        running_instances = []
        for host, instances_info in returned_array_from_datacollector.items():
            for instance_output in instances_info:
                if instance_output and "running" in instance_output:
                    try:
                        parts = instance_output.split()
                        if len(parts) >= 3:
                            virsh_name_from_virsh = parts[1].strip()
                            # Find the corresponding "vm_name" in inactive_instances
                            vm_name = None
                            for instance in filtered_inactive_instances:
                                if instance['virsh_name'] == virsh_name_from_virsh:
                                    vm_name = instance['vm_name']
                                    break
                            running_instances.append((virsh_name_from_virsh, vm_name, host))
                    except UnExpectedSystemOutput:
                        err_msg = "Unexpected error processing instance tuple: {} ".format(instance_output)
                        self._failed_msg += "\n" + err_msg

        if running_instances:
            for virsh_name, vm_name, host in running_instances:
                self._failed_msg += ("\nInstance name: '{}' or VM name: '{}' is not in RUNNING state in Openstack ,"
                                     "but its RUNNING on compute: '{}'").format(virsh_name, vm_name, host)
            return False
        else:
            return True


class CheckStaleVolumes(OpenstackResourceValidation):
    objective_hosts = [Objectives.ONE_CONTROLLER]

    def set_document(self):
        self._unique_operation_name = "check_stale_volumes"
        self._title = "Identify if Stale volumes are present in Mysql DB"
        self._failed_msg = "Stale volumes are present in Mysql DB"
        self._severity = Severity.ERROR
        self._is_clean_cmd_info = True
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        cmd = "sudo /bin/hiera -c /etc/puppet/hiera.yaml mysql::server::root_password"
        failure_message = "Un-Expected output: Password not able to retrieve"
        mysql_password = self.get_output_from_run_cmd(cmd, message=failure_message)
        mysql_password = mysql_password.strip()
        command = "select created_at,attach_status,volume_id from cinder.volume_attachment WHERE deleted=0 and attach_status!='attached';"
        container_name = 'galera-bundle'
        docker_or_podman = adapter.docker_or_podman()
        maria_db_cmd = "sudo {} exec $(sudo {} ps -f name={} -q) mysql -uroot --password={} -e \"{}\"".format(
            docker_or_podman, docker_or_podman, container_name, mysql_password, command)
        out = str(self.get_output_from_run_cmd(maria_db_cmd).strip())
        if len(out) > 0:
            self._failed_msg += "\n\n" + out
            return False
        return True
