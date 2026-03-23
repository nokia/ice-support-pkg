from __future__ import absolute_import
# hold the path of configuration files or other files in this project
import os.path

#Healthcheck configuration files
EXPECTED_DEAMONSET_FILE = './flows/K8s/k8s_components/expected_daemod_set.json'
ERROR_IN_LOG_CONFIG_FILE = "flows/Cbis/scale_in_out_log_errors/scale_error.json"
SYS_ERROR_CONF_FILE = "flows/Cbis/system_log_checkes/system_error.json"
NAME_TO_URL_FILE = './tools/name_to_url.json'
ABOUT_FILE = './about.txt'
INFRA_JSON_PATH = "flows/Cbis/cbis_system_checks/Files/Infra.json"
SYSTEM_OPERATION_JSON = 'flows/Chain_of_events/files/{}_operations_info.json'
NCD_CONFIG_FILE = 'flows/Applications/NCD/ncd_config.json'
ICE_LOGS_DIR = '/usr/share/ice/logs'

#Healthcheck configuration files & system
ENCRYPTION_KEY = "/usr/share/ice/ice-secret.key"

ENCRYPTION_OUT_FILES_KEYS_FOLDER = "/usr/share/ice/"
ENCRYPTION_OUT_FILES_KEYS_FILE = "keys.txt"
PUBLIC_KEY_PATH = "public_key/public_key.pem"

LOG_SCENARIOS_DIR_PATH = os.path.join(os.getcwd(), "..", "..", "log_scenarios")
LOG_COLLECTOR_CONF_FILES_DIR = "flows_of_sys_operations/sys_data_collector/log_collector/configurations/"
CBIS_LOG_OF_INTEREST = "cbis_log_of_interest.yaml"
NCS_LOG_OF_INTEREST = "ncs_log_of_interest.yaml"

# container
PRIVATE_KEY_FROM_CONTAINER_TO_HOST = "ice_container_key"  # name of private key, located under the user .ssh folder
MOUNTED_CA_CERT_PATH_IN_CONTAINER = "/etc/ssl/certs/ca-bundle.crt"

#CBIS:
CBIS_HOTFIX_FILE = "/var/lib/cbis/inventory"
CBIS_USER_CONFIG = '/home/stack/user_config.yaml'
CBIS_HOSTS_FILE = '/etc/ansible/hosts'
CBIS_VERSION_FILE = "/usr/share/cbis/cbis-version"

#NCA BM:
NCS_BM_POST_CONFIG = 'postconfig-inv.json'
NCS_BM_VERSION_FILE = '/opt/nokia/images/bcmt_images/BCMT_VARS.yml'
NCS_BM_CLUSTER_DATA_DIR = '/opt/install/data/cbis-clusters'

#NCS CNA:
DEFAULT_NCS_CLCM_USER_INPUT = '/opt/clcm/user_input.yml'

#NCS CNA & BM
DEFAULT_BCMT_CONF_FILE = '/opt/bcmt/bcmt_config.json'
