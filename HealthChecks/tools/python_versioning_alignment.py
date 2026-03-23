from __future__ import absolute_import
import base64
import sys
import time
import traceback

import configparser
import six
from six.moves import input

try:
    from StringIO import StringIO  # for Python 2
except ImportError:
    from io import StringIO  # for Python 3

try:
    from six.moves.builtins import enumerate  # for Python 2
except ImportError:
    from builtins import enumerate  # for Python 3

try:
    import six.moves.configparser as ConfigParser
except ImportError:
    import configparser as ConfigParser

try:
    # Python 3.3+
    from collections.abc import Hashable
except ImportError:
    # Python 2.7 and earlier versions of Python 3
    from collections import Hashable


def is_python_2():
    out = sys.version_info
    if out.major == 2:
        return True
    return False


def is_python_3():
    out = sys.version_info
    if out.major == 3:
        return True
    return False


def to_unicode(input, encoding=None):
    if isinstance(input, six.binary_type):
        encoding = encoding if encoding else "utf-8"
        return input.decode(encoding)
    if is_python_2():
        if encoding:
            to_return = six.text_type(input, encoding=encoding)
        else:
            to_return = six.text_type(input)
    else:
        to_return = str(input)
    return to_return


def get_unicode_type():
    if is_python_2():
        return six.text_type
    else:
        return str


def get_user_input(line_to_print):
    return input(line_to_print)


def get_full_trace():
    if is_python_2():
        return traceback.format_exc(sys.exc_info())
    else:
        return traceback.format_exc()


def get_default_timer():
    if is_python_2():
        return time.clock()
    return time.perf_counter()


def decode_base_64(encoded_str):
    if is_python_2():
        return encoded_str.decode('base64')
    return base64.b64decode(encoded_str).decode('utf-8')


def read_config(s):
    buf = StringIO('\n'.join([line.lstrip() for line in s.splitlines()]))
    if is_python_3():
        config = configparser.RawConfigParser(interpolation=None, strict=False)
    else:
        config = ConfigParser.ConfigParser()
    # Use read_file for Python 3 and readfp for Python 2
    if is_python_2():
        config.readfp(buf)
    else:
        config.read_file(buf)

    return config


def read_file(file_path):
    if is_python_2():
        # Python 2: Use default open without specifying encoding
        with open(file_path, 'r') as f:
            return f.read()
    else:
        # Python 3: Specify encoding to handle non-ASCII characters
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()


def get_zipper(iterable1, iterable2):
    if is_python_2():
        return map(None, iterable1, iterable2)
    else:
        from itertools import zip_longest
        return zip_longest(iterable1, iterable2)