from __future__ import absolute_import
from __future__ import print_function
import argparse
import json
import os

BLUEPRINT_CUSTOMERS_OUT_FOLDER_PATH = "customers_blueprint_data"


def main():
    parser = argparse.ArgumentParser(description="Convert blueprint validation json output to blueprint json.")
    parser.add_argument('-f', '--file_path', type=str, help='Path to validation json out file.')
    args = parser.parse_args()
    json_out_path = args.file_path

    with open(r"{}".format(json_out_path)) as f:
        validation_data = json.load(f)

    blueprint_hw_details, blueprint_firmware_details = get_blueprint_hw_fw_details(validation_data)
    blueprint_name = blueprint_hw_details["blueprint_name"]
    print("Blueprint name is '{}'".format(blueprint_name))
    hw_pairs_data = blueprint_hw_details["pairs_data"]
    customer_hw_blueprint_result = get_customer_blueprint_result(hw_pairs_data, get_hw_topic_data)
    customer_firmware_blueprint_result = get_customer_blueprint_result(blueprint_firmware_details, get_fw_topic_data)

    create_json_file_with_results(blueprint_name, customer_hw_blueprint_result, "HW")
    create_json_file_with_results(blueprint_name, customer_firmware_blueprint_result, "Firmware")


def get_customer_blueprint_result(hw_pairs_data, get_topic_data_func):
    customer_hw_blueprint_result = {}

    for role, role_data in list(hw_pairs_data.items()):
        customer_hw_blueprint_result[role] = {}
        for topic_name, topic_data in list(role_data.items()):
            customer_hw_blueprint_result[role][topic_name] = get_topic_data_func(topic_data)

    return customer_hw_blueprint_result


def create_json_file_with_results(blueprint_name, customer_blueprint_result, sub_dir):
    res_file_path = os.path.join(BLUEPRINT_CUSTOMERS_OUT_FOLDER_PATH, sub_dir, "new_" + blueprint_name + ".json")

    if os.path.exists(res_file_path):
        version = 0
        while True:
            res_file_path = os.path.join(
                BLUEPRINT_CUSTOMERS_OUT_FOLDER_PATH, sub_dir, "new_" + blueprint_name + "_v" + str(version) + ".json")
            if not os.path.exists(res_file_path):
                blueprint_name = blueprint_name + "_v" + str(version)
                break
            version += 1
    res_file_path = os.path.join(BLUEPRINT_CUSTOMERS_OUT_FOLDER_PATH, sub_dir, "new_" + blueprint_name + ".json")
    print("{} json file of blueprint '{}' is located at {}".format(sub_dir,blueprint_name, res_file_path))

    with open(res_file_path, "w") as f:
        json.dump(customer_blueprint_result, f, indent=2)


def get_blueprint_hw_fw_details(validation_data):
    for validation in validation_data:
        if validation.get("command_name") == "blueprint":
            host = list(validation["details"].keys())[0]
            blueprint_hw_details = validation["details"][host]["info_validate_is_hw_blueprint"]["system_info"]
            blueprint_fw_details = validation["details"][host]["info_validate_is_fw_blueprint"]["system_info"]
            break

    return blueprint_hw_details, blueprint_fw_details


def get_hw_topic_data(topic_data):
    res = []

    for topic_id, topic_id_data in list(topic_data.items()):
        topic_id_res = {}
        for collector_name, collector_data in list(topic_id_data["system output"].items()):
            topic_id_res[collector_name] = collector_data if type(
                collector_data) is not dict else list(collector_data.keys())
        res.append(topic_id_res)

    if len(res) == 1:
        res = res[0]

    return res


def get_fw_topic_data(topic_data):
    res = []

    for topic_id, topic_id_data in list(topic_data.items()):
        topic_id_res = {}
        for collector_name, collector_data in list(topic_id_data.items()):
            topic_id_res[collector_name] = collector_data if type(
                collector_data) is not dict else list(collector_data.keys())
        res.append(topic_id_res)

    if len(res) == 1:
        res = res[0]

    return res


if __name__ == '__main__':
    main()
