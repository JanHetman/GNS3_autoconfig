#!/usr/bin/python3

import sys
import threading
import time
import requests
import json

from pprint import pprint
from jinja2 import Environment, FileSystemLoader
from netaddr import IPNetwork
from netmiko import ConnectHandler


# GLOBAL VARIABLE:
GNS3_SERVER_ADDRESS = "localhost"
GNS3_SERVER_PORT = "3080"
ADDRESSING = "10.15.128.0/18"


def get_project_name():
    project_name = input("Podaj nazwe projektu: ")
    return project_name


def get_project_id_based_on_name(project_name):
    url = "http://" + GNS3_SERVER_ADDRESS + ":" + GNS3_SERVER_PORT + "/v2/projects"

    try:
        response = requests.request("GET", url)
    except requests.exceptions.ConnectionError:
        print("Brak odpowiedzi od serwera GNS3.")
        sys.exit(1)

    for single_project in response.json():
        if project_name == single_project["name"]:
            return single_project["project_id"]
    else:
        print("Nie ma takiego projektu")
        sys.exit(1)


def get_all_nodes_info(project_id):
    url = "http://" + GNS3_SERVER_ADDRESS + ":" + GNS3_SERVER_PORT + "/v2/projects/" + project_id + "/nodes"
    response = requests.request("GET", url)

    devices_dict = {}

    try:
        for single_node in response.json():
            os = single_node.get('properties', None).get('image', None)
            devices_dict[single_node["node_id"]] = {"name": single_node["name"],
                                                    "console_ip": single_node["console_host"],
                                                    "id": single_node["node_id"],
                                                    "console_port": single_node["console"],
                                                    "device_type": single_node["node_type"],
                                                    "os": os}
    except KeyError:
        print("Projekt nie otwarty lub niestandardowe parametry urzadzen")
        sys.exit(1)

    return devices_dict


def get_all_links_info(project_id):
    url = "http://" + GNS3_SERVER_ADDRESS + ":" + GNS3_SERVER_PORT + "/v2/projects/" + project_id + "/links"
    response = requests.request("GET", url)

    links_dict = {}

    for single_link in response.json():
        links_dict[single_link["link_id"]] = {"node_1_id": single_link["nodes"][0]["node_id"],
                                              "node_1_port": single_link["nodes"][0]["label"]["text"],
                                              "node_2_id": single_link["nodes"][1]["node_id"],
                                              "node_2_port": single_link["nodes"][1]["label"]["text"]}

    return links_dict


def check_naming_convention(nodes):
    list_of_nodes = []
    # pprint(nodes)

    for single_node in nodes.values():
        list_of_nodes.append(single_node['name'] + ":" + single_node['device_type'])

    nodes_verificarion = [x for x in list_of_nodes if
         ((len(x.split(':')[0]) <= 4 and x.split(':')[0][1:].isdigit() and 0 < int(x.split(':')[0][1:]) < 224) or "ethernet" in x.split(':')[1])]

    if list_of_nodes == nodes_verificarion:
        print("Wymogi spelnione")
        return True
    else:
        return False


def modify_links(links, nodes, decision):
    connection_tab = []

    for key, value in links.items():
        id_1, id_2 = value["node_1_id"], value["node_2_id"]
        name_1, name_2 = nodes[id_1]["name"], nodes[id_2]["name"]
        port_1, port_2 = value["node_1_port"], value["node_2_port"]
        node_1 = name_1 + ":" + port_1 if "switch" not in nodes[id_1]['device_type'] else name_1
        node_2 = name_2 + ":" + port_2 if "switch" not in nodes[id_2]['device_type'] else name_2
        connection_tab.append([node_1, node_2])

    list_of_switches = list({single_device for single_connection in connection_tab for single_device in single_connection if ":" not in single_device})
    # print(list_of_switches)

    for single_switch in list_of_switches:
        final_connection_table = []
        link_with_switch = []

        for single_link in connection_tab:
            if len(list(set(single_link).intersection([single_switch]))) == 0:
                final_connection_table.append(single_link)
            elif single_switch in single_link:
                link_with_switch += single_link
                del link_with_switch[link_with_switch.index(single_switch)]

        final_connection_table.append(link_with_switch)
        connection_tab = final_connection_table
        # print(connection_tab)

    list_of_networks_using_in_topology = []
    address_pool = IPNetwork(ADDRESSING)
    list_of_all_networks_in_address_pool = list(address_pool.subnet(24))

    for index_for_single_link in range(len(connection_tab)):
        try:
            list_of_networks_using_in_topology.append(str(list_of_all_networks_in_address_pool[index_for_single_link]))
        except IndexError:
            print("Bledna wartosc zmiennej 'ADDRESSING'.")
            sys.exit(1)

    # print(list_of_networks_using_in_topology)
    device_numering_for_non_standard_names = {}

    if not decision:
        for count, value in enumerate(nodes.values(), 1):
            value['number'] = count
            device_numering_for_non_standard_names[value['name']] = count

        # pprint(device_numering_for_non_standard_names)

    grouping_interfaces_on_devices = {}
    for index_for_single_link in range(len(connection_tab)):
        for node_on_single_link in connection_tab[index_for_single_link]:
            node_name = node_on_single_link.split(":")[0]
            node_interface = node_on_single_link.split(":")[1]
            last_octet_in_ip_address = node_name[1:] if decision else device_numering_for_non_standard_names[node_name]
            interface_address = str(IPNetwork(list_of_networks_using_in_topology[index_for_single_link])[last_octet_in_ip_address])
            network_address = str(IPNetwork(list_of_networks_using_in_topology[index_for_single_link]).network)
            interface_mask = "255.255.255.0"
            interface_wildcard_mask = "0.0.0.255"
            # print(node_name)
            # print(node_interface)
            # print(interface_address)

            if node_name not in grouping_interfaces_on_devices:
                grouping_interfaces_on_devices[node_name] = {}
                loopback_address = "{0}.{0}.{0}.{0}".format(last_octet_in_ip_address)
                loopback_mask = "255.255.255.255"
                loppback_wilcard = "0.0.0.0"
                grouping_interfaces_on_devices[node_name]["lo0"] = {"address": loopback_address,
                                                                 "mask": loopback_mask,
                                                                 "wildcard_mask": loppback_wilcard,
                                                                 "network_address": loopback_address}

            grouping_interfaces_on_devices[node_name][node_interface] = {"address": interface_address,
                                                                 "mask": interface_mask,
                                                                 "wildcard_mask": interface_wildcard_mask,
                                                                 "network_address": network_address}

    return grouping_interfaces_on_devices


def generete_config_from_template(data, nodes):
    RENDER = Environment(loader=FileSystemLoader('.'))
    information_about_nodes_os = {}

    for device_data in nodes.values():
        information_about_nodes_os[device_data['name']] = device_data['os']

    # print(information_about_nodes_os)
    config_to_add = {}

    for key, value in data.items():
        # if information_about_nodes_os[key] == 'c7200-adventerprisek9-mz.124-24.T5.image':
        #     template = RENDER.get_template('config_temp.j2')
        # elif information_about_nodes_os[key] == 'your_image.image':
        #     template = RENDER.get_template('your_template.j2')
        # .
        # .
        # .

        template = RENDER.get_template('config_temp.j2')
        config_for_single_node = template.render(data=value)
        config_to_add[key] = config_for_single_node

    return config_to_add


def start_all_nodes(nodes, project_id):
    for node_id in nodes:
        url = "http://" + GNS3_SERVER_ADDRESS + ":" + GNS3_SERVER_PORT + "/v2/projects/" + project_id + "/nodes/" + node_id + "/start"
        response = requests.request("POST", url)
        if '200' in response.text:
            print("Urządzenie {0} włączone, proszę czekać".format(nodes[node_id]['name']))


def create_threads_for_device_config(nodes, config_for_router):
    threads = []

    for node_info in nodes.values():
        if node_info["name"] in config_for_router:
            th = threading.Thread(target=device_config, args=(node_info, config_for_router[node_info["name"]]))
            time.sleep(0.1)
            th.start()
            threads.append(th)

    for th in threads:
        th.join()


def device_config(node_info, config_for_router):
    # if node_info['os'] == 'c7200-adventerprisek9-mz.124-24.T5.image':
    #     device_type = 'cisco_ios_telnet'
    # elif node_info['os'] == 'your_image.image':
    #     device_type = 'your_device_type_telnet'
    # .
    # .
    # .

    device = {
        'device_type': 'cisco_ios_telnet',
        'ip': node_info["console_ip"],
        'port': node_info["console_port"],
    }

    while True:
        try:
            net_connect = ConnectHandler(**device)
            break
        except:
            pass

    net_connect.send_command("\n\n\n\n")
    print("Trwa konfiguracja " + node_info['name'])

    for line_of_config in config_for_router.splitlines():
        net_connect.send_command(line_of_config, expect_string=r'#')

    print("Konfiguracja " + node_info['name'] + " zakonczona")


if __name__ == '__main__':
    name = get_project_name()
    id = get_project_id_based_on_name(name)
    nodes = get_all_nodes_info(id)
    decision = check_naming_convention(nodes)
    links = get_all_links_info(id)
    connection_tab = modify_links(links, nodes, decision)
    print("=======================================================================")
    print("Wygenerowana adresacja dla urządzeń")
    print(json.dumps(connection_tab, indent=4))
    print("=======================================================================")
    config = generete_config_from_template(connection_tab, nodes)
    # pprint(config)
    start_all_nodes(nodes, id)
    print("=======================================================================")
    create_threads_for_device_config(nodes, config)