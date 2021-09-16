"""
Created on May 20 2021 12:32 PM

@author: sabraham 
"""
import pandas as pd
import opendssdirect as dss
import os
import numpy as np
import networkx as nx
import sys
import matplotlib.pyplot as plt


def load_feeder(master_filepath):
    dss.run_command("Clear")
    r = dss.run_command(f"Redirect {master_filepath}")
    if r != '':
        raise ValueError(f"Error: {r}. \nSomething went wrong: check your master path {master_filepath}")
    else:
        return r


def plot_feeder(dss, render_plot=True, find_node=None):
    """
    This function plots the networkX representation of a given feeder
    and locates PV unites. Other items such us transformers, capacitors can
    be marked as well.
    """

    """
    LINES"""
    line_dict = {}
    dss.Circuit.SetActiveClass("Line")
    flag = dss.ActiveClass.First()
    while flag > 0:
        # Get the name of the Transformer
        line_name = dss.CktElement.Name().split('Line.')[1]
        line_fullname = dss.CktElement.Name()

        frombus = dss.Lines.Bus1().split('.')[0]
        tobus = dss.Lines.Bus2().split('.')[0]

        n_phases = dss.CktElement.NumPhases()

        line_dict[line_name] = {'Fullname': line_fullname, 'From Bus': frombus,
                                'To Bus': tobus,
                                'number_of_phases': n_phases}
        # Move on to the next Transformer...
        flag = dss.ActiveClass.Next()

    line_df = pd.DataFrame.from_dict(line_dict, orient='index')
    line_df = line_df.reset_index().rename(columns={'index': 'Name'})
    line_df['Type'] = 'Line'

    """
    # get list of all transformers
    # identify transformers with highest primary voltage level. These are the substation transformers
    # identify line connected to each of these substations. Any thing connected after this belongs to that transformer
    """

    transformer_dict = {}
    dss.Circuit.SetActiveClass("Transformer")
    flag = dss.ActiveClass.First()
    while flag > 0:
        # Get the name of the Transformer
        transformer_name = dss.CktElement.Name().split('Transformer.')[1]
        transformer_fullname = dss.CktElement.Name()

        bus_array = dss.Properties.Value('buses')
        bus_array = list([b.split('.')[0].strip() for b in bus_array.split('[')[1].split(', ]')[0].split(',')])
        # print(bus_array)
        bus_array = [bus_array[0]] + list(np.unique(bus_array[1:]))
        primary_bus = bus_array[0]
        secondary_bus = bus_array[1].split('.')[0]

        hs_kv = float(dss.Properties.Value('kVs').split('[')[1].split(',')[0])
        ls_kv = float(dss.Properties.Value('kVs').split('[')[1].split(',')[1])
        kva = float(dss.Properties.Value('kVA'))
        n_phases = dss.CktElement.NumPhases()
        # primary_bus = dss.Properties.Value("buses").split('[')[1].split(',')[0]
        # secondary_bus = dss.Properties.Value("buses").split('[')[1].split(', ')[1]

        transformer_dict[transformer_name] = {'Fullname': transformer_fullname, 'From Bus': primary_bus,
                                              'To Bus': secondary_bus,
                                              'High-side voltage': hs_kv, 'Low-side voltage': ls_kv,
                                              'kVA': kva, 'number_of_phases': n_phases}
        # Move on to the next Transformer...
        flag = dss.ActiveClass.Next()

    transformer_df = pd.DataFrame.from_dict(transformer_dict, orient='index')
    transformer_df = transformer_df.reset_index().rename(columns={'index': 'Name'})
    transformer_df['Type'] = 'Transformer'
    transformer_buses = list(transformer_df['From Bus'].values)

    combine_edges_input_df = transformer_df.append(line_df)
    combine_edges_input_df.reset_index(drop=True, inplace=True)

    # G = nx.from_pandas_edgelist(combine_edges_input_df, 'From Bus', 'To Bus')
    # diG = nx.from_pandas_edgelist(combine_edges_input_df, 'From Bus', 'To Bus', create_using=nx.DiGraph())

    G = nx.Graph()
    diG = nx.DiGraph()

    buslist = [b.split('.')[0] for b in dss.Circuit.AllBusNames()]

    flag = dss.Lines.First()
    while flag > 0:
        frombus = dss.Lines.Bus1().split('.')[0]
        tobus = dss.Lines.Bus2().split('.')[0]
        # if a in list(G.node) and b in list(G.node):
        G.add_edge(frombus, tobus)
        diG.add_edge(frombus, tobus)
        if flag == 1:
            first_bus = frombus

        flag = dss.Lines.Next()

    # diG = nx.DiGraph(G)
    # print(diG.nodes())
    transformer_buses = []

    flag = dss.Transformers.First()
    while flag > 0:
        bus_array = dss.Properties.Value('buses')
        bus_array = list([b.split('.')[0].strip() for b in bus_array.split('[')[1].split(', ]')[0].split(',')])
        # print(bus_array)
        bus_array = [bus_array[0]] + list(np.unique(bus_array[1:]))

        frombus = bus_array[0]
        transformer_buses.append(frombus)

        for i in range(1, len(bus_array)):
            tobus = bus_array[i].split('.')[0]
            diG.add_edge(frombus, tobus)
            G.add_edge(frombus, tobus)
            # print('Xfmr_edge: ',frombus,tobus)

        flag = dss.Transformers.Next()

    buslist = dss.Circuit.AllBusNames()
    first_bus = buslist[0].split('.')[0]
    # print("Feeder head @ bus: ", first_bus)
    # print(buslist)
    for b in buslist:

        dss.Circuit.SetActiveBus(b)

        try:
            predecessors = list(diG.predecessors(b))
        except:
            predecessors = []
            G.add_node(b.split('.')[0], pos=(dss.Bus.X(), dss.Bus.Y()))
            diG.add_node(b.split('.')[0], pos=(dss.Bus.X(), dss.Bus.Y()))
            print(f"There is probably no power delivery element connecting Node {b}")

        if dss.Bus.Coorddefined():
            G.add_node(b.split('.')[0], pos=(dss.Bus.X(), dss.Bus.Y()))
            diG.add_node(b.split('.')[0], pos=(dss.Bus.X(), dss.Bus.Y()))

        elif len(predecessors) > 0:
            # print(list(diG.predecessors(b)))

            pred_b = [bus for bus in buslist if predecessors[0] == bus.split('.')[0]][0]
            dss.Circuit.SetActiveBus(pred_b)
            if dss.Bus.Coorddefined():
                G.add_node(b.split('.')[0], pos=(dss.Bus.X(), dss.Bus.Y()))
            else:
                # G.remove_node(b)

                print(b)

    pos = nx.get_node_attributes(G, 'pos')
    pv_node_list = get_pv_buses(dss)
    load_node_list = get_load_buses(dss)

    #    to_remove = []
    #    for node in G:
    #        if not node in pos.keys():
    #            to_remove.append(node)
    #            #G.remove_node(node)
    #            if node in node_list:
    #                node_list.remove(node)
    #    for node in to_remove:
    #        G.remove_node(node)
    if len(pos.keys()) == 0:
        print('check if your master file redirects bus coordinates'.upper())
    color_map = []
    node_size_map = []
    for node in G:

        if node in pv_node_list:
            color_map.append('green')
            node_size_map.append(100)
        # elif node in load_node_list:
        #     color_map.append('orange')
        #     node_size_map.append(25)
        elif node in transformer_buses and node != first_bus:
            color_map.append('purple')
            node_size_map.append(50)
        elif node == first_bus:
            color_map.append('black')
            node_size_map.append(100)
        elif node == find_node:  # Example for locating a known node
            print('Yay')
            color_map.append('blue')
            node_size_map.append(500)
        else:
            color_map.append('red')
            node_size_map.append(5)

    if render_plot:
        plt.figure()
        nx.draw(G, pos, node_size=node_size_map, alpha=0.7, node_color=color_map, edge_color='b')
        plt.figure()
        nx.draw(diG, pos, node_size=node_size_map, alpha=0.7, node_color=color_map, edge_color='b')

    # plt.show()

    return pos, G, diG, node_size_map, color_map


def plot_feeder_og(dss, render_plot=True, find_node=None):
    """
    This function plots the networkX representation of a given feeder
    and locates PV unites. Other items such us transformers, capacitors can
    be marked as well.
    """

    G = nx.Graph()
    diG = nx.DiGraph()

    color_map = []
    node_size_map = []

    # buslist = [b.split('.')[0] for b in dss.Circuit.AllBusNames()]

    flag = dss.Lines.First()
    while flag > 0:
        frombus = dss.Lines.Bus1().split('.')[0]
        tobus = dss.Lines.Bus2().split('.')[0]
        # if a in list(G.node) and b in list(G.node):
        G.add_edge(frombus, tobus)
        diG.add_edge(frombus, tobus)
        if flag == 1:
            first_bus = frombus

        flag = dss.Lines.Next()

    # diG = nx.DiGraph(G)
    # print(diG.nodes())
    G, diG, transformer_buses = add_xfmr_edges(dss, G, diG)

    buslist = dss.Circuit.AllBusNames()
    first_bus = buslist[0].split('.')[0]
    # print("Feeder head @ bus: ", first_bus)
    # print(buslist)
    for b in buslist:

        dss.Circuit.SetActiveBus(b)

        try:
            predecessors = list(diG.predecessors(b))
        except:
            predecessors = []
            G.add_node(b.split('.')[0], pos=(dss.Bus.X(), dss.Bus.Y()))
            diG.add_node(b.split('.')[0], pos=(dss.Bus.X(), dss.Bus.Y()))
            print(f"There is probably no power delivery element connecting Node {b}")

        if dss.Bus.Coorddefined():
            G.add_node(b.split('.')[0], pos=(dss.Bus.X(), dss.Bus.Y()))
            diG.add_node(b.split('.')[0], pos=(dss.Bus.X(), dss.Bus.Y()))

        elif len(predecessors) > 0:
            # print(list(diG.predecessors(b)))

            pred_b = [bus for bus in buslist if predecessors[0] == bus.split('.')[0]][0]
            dss.Circuit.SetActiveBus(pred_b)
            if dss.Bus.Coorddefined():
                G.add_node(b.split('.')[0], pos=(dss.Bus.X(), dss.Bus.Y()))
            else:
                # G.remove_node(b)

                print(b)

    pos = nx.get_node_attributes(G, 'pos')
    pv_node_list = get_pv_buses(dss)
    load_node_list = get_load_buses(dss)

    #    to_remove = []
    #    for node in G:
    #        if not node in pos.keys():
    #            to_remove.append(node)
    #            #G.remove_node(node)
    #            if node in node_list:
    #                node_list.remove(node)
    #    for node in to_remove:
    #        G.remove_node(node)
    if len(pos.keys()) == 0:
        print('check if your master file redirects bus coordinates'.upper())

    for node in G:

        if node in pv_node_list:
            color_map.append('green')
            node_size_map.append(100)
        # elif node in load_node_list:
        #     color_map.append('orange')
        #     node_size_map.append(25)
        elif node in transformer_buses and node != first_bus:
            color_map.append('purple')
            node_size_map.append(50)
        elif node == first_bus:
            color_map.append('black')
            node_size_map.append(100)
        elif node == find_node:  # Example for locating a known node
            print('Yay')
            color_map.append('blue')
            node_size_map.append(500)
        else:
            color_map.append('red')
            node_size_map.append(10)

    if render_plot:
        nx.draw(G, pos, node_size=node_size_map, alpha=0.7, node_color=color_map, edge_color='b')

    # plt.show()

    return pos, G, diG, node_size_map, color_map


def add_xfmr_edges(dss, G, diG):
    transformer_buses = []

    flag = dss.Transformers.First()
    while flag > 0:
        bus_array = dss.Properties.Value('buses')
        bus_array = list([b.split('.')[0].strip() for b in bus_array.split('[')[1].split(', ]')[0].split(',')])
        # print(bus_array)
        bus_array = [bus_array[0]] + list(np.unique(bus_array[1:]))

        frombus = bus_array[0]
        transformer_buses.append(frombus)

        for i in range(1, len(bus_array)):
            tobus = bus_array[i].split('.')[0]
            diG.add_edge(frombus, tobus)
            G.add_edge(frombus, tobus)
            # print('Xfmr_edge: ',frombus,tobus)

        flag = dss.Transformers.Next()

    return G, diG, transformer_buses


def get_pv_buses(dss):
    pv_buses = []
    flag = dss.PVsystems.First()
    while flag > 0:
        pv_buses.append(dss.Properties.Value('bus1').split('.')[0])
        flag = dss.PVsystems.Next()
    # print(pv_buses)
    return pv_buses


def get_load_buses(dss):
    load_buses = []
    flag = dss.Loads.First()
    while flag > 0:
        load_buses.append(dss.Properties.Value('bus1').split('.')[0])
        flag = dss.Loads.Next()
    # print(pv_buses)
    return load_buses


def check_connectivity(dss, find_node=None, render_plot=True):
    # load_feeder(master)
    pos, G, diG, node_size_map, color_map = plot_feeder(dss, find_node=find_node, render_plot=render_plot)
    connectivity_status = nx.is_connected(G)

    if not connectivity_status:
        unconnected_nodes = list(nx.isolates(G))
    else:
        unconnected_nodes = None

    return pos, G, diG, node_size_map, color_map, connectivity_status, unconnected_nodes