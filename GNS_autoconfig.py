#!/usr/bin/python3

import requests
from pprint import pprint
from netaddr import IPNetwork
from netmiko import ConnectHandler

# GLOBAL VARIABLE:
gns3_server_address = "localhost"
gns3_server_port = "3080"
addressing = "192.168.0.0/16"
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
                                              "node_2_port": single_link["nodes"][1]["label"]["text"]}

    return links_dict


# def create_connection_table(nodes, links):
#
#     #connection_table = []
#     host = {}
#     for key, value in nodes.items():
#         # robimy tabele tylko dla routerow - jezeli mamy switcha to dla niego nie generujemy tabeli
#         # if "Switch" in value["name"]:
#         #     continue
#
#         #host = {}
#         #host["name"] = value["name"]
#         ports = []
#
#         for key2, value2 in links.items():
#
#             if value2["node_1_id"] == value["id"]:
#                 port = {}
#                 neighbors = []
#                 first_neighbor = {}
#                 port["number"] = value2["node_1_port"]
#                 first_neighbor["id"] = value2["node_2_id"]
#                 first_neighbor["port"] = value2["node_2_port"]
#                 first_neighbor["name"] = nodes[value2["node_2_id"]]["name"]
#                 neighbors.append(first_neighbor)
#                 port["neighbors"] = neighbors
#
#             elif value2["node_2_id"] == value["id"]:
#                 port = {}
#                 neighbors = []
#                 first_neighbor = {}
#                 port["number"] = value2["node_2_port"]
#                 first_neighbor["id"] = value2["node_1_id"]
#                 first_neighbor["port"] = value2["node_1_port"]
#                 first_neighbor["name"] = nodes[value2["node_1_id"]]["name"]
#                 neighbors.append(first_neighbor)
#                 port["neighbors"] = neighbors
#
#             else:
#                 continue
#
#             ports.append(port)
#
#         #host["ports"] = ports
#         #connection_table.append(host)
#         host[value["name"]] = ports
#
#     multi_access_connection_table = copy.copy(host)
#
#     # for i in range(len(host)):
#     #     for j in range(len(connection_table[i]["ports"])):
#     #         for k in range(len(connection_table[i]["ports"][j]['neighbors'])):
#     #             if "Switch" in connection_table[i]["ports"][j]['neighbors'][k]["name"]:
#     #                 sw_name = connection_table[i]["ports"][j]['neighbors'][k]["name"]
#     #                 del multi_access_connection_table[i]["ports"][j]['neighbors'][k]
#     pprint(host)
#     for name, ports in host.items():
#         for port in range(len(ports)):
#             for o in range(len(ports[port]['neighbors'])):
#                 print(ports[port]['neighbors'][o]["name"])
#                 if "Switch" in ports[port]['neighbors'][o]["name"]:
#                     sw_name = ports[port]['neighbors'][o]["name"]
#                     del multi_access_connection_table[name][port]["neighbors"][o]
#                     for abc in host[sw_name]:
#                         for element in abc["neighbors"]:
#                             print(element)
#                             multi_access_connection_table[name][port]["neighbors"].append(element)
#
#
#
#     return host

def modify_links(links, device):
    tab = []
    for key, value in links.items():
        id_1, id_2 = value["node_1_id"], value["node_2_id"]
        name_1, name_2 = device[id_1]["name"], device[id_2]["name"]
        port_1, port_2 = value["node_1_port"], value["node_2_port"]
        node_1 = name_1 + ":" + port_1 if "Switch" not in name_1 else name_1
        node_2 = name_2 + ":" + port_2 if "Switch" not in name_2 else name_2
        tablica = [node_1, node_2]
        tab.append(tablica)

    lista_sw = []
    print(tab)

    lista_sw = []
    for line in tab:
        for line2 in line:
            if "Switch" in line2:
                lista_sw.append(line2)
    lista_sw = list(set(lista_sw))

    print(lista_sw)
    #print(tab)

    for line in lista_sw:
        f_table = []
        print(line)
        f_table_link = []

        for line_links in range(len(tab)):
            if len(list(set(tab[line_links]).intersection([line]))) == 0:
                # print(tab[line_links])
                f_table_r = []
                f_table_r = tab[line_links]
                f_table.append(f_table_r)

            elif line in tab[line_links]:
                f_table_link = f_table_link + tab[line_links]
                #print(f_table_link)
                del f_table_link[f_table_link.index(line)]


        f_table.append(f_table_link)
        tab = f_table
        print(tab)

    lista_sieci = []
    siec = IPNetwork(addressing)
    siec_subnets = list(siec.subnet(24))
    for i in range(len(tab)):
        lista_sieci.append(str(siec_subnets[i]))

    print(lista_sieci)
    slownik_do_agregacji_interfacow = {}
    for j in range(len(tab)):
        for line2 in tab[j]:
            nazwa = line2.split(":")[0]
            interface = line2.split(":")[1]
            ostati_oktet = nazwa[1:]
            adresacja = str(IPNetwork(lista_sieci[j])[ostati_oktet]) + " " + str(IPNetwork(lista_sieci[j]).netmask)
            print(nazwa)
            print(interface)
            print(adresacja)

            if nazwa not in slownik_do_agregacji_interfacow.keys():
                slownik_do_agregacji_interfacow[nazwa] = []
                slownik_do_agregacji_interfacow[nazwa].append({interface: adresacja})

            else:
                slownik_do_agregacji_interfacow[nazwa].append({interface: adresacja})

    print(slownik_do_agregacji_interfacow)


    #print(tab)
    return slownik_do_agregacji_interfacow


def generete_config_from_template():
    pass

id = get_project_id_based_on_name("test")
nodes = get_all_nodes_info(id)
pprint(nodes)
links = (get_all_links_info(id))
pprint(links)
modify_links(links, nodes)