from __future__ import absolute_import
from tools.lazy_global_data_loader import *
import datetime
import json
import re
from dateutil import tz
from dateutil.parser import parse as original_parse

class DateAndTimeUtils:
    DATE_AND_TIME_WITH_TIMEZONE = 'tools/date_and_time_with_timezone.json'
    @staticmethod
    def convert_str_list_to_datetime(str_date_list, date_format):
        datetime_list = []
        for date in str_date_list:
            try:
                if '%Z' in date_format:
                    date_and_time_with_offset = DateAndTimeUtils._get_date_and_time_with_offset_by_timezone(date)
                    date_format = DateAndTimeUtils._remove_directive_from_date_format(date_format, '%Z')
                    datetime_object = DateAndTimeUtils._get_datetime_object_by_date_and_time_with_offset(
                        date_and_time_with_offset, date_format)
                elif '%z' in date_format:
                    datetime_object = DateAndTimeUtils._get_datetime_object_by_date_and_time_with_offset(date,
                                                                                                        date_format)
                else:
                    datetime_object = datetime.datetime.strptime(date, date_format)
            except AttributeError:
                e_type, e_value, e_traceback = sys.exc_info()
                ex = ''.join(traceback.format_exception(e_type, e_value, e_traceback))
                raise InvalidDatetimeFormat(date, date_format, ex)
            if datetime_object is not None:
                datetime_list.append(datetime_object)
        return datetime_list

    @staticmethod
    def _get_datetime_object_by_date_and_time_with_offset(date_and_time_with_offset, date_format):
        #TODO: relevant for python 2.7 as it doesn't support '%z' option in date_format
        # On Python3 we'll simply use: datetime.datetime.strptime(date_and_time_with_offset, date_format), while date_format will include '%z'
        assert not '%Z' in date_format, "'%Z' shouldn't be an option on date_format"
        date_format = DateAndTimeUtils._remove_directive_from_date_format(date_format, '%z')
        utc_offset = re.search(r'[+-]\d{4}', date_and_time_with_offset).group(0)
        date_and_time_only = date_and_time_with_offset[:-5].strip()
        datetime_object = datetime.datetime.strptime(date_and_time_only, date_format)
        datetime_object += datetime.timedelta(hours=int(utc_offset[1:3]), minutes=int(utc_offset[3:]))
        return datetime_object

    @staticmethod
    def _get_date_and_time_with_offset_by_timezone(date_and_time_with_timezone):
        with open(DateAndTimeUtils.DATE_AND_TIME_WITH_TIMEZONE) as json_file:
            all_timezones_offset_and_name = json.load(json_file)
        timezone = date_and_time_with_timezone.split(' ')[-1]
        timezone_info = all_timezones_offset_and_name.get(timezone)
        assert timezone_info, "Failed to find timezone '{}' at {}".format(timezone, DateAndTimeUtils.DATE_AND_TIME_WITH_TIMEZONE)
        offset = timezone_info['offset']
        date_and_time = ' '.join(date_and_time_with_timezone.split(' ')[:-1])
        date_and_time_with_offset = '{} {}'.format(date_and_time, offset)
        return date_and_time_with_offset

    @staticmethod
    def _remove_directive_from_date_format(date_format, directive):
        date_format_list = date_format.split(directive)
        return ' '.join(date_format_list).strip()

    @staticmethod
    def get_datetime_object_by_date_and_time_str(date_and_time_str, date_format):
        return datetime.datetime.strptime(date_and_time_str, date_format)

with open(DateAndTimeUtils.DATE_AND_TIME_WITH_TIMEZONE) as f:
    tz_json = json.load(f)

def parse_offset(offset_str):
    sign = 1 if offset_str[0] == '+' else -1
    hours = int(offset_str[1:3])
    minutes = int(offset_str[3:])
    return tz.tzoffset(None, sign * (hours * 3600 + minutes * 60))

tzinfos = {k: parse_offset(v["offset"]) for k, v in tz_json.items()}

def parse(dt_str, **kwargs):
    if "tzinfos" not in kwargs:
        kwargs["tzinfos"] = tzinfos
    return original_parse(dt_str, **kwargs)
