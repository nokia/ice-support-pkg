from IceInstaller import get_arguments, local_installer
import GlobalLogging
import CommonOperations
import GlobalParameters

arguments = get_arguments()
configuration = CommonOperations.get_env_configuration()
GlobalParameters.init_env_configuration(configuration)
deployment_type = CommonOperations.detect_deployment_type(configuration)
GlobalParameters.init_deployment_type(deployment_type)
GlobalLogging.init_loggers()
local_installer(arguments)
