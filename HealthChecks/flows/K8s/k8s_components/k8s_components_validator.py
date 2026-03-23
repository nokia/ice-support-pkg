from __future__ import absolute_import
from tools import adapter
from HealthCheckCommon.operations import *

from HealthCheckCommon.validator import Validator
from tools.ExecutionModule.execution_helper import ExecutionHelper
import tools.sys_parameters as globals
from tools.global_enums import *
import tools.paths as paths
from tools.global_enums import Version, SubVersion
import re
from tools.Conversion import Conversion
from datetime import datetime
from tools.python_versioning_alignment import decode_base_64


# ----------------------------------------------------------------------------------------------------------------------


class DaemonsetsValidator(Validator):
    """
    those set of class is used to make sure all the k8s component is configured, up and running
    """
    objective_hosts = [Objectives.ONE_MASTER]

    def get_daemonsets_names(self):
        cmd = "sudo kubectl get  daemonsets --all-namespaces   -o jsonpath='{.items[*].metadata.name}'"
        daemonsets_list = self.get_output_from_run_cmd(cmd)
        return daemonsets_list.split()


# ----------------------------------------------------------------------------------------------------------------------
class ValidateHasAllBasicDaemonsets(DaemonsetsValidator):
    def set_document(self):
        self._title = "Validate all the expected daemonsets are available"
        self._failed_msg = "not all the expected daemonsets are available"
        self._severity = Severity.ERROR
        self._unique_operation_name = "all_basic_daemonset_available"

        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        """return true if and only if the validation """
        # get the daemonsets name of the
        ncs_version = globals.get_version()
        if ncs_version < Version.V22:
            version = '20'
        else:
            version = ncs_version
        list_of_expected_daemonset = (ExecutionHelper.get_local_operator(True)).get_dict_from_file(
            paths.EXPECTED_DEAMONSET_FILE).get(version)
        daemonsets_list = self.get_daemonsets_names()
        missing_daemonsets = PythonUtils.words_in_A_missing_from_B(list_of_expected_daemonset.split(),
                                                                   daemonsets_list)
        if len(missing_daemonsets) > 0:
            self._details = "missing the following daemonsets :" + str(missing_daemonsets)
            return False
        return True


class ValidateAllDaemonsetsScheduled(DaemonsetsValidator):

    def set_document(self):
        self._title = "Validate all the expected daemonsets is in k8s"
        self._cmd_name = "daemonsets_in_k8s"
        self._severity = Severity.ERROR
        self._unique_operation_name = "all_basic_daemonset_scheduled"
        self._failed_msg = "ERROR!!!!\n"
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def get_nodes_count_selector_or_affinity(self, node_selector_dict, node_affinity_selector_list):
        is_error = False
        ## NODE SELECTOR PRESENT so node_selector_dict != {} and NODE AFFINITY NOT PRESENT so node_affinity_selector_list = []
        if node_selector_dict and not node_affinity_selector_list:
            label_string = ",".join("{label_key}={label_value}".format(label_key=key, label_value=value) for key, value in node_selector_dict.items())
            cmd = "sudo kubectl get nodes -l " + str(label_string) + " --no-headers| wc -l"
            return_code, node_list_count , err = self.run_cmd(cmd)
            if return_code != 0:
                is_error = True

        ## AFFINITY NODE SELECTOR PRESENT so matchExpressions Dict exists and NODE SELECTOR NOT PRESENT so node_selector_dict = {}
        elif not node_selector_dict and node_affinity_selector_list :
            node_list_count = 0
            node_array_set = set()
            # node_array_set is a SET to keep all Unique nodes names retreived from LABEL Selectors in Affinity seletor.

            for node_expression_dict in node_affinity_selector_list:
                selector_array = node_expression_dict.get('matchExpressions', [])
                for selector in selector_array:
                    if 'key' in selector and 'values' in selector:
                        selector_key = selector['key']
                        selector_value = selector['values'][0]
                        cmd = "sudo kubectl get nodes -l " + str(selector_key) + "=" + str(selector_value) + " -o NAME"
                        return_code, out , err = self.run_cmd(cmd)
                        if return_code != 0:
                            is_error = True
                        node_array = out.splitlines()
                        for node_name in node_array:
                            node_array_set.add(node_name)

            node_list_count =len(node_array_set)

        ## NODE SELECTOR NOT PRESENT so node_selector_dict = {} and NODE AFFINITY also NOT PRESENT so node_affinity_selector_list = [] too
        elif not node_selector_dict and not node_affinity_selector_list:
            return_code, node_list_count , err = self.run_cmd("sudo kubectl get nodes --no-headers| wc -l")
            if return_code != 0:
                is_error = True

        ## If for any reason k8s command fails to run then Something has to return , that is 0 value as node_list_count
        if is_error:
            self._failed_msg += "\nKubectl command failed to RUN : {} | Error :   {}".format (cmd, str(err))
            return 0
        
        return int(node_list_count)

        ########    LOGIC ENDS  #####################

    def is_validation_passed(self):
        problematic_daemonsets = []
        ## In 25.7/11 Version Because of no toleration on ISTIO-JAEGER Daemonsets the logic fails to get the desired number of pods so need to exclude ISTIO JAEGER daemonset in NCS 24.11 
        if globals.get_version() < Version.V24_11:
            cmd = "sudo kubectl get daemonsets -A -o jsonpath='{range .items[*]}{.metadata.name}{\"|\"}{.spec.template.spec.nodeSelector}{\"|\"}{.spec.template.spec.affinity.nodeAffinity}{\"|\"}{.status}{\"\\n\"}{end}'"
        else:
            cmd = "sudo kubectl get daemonsets -A -o jsonpath='{range .items[*]}{.metadata.name}{\"|\"}{.spec.template.spec.nodeSelector}{\"|\"}{.spec.template.spec.affinity.nodeAffinity}{\"|\"}{.status}{\"\\n\"}{end}' | grep -v 'cist-jaeger-jaeger'"

        """
        output format:

        WHEN NODE SELECTOR THERE 

        bcmt-api|{"is_control":"true"}||{"currentNumberScheduled":3,"desiredNumberScheduled":3,"numberAvailable":3,"numberMisscheduled":0,"numberReady":3,"observedGeneration":1,"updatedNumberScheduled":3}

        WHEN AFFINITY SELECTOR THERE

        node-feature-discovery-topology-updater||{"requiredDuringSchedulingIgnoredDuringExecution":{"nodeSelectorTerms":[{"matchExpressions":[{"key":"is_edge","operator":"In","values":["true"]}]},{"matchExpressions":[{"key":"is_worker","operator":"In","values":["true"]}]}]}}|{"currentNumberScheduled":2,"desiredNumberScheduled":2,"numberAvailable":2,"numberMisscheduled":0,"numberReady":2,"observedGeneration":1,"updatedNumberScheduled":2}

        WHEN NO NODE SELECTOR or AFFINITY SELECTOR There

        daemonset-test-pod|||{"currentNumberScheduled":4,"desiredNumberScheduled":4,"numberAvailable":4,"numberMisscheduled":1,"numberReady":4,"observedGeneration":1,"updatedNumberScheduled":4}
        """

        out = self.get_output_from_run_cmd(cmd)
        out_lines = out.splitlines()
        node_list_count = 0
        base_failed_message = "\nDaemonset: {} has replicas  :   {} but Desired Replicas are :   {}\n"
        for line in out_lines:
            if not line:
                continue
            node_selector_dict = {}
            node_affinity_dict = {}
            name, node_selector_dict_str, node_affinity_dict_str, status_dict_str = line.split('|')

            status_dict = json.loads(status_dict_str)
            desired_num = int(status_dict.get('desiredNumberScheduled', 0))
            available_num = int(status_dict.get('numberAvailable', 0))

            if (desired_num != available_num):
                problematic_daemonsets.append(name)
                self._failed_msg += base_failed_message.format(name, available_num,desired_num)

            if node_selector_dict_str:
                node_selector_dict = json.loads(node_selector_dict_str)
            if node_affinity_dict_str:
                node_affinity_dict = json.loads(node_affinity_dict_str)

            ### When NODE SELECTOR NOT there but Node Affinity there
            ### OR
            ### When NODE SELECTOR there and ALSO Node Affinity there, Both are present
            if node_affinity_dict:
                affinity_node_count = 0
                node_expressions_list = []
                affinity_types_k8s_list = ['preferredDuringSchedulingIgnoredDuringExecution',
                                           'requiredDuringSchedulingIgnoredDuringExecution']
                for affinity_type in affinity_types_k8s_list:
                    affinity_selector_list = (
                        node_affinity_dict.get(affinity_type, {}).get('nodeSelectorTerms', []))
                    if affinity_selector_list:
                        node_expressions_list.extend(affinity_selector_list)
                count = self.get_nodes_count_selector_or_affinity(None, node_expressions_list)
                affinity_node_count = count
                if (available_num != affinity_node_count):
                    problematic_daemonsets.append(name)
                    self._failed_msg += base_failed_message.format(name, available_num, affinity_node_count)
            ### When NODE SELECTOR there but Node Affinity not there
            elif node_selector_dict:
                node_list_count = self.get_nodes_count_selector_or_affinity (node_selector_dict, None)

                if (available_num != node_list_count):
                    problematic_daemonsets.append(name)
                    self._failed_msg += base_failed_message.format(name, available_num, node_list_count)
            ### When NODE SELECTOR NOT there and Node Affinity also NOT there
            else:
                node_list_count = self.get_nodes_count_selector_or_affinity (None, None)
                if (available_num != node_list_count):
                    problematic_daemonsets.append(name)
                    self._failed_msg += base_failed_message.format(name, available_num, node_list_count)

        if problematic_daemonsets:
            return False
        return True


######### ETCD DEFRAMENTATION SOUVIK CODE STARTS #################

#######     VALIDATION : 1 in CONTROLLER NODES  #####

class EtcdDefragmentationCheckInController(Validator):
    """
    Purpose:    To verify ETCD Defragmentation enabled in CONTROLLER NDOES or not
            If Enabled, then what is the configuration of ETCD_DEFRAGMENTAION

    Date:   07th OCT, 2021
    Author: SOUVIK DAS souvik.das@nokia.com
    """

    #### Runs only on K8s Controller/Master Nodes
    objective_hosts = [Objectives.MASTERS]

    def set_document(self):
        self._title = "Validate Etcd Defragmentation in Controller"
        self._failed_msg = "ETCD Defragmentaion function WRONG in Controller!!!"
        self._severity = Severity.ERROR
        self._unique_operation_name = "EtcdDefragmentationCheckInController"

        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_prerequisite_fulfilled(self):
        if globals.get_version() is Version.V20_FP2 and globals.get_hotfix_list():
            for item in globals.get_hotfix_list():
                sub_version = Conversion.convert_version_to_dict(hot_fix_version=item)
                if "SU" in sub_version.get("PP_SU") or sub_version.get("MP_SP") != SubVersion.NO_MP or \
                        (sub_version.get("PP_SU") != SubVersion.NO_PP and int(sub_version.get("PP_SU").split(
                            'PP')[1]) >= 9):
                    return False
        return True

    def is_validation_passed(self):
        # print ("EtcdDefragmentationCheckInController Validation begins ....  ")

        ## Step 1: Check bcmt_heartbeat.sh file and check whether function "etcd_defrag" is enabled or not

        ### Here "etcd_defrag &" should be present in the shell script

        stream = self.get_output_from_run_cmd("sudo less /opt/bcmt/bin/bcmt_heartbeat.sh | grep -i 'etcd_defrag &'")
        etcd_defrag_function = stream.strip()
        # print("etcd_defrag_function: " +etcd_defrag_function)

        ## Idea is: In controller node "etcd_defrag" should NOT be commented. It should remeain Enabled
        ## Check the function is commented out or Not
        ## We will check "#", as "#"" is used to comment out
        ## "#" there means "is_match1" = TRUE , Function is Disabled. Which is WRONG

        matched1 = re.search(r"(#)+.*", etcd_defrag_function)
        is_match1 = bool(matched1)
        # print("etcd_defrag_function COMMENTED:")
        # print(is_match1)

        ## Step 2: Check bcmt_heartbeat.sh file and check codeBlock inside function "etcd_defrag"
        ##      Wether "etcdctl defrag" command "--cluster" is enabled or not
        ## if "--cluster", then "is_match2" = TRUE, which should be WRONG

        stream = self.get_output_from_run_cmd(
            "sudo less /opt/bcmt/bin/bcmt_heartbeat.sh | grep -i 'etcdctl defrag in every 10 hours' -A10 | grep -i 'etcdctl defrag' | tail -1")
        etcd_defrag_cluster_enabled = stream.strip()
        # print("etcd_defrag_cluster_enabled: " +etcd_defrag_cluster_enabled)

        matched2 = re.search(r".*cluster.*", etcd_defrag_cluster_enabled)
        is_match2 = bool(matched2)
        # print("ETCDCTL function --cluster THERE")
        # print(is_match2)

        if (is_match1 or is_match2):
            # print("WRONG !!! ETCD Fucntion in Controller")
            return False
        else:
            # print("CORRECT Configuration in ETCD..... ")
            return True


#######     VALIDATION : 2 in WORKER and EDGE  NODES  #####

class EtcdDefragmentationCheckInWorkersEdges(Validator):
    """
    Purpose:    To verify ETCD Defragmentation enabled in WORKER and ESGE NDOES or not
            In WORKER or EDGES The fuction should be Disbaled

    Date:   07th OCT, 2021
    Author: SOUVIK DAS souvik.das@nokia.com
    """

    #### Runs only on K8s Worker and Edge Nodes
    objective_hosts = [Objectives.WORKERS, Objectives.EDGES]

    def set_document(self):
        self._title = "Validate Etcd Defragmentation in Worker/Edge"
        self._failed_msg = "ETCD Defragmentaion function in WORKER/EDGE WRONG !!!"
        self._severity = Severity.ERROR
        self._unique_operation_name = "EtcdDefragmentationCheckInWorkersEdges"

        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):

        # print ("EtcdDefragmentationCheckInWorkersEdges Validation begins ....  ")

        ## Step 1: Check bcmt_heartbeat.sh file and check whether function "etcd_defrag" is disabled or not

        cmd = "sudo less /opt/bcmt/bin/bcmt_heartbeat.sh | grep -i 'etcd_defrag &'"
        return_code, stream, err = self.run_cmd(cmd)
        if not stream:
            return True
        if return_code != 0:
            self._set_cmd_info(cmd, 20, return_code, stream, err)
            raise UnExpectedSystemOutput(ip=self._host_executor.ip, cmd=cmd, output=stream + err)
        etcd_defrag_function = stream.strip()
        # print("etcd_defrag_function: " +etcd_defrag_function)

        ## Idea is: In Worker and Edge nodes "etcd_defrag" Should be Commented. It should remeain Disabled

        ## Check the function is commented out or stil enabled
        ## We will check "#" as # is used to comment out
        ## "#" there means "is_match1" = TRUE , which s hould be TRUE only

        matched1 = re.search(r"(#)+.*", etcd_defrag_function)
        is_match1 = bool(matched1)
        # print("etcd_defrag_function COMMENTED:")
        # print(is_match1)

        if (is_match1):
            # print("CORRECT Configuration in ETCD in Workers/Edges")
            return True
        else:
            # print("WRONG !!! ETCD Fucntion enabled in Workers/Edges")
            return False


######### ETCD DEFRAMENTATION SOUVIK CODE ENDS #################

class EtcdDefragCronjobValidation(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "etcd_defrag_cronjob_validation"
        self._title = "Etcd Defrag cronjob validation"
        self._failed_msg = "Etcd Defrag cronjob is ineffective\n"
        self._severity = Severity.CRITICAL
        self.details = ""
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]
        self._blocking_tags = [BlockingTag.UPGRADE]

    def is_validation_passed(self):
        cmd = "sudo kubectl get cronjobs -n ncms -o custom-columns=NAME:.metadata.name |grep -i 'etcd-defrag'"
        # Validate that sleep and defrag commands are in same line.
        defrag_cronjob_list = self.get_output_from_run_cmd(cmd).split()
        failure_list = []
        for defrag_cronjob in defrag_cronjob_list:
            cmd = "sudo kubectl describe cronjobs {defrag_cronjob} -nncms |grep -i 'sleep'".format(
                defrag_cronjob=defrag_cronjob)
            return_code, out, err = self.run_cmd(cmd)
            if out == '':
                self._failed_msg += "sleep and defrag is expected in the command output ,but output is empty"
                return False
            failure_list.append(defrag_cronjob) if 'defrag' not in out else None
        if len(failure_list) > 0:
            self._failed_msg += "Below etcd defrag cronjob are ineffective in ncms namespace:\n{}".format(
                '\n'.join(failure_list))
            return False
        return True


######### MARIADB Validation SOUVIK CODE STARTS #################

class MariadbBaseValidator(Validator):
    def get_mariadb_admin_pod(self):
        cmd = "sudo /usr/local/bin/kubectl get pods -n ncms --no-headers | grep -i 'cmdb-admin' | grep Running"
        stream = self.get_output_from_run_cmd(cmd, message="No running maria db admin pod")

        output = stream.split()

        if len(output) < 2:
            raise UnExpectedSystemOutput(self.get_host_ip(), cmd, stream, "Expected to have at least 2 columns "
                                                                          "in cmd out.")
        mariadb_admin_pod = output[0].strip()
        mariadb_admin_pod_running_status = output[1].strip()

        if mariadb_admin_pod_running_status == "1/1":
            return mariadb_admin_pod
        else:
            raise UnExpectedSystemOutput(ip=self._host_executor.ip, cmd=cmd, output=stream,
                                         message="Expected to have 1/1 in second column")

    def get_mariadb_Pods_Dict(self):
        out = self.get_output_from_run_cmd(
            "sudo /usr/local/bin/kubectl get pods -n ncms --no-headers | grep -i 'mariadb'").strip()
        mariadb_all_pods_list = []
        mariadb_running_pods_list = []
        mariadb_failed_pods_list = []

        for line in out.splitlines():
            mariadb_pod = line.split()[0]
            running_status = line.split()[1]

            mariadb_all_pods_list.append(mariadb_pod)

            if running_status == "1/1":
                mariadb_running_pods_list.append(mariadb_pod)

            if running_status != "1/1":
                mariadb_failed_pods_list.append(mariadb_pod)

        mariadbpods = {}
        mariadbpods["ALL"] = mariadb_all_pods_list
        mariadbpods["RUNNING"] = mariadb_running_pods_list
        mariadbpods["FAILED"] = mariadb_failed_pods_list
        return mariadbpods

    def get_mariadb_Pods(self, status):
        MariadbBaseValidator.mariadb_pods_dict = {}
        if len(MariadbBaseValidator.mariadb_pods_dict) == 0:
            MariadbBaseValidator.mariadb_pods_dict = self.get_mariadb_Pods_Dict()
        return MariadbBaseValidator.mariadb_pods_dict[status]

    def get_mariadb_ncs22_secret(self):
        self._is_clean_cmd_info = True
        out = self.get_output_from_run_cmd(
            "sudo /usr/local/bin/kubectl get secret -n ncms bcmt-cmdb-admin-secrets -o jsonpath='{.data.admin}'").strip()
        secret_decoded = decode_base_64(out)
        mariadb_user = secret_decoded.split(":")[0]
        mariadb_password = secret_decoded.split(":")[1]
        return mariadb_user, mariadb_password


class CheckMaridbRunningPodCount(MariadbBaseValidator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "check_maridb_running_pod_count"
        self._title = "Check maridb running pod count"
        self._failed_msg = "ERROR!! Mariadb failed Pods are: "
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.SYMPTOM]

    def is_validation_passed(self):
        mariadb_Pods = self.get_mariadb_Pods("RUNNING")
        if (len(mariadb_Pods)) < 3:
            mariadb_failed_Pods = self.get_mariadb_Pods("FAILED")
            for line in mariadb_failed_Pods:
                self._failed_msg += "\n{}".format(line)
            return False
        else:
            return True


class CheckMariaDbAdminPodLogs(MariadbBaseValidator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "check_maridb_admin_pod_logs"
        self._title = "Check maridb admin pod logs"
        self._failed_msg = "ERROR!! ADMIN POD Has Error LOGS UNPAUSE"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.SYMPTOM]

    def is_validation_passed(self):
        mariadb_admin_pod = self.get_mariadb_admin_pod()
        cmd = "sudo kubectl logs -n ncms {} | grep -i 'Auto-Heal Paused' | wc -l".format(mariadb_admin_pod)
        count_paused = self.get_int_output_from_run_cmd(cmd)

        if count_paused > 0:
            cmd = "sudo kubectl logs -n ncms {} | grep -i 'Auto-Heal Enabled' | wc -l".format(mariadb_admin_pod)
            count_enabled = self.get_int_output_from_run_cmd(cmd)

            if count_enabled > 0:  # TODO: is it ok that count_enabled < count_paused
                return True
            else:
                return False
        else:
            return True


class CheckMaridbMysqldbStatus(MariadbBaseValidator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "check_maridb_mysqldb_status"
        self._title = "Check maridb mysqldb status"
        self._failed_msg = "ERROR in Mariadb DB"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.SYMPTOM]

    def is_validation_passed(self):
        mariadb_Pods = self.get_mariadb_Pods("RUNNING")
        flag = 0
        if len(mariadb_Pods) > 0:
            for pod in mariadb_Pods:
                if globals.get_version() >= Version.V25_11:
                    cmd = ("sudo kubectl exec -n ncms -i {} -- bash -c 'mariadb --defaults-extra-file=<(echo -e \"[client]\npassword=$(cat $MARIADB_ROOT_PASSWORD_FILE)\") -B "
                           "-uroot -e \"SHOW GLOBAL STATUS LIKE '\\''wsrep%'\\''\"'").format(pod)
                elif globals.get_version() >= Version.V24_7:
                    cmd = ("sudo kubectl exec -n ncms -i {} -- bash -c 'MYSQL_PWD=\"$MARIADB_ROOT_PASSWORD\" /opt/bitnami/mariadb/bin/mariadb -B "
                        "-uroot -e \"SHOW GLOBAL STATUS LIKE '\\''wsrep%'\\''\"'").format(pod)
                else:
                    cmd = "sudo kubectl exec -n ncms -i {} -- mariadb_passwd --user root --get".format(pod)
                    mysql_password = self.get_output_from_run_cmd(cmd).strip()
                    cmd = "sudo kubectl exec -n ncms -i {} -- mysql -uroot -p{} -e \"show wsrep_status\"".format(pod,
                                                                                                                 mysql_password)
                mysql_wsrep_status = self.get_output_from_run_cmd(cmd).strip()

                mysql_status_dict = self._get_mysql_wsrep_status_dict(mysql_wsrep_status, cmd)

                if mysql_status_dict["Cluster_Status"].lower() == "primary" and \
                        mysql_status_dict["Node_Status"].lower() == "synced":
                    flag = 0
                else:
                    flag = flag + 1
                    self._failed_msg = self._failed_msg + " | " + pod + " | " + mysql_status_dict["Node_Status"] + \
                                       " | " + mysql_status_dict["Cluster_Status"]

        else:
            return False
        if (flag == 0):
            return True
        else:
            return False

    def _get_mysql_wsrep_status_dict(self, mysql_wsrep_status, cmd):
        if globals.get_version() >= Version.V24_7:
            res = {}
            mapping = {'Node_Index': 'wsrep_local_index',
                       'Node_Status': 'wsrep_local_state_comment',
                       'Cluster_Status': 'wsrep_cluster_status',
                       'Cluster_Size': 'wsrep_cluster_size'}
            for key, value in list(mapping.items()):
                pattern = r'\b{}\b\s+([\w]+)'.format(value)
                match = re.search(pattern, mysql_wsrep_status)
                if match:
                    res[key] = match.group(1)
                else:
                    raise UnExpectedSystemOutput(ip=self._host_executor.ip, cmd=cmd,
                                                 output="Failed to fetch {} out of command output".format(value))
            return res
        else:
            if "|" in mysql_wsrep_status:
                delimiter = "|"
                header_line = 0 if mysql_wsrep_status.startswith("+") else 1
            else:
                delimiter = "\t"
                header_line = 0

            res = PythonUtils.get_dict_from_string(mysql_wsrep_status, 'linux_table', header_line,
                                                   custom_delimiter=delimiter, custom_header=["Node_Index",
                                                                                              "Node_Status",
                                                                                              "Cluster_Status",
                                                                                              "Cluster_Size"])

            if len(res) != 1:
                raise UnExpectedSystemOutput(ip=self._host_executor.ip, cmd=cmd,
                                             output=mysql_wsrep_status + " | " + "Array out of index on output -> "
                                                                                 "show wsrep_status")

            return res[0]


class CheckMaridbAdminDbConnection(MariadbBaseValidator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "check_maridb_admin_db_connection"
        self._title = "Check maridb admin db connection"
        self._failed_msg = "MariaDb Admin DB Connection Error !!"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.SYMPTOM]

    def is_validation_passed(self):

        NCS_version_MAJOR = globals.get_version()
        mariadb_all_pods = self.get_mariadb_Pods("ALL")
        flag = 0
        if len(mariadb_all_pods) > 0:
            for pod in mariadb_all_pods:
                cmd = "sudo kubectl exec -i {} -n ncms -- cat /etc/mariadb/admin.env | grep 'ADMIN_DB_HOST'" \
                    .format(pod)
                host = self.get_output_from_run_cmd(cmd).splitlines()[0]
                ADMIN_DB_HOST = host.split("=")[1]
                cmd = "sudo kubectl exec -i {} -n ncms -- cat /etc/mariadb/admin.env | grep 'ADMIN_DB_PORT'" \
                    .format(pod)
                port = self.get_output_from_run_cmd(cmd).splitlines()[0]
                ADMIN_DB_PORT = port.split("=")[1]

                if NCS_version_MAJOR < Version.V22:
                    cmd = "sudo kubectl exec -i {} -n ncms -- cat /etc/mariadb/admin.env | grep 'ADMIN_DB_AUTH'" \
                        .format(pod)
                    auth = self.get_output_from_run_cmd(cmd).splitlines()[0]
                    ADMIN_DB_AUTH = auth.split("=")[1]
                    cmd = "sudo kubectl exec -i {} -n ncms -- redis-cli -h {} -p {} -a '{}' PING" \
                        .format(pod, ADMIN_DB_HOST, ADMIN_DB_PORT, ADMIN_DB_AUTH)
                else:
                    MARIADB_USER, MARIADB_PASSWORD = self.get_mariadb_ncs22_secret()
                    cmd = "sudo kubectl exec -i {} -n ncms -- redis-cli -h {} -p {} -a '{}' --user '{}' PING" \
                        .format(pod, ADMIN_DB_HOST, ADMIN_DB_PORT, MARIADB_PASSWORD, MARIADB_USER)

                return_code, db_connection, err = self.run_cmd(cmd)
                if return_code != 0:
                    return False

                if "PONG" not in db_connection.strip():
                    flag += 1
                    self._failed_msg = self._failed_msg + " | " + pod
        else:
            return False

        return flag == 0


class CheckLoginConfFileMaridb(MariadbBaseValidator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "check_login_conf_file_maridb"
        self._title = "Check login conf file maridb"
        self._failed_msg = "MariaDb login.conf file does not exists in : "
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.SYMPTOM]

    def is_validation_passed(self):
        mariadb_all_Pods = self.get_mariadb_Pods("ALL")

        status = True
        if len(mariadb_all_Pods) > 0:
            for pod in mariadb_all_Pods:
                cmd = "sudo kubectl exec -it {} -n ncms -- ls -lrtha /mariadb/data/ | grep -i '.login.cnf' | wc -l".format(pod)
                file_exists = self.get_output_from_run_cmd(cmd).strip()

                if int(file_exists) == 0:
                    status = False
                    self._failed_msg = self._failed_msg + pod + " | "
        else:
            self._failed_msg = "Failed to find MariaDb pods"
            return False
        return status


class CheckKeystoreFileMaridb(MariadbBaseValidator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "check_keystore_file_maridb"
        self._title = "Check keystore file maridb"
        self._failed_msg = "MariaDb keystore file does not exists in : "
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.SYMPTOM]

    def is_validation_passed(self):
        mariadb_all_Pods = self.get_mariadb_Pods("ALL")

        status = True
        if len(mariadb_all_Pods) > 0:
            for pod in mariadb_all_Pods:
                cmd = "sudo kubectl exec -it {} -n ncms -- ls -lrtha /mariadb/data/ | grep -i '.keystore' | wc -l".format(pod)
                file_exists = self.get_output_from_run_cmd(cmd).strip()
                if int(file_exists) == 0:
                    status = False
                    self._failed_msg = self._failed_msg + pod + " | "
        else:
            self._failed_msg = "Failed to find MariaDb pods"
            return False
        return status


class CheckMyConfFileMaridb(MariadbBaseValidator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "check_my_conf_file_maridb"
        self._title = "Check 'my.cnf' conf file exists on maridb"
        self._failed_msg = "MariaDb my.cnf file does not exists in : "
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.SYMPTOM]

    def is_validation_passed(self):
        mariadb_all_Pods = self.get_mariadb_Pods("ALL")

        status = True
        if len(mariadb_all_Pods) > 0:
            for pod in mariadb_all_Pods:
                cmd = "sudo kubectl exec -it {} -n ncms -- ls -l /opt/bitnami/mariadb/conf/my.cnf".format(pod)
                if self.run_cmd_return_is_successful(cmd) is False:
                    status = False
                    self._failed_msg = self._failed_msg + pod + " | "
        else:
            self._failed_msg = "Failed to find MariaDb pods"
            return False
        return status


class CheckHarborRegistryDiskUsage(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER]
    }

    MAX_USAGE_PERCENTAGE = 0.85

    def set_document(self):
        self._unique_operation_name = "check_harbor_registry_disk_usage"
        self._title = "Check harbor registry disk usage"
        self._failed_msg = "harbor registry disk usage in risk :"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.RISK_RESOURCE_CLEANING_RECOMMENDED]

    def is_validation_passed(self):
        cmd_list_pods = "sudo kubectl get pods --all-namespaces -l app=harbor-harbor -o name | grep harbor-harbor-registry"
        res, pods_output, err = self.run_cmd(cmd_list_pods)

        # not all systems has harbor  - if no harbor no problem in harbor
        if res != 0 or not pods_output:
            return True
        overall_status = True
        for pod_line in pods_output.splitlines():
            parts = pod_line.split()
            if not parts:
                continue
            harbor_pod_name = parts[0]
            disk_usage_cmd = "sudo kubectl exec -i {} -n ncms -c registry -- df -h".format(harbor_pod_name)
            disk_usages = self.get_output_from_run_cmd(disk_usage_cmd)
            disk_usages_lines = disk_usages.strip().splitlines()
            for usage_line in disk_usages_lines[1:]:
                values = usage_line.split()
                if len(values) < 6:
                    raise UnExpectedSystemOutput(self.get_host_ip(),
                                                 disk_usage_cmd, disk_usages,
                                                 "expected output with more then 6 fields found - [ " + str(
                                                     values) + " ]")
                usage = values[4]
                if '%' not in usage:
                    raise UnExpectedSystemOutput(self.get_host_ip(),
                                                 disk_usage_cmd, disk_usages,
                                                 "expected the usage in percentage in the fifth field found - [ {usage} ]".format(
                                                     usage=usage))

                usage_ratio = float(usage.replace('%', '')) / 100.0
                if usage_ratio > self.MAX_USAGE_PERCENTAGE:
                    self._failed_msg += " " + usage_line
                    overall_status = False

        return overall_status


######### Validation SOUVIK CODE STARTS #################
######### ICET-1409 | Verify the podman managed volumes on systems and see if it is exceeding more than the default limit of 2048

class PodmanVolumes(Validator):

    def get_podman_volume_count(self):
        cmd = "sudo /usr/bin/podman volume ls"
        out = self.get_output_from_run_cmd(cmd).splitlines()
        podman_volume_count = int(len(out)) - 1
        ### substarct 1 (-1) because 1st ROW in output is COLUMN NAMES/HEADINGS
        return max(0, podman_volume_count)

    def get_podman_volume_count_inside_directory(self):
        cmd = "sudo /usr/bin/ls /data0/podman/storage/volumes/ | grep -v 'backingFsBlockDev' | wc -l"
        out = self.get_output_from_run_cmd(cmd).strip()
        podman_volume_count_directory = int(out)
        return max(0, podman_volume_count_directory)

    def get_num_lock_value(self, entry):
        num_locks_array = entry.split("=")
        value = num_locks_array[1].strip()
        return int(value)

    def get_num_lock_from_podman_conf_file(self, CONF_FILENAME):
        if (self.file_utils.is_file_exist(CONF_FILENAME)):
            cmd = "sudo cat {} | grep -i 'num_locks ='".format(CONF_FILENAME)
            out = self.get_output_from_run_cmd(cmd).strip()
            entries_list = out.splitlines()
            num_locks_value = 0
            for num_lock_entry in entries_list:
                if (num_lock_entry.startswith("#")):
                    num_locks_value = self.get_num_lock_value(num_lock_entry.strip())
                else:
                    return self.get_num_lock_value(num_lock_entry.strip())
            return num_locks_value
        else:
            err = " | File '{}' does not exist".format(CONF_FILENAME)
            raise UnExpectedSystemOutput(ip=self._host_executor.ip, cmd="", output=str(err), message=str(err))


class PodmanVolumesValidation(PodmanVolumes):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ALL_NODES],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ALL_NODES],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ALL_NODES]
    }

    def set_document(self):
        self._unique_operation_name = "podman_volumes_validation"
        self._title = "Podman volumes validation"
        self._failed_msg = "ERROR!! PODMAN VOLUMES NOT EQUAL, It is not necessarily an on going issue. but it is worth checking the cluster"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.SYMPTOM]

    def is_validation_passed(self):
        podman_volume_count = self.get_podman_volume_count()
        podman_volume_count_directory = self.get_podman_volume_count_inside_directory()
        if int(podman_volume_count) == int(podman_volume_count_directory):
            return True
        else:
            self._failed_msg = self._failed_msg + \
                               " | Podman volumes in system = " + \
                               str(podman_volume_count) + \
                               " | Podman volume count inside directory /data0/podman/storage/volumes/ = " + \
                               str(podman_volume_count_directory)
            return False


class PodmanNumLockValidation(PodmanVolumes):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ALL_NODES],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ALL_NODES],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ALL_NODES]
    }

    def set_document(self):
        self._unique_operation_name = "podman_num_lock_validation"
        self._title = "Podman volumes podman num lock validation"
        self._failed_msg = "ERROR!! PODMAN VOLUMES Exceeded NUM_LOCK Value defined in PODMAN CONF"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.SYMPTOM]

    def is_validation_passed(self):
        CONF_FILENAME = "/usr/share/containers/containers.conf"
        podman_volume_count = self.get_podman_volume_count()
        podman_volume_num_lock = self.get_num_lock_from_podman_conf_file(CONF_FILENAME)
        if podman_volume_num_lock == 0:
            self._failed_msg += "\nERROR !!! Failed to Retrieve num_locks parameter from CONF File : {}\n".format(CONF_FILENAME)
            return False
        if int(podman_volume_count) < int(podman_volume_num_lock):
            return True
        else:
            self._failed_msg = self._failed_msg + \
                               " | Podman volumes in system = " + str(podman_volume_count) + \
                               " | Podman NUM_LOCK value in PODMAN Configuration file /usr/share/containers/containers.conf = " + \
                               str(podman_volume_num_lock)
            return False


class HarborTlsCheck(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "check_harbor_registry_pod_running_with_tls_env_variable"
        self._title = "Check harbor pod_running with tls env variable"
        self._failed_msg = "harbor registry pod is not running with TLS."
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]

    def is_prerequisite_fulfilled(self):
        return not gs.get_hotfix_list()

    def is_validation_passed(self):
        cmd1 = "kubectl get po -nncms --selector component=jobservice,app=harbor-harbor -o name"
        res, harbor_jobservice_pod_name, err = self.run_cmd(cmd1)

        # not all systems has harbor  - if no harbor no problem in harbor
        if res != 0 or not harbor_jobservice_pod_name:
            return True
        josbservice_pod = harbor_jobservice_pod_name.strip()
        tls_check_cmd = "sudo kubectl exec -it {} -nncms  -- env | grep -i INTERNAL_TLS_ENABLED".format(josbservice_pod)
        tls_check_output = self.get_output_from_run_cmd(tls_check_cmd)
        if "INTERNAL_TLS_ENABLED=true" in tls_check_output:
            return True
        return False


class CheckRedisClusterStatus(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MANAGER]
    }

    def set_document(self):
        self._unique_operation_name = "check_redis_cluster_status"
        self._title = "Check redis sentinel cluster status"
        self._failed_msg = ""
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.APPLICATION_DOMAIN]

    def is_validation_passed(self):
        docker_or_podman = adapter.docker_or_podman()
        cmd = "sudo {} exec redis-sentinel redis-cli -p 26379 info Sentinel".format(docker_or_podman)
        out = self.get_output_from_run_cmd(cmd, add_bash_timeout=True)
        redis_status = re.findall("master0.*,status=(.*?),", out)

        if len(redis_status) != 1:
            raise UnExpectedSystemOutput(self.get_host_ip(), cmd, out, "Expected to get only 1 time status=<any status>"
                                                                       " in out.")
        redis_status = redis_status[0]

        if redis_status == "ok":
            return True
        else:
            self._failed_msg = "redis cluster status is not ok"
            return False


class CheckPerconaXtradbIsSynced(Validator):
    objective_hosts = [Objectives.ONE_MANAGER]

    def set_document(self):
        self._unique_operation_name = "check_percona_xtradb_is_synced"
        self._title = "Verify Percona XtraDB Cluster is synced"
        self._failed_msg = "Percona XtraDB Cluster is not synced"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        command = "sudo /usr/local/bin/clustercheck | grep -i 'is synced'|wc -l"
        # NOTE: without the command full
        # path this is not working on some od the systems
        out = self.get_output_from_run_cmd(command)

        if int(out) == 1:
            return True

        return False


class CheckRedisHAStatus(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.MANAGERS]
    }

    def set_document(self):
        self._unique_operation_name = "check_redis_HA_status"
        self._title = "Check redis cluster HA status on all managers"
        self._failed_msg = ""
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        docker_or_podman = adapter.docker_or_podman()

        redis_sentinel_status_cmd = "sudo {} inspect redis-sentinel | jq '.[0].State'".format(docker_or_podman)
        redis_status_cmd = "sudo {} inspect redis | jq '.[0].State'".format(docker_or_podman)

        redis_sentinel_state = str(self.get_output_from_run_cmd(redis_sentinel_status_cmd))
        redis_sentinel_state = json.loads(redis_sentinel_state)
        if redis_sentinel_state is None:
            raise UnExpectedSystemOutput(self.get_host_ip(), redis_sentinel_status_cmd, output=redis_sentinel_state,
                                         message="Failed to get state of 'redis-sentinel'")
        redis_state = str(self.get_output_from_run_cmd(redis_status_cmd))
        redis_state = json.loads(redis_state)
        if redis_state is None:
            raise UnExpectedSystemOutput(self.get_host_ip(), redis_status_cmd, output=redis_state,
                                         message="Failed to get state of 'redis'")

        if self._is_health_status_ok(redis_state, redis_status_cmd) \
                and self._is_status_ok(redis_state, redis_status_cmd) \
                and self._is_health_status_ok(redis_sentinel_state, redis_sentinel_status_cmd) \
                and self._is_status_ok(redis_sentinel_state, redis_sentinel_status_cmd):
            return True
        else:
            self._failed_msg = "redis/redis-sentinel containers status is not ok on this " + self.get_host_name() + \
                               " node, verify it on all managers and make sure they are in sync and healthy"
            return False

    def _is_status_ok(self, state, cmd):
        if "Status" not in list(state.keys()):
            raise UnExpectedSystemOutput(self.get_host_ip(), cmd, output=state, message="Expected to have 'Status' "
                                                                                        "in out keys.")
        return state["Status"] == "running"

    def _is_health_status_ok(self, state, cmd):
        if "Health" in list(state.keys()):
            key = "Health"
        elif "Healthcheck" in list(state.keys()):
            key = "Healthcheck"
        else:
            raise UnExpectedSystemOutput(self.get_host_ip(), cmd, output=state, message="Expected to have 'Health' "
                                                                                        "or 'Healthcheck' in out keys.")
        return state[key].get("Status") == "healthy"


class CburLatestBackupsSucceeded(Validator):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._unique_operation_name = "verify_cbur_latest_backups_succeeded"
        self._title = "Check if latest CBUR backups are successful in ncms namespace."
        self._failed_msg = ""
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.SYMPTOM, ImplicationTag.RISK_NO_HIGH_AVAILABILITY]

    def get_br_polices_name_list(self):
        # Returns a list with BRPolices names in the ncms namespace
        get_brpolices_cmd = 'sudo kubectl get brpolices.cbur.csf.nokia.com -n ncms --no-headers -o custom-columns=":metadata.name"'  # Applicable for NCS22.7+
        get_local_brpolices_cmd = 'sudo kubectl get brpolices.cbur.bcmt.local -n ncms --no-headers -o custom-columns=":metadata.name"'  # Applicable for NCS20FP2
        try:
            output_get_brpolices = self.get_output_from_run_cmd(get_brpolices_cmd)
            if not output_get_brpolices:
                output_get_brpolices = self.get_output_from_run_cmd(get_local_brpolices_cmd)
        except:
            self._failed_msg = "There are no ncms BRPolices in this cluster, check it with kubectl."
            return []
        if output_get_brpolices:
            brpolices_list = output_get_brpolices.split("\n")
            brpolices_name_list = [str(r) for r in brpolices_list]
            brpolices_name_list = list([_f for _f in brpolices_name_list if _f])
            return brpolices_name_list

    def get_brpolice_history(self, brpolice):
        self.get_brpolice_history_cmd = 'sudo kubectl get brpolices.cbur.csf.nokia.com -n ncms {0} -o jsonpath={{.status.requestHistory}}'.format(
            brpolice)  # Applicable for NCS22.7+
        self.get_local_brpolice_history_cmd = 'sudo kubectl get brpolices.cbur.bcmt.local -n ncms {0} -o jsonpath={{.status.requestHistory}}'.format(
            brpolice)  # Applicable for NCS20FP2
        try:
            history_output = self.get_output_from_run_cmd(self.get_brpolice_history_cmd)
            return history_output
        except:
            history_output = self.get_output_from_run_cmd(self.get_local_brpolice_history_cmd)
            return history_output

    def get_lastbackup_event_list(self):
        backup_event_list = []
        br_polices_name_list = self.get_br_polices_name_list()
        if br_polices_name_list:
            for brpolice in br_polices_name_list:
                event_backup_status = self.get_brpolice_history(brpolice)
                if not event_backup_status:
                    if "harbor-registry" in brpolice: # Harbor registry backups are disabled by default
                        continue
                    self._failed_msg += "\nNo backup event found in BP: {0}.".format(brpolice)
                    continue
                else:
                    data = event_backup_status.split('"status":')
                    backup_event_list.append({brpolice: data[-1]})
            if not backup_event_list:
                # This scenario is not likely to happen.
                # Only if the HC is triggered in a fresh deployment with empty BRPolices (no backup events).
                self._failed_msg += "\nNote: If this is a fresh deployment, desconsider this failure."
                self.add_to_validation_log(
                    "No backups events found in ncms BRPolices. If this is a fresh deployment, desconsider this failure.")
                return []
            return backup_event_list
        else:
            return []

    def is_validation_passed(self):
        backup_event_list = self.get_lastbackup_event_list()
        if not backup_event_list:
            return False
        failed_string = ""
        for event in backup_event_list:
            for key in list(event.keys()):
                value = event[key]
                if "Success" in value:
                    continue
                else:
                    failed_string += " {0}".format(key)
            continue
        if failed_string:
            self._failed_msg += "Failed backup event found in BRPolices:{0}.".format(failed_string)
            return False
        return True


class CheckWhereaboutsCleanerPodIsFrozen(Validator):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._unique_operation_name = "check_whereabouts_cleaner_pod_is_frozen"
        self._title = "Check if Whereabouts cleaner pod is frozen"
        self._failed_msg = ""
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.RISK_GARBAGE_CLEANING_RECOMMENDED]

    def get_whereabouts_pod_name(self):
        get_pod_name_cmd = "sudo kubectl get pods -n kube-system -l app=whereabouts-cleaner | grep whereabouts |" \
                           "grep -i Running | awk '{print $1}'"
        whereabouts_pod_name = self.get_output_from_run_cmd(get_pod_name_cmd)
        whereabouts_pod_name = whereabouts_pod_name.strip()
        return whereabouts_pod_name

    def set_unavailability_threshold_seconds(self, whereabouts_pod_name):
        default_unavailability_threshold_seconds = 24 * 60 * 60
        get_pod_interval_param_cmd = "sudo kubectl get pod {} -n kube-system -o json | jq -r 'if has(\"spec\")" \
                                     "and .spec.containers[0].env then .spec.containers[0].env[]" \
                                     "| select(.name == \"SCRIPT_INTERVAL\") | .value else empty end'" \
            .format(whereabouts_pod_name)
        pod_interval_param = self.get_output_from_run_cmd(get_pod_interval_param_cmd)

        if len(pod_interval_param) > 0:
            return int(pod_interval_param) + \
                default_unavailability_threshold_seconds
        else:
            return default_unavailability_threshold_seconds

    def get_whereabouts_pod_latest_log(self, whereabouts_pod_name):
        get_pod_latest_log_cmd = "sudo kubectl logs -n kube-system {0} | tail -n1".format(whereabouts_pod_name)
        pod_latest_log = self.get_output_from_run_cmd(get_pod_latest_log_cmd)
        pod_latest_log = pod_latest_log.replace("\n", "")
        return pod_latest_log

    def get_server_current_date(self):
        get_current_date_cmd = "date"
        date = self.get_output_from_run_cmd(get_current_date_cmd)
        date = date.replace("\n", "")
        return date

    def parse_datetime_without_tz(self, date_string):
        date_string_without_tz = ' '.join(date_string.split()[:-2] + date_string.split()[-1:])
        date_format = "%a %b %d %H:%M:%S %Y"
        return datetime.strptime(date_string_without_tz, date_format)

    def is_latest_log_recent(
            self,
            whereabouts_pod_name,
            server_current_date,
            whereabouts_latest_log):
        unavailability_threshold_seconds = self.set_unavailability_threshold_seconds(whereabouts_pod_name)

        try:
            whereabouts_latest_log_datetime = self.parse_datetime_without_tz(
                whereabouts_latest_log)
            server_current_date_datetime = self.parse_datetime_without_tz(
                server_current_date)
        except:
            return False

        time_difference = abs(
            whereabouts_latest_log_datetime -
            server_current_date_datetime)

        if time_difference.total_seconds() < unavailability_threshold_seconds:
            return True
        else:
            return False

    def is_validation_passed(self):
        whereabouts_pod_name = self.get_whereabouts_pod_name()
        server_current_date = self.get_server_current_date()
        whereabouts_pod_latest_log = self.get_whereabouts_pod_latest_log(whereabouts_pod_name)
        if len(whereabouts_pod_name) > 0:
            if self.is_latest_log_recent(
                    whereabouts_pod_name,
                    server_current_date,
                    whereabouts_pod_latest_log):
                return True
            else:
                self._failed_msg = "Latest Whereabouts Cleaner log is not recent. Restart the pod."
                return False
        # Not applicable - pod doesn't exist
        else:
            return True

class CheckAllowedDisruptionsInPodDisruptionBudget(Validator):

    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "verify_allowed_disruptions_in_Pod_Disruption_Budget_set_to_zero_or_not"
        self._title = "Verify Allowed Disruptions in PDB is not set to zero."
        self._failed_msg = "Allowed Disruptions in PDB is set to Zero"
        self._severity = Severity.NOTIFICATION
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.UPGRADE, BlockingTag.SCALE]

    def is_prerequisite_fulfilled(self):
        # no meaning to test this on singel node cluster
        return len(globals.get_host_executor_factory().get_all_host_executors()) > 2  # one ice container + one host

    def is_validation_passed(self):
        pdb_command = "sudo kubectl get pdb -A  -o json"
        out = self.get_output_from_run_cmd(pdb_command)
        pdb_dict={}  #Creating empty disctiory to get PDP list which are set to disruptionsAllowed  0
        convert_to_json = json.loads(out)
        ncs_version = globals.get_version()
        for item in convert_to_json['items']:
            if 'minAvailable' in str(item) and item['status']['disruptionsAllowed'] == 0:
                """
                sometime minAvailable will not be set any value ie ( minAvailable is set to N/A), in such cases no need to validate disruptionsAllowed.

                """
                distruption_allowed = item['status']['disruptionsAllowed']
                pdbname=item['metadata']['name']
                if ncs_version < Version.V25_11 and pdbname == "database-cluster-primary":
                    pdb_dict[pdbname] = distruption_allowed

        if len(pdb_dict) != 0:  #validating the list is empty or not.
            convert_dict_to_str = ''
            for key, value in list(pdb_dict.items()):
                convert_dict_to_str = convert_dict_to_str + 'PDB name: {}\nAllowed disruption value: {}\n'.format(str(key), str(value))
            self._failed_msg = "The below PDB allowed disruption value is set to Zero:\n{}".format(convert_dict_to_str)
            return False
        else:
            return True
class VerifyMissingContainerImages(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.MASTERS]
    }

    def set_document(self):
        self._unique_operation_name = "verify_container_images_not_missing"
        self._title = "Verfiy missing images in the master nodes."
        self._failed_msg = "The following container images are missing: "
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        expected_images_list = ['bcmt-nginx']
        docker_podman = adapter.docker_or_podman()
        list_images_cmd = "sudo  {} images --format '{{{{.Repository}}}}'".format(docker_podman)
        out = self.get_output_from_run_cmd(list_images_cmd, add_bash_timeout=True)
        actual_images_list = []   # Get the bcmt-nginx container image in the node
        for expected_image in expected_images_list:
            for image in out.splitlines():
                if expected_image in image:
                    actual_images_list.append(expected_image)    # Matching found will append the list.
                    continue
        if set(expected_images_list) != set(actual_images_list):   # if list is empty means bcmt-nginx image doesn't exists in the nodes.
            self._failed_msg += "\n{} images output these images are missing  {}".format(docker_podman,PythonUtils.words_in_A_missing_from_B(expected_images_list, actual_images_list))
            return False
        return True

class VerifyDeploymentAndStatefulsetResilient(Validator):

    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "verify_deployment_and_statefulset_resilient"
        self._title = "Check if Deployments and StatefulSets are resilient"
        self._failed_msg = "Verify Deployment or StatefulSet have multiple replicas, have an anti-affinity, and pdb disruptionsAllowed not zero\nfollowing Deployment/StatefulSet may cause an outage on reboot\n"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.RISK_NO_HIGH_AVAILABILITY]

    def is_prerequisite_fulfilled(self):
        # no meaning to test this on singel node cluster
        return len(globals.get_host_executor_factory().get_all_host_executors()) > 2  # one ice container + one host

    def is_validation_passed(self):
        get_resource_cmd = "sudo /usr/local/bin/kubectl get deployments,statefulset -A -o json | jq -r '.items[] | \"\\(.kind) \\(.metadata.namespace) \\(.metadata.name) \\(.spec.template.spec.affinity.podAntiAffinity) \\(.status.replicas) \\(.spec.template.metadata.labels)\"' "
        resource_cmd_output = self.get_output_from_run_cmd(get_resource_cmd)
        resources_one_replica_or_no_anti_affinity = []
        resources_no_disruption_budget = []
        namespace_list = ['ncms', 'kube-system', 'node-feature-discovery', 'rook-ceph', 'btel', 'istio-system']
        if resource_cmd_output:
            for resource in resource_cmd_output.strip().splitlines():
                resource_info = resource.split()
                resource_type, namespace, resource_name, anti_affinity_status, replica_count, resource_labels = resource_info
                try:
                    resource_labels_dict = json.loads(resource_labels)
                except:
                    resource_labels_dict = {}

                if namespace not in namespace_list and replica_count!= 'null' and int(replica_count) != 0:
                    resource_str = "{}:  {}, Namespace: {}, Is Anti-affinity presented: {}, Number of replicas: {}".format(
                        resource_type,
                        resource_name,
                        namespace,
                        bool(anti_affinity_status != 'null'),
                        replica_count
                    )

                    if (anti_affinity_status == 'null') or int(replica_count) == 1:
                        resources_one_replica_or_no_anti_affinity.append(resource_str)

                    pdb_cmd = "sudo /usr/local/bin/kubectl get pdb -n {} -o json".format(namespace)
                    pdb_dict = json.loads(self.get_output_from_run_cmd(pdb_cmd))
                    for pdb in pdb_dict.get('items', []):
                        pdb_match_labels = pdb['spec']['selector']['matchLabels'].items()
                        if set(pdb_match_labels).issubset(resource_labels_dict.items()):
                            disruptions_allowed = pdb["status"]["disruptionsAllowed"]
                            if disruptions_allowed == 0:
                                resources_no_disruption_budget.append(resource_str + ", PDB name: {}".format(pdb["metadata"]["name"]))

            if not resources_one_replica_or_no_anti_affinity and not resources_no_disruption_budget:
                return True
            if resources_one_replica_or_no_anti_affinity:
                self._failed_msg += "The following Deployments or StatefulSets are missing anti-affinity rules or have only 1 replica: \n {} \n".format(
                    '\n'.join(resources_one_replica_or_no_anti_affinity))
            if resources_no_disruption_budget:
                self._failed_msg += "The following Deployments or StatefulSets have a PodDisruptionBudget (PDB) configured with disruptionsAllowed = 0:  \n {} \n".format(
                    '\n'.join(resources_no_disruption_budget))
            return False
        else:
           return True


class ValidateLockForPodmanVolumes(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.MASTERS]
    }

    def set_document(self):
        self._unique_operation_name = "check_lock_for_volume"
        self._title = "Validate lock error for podman volumes"
        self._failed_msg = "Error present in podman volumes list: \n"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]
        self._blocking_tags = [BlockingTag.UPGRADE]

    def is_validation_passed(self):
        podman_volume_list_cmd = "sudo podman volume list"
        podman_volume_list = self.get_output_from_run_cmd(podman_volume_list_cmd)
        podman_volume_list = podman_volume_list.splitlines()
        volume_lock_list = []
        for volume in podman_volume_list:
            if 'ERRO[0000]' in volume:
                volume_lock_list.append(volume)
        if len(volume_lock_list) > 0:
            self._failed_msg += " {}".format("\n".join(volume_lock_list))
            return False
        return True


class CheckK8sPendingJobsCount(Validator):
    objective_hosts = [Objectives.ONE_MASTER]

    MAX_PENDING_JOBS_COUNT = 100

    def set_document(self):
        self._unique_operation_name = "check_k8s_pending_jobs_count"
        self._title = "Check k8s pending jobs count not exceeding {}".format(CheckK8sPendingJobsCount.MAX_PENDING_JOBS_COUNT)
        self._failed_msg = ""
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM, ImplicationTag.PERFORMANCE]

    def is_validation_passed(self):
        cmd = "sudo kubectl get jobs.batch -A --no-headers"
        out = self.get_output_from_run_cmd(cmd)
        count = len(out.strip().splitlines())
        if count > CheckK8sPendingJobsCount.MAX_PENDING_JOBS_COUNT:
            self._failed_msg = "k8s pending jobs number:{} exceeded Threshold:{}".format(count, CheckK8sPendingJobsCount.MAX_PENDING_JOBS_COUNT)
            return False
        return True


class ValidatePvSizeAgainstHelmChart(Validator):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._unique_operation_name = "validate_harbor_pvc_size_alignment_with_helm_chart"
        self._title = "Validate Harbor PVCs sizes are aligned with Helm chart of Harbor"
        self._failed_msg = "Harbor PVC size alignment with Helm chart failed due to the following issues:\n"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]
        self._blocking_tags = [BlockingTag.CERT_RENEWAL]

    def is_validation_passed(self):
        harbor_persistence_values_cmd = "sudo helm get values -n ncms harbor -o json"
        full_json_output = json.loads(self.get_output_from_run_cmd(harbor_persistence_values_cmd))
        persistence_config = full_json_output.get("persistence", {})

        helm_pvc_sizes_dict = {
            key: value.get("size")
            for key, value in persistence_config.get("persistentVolumeClaim", {}).items()
        }
        k8s_pvc_sizes_dict = self._get_harbor_pvc_sizes()
        validation_passed = True
        for helm_vol_name, helm_size in helm_pvc_sizes_dict.items():
            matched_pvc_size = None
            for pvc_name, pvc_size in k8s_pvc_sizes_dict.items():
                if helm_vol_name in pvc_name:
                    matched_pvc_size = pvc_size
                    break
            if matched_pvc_size is None:
                raise UnExpectedSystemOutput(
                    self.get_host_ip(), harbor_persistence_values_cmd, full_json_output,
                    message="PVC for '{}' not found.\n"
                            "Please check the enable flag for the missing PVC; "
                            "if it is false, please ignore this.".format(helm_vol_name))
            elif matched_pvc_size != helm_size:
                self._failed_msg += "Size mismatch for '{}' - Helm: {}, Harbor PVC: {}.\n".format(helm_vol_name, helm_size, matched_pvc_size)
                validation_passed = False

        return validation_passed

    def _get_harbor_pvc_sizes(self):
        pvc_list_cmd = "sudo kubectl get pvc -n ncms -o json"
        pvc_out_dict = json.loads(self.get_output_from_run_cmd(pvc_list_cmd))

        pvc_sizes = {}
        for item in pvc_out_dict.get("items", []):
            pvc_name = item["metadata"]["name"]
            if "harbor" in pvc_name:
                # read size from spec instead of status
                pvc_size = item["spec"]["resources"]["requests"].get("storage")
                if pvc_size:
                    pvc_sizes[pvc_name] = pvc_size

        return pvc_sizes


class ValidateGaleraDiskUsage(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER]
    }
    DISK_USAGE_THRESHOLD_PERCENT = 80

    def set_document(self):
        self._unique_operation_name = "check_galera_pods_disk_usage"
        self._title = "Galera Pod Disk Usage Check"
        self._failed_msg = "The following galera pod's disk usage has reached or exceeded {}%:".format(ValidateGaleraDiskUsage.DISK_USAGE_THRESHOLD_PERCENT)
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        pods = self._get_mariadb_pods()
        validation_passed = True
        for pod in pods:
            cmd = "sudo kubectl exec -ti -n ncms {} -- bash -c df -h | grep mariadb".format(pod)
            mariadb_disk_usage_output = self.get_output_from_run_cmd(cmd)
            disk_space_usage = re.findall(r'(\S+).*\s+([0-9]+)%.*', mariadb_disk_usage_output)
            for disk in disk_space_usage:
                usage = int(disk[1])
                if usage >= ValidateGaleraDiskUsage.DISK_USAGE_THRESHOLD_PERCENT:
                    self._failed_msg += "\n Note: {} on pod {} usage is {}%.\n".format(
                        disk[0], pod, usage)
                    validation_passed = False
        return validation_passed

    def _get_mariadb_pods(self):

        out = self.get_output_from_run_cmd("sudo /usr/local/bin/kubectl get pods -n ncms --no-headers | grep -i 'mariadb'").strip()
        mariadb_all_pods_list = []
        for line in out.splitlines():
            mariadb_pod = line.split()[0]
            mariadb_all_pods_list.append(mariadb_pod)
        return mariadb_all_pods_list

class ValidateCsiCephRbdConfigFile(Validator):
    objective_hosts = {Deployment_type.NCS_OVER_BM:[Objectives.MASTERS, Objectives.WORKERS, Objectives.EDGES]}

    def set_document(self):
        self._unique_operation_name = "check_csi_cephfs_config_file"
        self._title = "Check CSI CephFS Nodeplugin Config File"
        self._failed_msg = "TBD"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        get_pods_cephfs_cmd = "sudo kubectl get pods -nncms -l component=nodeplugin,app=csi-cephfs"
        get_pods_cephfs_out = self.get_output_from_run_cmd(get_pods_cephfs_cmd)
        pod_name_cephfs_list= [line.split()[0] for line in get_pods_cephfs_out.splitlines()[1:]]

        get_pods_cephrbd_cmd = "sudo kubectl get pods -nncms -l component=nodeplugin,app=csi-cephrbd"
        get_pods_cephrbd_out = self.get_output_from_run_cmd(get_pods_cephrbd_cmd)
        pod_name_cephrbd_list= [line.split()[0] for line in get_pods_cephrbd_out.splitlines()[1:]]

        cephrbd_config_file_path = "/etc/ceph-csi-config/config.json"
        missing_pods = []

        cephfsplugin_container = "csi-cephfsplugin"
        cephrbd_container = "csi-rbdplugin"
        cephrbd_config_check_cmd = "sudo kubectl exec -it {} -nncms -c {} -- /bin/ls {}"
        for pod_name in pod_name_cephfs_list:
            cephrbd_config_check_out = self.get_output_from_run_cmd(cephrbd_config_check_cmd.format(
                pod_name, cephfsplugin_container, cephrbd_config_file_path))
            if "No such file or directory" in cephrbd_config_check_out:
                missing_pods.append(pod_name)

        for pod_name in pod_name_cephrbd_list:
            cephrbd_config_check_out = self.get_output_from_run_cmd(cephrbd_config_check_cmd.format(
                pod_name,cephrbd_container, cephrbd_config_file_path))

            if "No such file or directory" in cephrbd_config_check_out:
                missing_pods.append(pod_name)

        if missing_pods:
            self._failed_msg = (
                "The following pods are missing {}:\n{}".format(
                    cephrbd_config_file_path,
                    "\n".join("- {}".format(pod) for pod in missing_pods))
            )
            return False
        return True

class HarborCertVipValidation(Validator):

    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "check_harbor_nginx_cert_vip"
        self._title = "Check Harbor Nginx Certificate VIP"
        self._failed_msg = "ERROR !!\n"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_prerequisite_fulfilled(self):
        get_cert_cmd = "sudo kubectl get certificates -n ncms harbor-harbor-nginx-cert --no-headers | wc -l"
        cert_out = self.get_output_from_run_cmd(get_cert_cmd)
        return int(cert_out.strip()) == 1

    def is_validation_passed(self):
        cmd = "sudo kubectl get pods -nncms -l app=harbor-harbor"
        out = self.get_output_from_run_cmd(cmd)
        if out.strip():
            cmd = "sudo kubectl get certificates -nncms harbor-harbor-nginx-cert -o json | jq .spec.ipAddresses"
            out = self.get_output_from_run_cmd(cmd)
            ip_list = json.loads(out)
            vip_cmd = "sudo /bin/hiera -c /usr/share/cbis/data/cbis_hiera.yaml tripleo::haproxy::public_virtual_ip"
            vip_out = self.get_output_from_run_cmd(vip_cmd)
            if vip_out in ip_list:
                return True
            else:
                self._failed_msg += ("The certificate: harbor-harbor-nginx-cert is not having the required Virtual IP (VIP): {}"
                                     " .App Images cannot be pulled because the client cannot "
                                     "verify the identity of the registry via the VIP.").format(vip_out)
                return False
        else:
            raise UnExpectedSystemOutput(ip=self.get_host_ip(), cmd=cmd, output="Harbor component pods were not found in the 'ncms' "
                                                                          "namespace. Certificate validation cannot proceed.")


class VerifyCkeyServiceConnectivity(MariadbBaseValidator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "check_ckey_service_connectivity"
        self._title = "Verify ckey service connectivity"
        self._failed_msg = ""
        self._severity = Severity.ERROR
        self._blocking_tags = [BlockingTag.UPGRADE]
        self._implication_tags = [ImplicationTag.PRE_OPERATION]


    def is_validation_passed(self):
        mariadb_pods = self.get_mariadb_Pods('RUNNING')
        is_passed = True
        for mariadb_pod in mariadb_pods:
            cmd = "sudo kubectl exec -n ncms {} -- curl -k https://bcmt-ckey-ckey.ncms.svc:8443/auth/realms/master/protocol/openid-connect/token".format(mariadb_pod)
            return_code, out, err = self.run_cmd(cmd, add_bash_timeout=True)
            if return_code == 0:
                pass
            elif return_code == 7:
                self._failed_msg += "Cannot connect to CKEY service from {mariadb_pod} connection refused. Ensure the CKEY service is running and reachable on port 8443.\n\n".format(mariadb_pod=mariadb_pod)
                is_passed = False
            else:
                self._failed_msg += "Unexpected error connecting to CKEY service from {mariadb_pod}. Return code: {return_code}, stderr: {err}\n\n".format(mariadb_pod=mariadb_pod, return_code=return_code, err=err)
                is_passed = False
        return is_passed

class ValidateHarborCburRegistryBackupWithPvc(Validator):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._unique_operation_name = "validate_harbor_cbur_registry_backupwithpvc_enabled"
        self._title = "Validate Harbor Registry backup is configured with pvc, if enabled"
        self._failed_msg = "Harbor Registry backup is enabled without using PVC"
        self._severity = Severity.NOTIFICATION
        self._implication_tags = [ImplicationTag.NOTE]

    def is_validation_passed(self):
        validation_passed = True

        # Pre-check: Verify if Harbor is installed
        check_harbor_present_cmd = "sudo helm list -n ncms --filter harbor -o json"
        harbor_list_out = self.get_output_from_run_cmd(check_harbor_present_cmd)

        harbor_installed = False
        try:
            releases = json.loads(harbor_list_out)
            for release in releases:
                if release.get('name') == 'harbor':
                    harbor_installed = True
                    break
        except (ValueError, TypeError):
            # If JSON parsing fails or output is empty, we assume Harbor is not present
            # so validation_passed remains True
            pass

        if harbor_installed:
            get_values_cmd = "sudo helm get values harbor -n ncms -o json"
            values_out = self.get_output_from_run_cmd(get_values_cmd)

            try:
                values = json.loads(values_out)

                # Navigate the dictionary safely using .get()
                cbur_config = values.get('cbur', {})
                registry_config = cbur_config.get('registry', {})

                is_registry_enabled = registry_config.get('enabled', False)
                is_backup_with_pvc = registry_config.get('backupwithpvc', False)

                # logic: Fail ONLY if enabled is True AND backupwithpvc is False
                if is_registry_enabled and not is_backup_with_pvc:
                    self._failed_msg += " (cbur.registry.enabled is True, but cbur.registry.backupwithpvc is False)"
                    validation_passed = False

            except (ValueError, TypeError):
                self._failed_msg += "\nUnable to parse Harbor helm values."
                validation_passed = False

        return validation_passed

class RedhatEfiGrubConfigExistenceValidator(Validator):
    objective_hosts = [Objectives.ALL_NODES]

    def set_document(self):
        self._unique_operation_name = "verify_redhat_efi_grub_config_exists"
        self._title = "Verify Red Hat EFI GRUB Configuration File Exists"
        self._failed_msg = ""
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.SYMPTOM, ImplicationTag.ACTIVE_PROBLEM]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_prerequisite_fulfilled(self):
        cmd = "sudo ls -ld /sys/firmware/efi | wc -l"
        efi_exists = self.get_output_from_run_cmd(cmd)
        system_cmd = "cat /etc/redhat-release"
        system_out = self.get_output_from_run_cmd(system_cmd)
        return int(efi_exists.strip()) == 1 and "Red Hat" in system_out

    def is_validation_passed(self):
        files_path = ["/boot/efi/EFI/redhat/grubenv"]
        validation_status = True

        for file in files_path:
            if not self.file_utils.is_file_exist(file):
                validation_status = False
                self._failed_msg += "Required EFI GRUB configuration {} is missing.\n".format(file)
                continue

            cmd = "sudo grep -w {} {}".format("kernelopts", file)
            return_code, out, err = self.run_cmd(cmd, add_bash_timeout=True)

            if return_code != 0:
                self._failed_msg = "Required EFI GRUB configuration {} is exits but {} is missing.".format(file, "kernelopts")
                validation_status = False

        return validation_status


class CheckCburBackendConfigFile(Validator):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._unique_operation_name = "check_cbur_backend_config_file"
        self._title = "Check /CLUSTER/backend.config in cbur mycelery pod"
        self._failed_msg = ""
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def _get_cbur_mycelery_pod(self):
        cmd = "sudo kubectl get pods -n ncms -l app=cbur-master-cbur-mycelery -o name"
        pod_name = self.get_output_from_run_cmd(cmd).strip()
        if not pod_name:
            return None
        return pod_name.splitlines()[0]

    def is_validation_passed(self):
        pod_name = self._get_cbur_mycelery_pod()
        if not pod_name:
            self._failed_msg = "cbur-master-cbur-mycelery pod not found in ncms namespace"
            return False

        cmd = "sudo kubectl exec -i -n ncms {} -c cbur -- ls /CLUSTER/backend.config".format(pod_name)
        return_code, out, err = self.run_cmd(cmd)
        if return_code != 0:
            self._severity = Severity.NOTIFICATION
            self._implication_tags = [ImplicationTag.NOTE]
            self._failed_msg = "/CLUSTER/backend.config file does not exist in cbur mycelery pod ({})".format(pod_name)
            return False

        cmd = "sudo kubectl exec -i -n ncms {} -c cbur -- wc -c /CLUSTER/backend.config".format(pod_name)
        return_code, out, err = self.run_cmd(cmd)
        if return_code != 0:
            self._failed_msg = "There was some issue reading file /CLUSTER/backend.config in the cbur mycelery pod ({})".format(pod_name)
            return False
        file_size = int(out.strip().split()[0])
        if file_size == 0:
            self._failed_msg = "/CLUSTER/backend.config in cbur mycelery pod ({}) is empty (0 bytes), likely due to a previous PVC related issue".format(pod_name)
            return False
        return True


class CheckCburBackupDiskUsage(Validator):
    objective_hosts = [Objectives.ONE_MASTER]

    MAX_USAGE_PERCENTAGE = 0.85

    def set_document(self):
        self._unique_operation_name = "check_cbur_backup_disk_usage"
        self._title = "Check CBUR /BACKUP and /CBUR_REPO disk usage"
        self._failed_msg = "CBUR disk usage in risk :"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.RISK_RESOURCE_CLEANING_RECOMMENDED]

    def _get_cbur_mycelery_pod(self):
        cmd = "sudo kubectl get pods -n ncms -l app=cbur-master-cbur-mycelery -o name"
        pod_name = self.get_output_from_run_cmd(cmd).strip()
        if not pod_name:
            return None
        return pod_name

    def _check_disk_usage(self, pod_name, path):
        cmd = "sudo kubectl exec -i -n ncms {} -c cbur -- df -h {}".format(pod_name, path)
        return_code, out, err = self.run_cmd(cmd)

        if return_code != 0 or not out.strip():
            self._failed_msg += " failed to check disk usage for {} in pod {}".format(path, pod_name)
            return False

        lines = out.strip().splitlines()
        overall_status = True
        for usage_line in lines[1:]:
            values = usage_line.split()
            if len(values) < 6:
                raise UnExpectedSystemOutput(self.get_host_ip(),
                                             cmd, out,
                                             "expected output with more than 6 fields found - [ " + str(
                                                 values) + " ]")
            usage = values[4]
            if '%' not in usage:
                raise UnExpectedSystemOutput(self.get_host_ip(),
                                             cmd, out,
                                             "expected the usage in percentage in the fifth field found - [ {usage} ]".format(
                                                 usage=usage))

            usage_ratio = float(usage.replace('%', '')) / 100.0
            if usage_ratio > self.MAX_USAGE_PERCENTAGE:
                self._failed_msg += " " + usage_line
                overall_status = False

        return overall_status

    def is_validation_passed(self):
        pod_name = self._get_cbur_mycelery_pod()
        if not pod_name:
            self._failed_msg = "No pod with label app=cbur-master-cbur-mycelery found in ncms namespace"
            self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]
            return False
        backup_ok = self._check_disk_usage(pod_name, "/BACKUP")
        cbur_repo_ok = self._check_disk_usage(pod_name, "/CBUR_REPO")
        return backup_ok and cbur_repo_ok
