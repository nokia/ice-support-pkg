from __future__ import absolute_import
from __future__ import print_function
import sys, os
import argparse
import json
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "ice", "lib"))
from tools.UI.HTMLPrint import create_validation_summary_html
import tools.global_logging as log


def logger_mock(text):
    print(text)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Call HTML builder with a json file.")
    parser.add_argument('-f', '--json-path', type=str, help='Path to out json file.', required=True)

    args = parser.parse_args()
    json_out_path = args.json_path

    with open(json_out_path) as f:
        json_out = json.load(f)

    log.log_and_print = logger_mock
    create_validation_summary_html(json_out, "out.html", "unknown", "unknown", "unknown",  "unknown", "unknown",
                                   {}, {}, "unknown", "unknown", "unknown", "unknown")
