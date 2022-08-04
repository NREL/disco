"""
Created on May 20 2021 7:39 PM

@author: sabraham

This script restructures the SMART-DS dataset to create substation transformer level folders
"""

import pandas as pd
import opendssdirect as dss
import os
import numpy as np
import shutil
import sys
from transformer_restructuring_functions import *


def modify_feeder_master_dss(feeder_master_filepath, new_voltage_bases=''):
    """ modify feeder master file: only replace voltage bases line"""
    # saves a copy of original dss file
    original_master_dss = os.path.join(os.path.dirname(feeder_master_filepath), 'Original_Master.dss')
    save_original = False

    # read original master file
    if os.path.exists(original_master_dss):
        master_file_to_read = original_master_dss
        with open(original_master_dss, 'r') as fr:
            s_original = fr.readlines()
    else:
        master_file_to_read = feeder_master_filepath
        with open(feeder_master_filepath, 'r') as fr:
            s_original = fr.readlines()

        if save_original:
            with open(original_master_dss, "w") as fw:
                fw.writelines(s_original)  # write original file as Original_Master.dss

    # open text file - to modify
    with open(master_file_to_read, 'r') as infile:
        data = infile.read()

    final_list = []
    for ind, val in enumerate(data.split('\n')):
        # make changes to set voltagebases and append to final list
        if val.lower().startswith('set voltagebases'):
            val = new_voltage_bases
            final_list.append(val)
        # add any other existing line to final list
        else:
            final_list.append(val)
    # save the text file
    with open(feeder_master_filepath, 'w') as outfile:
        data = outfile.write('\n'.join(final_list))


def modify_sub_xfmr_master_dss(new_sb_master_filepath, xfmr_feeder_map=None, sb_xfmr='',
                               sb_xfmr_df='', new_sub_xfmr_voltage_bases='', add_new_voltage_bases_flag=False):
    """ modify substation xfmr master file"""
    # saves a copy of original dss file
    original_master_dss = os.path.join(os.path.dirname(new_sb_master_filepath), 'Original_Master.dss')
    save_original = False

    # read original master file
    if os.path.exists(original_master_dss):
        master_file_to_read = original_master_dss
        with open(original_master_dss, 'r') as fr:
            s_original = fr.readlines()
    else:
        master_file_to_read = new_sb_master_filepath
        with open(new_sb_master_filepath, 'r') as fr:
            s_original = fr.readlines()

        if save_original:
            with open(original_master_dss, "w") as fw:
                fw.writelines(s_original)  # write original file as Original_Master.dss

    # open text file - to modify
    with open(master_file_to_read, 'r') as infile:
        data = infile.read()

    final_list = []
    for ind, val in enumerate(data.split('\n')):
        # make changes to circuit definition
        if val.lower().startswith('new circuit'):
            name = val.split('.')[1].split(' ')[0]
            bus = val.split('bus1=')[1].split(' ')[0]
            val = val.replace(name, 'sub_xfmr_'+sb_xfmr)
            val = val.replace(bus, sb_xfmr_df.loc[sb_xfmr]['Primary bus'])
            final_list.append(val)

        # if string contains 'Redirect', check further and then decide if string is to be appended to final list
        elif 'Redirect' in val:
            # this condition says that if string contains subfolder, then it redirects to dss file in feeder
            if len(val.split(' ')[1].split('/')) > 1:
                feeder_name = val.split(' ')[1].split('/')[0]
                new_feeder_name = feeder_name.replace(feeder_name.split('--')[0], sb_xfmr)
                # if feeder is connected to substation xfmr, change name and append to final list
                if feeder_name in xfmr_feeder_map[sb_xfmr]:
                    val = val.replace(feeder_name, new_feeder_name)
                    final_list.append(val)
                # if feeder is not connected to substation xfmr, don't append to final list
                else:
                    continue
            # this condition says that string points to sub_xfmr dss file (lying in same folder), append to final list
            else:
                final_list.append(val)
        # make changes to set voltagebases and append to final list (if flag is true)
        elif val.lower().startswith('set voltagebases'):
            if add_new_voltage_bases_flag:
                val = new_sub_xfmr_voltage_bases
            final_list.append(val)
        # add any other existing line to final list
        else:
            final_list.append(val)
    # save the text file
    with open(new_sb_master_filepath, 'w') as outfile:
        data = outfile.write('\n'.join(final_list))


# modify substation xfmr master file
def modify_sub_xfmr_transformer_dss(new_sb_xfmr_filepath, sb_xfmr='', text='Transformer'):
    # saves a copy of original dss file
    original_dss = os.path.join(os.path.dirname(new_sb_xfmr_filepath), f'Original_{text}.dss')

    save_original = False

    # read original master file
    if os.path.exists(original_dss):
        master_file_to_read = original_dss
        with open(original_dss, 'r') as fr:
            s_original = fr.readlines()
    else:
        master_file_to_read = new_sb_xfmr_filepath
        with open(new_sb_xfmr_filepath, 'r') as fr:
            s_original = fr.readlines()

        if save_original:
            with open(original_dss, "w") as fw:
                fw.writelines(s_original)  # write original file as Original_{element_name}.dss

    # open text file - to modify
    with open(master_file_to_read, 'r') as infile:
        data = infile.read()

    final_list = []
    for ind, val in enumerate(data.split('\n')):
        # append transformer definition to final list by checking name
        if val.lower().startswith(f'new {text.lower()}'):
            name = val.split('.')[1].split(' ')[0]
            if sb_xfmr in name:
                final_list.append(val)
            else:
                continue
        # add any other existing line to final list
        else:
            final_list.append(val)
    # save the text file
    with open(new_sb_xfmr_filepath, 'w') as outfile:
        data = outfile.write('\n'.join(final_list))


# modify substation xfmr regulator file
def modify_sub_xfmr_regulator_dss(new_sb_regulator_filepath, sb_xfmr='', text='Regulator'):
    # saves a copy of original dss file
    original_dss = os.path.join(os.path.dirname(new_sb_regulator_filepath), f'Original_{text}.dss')

    save_original = False

    # read original master file
    if os.path.exists(original_dss):
        master_file_to_read = original_dss
        with open(original_dss, 'r') as fr:
            s_original = fr.readlines()
    else:
        master_file_to_read = new_sb_regulator_filepath
        with open(new_sb_regulator_filepath, 'r') as fr:
            s_original = fr.readlines()

        if save_original:
            with open(original_dss, "w") as fw:
                fw.writelines(s_original)  # write original file as Original_{element_name}.dss

    # open text file - to modify
    with open(master_file_to_read, 'r') as infile:
        data = infile.read()

    final_list = []
    for ind, val in enumerate(data.split('\n')):
        # append transformer definition to final list by checking name
        if val.lower().startswith(f'new regcontrol'):
            name = val.split('transformer=')[1].split(' ')[0]
            if sb_xfmr in name:
                final_list.append(val)
            else:
                continue
        # add any other existing line to final list
        else:
            final_list.append(val)
    # save the text file
    with open(new_sb_regulator_filepath, 'w') as outfile:
        data = outfile.write('\n'.join(final_list))


# modify substation xfmr lines file
def modify_sub_xfmr_line_dss(new_sb_line_filepath, sb_xfmr='', text='Lines', xfmr_line_map=None):
    # saves a copy of original dss file
    original_dss = os.path.join(os.path.dirname(new_sb_line_filepath), f'Original_{text}.dss')
    save_original = False

    # read original master file
    if os.path.exists(original_dss):
        master_file_to_read = original_dss
        with open(master_file_to_read, 'r') as fr:
            s_original = fr.readlines()
    else:
        master_file_to_read = new_sb_line_filepath
        with open(master_file_to_read, 'r') as fr:
            s_original = fr.readlines()

        if save_original:
            with open(original_dss, "w") as fw:
                fw.writelines(s_original)  # write original file as Original_{element_name}.dss

    # identify lines in other transformers (which can be removed safely from this transformer lines.dss file)
    lines_list = []
    for key, val in xfmr_line_map.items():
        lines_list = lines_list + val
    lines_to_be_excluded = list(set(lines_list) - set(xfmr_line_map[sb_xfmr]))

    # open text file - to modify
    with open(master_file_to_read, 'r') as infile:
        data = infile.read()

    final_list = []
    for ind, val in enumerate(data.split('\n')):
        # remove lines that are there in other transformers descendants
        if val.lower().startswith(f'new line'):
            name = val.split(' ')[1].split('.')[1]
            if name in lines_to_be_excluded:
                continue
            else:
                final_list.append(val)
        # add any other existing text to final list
        else:
            final_list.append(val)
    # save the text file
    with open(new_sb_line_filepath, 'w') as outfile:
        data = outfile.write('\n'.join(final_list))


def parse_master_file(master_filepath):
    master_dict = {}
    with open(master_filepath, 'r') as fr:
        mlines = fr.readlines()

    for line in mlines:
        if line.lower().startswith('new circuit'):
            name = line.split('.')[1].split(' ')[0]
            bus = line.split('bus1=')[1].split(' ')[0]
            basekV = float(line.split('basekV=')[1].split(' ')[0])
            pu = float(line.split('pu=')[1].split(' ')[0])
            break
    master_dict[name] = {'name': name, 'bus': bus, 'basekV': basekV, 'pu': pu}
    master_df = pd.DataFrame.from_dict(master_dict, orient='index')
    master_df.reset_index(inplace=True, drop=True)
    return master_df


def parse_transformer_file(file_path):
    tdico = {}
    with open(file_path, 'r') as fr:
        tlines = fr.readlines()

    for line in tlines:
        if line.lower().startswith('new'):
            tname = line.split('.')[1].split(' ')[0]
            try:
                tsecbus = line.split('wdg=2')[1].split('bus=')[1].split(' ')[0].split('.')[0]
                tprimbus = line.split('wdg=1')[1].split('bus=')[1].split(' ')[0].split('.')[0]
            except:
                tsecbus = line.split('buses=')[1].split(")")[0].split(',')[1]

            try:
                tkva = float(line.lower().split('kva=')[1].split(' ')[0])
            except:
                tkva = float(line.lower().split('kvas=')[1].split(")")[0].split(',')[1])

            tdico[tname] = {'name': tname, 'Primary bus': tprimbus, 'Secondary bus': tsecbus,
                              'kva': tkva}
            sb_xfmr_df = pd.DataFrame.from_dict(tdico, orient='index')
            sb_xfmr_df.reset_index(inplace=True, drop=True)

    return sb_xfmr_df


def parse_line_file(file_path):
    tdico = {}
    with open(file_path, 'r') as fr:
        tlines = fr.readlines()

    for line in tlines:
        if line.lower().startswith('new line'):
            tname = line.split('.')[1].split(' ')[0]
            bus1 = line.split('bus1=')[1].split('.')[0]
            bus2 = line.split('bus2=')[1].split('.')[0]

            tdico[tname] = {'name': tname, 'From Bus': bus1, 'To Bus': bus2}
            sb_line_df = pd.DataFrame.from_dict(tdico, orient='index')
            sb_line_df.reset_index(inplace=True, drop=True)

    return sb_line_df


def restructure_smart_ds(region='', ds='', path_to_regions='', new_path_to_regions='',
                         ds_path='', new_sub_xfmr_voltage_bases='', add_new_voltage_bases_flag=False):
    master_filename = 'Master.dss'
    xfmr_filename = 'Transformers.dss'
    regulator_filename = 'Regulators.dss'
    line_filename = 'Lines.dss'

    list_feeders = [x for x in os.listdir(ds_path) if os.path.isdir(os.path.join(ds_path, x))]
    remove_keywords_feeders = ['analysis', 'hc_pv_deployments', 'zip']
    # Remove words containing keywords from above list using list comprehension + all()
    list_feeders = [ele for ele in list_feeders if all(ch not in ele for ch in remove_keywords_feeders)]

    sb_master_filepath = os.path.join(ds_path, master_filename)
    sb_xfmr_filepath = os.path.join(ds_path, xfmr_filename)
    sb_line_filepath = os.path.join(ds_path, line_filename)
    sb_regulator_filepath = os.path.join(ds_path, regulator_filename)

    sb_xfmr_df = parse_transformer_file(sb_xfmr_filepath)
    sb_xfmr_df.set_index('name', inplace=True)
    sb_master_df = parse_master_file(sb_master_filepath)
    sb_bus = sb_master_df['bus'].values[0]
    sb_line_df = parse_line_file(sb_line_filepath)

    master_df = pd.DataFrame()
    print("-> Collecting master data for all feeders.")
    for feeder in list_feeders:
        print(feeder)
        master_filepath = os.path.join(ds_path, feeder, master_filename)
        temp_df = parse_master_file(master_filepath)
        temp_df['feeder'] = feeder
        master_df = master_df.append(temp_df)

    run_dir = os.getcwd()
    print("-> Begin mapping process.")
    dss.run_command("Clear")
    print("-->Redirecting substation master file:")
    # dss.run_command(f"Redirect {sb_master_filepath}")

    # do this instead of redirect master to ignore some lines that solve for the whole year
    os.chdir(os.path.dirname(sb_master_filepath))
    print(sb_master_filepath)
    with open(sb_master_filepath, 'r') as fr:
        tlines = fr.readlines()
    for line in tlines:
        if ('Solve'.lower() in line.lower()) or ('Export'.lower() in line.lower()) or ('Plot'.lower() in line.lower()):
            print(f"Skipping this line: {line}")
            continue
        else:
            r = dss.run_command(f"{line}")
            if r != '':
                raise ValueError(f"Error: {r}. \nSomething went wrong: check {line}")
    os.chdir(run_dir)
    """ LINES"""
    line_dict = {}
    dss.Circuit.SetActiveClass("Line")
    flag = dss.ActiveClass.First()
    print("-> Begin collecting Line data.")
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
    print("-> Collected Line data.")

    """
    # get list of all transformers
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

    print("-> Collected Transformer data.")
    transformer_df = pd.DataFrame.from_dict(transformer_dict, orient='index')
    transformer_df = transformer_df.reset_index().rename(columns={'index': 'Name'})
    transformer_df['Type'] = 'Transformer'
    transformer_buses = list(transformer_df['From Bus'].values)

    combined_df = transformer_df.append(line_df)
    combined_df.reset_index(drop=True, inplace=True)
    pos, G, diG, node_size_map, color_map, connectivity_status, unconnected_nodes = check_connectivity(dss, render_plot=False)
    print("-> Created networkx graph for entire substation.")
    # remove the edge between substation transformer primary and line that connects to primary bus
    # lines are incorrectly defined (from and to directions are inverted)

    sb_xfmr_desc_dict = {}

    for index, row in sb_xfmr_df.iterrows():
        sb_xfmr_primary = row['Primary bus']
        sb_xfmr_secondary = row['Secondary bus']
        sb_xfmr_name = index
        try:
            a = combined_df.loc[(combined_df['To Bus'] == sb_xfmr_primary) &
                                (combined_df['Type'] == 'Line')]
            assert(len(a) == 1)
        except:
            a = combined_df.loc[(combined_df['From Bus'] == sb_xfmr_primary) &
                                (combined_df['Type'] == 'Line')]
            assert(len(a) == 1)

        G.remove_edge(a['From Bus'].values[0], a['To Bus'].values[0])

        # find list of connected nodes of substation transformer secondary bus
        # we search for all successors of transformer secondary
        desc = list(nx.descendants(G, sb_xfmr_secondary))
        sb_xfmr_desc_dict[sb_xfmr_name] = desc

    print("-> Removed the edge between substation transformer primary and line that connects to primary bus.")

    # plt.figure()
    # nx.draw(G, pos, node_size=node_size_map, alpha=0.7, node_color=color_map, edge_color='b')

    # for every feeder in this substation, find which sub xfmr descendants list does the feeder bus lie in
    # that's the transformer which the feeder belongs to
    xfmr_feeder_map = {}
    # initializing xfmr_map dict with substation xfmr names
    for i in sb_xfmr_desc_dict.keys():
        xfmr_feeder_map[i] = []

    feeder_map = {}

    for index, row in master_df.iterrows():
        feeder_name = row['feeder']
        feeder_bus = row['bus']

        for sb_xfmr in sb_xfmr_desc_dict.keys():
            if feeder_bus in sb_xfmr_desc_dict[sb_xfmr]:
                xfmr_feeder_map[sb_xfmr].append(feeder_name)
                feeder_map[feeder_name] = {'bus': feeder_bus, 'sub_xfmr_name': sb_xfmr}

    xfmr_line_map = {}
    line_passed_flag = {}
    # initializing xfmr_map dict with substation xfmr names
    for i in sb_xfmr_desc_dict.keys():
        xfmr_line_map[i] = []
    for index, row in sb_line_df.iterrows():
        line_name = row['name']
        from_bus = row['From Bus']
        line_passed_flag[row['name']] = False

        for sb_xfmr in sb_xfmr_desc_dict.keys():
            if from_bus in sb_xfmr_desc_dict[sb_xfmr]:
                xfmr_line_map[sb_xfmr].append(line_name)
                # print("Wohoo")
                line_passed_flag[row['name']] = True

    print("-> Mapping Complete.")
    # mapping complete

    print("-> Begin making new folder structure.")
    # now onto making new folder structure and files
    os.makedirs(new_path_to_regions, exist_ok=True)
    sb_xfmr = list(sb_xfmr_desc_dict.keys())[0]
    for sb_xfmr in sb_xfmr_desc_dict.keys():
        # new_sb_xfmr_directory_path = os.path.join(new_path_to_regions, region, sb_xfmr)
        new_sb_xfmr_directory_path = os.path.join(new_path_to_regions, region, 'scenarios', 'base_timeseries',
                                                  'opendss', sb_xfmr)  # eagle path
        os.makedirs(new_sb_xfmr_directory_path, exist_ok=True)

        # copy feeders into corresponding substation transformer directory
        for feeder in xfmr_feeder_map[sb_xfmr]:
            new_prefix_name = feeder.replace(feeder.split('--')[0], sb_xfmr)
            old_feeder_location = os.path.join(ds_path, feeder)
            new_feeder_location = os.path.join(new_sb_xfmr_directory_path, new_prefix_name)
            os.path.exists(old_feeder_location)
            shutil.copytree(old_feeder_location, new_feeder_location)

            new_feeder_master_filepath = os.path.join(new_feeder_location, 'Master.dss')
            if add_new_voltage_bases_flag:
                # modify feeder level master file:to change voltage bases, since some feeders have missing voltage bases
                modify_feeder_master_dss(new_feeder_master_filepath, new_voltage_bases=new_sub_xfmr_voltage_bases)
        # files to be created and changed for substation xfmr: Master.dss, Transformers.dss, Regulators.dss, Lines.dss
        new_sb_line_filepath = os.path.join(new_sb_xfmr_directory_path, line_filename)
        new_sb_xfmr_filepath = os.path.join(new_sb_xfmr_directory_path, xfmr_filename)
        new_sb_regulator_filepath = os.path.join(new_sb_xfmr_directory_path, regulator_filename)
        new_sb_master_filepath = os.path.join(new_sb_xfmr_directory_path, master_filename)

        dss_file_list = [f for f in os.listdir(ds_path) if os.path.isfile(os.path.join(ds_path, f))]

        for file in dss_file_list:
            # print(file)
            shutil.copy(os.path.join(ds_path, file), os.path.join(new_sb_xfmr_directory_path, file))

        modify_sub_xfmr_transformer_dss(new_sb_xfmr_filepath, sb_xfmr=sb_xfmr, text='Transformer')
        modify_sub_xfmr_regulator_dss(new_sb_regulator_filepath, sb_xfmr=sb_xfmr, text='Regulator')
        modify_sub_xfmr_line_dss(new_sb_line_filepath, sb_xfmr=sb_xfmr, text='Lines', xfmr_line_map=xfmr_line_map)
        modify_sub_xfmr_master_dss(new_sb_master_filepath, xfmr_feeder_map=xfmr_feeder_map, sb_xfmr=sb_xfmr,
                                   sb_xfmr_df=sb_xfmr_df, new_sub_xfmr_voltage_bases=new_sub_xfmr_voltage_bases,
                                   add_new_voltage_bases_flag=add_new_voltage_bases_flag)
    print("-> Folder Restructuring Complete.")


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print(f"Usage: {sys.argv[0]} BASE_PATH ORIGINAL_DATASET NEW_DATASET LIST_OF_REGIONS")
        print(f"Example: {sys.argv[0]} /projects/distcosts3/SMART-DS/v1.0/2018 SFO SFO_xfmr A,B,C")
        sys.exit(1)

    base_path = sys.argv[1]
    original_dataset = sys.argv[2]
    new_dataset = sys.argv[3]
    regions_list = sys.argv[4]
    regions_list = regions_list.split(',')

    # flag to  determine whether format.toml file should be copied over from original location
    copy_format_toml_flag = True
    FORMAT_FILENAME = "format.toml"

    # flag to determine if the voltage bases in feeder and substation transformer master file should be replaced
    add_new_voltage_bases_flag = False
    new_sub_xfmr_voltage_bases = "Set Voltagebases=[69.0, 25.0, 14.4338, 12.47, 7.199560000000001, " \
                                 "0.48, 0.2080002494301389]"

    path_to_regions = os.path.join(base_path, original_dataset)
    new_path_to_regions = os.path.join(base_path, new_dataset)

    # # substation level
    # # local
    # path_to_regions = r"C:\Users\SABRAHAM\Desktop\NREL\current_projects\SETO_distcost\models\SFO\SFO"
    # new_path_to_regions = r"C:\Users\SABRAHAM\Desktop\NREL\current_projects\SETO_distcost\models\SFO\SFO_xfmr"
    # # on eagle
    # path_to_regions = r"/lustre/eaglefs/projects/distcosts3/SMART-DS/v1.0/2018/SFO"
    # new_path_to_regions = r"/lustre/eaglefs/projects/distcosts3/SMART-DS/v1.0/2018/SFO_xfmr"

    # ds = 'p1uhs2_1247'  # to test (in region P1U)

    # UNCOMMENT THIS OUT IF YOU WANT TO AUTOMATICALLY DETERMINE REGION NAMES
    # regions_list = [f for f in os.listdir(path_to_regions) if os.path.isdir(os.path.join(path_to_regions, f))]
    # remove_keywords = ['analysis', 'pv-profiles', 'raw-solar-profiles']
    # # Remove words containing keywords from above list using list comprehension + all()
    # regions_list = [ele for ele in regions_list if all(ch not in ele for ch in remove_keywords)]

    # COMPLETE LIST OF REGIONS IN SFO
    # complete_regions_list = ['P2U', 'P9U', 'P10U', 'P3U', 'P13U', 'P14U', 'P7U', 'P24U', 'P33U', 'P20U', 'P23U', 'P25U', 'P15U', 'P29U', 'P21U',
    #  'P17U', 'P1U', 'P2R', 'P8U', 'P31U', 'P18U', 'P32U', 'P19U', 'P6U', 'P5R', 'P26U', 'P1R', 'P4U', 'P4R', 'P22U',
    #  'P27U', 'P12U', 'P16U', 'P3R', 'P28U', 'P5U', 'P34U', 'P35U', 'P11U']

    for region in regions_list:
        print(f"\n\n********Region: {region}********")

        # on eagle, we also need to copy the profiles folder (which contains load profiles as csv files)
        # copy profiles over-this takes a while
        old_profiles_path = os.path.join(path_to_regions, region, 'profiles')
        new_profiles_path = os.path.join(new_path_to_regions, region, 'profiles')

        if os.path.exists(new_profiles_path):
            print("->Profiles directory exists. They have already been copied!")
        else:
            shutil.copytree(old_profiles_path, new_profiles_path)
            print("->Finished copying load profiles")

        # if original substation structure does not exist, then go to next region. Cause that is needed.
        if not os.path.exists(os.path.join(path_to_regions, region, 'scenarios', 'base_timeseries', 'opendss')):
            print("->Original structured DSS file directory does not exist. It has to exist. Please check!")
            print("->Skipping region, and moving to next!")
            continue

        # if the new restructured substation xfmr directory structure already exists, delete it.
        if os.path.exists(os.path.join(new_path_to_regions, region, 'scenarios', 'base_timeseries')):
            shutil.rmtree(os.path.join(new_path_to_regions, region, 'scenarios', 'base_timeseries'))
            print("->Deleted existing restructured substation transformer directory with OpenDSS files.")

        # copy format.toml if present in original dataset
        os.makedirs(os.path.join(new_path_to_regions, region, 'scenarios', 'base_timeseries', 'opendss'))
        if copy_format_toml_flag and os.path.exists(os.path.join(path_to_regions, region, 'scenarios', 'base_timeseries', 'opendss', FORMAT_FILENAME)):
            shutil.copyfile(os.path.join(path_to_regions, region, 'scenarios', 'base_timeseries', 'opendss', FORMAT_FILENAME),
                            os.path.join(new_path_to_regions, region, 'scenarios', 'base_timeseries', 'opendss', FORMAT_FILENAME))

        # path_to_ds = os.path.join(path_to_regions, region)
        path_to_ds = os.path.join(path_to_regions, region, 'scenarios', 'base_timeseries', 'opendss')  # eagle

        ds_list = [f for f in os.listdir(path_to_ds) if os.path.isdir(os.path.join(path_to_ds, f))]

        remove_keywords = ['subtransmission', 'aggregate', 'analysis', 'hc_pv_deployments', 'zip']
        # Remove words containing keywords from above list using list comprehension + all()
        ds_list = [ele for ele in ds_list if all(ch not in ele for ch in remove_keywords)]
        # ds_list = [ds]  # TODO test

        for ds in ds_list:
            print(f"\n***DS: {ds}")
            ds_path = os.path.join(path_to_ds, ds)
            try:
                restructure_smart_ds(region=region,
                                     new_path_to_regions=new_path_to_regions, ds_path=ds_path,
                                     add_new_voltage_bases_flag=add_new_voltage_bases_flag,
                                     new_sub_xfmr_voltage_bases=new_sub_xfmr_voltage_bases)
            except:
                print(f'Failed due to error: {sys.exc_info()[0]}')
                continue
