from __future__ import absolute_import
from flows.Blueprint.BlueprintDataCollectorsCommon import *


class IPMIControllerManager(BlueprintDataCollector):
    def get_system_ids(self):
        return {1}


class IPMIControllerManagerVersion(IPMIControllerManager):

    def get_blueprint_objective_key_name(self):
        return "IPMI@controller_manager_version"

    def collect_blueprint_data(self, **kwargs):
        cmd = "sudo ipmitool -V"
        out = self.get_output_from_run_cmd(cmd, hosts_cached_pool=BlueprintDataCollector.cached_data_pool)
        ipmi_version = self.split_result_from_output(cmd=cmd, out=out, separator="ipmitool version")[0]

        return {ipmi_id: ipmi_version for ipmi_id in self.get_ids()}


class IPMIControllerManagerFirmware(IPMIControllerManager):

    def get_blueprint_objective_key_name(self):
        return "IPMI@controller_manager_firmware"

    def collect_blueprint_data(self, **kwargs):
        cmd = "sudo ipmitool mc info | grep 'Firmware Revision'"
        out = self.get_output_from_run_cmd(cmd, hosts_cached_pool=BlueprintDataCollector.cached_data_pool)
        ipmi_firmware = self.split_result_from_output(cmd, out)[0]

        return {ipmi_id: ipmi_firmware for ipmi_id in self.get_ids()}
