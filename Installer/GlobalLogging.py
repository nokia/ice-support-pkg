import getpass
import logging
import os
import subprocess

import Paths
from Action import Action

info_logger = None
debug_logger = None


def create_logger(logger_path, logger_name, debug=False, is_printable=False):
    if os.path.exists(logger_path):
        current_user = getpass.getuser()
        subprocess.call(['sudo', 'chown', '{}:{}'.format(current_user, current_user), logger_path])

    log = logging.getLogger(logger_name)
    formatter = logging.Formatter('%(levelname)s:%(asctime)s\t%(message)s')
    file_handler = logging.FileHandler(logger_path, mode='a')
    file_handler.setFormatter(formatter)
    if debug:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)
    log.addHandler(file_handler)
    if is_printable:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        log.addHandler(stream_handler)
    return log


def init_loggers():
    global info_logger
    global debug_logger
    info_logger = create_logger(Paths.INFO_LOG_FILE, 'ice_installation')
    debug_logger = create_logger(Paths.DEBUG_LOG_FILE, 'ice_installation_debug', debug=True)


def log_and_print(text, include_debug=True, is_error=False):
    print(text)
    if is_error:
        info_logger.error(text)
    else:
        info_logger.info(text)
    if include_debug:
        log_debug(text)


def log_debug(text):
    debug_logger.debug(text)


def print_results(dict_installation_result):
    message = """
        ========================================
                installation results:
        
        ========================================
        """
    log_and_print(message)
    for key, value in dict_installation_result.items():
        log_and_print("ICE {}:{}".format(key, "SUCCESS" if value else "FAILED"))


def print_header(action):
    message = """
        ========================================
                ICE {action}
        
        ========================================
        """.format(action=action)
    log_and_print(message)


def print_plugin_header(action, plugin_name):
    action = "INSTALLING" if action == Action.INSTALLATION else "UNINSTALLING"
    message = """
    #########################################
    {action} PLUGIN {plugin_name}
    #########################################
    """.format(action=action, plugin_name=plugin_name.upper())
    log_and_print(message)


def log_plugin_results(action, plugin_name, results):
    header = '\n{}\nPLUGIN {} {} RESULTS:\n{}\n'.format("#" * 100, plugin_name.upper(), action, "_" * 100)
    body = ""
    debug_text = ''
    for res in results:
        line = "\n{}:\t{}\n".format(res, results[res])
        if res == 'trace':
            debug_text = line
        else:
            body += line
    bottom_border = "_" * 100 + "\n" + "#" * 100
    text = header + body + bottom_border
    debug_log = header + body + debug_text + bottom_border
    log_debug(debug_log)
    log_and_print(text, include_debug=False)
