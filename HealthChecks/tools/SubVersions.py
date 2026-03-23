from __future__ import absolute_import
from tools.global_enums import Deployment_type, Version, SubVersion

# PPs and MPs list should be updated once in a while info is taken from :
# https://nokia.sharepoint.com/:f:/r/sites/CBInfo/CloudBand%20Documents/Public/Product%20Programs/CBIS/Releases/Maintenance%20Releases%20-%20MP%20%26%20PP?csf=1&web=1&e=3tLQ9X

SUB_VERSION_DICT = {
    Deployment_type.CBIS: {
        Version.V19: {
            1564: SubVersion.MP2,
            1438: SubVersion.MP4,
            1745: SubVersion.MP5
        },
        Version.V19A: {
            1633: SubVersion.MP3
        }
    }
}

# A mapping between hotfix number and hotfix name.
# For example, the version number of NCS22.12 MP3 is 22.12.5, so the hotfix number is '5' and the hotfix name is 'MP3'.
CNA_HOTFIX_MAPPING_DICT = {
    Version.V24_7:{
      "1": SubVersion.MP1
    },
    Version.V23_10: {
        "1": SubVersion.MP1
    },
    Version.V22_12: {
        "1": SubVersion.PP1,
        "2": SubVersion.PP2,
        "3": SubVersion.MP1,
        "4": SubVersion.MP2,
        "5": SubVersion.MP3
    },
    Version.V20_FP2: {
        "2": SubVersion.PP4,
        "14": SubVersion.PP14,
        "17": SubVersion.MP1
    }
}

HOT_FIX_DICT = {
    Deployment_type.CBIS: {
        Version.V19: {
            SubVersion.NO_MP: [SubVersion.PP1],
            SubVersion.MP2: [SubVersion.NO_PP, SubVersion.PP2, SubVersion.PP1],
            SubVersion.SP3: [SubVersion.NO_PP, SubVersion.PP2, SubVersion.PP1, SubVersion.PP3],
            SubVersion.MP4: [SubVersion.NO_PP, SubVersion.PP4, SubVersion.PP3, SubVersion.PP2, SubVersion.PP1],
            SubVersion.MP5: [SubVersion.NO_PP, SubVersion.PP2, SubVersion.PP1],
        },
        Version.V19A: {
            SubVersion.NO_MP: [SubVersion.NO_PP],
            SubVersion.SP1: [SubVersion.NO_PP],
            SubVersion.SP2: [SubVersion.NO_PP, SubVersion.PP1],
            SubVersion.MP3: [SubVersion.NO_PP],
            SubVersion.SP4: [SubVersion.NO_PP, SubVersion.PP1, SubVersion.PP2, SubVersion.PP3, SubVersion.PP4],
            SubVersion.MP5: [SubVersion.NO_PP, SubVersion.PP1, SubVersion.PP2],
        },
        Version.V20: {
            SubVersion.NO_MP: [SubVersion.NO_PP, SubVersion.PP1, SubVersion.PP2, SubVersion.PP3, SubVersion.PP4, SubVersion.PP5],
            SubVersion.SP1: [SubVersion.NO_PP],
            SubVersion.SP2: [SubVersion.NO_PP],
            SubVersion.SP3: [SubVersion.NO_PP, SubVersion.PP1],
            SubVersion.MP4: [SubVersion.NO_PP, SubVersion.PP1],
            SubVersion.MP5: [SubVersion.NO_PP, SubVersion.PP1],
            SubVersion.MP6: [SubVersion.NO_PP, SubVersion.PP1, SubVersion.PP2]
        },
        Version.V22: {
            SubVersion.NO_MP: [SubVersion.NO_PP, SubVersion.PP1]
        },
        Version.V22_FP1: {
            SubVersion.NO_MP: [SubVersion.NO_PP, SubVersion.PP1],
            SubVersion.MP1: [SubVersion.NO_PP],
            SubVersion.MP1_2: [SubVersion.NO_PP],
            SubVersion.MP2: [SubVersion.NO_PP],
            SubVersion.MP3: [SubVersion.NO_PP]
        },
        Version.V24: {
            SubVersion.NO_MP: [SubVersion.NO_PP],
            SubVersion.MP1: [SubVersion.NO_PP, SubVersion.PP2],
            SubVersion.MP1_2: [SubVersion.NO_PP],
            SubVersion.MP2: [SubVersion.NO_PP]
        },
        Version.V25: {
            SubVersion.NO_MP: [SubVersion.NO_PP],
            SubVersion.MP1: [SubVersion.NO_PP]
        }
    },
    # NCS released version - https://confluence.ext.net.nokia.com/pages/viewpage.action?spaceKey=NCS&title=NCS+Maintenance+and+Priority+Pack+releases
    Deployment_type.NCS_OVER_BM: {
        Version.V20_FP1: {
            SubVersion.NO_MP: [SubVersion.NO_PP, SubVersion.PP1],
        },
        Version.V20_FP2: {
            SubVersion.NO_MP: [SubVersion.NO_PP, SubVersion.PP1, SubVersion.PP3, SubVersion.PP5, SubVersion.PP6,
                               SubVersion.PP7, SubVersion.PP8, SubVersion.PP9, SubVersion.PP10, SubVersion.PP11,
                               SubVersion.SU3, SubVersion.PP12, SubVersion.PP13, SubVersion.PP15],
            SubVersion.MP1: [SubVersion.NO_PP]
        },
        Version.V22: {
            SubVersion.NO_MP: [SubVersion.NO_PP, SubVersion.PP1],
        },
        Version.V22_7: {
            SubVersion.NO_MP: [SubVersion.NO_PP, SubVersion.PP1, SubVersion.PP2]
        },
        Version.V22_12: {
            # NCS22.12 PP0 is only for TMO - subset of MP1 due to security isues
            SubVersion.NO_MP: [SubVersion.NO_PP, SubVersion.PP0, SubVersion.PP1, SubVersion.PP2],
            SubVersion.MP1: [SubVersion.NO_PP],
            SubVersion.MP2: [SubVersion.NO_PP],
            SubVersion.MP3: [SubVersion.NO_PP]
        },
        Version.V23_10: {
            SubVersion.NO_MP: [SubVersion.NO_PP, SubVersion.PP1],
            SubVersion.MP1: [SubVersion.NO_PP],
            SubVersion.MP2: [SubVersion.NO_PP]
        },
        Version.V24_7: {
            SubVersion.NO_MP: [SubVersion.NO_PP],
            SubVersion.MP1: [SubVersion.NO_PP],
            SubVersion.MP2: [SubVersion.NO_PP]
        },
        Version.V24_11: {
            SubVersion.NO_MP: [SubVersion.NO_PP],
            SubVersion.MP1: [SubVersion.NO_PP]
        },
        Version.V25_7: {
            SubVersion.NO_MP: [SubVersion.NO_PP, SubVersion.PP1],
            SubVersion.MP1: [SubVersion.NO_PP]
        },
        Version.V25_11: {
            SubVersion.NO_MP: [SubVersion.NO_PP]
        },
        Version.V26_7: {
            SubVersion.NO_MP: [SubVersion.NO_PP]
        }
    },
    Deployment_type.NCS_OVER_OPENSTACK:{
        Version.V20: {
            SubVersion.NO_MP: [SubVersion.NO_PP, SubVersion.PP1],
        },
        Version.V20_FP2: {
            SubVersion.NO_MP: [SubVersion.NO_PP, SubVersion.PP2, SubVersion.PP4, SubVersion.PP14, SubVersion.SU4],
            SubVersion.MP1: [SubVersion.NO_PP],
        },
        Version.V22_7: {
            SubVersion.NO_MP: [SubVersion.NO_PP, SubVersion.PP1, SubVersion.PP2]
        },
        Version.V22_12: {
            SubVersion.NO_MP: [SubVersion.NO_PP, SubVersion.PP1, SubVersion.PP2],
            SubVersion.MP1: [SubVersion.NO_PP],
            SubVersion.MP2: [SubVersion.NO_PP],
            SubVersion.MP3: [SubVersion.NO_PP]
        },
        Version.V23_10: {
            SubVersion.NO_MP: [SubVersion.NO_PP, SubVersion.PP1],
            SubVersion.MP1: [SubVersion.NO_PP],
            SubVersion.MP2: [SubVersion.NO_PP]
        },
        Version.V24_7: {
            SubVersion.NO_MP: [SubVersion.NO_PP],
            SubVersion.MP1: [SubVersion.NO_PP],
            SubVersion.MP2: [SubVersion.NO_PP]
        },
        Version.V24_11: {
            SubVersion.NO_MP: [SubVersion.NO_PP],
            SubVersion.MP1: [SubVersion.NO_PP]
        },
        Version.V25_7: {
            SubVersion.NO_MP: [SubVersion.NO_PP, SubVersion.PP1],
            SubVersion.MP1: [SubVersion.NO_PP]
        },
        Version.V25_11: {
            SubVersion.NO_MP: [SubVersion.NO_PP]
        },
        Version.V26_7: {
            SubVersion.NO_MP: [SubVersion.NO_PP]
        }
    },
    Deployment_type.NCS_OVER_VSPHERE:{
        Version.V20: {
            SubVersion.NO_MP: [SubVersion.NO_PP, SubVersion.PP1],
        },
        Version.V20_FP2: {
            SubVersion.NO_MP: [SubVersion.NO_PP, SubVersion.PP4, SubVersion.PP16],
        },
        Version.V22: {
            SubVersion.NO_MP: [SubVersion.NO_PP, SubVersion.PP2, SubVersion.PP3, SubVersion.PP4],
        }
    }
}
# todo -automatic_test updated
LATEST_PP_DICT = {
    Deployment_type.CBIS: {
        Version.V19: {
            SubVersion.MP5: [SubVersion.PP2]
        },
        Version.V19A: {
            SubVersion.MP5: [SubVersion.PP2]
        },
        Version.V20: {
            SubVersion.MP6: [SubVersion.PP2]
        },
        Version.V22: {
            SubVersion.NO_MP:  [SubVersion.NO_PP, SubVersion.PP1]
        },
        Version.V22_FP1: {
            SubVersion.MP3: [SubVersion.NO_PP]
        },
        Version.V24: {
            SubVersion.MP2: [SubVersion.NO_PP]

        },
        Version.V25: {
            SubVersion.NO_MP: [SubVersion.NO_PP]
        }
    },
    Deployment_type.NCS_OVER_BM: {
        Version.V20_FP1: {
            SubVersion.NO_MP: [SubVersion.PP1],
        },
        Version.V20_FP2: {
            SubVersion.MP1: [SubVersion.NO_PP]
        },
        Version.V22: {
            SubVersion.NO_MP: [SubVersion.PP1]
        },
        Version.V22_7: {
            SubVersion.NO_MP: [SubVersion.PP2]
        },
        Version.V22_12: {
            SubVersion.MP3: [SubVersion.NO_PP]
        },
        Version.V23_10: {
            SubVersion.MP1: [SubVersion.NO_PP],
        },
        Version.V24_7: {
            SubVersion.MP1: [SubVersion.NO_PP],
            SubVersion.MP2: [SubVersion.NO_PP]
        },
        Version.V24_11: {
            SubVersion.NO_MP: [SubVersion.NO_PP]
        },
        Version.V25_7: {
            SubVersion.NO_MP: [SubVersion.NO_PP]
        },
        Version.V25_11: {
            SubVersion.NO_MP: [SubVersion.NO_PP]
        },
        Version.V26_7: {
            SubVersion.NO_MP: [SubVersion.NO_PP]
        }
    },
    Deployment_type.NCS_OVER_OPENSTACK: {
        Version.V20: {
            SubVersion.NO_MP: [SubVersion.PP1],
        },
        Version.V20_FP2: {
            SubVersion.MP1: [SubVersion.NO_PP],
        },
        Version.V22_7: {
            SubVersion.NO_MP: [SubVersion.PP2]
        },
        Version.V22_12: {
            SubVersion.MP3: [SubVersion.NO_PP]
        },
        Version.V23_10: {
            SubVersion.MP1: [SubVersion.NO_PP]
        },
        Version.V24_7: {
            SubVersion.MP1: [SubVersion.NO_PP],
            SubVersion.MP2: [SubVersion.NO_PP]
        },
        Version.V24_11: {
            SubVersion.NO_MP: [SubVersion.NO_PP]
        },
        Version.V25_7: {
            SubVersion.NO_MP: [SubVersion.NO_PP]
        },
        Version.V25_11: {
            SubVersion.NO_MP: [SubVersion.NO_PP]
        },
        Version.V26_7: {
            SubVersion.NO_MP: [SubVersion.NO_PP]
        }
    },
    Deployment_type.NCS_OVER_VSPHERE: {
        Version.V20: {
            SubVersion.NO_MP: [SubVersion.PP1],
        },
        Version.V20_FP2: {
            SubVersion.NO_MP: [SubVersion.PP16],
        },
        Version.V22: {
            SubVersion.NO_MP: [SubVersion.PP4],
        }
    }
}
