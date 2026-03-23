from __future__ import print_function

# -----------------------------------------------------------------------------------------------------------------------
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


# -----------------------------------------------------------------------------------------------------------------------
# base class
class ICERC_printer:
    def __init__(self, details):
        self._details = details

    # virtual methods
    def _get_UC_validtions_iceStr_map(self):
        assert False

    def _get_controllers_validtions_iceStr_map(self):
        assert False

    def _get_computes_validtions_iceStr_map(self):
        assert False

    def _get_storages_validtions_iceStr_map(self):
        assert False

    def _get_time_starting(self):
        raise NotImplementedError

    def _validtion_title(self):
        raise NotImplementedError

    def _validtion_footer(self):
        raise NotImplementedError

    def _print_info(self):
        assert False

    def _health_check_cmd(self):
        assert False

    # shard methods
    @staticmethod
    def bool_to_NOK(ok):
        if ok:
            return bcolors.OKGREEN + 'OK' + bcolors.ENDC
        return bcolors.FAIL + 'NOK' + bcolors.ENDC

    def _validtion_to_icrec_str(self, host, validtion_id, icerc_name):
        is_pass = self._details[host][validtion_id]["pass"]
        str_ok = ICERC_printer.bool_to_NOK(is_pass)
        to_return = ": {}={} ".format(icerc_name, str_ok)
        return to_return

    def _host_type_validations_print(self, host_type, host_type_validtion_id_to_str, title=None):
        for host in self._details:
            if host_type in host:
                if not title:
                    host_name = host
                else:
                    host_name = host
                to_print = ":: {} ".format(host_name)

                for validtion in sorted(host_type_validtion_id_to_str):
                    icerc_name = host_type_validtion_id_to_str[validtion]
                    to_add = self._validtion_to_icrec_str(host=host, validtion_id=validtion,
                                                          icerc_name=icerc_name)
                    to_print = to_print + to_add
                print(to_print)


# -----------------------------------------------------------------------------------------------------------------------
# example of fsid output
###############################################################
## 2021-04-18:22:19:21 :: Ceph FSID and Keys Checks Starting ##
###############################################################
# 2021-04-18:22:19:28 :: overcloud-controller-0 To GET Reference FSID and client.admin Key:
# 2021-04-18:22:19:28 :: FSID = dc917faf-6958-4a0b-8c9c-dab42892102d
# 2021-04-18:22:19:28 :: client.openstack Key = AQBrcjJf4we1FhAANHt86bbp2XrmjUwB6g3VFQ==
# 2021-04-18:22:19:28 :: client.admin Key = AQAI9zNfWvrRFRAACR03DvLOY/1s1i75HDW1Mg==
# 2021-04-18:22:19:31 :: Templates :: Ceph FSID = OK :: Ceph Client OpenStack Key = OK
# 2021-04-18:22:19:38 :: overcloud-controller-0   :: ceph.conf=OK :: openstack.keyring=OK :: admin.keyring=OK :: service_configs.json=OK :: cinder.conf=OK
# 2021-04-18:22:19:40 :: overcloud-ovscompute-0   :: ceph.conf=OK :: openstack.keyring=OK :: admin.keyring=OK :: service_configs.json=OK :: nova.conf=OK :: secret.xml=OK :: Virsh DB=OK
# 2021-04-19:21:11:38 :: overcloud-Storage-0      :: ceph.conf=OK :: admin.keyring=OK :: service_configs.yaml=OK
# 2021-04-19:21:11:39 :: overcloud-Storage-1      :: ceph.conf=OK :: admin.keyring=OK :: service_configs.yaml=OK
######################################################################################################################################################
## 2021-04-18:22:19:44 :: Ceph FSID and Keys Checks Completed, please review the previous output carefully and fix before doing any scale activity. ##
######################################################################################################################################################
class FSID_ICERC_print(ICERC_printer):
    def _get_UC_validtions_iceStr_map(self):
        templates_validtion_id_to_str = \
            {
                "is_runtime_CephClusterFSID_match_configured_CephClusterFSID": "Ceph FSID",
                "is_runtime_CephClientKey_match_configured_CephClientKey": "Ceph Client OpenStack Key"
            }
        return templates_validtion_id_to_str

    def _get_controllers_validtions_iceStr_map(self):
        controller_validtion_id_to_str = \
            {
                "is_runtime_ceph_conf_fsid_match_configured_ceph_conf_fsid": "ceph.conf",
                "is_runtime_openstack_keyring_match_configured_openstack_keyring": "openstack.keyring",
                "is_runtime_admin_keyring_match_configured_admin_keyring": "admin.keyring",
                "is_runtime_puppet_fsid_match_configured_puppet_fsid": "service_configs.json",
                "is_runtime_cinder_fsid_match_configured_cinder_fsid": "cinder.conf"
            }
        return controller_validtion_id_to_str

    def _get_computes_validtions_iceStr_map(self):
        compute_validtion_id_to_str = \
            {
                "is_runtime_ceph_conf_fsid_match_configured_ceph_conf_fsid": "ceph.conf",
                "is_runtime_openstack_keyring_match_configured_openstack_keyring": "openstack.keyring",
                "is_runtime_admin_keyring_match_configured_admin_keyring": "admin.keyring",
                "is_runtime_puppet_fsid_match_configured_puppet_fsid": "service_configs.json",
                "is_runtime_nova_fsid_match_configured_nova_fsid": "nova.conf",
                "is_runtime_nova_secret_match_configured_nova_secret": "secret.xml",
                "is_virsh_fsid_secret_conf_as_runtime": "Virsh DB"
            }
        return compute_validtion_id_to_str

    def _get_storages_validtions_iceStr_map(self):
        storage_validtion_id_to_str = \
            {
                "is_runtime_ceph_conf_fsid_match_configured_ceph_conf_fsid": "ceph.conf",
                "is_runtime_admin_keyring_match_configured_admin_keyring": "admin.keyring",
                # "is_runtime_puppet_fsid_match_configured_puppet_fsid": "service_configs.json",
            }
        return storage_validtion_id_to_str

    def _get_time_starting(self):
        time_starting = self._details["undercloud - localhost"]["info_get_fsid"]["time"]
        return time_starting

    def _validtion_title(self):
        return "Ceph FSID and Keys Checks Starting"

    def _validtion_footer(self):
        return "Ceph FSID and Keys Checks Completed, please review the previous output carefully and fix before doing any scale activity."

    def _health_check_cmd(self):
        return "ice healthcheck --run-flows ceph_fsid"

    def _print_info(self):
        fsid = self._details["undercloud - localhost"]["info_get_fsid"]["system_info"]
        print(":: FSID = {}".format(fsid))

