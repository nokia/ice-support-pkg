from __future__ import absolute_import
from __future__ import print_function
import json
import os
# from json import JSONDecodeError
import sys
from os import listdir

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../..")))
from tests.debug_tools.debug_tools_helper import *


def get_all_hosts_logs(updated_dict):
    all_host_logs_list = None

    for key, value in list(updated_dict.items()):
        if not all_host_logs_list:
            all_host_logs_list = value
        else:
            all_host_logs_list = list(set(all_host_logs_list) & set(value))
    return all_host_logs_list


def remove_all_hosts_logs_from_other_hosts(updated_dict):
    for key, value in list(updated_dict.items()):
        updated_dict[key] = list(set(value).difference(updated_dict["Objectives.ALL_HOSTS"]))


def write_dict_in_file(out_dir, updated_dict):
    cbis_logs_path = os.path.join(out_dir, "CBIS_log_of_interest_dict.hjson")
    with open(cbis_logs_path, "w") as f:
        f.write(json.dumps(updated_dict, indent=4))

    print("\nsave file in {}".format(cbis_logs_path))


updated_dict = {}
cbis_roles_list = ["undercloud", "hypervisor", "controllers", "computes", "storages"]
# computes_roles_list = ["SRIOV_computes", "OvsCompute", "DpdkCompute", "AvrsCompute"]

objectives_dict = {
    "undercloud": "Objectives.UC",
    "hypervisor": "Objectives.HYP",
    "controllers": "Objectives.CONTROLLERS",
    # "AvrsCompute":"Objectives.AVRS_COMPUTES",
    "storages": "Objectives.STORAGE",
    "computes": "Objectives.COMPUTES",
    # "SRIOV_computes":"Objectives.SRIOV_COMPUTES",
    # "OvsCompute":"Objectives.OVS_COMPUTES",
    # "DpdkCompute":"Objectives.DpdkCompute",

}


def main():
    out_dir = DebugToolsHelper.get_out_dir()
    for ip in listdir(out_dir):
        ip_path = os.path.join(out_dir, ip)
        if os.path.isdir(ip_path):
            for file_name in listdir(ip_path):
                if ".decrypted.json" in file_name:
                    with open(os.path.join(ip_path, file_name), "r") as f:
                        origin_dict = json.load(f)
                        if origin_dict[0]["details"].get("undercloud - localhost") and origin_dict[0]["details"][
                            "undercloud - localhost"].get("info_LogsVal"):
                            for key, value in list(origin_dict[0]["details"]["undercloud - localhost"]["info_LogsVal"][
                                "system_info"].items()):
                                for objective_host in cbis_roles_list:
                                    if type(value) is str and value == "None":
                                        break
                                    if type(value) is dict and value.get("roles") and objective_host in value["roles"]:
                                        # if objective_host != "compute":
                                        updated_dict.setdefault(objectives_dict[objective_host], []).extend(
                                            value["log_files"])
                                        # else:
                                        #     for compute_host_type in computes_roles_list:
                                        #         if compute_host_type in value["roles"]:
                                        #             updated_dict.setdefault(objectives_dict[compute_host_type], []).extend(value["log_files"])
                                        break
    for key, value in list(updated_dict.items()):
        updated_dict[key] = list(set(value))

    # all_host_logs_list = get_all_hosts_logs(updated_dict)
    # remove_all_hosts_logs_from_other_hosts(updated_dict)
    # updated_dict["Objectives.ALL_HOSTS"] = all_host_logs_list
    write_dict_in_file(DebugToolsHelper.get_out_dir(), updated_dict)


if __name__ == '__main__':
    DebugToolsHelper.run_flow(flow_name="logs_by_roles")
    main()
