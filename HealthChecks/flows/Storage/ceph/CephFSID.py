from __future__ import absolute_import
from HealthCheckCommon.validator import InformatorValidator
from flows.Storage.ceph.Ceph import CephValidation
from flows.Storage.ceph.CephInfo import *
from flows.Cbis.user_config_validator.user_config_checks import *
import tools.DynamicPaths as DynamicPaths
from tools.python_versioning_alignment import get_full_trace
import os


class CephFSIDValidation(CephValidation):
    def __init__(self, ip):
        CephValidation.__init__(self, ip)
        self._conf_dict = None

    def append_domain_tags(self):
        pass

    def _get_conf_name(self):
        path = self._get_conf_path()
        return path.split("/")[-1]

    def _get_value_from_config(self):
        raise NotImplementedError

    def _get_conf_path(self):
        raise NotImplementedError

    def _get_value_from_system(self):
        raise NotImplementedError

    def _set_document_config_validator(self):
        raise NotImplementedError

    def set_document(self):
        self.objective = self._set_document_config_validator()
        self.conf_name = self._get_conf_name()
        self._title = "Is the runtime {} matches the configured {} in the {} file".format(self.objective,
                                                                                          self.objective,
                                                                                          self.conf_name)
        self._unique_operation_name = "is_runtime_{}_match_configured_{}".format(self.objective, self.objective)
        self._failed_msg = "The {} configured is {{}} but the runtime value is {{}}".format(self.objective)
        self._severity = Severity.ERROR
        self._is_clean_cmd_info = True
        self._implication_tags = [ImplicationTag.NOTE]

    def _set_faild_msg(self, config_obj, real_obj):
        if not config_obj:
            self._failed_msg = "{} is not configured in {}".format(self.objective, self.conf_name)
        else:
            if PythonUtils.is_64_secret(config_obj):
                config_obj = PythonUtils.get_object_in_secret_format(config_obj)
            if PythonUtils.is_64_secret(real_obj):
                real_obj = PythonUtils.get_object_in_secret_format(real_obj)
            self._failed_msg = self._failed_msg.format(str(config_obj).strip(), str(real_obj).strip())

    def is_validation_passed(self):
        if ImplicationTag.APPLICATION_DOMAIN in self.get_implication_tags():
            self._implication_tags.remove(ImplicationTag.APPLICATION_DOMAIN)
        real_val = self._get_value_from_system()
        config_val = self._get_value_from_config()
        if real_val == "":
            raise IOError

        if real_val == config_val:
            return True
        else:
            self._set_faild_msg(config_val, real_val)
            return False

    def _get_conf_dict(self, conf_format=None):
        if not self._conf_dict:
            file_path = self._get_conf_path()
            self._conf_dict = self.get_dict_from_file(file_path, file_format=conf_format)
        return self._conf_dict

    def get_ip_address(self):
        info_table = self.get_dict_from_command_output('sudo ipmitool lan print', 'space', custom_delimiter=':')
        return info_table.get('IP Address')

    def get_vm_pool_by_pm_addr(self, pm_addr):
        out = self.get_dict_from_file(CephPaths.HOST_CONF, file_format='yaml')
        try:
            for item in out['host_groups']:
                if pm_addr in item['pm_addr']:
                    if 'vm_pool' in list(item.keys()):
                        return item['vm_pool']
        except KeyError:
            raise UnExpectedSystemOutput(ip=self.get_host_ip(), cmd="", output=get_full_trace())

    def get_pool_uuid_if_exist(self):
        if CephInfo.is_multiple_pools_enable():
            pm_addr = self.get_ip_address()
            vm_pool = self.get_vm_pool_by_pm_addr(pm_addr=pm_addr)
            if vm_pool:
                uuid_pool = CephInfo.get_uuid_pools()
                try:
                    return uuid_pool[vm_pool]
                except KeyError:
                    raise UnExpectedSystemOutput(ip=self.get_host_ip(), cmd="", output=get_full_trace())
        return None


class StorageTemplateConfigValidator(CephFSIDValidation):
    objective_hosts = [Objectives.UC]

    def _get_conf_path(self):
        return CephPaths.STORAGE_TEMPLATE_CONF

    def _get_conf_name(self):
        return "storage-environment.yaml"

    def _get_value_from_config(self):
        conf_fsid = self._get_conf_dict(conf_format="yaml").get('parameter_defaults', {}).get(self.objective)
        return conf_fsid


class TemplateFSIDCheck(StorageTemplateConfigValidator):
    def _get_value_from_system(self):
        return CephInfo.get_fsid()

    def _set_document_config_validator(self):
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]
        return 'CephClusterFSID'


class FsidInfo(InformatorValidator, CephFSIDValidation):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.UC],
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MASTER]
    }

    def set_document(self):
        self._is_pure_info = True
        self._unique_operation_name = "get_fsid"
        self._title_of_info = "Ceph fsid"
        self._system_info = ""
        self._is_clean_cmd_info = True

    def get_system_info(self):
        fsid = CephInfo.get_fsid()
        return fsid


class TemplateOpenStackKeyringCheck(StorageTemplateConfigValidator):
    def _get_value_from_system(self):
        return CephInfo.get_clients_keys_map(client_name="openstack")

    def _set_document_config_validator(self):
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]
        return 'CephClientKey'


# deleted as the recommendation at ICET-672
#
# class TemplateAdminKeyringCheck(StorageTemplateConfigValidator):
#     def _get_value_from_system(self):
#         return CephInfo.get_clients_keys_map(client_name="admin")
#
#     def _set_document_config_validator(self):
#         return 'CephAdminKey'


class RegexConfValidator(CephFSIDValidation):

    def _set_conf_line_pattern(self):
        raise NotImplementedError

    def _set_value_from_conf_line(self, conf_line):
        raise NotImplementedError

    def _get_value_from_config(self):
        path = self._get_conf_path()
        pattern = self._set_conf_line_pattern()
        pattern = r"#*\s*" + pattern
        conf_lines = re.findall(pattern, self._get_conf_dict())
        conf_lines_not_commented = [conf_line for conf_line in conf_lines
                                    if not conf_line.strip().startswith("#")]
        if not len(conf_lines_not_commented):
            return None
        conf_value = self._set_value_from_conf_line(conf_lines_not_commented[0])
        return conf_value


class KeyringConfigCheck(CephFSIDValidation):

    def _get_conf_path(self):
        return CephPaths.KEYRING_PATH_TEMPLATE.format(self.client)

    def _set_client(self):
        raise NotImplementedError

    def _set_document_config_validator(self):
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self.client = self._set_client()
        return '{}_keyring'.format(self.client)

    def _get_value_from_system(self):
        return CephInfo.get_clients_keys_map(client_name=self.client)

    def _get_value_from_config(self):
        client_section = 'client.{}'.format(self._set_client())
        key = self._get_conf_dict(conf_format='ini')[client_section]['key']
        if key.startswith('"') and key.endswith('"'):
            key = key.strip('"')
        return key

    def _keyring_file_exists(self):
        return self.file_utils.is_file_exist(file_path=self._get_conf_path())

    def is_prerequisite_fulfilled(self):
        if CephValidation.is_prerequisite_fulfilled(self):  # ceph in use
            return self._keyring_file_exists()              # and keyring file exists
        return False


class CBISKeyringConfigCheck(KeyringConfigCheck):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.COMPUTES, Objectives.CONTROLLERS]
    }


class KeyringMultiplePoolConfigCheck(CBISKeyringConfigCheck):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.CONTROLLERS, Objectives.COMPUTES]
    }
    pm_addr = None
    vm_pool = None

    def _set_client(self):
        return None

    def set_document(self):
        self.client = None
        self.objective = "pool_name_keyring"
        self.conf_name = "pool_name_keyring"
        self._title = "Is the runtime {} matches the configured {} in the {} file".format(self.objective,
                                                                                          self.objective,
                                                                                          self.conf_name)
        self._unique_operation_name = "is_runtime_{}_match_configured_{}".format(self.objective, self.objective)
        self._is_clean_cmd_info = True
        self._failed_msg = "TBD"
        self._severity = Severity.ERROR

    def is_validation_passed(self):
        incorrect_keyring_dict = []
        self.pm_addr = self.get_ip_address()
        self.vm_pool = self.get_vm_pool_by_pm_addr(pm_addr=self.pm_addr)
        for key in list(CephInfo.get_uuid_pools().keys()):
            if "compute" in self.get_host_name().lower() and key != self.vm_pool:
                continue
            real_val = CephInfo.get_clients_keys_map(client_name=key)
            keyring_dict = self.get_dict_from_file(CephPaths.KEYRING_PATH_TEMPLATE.format(key), file_format='ini')
            config_val = keyring_dict['client.{}'.format(key)]['key']
            if real_val != config_val:
                self._set_faild_msg(config_val, real_val)
                incorrect_keyring_dict.append(CephPaths.KEYRING_PATH_TEMPLATE.format(key))
        if len(incorrect_keyring_dict) > 0:
            self._failed_msg = "some keys not match: {}".format(incorrect_keyring_dict)
            return False
        return True

    def is_prerequisite_fulfilled(self):
        if CephValidation.is_prerequisite_fulfilled(self):
            return CephInfo.is_multiple_pools_enable()
        return False


class NCSKeyringConfigCheck(KeyringConfigCheck):
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.STORAGE]
    }


class FSIDConfigValidator(CephFSIDValidation):
    def _get_value_from_system(self):
        return CephInfo.get_fsid()


class KeyringOpenstackConfigCheck(CBISKeyringConfigCheck):
    def _set_client(self):
        return "openstack"


class KeyringAdminConfigCheck(CBISKeyringConfigCheck):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.COMPUTES, Objectives.CONTROLLERS, Objectives.STORAGE]
    }

    def _set_client(self):
        return "admin"


class KeyringCephFSConfigCheck(NCSKeyringConfigCheck):
    def _set_client(self):
        return "cephfs"


class KeyringBareMetalConfigCheck(NCSKeyringConfigCheck):
    def _set_client(self):
        return "baremetal.cephfs"


class KeyringCephRBDConfigCheck(NCSKeyringConfigCheck):
    def _set_client(self):
        return "cephrbd"


class KeyringRadosGWConfigCheck(NCSKeyringConfigCheck):
    def _set_client(self):
        return "radosgw"


class FSIDPuppetConfValidator(FSIDConfigValidator):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.COMPUTES, Objectives.CONTROLLERS]
    }

    def _get_conf_path(self):
        if gs.get_version() < Version.V19:
            return CephPaths.PUPPET_CONF_18
        return CephPaths.PUPPET_CONF

    def _set_document_config_validator(self):
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]
        return "puppet_fsid"

    def _get_value_from_config(self):
        if gs.get_version() < Version.V19:
            return self._get_conf_dict(conf_format='yaml').get('ceph::profile::params::fsid')
        else:
            conf = self._get_conf_dict(conf_format='json')
            return conf.get('tripleo::profile::base::cinder::volume::rbd::cinder_rbd_secret_uuid') or \
                   conf.get('nova::compute::rbd::libvirt_rbd_secret_uuid') or \
                   conf.get('ceph_mds_ansible_vars', {}).get("fsid") or \
                   conf.get('ceph_mgr_ansible_vars', {}).get("fsid") or \
                   conf.get('ceph_mon_ansible_vars', {}).get("fsid")


class FSIDCinderConfValidator(CephFSIDValidation):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.CONTROLLERS]
    }

    def set_document(self):
        self._unique_operation_name = "is_runtime_cinder_fsid_match_configured_cinder_fsid"
        self._title = "Is the runtime cinder_fsid matches the configured cinder_fsid in the cinder.conf file"
        self._failed_msg = "TBD"
        self._severity = Severity.ERROR
        self._is_clean_cmd_info = True
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        problematic_conf_sections = []
        sys_fsid = None
        is_conf_fsid = False
        if not CephInfo.is_multiple_pools_enable():
            sys_fsid = CephInfo.get_fsid()
        if gs.get_version() < Version.V19:
            conf_path = CephPaths.CINDER_CONF_18
        else:
            conf_path = CephPaths.CINDER_CONF
        conf_dict = self.get_dict_from_file(conf_path, file_format='ini')
        for section in conf_dict:
            conf_fsid = conf_dict[section].get('rbd_secret_uuid')
            if conf_fsid:
                is_conf_fsid = True
                if conf_fsid != sys_fsid:
                    problematic_conf_sections.append("{}:rbd_secret_uuid - {}".format(section, conf_fsid))
        if problematic_conf_sections:
            self._failed_msg = 'conf file: {} \nrbd_secret_uuid value/s is/are not equal to fsid runtime value -{} ' \
                               '.\nconf sections: \n{}'.format(conf_path, sys_fsid, ','.join(problematic_conf_sections))
            return False
        if not is_conf_fsid and sys_fsid:
            self._failed_msg = "rbd_secret_uuid is not defined in conf file: {}".format(conf_path)
            return False
        return True


class FsidNovaConfValidator(FSIDConfigValidator):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.COMPUTES]
    }

    def _get_value_from_system(self):
        if self.get_pool_uuid_if_exist() is None:
            return CephInfo.get_fsid()
        else:
            return self.get_pool_uuid_if_exist()

    def _get_conf_path(self):
        if gs.get_version() < Version.V19:
            return CephPaths.NOVA_CONF_18
        return CephPaths.NOVA_CONF

    def _set_document_config_validator(self):
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]
        return "nova_fsid"

    def _get_value_from_config(self):
        return self._get_conf_dict(conf_format='ini').get('libvirt', {}).get('rbd_secret_uuid')


class FSIdNovaSecretValidator(FSIDConfigValidator, RegexConfValidator):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.COMPUTES]
    }

    def _get_conf_path(self):
        if gs.get_version() < Version.V19:
            return CephPaths.NOVA_SECRET_18
        return CephPaths.NOVA_SECRET

    def _set_document_config_validator(self):
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]
        return "nova_secret"

    def _set_conf_line_pattern(self):
        return r"<uuid>.+</uuid>"

    def _set_value_from_conf_line(self, conf_line):
        return re.sub(r"<\/*uuid>", "", conf_line).strip()


class FSIdNovaSecretMultiplePoolsValidator(FSIdNovaSecretValidator):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.COMPUTES]
    }
    pool_uuid = None

    def _set_document_config_validator(self):
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]
        return "nova_secret_multiple_pool"

    def set_document(self):
        self.objective = self._set_document_config_validator()
        self.conf_name = "/etc/nova/secret_pool_name.xml"
        self._title = "Is the runtime {} matches the configured {} in the {} file".format(self.objective,
                                                                                          self.objective,
                                                                                          self.conf_name)
        self._unique_operation_name = "is_runtime_{}_match_configured_{}".format(self.objective, self.objective)
        self._failed_msg = "The {} configured is {{}} but the runtime value is {{}}".format(self.objective)
        self._severity = Severity.ERROR
        self._is_clean_cmd_info = True

    def is_prerequisite_fulfilled(self):
        if CephValidation.is_prerequisite_fulfilled(self):
            self.pool_uuid = self.get_pool_uuid_if_exist()
            return True if self.pool_uuid else False
        return False

    def _get_value_from_system(self):
        return self.get_pool_uuid_if_exist()

    def _get_conf_path(self):
        pool_vm = self.get_vm_pool_by_pm_addr(pm_addr=self.get_ip_address())
        return CephPaths.NOVA_SECRET_MULTIPLE_POOL.format(pool_vm)

    def _get_conf_dict(self, conf_format=None):
        if gs.get_version() < Version.V25:
            return super(FSIdNovaSecretMultiplePoolsValidator, self)._get_conf_dict()
        else:
            file_path = self._get_conf_path()
            cmd = "sudo podman exec nova_compute cat {}".format(file_path)
            out = self.get_output_from_run_cmd(cmd, add_bash_timeout=True)
            if not out:
                error = "The file: {} is empty\n".format(cmd)
                raise UnExpectedSystemOutput(self.get_host_name(), "", error)
            self._conf_dict = out
            return self._conf_dict


class FSIDCephConfValidator(FSIDConfigValidator):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.COMPUTES, Objectives.CONTROLLERS, Objectives.STORAGE],
        Deployment_type.NCS_OVER_BM: [Objectives.STORAGE]
    }

    def _get_conf_path(self):
        return CephPaths.CEPH_CONF

    def _set_document_config_validator(self):
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]
        return "ceph_conf_fsid"

    def _get_value_from_config(self):
        return self._get_conf_dict(conf_format='ini').get('global', {}).get('fsid')


class CephKeysConfigValidator(CephFSIDValidation):      # Removed as decided on ICET-1606
    objective_hosts = {
        Deployment_type.NCS_OVER_BM: [Objectives.ONE_MANAGER]
    }

    def set_document(self):
        self._unique_operation_name = "ceph_keys_values_as_runtime"
        self._title = "checks if ceph-keys file values are the same as the runtime"
        self._failed_msg = "TBD"
        self._severity = Severity.ERROR
        self._is_clean_cmd_info = True
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        errors = []
        conf_dir_path = DynamicPaths.ncs_bm_config_dir_path
        path = os.path.join(conf_dir_path, 'ceph_keys.json')
        ceph_keys_dict = self.get_dict_from_file(path, file_format='json')
        fsid = CephInfo.get_fsid()
        for k in ceph_keys_dict:
            val = ceph_keys_dict[k]
            if k == 'fsid' and val != fsid:
                errors.append('FSID: configured - {} . runtime - {}'.format(val, fsid))
            elif '_key' in k:
                client_name = k.replace('_key', '').replace('_', '.')
                runtime_key = CephInfo.get_clients_keys_map(client_name=client_name)
                if runtime_key and (runtime_key != val):
                    errors.append('Client {} key : configured - {}, runtime - {}'.format(client_name, val, runtime_key))
        if len(errors):
            self._failed_msg = 'File {} :\nFollowing keys configured value is not as runtime:\n{}'.format(path,
                                                                                                          '\n'.join(
                                                                                                              errors))
            return False
        return True


class VmsFSIDCheck(CephFSIDValidation):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.COMPUTES]
    }

    def set_document(self):
        self._unique_operation_name = "is_virsh_vms_fsid_conf_as_runtime"
        self._title = "is virsh vms fsid conf as runtime"
        self._failed_msg = "TBD"
        self._severity = Severity.CRITICAL
        self._is_clean_cmd_info = True
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        fsid = self.get_pool_uuid_if_exist()
        if fsid is None:
            fsid = CephInfo.get_fsid()
        inactive_vms = self.get_output_from_run_cmd("sudo virsh list --inactive --name").strip().splitlines()
        all_vms = self.get_output_from_run_cmd("sudo virsh list --all --name").strip().splitlines()
        active_vms = list(set(all_vms).difference(set(inactive_vms)))
        failed_active_vms_set = self.get_failed_vms_by_xml_path(
            expected_vms=active_vms, path="/var/run/libvirt/qemu/", fsid=fsid)
        failed_vms_set = self.get_failed_vms_by_xml_path(expected_vms=all_vms, path="/etc/libvirt/qemu/", fsid=fsid)
        failed_inactive_vms_set = set(inactive_vms).intersection(failed_vms_set)
        failed_active_vms_set.update(set(active_vms).intersection(failed_vms_set))
        if failed_inactive_vms_set or failed_active_vms_set:
            self._failed_msg = "following vms configured with a different fsid:"
            if failed_active_vms_set:
                self._failed_msg += "\nactive vms: {}".format(list(failed_active_vms_set))
            if failed_inactive_vms_set:
                self._failed_msg += "\ninactive vms: {}".format(list(failed_inactive_vms_set))
            return False
        return True

#    Below function is to detect CEPH Storage and External Storage
#    disk type='network' is for CEPH example <disk type='network' device='cdrom'>
#    Anything else apart from this lke BLOCK or FILE are for EXTERNAL
#    <disk type='file' device='cdrom'>

    def validate_CEPH_Vms(self, vm_path):
        get_disk_type_command = "sudo grep -i \"<disk type='network'\" {}".format(vm_path)
        return_code, disk_type, err = self.run_cmd(get_disk_type_command)
        if (int(return_code) == 0):
            return 0
        else:
            return 1

    def get_failed_vms_by_xml_path(self, expected_vms, path, fsid):
        vm_by_path_list = []
        failed_vms = []
        final_ceph_vm_list = []
        cmd = "sudo find {} -name \"inst*.xml\"".format(path)
        vms_lines = self.get_output_from_run_cmd(cmd).strip().splitlines()
        if expected_vms and not vms_lines:
            raise UnExpectedSystemOutput(ip=self.get_host_ip(), cmd=cmd,
                                         output="No instance.xml file found for vms: {}".format(expected_vms))

        vm_name = ""
        for vm_path in vms_lines:
            vm_name = re.findall(r"inst.+.xml", vm_path)[0].replace(".xml", "")
            vm_by_path_list.append(vm_name)
            validation_tag_ceph_vm = self.validate_CEPH_Vms(vm_path)
            if int(validation_tag_ceph_vm) == 0:
                final_ceph_vm_list.append(vm_path)

            if len(final_ceph_vm_list) != 0:
                for vm_path in final_ceph_vm_list:
                    get_vm_secret_lines = "sudo grep -oP \"<secret.*ceph.*>\" {}".format(vm_path)
                    secrets_lines = self.get_output_from_run_cmd(get_vm_secret_lines).strip().splitlines()
                    for secret_line in secrets_lines:
                            fsid_str = "'{fsid}'".format(fsid=fsid)
                            if fsid_str not in secret_line:
                                failed_vms.append(vm_name)
                                break
            
        if set(vm_by_path_list) != set(expected_vms):
            raise UnExpectedSystemOutput(ip=self.get_host_ip(), cmd="", output=
            "Mismatch between vms_list: {} and instance.xml files: {}".format(expected_vms, vm_by_path_list))

        return set(failed_vms)


class VirshSecretFsidCheck(CephFSIDValidation):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.COMPUTES]
    }

    def set_document(self):
        self._unique_operation_name = "is_virsh_fsid_secret_conf_as_runtime"
        self._title = "is virsh fsid secret conf as runtime"
        self._failed_msg = "TBD"
        self._severity = Severity.CRITICAL
        self._is_clean_cmd_info = True
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        fsid = CephInfo.get_fsid()
        out = self.get_output_from_run_cmd("sudo virsh secret-list")
        if out and fsid not in out:
            self._failed_msg = "cluster fsid is not in the virsh secrets list"
            return False
        uuid = self.get_pool_uuid_if_exist()
        if uuid:
            if out and uuid not in out:
                self._failed_msg = "uuid is not in the virsh secrets list"
                return False
        return True


class CephSizeConfigValidator(CephFSIDValidation):
    def __init__(self, ip):
        CephValidation.__init__(self, ip)
        self._conf_dict = ConfigStore.get_cbis_user_config()

    def _get_conf_name(self):
        return "user_config.yaml"


class CephPoolSizeConfigCheck(CephSizeConfigValidator):
    objective_hosts = {
        Deployment_type.CBIS: [Objectives.CONTROLLERS]
    }

    def __init__(self, ip):
        CephSizeConfigValidator.__init__(self, ip)

    def _set_document_config_validator(self):
        objective = 'ceph_pool_size'
        self._severity = Severity.ERROR
        return objective

    def _get_value_from_config(self):
        try:
            to_return = str(self._get_conf_dict()['CBIS']['storage']['ceph_pool_size'])
        except KeyError:
            raise UnExpectedSystemOutput(ip=self.get_host_ip(), cmd="", output=get_full_trace())
        return to_return

    def _get_value_from_system(self):
        try:
            return self.get_dict_from_file(CephPaths.CEPH_CONF, 'ini')['global']['osd_pool_default_size']
        except KeyError:
            raise UnExpectedSystemOutput(ip=self.get_host_ip(), cmd="", output=get_full_trace())


class CephJournalSizeConfCheck(CephSizeConfigValidator):
    objective_hosts = [Objectives.CONTROLLERS]

    def __init__(self, ip):
        CephSizeConfigValidator.__init__(self, ip)

    def _set_document_config_validator(self):
        objective = 'ceph_journal_size'
        self._severity = Severity.ERROR
        return objective

    def _get_value_from_config(self):
        try:
            to_return = str(self._get_conf_dict()['CBIS']['storage']['ceph_journal_size'])
        except KeyError:
            raise UnExpectedSystemOutput(ip=self.get_host_ip(), cmd="", output=get_full_trace())
        return to_return

    def _get_value_from_system(self):
        ceph_conf = self.get_dict_from_file(CephPaths.CEPH_CONF, 'ini')
        return str(ceph_conf.get('global', {}).get('osd_journal_size') or ceph_conf.get('osd', {}).get('osd_journal_size'))

class CheckCEPHStoreDBSize(CephFSIDValidation):
    objective_hosts = {
        Deployment_type.CBIS: [ Objectives.CONTROLLERS],
        Deployment_type.NCS_OVER_BM: [Objectives.MASTERS]
    }
    CEPH_SIZE_LIMIT_GB = 40

    def set_document(self):
        self._unique_operation_name = "check_ceph_storedb_size"
        self._title = "is ceph storedb size within limits"
        self._failed_msg = "TBD"
        self._severity = Severity.CRITICAL
        self._implication_tags = [ImplicationTag.PRE_OPERATION]
        self._blocking_tags = [BlockingTag.SCALE, BlockingTag.UPGRADE]

    def is_validation_passed(self):
        version = gs.get_version()
        deployment_type = gs.get_deployment_type()
        if (version >= Version.V24_11 and deployment_type == Deployment_type.NCS_OVER_BM) \
                or (version >= Version.V25 and deployment_type == Deployment_type.CBIS):
            fsid = CephInfo.get_fsid()
            path = "/var/lib/ceph/{}".format(fsid)
        else:
            path = "/var/lib/ceph/"

        cmd = "sudo du -s --block-size=1G {}".format(path)
        out = self.get_output_from_run_cmd(cmd, add_bash_timeout=True).strip()
        try:
            size_gb = int(out.split()[0])
        except (IndexError, ValueError):
            raise UnExpectedSystemOutput(ip=self.get_host_ip(), cmd="", output=get_full_trace())

        if size_gb >= CheckCEPHStoreDBSize.CEPH_SIZE_LIMIT_GB:
            self._failed_msg = "Ceph StoreDB size at {} is {} GB, which exceeds the allowed limit of {} GB.".format(path, size_gb, CheckCEPHStoreDBSize.CEPH_SIZE_LIMIT_GB)
            return False

        return True
