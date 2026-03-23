from __future__ import absolute_import
from __future__ import print_function
import ast
import heapq
import json
import os
from collections import OrderedDict
from os import listdir
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../..")))
from tests.debug_tools.debug_tools_helper import *


def create_res_dict(out_dir):
    res_dict = {}
    for ip in listdir(out_dir):
        ip_path = os.path.join(out_dir, ip)
        if os.path.isdir(ip_path):
            for file_name in listdir(ip_path):
                if ".decrypted.log" in file_name:
                    with open(os.path.join(ip_path, file_name), "r") as f:
                        for line in f.readlines():
                            if "top 10 large streams" in line:
                                res_dict[ip] = json.loads(line.split("INFO ")[1])["top 10 large streams"]
    return res_dict


def create_top_10_res_dict(res_dict):
    top_10_res_dict = {}
    top_10_large_streams = {"out": [], "err": []}
    for stream in list(top_10_large_streams.keys()):
        for ip, stream_dict in list(res_dict["Large streams from all ips"].items()):
            if not len(list(stream_dict[stream].keys())):
                continue
            top_10_large_streams[stream].extend(list(stream_dict[stream].keys()))
    top_10_large_streams = {k: heapq.nlargest(10, list(set(v))) for k, v in list(top_10_large_streams.items())}
    for ip, stream_dict in list(res_dict["Large streams from all ips"].items()):
        for stream in top_10_large_streams:
            for len_stream in top_10_large_streams[stream]:
                if len_stream in list(stream_dict[stream].keys()):
                    top_10_res_dict.setdefault(stream, {}).setdefault(int(len_stream), {}).setdefault(ip, stream_dict[
                        stream][len_stream])
    return OrderedDict(
        (outer_key, OrderedDict(sorted(list(inner_dict.items()), reverse=True)))
        for outer_key, inner_dict in list(top_10_res_dict.items())
    )


def main():
    out_dir = DebugToolsHelper.get_out_dir()
    res_dict = {"Large streams from all ips": create_res_dict(out_dir)}
    res_dict["Top 10 large streams"] = create_top_10_res_dict(res_dict)

    out_file = os.path.join(out_dir, "top_10_large_streams.json")
    with open(out_file, "w") as f:
        f.write(json.dumps(res_dict, indent=4))
    print("save file in {}".format(out_file))


if __name__ == '__main__':
    main()
