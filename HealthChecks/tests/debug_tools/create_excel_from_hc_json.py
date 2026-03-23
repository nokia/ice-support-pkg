from __future__ import absolute_import
from __future__ import print_function
import sys, os
import argparse
import json

import pandas as pd
import re
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "ice", "lib"))

ORGANIZED_JSON_FILE_NAME = 'organized.json'

def create_organized_json_file(folder_path):
    updated_organized_json = get_organized_json(folder_path)

    organized_json_path = os.path.join(folder_path, ORGANIZED_JSON_FILE_NAME)
    with open(organized_json_path, 'w') as outfile:
        json.dump(updated_organized_json, outfile, indent=4)

    return updated_organized_json

def get_organized_json(folder_path):
    updated_organized_json = {}
    for file_name in os.listdir(folder_path):
        system_versions_info = {}
        if file_name.endswith('.json'):
            if file_name == ORGANIZED_JSON_FILE_NAME:
                continue
            cluster_name = get_cluster_name(file_name)
            json_file_path = os.path.join(folder_path, file_name)
            with open(json_file_path, 'r') as file:
                try:
                    json_data = json.load(file)
                    new_organized_json = build_new_json(cluster_name, json_data)
                except ValueError as e:
                    print("Error decoding JSON in file {}: {}".format(json_file_path, e))
            log_file_path = json_file_path.replace('.json', '.log')
            if os.path.exists(log_file_path):
                system_versions_info = get_versions_info(log_file_path, cluster_name)
            combined_dict = {**system_versions_info, **new_organized_json}
            if not combined_dict:
                combined_dict = generate_dict_if_empty_results(updated_organized_json, cluster_name)
            updated_organized_json = merge_json(updated_organized_json, combined_dict, cluster_name)
    return updated_organized_json

def generate_dict_if_empty_results(updated_organized_json, cluster_name):
    existing_validation = list(updated_organized_json.keys())[0]
    combined_dict = {
        existing_validation: {
            cluster_name: {}
        }
    }
    return combined_dict

def get_cluster_name(file_name):
    base_name, extension = os.path.splitext(file_name)
    cluster_name = base_name.replace('_HealthChecksSummary', '')
    return cluster_name

def get_versions_info(log_file_path, cluster_name):
    system_info = {'ice_version': {cluster_name: {'final_status': '', 'final_severity': '', 'documentation_link': ''}},
                   'product_version': {cluster_name: {'final_status': '', 'final_severity': '', 'documentation_link': ''}}}
    with open(log_file_path, 'r') as log_file:
        for line in log_file:
            match_ice = re.search(r'Health check version (\S+) starting:', line)
            if match_ice:
                system_info['ice_version'][cluster_name]['final_status'] = match_ice.group(1)
            if 'Product version: ' in line:
                system_info['product_version'][cluster_name]['final_status'] = line.split('Product version:')[1].strip()
            if system_info['ice_version'][cluster_name]['final_status'] and system_info['product_version'][cluster_name]['final_status']:
                return system_info
    return system_info

def build_new_json(cluster_name, json_data):
    organized_json = get_organized_json_by_validations(cluster_name, json_data)
    for validation_data in list(organized_json.values()):
        if validation_data[cluster_name].get('results'):
            not_all_pass = any(
                item['pass'] != "True" and item['pass'] != True and item['pass'] != "--" for item in validation_data[cluster_name]['results'])
            validation_data[cluster_name]['relevance_for_app'] = get_higher_value_of_relevancy(validation_data[cluster_name]['results'])
            if not_all_pass:
                validation_data[cluster_name]['final_status'] = get_final_status(validation_data[cluster_name]['results'])
                if any(item['documentation_link'] for item in validation_data[cluster_name]['results']):
                    for item in validation_data[cluster_name]['results']:
                        if item.get('documentation_link'):
                            validation_data[cluster_name]['documentation_link'] = item['documentation_link']
                            break
            else:
                validation_data[cluster_name]['final_status'] = 'True'
    return organized_json

def get_final_status(validation_results):
    for status in ['NA', 'sys_problem']:
        if any(item['pass'] == status for item in validation_results):
            return status
    return 'False'

def get_higher_value_of_relevancy(list_of_relevancy):
    if list_of_relevancy and isinstance(list_of_relevancy[0], dict):
        higher_value_of_relevancy =  max([item['relevance_for_app'] for item in list_of_relevancy])
    else:
        higher_value_of_relevancy = max([int(x) for x in list_of_relevancy])
    return higher_value_of_relevancy

def check_if_ncs(json_data):
    for flow in json_data:
        if flow['command_name'] == 'test_k8s_basics':
            return True
    return False

def get_organized_json_by_validations(cluster_name, json_data):
    organized_json = {}
    for flow in json_data:
        flow_name = flow['command_name']
        for host_name, validations in list(flow['details'].items()):
            for validation_data in list(validations.values()):
                validation_name = validation_data['description_title']
                pass_status = validation_data.get('pass', '')
                host_ip = validation_data.get('host_ip', '')
                relevance_for_app = validation_data.get('relevance_for_app', '0')
                documentation_link = validation_data.get('documentation_link', '')

                if validation_name not in organized_json:
                    organized_json[validation_name] = {}
                    organized_json[validation_name][cluster_name] = {}
                    organized_json[validation_name][cluster_name]['results'] = []

                organized_json[validation_name][cluster_name]['results'].append(
                    {'host_name': host_name, 'host_ip': host_ip, 'pass': pass_status, 'relevance_for_app': relevance_for_app,
                     'documentation_link': documentation_link, 'flow_name': flow_name})
    return organized_json

def merge_json(exist_json, new_json, cluster_name):
    for validation_name, validation_data in list(new_json.items()):
        if not exist_json.get(validation_name):
            exist_json[validation_name] = {}
        exist_json[validation_name][cluster_name] = {}
        exist_json[validation_name][cluster_name]['results'] = new_json[validation_name][cluster_name].get('results')
        exist_json[validation_name][cluster_name]['final_status'] = new_json[validation_name][cluster_name].get('final_status')
        exist_json[validation_name][cluster_name]['relevance_for_app'] = new_json[validation_name][cluster_name].get('relevance_for_app', '0')
        exist_json[validation_name][cluster_name]['documentation_link'] = new_json[validation_name][cluster_name].get('documentation_link', '')
    return exist_json

def save_json_data_on_excel(json_data, excel_path):
    data_list = []
    column_order = ["Validation name", "Relevance for app", "Confluence link"]
    for validation_name, validation_data in list(json_data.items()):
        relevance_list = []
        documentation_link = ''
        validation_info = {"Validation name": validation_name, "Relevance for app": "", "Confluence link": ""}
        for cluster_name in validation_data:
            if cluster_name not in column_order:
                column_order.append(cluster_name)
            final_status = validation_data[cluster_name].get("final_status", "")
            relevance_list.append(validation_data[cluster_name].get("relevance_for_app"))
            if validation_data[cluster_name].get("documentation_link") and not documentation_link:
                documentation_link = validation_data[cluster_name].get("documentation_link")
            validation_info[cluster_name] = final_status
        validation_info["Relevance for app"] = get_higher_value_of_relevancy(relevance_list)
        validation_info["Confluence link"] = documentation_link
        data_list.append(validation_info)

    df = pd.DataFrame(data_list, columns=column_order)
    excel_file_name = os.path.join(excel_path, "validations_results.xlsx")
    df.to_excel(excel_file_name, index=False)
    print("Excel file {}' created successfully.".format(excel_file_name))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Creating excel file with all validations status by json files")
    parser.add_argument('-f', '--json-path', type=str, help='Path of folder including out json files', required=True)
    args = parser.parse_args()
    folder_path = args.json_path

    updated_organized_json = create_organized_json_file(folder_path)
    save_json_data_on_excel(updated_organized_json, folder_path)
