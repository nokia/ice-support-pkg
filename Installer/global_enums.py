import GlobalParameters


class Objectives():
    # cbis
    UC = "undercloud"
    HYP = "hypervisor"
    ALL_HOSTS = "all-hosts"
    # ALL_HOSTS = { COMPUTES, CONTROLLERS, STORAGE, UC }
    CONTROLLERS = "controllers"
    ONE_CONTROLLER = "one_controller"
    COMPUTES = "computes"
    SRIOV_COMPUTES = "SRIOV_computes"
    OVS_COMPUTES = "OvsCompute"
    DPDK_COMPUTES = "DpdkCompute"
    AVRS_COMPUTES = "AvrsCompute"

    # ncs
    ALL_NODES = "all-k8s-nodes"
    MASTERS = "all_k8s_master"
    ONE_MASTER = "single_k8s_master"
    MANAGERS = 'managers'
    ONE_MANAGER = 'one_manager'
    WORKERS = "workers"
    EDGES = "edges"
    # on ncs on openstack / vsphere
    DEPLOYER = 'deployer'
    # shared
    STORAGE = "storage"
    MONITOR = 'monitoring'

    # for the log implementation
    # logs get the objectives from the config file
    # this is just turn off the assert in that case
    NA = "not relevant to this case"

    @staticmethod
    def get_available_types(deployment_type):
        if DeploymentType.is_ncs(GlobalParameters.deployment_type):
            return [Objectives.ALL_NODES,
                    Objectives.ONE_MASTER,
                    Objectives.MASTERS,
                    Objectives.EDGES,
                    Objectives.WORKERS,
                    Objectives.MANAGERS,
                    Objectives.ONE_MANAGER,
                    Objectives.STORAGE,
                    Objectives.MONITOR,
                    Objectives.DEPLOYER
                    ]

        if DeploymentType.is_cbis(GlobalParameters.deployment_type):
            return [Objectives.ALL_HOSTS,
                    Objectives.ONE_CONTROLLER,
                    Objectives.CONTROLLERS,
                    Objectives.SRIOV_COMPUTES,
                    Objectives.OVS_COMPUTES,
                    Objectives.UC,
                    Objectives.HYP,
                    Objectives.COMPUTES,
                    Objectives.STORAGE
                    ]

    @staticmethod
    def get_all_single_types():
        return [
            Objectives.UC,
            Objectives.HYP,
            Objectives.ONE_CONTROLLER,
            Objectives.DEPLOYER,
            Objectives.ONE_MASTER
        ]