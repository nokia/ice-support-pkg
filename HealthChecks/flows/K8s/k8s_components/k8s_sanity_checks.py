from __future__ import absolute_import
from tools import adapter
from HealthCheckCommon.operations import *
from HealthCheckCommon.validator import Validator, InformatorValidator
from tools.global_enums import *
import tools.sys_parameters as sys_param
import datetime
import time
import re
import pkg_resources
from tools.date_and_time_utils import parse
from tools.python_utils import PythonUtils
from tools.Exceptions import *
from flows.Security.Certificate.ncs_allcertificate_expiry_dates import CaIssuer_CNA_23_10
from flows.Security.Certificate.ncs_allcertificate_expiry_dates import CaIssuer_CNB
from six.moves import range


class K8sValidation(Validator):
    def get_pods_lists(self, namespace='-n ncms', ignore_jobs=True):
        pods_list = self.get_all_pods(namespace=namespace, ignore_jobs=ignore_jobs)
        pods_headers = self.get_output_from_run_cmd("sudo {} get pods {} | head -n 1".format(
            adapter.kubectl(), namespace)).split()
        return self.parse_pods_list(pods_list, namespace=namespace, pods_headers=pods_headers)

    def get_all_pods(self, namespace='--all-namespaces', ignore_jobs=True):
        filter_out_jobs = ''
        if ignore_jobs:
            filter_out_jobs = '| grep -v Complete'

        kubectl = adapter.kubectl()
        out = self.get_output_from_run_cmd("sudo {} get pods {} --no-headers {}".format(
            kubectl, namespace, filter_out_jobs), timeout=45, add_bash_timeout=True)
        return out

    @staticmethod
    def parse_pods_list(kube_out, namespace, pods_headers):
        not_ready_pods = []
        ready_pods = []
        for line in kube_out.splitlines():
            words = re.split(r'\s{2,}', line)
            if len(words) > 0:
                pod_dict = {pods_headers[i]: words[i] for i in range(len(pods_headers))}
                status = pod_dict["STATUS"]
                if status != 'Running':
                    not_ready_pods.append(pod_dict)
                else:
                    ready = pod_dict["READY"]
                    readies = ready.split("/")
                    if readies[0] != readies[1]:
                        not_ready_pods.append(pod_dict)
                    else:
                        ready_pods.append(pod_dict)
        return ready_pods, not_ready_pods

    def get_all_pods_limits(self):
        kubectl = adapter.kubectl()
        out = self.get_output_from_run_cmd(
            "sudo " + kubectl + " get pods --all-namespaces -o json | jq '[.items[] | "
            "{pod_name: .metadata.name, container_limits:[.spec.containers[] |"
            "{container_name: .name, container_limit: .resources}]}]'",
            timeout=45, add_bash_timeout=True)
        return out

    def get_all_containers_status(self, namespace=None):
        if not namespace:
            namespace = '--all-namespaces'

        kubectl = adapter.kubectl()
        out = self.get_output_from_run_cmd(
            "sudo " + kubectl + " get pods {} -o json | jq '[.items[] | "
            "{{pod_name: .metadata.name, containers_status:[.status.containerStatuses[] | "
            "{{container_name: .name, container_state: .state}}]}}]'".format(namespace),
            timeout=45, add_bash_timeout=True)
        return out

    def get_nodes_only(self):
        kubectl = adapter.kubectl()
        cmd = "sudo {} get nodes --no-headers -A -o custom-columns=NAME:.metadata.name".format(kubectl)
        nodes_list = self.get_output_from_run_cmd(cmd, timeout=45, add_bash_timeout=True).splitlines()
        return nodes_list

    def get_nodes_lists(self):
        kubectl = adapter.kubectl()
        cmd = "sudo {} get nodes --no-headers".format(kubectl)
        nodes_list = self.get_output_from_run_cmd(cmd, timeout=45, add_bash_timeout=True)
        return self.parse_nodes_list(nodes_list)

    @staticmethod
    def parse_nodes_list(kube_out):
        not_ready_list = []
        warned_list = []
        ready_list = []
        for line in kube_out.splitlines():
            rows = line.split()
            if len(rows) > 0:
                if (rows[1] != 'Ready'):
                    if rows[1].startswith('Ready'):
                        warned_list.append('{} - {}'.format(rows[0], rows[1]))
                    else:
                        not_ready_list.append(rows[0])
                else:
                    ready_list.append(rows[0])
        return ready_list, not_ready_list, warned_list

    def add_details_when_validation_fails(self, resource, resource_name, namespace=''):
        if namespace:
            if namespace !='--all-namespaces' and '-n ' not in namespace:
                namespace = "-n {}".format(namespace)
        self._details += "Following are the last events for '{}':\n".format(resource_name)
        kubectl = adapter.kubectl()
        cmd = "sudo {} describe {} {} {} | tail -100".format(kubectl,
                                                             resource,
                                                             resource_name,
                                                             namespace)
        pod_description = self.get_output_from_run_cmd(cmd, timeout=45, add_bash_timeout=True)
        event_info = PythonUtils.get_lines_after_label(pod_description, "Events:")
        self._details = self._details + " {}\n\n".format(event_info)


class RunK8sCmd(DataCollector):
    objective_hosts = {Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
                       Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
                       Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER]}

    def collect_data(self, cmd, timeout, add_bash_timeout, get_output_from_run_cmd):
        if get_output_from_run_cmd:
            return self.get_output_from_run_cmd(cmd, timeout=timeout, add_bash_timeout=add_bash_timeout)

        return self.run_cmd(cmd, timeout=timeout, add_bash_timeout=add_bash_timeout)


# this test are based on the confluence page:
# https://confluence.ext.net.nokia.com/pages/viewpage.action?pageId=716182350
# by Gideon
# todo - check that is works

class NodeAreReadyValidetor(K8sValidation):
    objective_hosts = [Objectives.ONE_MASTER]

    def __init__(self, ip):
        Validator.__init__(self, ip)

    def set_document(self):

        self._unique_operation_name = "all_nodes_are_ready"
        self._title = "Verify nodes are ready"
        self._failed_msg = ""
        self._severity = Severity.ERROR

        self._implication_tags = [ImplicationTag.PERFORMANCE, ImplicationTag.APPLICATION_DOMAIN]

    def is_validation_passed(self):
        ready_list, not_ready_list, warned_list = self.get_nodes_lists()
        self._not_ready_list = not_ready_list
        if len(ready_list) == 0:
            self._failed_msg += "Did not get nodes list from 'kubectl get nodes' "
            return False
        if len(not_ready_list) > 0:
            self._failed_msg += "The following nodes are not ready:\n{}\n".format(",\n".join(not_ready_list))
            for node in not_ready_list:
                self.add_details_when_validation_fails(resource='nodes', resource_name=node)
        if len(warned_list) > 0:
            self._failed_msg += "\nThe following nodes are ready but having some issues:\n{}".format(
                ",\n".join(warned_list))
        if not_ready_list or warned_list:
            return False
        return True


class AllPodsReadyAndRunning(K8sValidation):
    objective_hosts = [Objectives.ONE_MASTER]
    #We do not want to occupy too much of the kube API
    MAX_NUMBER_OF_ALLOWED_DETAILS = 25
    def __init__(self, ip):
        Validator.__init__(self, ip)
    def set_document(self):
        self._title = "Verify all pods are ready and on running state"
        self._unique_operation_name = "all_pods_are_running_all_namespaces"
        self._failed_msg = "Not all pods are running\n"
        self._severity = Severity.NOTIFICATION
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.SYMPTOM, ImplicationTag.APPLICATION_DOMAIN]

    def is_validation_passed(self):
        namespace = self.get_namespace()
        high_severity_namespaces_list = ['ncms', 'kube-system']
        ready_pods, not_running_pods = self.get_pods_lists(namespace=namespace)
        if len(ready_pods) == 0:
            self._failed_msg += "Did not get pods list from 'kubectl get pods {}'".format(namespace)
            return False
        if not_running_pods:
            not_running_pods_str = "\n".join("{}".format(json.dumps(item)) for item in not_running_pods)
            self._failed_msg += "Following pods are not running or partially not ready:\n{}".format(not_running_pods_str)
            self._failed_msg += "\n\nDetails of the first {}:".format(AllPodsReadyAndRunning.MAX_NUMBER_OF_ALLOWED_DETAILS)
            self._failed_msg += "\n---------------------------\n"

            if len(not_running_pods) > AllPodsReadyAndRunning.MAX_NUMBER_OF_ALLOWED_DETAILS:
                not_running_pods_short = not_running_pods[:AllPodsReadyAndRunning.MAX_NUMBER_OF_ALLOWED_DETAILS]
            else:
                not_running_pods_short = not_running_pods

            for failed_pod in not_running_pods_short:
                pod_name = failed_pod["NAME"]
                failed_namespace = self.get_namespace()
                if failed_namespace == "--all-namespaces":
                    failed_namespace = failed_pod["NAMESPACE"]
                if failed_namespace in high_severity_namespaces_list:
                    self._severity = Severity.ERROR
                self.add_details_when_validation_fails(resource='pods', resource_name=pod_name, namespace=failed_namespace)
            return False
        return True

    def get_namespace(self):
        return "--all-namespaces"


# todo - more name spaces
class SystemPodsReadyAndRunning(AllPodsReadyAndRunning):
    objective_hosts = [Objectives.ONE_MASTER]

    def __init__(self, ip):
        Validator.__init__(self, ip)

    def set_document(self):
        self._title = "Verify all system pods are ready and on running state"
        self._unique_operation_name = "all_pods_are_running"
        self._failed_msg = "Not all pods are running\n"
        self._severity = Severity.ERROR

        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.SYMPTOM, ImplicationTag.APPLICATION_DOMAIN]

    def get_namespace(self):
        return "-n kube-system"


class TotalNumberOfPodsPerCluster(Validator):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._unique_operation_name = "Total_number_of_pods_per_cluster"
        self._title = "Total number of pods per cluster"
        self._failed_msg = "There are more than 17000 pods in this cluster"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.RISK_RESOURCE_CLEANING_RECOMMENDED]

    def is_validation_passed(self):
        kubectl = adapter.kubectl()
        cmd = "sudo {} get pods -A --no-headers | wc -l".format(kubectl)
        out = self.get_output_from_run_cmd(cmd, timeout=45, add_bash_timeout=True)
        if int(out) > 17000:
            self.failed_msg = "There are more than 17000 pods in this cluster"
            return False
        else:
            return True


class NumberOfPodsPerNode(Validator):
    objective_hosts = [Objectives.ONE_MASTER]
    POD_THRESHOLD_PER_NODE = 110

    def set_document(self):
        self._unique_operation_name = "total_number_of_pods_per_node"
        self._title = "Total number of pods per node"
        self._failed_msg = "There are more than {} pods per node".format(self.POD_THRESHOLD_PER_NODE)
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.RISK_RESOURCE_CLEANING_RECOMMENDED]

    def is_validation_passed(self):
        kubectl = adapter.kubectl()
        cmd = "sudo {} get nodes".format(kubectl)
        node = self.get_output_from_run_cmd(cmd, timeout=45, add_bash_timeout=True)
        node_split = node.split()
        node_list = []
        for num in range(1, len(node_split)):
            if num % 5 == 0:
                node_list.append(node_split[num])

        bad_node = []
        count = 0
        kubectl = adapter.kubectl()

        for nodes in node_list:
            cmd1 = "sudo {} describe node {}".format(kubectl, nodes)
            cmd = cmd1 + '| grep -i non-t'
            out = self.get_output_from_run_cmd(cmd, timeout=45, add_bash_timeout=True)
            out_split = out.split(':')
            new_split = out_split[1].split()
            num = new_split[0][1:]
            if num.isdigit():
                if int(num) > self.POD_THRESHOLD_PER_NODE:
                    bad_node.append(nodes)
                    count += 1
            else:
                self._failed_msg = "Unexpected system output, integer is expected"

        if len(bad_node):
            bad_node_st = "\n".join(bad_node)
            self._failed_msg = "There are more than {} pods in all of the below nodes in the cluster: \n {}".format(
                self.POD_THRESHOLD_PER_NODE, bad_node_st)

        if count > 0:
            return False
        else:
            return True


class TotalNumberOfContainersPerCluster(K8sValidation):
    objective_hosts = [Objectives.ONE_MASTER]
    CONTAINER_THRESHOLD = 34000

    def set_document(self):
        self._unique_operation_name = "Total_number_of_containers_per_cluster"
        self._title = "Total number of containers per cluster"
        self._failed_msg = "There are more than {} containers in this cluster".format(self.CONTAINER_THRESHOLD)
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.RISK_RESOURCE_CLEANING_RECOMMENDED]

    def is_validation_passed(self):
        out = self.get_all_pods()
        out_split = out.split()
        out_new = []
        for list in out_split:
            if '/' in list:
                out_new.append(list)

        count = 0
        for container in out_new:
            number = container.split('/')
            count = count + int(number[1])

        if count > self.CONTAINER_THRESHOLD:
            self._failed_msg = "There are more than {} containers present in the cluster".format(
                self.CONTAINER_THRESHOLD)
            return False
        else:
            return True


class ContainersNcmsPodsReadyAndRunning(AllPodsReadyAndRunning):
    objective_hosts = [Objectives.ONE_MASTER]

    def __init__(self, ip):
        Validator.__init__(self, ip)

    def set_document(self):
        self._title = "Check all ncms pods are ready and on running state"
        self._unique_operation_name = "all_containers_in_pods_are_running_ncms"
        self._failed_msg = "Not all containers in pods are running\n"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.SYMPTOM, ImplicationTag.APPLICATION_DOMAIN]

    def get_namespace(self):
        return "-n ncms"




class AllPodsHasLimits(K8sValidation):
    objective_hosts = [Objectives.ONE_MASTER]

    def __init__(self, ip):
        Validator.__init__(self, ip)

    def set_document(self):
        self._title = "Verify all pods has limits of CPU and memory"
        self._unique_operation_name = "all_pods_has_limits"
        self._failed_msg = "Not all pods has limits (details in the .json file)"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.SYMPTOM]

    def is_validation_passed(self):
        status = True
        all_pods_limits = json.loads(self.get_all_pods_limits())
        for pod in all_pods_limits:
            try:
                for container in pod['container_limits']:
                    if not PythonUtils.get_value_by_path_from_nested_dict(container,
                                                                          ['container_limit', 'limits', 'cpu']):
                        status = False
                        self.add_to_validation_log('Pod {}, container {}: No max limits of CPU'.format(pod['pod_name'],
                                                                                                       container[
                                                                                                           'container_name']))
                    if not PythonUtils.get_value_by_path_from_nested_dict(container,
                                                                          ['container_limit', 'limits', 'memory']):
                        status = False
                        self.add_to_validation_log(
                            'Pod {}, container {}: No max limits of memory'.format(pod['pod_name'],
                                                                                   container['container_name']))
            except:
                continue
        if status:
            self.add_to_validation_log(('All pods containers has limits'))
        return status


class CheckCloudUserPermissions(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.MASTERS],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.MASTERS],
    }

    def __init__(self, ip):
        Validator.__init__(self, ip)

    def set_document(self):
        self._unique_operation_name = "Check_cloud_user_permissions"
        self._title = "check cloud-user home dir ownership and permissions"
        self._failed_msg = "please check the cloud-user home directory permission, should be 700 and home directory owner should be cloud-user"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION, ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        home_dir_path = '/home/cloud-user'
        if self.file_utils.is_dir_exist(home_dir_path):
            cmd = "stat -c \"%a %U\" {}".format(home_dir_path)
            dir_attributes = self.get_output_from_run_cmd(cmd).split()

            if len(dir_attributes) != 2:
                raise UnExpectedSystemOutput(self.get_host_ip(), cmd, dir_attributes,
                                             "Expected to have exactly 2 attributes in the list")
            dir_perm = dir_attributes[0]
            dir_owner = dir_attributes[1]

            if dir_perm == '700' and dir_owner == 'cloud-user':
                return True

            self._failed_msg = "home directory {} perm and owner are not as expected, perm: {}, expected: '700'," \
                               "owner: {}, expected: 'cloud-user'".format(home_dir_path, dir_perm, dir_owner)
            return False
        self._failed_msg = "home directory {} not found ".format(home_dir_path)

        return False
'''
class AllNodesHaveRoutesToAPIServer(Validator):
    objective_hosts = [Objectives.MASTERS, Objectives.WORKERS, Objectives.EDGES]

    def __init__(self, ip):
        Validator.__init__(self, ip)

    def set_document(self):
        self._title = "Verify all nodes has routes to api server"
        self._unique_operation_name = "all_nodes_has_routes_to_apiserver"
        self._failed_msg = "Some nodes dont have route to kube apiserver."
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.SYMPTOM]

    def is_validation_passed(self):
        findsvc_cmd = 'sudo kubectl get svc kubernetes --no-headers'
        ip_address = self.run_and_get_the_nth_field(findsvc_cmd, 3)
        findroute_cmd = 'sudo ip r g {}'.format(ip_address)
        route_status = self.get_output_from_run_cmd(findroute_cmd)
        port_status = self.is_port_open(ip_address)
        status = all([bool(route_status), port_status])
        if status:
            return True
        self._failed_msg += '\nUnable to reach k8 service from this node, Please check if route present or 443 port opened is not connecting now'
        return False

    def is_port_open(self, ip_address):
        findport_cmd = 'sudo nc -zvw 15 {} 443'.format(ip_address)
        ret_code, out, err = self.run_cmd(findport_cmd)
        if 'Connected to' in err:
            return True
        return False
'''


class K8DefaultServiceIpDataCollector(DataCollector):
    objective_hosts = [Objectives.WORKERS, Objectives.EDGES]

    # todo - do we needs this
    def is_port_open(self, ip_address):
        findport_cmd = 'sudo nc -zvw 15 {} 443'.format(ip_address)
        ret_code, out, err = self.run_cmd(findport_cmd)
        if 'Connected to' in err:
            return True
        return False

    def collect_data(self, **kwargs):
        ip_address = kwargs['ip_address']
        find_route_cmd = 'sudo ip r g {}'.format(ip_address)
        rc, route_status, err = self.run_cmd(find_route_cmd)
        test = re.findall(r'dev|via', route_status, re.IGNORECASE)
        flg_is_route_found = False
        if any(test):
            flg_is_route_found = True
        return flg_is_route_found


class AllNodesHaveRoutesToAPIServer(Validator):
    objective_hosts = [Objectives.ONE_MASTER]

    def __init__(self, ip):
        Validator.__init__(self, ip)

    def set_document(self):
        self._title = "Verify all nodes have routes to api server"
        self._unique_operation_name = "all_nodes_has_routes_to_apiserver"
        self._failed_msg = "Some nodes dont have route to kube apiserver."
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.SYMPTOM]

    def is_validation_passed(self):
        findsvc_cmd = 'sudo kubectl get svc kubernetes -n default --no-headers'
        ### -n default -- to specify DEFAULT namespace explicitly, even if i dont mention it wil be by default DEFAULT only but But users can change this anytime. kubectl config set-context kubectl-context --namespace=XXXXXX
        ip_address = self.run_and_get_the_nth_field(findsvc_cmd, 3)

        routes_status_from_all_hosts = self.run_data_collector(K8DefaultServiceIpDataCollector, ip_address=ip_address)
        hosts_with_no_route = list([host_name for host_name in list(routes_status_from_all_hosts.keys()) if routes_status_from_all_hosts[host_name] is False])

        if len(hosts_with_no_route) >= 1:
            self._failed_msg += 'Unable to reach k8 service from the fallowing nodes: {}, ' \
                                '\n Please check if route present or 443 port opened is not connecting now'.format(
                hosts_with_no_route)
            return False

        return True


class RootCertificateExpiryValidator(Validator):
    objective_hosts = [Objectives.ONE_MASTER]

    def __init__(self, ip):
        Validator.__init__(self, ip)

    def set_document(self):
        self._title = "Check if root certificates doesnt expire "
        self._unique_operation_name = "root_certs_are_valid"
        self._failed_msg = "TBD"
        self._severity = Severity.CRITICAL
        self._is_clean_cmd_info = True
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.SYMPTOM, ImplicationTag.APPLICATION_DOMAIN]

    def is_validation_passed(self):
        td = datetime.timedelta(days=180)
        check_date = datetime.datetime.now() + td
        end_date = self.decode_openssl()
        formatted_end_date = parse(end_date)
        t1 = str(formatted_end_date).split(' ')[0]
        t2 = str(datetime.datetime.now().date())
        remaining_days = parse(t1) - parse(t2)
        rem_days = remaining_days.days

        if formatted_end_date.replace(tzinfo=None) < check_date and self.parse_to_int(rem_days) > 0:
            self._failed_msg = "The expiry date of root cert is: {}. it is less than 180 days. " \
                               "It will be expired in {} from today.".format(end_date,
                                                                             str(remaining_days).split(',')[0])
            return False

        elif formatted_end_date.replace(tzinfo=None) < check_date and int(rem_days) <= 0:
            self._failed_msg = "The root certificate already expired."
            return False

        self._validation_log.append("The root certificate expiry date is: {}. "
                                    "It will expire in {} from today ".format(end_date,
                                                                              str(remaining_days).split(',')[0]))

        return True

    def decode_openssl(self):
        self._is_clean_cmd_info = True
        cmd = "sudo openssl x509 -enddate -noout -in /etc/kubernetes/ssl/ca.pem"
        out = self.get_output_from_run_cmd(cmd)
        return out.split("=")[1]


class VerifyOrphanedPods(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ALL_NODES],
        Deployment_type.NCS_OVER_BM: [Objectives.ALL_NODES],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ALL_NODES]
    }

    def set_document(self):
        self._unique_operation_name = "verify_orphaned_pods"
        self._title = "Verify Orphaned Pods"
        self._failed_msg = "Found Orphaned pods in the cluster"
        self._severity = Severity.NOTIFICATION
        self._details = ""
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.SYMPTOM, ImplicationTag.APPLICATION_DOMAIN]

    def is_validation_passed(self):
        cmd = "sudo journalctl -ru kubelet --since '1 minute ago' |grep -i 'orphaned' | grep -v 'Cleaned up' |sort|uniq"
        out = self.get_output_from_run_cmd(cmd)
        if out:
            self._details += "{}".format(out)
            return False
        return True


class ValidatePodsRestartedDueToOutofMemory(Validator):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._unique_operation_name = "verify_pods_restarted_due_out_of_memory"
        self._title = "Verify pods restarted due to out of memory"
        self._failed_msg = ""
        self._severity = Severity.CRITICAL
        self._details = ""
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.SYMPTOM, ImplicationTag.APPLICATION_DOMAIN]

    def is_validation_passed(self):
        # get pod info and filter only namespace,podname,pod exit reason/status
        pods_info_cmd = "sudo kubectl get pods --all-namespaces -o=jsonpath='{range .items[*]}{.metadata.namespace}{\"|\"}{.metadata.name}{\"|\"}{.status.containerStatuses[].lastState.terminated.reason}{\"\\n\"}{end}'"
        pods_info_ouptut = self.get_output_from_run_cmd(pods_info_cmd)
        if isinstance(pods_info_ouptut, bytes):
            pods_info_ouptut = pods_info_ouptut.decode('utf-8')
        pods_info_in_list = pods_info_ouptut.split(',')[0].split('\n')
        restarted_pod_list = []
        for each_pod in pods_info_in_list:
            if 'OOMKilled' in each_pod and ('kube-system' in each_pod or 'ncms' in each_pod):
                restarted_pod_list.append(each_pod)
        re_arrange_list_elements = '\n'.join(
            restarted_pod_list)  # converting restarted_pod_list in to a string with '\n'.
        if len(restarted_pod_list) != 0:
            self._failed_msg += 'Following Pods were restarted due to memory over utilization \n{} '.format(
                re_arrange_list_elements)
            return False
        else:
            return True


class CheckWhetherCbisDirsExistsUnderRootDir(Validator):
    objective_hosts = [Objectives.MANAGERS]

    def set_document(self):
        self._unique_operation_name = "check_whether_cbis_dirs_exists_under_root_dir"
        self._title = "Check whether cbis dirs exists under root dir"
        self._failed_msg = ""
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        files_to_be_checked = ['cbis', 'cbis-installer', 'cbis-manager.tar.gz']
        count = 0
        missing_file = []

        if gs.is_ncs_central():
            return True

        if gs.get_version() < Version.V24_11:
            files_to_be_checked.append('cbis-extensions')

        for file in files_to_be_checked:
            cmd = "/root/{}".format(file)
            if self.file_utils.is_dir_exist(cmd) or self.file_utils.is_file_exist(cmd):
                count += 1
            else:
                missing_file.append(file)

        if count == len(files_to_be_checked):
            return True
        else:
            self._failed_msg = "The following files seems to be missed under /root/ directory in manager nodes : {}".format(
                missing_file)
            return False


class ValidateNamespaceStatus(Validator):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._unique_operation_name = "verify_namespaces_are_in_active_status"
        self._title = "Validate namespace in Active status"
        self._failed_msg = ""
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        kubectl = adapter.kubectl()
        cmd = "sudo {} get namespaces --no-headers=true --field-selector=status.phase!=Active -o " \
              "custom-columns='NAMESPACE:.metadata.name,STATUS:.status.phase' ".format(kubectl)
        cmd_output = self.get_output_from_run_cmd(cmd, timeout=45, add_bash_timeout=True).strip().split("\n")
        namespace_list = [lines.split() for lines in cmd_output]
        length_of_namespace = len(namespace_list)
        if length_of_namespace == 1 and len(namespace_list[0]) == 0:
            length_of_namespace = 0
        if int(length_of_namespace) > 0:
            self._failed_msg += "Below namespaces are not in Active state:\n{}".format(
                '\n'.join('-'.join(namespace) for namespace in namespace_list))
            return False
        return True


#####################################################
###     ICET-2663 | Bug fix | Validate  ncms-ca-issuer exists in the cluster
###     Author :   SOUVIK DAS |     30-12-2024 
#####################################################

################### SOUVIK CODE STARTS #####################
###     ICET-2812 | Bug fix | ExternalCA Check for NCS CNA
###     Author :   SOUVIK DAS |     11-03-2025 
############################################################

class ValidateCAIssuer(InformatorValidator):
    objective_hosts = {
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "verify_ca_issuer_is_present"
        self._title = "Validate ncms-ca-issuer exists in the cluster"
        self._failed_msg = ""
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._is_highlighted_info = True
        self._title_of_info = "External CA Integration"
        self._is_pure_info = False

    def check_ncms_ca_issuer(self):
        cmd = "sudo  kubectl get clusterissuers ncms-ca-issuer -o=jsonpath='{.status.conditions[?(@.type==\"Ready\")].status}'"
        cmd_output = self.get_output_from_run_cmd(cmd)
        cmd2 = "sudo echo $?"
        cmd_output2 = self.get_output_from_run_cmd(cmd2)
        return cmd_output, cmd_output2

    def is_validation_passed(self):

    ###############################################################
    ##
    ##   Till NCS 22.12 normal check "check_ncms_ca_issuer" is fine and This validation is correct but 23.10 onward External CA integration is intriduced as a Day2 post install operation so in this case we need to verify if Version is NCS 22.12 above or not and if yes then we need to see first ExternalCA integrated or not. And If external CA is used then the command "kubectl get clusterissuers ncms-ca-issuer" will return error as clusterissuers ncms-ca-issuer itsemf won't be there so the validation directly we cant use
    ##
    ############################################################### 
        
        if gs.get_version() <= Version.V22_12:
            cmd_output, cmd_output2 = self.check_ncms_ca_issuer()
            if cmd_output == "True" and int(cmd_output2) == 0:
                return True
            else:
                return False
        else:
            ## Version is greater than 22.12 | NCS 23.10 / 24.7/ 24.11
            ## First check External CA used or not
            ## Verify Deployment type CN-A or CN-B

            if gs.get_deployment_type() == Deployment_type.NCS_OVER_BM:
                is_external_CA_issuer_used_dict = self.run_data_collector(CaIssuer_CNB)
            else:
                is_external_CA_issuer_used_dict = self.run_data_collector(CaIssuer_CNA_23_10)

            is_external_CA_issuer_data = list(is_external_CA_issuer_used_dict.values())[0]
            is_external_CA_issuer_used = is_external_CA_issuer_data['is_external_ca']

            for key,value in list(is_external_CA_issuer_data.items()):
                if value !="":
                    self._system_info = self._system_info + "\n" + str(key) + " : " + str(value)

            if is_external_CA_issuer_used:      ## If True case- External CA used
                self._system_info = str(self._system_info) + "\nExternal CA Integrated"
                return True     ## In case of EXTERNAL CA no ClusterIssuer on cluster
            else:       ## If False case - External CA Not used
                self._system_info = str(self._system_info) + "\nNO External CA Integrated"
                cmd_output, cmd_output2 = self.check_ncms_ca_issuer()
                if cmd_output == "True" and int(cmd_output2) == 0:
                    return True
                else:
                    return False

##############      SOUVIK CODE ENDS    ##################

class VerifyKubectlCommand(Validator):
    objective_hosts = [Objectives.MASTERS]

    def set_document(self):
        self._unique_operation_name = "verify_kubectl_command_execution"
        self._title = "Verify kubectl command execution on master nodes"
        self._failed_msg = "Error executing kubectl command"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PRE_OPERATION]

    def is_validation_passed(self):
        cmd = "sudo kubectl get nodes --kubeconfig=/root/.kube/config"
        if self.run_cmd_return_is_successful(cmd):
            return True

        else:
            self._failed_msg = self._failed_msg + "\nPlease Check the confluence page.\n"
            return False


class ServiceTokenValidityCheck(Validator):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._unique_operation_name = 'service_token_validity_check'
        self._title = 'Service token validity check'
        self._failed_msg = ""
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]
        self._is_clean_cmd_info = True

    def get_installed_istio_version(self):
        installed_istio_charts = json.loads(self.get_output_from_run_cmd('sudo helm ls -n istio-system -o json'))
        for chart in installed_istio_charts:
            if re.findall(r'cist-istio-\d+.\d+.\d+', chart['chart']):
                installed_istio_version = chart['app_version']
                return pkg_resources.parse_version(installed_istio_version)
        return []

    def is_istio_version_affected(self):
        installed_istio_version = self.get_installed_istio_version()
        istio_version_with_fix = pkg_resources.parse_version('1.15.0')
        if not installed_istio_version:
            return False
        if istio_version_with_fix > installed_istio_version:
            return True
        else:
            return False

    def is_validation_passed(self):
        time_conversion = 86400
        max_days = 300
        resource_name = [("bcmt-operator", "ncms")]
        is_istio_version_affected = self.is_istio_version_affected()
        # istio application versions 1.15.0 or greater should not get checked for this validation because 1.15.0 has
        # the fix for this bug
        if is_istio_version_affected:
            resource_name.append(("istio-cni-node", "istio-system"))
        pod = []
        for [pods, ns] in resource_name:
            cmd = "sudo kubectl get pods -n {ns} -o custom-columns=:.metadata.name |grep {pod}".format(pod=pods, ns=ns)
            return_code, out, err = self.run_cmd(cmd)
            if return_code == 0:
                out = out.strip().split('\n')
            if len(out) > 0:
                for pod_name in out:
                    cmd = "sudo kubectl get pods {pod_name} -n {ns} ".format(pod_name=pod_name, ns=ns)
                    cmd = cmd + "-o jsonpath='{.metadata.creationTimestamp}'"
                    out = self.get_output_from_run_cmd(cmd).strip()
                    current_date_seconds = int(time.time())
                    creation_date = time.strptime(out, '%Y-%m-%dT%H:%M:%SZ')
                    creation_date_seconds = int(time.mktime(creation_date))
                    validity_time = (int(current_date_seconds) - int(creation_date_seconds)) / time_conversion
                    if int(validity_time) > max_days:
                        pod.append(pod_name)
            else:
                continue
        if len(pod) > 0:
            self._failed_msg += ("Below pods age are nearing 365 days, service token about to expire.\n"
                                 "{}").format('\n'.join(pod))
            return False
        else:
            return True

class CheckWhetherYumRepoExists(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.MASTERS, Objectives.EDGES, Objectives.WORKERS],
        Deployment_type.NCS_OVER_BM: [Objectives.MASTERS, Objectives.EDGES, Objectives.WORKERS]
    }

    def set_document(self):
        self._unique_operation_name = "check_whether_bcmt_extra_repo_exists"
        self._title = "Check whether bcmt-extra repo is present under '/etc/yum.repos.d'"
        self._failed_msg = ""
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]
        self._blocking_tags = [BlockingTag.SCALE]
        self._is_clean_cmd_info = True

    def is_validation_passed(self):
        files_to_be_checked = "/etc/yum.repos.d/bcmt-extra.repo"
        if not self.file_utils.is_file_exist(files_to_be_checked):
            self._failed_msg = "The following file seems to be missing : \n'{}'".format(files_to_be_checked)
            return False
        return True


class CheckBCMTRegistry(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.MASTERS, Objectives.EDGES, Objectives.WORKERS],
        Deployment_type.NCS_OVER_BM: [Objectives.MASTERS, Objectives.EDGES, Objectives.WORKERS]
    }

    def set_document(self):
        self._unique_operation_name = "check_bcmt_registry"
        self._title = "Check if repositories available in bcmt-registry:5000"
        self._failed_msg = ""
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.SYMPTOM]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE, BlockingTag.MIGRATION]
        self._is_clean_cmd_info = True

    def is_validation_passed(self):
        '''
        checking the bcmt-registry through root CA cert because if we don't specify CAcert, it checks through '/etc/pki/tls/certs/ca-bundle.crt'
        if '/etc/pki/tls/certs/ca-bundle.crt' is not having root CA at first position the validation may fail, so checking through root CAcert itself.
        '''
        return_code, out, err = self.run_cmd("sudo curl --max-time 10 https://bcmt-registry:5000/v2/_catalog?n=1 --cacert /etc/kubernetes/ssl/ca.pem")
        if return_code == 0:
            try:
                parsed_output = json.loads(out)
                repos = parsed_output.get('repositories', [])
                if len(repos) >= 1:
                    return True
                else:
                    self._failed_msg += "No repositories found in bcmt-registry"
                return False
            except ValueError:
                raise UnExpectedSystemOutput(self.get_host_ip(), out, output=out, message="Unable to parse JSON")

        elif return_code == 35:
            self._failed_msg += "Failed to connect to bcmt-registry, SSL handshake failure."

            return False
        else:
            self._failed_msg += "Failed to connect to bcmt-registry."

            return False

