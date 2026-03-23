from __future__ import absolute_import
import pytest
from flows.Etcd.etcd_validations import VerifyETCDRulesPresentInIPtables, EtcdBCMTTransactionsCountValidator
from tests.pytest.pytest_tools.operator.test_validation_base import ValidationTestBase, ValidationScenarioParams
from tests.pytest.pytest_tools.operator.test_operator import CmdOutput
from tests.pytest.tools.versions_alignment import Mock

class TestVerifyETCDRulesPresentInIPtables(ValidationTestBase):

    tested_type = VerifyETCDRulesPresentInIPtables

    validation_cmd = "sudo iptables -t nat -L | grep 2379"

    out = """
CNI-HOSTPORT-SETMARK  tcp  --  169.254.170.0/24     localhost            tcp dpt:2379
CNI-HOSTPORT-SETMARK  tcp  --  localhost            localhost            tcp dpt:2379
DNAT       tcp  --  anywhere             localhost            tcp dpt:2379 to:169.254.170.2:2379
CNI-HOSTPORT-SETMARK  tcp  --  169.254.170.0/24     fi822b-22-12-ice-control-02  tcp dpt:2379
CNI-HOSTPORT-SETMARK  tcp  --  localhost            fi822b-22-12-ice-control-02  tcp dpt:2379
DNAT       tcp  --  anywhere             fi822b-22-12-ice-control-02  tcp dpt:2379 to:169.254.170.2:2379
CNI-DN-fcdb424376254e82e96d6  tcp  --  anywhere             anywhere             /* dnat name: "podman" id: "8777c5ee1a45fd3132bfe1fafc2850c12411774a32f37fdb6af70ce44f2e9c38" */ multiport dports 2379,2379,2380
"""

    scenario_passed = [
        ValidationScenarioParams(scenario_title="ETCD rules are present",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out=out)}
                                 )
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="ETCD rules not present",
                                 cmd_input_output_dict={validation_cmd: CmdOutput(out="")}
                                 )
    ]

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)


class TestEtcdBCMTTransactionsCountValidator(ValidationTestBase):
    EtcdBCMTTransactionsCountValidator.TRANSACTION_COUNT_THRESHOLD = 3
    tested_type = EtcdBCMTTransactionsCountValidator

    etcd_cmd = "sudo cat /etc/etcd/etcd_endpoints.yml"
    etcd_cmd_out = 'etcd_endpoints: "https://172.31.7.2:2379,https://172.31.7.4:2379,https://172.31.7.5:2379"'

    validation_cmd = "sudo ETCDCTL_API=3 bash -c 'etcdctl --endpoints=https://172.31.7.2:2379,https://172.31.7.4:2379,https://172.31.7.5:2379 --cacert=/etc/etcd/ssl/ca.pem --cert=/etc/etcd/ssl/etcd-client.pem --key=/etc/etcd/ssl/etcd-client-key.pem get --prefix /BCMTClusterManager/ --keys-only | grep BCMTClusterManager/transactions/ | wc -l '"
    out = "3"

    scenario_prerequisite_not_fulfilled = [
        ValidationScenarioParams(scenario_title="prerequisite not fulfilled",
                                 tested_object_mock_dict={"is_etcd_API_3": Mock(return_value=False)}
                                 )
    ]

    scenario_prerequisite_fulfilled = [
        ValidationScenarioParams(scenario_title="prerequisite fulfilled",
                                 tested_object_mock_dict={"is_etcd_API_3": Mock(return_value=True)}
                                 )
    ]

    scenario_passed = [
        ValidationScenarioParams(scenario_title="transactions count lower than threshold",
                                 cmd_input_output_dict={etcd_cmd: CmdOutput(out=etcd_cmd_out),
                                                        validation_cmd: CmdOutput(out=out)}
                                 ),
        ValidationScenarioParams(scenario_title="no transactions found",
                                 cmd_input_output_dict={etcd_cmd: CmdOutput(out=etcd_cmd_out),
                                                        validation_cmd: CmdOutput(out="0")}
                                 )
    ]

    scenario_failed = [
        ValidationScenarioParams(scenario_title="transactions count higher than threshold",
                                 cmd_input_output_dict={etcd_cmd: CmdOutput(out=etcd_cmd_out),
                                                        validation_cmd: CmdOutput(out="5")}
                                 )
    ]

    scenario_unexpected_system_output = [
        ValidationScenarioParams(scenario_title="unexpected output returned",
                                 cmd_input_output_dict={etcd_cmd: CmdOutput(out=etcd_cmd_out),
                                                        validation_cmd: CmdOutput(out="", return_code=1)}
                                 )
    ]

    @pytest.mark.parametrize("scenario_params", scenario_prerequisite_not_fulfilled)
    def test_prerequisite_not_fulfilled(self, scenario_params, tested_object):
        ValidationTestBase.test_prerequisite_not_fulfilled(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_prerequisite_fulfilled)
    def test_prerequisite_fulfilled(self, scenario_params, tested_object):
        ValidationTestBase.test_prerequisite_fulfilled(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_passed)
    def test_scenario_passed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_passed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_failed)
    def test_scenario_failed(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_failed(self, scenario_params, tested_object)

    @pytest.mark.parametrize("scenario_params", scenario_unexpected_system_output)
    def test_scenario_unexpected_system_output(self, scenario_params, tested_object):
        ValidationTestBase.test_scenario_unexpected_system_output(self, scenario_params, tested_object)
