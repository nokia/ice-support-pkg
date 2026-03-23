import GlobalParameters
from DeploymentType import DeploymentType

class Action:
    INSTALLATION = 'INSTALLATION'
    INSTALLATION_FILE_TRACKER = 'INSTALLATION FILE TRACKER'
    UNINSTALLATION = 'UN-INSTALLATION'
    KEY_RECREATION = 'KEY-RECREATION'
    LOAD_DOCKER = 'LOAD_DOCKER'
    UNLOAD_DOCKER = 'UNLOAD_DOCKER'
    LOAD_ICE_PYTHON_CONTAINER = 'LOAD-ICE-PYTHON-CONTAINER'
    UNLOAD_ICE_PYTHON_CONTAINER = 'UNLOAD-ICE-PYTHON-CONTAINER'
    REMOVE_OLD_ICE_KEY = 'REMOVE_OLD_ICE_KEY'
    ROLLBACK = 'ROLLBACK'
    GENERATE_LOG_SCENARIOS_FILES = 'GENERATE-LOG-SCENARIOS-FILES'

    @staticmethod
    def is_supported(action):
        if action not in [Action.INSTALLATION, Action.UNINSTALLATION, Action.KEY_RECREATION, Action.LOAD_DOCKER,
                          Action.UNLOAD_DOCKER, Action.LOAD_ICE_PYTHON_CONTAINER,
                          Action.UNLOAD_ICE_PYTHON_CONTAINER, Action.GENERATE_LOG_SCENARIOS_FILES,
                          Action.REMOVE_OLD_ICE_KEY]:
            return False
        return True

    @staticmethod
    def get_actions_list_from_args(uninstallation, key_recreation, no_file_tracker, rollback):
        if rollback:
            return [
                Action.ROLLBACK,
                Action.REMOVE_OLD_ICE_KEY
            ]

        if uninstallation:
            return [
                Action.UNINSTALLATION,
                Action.LOAD_DOCKER,
                Action.UNLOAD_ICE_PYTHON_CONTAINER,
                Action.REMOVE_OLD_ICE_KEY
            ]

        if key_recreation:
            return [
                Action.KEY_RECREATION
            ]

        if not no_file_tracker:
            return [
                Action.INSTALLATION,
                Action.KEY_RECREATION,
                Action.LOAD_DOCKER,
                Action.LOAD_ICE_PYTHON_CONTAINER,
                Action.REMOVE_OLD_ICE_KEY,
                Action.INSTALLATION_FILE_TRACKER,
                Action.GENERATE_LOG_SCENARIOS_FILES
            ]

        return [
            Action.INSTALLATION,
            Action.KEY_RECREATION,
            Action.LOAD_DOCKER,
            Action.LOAD_ICE_PYTHON_CONTAINER,
            Action.REMOVE_OLD_ICE_KEY,
            Action.GENERATE_LOG_SCENARIOS_FILES
        ]


    @staticmethod
    def is_action_essential(action):
        if action in [
            Action.INSTALLATION,
            Action.UNINSTALLATION,
            Action.KEY_RECREATION
        ]:
            return True
        return False
