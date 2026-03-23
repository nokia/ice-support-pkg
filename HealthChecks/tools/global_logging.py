from __future__ import absolute_import
from __future__ import print_function
# *******************************************************************************
# log
# *******************************************************************************
import logging
import sys
from six.moves import range

logger = None


def set_base_logger_to_default_setting(name=None):
    #based on ICET-943
    # there are some class that may chang our base logger configuration
    # particularly:
    # from tools.ExecutionModule.HostExecutorsFactory.CbisHostExecutorFactory import CbisHostExecutorFactory
    # from ansible.parsing.dataloader import DataLoader
    # from ansible.inventory.manager import InventoryManager
    # uses
    # /usr/lib/python2.7/site-packages/ansible/utils/display.py
    # which change the base logger configuration in the global scope:
    # logging.basicConfig(filename=path, level=logging.DEBUG, format='%(asctime)s %(name)s %(message)s')
    # there for - we delete any unnecessary handler that may be added
    # and set the default base logger the default : WARNING

    base_logger = logging.getLogger(name)
    while len(base_logger.handlers) > 0:
        base_logger.removeHandler(base_logger.handlers[0])

    base_logger.setLevel(logging.WARNING)

def init(logger_path="", debug=False, quiet=False):
    global logger
    set_base_logger_to_default_setting()
    logger = set_log(logger_path, "health_checker", debug=debug, quiet=quiet)

# -------------------------------------------------------------------------
def set_log(log_file_name, logger_name, debug=False, quiet=False):

    logger_obj = logging.getLogger(logger_name)
    logger_obj.propagate = False

    if quiet or not log_file_name :  # if we do not want out files and min out pot
        hdlr = logging.StreamHandler(sys.stderr)
    else:
        hdlr = logging.FileHandler(log_file_name)

    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger_obj.addHandler(hdlr)

    if debug:
        logger_obj.setLevel(logging.DEBUG)
    elif quiet:
        logger_obj.setLevel(logging.ERROR)
    else:
        logger_obj.setLevel(logging.INFO)
    return logger_obj


# -------------------------------------------------------------------------
def print_file_to_log(file):
    with open(file) as f:
        lines = f.readlines()
        logger.info("----------------------------------------")
        logger.info("print the file: " + file + " : ")
        for line in lines:
            logger.info(line)
        logger.info("----------------------------------------")

# -------------------------------------------------------------------------
def log_and_print(text, level='info'):
    assert level in ['info', 'error'], 'log level should be info / error'
    print(text)
    if level == 'info':
        logger.info(text)
    elif level == 'error':
        logger.error(text)

def log_and_print_with_frame(text_msg):
    text_msg = '===========  {}  ==========='.format(text_msg)
    frame_line = ''
    for charcter in range(len(text_msg)):
        frame_line += '='
    log_and_print('\n' + frame_line)
    log_and_print(text_msg)
    log_and_print(frame_line + '\n')

# ----------------------------------------------------------------
def log(text):
    logger.info(text)

def log_error(text):
    logger.error(text)
# ----------------------------------------------------------------
def set_level_to_error():
    logger.setLevel(logging.ERROR)
# ----------------------------------------------------------------

