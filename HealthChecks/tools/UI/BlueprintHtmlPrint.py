from __future__ import absolute_import
import six

from flows.Blueprint.BlueprintValidations import ValidateBlueprint
from tools.UI.HTMLBuilder import HTMLBuilder
from collections import OrderedDict


class BlueprintHtmlPrint:
    table_id_counter = 0
    print_table = False

    def create_blueprint_html_tab(self, roles_json, name_table):
        note = 'Please note that information provided show only differentiation from known configuration, and does ' \
               'not necessarily indicate a non-blueprint state'
        table_elements_list = []
        
        note_element = HTMLBuilder.create_element('div', [note], {"class": "center width_90 middle_font"})
        table_elements_list.append(note_element)
        table_elements_list += name_table + self.create_table(roles_json)

        properties_dict = {"id": "innerTab" + BlueprintHtmlPrint.get_id_prefix() + self.get_id(), "class": "tabContent",
                           "style": self.get_display_properties()}

        return HTMLBuilder.create_element('div', table_elements_list, properties_dict)

    def create_table(self, roles_json):
        tables_elements = []
        if roles_json == {}:
            tables_elements.append(HTMLBuilder.create_element("h1", ["Failed to collect data."]))
        else:
            for role, role_data in list(roles_json.items()):
                table = self.create_blueprint_table_rows(role_data, role)
                tables_elements.append(table)
                tables_elements.append("<br>")
        return tables_elements

    def get_display_properties(self):
        return "display: none"

    def get_cell_properties(self):
        return {}

    @staticmethod
    def get_id():
        assert False, "Please implement get_id"

    @staticmethod
    def get_id_prefix():
        return "blueprint"

    def create_blueprint_table_rows(self, role_data, title):
        rows = []
        header_element = self.create_blueprint_header_element()
        table_title_element = HTMLBuilder.create_table_title_element(
            title=title.replace("_", " ").capitalize(), title_properties_dict={"class": "center width_90 middle_font"})

        self.print_table = False

        for topic, topic_data in list(role_data.items()):
            for id_, id_data in list(self.get_pairs(topic_data).items()):
                topic_remarks = topic_data.get("knowledge_data", {})
                rows += self.get_id_rows(id_, id_data, title, topic, topic_remarks)

        if not self.print_table:
            table_element = HTMLBuilder.create_element('h6', ["No data"])
            return HTMLBuilder.create_element('div', [table_title_element, table_element])

        body_element = HTMLBuilder.create_element('tbody', rows)
        table_element = HTMLBuilder.create_element('table', [header_element, body_element],
                                                   {"class": "width_90 center", "border": "1",
                                                    "style": "font-size:80%"}
                                                   )

        table_with_title = HTMLBuilder.create_element('div', [table_title_element, table_element],
                                                      {"class": "fixTableHead"})

        return table_with_title

    def get_pairs(self, topic_data):
        return topic_data.get("pairs_by_id", {})

    def create_blueprint_header_element(self):
        header_row = self.get_header_rows()
        cells_list_header = []

        for item in header_row:
            cell_element = HTMLBuilder.create_cell(item, is_title=True)
            cells_list_header.append(cell_element)

        columns_row_element = HTMLBuilder.create_element('tr', cells_list_header)

        return HTMLBuilder.create_element('thead', [columns_row_element])

    def get_id_rows(self, id_, id_data, title, topic, topic_remarks):
        res = []
        blueprint_properties = id_data.get("expected blueprint", {})
        system_properties = id_data.get("system output", {})
        if id_data.get("hosts", {}):
            id_hosts = OrderedDict()
            id_hosts['Missing on hosts'] = id_data.get("hosts").get('Missing on hosts')
            id_hosts['Existing on hosts'] = id_data.get("hosts").get('Existing on hosts')
            id_ = {id_: id_hosts}
        properties_names = set(list(blueprint_properties.keys()) + list(system_properties.keys()))
        for property_index, property_name in enumerate(properties_names):
            merge_len = len(properties_names)
            property_remarks = topic_remarks.get(property_name, [])
            property_remarks_str = "\n".join([remark["remark"] for remark in property_remarks])
            cells_elements_list = self.get_blueprint_table_line_cells(blueprint_properties, id_, merge_len,
                                                                      property_index, property_name, system_properties,
                                                                      topic,
                                                                      "{}_{}".format(title,
                                                                                     BlueprintHtmlPrint.table_id_counter
                                                                                     ), property_remarks_str)
            BlueprintHtmlPrint.table_id_counter += 1
            res.append(HTMLBuilder.create_element('tr', cells_elements_list))

        return res

    def get_blueprint_table_line_cells(self, blueprint_properties, id_, merge_len, property_index,
                                       property_name, system_properties, topic, element_id, property_remarks):
        element_id = "b_id_{}".format(element_id)
        expected_value = self.convert_range_column(blueprint_properties.get(property_name, ""))
        actual_value = system_properties.get(property_name, {}).get('value', "")
        is_equal = self.is_system_value_collect_succeeded(
            is_equal=system_properties.get(property_name, {}).get('is equal', ""), system_value=actual_value)
        if actual_value:
            self.print_table = True

        if property_index == 0:
            cells_elements_list = [HTMLBuilder.create_element('td', [topic], {"rowspan": str(merge_len)}),
                                   HTMLBuilder.create_host_details_by_click_cell(
                                       id_, element_id + "_0", properties_dict={"rowspan": str(merge_len)},
                                       msg="Failed to get ID for some hosts"),
                                   HTMLBuilder.create_cell(property_name),
                                   HTMLBuilder.create_host_details_by_click_cell(
                                       expected_value, element_id + "_1", is_equal,
                                       self.get_cell_properties()),
                                   HTMLBuilder.create_host_details_by_click_cell(
                                       actual_value, element_id + "_2", is_equal),
                                   HTMLBuilder.create_cell(property_remarks)]

        else:
            cells_elements_list = [HTMLBuilder.create_cell(property_name),
                                   HTMLBuilder.create_host_details_by_click_cell(
                                       expected_value, element_id + "_0", is_equal,
                                       self.get_cell_properties()),
                                   HTMLBuilder.create_host_details_by_click_cell(
                                       actual_value, element_id + "_1", is_equal),
                                   HTMLBuilder.create_cell(property_remarks)]

        return cells_elements_list

    def is_system_value_collect_succeeded(self, is_equal, system_value):
        if system_value == "failed to collect data (details in the .json file)":
            return False
        return is_equal

    def get_header_rows(self):
        raise NotImplementedError

    def convert_range_column(self, column_str):
        if not isinstance(column_str, six.string_types):
            return column_str
        range_list = ValidateBlueprint.get_blueprint_range_from_str(column_str)

        if not range_list:
            return column_str

        if range_list[1] == ValidateBlueprint.UNLIMITED:
            return "Actual value should be >= {}".format(range_list[0])

        return "Actual value should be in range [{} - {}]".format(range_list[0], range_list[1])


class BlueprintHwHtmlPrint(BlueprintHtmlPrint):
    def __init__(self, has_match):
        self._has_match = has_match

    def get_display_properties(self):
        return "display: block"

    def get_header_rows(self):
        if self._has_match:
            return ["Topic", "ID", "Property", "Expected", "Actual", "Remarks"]

        return ["Topic", "ID", "Property", "System Data", "Remarks"]

    @staticmethod
    def get_id():
        return "Hardware info"

    def get_cell_properties(self):
        if self._has_match:
            return {}

        return {"style": "display: none"}

    @classmethod
    def get_class(cls):
        return "info_validate_is_hw_blueprint"


class BlueprintFwHtmlPrint(BlueprintHtmlPrint):
    @staticmethod
    def get_id():
        return "Firmware and Software info"

    @classmethod
    def get_class(cls):
        return "info_validate_is_fw_blueprint"

    def get_header_rows(self):
        return ["Topic", "Property", "System Data"]

    def get_id_rows(self, _, id_data, title, topic, topic_remarks):
        self.print_table = True
        res = []
        properties_names = list(id_data.keys())

        for property_index, property_name in enumerate(properties_names):
            merge_len = len(properties_names)
            cells_elements_list = self.get_blueprint_table_line_cells(None, None, merge_len,
                                                                      property_index, property_name, id_data,
                                                                      topic,
                                                                      "{}_{}".format(
                                                                          title, BlueprintHtmlPrint.table_id_counter),
                                                                      None)
            BlueprintHtmlPrint.table_id_counter += 1
            res.append(HTMLBuilder.create_element('tr', cells_elements_list))

        return res

    def get_pairs(self, topic_data):
        return topic_data

    def get_blueprint_table_line_cells(self, blueprint_properties, id_, merge_len, property_index, property_name,
                                       system_properties, topic, element_id, property_remarks):
        element_id = "b_id_{}".format(element_id)
        is_equal = self.is_system_value_collect_succeeded(is_equal=True,
                                                          system_value=system_properties.get(property_name, ""))

        if property_index == 0:
            cells_elements_list = [HTMLBuilder.create_element('td', [topic], {"rowspan": str(merge_len)}),
                                   HTMLBuilder.create_cell(property_name),
                                   HTMLBuilder.create_host_details_by_click_cell(
                                       system_properties.get(property_name, ""), element_id + "_1", is_equal)]
        else:
            cells_elements_list = [HTMLBuilder.create_cell(property_name),
                                   HTMLBuilder.create_host_details_by_click_cell(
                                       system_properties.get(property_name, ""), element_id + "_1", is_equal)]

        return cells_elements_list


class BlueprintNameHtmlPrint:
    @staticmethod
    def create_table(roles_json):
        cells_header = [HTMLBuilder.create_cell("Blueprint Name", is_title=True),
                        HTMLBuilder.create_cell("Is In ICE Database ", is_title=True)]

        header_row_element = HTMLBuilder.create_element('tr', cells_header)

        header_element = HTMLBuilder.create_element('thead', [header_row_element])

        cells_elements_list = [HTMLBuilder.create_element('td', [roles_json["blueprint_name"]]),
                               HTMLBuilder.create_element('td', [roles_json["has_match"]])]

        row = [HTMLBuilder.create_element('tr', cells_elements_list)]

        body_element = HTMLBuilder.create_element('tbody', row)
        table_element = HTMLBuilder.create_element('table', [header_element, body_element],
                                                   {"class": "width_90 center", "border": "1", "style": "font-size:80%"}
                                                   )

        return [table_element]
