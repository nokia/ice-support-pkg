from __future__ import absolute_import
from HealthCheckCommon.printer import StructedPrinter
from mains.file_tracker_static_test_main import FileTrackerStaticTestMain

if __name__ == '__main__':
    StructedPrinter.encrypt_out = False
    my_main = FileTrackerStaticTestMain()
    my_main.run_me(parser_description='run static tests for file tracker')


