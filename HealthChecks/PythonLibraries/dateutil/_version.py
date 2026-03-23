"""
Contains information about the dateutil version.
"""
from __future__ import absolute_import
from six.moves import map

VERSION_MAJOR = 2
VERSION_MINOR = 6
VERSION_PATCH = 1

VERSION_TUPLE = (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH)
VERSION = '.'.join(map(str, VERSION_TUPLE))
