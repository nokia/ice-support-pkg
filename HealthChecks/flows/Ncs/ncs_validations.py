from __future__ import absolute_import

# from unittest import result
from tools.python_utils import PythonUtils
import tools.sys_parameters as globals
from tools import adapter
import tools.sys_parameters as sys_parameters
import tools.global_logging as gl
from HealthCheckCommon.validator import Validator, InformatorValidator
from tools.ConfigStore import ConfigStore
from tools.EnvironmentInfo import *
from HealthCheckCommon.operations import *
import re
from six.moves import range


class RedisContainerCheck(Validator):

    def get_redis_container_password(self):
        cluster_name = sys_parameters.get_cluster_name()
        error_msg = ""
        ncs_version = sys_parameters.get_version()
        output = None
        docker_or_podman = adapter.docker_or_podman()
        ps_cmd = "sudo /usr/bin/{} ps --format '{{{{.Names}}}}' | grep redis".format(docker_or_podman)
        stream = self.get_output_from_run_cmd(ps_cmd).split()
        if "redis" in stream:
            if Version.V22_7 >= ncs_version > Version.V20_FP2:
                exec_cmd = "sudo {docker_or_podman} exec {stream} redis-cli -n 7 hmget 'cbis:ncs:cluster:{cluster_name}'\
                 'admin_pwd'".format(docker_or_podman=docker_or_podman, stream=stream[0], cluster_name=cluster_name)
                output = self.get_output_from_run_cmd(exec_cmd, add_bash_timeout=True).strip()
            elif ncs_version >= Version.V22_12:
                find_credis_path_cmd = 'sudo find /usr/lib/ -name "credis.py"'
                output_credis_path_cmd = self.get_output_from_run_cmd(find_credis_path_cmd)
                output_credis_path_cmd = output_credis_path_cmd.split()[0].strip()
                exec_cmd = "sudo python {credis_path_cmd} --db 7 --cmd hget " \
                           "cbis:ncs:cluster:{cluster_name} admin_pwd".format(credis_path_cmd=output_credis_path_cmd,
                                                                              cluster_name=cluster_name)

                # exec_cmd = "sudo python /usr/lib/python2.7/site-packages/cbis_common/credis.py --db 7 --cmd hget " \
                #           "cbis:ncs:cluster:{cluster_name} admin_pwd".format(cluster_name=cluster_name)
                output = self.get_output_from_run_cmd(exec_cmd).strip()
        else:
            error_msg = "No redis container found"

        return output, error_msg


class RedisLoginDataCollector(DataCollector):
    objective_hosts = [Objectives.ONE_MASTER]

    def collect_data(self, **kwargs):
        self._is_clean_cmd_info = True
        if PythonUtils.is_ipv6(kwargs['external_ip']):
            external_ip_string = "[{}]".format(kwargs['external_ip'])
        else:
            external_ip_string = kwargs['external_ip']

        final_cmd = "ncs config set --endpoint=https://{external_ip}:{port}/ncm/api/v1;ncs user login --username {username} --password '{password}'".format(external_ip=external_ip_string, port=kwargs['port'], username=kwargs['username'],password=kwargs['password'])

        out = self.get_output_from_run_cmd(final_cmd)
        return out


class RedisPasswordSyncCheck(RedisContainerCheck):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MANAGER]
    }

    def set_document(self):
        self._unique_operation_name = "redis_password_sync_check"
        self._title = "Check sync of redis password"
        self._failed_msg = "ncs-admin password is not in sync with redis"
        self._severity = Severity.CRITICAL
        self._details = ""
        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.ACTIVE_PROBLEM]
        self._is_clean_cmd_info = True
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        username = "ncs-admin"
        password, error_msg = self.get_redis_container_password()
        conf_dict = ConfigStore.get_ncs_bm_conf()
        external_ip = conf_dict["cluster_external_vip"]
        port = conf_dict["cluster_deployment"]["cluster_config"]["bcmt_portal_port"]
        if sys_parameters.get_version() >= Version.V24_7:
            port = '8082'
        if password != "" and error_msg == "":
            out = self.get_first_value_from_data_collector(RedisLoginDataCollector, external_ip=external_ip, port=port,
                                                           username=username,
                                                           password=password)
            if 'Login successfully' in out:
                gl.log_and_print("redis is in synced")
                return True
            else:
                gl.log_and_print("redis not in synced")
                self._details = "Failed to run command 'ncs config set --endpoint=https://{external_ip}:{port}/ncm/api/v1;ncs user login --username " \
                                "{username} --password REDIS_PASSWORD':\n{cmd_out}".format(external_ip=external_ip,
                                                                                           port=port,
                                                                                           username=username,
                                                                                           cmd_out=out)
                return False
        else:
            gl.log_and_print(error_msg)
            return False


class CheckSymLink(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MANAGER]
    }

    def set_document(self):
        self._unique_operation_name = "check_sym_link"
        self._title = "Check symbolic link for dir in /var/log/cbis and /var/log/cbis_services"
        self._failed_msg = ""
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def verify_symlink_for_source_file(self, cmd, file_path, container_name=''):
        status, out, err = self.run_cmd(cmd, add_bash_timeout=True)
        if status != 0:
            if container_name:
                self._failed_msg += "Failed to get {} file in {} container.\n".format(file_path, container_name)
                return False
            self._failed_msg += "Failed to get {} file.\n".format(file_path)
            return False
        if self.file_utils.symbolic_link_present_or_absent(out):
            return True
        if container_name:
            self._failed_msg += "Sym link doesn't exist for {} in {} container.\n".format(file_path, container_name)
            return False
        self._failed_msg += "Sym link doesn't exist for {} file.\n".format(file_path)
        return False

    def is_validation_passed(self):
        link_files = ['cbis_services', 'cbis']
        symlink_missing_files = []
        for file_name in link_files:
            file_path = os.path.join("/var/log/", file_name)
            cmd = 'sudo ls -l {}'.format(file_path)
            if not self.verify_symlink_for_source_file(cmd, file_path):
                symlink_missing_files.append(file_name)
        if len(symlink_missing_files) > 0:
            return False
        return True


class CheckManagerPort(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.MANAGERS]
    }

    def set_document(self):
        self._unique_operation_name = "check_ncsmanager_port"
        self._title = "Verify NCS Manager port is not used by other process"
        self._failed_msg = ""
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        result = True
        # NCS releases 23.10 uses port 8001 NCSDEV-7807, NCS 24.7 uses port 8002
        port = 8000
        return_code, out, err = self.run_cmd('sudo cat /root/cbis/version_conf.yaml')
        if return_code == 0:
            ncs_manager_port_per_version = PythonUtils.yaml_safe_load(out, file_path='/root/cbis/version_conf.yaml')['releases']
            ncs_version = Version.get_version_name(sys_parameters.get_version())
            for section in ncs_manager_port_per_version:
                if ncs_version in section['release_version']:
                    port = section.get('cbis_manager_port')
        port_cmd = "sudo netstat -tulpn | grep ':{} '".format(port)
        status, out, err = self.run_cmd(port_cmd, add_bash_timeout=True)
        if status != 0:
            self._failed_msg += "NCS Manager service not running\n"
            result = False
        else:
            proc1 = str(out.split()[-1:]).split('/')[0]
            proc = proc1.lstrip("[").lstrip("'").lstrip("u'")
            proc_cmd = "ps --no-headers -p {}".format(proc)
            proc_output = self.get_output_from_run_cmd(proc_cmd).strip()
            if 'gunicorn' in proc_output:
                result = True
            else:
                self._failed_msg += "Port {} is used by non NCS Manager process {}\n".format(port, proc_output)
                result = False
        return result


class CheckManagerContainers(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.MANAGERS]
    }

    def set_document(self):
        self._unique_operation_name = "check_ncsmanager_containers"
        self._title = "Verify NCS manager containers are running"
        self._failed_msg = ""
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def get_manager_container_list(self):
        containers_base_name = ['cbis_manager', 'cbis_conductor', 'cbis_websocket', 'nginx',
                                'redis']
        verified_running_manager_container_name_list = []
        verified_not_running_manager_container_name_list = []
        docker_or_podman = adapter.docker_or_podman()
        for container in containers_base_name:
            cmd = "sudo /usr/bin/{} ps --format '{{{{.Names}}}}'".format(docker_or_podman)
            pattern_to_grep = container
            manager_containers_name = self.run_command_and_grep(cmd, pattern_to_grep)
            if not manager_containers_name:
                verified_not_running_manager_container_name_list.append(container)
            else:
                for manager_container_name in manager_containers_name:
                    verified_running_manager_container_name_list.append(manager_container_name)
        return verified_running_manager_container_name_list, \
               verified_not_running_manager_container_name_list

    def is_manager_container_healthy(self, container_name):
        docker_or_podman = adapter.docker_or_podman()
        status_cmd = "sudo /usr/bin/{} inspect --format '{{{{.State.Running}}}}' {}".format(docker_or_podman,
                                                                                            container_name)
        health_cmd = "sudo /usr/bin/{} inspect --format '{{{{.State.Healthcheck.Status}}}}' {}".format(docker_or_podman,
                                                                                                       container_name)
        status = self.run_cmd(status_cmd)
        health = self.run_cmd(health_cmd)
        if 'false' in status or 'unhealthy' in health:
            return False
        else:
            return True

    def check_all_manager_containers(self):
        running_manager_containers, not_running_manager_containers = self.get_manager_container_list()
        containers_verified_unhealthy = []
        containers_verified_not_running = not_running_manager_containers
        for manager_container in running_manager_containers:
            result = self.is_manager_container_healthy(manager_container)
            if not result:
                containers_verified_unhealthy.append(manager_container)
        return containers_verified_unhealthy, containers_verified_not_running

    def is_validation_passed(self):
        result_unhealthy, result_not_running = self.check_all_manager_containers()
        unhealthy = False
        not_running = False
        if len(result_unhealthy) > 0:
            self._failed_msg += "Not healthy NCS manager container: {}".format(result_unhealthy)
            unhealthy = True
        if len(result_not_running) > 0:
            self._failed_msg += "Not running NCS manager container: {}".format(result_not_running)
            not_running = True
        if not_running or unhealthy:
            return False
        else:
            return True


class SecurityPatchValidation(InformatorValidator):
    objective_hosts = {
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.MASTERS]
    }

    def set_document(self):
        self._is_pure_info = True
        self._unique_operation_name = 'security_patch_validation'
        self._title_of_info = 'Security Patch Details'
        self._system_info = ""

    def get_system_info(self):
        cmd = "sudo yum list |grep -i BCMT-EXTRA |wc -l"
        out = self.get_output_from_run_cmd(cmd)
        if int(out) > 1:
            # 15 yum packages are getting updated in SU1 with BCMT-EXTRA tag
            if int(out) == 15:
                return "NCS20FP2SU1 Security patch is applied."
            # 24 yum packages are getting updated in SU2 with BCMT-EXTRA tag
            if int(out) == 24:
                return "NCS20FP2SU2 Security patch is applied."
            # 59 yum packages are getting updated in SU4 with BCMT-EXTRA tag
            if int(out) == 59:
                return "NCS20FP2SU4 Security patch is applied."
            # If return value more than 1 and not matching any above value, we have to check manually for SU details.
            else:
                return "Security patch is applied"
        else:
            return "No Security patch is applied."


class VerifyCertificate(Validator):
    def verify_cert(self, ca, cert):
        if not self.file_utils.is_file_exist(cert):
            self._failed_msg = "Could not find cert: {}".format(cert)

            return False

        if not self.file_utils.is_file_exist(ca):
            self._failed_msg = "Could not find CA: {}".format(ca)

            return False

        cmd = "sudo openssl verify -CAfile {} {}".format(ca, cert)
        return_code, out, err = self.run_cmd(cmd)

        if return_code != 0:
            return False
        parts = out.split(':')
        ok_value = parts[-1].strip()

        if ok_value == "OK":
            return True
        else:
            return False


class CheckCertificateCommonName(VerifyCertificate):
    objective_hosts = {Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER]}

    def set_document(self):
        self._unique_operation_name = "Check_Certificate_Common_Name"
        self._title = "Check common name of the certificate should be cluster name"
        self._failed_msg = "Certificate Common Name is not the name of cluster"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.ACTIVE_PROBLEM]
        self._is_clean_cmd_info = True

    def is_validation_passed(self):
        crt1 = "/etc/pki/ca-trust/source/anchors/ca.crt.pem"
        crt2 = "/etc/pki/tls/private/overcloud_endpoint.pem"

        return self.verify_cert(crt1, crt2)


class VerifySecretCertETCDCert(Validator):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._unique_operation_name = "Verify_SecretCert_ETCDCert"
        self._title = "Verify Common Name should be matching cluster name"
        self._failed_msg = "Certificate Common Name is not Cluster Name"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.ACTIVE_PROBLEM]
        self._is_clean_cmd_info = True

    def is_validation_passed(self):
        cmd = "sudo kubectl get secret etcd-client-certs -n ncms --template='{{index .data \"ca.pem\"}}' | base64 -d"
        etcd_cert = str(self.get_output_from_run_cmd(cmd).strip())
        cmd1 = "sudo  cat /etc/kubernetes/ssl/ca.pem"
        ca_pem = str(self.get_output_from_run_cmd(cmd1).strip())
        if etcd_cert == ca_pem:
            return True
        else:
            return False


class CertificateVerifyCA(VerifyCertificate):
    objective_hosts = {Deployment_type.NCS_OVER_BM: [Objectives.MASTERS]}

    def set_document(self):
        self._unique_operation_name = "Certificate_Verify_CA"
        self._title = "Certificate CA Verification"
        self._failed_msg = "Certificate CA Verification failed"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.ACTIVE_PROBLEM]
        self._is_clean_cmd_info = True

    def is_validation_passed(self):
        k8s_root_CA = "/etc/kubernetes/ssl/ca.pem"
        CA_Bundle_file = "/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem"
        CA_trust_anchors_file = "/etc/pki/ca-trust/source/anchors/ca.crt.pem"
        endpoint_pem_file = "/etc/pki/tls/private/overcloud_endpoint.pem"

        ca1_valid = self.verify_cert(CA_Bundle_file, k8s_root_CA)
        ca2_valid = self.verify_cert(CA_trust_anchors_file, endpoint_pem_file)

        if ca1_valid and ca2_valid:
            return True

        return False


class RedisActiveOperationsCheck(Validator):
    objective_hosts = [Objectives.ONE_MANAGER]

    def set_document(self):
        self._unique_operation_name = "check_manager_redis_active_operations"
        self._title = "Check Manager Redis Active Operations"
        self._failed_msg = ""
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.ACTIVE_PROBLEM]

    def get_all_redis_operation_status(self):
        ncs_version = sys_parameters.get_version()
        cluster_name = sys_parameters.get_cluster_name()
        docker_or_podman = adapter.docker_or_podman()
        if ncs_version > Version.V20_FP2:
            cmd = "sudo {} exec -it redis redis-cli -n 7 hgetall general:{}:is_active.yaml".format(docker_or_podman,
                                                                                                   cluster_name)
            out = self.get_output_from_run_cmd(cmd, add_bash_timeout=True)
        else:
            cmd = "sudo cat /opt/install/data/general/is_active.yaml"
            out = self.get_output_from_run_cmd(cmd)
        return out

    def get_redis_active_operations(self):
        ncs_version = sys_parameters.get_version()
        redis_operations = self.get_all_redis_operation_status()
        active_operations_status_dict = {}
        if ncs_version > Version.V20_FP2:
            redis_operations_list = redis_operations.split("\n")

            for i in range(0, len(redis_operations_list) - 1, 2):
                operation = redis_operations_list[i].split(") \"")[1].strip('"\\r')
                state = redis_operations_list[i + 1].split(") \"")[1].strip('"\\r')

                if not re.search(r'\bactive\b',state):  ## NOT matched with "inactive" or "failed" so "if not false" says true
                    continue
                else:  ## re.search(r'\bactive\b', state) Matched with "active"
                    active_operations_status_dict[operation] = state
        else:
            operations_and_statuses = re.findall(r'(\w+): (\w+)', redis_operations)
            for operation_and_status in operations_and_statuses:
                operation = operation_and_status[0]
                state = operation_and_status[1]

                if not re.search(r'\bactive\b', state):
                    continue
                else:
                    active_operations_status_dict[operation] = state

        return active_operations_status_dict

    def is_validation_passed(self):
        active_operations = self.get_redis_active_operations()
        active_operations_count = len(active_operations)
        CAN_BE_IGNORED_FLAG = 0
        for key, value in list(active_operations.items()):
            match = re.search(".*cluster_bm_health_check.*", key)
            if match:
                CAN_BE_IGNORED_FLAG = 1

        ## IF Only one ACTIVE Operation is there and That is "cluster_bm_health_check" operation then its not an Error so return TRUE

        if active_operations_count == 0:
            return True
        elif active_operations_count == 1 and CAN_BE_IGNORED_FLAG == 1:
            return True
        else:
            self._failed_msg += "Found NCS operations in Active state: {}".format(active_operations)
            return False


class CheckResourceLimitsOfBcmtCitmIngress(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "check_resource_limits_of_bcmt_citm_ingress"
        self._title = "Check resource limits of bcmt citm ingress"
        self._failed_msg = "It is just a Notification. bigger images( > ~1.5 Gb) upload to harbor might fail becuase of current limits of bcmt-citm_ingress pods with memory as {}Gb and cpu as {}m. please ignore this check if you don't have any issue with image uploading. if u have issue with image uploading, please refer to confluence"
        self._severity = Severity.NOTIFICATION
        self._implication_tags = [ImplicationTag.NOTE, ImplicationTag.APPLICATION_DOMAIN]

    def is_validation_passed(self):
        cmd = "sudo kubectl get daemonsets -n ncms bcmt-citm-ingress " \
              "-o jsonpath='{.spec.template.spec.containers[0].resources}'"
        out = self.get_output_from_run_cmd(cmd)
        out_json = json.loads(out)

        if "limits" not in out_json:
            return True

        mem = out_json["limits"].get("memory", "").replace("Gi", "")
        cpu = out_json["limits"].get("cpu", "").replace("m", "")

        try:
            mem_limit = int(mem)
            cpu_limit = int(cpu)
        except ValueError:
            self._failed_msg = "Failed to parse cpu and memory limits"
            return False

        if mem_limit > 1 and int(cpu_limit) > 300:
            return True

        self._failed_msg = self._failed_msg.format(mem_limit, cpu_limit)

        return False


class CheckLDAPConnectivity(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER],
        Deployment_type.NCS_OVER_VSPHERE: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._unique_operation_name = "check_ldap_connectivity"
        self._title = "check LDAP connectivity in NCS"
        self._failed_msg = "There is something wrong in LDAP connectivity!!"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION]
        self._is_clean_cmd_info = True

    def is_prerequisite_fulfilled(self):
        return self.read_sssd_conf()

    def read_sssd_conf(self):
        file_path = "/etc/sssd/sssd.conf"
        file_lines = self.file_utils.get_lines_in_file(file_path)
        if file_lines:
            ldap_uri = None
            ldap_default_bind_dn = None
            ldap_default_authtok = None
            for line in file_lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith("ldap_uri"):
                    ldap_uri = line.split('=', 1)[1].strip().rstrip(',')
                elif line.startswith("ldap_default_bind_dn"):
                    ldap_default_bind_dn = line.split('=', 1)[1].strip()
                elif line.startswith("ldap_default_authtok"):
                    ldap_default_authtok = line.split('=', 1)[1].strip()

            return ldap_uri, ldap_default_bind_dn, ldap_default_authtok

    def is_validation_passed(self):
        ldap_uri, ldap_default_bind_dn, ldap_default_authtok = self.read_sssd_conf()
        if ldap_uri and ldap_default_authtok and ldap_default_authtok:
            command = "ldapwhoami -H {} -D {} -w {}".format(ldap_uri, ldap_default_bind_dn, ldap_default_authtok)
            try:
                self.run_cmd(command, add_bash_timeout=True)
            except UnExpectedSystemTimeOut:
                self._failed_msg += " Kindly check LDAP configuration!!"
                return False
            return True
        else:
            return False


class PreUpgradeNotification(Validator):
    objective_hosts = [Objectives.ONE_MANAGER]

    def set_document(self):
        self._unique_operation_name = "pre_upgrade_notification"
        self._title = "Pre upgrade notification for this version (22.7)"
        self._failed_msg = "Note: It's critical to check the attached link before proceeding with the NCS upgrade.\n****This validation is primarily for the attached document.****"
        self._severity = Severity.NOTIFICATION
        self._implication_tags = [ImplicationTag.NOTE, ImplicationTag.PRE_OPERATION]

    def is_validation_passed(self):
        return False


class CheckWebsocketProcessCount(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.MANAGERS]
    }

    def set_document(self):
        self._unique_operation_name = "check_websocket_process_count"
        # Checking whether cbis_websocket process count is high as described in NCSFM-9611
        self._title = "Check cbis_websocket process count"
        self._failed_msg = ""
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):
        result = True
        cmd = '/usr/bin/ps -ef --no-headers| grep cbis_websocket | wc -l'
        status, out, err = self.run_cmd(cmd, add_bash_timeout=True)
        if status != 0:
            self._failed_msg += "Failed to get output of {}\n".format(cmd)
            result = False
        else:
            if int(out) <= 10:
                pass
            else:
                result = False
                self._failed_msg += "cbis_websocket process count is high"
        return result


class BcmtImageMatchingNCSVersion(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER]}
    checksums = "flows/Ncs/checksums.json"
    with open(checksums) as json_file:
        ncs_images_checksums = json.load(json_file)

    def set_document(self):
        self._unique_operation_name = "check_bcmt_image_correct_for_ncs_version"
        self._title = "Check if bcmt image used in cluster deployment is correct for ncs version GA"
        self._failed_msg = "BCMT image used in cluster deployment is not for NCS version GA"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def get_image_checksum(self, image):
        cmd = "sudo /usr/local/bin/kubectl get pod -n ncms | grep -i 'bcmt-api' | grep -i 'Running'"
        bcmt_api_pod_output = self.get_output_from_run_cmd(cmd).strip()
        bcmt_api_pod_array = bcmt_api_pod_output.split()
        bcmt_api_pod = bcmt_api_pod_array[0].strip()
        main_command = "sudo /usr/local/bin/kubectl exec -n ncms {}".format(bcmt_api_pod)
        openstack_command = "  image show {} -c checksum -f value".format(image)
        command_to_be_run = self.get_openstack_api_command(main_command, openstack_command)
        command_output = self.get_output_from_run_cmd(command_to_be_run).strip()
        return command_output

    def get_image_name(self):
        cluster_data = sys_parameters.get_ncs_cna_user_conf()
        image = cluster_data["Clusters"]["cluster-01"]["target_vms"]["group_01"]["image_uuid_or_name"]
        return image

    def is_validation_passed(self):
        image_checksum = self.get_image_checksum(self.get_image_name())
        cmd_version = "ncs -v"
        output = self.get_output_from_run_cmd(cmd_version).strip()
        match = re.search(r"\b(\d+\.\d+(?:\.\d+)?(?:-\d+)?)\b", output)
        ncs_version = match.group(0)
        if image_checksum == self.ncs_images_checksums.get(ncs_version):
            return True
        else:
            self._failed_msg += "\nWrong image used for the cluster deployment ncs_version: {}, image checksum should be: {}, current checksum: {}\n".format(
                ncs_version, self.ncs_images_checksums.get(ncs_version), image_checksum)
            return False


class CheckRedundantDirectivesInResolvConf(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.MASTERS]
    }

    def set_document(self):
        self._unique_operation_name = "check_redundant_directives_in_resolv_conf"
        self._title = "check whether redundant search directives exists in dns resolv.conf"
        self._failed_msg = "Please check the search directives in /etc/resolv.conf. "
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.RISK_BAD_CONFIGURATION, ImplicationTag.APPLICATION_DOMAIN]

    def is_validation_passed(self):
        dns_cmd = "grep -w '^search' /etc/resolv.conf"
        dns_cmd_out = self.get_output_from_run_cmd(dns_cmd)
        dns_cmd_strip = to_unicode(dns_cmd_out).strip().splitlines()
        if len(dns_cmd_strip) == 1:
            dns_cmd_out_split = dns_cmd_out.split()
            expected_params = ['bcmt', 'cluster.local']
            actual_params = dns_cmd_out_split[1:]
            extra_params = []
            count = 0
            for param in actual_params:
                if param not in expected_params:
                    extra_params.append(param)
                else:
                    count += 1
            if count == len(expected_params) and len(extra_params) == 0:
                return True
            else:
                self._failed_msg = self._failed_msg + 'by default only will have bcmt and cluster.local as domains. Please check these domains:{}'.format(
                    extra_params)
                self._severity = Severity.NOTIFICATION
                return False
        else:
            self._failed_msg = self._failed_msg + ' There should only be one search directive'
            return False


class ValidateTunedProfile(Validator):
    objective_hosts = [Objectives.WORKERS, Objectives.EDGES]

    def set_document(self):
        self._unique_operation_name = "verify_active_tuned_profile"
        self._title = "Verify if correct tuned profile is active in Worker and Edge NCS nodes"
        self._failed_msg = ""
        self._severity = Severity.NOTIFICATION
        self._implication_tags = [ImplicationTag.NOTE]
        self._is_clean_cmd_info = True

    def is_validation_passed(self):
        # list of valid tuned profiles in NCS
        valid_tuned_profiles = ["throughput-performance", "cpu-partitioning", "virtual-host"]
        return_code, out, err = self.run_cmd('sudo tuned-adm active')
        if return_code != 0:
            raise UnExpectedSystemOutput(ip=self.get_host_ip(), cmd="", output=err,
                                         message="Failed to check active tuned profile")
        else:
            current_tuned_profile_name = out.strip().split(":")[-1].strip().replace("\\n", "")
            if current_tuned_profile_name in valid_tuned_profiles:
                return True
            else:
                self._failed_msg += "Current Tuned profile set on this node is not matching with recommended tuned profile."
                return False


class GenOpensslCnfFileExists(Validator):
    objective_hosts = {Deployment_type.NCS_OVER_BM: [Objectives.MANAGERS]}

    def set_document(self):
        self._unique_operation_name = "check_openssl_cnf_file_exists"
        self._title = "Check gen_openssl_cnf.sh file exists"
        self._failed_msg = ""
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.SYMPTOM]

    def is_validation_passed(self):
        filename = "/usr/share/cbis/undercloud/tools/gen_openssl_cnf.sh"
        is_gen_openssl_cnf_file_exists = self.file_utils.is_file_exist(filename)
        if is_gen_openssl_cnf_file_exists:
            return True
        self._failed_msg += filename + ' file is missing'
        return False


class ValidateLogrotateTimerEnabledActive(Validator):
    objective_hosts = [Objectives.ALL_NODES]

    def set_document(self):
        self._unique_operation_name = "validate_logrotate_timer_enabled_active"
        self._title = "Validate Logrotate.timer is enabled and active"
        self._failed_msg = "Logrotate.timer is not enabled or active"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]

    def is_validation_passed(self):

        if self.run_cmd_return_is_successful("sudo systemctl is-enabled logrotate.timer"):
            return self.run_cmd_return_is_successful("sudo systemctl is-active logrotate.timer")
        else:
            return False



class GetIrqServiceStatus(DataCollector):
    objective_hosts = {Deployment_type.NCS_OVER_BM: [Objectives.EDGES, Objectives.WORKERS]}

    def collect_data(self):
        services = ["irqbalance.service", "cbis-irq-pinning.service"]
        status_dict = {}

        cmd = "systemctl list-unit-files | grep irq"
        out = self.get_output_from_run_cmd(cmd).strip().splitlines()
        available_irq_status = {}
        for line in out:
            parts = line.split()
            available_irq_status[parts[0].strip()] = parts[1].strip()

        for service in services:
            status_dict[service] = available_irq_status.get(service, "disabled")

        return status_dict


class IrqServiceValidator(Validator):
    objective_hosts = {Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER]}

    def set_document(self):
        self._unique_operation_name = "irq_service_match_config"
        self._title = "Verify IRQ Service Matches System Configuration"
        self._failed_msg = "Mismatch found between IRQ service status and system configuration:\n"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.PRE_OPERATION, ImplicationTag.PERFORMANCE]
        self._blocking_tags = [BlockingTag.UPGRADE, BlockingTag.SCALE]


    def is_validation_passed(self):
        system_config = ConfigStore.get_ncs_bm_conf()
        hosts_irq = self.run_data_collector(GetIrqServiceStatus)
        service_map = {"linux": "irqbalance.service", "custom-numa": "cbis-irq-pinning.service"}

        is_passed = True

        for host in hosts_irq:
            irq_mode = self.get_irq_mode(system_config, host)
            expected_service = service_map.get(irq_mode, None)

            if expected_service is None:
                self._severity = Severity.NOTIFICATION
                self._blocking_tags = []
                self._failed_msg = "unsupported irq_pinning_mode {} found for host {} validation won't run correctly".format(irq_mode, host)
                return False

            enabled_services = [service for service, status in hosts_irq[host].items() if status == "enabled"]

            if expected_service not in enabled_services:
                is_passed = False
                self._failed_msg += "Host {host} should have {expected_service} enabled.\n".format(host=host, expected_service=expected_service)

            for service in enabled_services:
                if service != expected_service:
                    is_passed = False
                    self._failed_msg += "Host {host} has unexpected service {service} enabled, only {expected_service} should be enabled.\n".format(host=host, service=service, expected_service=expected_service)

        return is_passed

    def get_irq_mode(self, data, host_name):
        keys_list = ['hosts', host_name, 'hieradata', 'my_host_group']
        data = self.find_value(data, keys_list)
        return data.get('cbis::my_host_group::irq_pinning_mode', None)


    def find_value(self, data, keys_list):
        value_dict = data
        for key in keys_list:
            value_dict = value_dict.get(key, {})
        return value_dict


class BcmtVrrpSecurityGroupValidation(Validator):
    objective_hosts = {
        Deployment_type.NCS_OVER_OPENSTACK: [Objectives.ONE_MASTER]}

    def set_document(self):
        self._unique_operation_name = "check_vrrp_protocol_112_allowed"
        self._title = "Validate VRRP (IP protocol 112) allowed in Openstack Security Groups"
        self._failed_msg = "VRRP (IP protocol 112) ingress rule is missing in OpenStack security groups"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]
        self._is_clean_cmd_info = True

    def is_prerequisite_fulfilled(self):
        # If there are no VIP groups to check, then no need to validate this check
        output = self.get_output_from_run_cmd(
            "sudo /usr/local/bin/kubectl get virtualipinstancegroup -A --no-headers |wc -l"
        ).strip()
        return int(output) > 0

    # -------------------
    # bcmt helper command to run openstack cli
    # -------------------
    def get_bcmt_exec_cmd(self):
        cmd = "sudo /usr/local/bin/kubectl get pod -n ncms | grep -i 'bcmt-api' | grep -i 'Running'"
        bcmt_api_pod_output = self.get_output_from_run_cmd(cmd).strip()
        if not bcmt_api_pod_output:
            raise UnExpectedSystemOutput(ip=self.get_host_ip(), cmd=cmd, output="No running bcmt-api pod found")
        bcmt_api_pod_name = bcmt_api_pod_output.split()[0].strip()
        bcmt_exec_cmd = "sudo /usr/local/bin/kubectl exec -n ncms {}".format(bcmt_api_pod_name)
        return bcmt_exec_cmd

    def run_openstack_cmd(self, os_cmd):
        bcmt = self.get_bcmt_exec_cmd()
        full_cmd = self.get_openstack_api_command(bcmt, os_cmd)
        return self.get_output_from_run_cmd(full_cmd).strip()

    # -----------------------------
    # Get VIP InstanceGroup names
    # -----------------------------
    def get_virtualipinstancegroups(self):
        output = self.get_output_from_run_cmd(
            "sudo /usr/local/bin/kubectl get virtualipinstancegroup -A --no-headers"
        ).strip()

        names = []
        namespaces = []

        for line in output.splitlines():
            parts = line.split()
            if len(parts) < 2:
                continue
            namespaces.append(parts[0])
            names.append(parts[1])

        return names, namespaces

    # -----------------------------
    # Validate VRRP state per group
    # -----------------------------
    def validate_vrrp_state(self, group_json):
        states = []
        for entry in group_json.get("status", {}).get("vrrpState", []):
            state = entry.get("state")
            if state:
                states.append(state)

        TOTAL_STATE_COUNT = len(states)
        ACTIVE_COUNT = states.count("ACTIVE")
        STANDBY_COUNT = states.count("STANDBY")
        UNKNOWN_COUNT = states.count("UNKNOWN")

        # 1.  Single-Node Case
        if TOTAL_STATE_COUNT == 1:
            return ACTIVE_COUNT == 1

        # 2.  Multi-Node Case
        if TOTAL_STATE_COUNT > 1:
            # Split Brain (All Active) , bad
            if ACTIVE_COUNT == TOTAL_STATE_COUNT:
                return False

            # all standby, bad
            if STANDBY_COUNT == TOTAL_STATE_COUNT:
                return False

            # all unknown, bad
            if UNKNOWN_COUNT == TOTAL_STATE_COUNT:
                return False

            # GOOD state
            if ACTIVE_COUNT == 1 and STANDBY_COUNT == (TOTAL_STATE_COUNT - ACTIVE_COUNT):
                return True

        return False

    # -----------------------------
    # Get nodes for a VIP group
    # -----------------------------

    def get_nodes_for_vip_group(self, group_json):
        nodes = []

        for entry in group_json.get("spec", {}).get("nodeAssignment", []):
            node = entry.get("name")
            if node:
                nodes.append(node)

        return nodes

    # -----------------------------
    # Node -> Server  -> Ports -> SG IDs
    # -----------------------------
    def get_sg_ids_for_nodes(self, nodes):
        sg_ids = []
        for node in nodes:
            server_output = self.run_openstack_cmd(
                "server list --name {} -f json".format(node)
            )

            servers = json.loads(server_output)
            if not servers:
                raise UnExpectedSystemOutput (ip=self.get_host_ip(),
                                              cmd="server list --name {}".format(node),
                                              output="No openstack server servers found for node '{}'".format(node))
            # Get the first server ID matching the name
            server_id = servers[0].get("ID")
            if not server_id:
                raise UnExpectedSystemOutput(ip=self.get_host_ip(),
                                             cmd="server list --name {}".format(node),
                                             output="Openstack server ID is missing for node '{}'".format(node))

            # Get the ports for this server
            ports_output = self.run_openstack_cmd(
                "port list --server {} -f json".format(server_id)
            )

            ports = json.loads(ports_output)
            if not ports:
                raise UnExpectedSystemOutput(ip=self.get_host_ip(),
                                             cmd="port list --server {}".format(server_id),
                                             output="no ports found for Openstack server '{}'".format(server_id))

            for port in ports:
                port_id = port.get("ID")
                if not port_id:
                    raise UnExpectedSystemOutput(ip=self.get_host_ip(),
                                                 cmd="port list --server {}".format(server_id),
                                                 output="PORT ID is missing for Openstack server '{}'".format(server_id))

                port_details = json.loads(self.run_openstack_cmd(
                    "port show {} -f json".format(port_id)))

                # security_group_ids is a list in the JSON response
                for sg_id in port_details.get("security_group_ids", []):
                    if sg_id not in sg_ids:
                        sg_ids.append(sg_id)

        return sg_ids

    # -----------------------------
    # Checks SG has protocol 112 allowed or not
    # -----------------------------
    def is_vrrp_allowed_in_sg(self, sg_id):
        # Checks if an SG allows VRRP and prints the match count
        cmd = "security group show {} | grep '112' | wc -l".format(sg_id)
        output = self.run_openstack_cmd(cmd).strip()
        count = int(output)
        if count == 0:
            return False
        return True

    # -----------------------------
    # FINAL VALIDATION
    # -----------------------------
    def is_validation_passed(self):
        names, namespaces = self.get_virtualipinstancegroups()

        for i in range(len(names)):
            name = names[i]
            ns = namespaces[i]

            cmd = "sudo /usr/local/bin/kubectl get virtualipinstancegroup {} -n {} -o json".format(name, ns)
            group_json = json.loads(self.get_output_from_run_cmd(cmd))

            # 1. Check if VRRP state is healthy
            if not self.validate_vrrp_state(group_json):
                # 2. Get nodes assigned to this VIP group
                nodes = self.get_nodes_for_vip_group(group_json)
                failed_nodes = []

                for node_name in nodes:
                    # 3. Get all SG IDs attached to this node
                    sg_ids = self.get_sg_ids_for_nodes([node_name])
                    vrrp_allowed_on_node = False

                    for sg_id in sg_ids:
                        # 4. If AT LEAST ONE SG has the rule, the node is PASS
                        if self.is_vrrp_allowed_in_sg(sg_id):
                            vrrp_allowed_on_node = True
                            break

                    if not vrrp_allowed_on_node:
                        failed_nodes.append(node_name)

                if failed_nodes:
                    self._failed_msg += (
                        "\n\nVRRP State is unhealthy for VirtualInstanceGroup '{}'."
                        "\nOpenStack verification failed for nodes: {}"
                        "\nNone of their attached Security Groups allow VRRP (Protocol 112)."
                    ).format(name, ", ".join(failed_nodes))
                    return False
        return True

class ValidateHelmStatus(Validator):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._unique_operation_name = "validate_helm_status_ncms"
        self._title = "Validate Helm Status"
        self._failed_msg = "Failed Helm Deployments"
        self._severity = Severity.ERROR
        self._implication_tags = [ImplicationTag.ACTIVE_PROBLEM]
        self._blocking_tags = [BlockingTag.UPGRADE]

    def is_validation_passed(self):
        ncs_version = globals.get_version()
        if ncs_version >= Version.V22:
            return_code,out, err = self.run_cmd('sudo helm ls -n ncms --all --output json | jq -r \'.[] | select(.status != "deployed") | .name\'')
        else:
            return_code, out, err = self.run_cmd('sudo helm ls --all --output json | jq -r \'.[] | select(.status != "deployed") | .name\'')
        if return_code == 0:
            if out:
                self._failed_msg = "Helm Deployments in ncms namespace not in deployed state:\n{}".format(out)
                return False
            return True
        else:
            self._failed_msg = "Helm Command Failed to run"
            return False



class GetNodeNameForRebootRequired(DataCollector):
    objective_hosts = [Objectives.ALL_NODES]

    def collect_data(self):
        cmd = "sudo ls /var/run/reboot-required*"
        return_code, out, err = self.run_cmd(cmd)
        return out


class CheckNodeRebootRequired(Validator):
    objective_hosts = [Objectives.ONE_MASTER]

    def set_document(self):
        self._unique_operation_name = "check_if_reboot_required_on_node"
        self._title = "Check If Reboot Required on Node"
        self._failed_msg = "Node Reboot Required"
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.UPGRADE]

    def is_validation_passed(self):
        node_with_reboot_required_dict = self.run_data_collector(GetNodeNameForRebootRequired)
        formatted_lines = []
        for k, v in node_with_reboot_required_dict.items():
            if v:
                clean_v = ", ".join(v.splitlines()) if isinstance(v, str) else ", ".join(v)
                formatted_lines.append("{} file found {}".format(k, clean_v))

        if formatted_lines:
            self._failed_msg = "Reboot required on nodes:\n{}".format("\n".join(formatted_lines))
            return False
        else:
            return True


class CheckCburPvCount(Validator):

    objective_hosts = {Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER]}

    CBUR_PV_CMD = "sudo /usr/local/bin/kubectl get pv | grep -i cbur"
    EXPECTED_PV_COUNT = 3
    EXPECTED_PV_COUNT_25_11_onward = 4

    def set_document(self):
        self._unique_operation_name = "check_cbur_pv_count"
        self._title = "Validate CBUR PV count has no duplicates and all CBUR pv are in healthy state"
        self._failed_msg = ""
        self._severity = Severity.WARNING
        self._implication_tags = [ImplicationTag.PRE_OPERATION]

    def is_validation_passed(self):
        try:
            return self._execute_check()
        except Exception as e:
            err_msg = getattr(e, "message", e.args[0] if e.args else e.__class__.__name__)
            raise UnExpectedSystemOutput(
                ip=self.get_host_ip(),
                cmd=self.CBUR_PV_CMD,
                output=err_msg,
                message="[CBUR PV] Internal script failure: {}.".format(err_msg)
            )

    def _execute_check(self):
        ncs_version = sys_parameters.get_version()
        return_code, out, err = self.run_cmd(self.CBUR_PV_CMD)

        if return_code != 0:
            self._failed_msg = "\nUnable to retrieve PV, as k8s command '{}' failed to run with '{}'".format(self.CBUR_PV_CMD ,err)
            return False

        out_str = self._normalize_output(out)
        lines = self._non_empty_lines(out_str)
        pv_count = len(lines)
        # Use CLAIM column (namespace/pvc-name) for display; easier to read than PV UUID
        pv_display_names = self._claim_column(lines)

        if pv_count < self.EXPECTED_PV_COUNT and ncs_version < Version.V25_11:
            self._failed_msg = "Fewer than 3 CBUR PVs found (found {}). Expected: cbur-backup, cbur-backup-cluster, cbur-repo.".format(pv_count)
            self._append_pv_names(pv_display_names)
            return False

        if pv_count < self.EXPECTED_PV_COUNT_25_11_onward and ncs_version >= Version.V25_11:
            self._failed_msg = "Fewer than 4 CBUR PVs found (found {}). Expected: cbur-backup, cbur-backup-cluster, cbur-repo, cloudnativepg-cbur-helper-pvc.".format(pv_count)
            self._append_pv_names(pv_display_names)
            return False

        if pv_count > self.EXPECTED_PV_COUNT and ncs_version < Version.V25_11:
            self._failed_msg = "More than 3 CBUR PVs found (found {}).".format(pv_count)
            self._append_pv_names(pv_display_names)
            return False
        
        if pv_count > self.EXPECTED_PV_COUNT_25_11_onward and ncs_version >= Version.V25_11:
            self._failed_msg = "More than 4 CBUR PVs found (found {}).".format(pv_count)
            self._append_pv_names(pv_display_names)
            return False

        if not self._all_pvs_bound(lines):
            self._failed_msg = "Not all CBUR PVs are in Bound state (expected all to be healthy)."
            self._failed_msg += "\nPV (claim) and state:\n" + self._pv_claims_and_states(lines)
            return False

        return True

    def _normalize_output(self, out):
        if out is None:
            return ""
        if isinstance(out, bytes):
            # Use default encoding; replace invalid bytes so parsing does not fail
            return out.decode(errors="replace")
        return str(out)

    def _non_empty_lines(self, text):
        result = []
        for line in text.strip().splitlines():
            line = line.strip()
            if line:
                result.append(line)
        return result

    # kubectl get pv: column index 5 = CLAIM = PVC/CBUR volume name. Real kubectl output always has 6+ columns.
    def _claim_column(self, lines):
        result = []
        for line in lines:
            parts = line.split()
            if len(parts) > 5:
                result.append(parts[5])
            else:
                result.append("")
        return result

    def _append_pv_names(self, pv_names):
        if pv_names:
            self._failed_msg += "\nPV (claim):\n" + "\n".join(pv_names)

    def _all_pvs_bound(self, lines):
        for line in lines:
            if "Bound" not in line:
                return False
        return True

    def _pv_claims_and_states(self, lines):
        result = []
        for line in lines:
            claim = self._claim_from_line(line)
            state = self._state_from_line(line)
            result.append("{} {}".format(claim, state))
        return "\n".join(result)

    # Same as _claim_column: index 5 = CLAIM; else "".
    def _claim_from_line(self, line):
        parts = line.split()
        if len(parts) > 5:
            return parts[5]
        return ""

    def _state_from_line(self, line):
        if "Bound" in line:
            return "Bound"
        if "Available" in line:
            return "Available"
        if "Released" in line:
            return "Released"
        return "Other"
