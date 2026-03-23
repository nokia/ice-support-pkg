from __future__ import absolute_import
import json
import os
import tools.sys_parameters as gs
import tools.user_params
from tools.global_enums import Deployment_type
from tools.lazy_global_data_loader import *


class FileTrackerPaths(object):
    BASE_PATH_ON_HOST = ""
    MAIN_FILE_TRACKER_DIR_PATH = ""
    FILE_TRACKER_DIR_PATH_ON_HOST = ""
    SNAPSHOTS_DIRECTORY = ""
    DYNAMIC_SNAPSHOTS_DIRECTORY = ""
    FOLDERS_SNAPSHOTS_DIRECTORY = ""
    COMMANDS_SNAPSHOTS_DIRECTORY = ""
    DIFFERENCES_SUMMARY_FILE = ""
    FILE_TRACKER_LOG_PATH = ""
    VERSION_DETAILS = ""
    FILE_TRACKER_LOCKER = ""
    CONF_FILES_JSON = ""
    TRACKED_FOLDERS_JSON = ""
    TRACKED_COMMANDS_JSON = ""
    CONF_FILES_PER_DEPLOYMENT = None
    DYNAMIC_RESOURCES_JSON = ""
    CURRENT_ICE_VERSION_FILE = ""
    LAST_ICE_VERSION_PATH = ""
    TMP_YAML_DIR = ""
    TMP_CMD_OUT_DIR = ""
    DYNAMIC_RESOURCES_PER_DEPLOYMENT = ""
    DISK_SPACE_THRESHOLD = None  # In Kilobytes

    FILE_TRACKER_CONFIGURATIONS = "flows_of_sys_operations/FileTracker/Files/file_tracker_configurations.json"

    def __init__(self):
        self.config_dict = None
        self.file_tracker_parent_dir = os.path.dirname(os.path.abspath(__file__))
        self._load_files()

    @lazy_global_data_loader
    def _load_files(self):
        if tools.user_params.config_json_path:
            config_json_path = tools.user_params.config_json_path
        else:
            config_json_path = FileTrackerPaths.FILE_TRACKER_CONFIGURATIONS
        with open(config_json_path) as json_file:
            config_dict = json.load(json_file)

        self.init_config_dict(config_dict)
        self.set_config_values()

    def init_config_dict(self, config_dict):
        self.config_dict = config_dict["shared"]

    def set_config_values(self):
        FileTrackerPaths.BASE_PATH_ON_HOST = self.config_dict['BASE_PATH_ON_HOST']
        FileTrackerPaths.MAIN_FILE_TRACKER_DIR_PATH = os.path.join(self.config_dict['MAIN_ICE_BASE_PATH'],
                                                                   self.config_dict['FILE_TRACKER_DIRECTORY'])
        FileTrackerPaths.FILE_TRACKER_DIR_PATH_ON_HOST = "{}{}".format(FileTrackerPaths.BASE_PATH_ON_HOST,
                                                                       self.config_dict['FILE_TRACKER_DIRECTORY'])
        FileTrackerPaths.SNAPSHOTS_DIRECTORY = "{}{}".format(FileTrackerPaths.FILE_TRACKER_DIR_PATH_ON_HOST,
                                                             self.config_dict['SNAPSHOTS_DIRECTORY'])
        FileTrackerPaths.FOLDERS_SNAPSHOTS_DIRECTORY = "{}{}".format(FileTrackerPaths.FILE_TRACKER_DIR_PATH_ON_HOST,
                                                                     self.config_dict['FOLDERS_SNAPSHOTS_DIRECTORY'])
        FileTrackerPaths.COMMANDS_SNAPSHOTS_DIRECTORY = "{}{}".format(FileTrackerPaths.FILE_TRACKER_DIR_PATH_ON_HOST,
                                                                     self.config_dict['COMMANDS_SNAPSHOTS_DIRECTORY'])
        FileTrackerPaths.DYNAMIC_SNAPSHOTS_DIRECTORY = "{}{}".format(FileTrackerPaths.MAIN_FILE_TRACKER_DIR_PATH,
                                                                     self.config_dict['DYNAMIC_SNAPSHOTS_DIRECTORY'])
        FileTrackerPaths.DIFFERENCES_SUMMARY_FILE = os.path.join(FileTrackerPaths.MAIN_FILE_TRACKER_DIR_PATH,
                                                                 self.config_dict['DIFFERENCES_SUMMARY_FILE'])
        FileTrackerPaths.FILE_TRACKER_LOG_PATH = os.path.join(FileTrackerPaths.MAIN_FILE_TRACKER_DIR_PATH,
                                                              self.config_dict['FILE_TRACKER_LOG_NAME'])
        FileTrackerPaths.VERSION_DETAILS = os.path.join(FileTrackerPaths.MAIN_FILE_TRACKER_DIR_PATH,
                                                        self.config_dict['VERSION_DETAILS'])
        FileTrackerPaths.FILE_TRACKER_LOCKER = os.path.join(FileTrackerPaths.MAIN_FILE_TRACKER_DIR_PATH,
                                                            self.config_dict['FILE_TRACKER_LOCKER'])
        FileTrackerPaths.CURRENT_ICE_VERSION_FILE = os.path.join(self.file_tracker_parent_dir,
                                                                 self.config_dict['CURRENT_ICE_VERSION_FILE'])
        FileTrackerPaths.LAST_ICE_VERSION_PATH = self.config_dict['LAST_ICE_VERSION_PATH']
        FileTrackerPaths.TMP_YAML_DIR = "{}{}".format(FileTrackerPaths.FILE_TRACKER_DIR_PATH_ON_HOST,
                                                      self.config_dict['TMP_YAML_DIR'])
        FileTrackerPaths.TMP_CMD_OUT_DIR = "{}{}".format(FileTrackerPaths.FILE_TRACKER_DIR_PATH_ON_HOST,
                                                      self.config_dict['TMP_CMD_OUT_DIR'])
        FileTrackerPaths.DISK_SPACE_THRESHOLD = self.config_dict['DISK_SPACE_THRESHOLD']
        FileTrackerPaths.TRACKED_FOLDERS_JSON = os.path.join(self.file_tracker_parent_dir,
                                                             self.config_dict["TRACKED_FOLDERS_JSON"])
        FileTrackerPaths.TRACKED_COMMANDS_JSON = os.path.join(self.file_tracker_parent_dir,
                                                             self.config_dict["TRACKED_COMMANDS_JSON"])


class FileTrackerPathsCBIS(FileTrackerPaths):
    def init_config_dict(self, config_dict):
        super(FileTrackerPathsCBIS, self).init_config_dict(config_dict)
        self.config_dict.update(config_dict["cbis"])

    def set_config_values(self):
        super(FileTrackerPathsCBIS, self).set_config_values()
        FileTrackerPaths.CONF_FILES_JSON = os.path.join(self.file_tracker_parent_dir,
                                                        self.config_dict['CONF_FILES_JSON'])


class FileTrackerPathsSharedNCS(FileTrackerPaths):
    def init_config_dict(self, config_dict):
        super(FileTrackerPathsSharedNCS, self).init_config_dict(config_dict)
        self.config_dict.update(config_dict["shared_ncs"])

    def set_config_values(self):
        super(FileTrackerPathsSharedNCS, self).set_config_values()
        FileTrackerPaths.DYNAMIC_RESOURCES_JSON = os.path.join(self.file_tracker_parent_dir,
                                                               self.config_dict['NCS_DYNAMIC_RESOURCES_JSON'])
        FileTrackerPaths.CONF_FILES_JSON = os.path.join(self.file_tracker_parent_dir,
                                                        self.config_dict['NCS_CONF_FILES_JSON'])
        FileTrackerPaths.CONF_FILES_PER_DEPLOYMENT = os.path.join(self.file_tracker_parent_dir,
                                                                  self.config_dict['CONF_FILES_JSON'])
        FileTrackerPaths.DYNAMIC_RESOURCES_PER_DEPLOYMENT = os.path.join(self.file_tracker_parent_dir,
                                                                         self.config_dict["DYNAMIC_RESOURCES"])


class FileTrackerPathsCNA(FileTrackerPathsSharedNCS):
    def init_config_dict(self, config_dict):
        super(FileTrackerPathsCNA, self).init_config_dict(config_dict)
        self.config_dict.update(config_dict["cna"])


class FileTrackerPathsCNB(FileTrackerPathsSharedNCS):
    def init_config_dict(self, config_dict):
        super(FileTrackerPathsCNB, self).init_config_dict(config_dict)
        self.config_dict.update(config_dict["cnb"])


class FileTrackerPathsInitiator(object):
    def __init__(self):
        deployment_type = gs.get_deployment_type()

        if deployment_type == Deployment_type.CBIS:
            FileTrackerPathsCBIS()
        elif deployment_type == Deployment_type.NCS_OVER_BM:
            FileTrackerPathsCNB()
        elif deployment_type == Deployment_type.NCS_OVER_VSPHERE or \
                deployment_type == Deployment_type.NCS_OVER_OPENSTACK:
            FileTrackerPathsCNA()
        else:
            assert False, "Unknown deployment type: {}".format(deployment_type)
