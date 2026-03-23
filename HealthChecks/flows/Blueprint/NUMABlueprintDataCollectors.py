from __future__ import absolute_import
import os.path
from flows.Blueprint.BlueprintDataCollectorsCommon import *
from flows.Blueprint.NICBlueprintDataCollectors import NICBlueprintDataCollector
from six.moves import range


class NUMA(BlueprintDataCollector):
    objective_hosts = {Deployment_type.CBIS: [Objectives.COMPUTES],
                       Deployment_type.NCS_OVER_BM: [Objectives.WORKERS,
                                                     Objectives.EDGES]}

    def get_system_ids(self):
        numa_ids = []
        cmd = "lscpu | grep 'NUMA node(s):'"
        out = self.get_output_from_run_cmd(cmd, hosts_cached_pool=BlueprintDataCollector.cached_data_pool)
        num_nodes = int(self.split_result_from_output(cmd=cmd, out=out, is_number=True)[0])
        for i in range(num_nodes):
            numa_ids.append('node {}'.format(i))
        return set(numa_ids)

    def get_numa_objective_value_by_cmd(self, cmd):
        objective_dict = {}
        for objective_id in self.get_ids():
            full_cmd = cmd.format(objective_id)
            objective_dict[objective_id] = self.get_objective_value_by_cmd(full_cmd, objective_id)
        return objective_dict


class NumaSizeMemory(NUMA):

    def get_blueprint_objective_key_name(self):
        return "Numa@total_allocated_memory_in_mb"

    def collect_blueprint_data(self, **kwargs):
        cmd = "numactl --hardware | grep 'size:' | grep '{}'"
        sizes_with_mb_suffix = self.get_numa_objective_value_by_cmd(cmd)
        res = self.set_dict_values_to_numeric(sizes_with_mb_suffix, 'size', 'MB', cmd, is_unicode=True)
        return res


class NumaNICs(NUMA):

    def get_blueprint_objective_key_name(self):
        return "Numa@nic_per_numa"

    def collect_blueprint_data(self, **kwargs):
        numa_NICs = {}
        relevant_ports = []

        nic_collector = NICBlueprintDataCollector(host_executor=self._host_executor)
        nics_and_ports = nic_collector.get_nic_ports_names_dict()
        for nic in nics_and_ports:
            relevant_ports.extend(nics_and_ports[nic])

        numa_ids = self.get_ids()
        prefix_of_numa_id = next(iter(numa_ids))[:-1]
        for numa_id in numa_ids:
            numa_NICs[numa_id] = []

        dir_path = '/sys/class/net/'
        for port in relevant_ports:
            device_path = os.path.join(dir_path, port)
            file_path = os.path.join(device_path, "device/numa_node")
            if self.file_utils.is_dir_exist(device_path) and self.file_utils.is_file_exist(file_path):
                numa_node = abs(self.get_int_output_from_run_cmd(
                    "cat {}".format(file_path), hosts_cached_pool=BlueprintDataCollector.cached_data_pool))
                numa_id = '{}{}'.format(prefix_of_numa_id, numa_node)
                numa_NICs[numa_id].append(port)
        return numa_NICs


class NumaCpus(NUMA):
    def get_blueprint_objective_key_name(self):
        return "Numa@cpus_per_numa"

    def collect_blueprint_data(self, **kwargs):
        cmd = "lscpu | grep NUMA"
        lscpu_yaml = self.get_output_from_run_cmd(cmd, hosts_cached_pool=BlueprintDataCollector.cached_data_pool)
        lscpu_dict = PythonUtils.get_dict_from_string(lscpu_yaml, 'yaml')
        res = {}

        for numa_id in self.get_system_ids():
            numa_number = re.findall(r"\d+", numa_id)

            if len(numa_number) != 1:
                raise UnExpectedSystemOutput(self.get_host_ip(), "", numa_id, "expected to have only 1 number in "
                                                                              "numa id")
            res[numa_id] = lscpu_dict.get("NUMA node{} CPU(s)".format(numa_number[0]))

        return res
