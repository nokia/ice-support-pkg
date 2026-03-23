from __future__ import absolute_import
import logging

from PythonLibraries.GZipRotatingFileHandler import GZipRotatingFileHandler
from tools.ExecutionModule.execution_helper import ExecutionHelper
from tools.global_logging import set_base_logger_to_default_setting

logger = None
first_log_handler = None


class CaptureFirstLogDateHandler(logging.Handler):
    def __init__(self, level):
        super(CaptureFirstLogDateHandler, self).__init__(level)
        self.first_log_date = None
        self.first_log_captured = False

    def emit(self, record):
        if not self.first_log_captured:
            split_log_line = self.format(record).split(" ")
            self.first_log_date = split_log_line[0] + " " + split_log_line[1]
            self.first_log_captured = True

    def get_first_log_date(self):
        return self.first_log_date


def init(logger_path):
    global logger
    logger_name = "file_tracker"
    set_base_logger_to_default_setting(logger_name)
    host_operator = ExecutionHelper.get_hosting_operator(False)

    # Change log owner to support old versions that ran from root and logger owner was root
    if host_operator.file_utils.is_file_exist(logger_path):
        host_operator.get_output_from_run_cmd("sudo chown {}:{} {}".format(
            ExecutionHelper.get_local_uid(), ExecutionHelper.get_local_gid(), logger_path))
    logger = set_log(logger_path, logger_name)


def set_log(logger_path, logger_name):
    global first_log_handler
    level = logging.INFO
    logger_obj = logging.getLogger(logger_name)
    logger_obj.propagate = False
    logger_obj.setLevel(level)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

    rotate_handler = GZipRotatingFileHandler(logger_path, maxBytes=1000000, backupCount=10)
    rotate_handler.setLevel(level)
    rotate_handler.setFormatter(formatter)
    logger_obj.addHandler(rotate_handler)

    first_log_handler = CaptureFirstLogDateHandler(level)
    first_log_handler.setFormatter(formatter)
    logger_obj.addHandler(first_log_handler)

    return logger_obj


def get_first_log_time():
    return first_log_handler.get_first_log_date()


def log(self, text, error=False):
    host_name = self.get_host_name()
    if error:
        logger.error("[{}]: {}".format(host_name, text))
    else:
        logger.info("[{}]: {}".format(host_name, text))
