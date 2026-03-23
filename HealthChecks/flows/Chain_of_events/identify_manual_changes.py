from __future__ import absolute_import
import time
import datetime
from HealthCheckCommon.operations import *
from HealthCheckCommon.validator import InformatorValidator
from flows.Chain_of_events.operation_timing_info import Operation_timing_info
import tools.sys_parameters as sys_parameters


#############################################################
##      https://jiradc2.ext.net.nokia.com/browse/ICET-2046
##      Author : SOUVIK DAS
##      Date : 22-Nov-2023
##      Validate if there are any other external service/process
##      running on NCS/CBIS nodes
###############################################################

#   First Class is GetServiceFilesFromHosts for Data Collecting
#   Across the nodes and send to UC/ Manager as a Dictionary
#   Dictionary:
#       Key = HOST
#       Values = A Dictionary:
#                   Key = Service_name
#                   Value = Date of Creation of Servicefile in EPOCH Timestamp format

class GetServiceFilesFromHosts(DataCollector):
    objective_hosts = [Objectives.CONTROLLERS, Objectives.COMPUTES, Objectives.STORAGE, Objectives.ALL_NODES]

    def collect_data(self):
        dict = {}
        #   Services which can come up later post install or any type of issue or can come up once only when enabled
        #   New service which you want to discard from chekcing please add below with single quote (') on ARRAY : service_list_not_to_be_considered

        service_list_not_to_be_considered = ['elk', 'alarm-manager', 'ceph', 'kubelet', 'zabbix',
                                             'cloud', 'cbis', 'calico', 'kube-', 'glusterd',
                                             'podman', 'docker', 'node_exporter', 'bcmt-', 'etcd',
                                             'ironic', 'tripleo', 'container', 'dns', 'httpserver',
                                             'mysql', 'registry', 'nginx', 'mlnx_', 'sriov', 'libvirt',
                                             'sharpd', 'dpdk', 'mst', 'dispatcher', 'dbus', 'syslog', 'audit',
                                             'timedate', 'ksm',
                                             'hpraid-exporter']

        services_not_to_be_considered_string = "|".join(service_list_not_to_be_considered)
        services_not_to_be_considered_string = "'" + services_not_to_be_considered_string + "'"

        #   In Linux All services are created by .service files inside
        #   /etc/systemd/system/ directory. File should be created here only
        #   Not inside any directory which is inside the parent directory
        #  : /etc/systemd/system/

        cmd = "sudo /usr/bin/ls /etc/systemd/system/*.service | grep -E -v " + services_not_to_be_considered_string
        # out = self.get_output_from_run_cmd(cmd).strip()
        return_code, out, err = self.run_cmd(cmd)
        if int(return_code) == 0:
            vm_array = out.splitlines()

            #   stat comman in linux will get the Creation and Modification date
            #   of any File in linux
            #   %Y     time of last modification, seconds since Epoch

            for i in vm_array:
                cmd = "sudo stat -c %Y " + str(i)
                out = self.get_output_from_run_cmd(cmd).strip()
                dict[i] = out
        else:
            pass
        return dict


#   Main Class for VALIDATION begins

class ValidateUnwantedServicesOnNodes(InformatorValidator):
    objective_hosts = [Objectives.UC, Objectives.ONE_MANAGER, Objectives.DEPLOYER]

    def set_document(self):
        self._unique_operation_name = "validate_unwanted_services_on_nodes"
        self._title = "Validate UN-WANTED Services on Nodes"
        self._title_of_info = "Services that were installed after post install."
        self._failed_msg = "ERROR !! UN-WANTED Services are present in system\n"
        self._implication_tags = [ImplicationTag.NOTE]
        self._is_pure_info = True
        self._system_info = ""

    #   Function get_cluster_installation_end_date
    #   is for getting the Installation Date of Overcloud / Cluster
    #   Returns Date both in DATE_TIME format and in Linux Timestamp EPOCH

    def get_cluster_installation_end_date(self):
        cluster_installation_info = None
        operation_timing = Operation_timing_info(self)
        res = operation_timing.get_operations_datetime()

        #   Based on the Deployment type CBIS or NCS Get the Installation date-time of the setup
        #   As of now Operation Timeline not available for NCS CN-A
        #   So as of not this validation added only for CBIS and NCS_OVER_BM

        if sys_parameters.get_deployment_type() == Deployment_type.CBIS:
            cluster_installation_info = res.get('post_install', None)
        elif sys_parameters.get_deployment_type() == Deployment_type.NCS_OVER_BM:
            cluster_installation_info = res.get('cluster_installation', None)
        elif gs.get_deployment_type() in Deployment_type.get_ncs_vsphere_openstack_types():
            cluster_installation_info = res.get('ncm_installation', None)
        if cluster_installation_info is None:
            return None, None
        date = cluster_installation_info[-1].get("end_time")
        if not date:
            return None, None
        datetime_object = datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
        timestamp = time.mktime(datetime_object.timetuple())
        return date, timestamp

    #   Function get_service_CreationDate_dictionary
    #   is for getting the creation date of each service from all nodes
    #   And compare each with Installation date
    #   Returns Dictionary with,
    #   Key = HOST
    #   Value = Unwanted Service Name + Service file creation time in EPOCH

    def get_service_CreationDate_dictionary(self, Service_Files_From_Hosts, epoch):
        all_bad_services = {}

        #   buffer_time_post_install = Half an hour 30 minutes we took
        #   to check those services installed after (INTALLATION + 30 minutes later)

        buffer_time_post_install = 3600
        time_duration = int(epoch) + buffer_time_post_install
        for host, serviceName_dates in list(Service_Files_From_Hosts.items()):
            if serviceName_dates != None:
                for serviceName, date in list(serviceName_dates.items()):
                    if date != None:
                        if int(date) >= int(time_duration):
                            all_bad_services[host] = str(serviceName) + " | " + str(date)
        return all_bad_services

    #   Main Function inside ValidateUnwantedServicesOnNodes class for Validation

    def is_validation_passed(self):
        overclud_installation_end_date, overclud_installation_end_date_epoch = self.get_cluster_installation_end_date()
        if overclud_installation_end_date is None:
            self._failed_msg = 'Failed to get Installation date-time of the setup'
            return True

        #   Service_Files_From_Hosts is Dictionary which gets
        #   all Service and their dates from DataCollector

        service_files_from_hosts = self.run_data_collector(GetServiceFilesFromHosts)

        #   all_bad_services is Dictionary which gets
        #   all Unwanted Service which got installed on system manually post install
        #   via calling function :  get_service_CreationDate_dictionary
        #   Key = HOST
        #   Value = Unwanted Service Name + Service file creation time in EPOCH

        all_bad_services = self.get_service_CreationDate_dictionary(service_files_from_hosts,
                                                                    overclud_installation_end_date_epoch)

        if not all_bad_services:
            self._system_info = "No services"
            return True
        else:
            info = ""
            for host, item in list(all_bad_services.items()):
                service = item.split("|")[0].strip()
                date = item.split("|")[1].strip()
                Actual_date = datetime.datetime.fromtimestamp(float(date))
                info = info + "\n" + "On Host: " + host + " | Service: " + service + " | Date:  " + str(
                    Actual_date) + " | Timestamp : " + str(date)

            overcloud_installed = "\nOverCloud was installed on : " + str(
                overclud_installation_end_date) + " | Timestamp : " + str(overclud_installation_end_date_epoch) + "\n"

            self._failed_msg = self._failed_msg + overcloud_installed + info
            self._system_info = overcloud_installed + info

            return True
