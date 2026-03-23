from __future__ import absolute_import
import re


class DiffParser(object):

    def parse_output(self, diff_output):
        new_diff_output = ""
        diff_output = diff_output.replace("\n<", "\nOld Line:")
        diff_output = diff_output.replace("\n>", "\nNew Line:")
        diff_output_split_arr = diff_output.split('\n')
        for item in diff_output_split_arr:
            if len(item) > 0 and item[0].isdigit() and re.search('[acd]', item):  # For example item "13c13"
                new_line = self._parse_line_code_in_output(item)
                new_diff_output += new_line + '\n'
            else:
                new_diff_output += item + '\n'
        return new_diff_output

    def _parse_line_code_in_output(self, line_code):
        line_code_arr = re.split('[acd]', line_code)
        num_before_char = line_code_arr[0]
        num_after_char = line_code_arr[1]
        new_line_in_diff_output = ""
        if 'c' in line_code:
            if ',' in num_after_char:
                num_after_char = num_after_char.replace(",", "-")
                new_line_in_diff_output = "\nLines {} were changed:".format(num_after_char)
            else:
                new_line_in_diff_output = "\nLine {} was changed:".format(num_after_char)
        if 'd' in line_code:
            if ',' in num_before_char:
                num_before_char = num_before_char.replace(",", "-")
                new_line_in_diff_output = "\nLines {} were deleted:".format(num_before_char)
            else:
                new_line_in_diff_output = "\nLine {} was deleted:".format(num_before_char)
        if 'a' in line_code:
            if ',' in num_after_char:
                num_after_char = num_after_char.replace(",", "-")
                new_line_in_diff_output = "\nLines {} were added:".format(num_after_char)
            else:
                new_line_in_diff_output = "\nLine {} was added:".format(num_after_char)
        return new_line_in_diff_output
