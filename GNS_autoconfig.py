#!/usr/bin/python3

import requests
import threading
from pprint import pprint
from netaddr import IPNetwork
from jinja2 import Environment, FileSystemLoader
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
                                                "console_ip": single_node["console_host"],
                                                "id": single_node["node_id"],
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
            adresacja = str(IPNetwork(lista_sieci[j])[ostati_oktet])# + " " + str(IPNetwork(lista_sieci[j]).netmask)
            print(nazwa)
            print(interface)
            print(adresacja)

            if nazwa not in slownik_do_agregacji_interfacow.keys():
                slownik_do_agregacji_interfacow[nazwa] = []

            slownik_interfacy_zwykle = {interface: adresacja}
            slownik_do_agregacji_interfacow[nazwa].append({interface: adresacja})

    for router, interfacy in slownik_do_agregacji_interfacow.items():
        numer_routera = router[1:]
        address_loopbacka = str(numer_routera) + "." + str(numer_routera) + "." + str(numer_routera) + "." + str(numer_routera)# + " 255.255.255.255"
        slownik_do_agregacji_interfacow[router].append({"lo0": address_loopbacka})

    #print(slownik_do_agregacji_interfacow)


    #print(tab)
    return slownik_do_agregacji_interfacow


def generete_config_from_template(dane):
    RENDER = Environment(loader=FileSystemLoader('.'))  # tu podajemy sciezke do templatow '.'
    template = RENDER.get_template('config_temp.j2')
    konfiguracja_do_dodania = {}
    for key, value in dane.items():
        #print(key)
        generacja_templatu_dla_pojedynczego_urzadzenia = template.render(data = value)
        #print(generacja_templatu_dla_pojedynczego_urzadzenia)
        konfiguracja_do_dodania[key] = generacja_templatu_dla_pojedynczego_urzadzenia

    return konfiguracja_do_dodania



def start_all_nodes(nodes, project_id):

    for node_id in nodes.keys():
        url = "http://" + gns3_server_address + ":" + gns3_server_port + "/v2/projects/" + project_id + "/nodes/" + node_id + "/start"
        response = requests.request("POST", url)
        print(response)



def device_config(nodes, config_for_router):

    for info in nodes.values():

        if "Switch" not in info["name"]:

            device = {
                'device_type': 'cisco_ios_telnet',
                'ip': info["console_ip"],
                'port': info["console_port"],
            }

            while True:
                try:
                    net_connect = ConnectHandler(**device)
                    net_connect.send_command("\n\n\n")
                    print(net_connect.find_prompt())
                    break
                except:
                    pass

            net_connect.disconnect()



id = get_project_id_based_on_name("test")
nodes = get_all_nodes_info(id)
pprint(nodes)
links = (get_all_links_info(id))
pprint(links)
tab = modify_links(links, nodes)
pprint(tab)
konfig = generete_config_from_template(tab)
pprint(konfig)
start_all_nodes(nodes, id)
device_config(nodes, konfig)