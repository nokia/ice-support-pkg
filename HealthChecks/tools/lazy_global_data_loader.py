from __future__ import absolute_import
# use for one time loading any reused & shard data amonge diffrent therds
import inspect
import sys

from tools.python_utils import PythonUtils
from tools.python_versioning_alignment import get_full_trace
import threading
import tools.global_logging as log
from tools.Exceptions import *
import traceback

TAG_FOR_PREVIOUS_FAILER = "TAG_FOR_PREVIOUS_LAZY_DATA_LOADER_FAILER"


def check_function_params(func):
    if sys.version_info[0] < 3:
        argspec = inspect.getargspec(func)
        parameters = argspec.args
    else:
        signature = inspect.signature(func)
        parameters = list(signature.parameters)

    assert_message = "lazy_global_data_loader Assert: "
    if 'self' in parameters or 'cls' in parameters:
        assert len(parameters) == 1, "{}Instance or class method should have one parameter: 'self' or 'cls'".format(
            assert_message)
    else:
        assert len(parameters) == 0, "{}Static method or unbound function should not have parameters".format(
            assert_message)


def lazy_global_data_loader(func):
    def inner(*args):
        check_function_params(func)
        lazy_fun = LazyDataLoader.get_common_data(func, *args)
        return lazy_fun

    return inner


def clean_lazy_global_data_loader():
    LazyDataLoader.clean_lazy()


class LazyDataLoader:
    threadLock = threading.RLock()
    my_data_db = {}

    @classmethod
    def _load_data(cls, data_class, data_name, data_loader, *args):

        try:
            my_data = data_loader(*args)
            cls.my_data_db.setdefault(data_class, {})[data_name] = my_data


        except UnExpectedSystemOutput as e:
            full_trace = get_full_trace()
            e.full_trace = full_trace
            cls.my_data_db.setdefault(data_class, {})[data_name] = e
            log.log_and_print("problem with loading {}".format(data_name))
            log.log(str(e))
            log.log(full_trace)

            raise

        except Exception as e:
            full_trace = get_full_trace()
            cls.my_data_db.setdefault(data_class, {})[data_name] = LazyDataLoaderPreviousLoadProblem(
                previous_exception=e, previous_trace=full_trace)
            log.log_and_print("problem with loading {}".format(data_name))
            log.log(str(e))
            log.log(full_trace)
            raise

    @classmethod
    def get_common_data(cls, data_loader, *args):

        data_name = data_loader.__name__

        data_class = str(PythonUtils.get_class_name(data_loader, *args))
        if data_class not in cls.my_data_db or data_name not in cls.my_data_db[data_class]:
            cls.threadLock.acquire()
            try:
                if data_name not in cls.my_data_db:
                    cls._load_data(data_class, data_name, data_loader, *args)
            finally:
                cls.threadLock.release()
        my_data = cls.my_data_db[data_class][data_name]
        if isinstance(my_data, Exception):
            raise my_data

        # if my_data == TAG_FOR_PREVIOUS_FAILER:
        #    raise LazyDataLoaderPreviousLoadProblem

        return my_data

    @classmethod
    def clean_lazy(cls):
        cls.my_data_db = {}
