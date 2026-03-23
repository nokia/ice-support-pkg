from __future__ import absolute_import
from collections import OrderedDict


def get_os_disk_data_scenario(lab_name):

    id_ = 'disk used for / (root filesystem)'

    # no actual need to be this specific, but I had the data:
    info_from_fi803 = OrderedDict([
     ('operating_system_disk@name', OrderedDict(
      [(u'fi-803-hpe-bm-workerbm-1', {'disk used for / (root filesystem)': u'sda'}),
       (u'fi-803-hpe-bm-storagebm-0', {'disk used for / (root filesystem)': u'sda'}),
       (u'fi-803-hpe-bm-storagebm-1', {'disk used for / (root filesystem)': u'sda'}),
       (u'fi-803-hpe-bm-storagebm-2', {'disk used for / (root filesystem)': u'sda'}),
       (u'fi-803-hpe-bm-edgebm-0', {'disk used for / (root filesystem)': u'sda'}),
       (u'fi-803-hpe-bm-masterbm-1', {'disk used for / (root filesystem)': u'sda'}),
       (u'fi-803-hpe-bm-workerbm-0', {'disk used for / (root filesystem)': u'sda'}),
       (u'fi-803-hpe-bm-edgeipv6-0', {'disk used for / (root filesystem)': u'sda'}),
       (u'fi-803-hpe-bm-workerbm-2', {'disk used for / (root filesystem)': u'sda'}),
       (u'fi-803-hpe-bm-masterbm-0', {'disk used for / (root filesystem)': u'sda'}),
       (u'fi-803-hpe-bm-edgebm-1', {'disk used for / (root filesystem)': u'sda'}),
       (u'fi-803-hpe-bm-masterbm-2', {'disk used for / (root filesystem)': u'sda'})])),
     ('operating_system_disk@type', OrderedDict(
      [(u'fi-803-hpe-bm-workerbm-1', {'disk used for / (root filesystem)': 'SSD'}),
       (u'fi-803-hpe-bm-storagebm-0', {'disk used for / (root filesystem)': 'SSD'}),
       (u'fi-803-hpe-bm-storagebm-1', {'disk used for / (root filesystem)': 'SSD'}),
       (u'fi-803-hpe-bm-storagebm-2', {'disk used for / (root filesystem)': 'SSD'}),
       (u'fi-803-hpe-bm-edgebm-0', {'disk used for / (root filesystem)': 'SSD'}),
       (u'fi-803-hpe-bm-masterbm-1', {'disk used for / (root filesystem)': 'SSD'}),
       (u'fi-803-hpe-bm-workerbm-0', {'disk used for / (root filesystem)': 'SSD'}),
       (u'fi-803-hpe-bm-edgeipv6-0', {'disk used for / (root filesystem)': 'SSD'}),
       (u'fi-803-hpe-bm-workerbm-2', {'disk used for / (root filesystem)': 'SSD'}),
       (u'fi-803-hpe-bm-masterbm-0', {'disk used for / (root filesystem)': 'SSD'}),
       (u'fi-803-hpe-bm-edgebm-1', {'disk used for / (root filesystem)': 'SSD'}),
       (u'fi-803-hpe-bm-masterbm-2', {'disk used for / (root filesystem)': 'SSD'})])),
     ('operating_system_disk@size_in_mb', OrderedDict(
      [(u'fi-803-hpe-bm-workerbm-1', {'disk used for / (root filesystem)': '915715'}),
       (u'fi-803-hpe-bm-storagebm-0', {'disk used for / (root filesystem)': '457862'}),
       (u'fi-803-hpe-bm-storagebm-2', {'disk used for / (root filesystem)': '457862'}),
       (u'fi-803-hpe-bm-storagebm-1', {'disk used for / (root filesystem)': '457862'}),
       (u'fi-803-hpe-bm-edgebm-0', {'disk used for / (root filesystem)': '915715'}),
       (u'fi-803-hpe-bm-masterbm-1', {'disk used for / (root filesystem)': '915715'}),
       (u'fi-803-hpe-bm-workerbm-0', {'disk used for / (root filesystem)': '915715'}),
       (u'fi-803-hpe-bm-edgeipv6-0', {'disk used for / (root filesystem)': '915715'}),
       (u'fi-803-hpe-bm-workerbm-2', {'disk used for / (root filesystem)': '915715'}),
       (u'fi-803-hpe-bm-masterbm-0', {'disk used for / (root filesystem)': '915715'}),
       (u'fi-803-hpe-bm-edgebm-1', {'disk used for / (root filesystem)': '915715'}),
       (u'fi-803-hpe-bm-masterbm-2', {'disk used for / (root filesystem)': '915715'})]))])

    info_from_fi819 = OrderedDict([
     ('operating_system_disk@name', OrderedDict(
      [('overcloud-controller-v20-819-lab1-3', {'disk used for / (root filesystem)': u'sda,sdb'}),
       ('overcloud-controller-v20-819-lab1-2', {'disk used for / (root filesystem)': u'sda,sdb'}),
       ('overcloud-controller-v20-819-lab1-1', {'disk used for / (root filesystem)': u'sda,sdb'}),
       ('overcloud-sriovperformancecompute-v20-819-lab1-1', {'disk used for / (root filesystem)': u'sda,sdb'}),
       ('overcloud-ovscompute-v20-819-lab1-1', {'disk used for / (root filesystem)': u'sda,sdb'}),
       ('overcloud-storage-v20-819-lab1-4', {'disk used for / (root filesystem)': u'sda'}),
       ('overcloud-storage-v20-819-lab1-1', {'disk used for / (root filesystem)': u'sda'}),
       ('overcloud-sriovperformancecompute-v20-819-lab1-0', {'disk used for / (root filesystem)': u'sda,sdb'}),
       ('overcloud-sriovperformancecompute-v20-819-lab1-2', {'disk used for / (root filesystem)': u'sda,sdb'}),
       ('overcloud-storage-v20-819-lab1-2', {'disk used for / (root filesystem)': u'sda'}),
       ('overcloud-ovscompute-v20-819-lab1-2', {'disk used for / (root filesystem)': u'sda,sdb'}),
       ('overcloud-ovscompute-v20-819-lab1-3', {'disk used for / (root filesystem)': u'sda,sdb'})])),
     ('operating_system_disk@type', OrderedDict(
      [('overcloud-controller-v20-819-lab1-3', {'disk used for / (root filesystem)': 'SSD,SSD'}),
       ('overcloud-controller-v20-819-lab1-2', {'disk used for / (root filesystem)': 'SSD,SSD'}),
       ('overcloud-controller-v20-819-lab1-1', {'disk used for / (root filesystem)': 'SSD,SSD'}),
       ('overcloud-ovscompute-v20-819-lab1-1', {'disk used for / (root filesystem)': 'SSD,SSD'}),
       ('overcloud-sriovperformancecompute-v20-819-lab1-1', {'disk used for / (root filesystem)': 'SSD,SSD'}),
       ('overcloud-storage-v20-819-lab1-4', {'disk used for / (root filesystem)': 'SSD'}),
       ('overcloud-storage-v20-819-lab1-1', {'disk used for / (root filesystem)': 'SSD'}),
       ('overcloud-sriovperformancecompute-v20-819-lab1-0', {'disk used for / (root filesystem)': 'SSD,SSD'}),
       ('overcloud-storage-v20-819-lab1-2', {'disk used for / (root filesystem)': 'SSD'}),
       ('overcloud-sriovperformancecompute-v20-819-lab1-2', {'disk used for / (root filesystem)': 'SSD,SSD'}),
       ('overcloud-ovscompute-v20-819-lab1-2', {'disk used for / (root filesystem)': 'SSD,SSD'}),
       ('overcloud-ovscompute-v20-819-lab1-3', {'disk used for / (root filesystem)': 'SSD,SSD'})])),
     ('operating_system_disk@size_in_mb', OrderedDict(
      [('overcloud-controller-v20-819-lab1-3', {'disk used for / (root filesystem)': '915715,915715'}),
       ('overcloud-controller-v20-819-lab1-2', {'disk used for / (root filesystem)': '915715,915715'}),
       ('overcloud-controller-v20-819-lab1-1', {'disk used for / (root filesystem)': '915715,915715'}),
       ('overcloud-ovscompute-v20-819-lab1-1', {'disk used for / (root filesystem)': '915715,915715'}),
       ('overcloud-sriovperformancecompute-v20-819-lab1-1', {'disk used for / (root filesystem)': '915715,915715'}),
       ('overcloud-storage-v20-819-lab1-4', {'disk used for / (root filesystem)': '457862'}),
       ('overcloud-storage-v20-819-lab1-1', {'disk used for / (root filesystem)': '457862'}),
       ('overcloud-sriovperformancecompute-v20-819-lab1-0', {'disk used for / (root filesystem)': '915715,915715'}),
       ('overcloud-storage-v20-819-lab1-2', {'disk used for / (root filesystem)': '457862'}),
       ('overcloud-sriovperformancecompute-v20-819-lab1-2', {'disk used for / (root filesystem)': '915715,915715'}),
       ('overcloud-ovscompute-v20-819-lab1-2', {'disk used for / (root filesystem)': '915715,915715'}),
       ('overcloud-ovscompute-v20-819-lab1-3', {'disk used for / (root filesystem)': '915715,915715'})]))])

    scenario_dict = None
    if '803' in lab_name:
        scenario_dict = info_from_fi803
    if '819' in lab_name:
        scenario_dict = info_from_fi819

    if '803-bad' in lab_name:
        scenario_dict['operating_system_disk@type']['fi-803-hpe-bm-storagebm-1'][id_] = 'NVMe'
    if '819-bad' in lab_name:
        scenario_dict['operating_system_disk@size_in_mb']['overcloud-controller-v20-819-lab1-1'][id_] = '457862,457862'

    return scenario_dict


def get_os_disk_data_scenario_nodes(lab_name):
    scenario_dict = get_os_disk_data_scenario(lab_name)
    one_objective_name = list(scenario_dict.keys())[0]
    node_names = list(scenario_dict[one_objective_name].keys())
    return node_names
