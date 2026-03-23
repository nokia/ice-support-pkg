from __future__ import absolute_import
import re

from tools.global_enums import States
from six.moves import range


class ExpectedStateValues(object):
    def __init__(self, valid_value=None, invalid_value=None, unknown_value=None):
        assert valid_value or invalid_value or unknown_value, "one of valid_values, invalid_values, unknown_value should be initalize"
        self.valid_values = valid_value
        self.invalid_values = invalid_value
        self.unknown_value = unknown_value

    def get_cell_state(self, cell_value):
        if self.valid_values and self.is_value_matched(self.valid_values, cell_value):
            return States.VALID
        if self.invalid_values and self.is_value_matched(self.invalid_values, cell_value):
            return States.INVALID
        if self.unknown_value and self.is_value_matched(self.unknown_value, cell_value):
            return States.UNKNOWN
        return States.INFO

    def is_value_matched(self, values_list, cell_value):
        return any(re.match(value, cell_value) for value in values_list)


class TableSystemInfo(object):
    def __init__(self, table=None, headers=None, remarks="", print_host_as_title=True):
        self.table = table if table else []
        self.headers = headers if headers else []
        self.remarks = remarks
        self.print_host_as_title = print_host_as_title
        self._expected_values_by_column = {}

    def to_dict(self):
        return {
            "table": self.get_table_with_states(),
            "headers": self.headers,
            "remarks": self.remarks,
            "print_host_as_title": self.print_host_as_title
        }

    def set_expected_column_values(self, column_header=None, column_index=None, valid_value=None, invalid_value=None,
                                   unknown_value=None):
        if column_header:
            assert column_header in self.headers, "Column header '{}' not found in available headers: {}".format(
                column_header, self.headers)
            column_index = self.headers.index(column_header)
        else:
            assert column_index, "Either column_header or column_index must be set."
        assert not self._expected_values_by_column.get(column_index), \
            "Expected values for column {} are already defined.".format(column_index)
        self._expected_values_by_column[column_index] = ExpectedStateValues(valid_value, invalid_value, unknown_value)

    def assert_table_system_info(self):
        if self.table:
            headers_table_system_info = self.headers
            if self.table is not None and len(self.table):
                if len(headers_table_system_info):
                    assert (len(self.table[0]) == len(headers_table_system_info)), \
                        "Inconsistency between the number of columns of table_system_info.headers and " \
                        "table_system_info.table"
                assert (max(len(x) for x in self.table) == min(
                    len(x) for x in self.table)), \
                    "Not all rows of table_system_info.table have the same number of columns"
            if self._expected_values_by_column:
                assert type(self._expected_values_by_column) is dict, \
                    "Expected '_expected_values_by_column' to be of type 'dict'"
                for key, value in list(self._expected_values_by_column.items()):
                    assert isinstance(value, ExpectedStateValues), \
                        "Expected each item in '_expected_values_by_column' to be an instance of 'ExpectedStateValues'"

    def get_table_with_states(self):
        table_with_states = []
        if self.table is None:
            return table_with_states
        for row in self.table:
            row_with_states = []
            for column_index in range(len(row)):
                state = States.INFO
                if column_index in list(self._expected_values_by_column.keys()):
                    state = self._expected_values_by_column[column_index].get_cell_state(row[column_index])
                row_with_states.append({row[column_index]: state})
            table_with_states.append(row_with_states)
        return table_with_states
