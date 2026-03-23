from __future__ import absolute_import
from __future__ import print_function
import json

with open("list_23_10.json", "r") as file:
    data = json.load(file)

data = data["available flows for this system are:"]

for domain in data:
    for validtion in data[domain]:
       print("{} , {}, {} ".format(domain, validtion['title'],validtion.get('documentation link',"")))

