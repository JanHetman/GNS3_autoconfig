#!/usr/bin/python3

import requests
from pprint import pprint
from netmiko import ConnectHandler

# GLOBAL VARIABLE:
gns3_server_address = "localhost"
gns3_server_port = "3080"
# GLOBAL VARIABLE END

def get_project_id_based_on_name(project_name):

    url = "http://" + gns3_server_address + ":" + gns3_server_port + "/v2/projects"
    response = requests.request("GET", url)

    for single_project in response.json():
        if project_name == single_project["name"]:
            return single_project["project_id"]
        else:
            continue
    else:
        return None


def get_all_nodes_info(project_id):

    url = "http://" + gns3_server_address + ":" + gns3_server_port + "/v2/projects/" + project_id + "/nodes"
    response = requests.request("GET", url)

    devices_dict = {}

    for single_node in response.json():
        devices_dict[single_node["node_id"]] = {"name": single_node["name"],
                                                "id": single_node["node_id"],
                                                "console_ip": single_node["console_host"],
                                                "console_port": single_node["console"],
                                                "device_type": single_node["node_type"]}

    return devices_dict


def get_all_links_info(project_id):

    url = "http://" + gns3_server_address + ":" + gns3_server_port + "/v2/projects/" + project_id + "/links"
    response = requests.request("GET", url)

    links_dict = {}

    for single_link in response.json():
        links_dict[single_link["link_id"]] = {"node_1_id": single_link["nodes"][0]["node_id"],
                                              "node_1_port": single_link["nodes"][0]["label"]["text"],
                                              "node_2_id": single_link["nodes"][1]["node_id"],
                                              "node_2_port": single_link["nodes"][0]["label"]["text"]}

    return links_dict


id = get_project_id_based_on_name("test")
nodes = get_all_nodes_info(id)
pprint(nodes)
pprint(get_all_links_info(id))