from __future__ import absolute_import
# from tools.base_linux_utils import *
from tools.ExecutionModule.HostExecutorsFactory.CbisHostExecutorFactory import CbisHostExecutorFactory \
    as HealthCheckCbisHostExecutorFactory
from tools.ExecutionModule.HostExecutorsFactory.NcsBareMetalHostExecutorFactory import NcsBareMetalHostExecutorFactory \
    as HealthCheckNcsBareMetalHostExecutorFactory
import tools.UI.HTMLPrint as HTMLPrint

# hold reference to all the tools in those project that need a system to run on
# for example : running command over linux
# this class gives another layer of abstraction that is very useful for testing this tool with out a system
# using system mmimk

# all 'external' tools must be referenced from here
# base_linux_utils = BaseLinuxUtils
CbisHostExecutorFactory = HealthCheckCbisHostExecutorFactory
NcsBareMetalHostExecutorFactory = HealthCheckNcsBareMetalHostExecutorFactory
HtmlPrint = HTMLPrint
