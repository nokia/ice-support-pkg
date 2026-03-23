from __future__ import absolute_import
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "ice", "lib"))
from tests.pytest.pytest_tools.operator.test_operator import ScenarioParams

module = type(sys)('pwd')
sys.modules['pwd'] = module


def pytest_make_parametrize_id(config, val, argname):
    if isinstance(val, ScenarioParams):
        return "ICE test: " + val.scenario_title

    # return None to let pytest handle the formatting
    return None
