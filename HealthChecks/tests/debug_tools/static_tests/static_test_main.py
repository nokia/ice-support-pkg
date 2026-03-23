from __future__ import absolute_import
import os
import sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.append(os.path.join(os.getcwd(), "..", "ice", "lib"))

from tests.debug_tools.static_tests.Tester import Tester

if __name__ == '__main__':
    Tester().run_tests()
