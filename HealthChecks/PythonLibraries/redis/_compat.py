"""Internal module for Python 2 backwards compatibility."""
from __future__ import absolute_import
import sys
import six
from six import string_types


if sys.version_info[0] < 3:
    from urlparse import urlparse
    from itertools import imap, izip
    from string import letters as ascii_letters
    try:
        from cStringIO import StringIO as BytesIO
    except ImportError:
        from StringIO import StringIO as BytesIO

    iteritems = lambda x: six.iteritems(x)
    dictkeys = lambda x: list(x.keys())
    dictvalues = lambda x: list(x.values())
    nativestr = lambda x: \
        x if isinstance(x, str) else x.encode('utf-8', 'replace')
    u = lambda x: x.decode()
    b = lambda x: x
    next = lambda x: next(x)
    byte_to_chr = lambda x: x
    unichr = unichr
    xrange = xrange
    six.string_types = six.string_types
    six.text_type = six.text_type
    bytes = str
    long = int
else:
    from urllib.parse import urlparse
    from io import BytesIO
    from string import ascii_letters

    iteritems = lambda x: list(x.items())
    dictkeys = lambda x: list(x.keys())
    dictvalues = lambda x: list(x.values())
    byte_to_chr = lambda x: chr(x)
    nativestr = lambda x: \
        x if isinstance(x, str) else x.decode('utf-8', 'replace')
    u = lambda x: x
    b = lambda x: x.encode('iso-8859-1')
    next = next
    unichr = chr
    imap = map
    izip = zip
    xrange = range
    six.string_types = str
    six.text_type = str
    bytes = bytes
    long = int
