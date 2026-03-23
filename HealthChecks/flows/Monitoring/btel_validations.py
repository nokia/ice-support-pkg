from __future__ import absolute_import
from HealthCheckCommon.operations import *
import re
import tools.sys_parameters as sys_parameters

from HealthCheckCommon.validator import Validator, InformatorValidator
from flows.K8s.k8s_components.k8s_sanity_checks import K8sValidation
from tools.lazy_global_data_loader import *
from tools.python_utils import PythonUtils
from six.moves import zip


######  SOUVIK BTEL TEST CODE   BEGINS  #########################

######################################################
## btel_validations     bm-20-555,bm-20-803,bm-21-allinone,vsphere,openstack
## bm-20-555,vsphere,bm-20-803
#######################################################

class BTELValidationStatusRequirement(K8sValidation):

    #### This class is BASE class . Here we are checing Wheher in the cluster
    #### BTEL is installed or not....
    objective_hosts = [Objectives.ONE_MASTER]

    #### the data of if BTEL is installed is saved in a Class varible. it is shared among all validation
    #### it is save to use it even this is multythrede system becouse we assume the answer of 'is BTEl in helm'
    #### will alwyse return the same answer if run tiwece.
    #we assume that all the validation that inhetare from this base class should run if and only if BTEL is instaled

    is_BTEL_installed = None
    app_name_map = None

    def get_btel_installed_status(self):
        stream = self.get_output_from_run_cmd("sudo helm status btel | grep -i 'status:' | cut -d ' ' -f2")
        btel_installed_or_not = stream.strip()
        return btel_installed_or_not

    def installed_btel_version(self):
        stream = self.get_output_from_run_cmd(
            "sudo helm status btel | grep -i 'version Installed :' | cut -d ':' -f2 | sed 's/^ *//'")
        # stream=self.run_cmd("sudo helm status btel | grep -i 'version Installed :' | cut -d ':' -f2 | sed 's/^ *//'",timeout=120)
        btel_version = stream.strip()
        return btel_version

    def is_btel_in_helm(self):
        cmd = "sudo helm list"
        out = self.get_output_from_run_cmd(cmd)
        return "btel" in out

    def get_btel_app_namespace(self):
        try:
            btel_chart = {}
            charts = self.get_dict_from_command_output("sudo helm list --output json --deployed", 'json', timeout=10)
            btel_app = []
            btel_namespace = []
            try:
                for chart in charts["Releases"]:
                    charts = chart["Chart"]
                    if 'btel' in charts.lower():
                        btel_app.append(chart["Name"])
                        btel_namespace.append(chart["Namespace"])
            except:
                self._system_info = "No charts are installed"
            btel_chart = dict(list(zip(btel_app, btel_namespace)))
            return btel_chart

        except UnExpectedSystemOutput:
            return False

    def get_app_map(self):
        try:
            btel_app_namespace = self.get_btel_app_namespace()
            if btel_app_namespace:
                if len(btel_app_namespace) > 0:
                    namespace = []
                    apps = []
                    for app, name in list(btel_app_namespace.items()):
                        cmd = "sudo helm get values {} --all".format(app)
                        out = self.get_output_from_run_cmd(cmd)
                        output = PythonUtils.yaml_safe_load(out)
                        output_ext = output['tags']
                        namespace.append(name)
                        apps.append(output_ext)
                    apps_namespace = dict(list(zip(namespace, apps)))
                    return apps_namespace
            return False
        except UnExpectedSystemOutput:
            return False

    def _is_app_installed(self, app_name):
        if BTELValidationStatusRequirement.app_name_map is None:
            BTELValidationStatusRequirement.app_name_map = self.get_app_map()

        app_name_map = BTELValidationStatusRequirement.app_name_map
        if not app_name_map:
            return False
        self.dict = {}
        for namespace, apps in list(app_name_map.items()):
            count = 0
            for key, value in list(apps.items()):
                if app_name in key:
                    if value == True:
                        count += 1
            self.dict[namespace] = count

        total = sum(self.dict.values())
        if total > 0:
            return True
        else:
            return False

    def namespace_app_exists_dict(self):
        final_dict = {}
        for namespace, app_exists in list(self.dict.items()):
            if app_exists != 0:
                final_dict[namespace] = app_exists
        return final_dict

    def is_prerequisite_fulfilled(self):
        if BTELValidationStatusRequirement.is_BTEL_installed is None:
            BTELValidationStatusRequirement.is_BTEL_installed = self.is_btel_in_helm()
        return BTELValidationStatusRequirement.is_BTEL_installed


class is_btel_installed_successfully(BTELValidationStatusRequirement):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "is_btel_installed_successfully"
        self._title = "Verify btel installed successfully"
        self._failed_msg = "Verify btel not installed successfully"
        self._severity = Severity.ERROR

        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        return self.get_btel_installed_status() == "DEPLOYED"


class FluentdDaemonSetRunningInAllNodesOrNot(BTELValidationStatusRequirement):
    #### VALIDATION : 1
    #### Inherited from BASE CLASS
    #### Here we are checking Fluentd DaemonSet is configured in All NODES or not

    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "FluentdDaemonSetRunningInAllNodesOrNot"
        self._title = "Verify FluentdDaemonSet Running In All Nodes Or Not"
        self._failed_msg = "FluentdDaemonSet Not runnign in All Nodes"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PRE_OPERATION, ImplicationTag.APPLICATION_DOMAIN]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):

        # print ("SOUVIK 1 BTEL Test STARTS: FluentdDaemonSetRunningInAllNodesOrNot........")

        stream = self.get_output_from_run_cmd("sudo /usr/local/bin/kubectl get nodes --no-headers=true | wc -l")
        total_nodes = stream.strip()
        # print ("TOTAL NODES :  " +total_nodes)

        stream = self.get_output_from_run_cmd(
        "sudo /usr/local/bin/kubectl get daemonset btel-belk-fluentd-daemonset --namespace btel -o jsonpath=\'{.status.desiredNumberScheduled}\'")
        desired_pods_Fluentd_Ds = stream.strip()
        # print ("TOTAL DESIRED PODS for FLUENTD DS :  " +desired_pods_Fluentd_Ds)

        ########	Validation  1: DaemonSet running in all nodes or not #############

        if int(total_nodes) != int(desired_pods_Fluentd_Ds):
            self._failed_msg = self._failed_msg + "\n"
            # print ("WRONG !! FluentD DaemonSet is not running in all Nodes !!")
            return False
        else:
            # print ("CORRECT !! FluentD DaemonSet is set for all NODES..")
            return True


class FluentdDaemonSetReplicasAllRunning(BTELValidationStatusRequirement):
    #### VALIDATION : 2
    #### Inherited from BASE CLASS
    #### Here we are checking Fluentd DaemonSet all Replicas are running or Not

    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "FluentdDaemonSetReplicasAllRunning"
        self._title = "Verify FluentdDaemonSet Replicas All Running"
        self._failed_msg = "Not all FluentdDaemonSet replicas are running"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        stream = self.get_output_from_run_cmd(
            "sudo /usr/local/bin/kubectl get daemonset btel-belk-fluentd-daemonset --namespace btel -o jsonpath=\'{.status.desiredNumberScheduled}\'")
        desired_pods_Fluentd_Ds = stream.strip()
        stream = self.get_output_from_run_cmd(
            "sudo /usr/local/bin/kubectl get daemonset btel-belk-fluentd-daemonset --namespace btel -o jsonpath=\'{.status.numberAvailable}\'")
        running_pods_Fluentd_Ds = stream.strip()
        if not running_pods_Fluentd_Ds:
            running_pods_Fluentd_Ds = 0
        if int(desired_pods_Fluentd_Ds) != int(running_pods_Fluentd_Ds):
            self._failed_msg += "\nExpected {} of FluentdDaemonSet replicas to be running, while actually {} FluentdDaemonSet replicas running".\
                format(desired_pods_Fluentd_Ds, running_pods_Fluentd_Ds)
            return False
        else:
            return True


class AlertManagerAndCPROClusterIPAccessableOrNot(BTELValidationStatusRequirement):
    #### Here we are checking BTEL-CPRO PROMETHEUS and BTEL-CPRO AlertManager RestApiServer Acessable or not.
    #### Here We will take in consideration that default service is ClusterIp. It may be or may not be exposed as INGRESS or NodePort

    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "AlertManagerAndCPROClusterIPAccessableOrNot"
        self._title = "Verify BTEL-CPRO PROMETHEUS and BTEL-CPRO AlertManager ClusterIP accessible or not"
        self._failed_msg = "BTEL-CPRO PROMETHEUS / BTEL-CPRO AlertManager ClusterIP not accessible"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        cpro_service = {'cpro-server-ext': {'service_name': 'BTEL-CPRO PROMETHEUS',
                                            'curl_find': '.*href.*Found.*'},
                        'cpro-alertmanager-ext': {'service_name': 'BTEL-CPRO AlertManager',
                                            'curl_find': '.*DOCTYPE html*'}}
        unaccessible_cpro_service = []
        for service in cpro_service:
            stream = self.get_output_from_run_cmd("sudo /usr/local/bin/kubectl get svc -n btel {} -o=jsonpath='{{.spec.clusterIP}}'".format(service))
            cluster_ip = stream.strip()
            #### Timeout used 2 seconds otherwise if no Connectivity it waits for a long time to give error message in CURL
            return_code, out, err = self.run_cmd("sudo curl --connect-timeout 2 {}".format(cluster_ip))
            if return_code != 0:
                unaccessible_cpro_service.append(cpro_service[service]['service_name'])
                continue
            curl_output = out.strip()
            ### If The ClusterIP is accessable CURL should return,
            ### <a href=\"/graph\">Found</a>.
            matched = re.search(r"{}".format(cpro_service[service]['curl_find']), curl_output)
            is_match = bool(matched)
            if is_match is False:
                unaccessible_cpro_service.append(cpro_service[service]['service_name'])
        if unaccessible_cpro_service:
            self._failed_msg = "The ClusterIP of services {} isn't accessible".format(unaccessible_cpro_service)
            return False
        return True

# TODO in the future -- add Helm3 option
class list_of_btel_components_installed(InformatorValidator):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._unique_operation_name = "list_of_btel_components_installed"
        self._title_of_info = "List of installed btel components"
        self._is_pure_info = True
        self._is_highlighted_info = True
        self._system_info = ""

    def is_validation_passed(self):
        charts = self.get_dict_from_command_output("sudo helm list --output json --deployed", 'json', timeout=10)
        btel_app = []
        try:
            for chart in charts["Releases"]:
                charts = chart["Chart"]
                if 'btel' in charts.lower():
                    btel_app.append(chart["Name"])
        except:
            self._system_info = "No charts are installed"
        if len(btel_app) > 0:
            ncs_version = sys_parameters.get_version()
            if ncs_version <= Version.V22:
                get_btel_status = 'sudo helm status btel | grep -i "Release Name"  -A 20'
            else:
                get_btel_status = 'sudo helm status btel -n btel | grep -i "Release Name"  -A 20'
            exit_code, btel_status, err = self.run_cmd(get_btel_status)
            if exit_code == 0:
                out = btel_status.replace('=', '')
                self._system_info = "The installed btel components are : \n {}".format(out)
            else:
                self._system_info = "BTEL is not installed on the cluster"
        else:
            self._system_info = "BTEL is not installed on the cluster"
        return True

class AreBtelPodsTerminatedWithOOMKILLED(BTELValidationStatusRequirement):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._unique_operation_name = "is_btel_pods_terminated_with_OOMKILLED"
        self._title = "is btel pods terminated with OOMKILLED (killed due to low memory)"
        self._failed_msg = " "
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.APPLICATION_DOMAIN]

    def is_validation_passed(self):
        status = True
        btel_dict = self.get_btel_app_namespace()
        for namespace in list(btel_dict.values()):
            pods_status = json.loads(self.get_all_containers_status(namespace='-n {}'.format(namespace)))
            for pod in pods_status:
                try:
                    for container in pod['containers_status']:
                        container_status = list(container['container_state'])
                        if 'running' not in container_status:
                            if 'OOMKilled' in container['container_state'][container_status[0]]['reason']:
                                status = False
                                self.add_to_validation_log("Pod '{}', container '{}': container status is '{}' - '{}'".format(pod['pod_name'],
                                                                                                                              container['container_name'],
                                                                                                                              container_status[0],
                                                                                                                              container['container_state'][container_status[0]]['reason']))
                except:
                    continue
        return status

class CheckWhetherKibanaIsAccesible(BTELValidationStatusRequirement):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._unique_operation_name = "Check_whether_kibana_is_accesible"
        self._title = "Check whether kibana is accesible"
        self._failed_msg = "kibana is not working as expected. please check the kibana service"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]


    def is_prerequisite_fulfilled(self):
        return self._is_app_installed('kibana')

    def is_validation_passed(self):
        btel_dict = self.namespace_app_exists_dict()
        btel_dict_len = len(btel_dict)
        count = 0
        for namespace in list(btel_dict.keys()):
            kibana = "sudo kubectl get service kibana -n {} -o=custom-columns=IP:.spec.clusterIP,PORT:.spec.ports[*].port --no-headers".format(
                namespace)
            exit,out, err = self.run_cmd(kibana)
            if exit == 0:
              out_split = out.split()
              kibana_out = 'curl --max-time 60 -s http://{}:{}/status  -o /dev/null'.format(out_split[0], out_split[1])
              kibana_output = kibana_out + " --write-out '%{http_code}'"
              exit,output,err = self.run_cmd(kibana_output)
              if '200' in output:
                count += 1

        if count == btel_dict_len:
            return True
        else:
            return False


class IsBtelPodsReadyAndRunningWithNoRestarts(BTELValidationStatusRequirement):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._unique_operation_name = "is_btel_pods_ready_and_running_with_no_restarts"
        self._title = "is btel pods ready and running with no restarts"
        self._failed_msg = " "
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.APPLICATION_DOMAIN]

    #note - defult btel prerequesit

    def is_validation_passed(self):
        problematic_pods = []
        btel_dict = self.get_btel_app_namespace()
        for pod_namespace in list(btel_dict.values()):
            out = self.get_all_pods(namespace='-n {}'.format(pod_namespace))
            for line in out.splitlines():
                pod_info = line.split()
                pod_name = pod_info[0]
                pod_ready = pod_info[1].split("/")
                pod_status = pod_info[2]
                pod_restarts = pod_info[3]
                if not ((pod_status == 'Completed') or (pod_status == 'Running' and pod_ready[0] == pod_ready[1])):
                    problematic_pods.append(pod_name)
                if int(pod_restarts) > 1:
                    pod_age = pod_info[4]
                    if 's' == pod_age[-1] or 'm' == pod_age[-1]:
                        problematic_pods.append(pod_name)

        if problematic_pods:
            list_problematic_pods = "\n".join(problematic_pods)
            self._failed_msg = "These are the pods that were not running or not ready or running with restarts.\n {}".format(
                list_problematic_pods)
            return False
        else:
            return True


class CheckWhetherElasticsearchIsWorkingAsExpected(BTELValidationStatusRequirement):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._unique_operation_name = "Check_whether_elasticsearch_is_working_as_expected"
        self._title = "Check whether elasticsearch is working as expected"
        self._failed_msg = "btel elaticsearch is not in good state. Please check the elasticsearch service"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_prerequisite_fulfilled(self):
        return self._is_app_installed('elasticsearch')

    def is_validation_passed(self):
        btel_dict = self.namespace_app_exists_dict()
        btel_dict_len = len(btel_dict)
        count = 0
        for namespace in list(btel_dict.keys()):
            elastic = "sudo kubectl get svc elasticsearch -n {}  -o=custom-columns=clusterIP:.spec.clusterIP,PORT:.spec.ports[*].port  --no-headers".format(
                namespace)
            exit,out,err = self.run_cmd(elastic)
            if exit == 0:
              out_split = out.split()
              elastic_status = "curl --max-time 60 -s http://{}:{}/_cluster/health?pretty | grep -i status".format(out_split[0],
                                                                                                   out_split[1])
              exit, output, err = self.run_cmd(elastic_status)
              if exit == 0:
                output_split = output.split(':')
                if 'green' in output_split[1]:
                  count += 1

        if count == btel_dict_len:
            return True
        else:
            return False


class CheckWhetherGrafanaIsAccesible(BTELValidationStatusRequirement):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._unique_operation_name = "Check_whether_grafana_is_accesible"
        self._title = "Check whether grafana is accesible"
        self._failed_msg = "Grafana page is not accesible. please check grafana service"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_prerequisite_fulfilled(self):
        return self._is_app_installed('grafana')

    def is_validation_passed(self):
        btel_dict = self.namespace_app_exists_dict()
        btel_dict_len = len(btel_dict)
        count = 0
        for namespace in list(btel_dict.keys()):
            cmd = "sudo kubectl get service grafana -n {} -o=custom-columns=IP:.spec.clusterIP,PORT:.spec.ports[*].port --no-headers".format(
                namespace)
            exit,out,err = self.run_cmd(cmd)
            if exit == 0:
              output_split = out.split()
              grafana_out = "curl --max-time 60 -k https://{}:{}/grafana".format(output_split[0], output_split[1])
              exit, grafana_output, err = self.run_cmd(grafana_out)
              if exit == 0:
                if '/grafana/login' in grafana_output:
                  count += 1

        if count == btel_dict_len:
            return True
        else:
            return False
class CheckWhetherBelkCuratorIsWorkingAsExpected(BTELValidationStatusRequirement):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._unique_operation_name = "Check_whether_belk_curator_is_working_as_expected"
        self._title = "Check whether belk curator is working as expected"
        self._failed_msg = "Please check the belk curator job"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_prerequisite_fulfilled(self):
        return self._is_app_installed('curator')

    def is_validation_passed(self):
        btel_dict = self.namespace_app_exists_dict()
        btel_dict_len = len(btel_dict)
        count = 0
        for namespace in list(btel_dict.keys()):
            cmd = "sudo kubectl get pods -n {} | grep -i curator | tail -n1".format(namespace)
            out = self.get_output_from_run_cmd(cmd) #note it will come to this block of code
                                                    #only if the curator is installed as part of btel
            out_strip = out.strip()
            out_split = out_strip.split()
            if 'Completed' in out_split:
                count += 1

        if count == btel_dict_len:
            return True
        else:
            return False


class CheckNodeLabels(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "check_node_labels"
        self._title = "Verify unmatched labels on nodes for Prometheus"
        self._failed_msg = "Prometheus unable to distingush the labels on nodes "
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]

    def is_validation_passed(self):
        cmd = "sudo kubectl get node -o json | jq -r '[.items[] | {name:.metadata.name,labels:.metadata.labels}]'"
        get_nodes_labels = self.get_output_from_run_cmd(cmd)
        nodes_labels_in_json = json.loads(get_nodes_labels)   #convert to json
        conflict_labels = dict()
        found_unmatch_label = False
        for node in nodes_labels_in_json:
            node_name = node['name']     #get node name
            labels = list(node['labels'].keys())   #get labels related to the node
            filter_node_labels = [label for label in labels if (('-' in label or '_' in label) and ('kubernetes' not in label and 'ncs.nokia.com' not in label))]     #exclude kubernetes and ncs.nokia.com labels
            conflict_labels[node_name] = []
            for label in filter_node_labels:
                if not re.match(r'[a-zA-Z_:][a-zA-Z0-9_:]*$', label): #compare each label with REGEX  pattern. Example of matched pattern: is_worker
                    # exmaple of unmatched regax patter: is-worker
                    conflict_labels[node_name].append(label)
        message=''
        for key in list(conflict_labels.keys()):
            if len(conflict_labels[key]) > 0:
                message = message +key+" {} ".format(conflict_labels[key]) + "\n"
                found_unmatch_label=True
        if not found_unmatch_label:
            return True
        else:
            self._failed_msg = self._failed_msg + message
            return False


####### SOUVIK DAS CODE STARTS #########
####### ICET-1445 | cpro-kube-state-metrics and Host TimeZone Difference check  ########

class CproKubeStateMetricsTimeZoneValidation(BTELValidationStatusRequirement):
    objective_hosts = {
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "Cpro_Kube_State_Metrics_TimeZone_Validation"
        self._title = "Cpro-Kube-State-Metrics TimeZone Validation"
        self._failed_msg = "TimeZone Validation Failure in cpro-kube-state-metrics pod"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        out = self.get_btel_installed_status()
        if out == "DEPLOYED":
            cmd = "sudo /usr/local/bin/kubectl get pods -n btel --no-headers=true | grep 'cpro-kube-state-metrics'"
            stream = self.get_output_from_run_cmd(cmd)
            array = stream.split()
            pod_name = array[0]
            container_running_status = array [1]
            pod_running_status  = array[2]
            if container_running_status == '1/1' and pod_running_status == "Running":
                cmd = "sudo /usr/local/bin/kubectl exec -it {} -n btel -- /usr/bin/date".format(pod_name)
                stream = self.get_output_from_run_cmd(cmd).strip()
                timezone_in_pod = PythonUtils.get_timezone_from_date(stream)
                stream = self.get_output_from_run_cmd("sudo /bin/date").strip()
                timezone_in_host = PythonUtils.get_timezone_from_date(stream)

                if timezone_in_pod == timezone_in_host:
                    return True
                else:
                    self._failed_msg = self._failed_msg + " | Pod TimeZone: "+timezone_in_pod + " | Host TimeZone: "+timezone_in_host
                    return False
            else:
                err = "Pod cpro-kube-state-metrics-xxxxx not Running"
                raise UnExpectedSystemOutput(ip=self._host_executor.ip, cmd=cmd, output=stream + err)


class CheckPrometheusStorageUsage(Validator):
    objective_hosts = [Objectives.ONE_MASTER]

    MAX_PROMETHEUS_STORAGE_USAGE_PERCENT = 80

    def set_document(self):
        self._unique_operation_name = "check_prometheus_storage_usage"
        self._title =  "Check prometheus storage usage isn't over {}%".format(CheckPrometheusStorageUsage.MAX_PROMETHEUS_STORAGE_USAGE_PERCENT)
        self._failed_msg = (
            "The following Prometheus operator pods (namespace: ncms) have exceeded "
            "{}% storage usage, mainly due to high WAL partition size. A cleanup may be required:\n".format(
                CheckPrometheusStorageUsage.MAX_PROMETHEUS_STORAGE_USAGE_PERCENT
            )
        )
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.RISK_RESOURCE_CLEANING_RECOMMENDED]
        self._blocking_tags = [BlockingTag.UPGRADE]

    def is_validation_passed(self):
        get_pods_cmd = "sudo kubectl get pods -n ncms | grep prometheus-operator"
        get_pods_out = self.get_output_from_run_cmd(get_pods_cmd)
        pod_name_list= [line.split()[0] for line in get_pods_out.splitlines()]

        is_passed = True
        for pod_name in pod_name_list:
            prometheus_volume_cmd = 'sudo kubectl exec -n ncms -c prometheus {} -- df -kh | grep " /prometheus$"'.format(pod_name)
            prometheus_volume_out = self.get_output_from_run_cmd(prometheus_volume_cmd)
            values = prometheus_volume_out.strip().split()
            if len(values) != 6:
                raise UnExpectedSystemOutput(self.get_host_ip(), cmd=prometheus_volume_cmd, output=prometheus_volume_out, message="failed to parse the output into exactly 6 values")
            usage_percentage_str = values[4]
            try:
                usage_percentage = int(usage_percentage_str.strip('%'))
            except ValueError:
                raise UnExpectedSystemOutput(self.get_host_ip(), cmd=prometheus_volume_cmd, output=prometheus_volume_out, message="failed to parse percentage {} into integer ".format(usage_percentage_str))
            if usage_percentage > CheckPrometheusStorageUsage.MAX_PROMETHEUS_STORAGE_USAGE_PERCENT:
                self._failed_msg+="pod name {}  usage {}%\n".format(pod_name, usage_percentage)
                is_passed = False
        return is_passed
