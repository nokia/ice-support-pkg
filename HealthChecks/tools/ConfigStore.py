from __future__ import absolute_import
import tools.sys_parameters as gs


class ConfigStore:
    @staticmethod
    def get_cbis_user_config():
        return gs.get_base_conf()

    @staticmethod
    def get_ncs_bm_conf():
        return gs.get_base_conf()

    @staticmethod
    def get_ncs_cna_conf():
        '''get the bcmt_config.json dict'''
        return gs.get_base_conf()

    @staticmethod
    def get_ncs_cna_user_conf():
        return gs.get_ncs_cna_user_conf()

    @staticmethod
    def get_openstack_info():
        return gs.get_base_conf()
