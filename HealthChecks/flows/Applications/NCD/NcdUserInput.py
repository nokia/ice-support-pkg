from __future__ import absolute_import
import json
from os import path
from six.moves import input


def get_user_input(prompt):
    user_input = input(prompt)
    return user_input


def append_to_json(config_file, parameters_to_insert, fqdn_to_insert):
    with open(config_file, "r+") as file:
        data = json.load(file)
        data.update(parameters_to_insert)
        fqdn_list = data.get("fqdn_list")
        for fqdn in fqdn_to_insert:
            fqdn_list.append(fqdn)
        file.seek(0)
        json.dump(data, file, indent=4, sort_keys=True)


def main():
    config_path = path.join(path.dirname(path.abspath(__file__)), 'ncd_config.json')
    input_parameters = {"ncom_url": ""}
    input_fqdns = ["ncd-core", "ncd-key-cloak", "ncd-Harbor", "ncd-artifactory"]
    fqdns_values = []
    input_parameters['ncom_url'] = get_user_input(prompt="Please enter the ncom_url, format: https://<rest_of_url> "
                                                         "if none, please press enter: ")
    for fqdn in input_fqdns:
        value = get_user_input(prompt="Please enter the {} FQDN to be configured, if none, please press enter: ".format(
            fqdn))
        if value:
            fqdns_values.append(value)

    append_to_json(config_file=config_path, parameters_to_insert=input_parameters, fqdn_to_insert=fqdns_values)


if __name__ == '__main__':
    main()
