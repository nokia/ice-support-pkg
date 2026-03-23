from __future__ import absolute_import
import sys

try:
    from unittest.mock import Mock, patch, MagicMock  # Python 3.3 and later
except ImportError:
    from mock.mock import Mock, patch, MagicMock  # Python 2 and older versions of Python 3

try:
    from contextlib import nested  # Python 2
except ImportError:
    from contextlib import ExitStack, contextmanager

    @contextmanager
    def nested(*contexts):
        """
        Reimplementation of nested in python 3.
        """
        with ExitStack() as stack:
            for ctx in contexts:
                stack.enter_context(ctx)
            yield contexts


def is_python_2():
    out = sys.version_info
    if out.major == 2:
        return True
    return False


def decode_res(res, get_not_ascii):
    if is_python_2():
        if get_not_ascii:
            out = str(res.out).decode('ascii', 'replace')
            err = str(res.err).decode('ascii', 'replace')
        else:
            out = str(res.out).decode('ascii', 'ignore')
            err = str(res.err).decode('ascii', 'ignore')
    else:
        err = res.err
        out = res.out

    return out, err
