from __future__ import absolute_import
from tools.UI.VmsProcessResultDict import VmsProcessResultDict
from prettytable import PrettyTable


def get_table_string(name, headers, rows):
    table = PrettyTable()
    table.max_table_width = 60
    table.field_names = headers
    for row in rows:
        table.add_row(row)
    return "{}\n{}".format(name, table)


def get_section(title, items_list):
    title = """
---------------------------------------------------
{}
---------------------------------------------------
    """.format(title)
    return "{}\n{}".format(title, '\n'.join(items_list))


def get_vms_domains_section(title, domains_dict):
    domain_sections_list = []
    for domain in domains_dict:
        tables_list = []
        for info_name in domains_dict[domain]:
            table_data = domains_dict[domain][info_name]
            table_element = get_table_string(table_data['name'], table_data['header'], table_data['fields'])
            tables_list.append(table_element)
        domain_section = get_section(domain, tables_list)
        domain_sections_list.append(domain_section)
    wrapper_section = get_section(title, domain_sections_list)
    return wrapper_section


def create_vms_summary_cli(result_dict):
    printed_lines = []
    result_dict_processor = VmsProcessResultDict(result_dict, include_help_text=False)
    processed_result = result_dict_processor.get_processed_dict()
    vm_name_id_dict = result_dict_processor.get_vm_name_id_dict(result_dict)
    printed_lines.append('Vms Info')

    for host_name in processed_result:
        info_sections = []
        host_section = get_vms_domains_section('Host Info', processed_result[host_name]['host_info'])
        info_sections.append(host_section)
        vms_sections_list = []
        if len(processed_result[host_name]['vms_info']):
            for vm_id in processed_result[host_name]['vms_info']:
                vm_title = 'vm name : {}\nvm id: {}'.format(vm_name_id_dict.get(vm_id), vm_id)
                vm_domains_section = get_vms_domains_section(vm_title, processed_result[host_name]['vms_info'][vm_id])
                vms_sections_list.append(vm_domains_section)
            vms_info_section = get_section('Vms Info', vms_sections_list)
            info_sections.append(vms_info_section)
        host_element = get_section(host_name, info_sections)

        printed_lines.append(host_element)

    return '\n'.join(printed_lines)

