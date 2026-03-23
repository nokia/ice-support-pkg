from __future__ import absolute_import
from __future__ import print_function
import csv
import json
import os
import sys
from os import listdir
import datetime
from six.moves import range

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../..")))
from tests.debug_tools.debug_tools_helper import *


def create_csv_file(ls, file_name):
    with open(file_name, "wb") as f_out:
        writer = csv.writer(f_out)
        writer.writerows(ls)


def create_setups_results_dict(out_dir):
    setups_results_dict = {}
    deployment_types_list = ["cbis", "ncs"]
    for ip in listdir(out_dir):
        ip_path = os.path.join(out_dir, ip)
        if os.path.isdir(ip_path):
            for file_name in listdir(ip_path):
                if ".decrypted.json" in file_name:
                    setups_results_dict = get_setups_results_dict_by_file(out_dir, file_name, deployment_types_list, ip,
                                                                          setups_results_dict)
    return setups_results_dict


def get_setups_results_dict_by_file(out_dir, file_name, deployment_types_list, ip, setups_results_dict):
    ip_path = os.path.join(out_dir, ip)
    with open(os.path.join(ip_path, file_name), "r") as f:
        origin_dict = json.load(f)
        for flow_index in range(len(origin_dict)):
            for host in origin_dict[flow_index]["details"]:
                if origin_dict[flow_index]["details"][host].get("info_find_certificates"):
                    system_info_dict = origin_dict[flow_index]["details"][host]["info_find_certificates"][
                        "system_info"]
                    for deployment_type_item in deployment_types_list:
                        if system_info_dict.get("deployment_type") and \
                                deployment_type_item in system_info_dict["deployment_type"]:
                            setups_results_dict.setdefault(deployment_type_item, {})
                            setup_name = "{} {} {} {}".format(ip, system_info_dict.get("cluster_name", ""),
                                                              deployment_type_item,
                                                              system_info_dict["version"])
                            setups_results_dict[deployment_type_item][setup_name] = system_info_dict
    return setups_results_dict


def convert_setups_results_to_list(setups_dict):
    all_paths_list = []
    setups_results_list = []
    for setup, files_dict in list(setups_dict.items()):
        for key, value in list(files_dict.items()):
            if type(value) is list:
                all_paths_list.extend(value)
    all_paths_list = list(set(all_paths_list))
    paths_dict = {}
    for setup, files_dict in list(setups_dict.items()):
        for path in all_paths_list:
            hosts = [i for i in files_dict if path in files_dict[i]]
            hosts = hosts[0] if len(hosts) else "Not supported for deployment type"
            if hosts == "missing_paths":
                hosts = "NULL"
            paths_dict.setdefault(path, []).append(hosts)
    setups_results_list.append(["paths"] + list(setups_dict.keys()))
    for path, hosts_list in list(paths_dict.items()):
        if "NULL" in hosts_list and set(hosts_list) == {"NULL"}:
            hosts_list = ["Not found"] * len(hosts_list)
        setups_results_list.append([path] + hosts_list)
    return setups_results_list


def main():
    RUNNING_DATE = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_dir = DebugToolsHelper.get_out_dir()
    DebugToolsHelper.run_flow(flow_name="certificates_by_roles")
    for deployment_type, setups_dict in list(create_setups_results_dict(out_dir).items()):
        file_name = "{}_certificates_{}.csv".format(os.path.join(out_dir, deployment_type), RUNNING_DATE)
        create_csv_file(convert_setups_results_to_list(setups_dict), file_name)
        print("save {}".format(file_name))


if __name__ == '__main__':
    main()
