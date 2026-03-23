from __future__ import absolute_import
from flows.Cbis.user_config_validator.user_config_checks import *
import tools.DynamicPaths as DynamicPaths
import re
import tools.sys_parameters as sys_param
from tools.ConfigStore import ConfigStore

from tools.python_versioning_alignment import decode_base_64
from six.moves import range
from six.moves import zip


######  SOUVIK GLUSTERFS TEST CODE BEGINS  #########################

############################################################
## glusterfs_validations     oepnstack,vsphere, CN_B,CN_A
#############################################################

class glusterFsInstalledStatus(Validator):

    #### This class is BASE class
    ### Here we are checing Wheher in the cluster GLUSTER is installed or not....

    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MANAGER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.DEPLOYER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.DEPLOYER],
    }

    def glusterFs_installed_or_not_status(self):
        gluster_flag = None
        ## If CN-B Then Follow this Block
        if sys_param.get_deployment_type() == Deployment_type.NCS_OVER_BM:
            conf_dict = ConfigStore.get_ncs_bm_conf()
            # print(conf_dict)

            if conf_dict["cluster_deployment"]["cluster_config"]["k8s_shared_storage"]:
                cidr_block = conf_dict["cluster_deployment"]["cluster_config"]["k8s_shared_storage"]
            else:
                self._system_info = "GLUSTERFS NOT Enabled"

        ## If CN-A Then Follow this Block
        else:
            conf_dict = ConfigStore.get_ncs_cna_conf()
            if conf_dict is None:
                self._system_info = "No {} file in system".format(DynamicPaths.bcmt_conf_path)
            else:
                if conf_dict["cluster_config"]["k8s_shared_storage"]:
                    gluster_flag = conf_dict["cluster_config"]["k8s_shared_storage"]
                else:
                    self._system_info = "GLUSTERFS NOT Enabled"
        #print (gluster_flag)
        return gluster_flag

class heketi_pod_value(glusterFsInstalledStatus):

    #### This class is inherited from BASE class
    #### Here we are checing HEKETI POD is running or not. Heketi is GLUSTER AGENT, which has to be run in all PEERs
    #### All other classes will Inherit this class

    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER]
    }

    #def heketi_pod_name(self):
    def get_heketi_pod_name(self):
        status_check=self.glusterFs_installed_or_not_status()

        if(status_check):
            stream=self.get_output_from_run_cmd("sudo /usr/local/bin/kubectl get pod -n ncms | grep -i 'heketi' | awk '{print $1}'")
            heketi_pod_name=stream.strip()
            self.heketi_pod_name=str(heketi_pod_name)
            #print ("inside class heketi_pod_value:" +str(self.heketi_pod_name))
            return self.heketi_pod_name

        else:
            self.heketi_pod_name=""
            return self.heketi_pod_name


    #def get_heketi_secret(self):
    def get_heketi_secret(self):
        status_check=self.glusterFs_installed_or_not_status()

        if(status_check):
            stream2=self.get_output_from_run_cmd("sudo /usr/local/bin/kubectl get secret -n ncms heketi-secret -o jsonpath=\'{.data.key}\'")
            heketi_secret=stream2.strip()

            #command="sudo /usr/bin/echo \"" + heketi_secret + "\" | base64 --decode"
            command="sudo /usr/bin/echo " + heketi_secret
            encoded_value=self.get_output_from_run_cmd(command).strip()
            mystr_decoded = decode_base_64(encoded_value)
            self.heketi_secret_decode=mystr_decoded
            return self.heketi_secret_decode
        else:
            self.heketi_secret_decode=""
            return self.heketi_secret_decode

    #def get_heketi_db_dump(self):
    def get_heketi_db_dump(self,heketi_pod_name,heketi_secret_decode):
        status_check=self.glusterFs_installed_or_not_status()

        if(status_check):
            command_string1="sudo /usr/local/bin/kubectl exec -it -n ncms "
            command_string2=heketi_pod_name
            command_string3=" -- /usr/bin/heketi_cli.py db dump --user admin --secret "
            command_string4=heketi_secret_decode
            command_string5=">heketi_db_orig_healthCheck.json"
            command_final=command_string1 + command_string2 + command_string3 + command_string4 + command_string5

            stream=self.get_output_from_run_cmd(command_final)
        else:
            pass

########    Validation  1: GLUSTER_FS all PEERS are connected or not #########
########    ClassName : gluser_peer_status


class GlusterPeerStatus(heketi_pod_value):
    objective_hosts = {
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.STORAGE],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.STORAGE]
    }

    def set_document(self):
        self._unique_operation_name = "gluser peer status"
        self._title = "gluster peer status"
        self._failed_msg = "Gluster Peers are not connected"
        self._severity = Severity.CRITICAL

        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.SYMPTOM]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        #print ("VALIDATION 1 :  gluser_peer_status Check")
        status_check=self.glusterFs_installed_or_not_status()

        if(status_check):
            stream=self.get_output_from_run_cmd("sudo /usr/sbin/gluster pool list")
            pool_list = stream.splitlines()
            total_peers = len(pool_list) -1
            i = 1
            connected_peers = 0
            for i in range(1,len(pool_list)):
                pool = pool_list[i].split("\t")
                pool_status = pool[2].strip()
                if (pool_status) == "Connected":
                    connected_peers = connected_peers + 1

            if int(total_peers) != int(connected_peers):
                self._failed_msg = self._failed_msg + "\n\n" + str(stream)
                return False
            else:
                return True
        else:
            return True

########    Validation  2: HEKETI PODS Replicas All Running or not #########
########    ClassName : heketi_pod_status

class heketi_pod_status(heketi_pod_value):
    objective_hosts = {
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "heketi pod status"
        self._title = "heketi pod status"
        self._failed_msg = "heketi pod NOT RUNNING."
        self._severity = Severity.CRITICAL

        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.SYMPTOM]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        status_check = self.glusterFs_installed_or_not_status()

        if status_check:
            cmd = "sudo /usr/local/bin/kubectl get deployment heketi --namespace ncms " \
                  "-o jsonpath=\'{.status.replicas}\'"
            stream = self.get_output_from_run_cmd(cmd)
            desired_pods_heketi = stream.strip()

            if not desired_pods_heketi:
                raise UnExpectedSystemOutput(self.get_host_ip(), cmd, desired_pods_heketi,
                                             "Expected to have out from cmd, pls check if heketi deployment is running")

            cmd = "sudo /usr/local/bin/kubectl get deployment heketi" \
                  " --namespace ncms -o jsonpath=\'{.status.availableReplicas}\'"
            stream = self.get_output_from_run_cmd(cmd)
            running_pods_heketi = stream.strip()

            if not running_pods_heketi:
                raise UnExpectedSystemOutput(self.get_host_ip(), cmd, running_pods_heketi,
                                             "Expected to have out from cmd, pls check if heketi deployment is running")

            if int(desired_pods_heketi) != int(running_pods_heketi):
                self._failed_msg = self._failed_msg + "\n" + "Desired Heketi pods = " + desired_pods_heketi + \
                                   " But Running Heketi pods = " + running_pods_heketi
                return False
            else:
                return True
        else:
            return True

########    Validation  3: HEKETI_DB Pending Operations exists or not #########
########    ClassName : heketi_db_pending_operation

class heketi_db_pending_operation(heketi_pod_value):
    objective_hosts = {
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "heketi_db_pending_operation"
        self._title = "heketi_db_pending_operation"
        self._failed_msg = "heketi_db pending_operations exist"
        self._severity = Severity.CRITICAL

        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.SYMPTOM]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        #print ("VALIDATION 3 STARTS:  heketi_db_pending_operation")
        status_check=self.glusterFs_installed_or_not_status()

        if (status_check):
            heketi_pod_name=self.get_heketi_pod_name()
            heketi_secret_decode=self.get_heketi_secret()
            self.get_heketi_db_dump(heketi_pod_name,heketi_secret_decode)

            #stream=self.get_output_from_run_cmd("sudo /usr/bin/cat heketi_db_orig_healthCheck.json | grep -i 'pendingoperations' | cut -d ':' -f2")

            stream=self.get_output_from_run_cmd("sudo /usr/bin/cat heketi_db_orig_healthCheck.json | grep -i 'pendingoperations'")

            a=str(stream).split(":")
            b=str(a[1])
            pending_operations=b.strip()

            matched = re.search(r".*{}*", pending_operations)
            is_match = bool(matched)

            if(is_match):
                return True
            else:
                self._failed_msg = self._failed_msg + "\n Pending operations = " + str(pending_operations)
                return False
        else:
            return True

########    Validation 4 : HEKETI_DB Inconsistency Check #########
########    ClassName : heketi_db_inconsistency_check

class heketi_db_inconsistency_check(heketi_pod_value):
    objective_hosts = {
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "heketi_db_inconsistency_check"
        self._title = "heketi_db_inconsistency_check"
        self._failed_msg = "heketi_db INCONSISTENCIES exist"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.SYMPTOM]

    def get_severity_from_json(self,db_status):
        if db_status=='device_inconsistency':
            self._implication_tags = [ImplicationTag.NOTE]
            return Severity.NOTIFICATION
        else:
            self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]
            return Severity.CRITICAL

    def is_validation_passed(self):
        #print ("VALIDATION 4 STARTS:  heketi_db_inconsistency_check")
        status_check=self.glusterFs_installed_or_not_status()

        if (status_check):
            pod_name=self.get_heketi_pod_name()
            command_string1="sudo /usr/local/bin/kubectl exec -it -n ncms "
            command_string2=pod_name
            #command_string3=" -- /usr/bin/heketi_cli.py db check |grep totalinconsistencies |cut -d':' -f2 "
            command_string3=" -- /usr/bin/heketi_cli.py db check "
            command_input= "{} {} {}".format(command_string1,command_string2,command_string3)
            commnad_output=self.get_output_from_run_cmd(command_input)
            convert_output_to_json=json.loads(commnad_output)
            if 'totalinconsistencies' in convert_output_to_json:
                totalinconsistencies=convert_output_to_json['totalinconsistencies']     #get the total inconsistency number
            #get all incosistency info in to a dictionary
            inconsistencies_info={}
            # verify the total inconsistency count is 0 or not
            if int(totalinconsistencies) != int(0):
                self._failed_msg = self._failed_msg + "\n" + "Total Inconsistencies = " + str(totalinconsistencies)
                for key in list(convert_output_to_json.keys()):
                    if key.strip() != 'totalinconsistencies':
                        if convert_output_to_json[key]['inconsistencies'] == None:
                            inconsistencies_info[key]=''
                        else:
                            inconsistencies_info[key]=convert_output_to_json[key]['inconsistencies']

                if len(inconsistencies_info) != 0 :
                    bricks = inconsistencies_info['bricks']
                    devices= inconsistencies_info['devices']
                    volumes= inconsistencies_info['volumes']
                    #identify only device inconsistency exists or not.
                    if devices != '' and  bricks == '' and volumes == '':
                        db_status='device_inconsistency'
                        self._failed_msg = self._failed_msg +"\n" + " ".join([str(i) for i in devices])
                        self._severity= self.get_severity_from_json(db_status)
                        return False
                    else:
                        db_status='inconsistency'
                        self._failed_msg = self._failed_msg +"\n" + " ".join([str(i) for i in devices]) +"\n" + " ".join([str(j) for j in volumes]) +"\n"+" ".join([str(k) for k in bricks])
                        self._severity= self.get_severity_from_json(db_status)
                        return False
            return True
        else:
            return True

########    Validation 5 : To check if any volumes need HEALING #########
########    ClassName : volume_heal_need_check

#############       Requirement     #############

# The self-heal daemon runs in the background and diagnoses issues
# with bricks and automatically initiates a self-healing process every 10 minutes on the files that require healing.
# To see the files that require healing, use: "gluster volume heal myvolume info"
# This command output should return NULL as We dont really want any volume which needs healing.

#######################################################

class VolumeHealNeedCheck(heketi_pod_value):
    objective_hosts = {
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.STORAGE],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.STORAGE]
    }

    NEED_HEAL_THRESHOLD = 50

    def set_document(self):
        self._unique_operation_name = "volume_heal_need_check"
        self._title = "volume_heal_need_check"
        self._failed_msg = "volume_heal_need_check Failed"
        self._severity = Severity.NOTIFICATION

        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.ACTIVE_PROBLEM]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        status_check = self.glusterFs_installed_or_not_status()

        if (status_check):
            stream1=self.get_output_from_run_cmd("sudo /usr/sbin/gluster volume list")
            gluster_volumes_list = stream1.split()

            volume_heal_info = []
            gluster_volumes_list_for_entries = []

            if len(gluster_volumes_list) > 0:
                for num in range(0, len(gluster_volumes_list)):
                    cmd_to_run="sudo /usr/sbin/gluster volume heal " + gluster_volumes_list[num] + " info | grep -i 'Number of entries:'"
                    stream2 = self.get_output_from_run_cmd(cmd_to_run, timeout=150)
                    line_split = stream2.splitlines()
                    for each_line in line_split:
                        each_line = each_line.strip()
                        if each_line:
                            volume_heal_info.append(each_line)
                            gluster_volumes_list_for_entries.append(gluster_volumes_list[num])

            if len(volume_heal_info) > 0:
                flg_is_pass = True
                for num in range(0, len(volume_heal_info)):
                    entries_num = volume_heal_info[num].split(':')[1].strip()
                    entries_num.replace('.', "")
                    if not entries_num.isnumeric():
                        flg_is_pass = False
                        self._severity = Severity.ERROR
                        self._failed_msg = self._failed_msg + "\n" + "Volume name: " +\
                                           gluster_volumes_list_for_entries[num] +\
                                           " has an issue - please check "
                    else:
                        if int(entries_num) > VolumeHealNeedCheck.NEED_HEAL_THRESHOLD:
                            flg_is_pass = False
                            self._severity = Severity.ERROR
                            self._failed_msg = self._failed_msg + "\n" + "Volume name: " + \
                                               gluster_volumes_list_for_entries[num] +\
                                               " | Healing or needs Healing -  " +\
                                               str(volume_heal_info[num])
                        elif int(entries_num) > 0:
                            flg_is_pass = False
                            self._failed_msg = self._failed_msg + "\n" + "Volume name: " + \
                                                gluster_volumes_list_for_entries[num] + \
                                                " | Healing or needs Healing -  " + \
                                                str(volume_heal_info[num])

            return flg_is_pass
        else:
            return True


########    Validation 6 : gluster_db_cluster_check #########
########    ClassName : gluster_db_cluster_check

class gluster_db_cluster_check(heketi_pod_value):
    objective_hosts = {
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "gluster_db_cluster_check"
        self._title = "gluster_db_cluster_check"
        self._failed_msg = "GlsuterFS Cluster does not exist in Heketi"
        self._severity = Severity.CRITICAL

        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.RISK_BAD_CONFIGURATION, ImplicationTag.SYMPTOM]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        status_check=self.glusterFs_installed_or_not_status()

        if (status_check):
            pod_name=self.get_heketi_pod_name()
            heketi_secret_decode=self.get_heketi_secret()
            self.get_heketi_db_dump(pod_name,heketi_secret_decode)

            stream4=self.get_output_from_run_cmd("sudo /usr/bin/cat heketi_db_orig_healthCheck.json| grep -i 'clusterentries'")
            cluster_entry=stream4.strip()

            x = re.search("}", cluster_entry)

            if x:
                # {} = means CLUSTER NAME NULL so wrong !!!!!
                self._failed_msg=self._failed_msg + " | " + str(cluster_entry)
                return False
            else:
                # IF no } it means CLUSTER NAME there .. so Good

                stream3=self.get_output_from_run_cmd ("sudo /usr/bin/cat heketi_db_orig_healthCheck.json| grep -i 'clusterentries' -A3| tail -1")

                a=stream3.split(":")
                b=a[1].strip()
                c=b.split(',')
                cluster_id=c[0].strip()

                cluster_id_from_json=re.sub('"', '', cluster_id)

                ## Lets try et the cluster name from CLI as well. cluster_id_from_CLI

                command_string1="sudo /usr/local/bin/kubectl exec -it -n ncms "
                command_string2=pod_name
                command_string3=" -- heketi_cli.py cluster list | head -2 | tail -1"

                command_final=command_string1 + command_string2 + command_string3

                try:
                    stream=self.get_output_from_run_cmd(command_final).strip()

                    a=stream.split(":")
                    b=a[1].strip()
                    c=b.split(' ')
                    d=c[0].strip()
                    cluster_id_from_CLI=d

                except:
                    return False

                if str(cluster_id_from_CLI) == str(cluster_id_from_json):
                    return True
                else:
                    self._failed_msg = self._failed_msg + "\n" + "Cluster ID from CLI = " + cluster_id_from_CLI + " | Cluster ID from JSON = " + cluster_id_from_json
                    return False
        return True


#####   Validation 7 | ICET-1448 | GlusterFS Heketi Mount points disk space check on storeage nodes  ######

class GlusterHeketiMountDiskSpaceValidation(heketi_pod_value):
    objective_hosts = {
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.STORAGE],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.STORAGE]
    }

    def set_document(self):
        self._unique_operation_name = "gluster_heketi_mount_diskspace_validation"
        self._title = "Gluster Heketi MountPoint DiskSpace Usage Validation"
        self._failed_msg = "Heketi mount point Disk space usage high more than 90%"
        self._severity = Severity.CRITICAL

        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.RISK_RESOURCE_CLEANING_RECOMMENDED,
                                  ImplicationTag.SYMPTOM]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]
        self._is_clean_cmd_info = True

    def is_prerequisite_fulfilled(self):
        return bool(self.glusterFs_installed_or_not_status())

    def is_validation_passed(self):
        cmd = "sudo gluster volume list"
        #collecting the heketi volumes list
        total_heketi_volumes = self.run_command_and_grep(cmd, "vol_")
        for volume in total_heketi_volumes:
            brick_name = []
            cmd = "sudo gluster volume info {}".format(volume)
            #collecting the brick_details for heketi volume
            bricks_in_heketi_volume = self.run_command_and_grep(cmd, "brick")
            for brick_details in bricks_in_heketi_volume:
                brick_path = brick_details.split(':')[2]
                name = brick_path.split("/")[-2]
                brick_name.append(name)
            size = []
            if len(brick_name) > 0:
            #Iterate over each brick for size details
                for brick in brick_name:
                    usage_details = self.run_command_and_grep("sudo df -Th", brick)
                    if len(usage_details) > 0:
                        for usage in usage_details:
                            usage = re.split(r'\s+', usage)
                            old_list = [usage[2], usage[3]]
                            new_list = []
                            for item in old_list:
                                if 'G' in str(item):
                                    item = item.replace('G', '').split(".")
                                    item = int(item[0]) * 1024
                                elif 'M' in str(item):
                                    item = item.replace('M', '').split(".")
                                    item = int(item[0])
                                new_list.append(item)
                            size.append(new_list)
                if len(size) > 0:
                    #sum the total available size and utilized size of a heketi volume for a node
                    sums = [sum(value) for value in zip(*size)]
                    utilized_percentage = (float(sums[1])/float(sums[0])) * 100
                    if int(utilized_percentage) > 90:
                        return False

        return True

class GlusterFSInvalidGFIDs(heketi_pod_value):
    objective_hosts = {
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.STORAGE],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.STORAGE]
    }

    heketi_dir_path = "/var/lib/heketi"

    def set_document(self):
        self._unique_operation_name = "glusterfs_invalid_gfids"
        self._title = "Invalid GlusterFS GFIDs"
        self._failed_msg = ""
        self._severity = Severity.CRITICAL

        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.SYMPTOM]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]
        self._is_clean_cmd_info = True

    def is_prerequisite_fulfilled(self):
        return bool(self.glusterFs_installed_or_not_status()) and self.file_utils.is_dir_exist(self.heketi_dir_path)

    def is_validation_passed(self):
        find_brick_path = "sudo find {} -name 'brick'".format(self.heketi_dir_path)
        output_brick_path = self.get_output_from_run_cmd(find_brick_path).strip().split("\n")
        invalid_gfid_list = []
        for brick_path in output_brick_path:
            gfid_cmd = "sudo find {}/.glusterfs/ -type f -links 1 | grep -v -e health -e indi".format(brick_path)
            return_code, out, err = self.run_cmd(gfid_cmd)
            if len(out) == 0:
                continue
            else:
                invalid_gfid_list.append(out)
        if len(invalid_gfid_list) > 0:
            self._failed_msg += "Below invalid GFIDs are present in the node:\n{}".format('\n'.join(invalid_gfid_list))
            return False
        return True


class StorageSpaceValidationBeforeRecovery(heketi_pod_value):
    objective_hosts = {
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_STORAGE],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_STORAGE]
    }

    def set_document(self):
        self._unique_operation_name = "gluster_storage_space_validation_before_recovery"
        self._title = "Gluster Storage space validation before recovery"
        self._failed_msg = "No enough storage space available to do node recovery"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.SYMPTOM]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_prerequisite_fulfilled(self):
        return bool(self.glusterFs_installed_or_not_status())

    def is_validation_passed(self):
        pod_name_cmd = "sudo kubectl get pods -l heketi=pod -nncms -o=jsonpath='{.items[*].metadata.name}'"
        pod_name = self.get_output_from_run_cmd(pod_name_cmd).strip()
        #Collecting the storage node space details from heketi topology info , sample output below
        #Id:50dfee8603fe66d2890284302638bb78   State:online    Size (GiB):199     Used (GiB):108     Free (GiB):91
        #Id:21821492d99541ee1328eb29f4cdac29   State:online    Size (GiB):199     Used (GiB):103     Free (GiB):96
        #Id:e3ce51d14120c19444b3dc8885656dd7   State:online    Size (GiB):199     Used (GiB):5       Free (GiB):194

        cmd = "sudo kubectl exec -it {} -n ncms --  heketi_cli.py topology info | grep Free".format(pod_name)
        out = self.get_output_from_run_cmd(cmd).strip().split("\n")
        used_list = []
        free_list = []
        for used in out:
            if ("Used (GiB):" and "Free (GiB):") not in used:
                raise UnExpectedSystemOutput(self.get_host_ip(), cmd, out, message="Output should be in GiB but not found")
            used_start = used.find("Used (GiB):") + len("Used (GiB):")
            used_end = used.find("Free (GiB):")
            used = int(used[int(used_start):int(used_end)].strip())
            used_list.append(used)

        for free in out:
            free_start = free.find("Free (GiB):") + len("Free (GiB):")
            free = int(free[int(free_start):].strip())
            free_list.append(free)

        flg_has_space = True
        # Validating for each item in used_list to see other nodes free space is sufficient to accommodate
        for used in range(len(used_list)):
            if flg_has_space:
                sum_of_available_space = sum(free_list) - free_list[used]
                if not (sum_of_available_space > used_list[used]):
                    flg_has_space = False
            if not flg_has_space:
                return False
        return True
