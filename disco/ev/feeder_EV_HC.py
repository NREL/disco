# -*- coding: utf-8 -*-
"""
Created on Wed Sep 25 07:53:52 2019

@author: ppaudyal
"""

# -*- coding: utf-8 -*-
"""
Created on Wed Sep 18 14:32:29 2019

@author: ppaudyal
"""


#this code calculates the hosting capcity (checks voltage and thermal violation limits) for a given feeder
# every feeder model should have a 'Master.dss' as main dss file
#

import os
import pandas as pd
import numpy as np
import math 
import opendssdirect as dss

import load_distance_from_SS
import plot_hosting_capacity
import number_of_ev_chargers


# variable quantities
feeder_folder =  '477NHS'   #'BaseCaseWRR074'   #'BaseaseALD095'
low_lmt_0 = 0.950    # lower voltage limit
high_lmt_0 = 1.050   # upper voltage limit
low_lmt_1 = 0.975    # lower voltage limit
high_lmt_1 = 1.05   # upper voltage limit
low_lmt_2 = 0.985    # lower voltage limit
high_lmt_2 = 1.05   # upper voltage limit
v_limit = [[low_lmt_0, high_lmt_0], [low_lmt_1, high_lmt_1], [low_lmt_2, high_lmt_2]]
step_v = 10
step_thermal = 5

extra_percent = [2]#, 25]  # in case, this considers extra % for already overloaded elements
extra_limit = [100]#, 120]  #120, if we want to consider overload condition when %Normal>= 120 or any other %

master_dssfile = 'Master.dss'

# **************** System Information *****************
MainDir = os.getcwd()
FeederDir = os.path.join(MainDir, feeder_folder)
MasterFile = os.path.join(FeederDir,master_dssfile)
dss.run_command('clear')
dss.run_command('Compile '+ MasterFile)
dss.run_command('solve')
circuit = dss.Circuit
ckt_name = circuit.Name()
print('\n*** Circuit name:',ckt_name,'***\n from ', feeder_folder, ' folder\n')

AllNodeNames = circuit.YNodeOrder()
pd.DataFrame(AllNodeNames).to_csv('Allnodenames.csv')
#print(type(AllNodeNames))

# --------- Voltage Base kV Information -----
node_number = len(AllNodeNames)
Vbase_allnode = [0] * node_number
ii = 0
for node in AllNodeNames:
    circuit.SetActiveBus(node)
    Vbase_allnode[ii] = dss.Bus.kVBase() * 1000
    ii = ii + 1

# --------- Capacitor Information ----------
capNames = dss.Capacitors.AllNames()
hCapNames = [None] * len(capNames)
for i, n in enumerate(capNames):
    hCapNames[i] = str(n)
hCapNames = str(hCapNames)[1:-1]

# --------- Regulator Information ----------
regNames = dss.RegControls.AllNames()
hRegNames = [None] * len(regNames)
for i, n in enumerate(regNames):
    hRegNames[i] = str(n)
hRegNames = str(hRegNames)[1:-1]

dss.run_command('solve mode=snap')
#dss.run_command('export voltages') 
v = np.array(dss.Circuit.AllBusMagPu())


dss.utils.lines_to_dataframe()

volt_violation = np.any(v>high_lmt_0) or np.any(v<low_lmt_0)
print("Initial condition voltage violation: ", volt_violation) 

Bus_Distance = []
for node in AllNodeNames:
    circuit.SetActiveBus(node)
    # print('node', node, 'bus_distance', dss.Bus.Distance()) # testing
    Bus_Distance.append(dss.Bus.Distance())
np.savetxt("node_distance_"  + str(feeder_folder) + ".csv", Bus_Distance)

# --------- Load Information ----------
def get_loads(dss, circuit, loadshape_flag, loadshape_folder):
    data = []
    load_flag = dss.Loads.First()
    total_load = 0

    while load_flag:
        load = dss.Loads
        datum = {
            "name": load.Name(),
            "kV": load.kV(),
            "kW": load.kW(),
            "PF": load.PF(),
            "Delta_conn": load.IsDelta()
        }

        cktElement = dss.CktElement
        bus = cktElement.BusNames()[0].split(".")
        datum["kVar"] = float(datum["kW"]) / float(datum["PF"]) * math.sqrt(1 - float(datum["PF"]) * float(datum["PF"]))
        datum["bus1"] = bus[0]
        datum["numPhases"] = len(bus[1:])
        datum["phases"] = bus[1:]
        if not datum["numPhases"]:
            datum["numPhases"] = 3
            datum["phases"] = ['1', '2', '3']
        datum["voltageMag"] = cktElement.VoltagesMagAng()[0]
        datum["voltageAng"] = cktElement.VoltagesMagAng()[1]
        datum["power"] = dss.CktElement.Powers()[0:2]

        data.append(datum)
        load_flag = dss.Loads.Next()
        total_load += datum["kW"]

    return [data, total_load]


############################################## for voltage violation capacity ######################################
def node_V_capacity_check(which_load, low_lmt, high_lmt):
    initial_kW = which_load['kW']
    #print(initial_kW)  #just for testing
    add_kW = step_v #10
    tmp_kW = initial_kW
    volt_violation = False
    v=None

    while volt_violation==False:
    # while the voltages are within limits keep on increasing 
        new_kW = tmp_kW + add_kW    # increase the load by 10 kW each time
        dss.run_command('edit Load.' + str(which_load["name"]) + ' kW=' + str(new_kW))
        dss.run_command('solve mode = snap')
        v = np.array(dss.Circuit.AllBusMagPu())
        volt_violation = np.any(v>high_lmt) or np.any(v<low_lmt)
      #  print(volt_violation)  # for initial testing
        if volt_violation==True:
            #print(volt_violation)  # for initial testing
            vmax = np.max(v)
            vmin = np.min(v)
            cap_limit = new_kW
            dss.run_command('edit Load.' + str(which_load["name"]) + ' kW=' + str(initial_kW))
            dss.run_command('Compile '+ MasterFile)
            dss.run_command('solve mode = snap')
        else:
            tmp_kW = new_kW 

    return[cap_limit, vmax, vmin]
   
   
################################# for thermal overload capapcity #######################################################    
dss.run_command('solve mode = snap')
dss.run_command("export Overloads")

#rename this overload csv file 
src = circuit.Name() + "_EXP_OVERLOADS.CSV"
dst = feeder_folder + "_overloads.csv"
if os.path.exists(dst):
    os.remove(dst)
os.rename(src, dst)

#read this overload file and record the ' %Normal' for each line in this file
overload_df = pd.read_csv(dst)
#len(overload_df)
if(len(overload_df)==0):
    print("No thermal violation initially \n")
else:
    print("Thermal violation exists initially \n")
    print(overload_df.head())
   

elements = [[], []]
amps = [[], []]
new_threshold = [[], []]
for j in range(len(extra_percent)):
   
    for i in range(len(overload_df)):
        overload_df['Element'] =  overload_df['Element'].str.strip() # removing the extra spaces at the end (if any)
        element = overload_df['Element'][i] 
        amp = overload_df[' %Normal'][i]
        element_new_limit = amp + extra_percent[j]
        elements[j].append(str(element))
        amps[j].append(amp)
        new_threshold[j].append(element_new_limit)
       
print('new_threshold', new_threshold) # testing

def thermal_overload_check(which_load, th_limit, case):
    initial_kW = which_load['kW']
    #print(initial_kW)
    add_kW = step_thermal #5
    tmp_kW = initial_kW
    thermal_violation = False
 
    while thermal_violation==False:
    # while the elements loadings are within limits keep on increasing 
        new_kW = tmp_kW + add_kW    # increase the load by 5 kW each time
        dss.run_command('edit Load.' + str(which_load["name"]) + ' kW=' + str(new_kW))
        dss.run_command('solve mode = snap')
        dss.run_command("export Overloads")
        report = pd.read_csv(str(ckt_name) + "_EXP_OVERLOADS.CSV") 
        report['Element'] = report['Element'].str.strip()
   
        if(len(report)==0): # if no any overload element
            thermal_violation = False
           
        elif report['Element'].isin(elements[case]).any():
            for i in range(len(report)):
                if report['Element'][i] in elements[case]:
                    indx_ = elements[case].index(report['Element'][i])  #find the index of
                    if report[' %Normal'][i]>=new_threshold[case][indx_]:
                        thermal_violation = True #just exit here (get out of for loop)
                        #print(i)
                        break
                    else:
                        thermal_violation = False
                else:
                    #check the percentage normal if greater than specified % then only violation
                    if report[' %Normal'][i]>= th_limit:
                        thermal_violation = True 
                        break
                    else:
                        thermal_violation = False 
                               
        else:
            #check the percentage normal if greater than specified % then only violation
            for i in range(len(report)):
                if report[' %Normal'][i]>= th_limit:
                    thermal_violation = True 
                    break
                else:
                    thermal_violation = False            
       

        #print(thermal_violation)  # for initial testing
        if thermal_violation==True:
            #print(thermal_violation)  # for initial testing
            dss.run_command("export Capacity")
            dss.run_command("export Currents")
            cap_limit = new_kW
            dss.run_command('edit Load.' + str(which_load["name"]) + ' kW=' + str(initial_kW))
            dss.run_command('Compile '+ MasterFile)
            dss.run_command('solve mode = snap')
        else:
            tmp_kW = new_kW 

    return[cap_limit]   
   
#########################################################################################################################    
# get the load data    
[Load,totalkW] = get_loads(dss,circuit,0,'') 

# calculate the hosting capacity based on voltage constraints
v_output_df = []
for j in range(len(v_limit)):
    lmt1 = v_limit[j][0]
    lmt2 = v_limit[j][1]
    v_lst = []
    v_output_list = []
    v_threshold = []
    v_allow_limit = []
    v_names = []
    v_bus_name = []
    v_default_load = []
    v_maxv = []
    v_minv = []
    for i in range(len(Load)):
        v_node_cap = node_V_capacity_check(Load[i], lmt1, lmt2) # v_node_cap is a list
        v_allowable_load = v_node_cap[0] - step_v  #10 # v_node_cap[0] is a float
        v_threshold.append(v_node_cap[0])
        v_allow_limit.append(v_allowable_load)
        v_names.append(Load[i]["name"])
        v_bus_name.append(Load[i]["bus1"])
        v_default_load.append(Load[i]["kW"])
        v_maxv.append(v_node_cap[1]) 
        v_minv.append(v_node_cap[2])
    
    v_lst = [v_names, v_bus_name, v_default_load, v_threshold, v_allow_limit, v_maxv, v_minv]  
    v_output_list = list(map(list, zip(*v_lst)))   
    #v_output_df[0] = pd.DataFrame(v_output_list, columns = ['Load' , 'Bus', 'Initial_kW', 'Volt_Violation', 'Maximum_kW', 'Max_voltage', 'Min_voltage'])
    v_output_df.append(pd.DataFrame(v_output_list, columns = ['Load' , 'Bus', 'Initial_kW', 'Volt_Violation', 'Maximum_kW', 'Max_voltage', 'Min_voltage']))
    
    v_output_df[j].to_csv("Hosting_capacity_test_" + str(feeder_folder) + "_" + str(lmt1) + ".csv")

# calculate the hosting capacity based on thermal ratings constraint
th_threshold = [[], []]
th_allow_limit = [[], []]
th_names = [[], []]
th_bus_name = [[], []]
th_default_load = [[], []]

th_output_df = []
for i in range(len(extra_limit)):
    
    th_lst = []
    for j in range(len(Load)):
        th_node_cap = thermal_overload_check(Load[j], extra_limit[i], i) # th_node_cap is a list
        th_allowable_load = th_node_cap[0] - step_thermal  #5 # th_node_cap[0] is a float  # reduce the value of add_kW
        th_threshold[i].append(th_node_cap[0])
        th_allow_limit[i].append(th_allowable_load)
        th_names[i].append(Load[j]["name"])
        th_bus_name[i].append(Load[j]["bus1"])
        th_default_load[i].append(Load[j]["kW"])
    
    th_lst = [th_names[i], th_bus_name[i], th_default_load[i], th_threshold[i], th_allow_limit[i]]  
    th_output_list = list(map(list, zip(*th_lst)))   
    th_output_df.append(pd.DataFrame(th_output_list, columns = ['Load' , 'Bus', 'Initial_kW', 'Thermal_Violation', 'Maximum_kW']))
    
    th_output_df[i].to_csv("Thermal_capacity_test_"  + str(feeder_folder)  + "_" + str(extra_limit[i]) + ".csv")   
    

############################################## for plotting results ####################################################

load_bus = pd.DataFrame()
load_bus["Load"] = th_output_df[0]["Load"] #
load_bus["Bus"] = th_output_df[0]["Bus"]        
node_distance = pd.DataFrame()
node_distance["Node"] = AllNodeNames
node_distance["Distance"] = Bus_Distance    

dist_file = load_distance_from_SS.calc_dist(load_bus, node_distance)



dist_file["Initial_MW"] = th_output_df[0]["Initial_kW"]/1000
dist_file["Volt_Violation_0.95"] = v_output_df[0]["Volt_Violation"]/1000
dist_file["Volt_Violation_0.975"] = v_output_df[1]["Volt_Violation"]/1000
dist_file["Volt_Violation_0.985"] = v_output_df[2]["Volt_Violation"]/1000

dist_file["Thermal_Violation_100"] = th_output_df[0]["Thermal_Violation"]/1000
#dist_file["Thermal_Violation_120"] = th_output_df[1]["Thermal_Violation"]/1000

plot_df = dist_file.sort_values(by=['Distance'])

#plot voltage violation scenarios
plot_hosting_capacity.plot_capacity_V(plot_df, 'Initial_MW', 'Volt_Violation_0.95', 'Volt_Violation_0.975', 'Volt_Violation_0.985', feeder_folder)

#plot thermal violation
plot_hosting_capacity.plot_capacity_thermal_1(plot_df, 'Initial_MW', 'Thermal_Violation_100', feeder_folder, 100)
#plot_hosting_capacity.plot_capacity_thermal_2(plot_df, 'Initial_MW', 'Thermal_Violation_100', 'Thermal_Violation_120', feeder_folder)



####################### Assuming the hosting capacity is limited by thermal loading #####################################

## Difference of initial load and maximum hosting capacity (assuming always thermal limit occurs first) ##

for i in range(len(extra_limit)):
    diff = th_output_df[i]['Thermal_Violation'] - th_output_df[i]['Initial_kW']
    new_df = pd.DataFrame()
    
    new_df['Load'] = th_output_df[i]['Load']
    new_df['Bus'] = th_output_df[i]['Bus']
    new_df['Initial_kW'] = th_output_df[i]['Initial_kW']
    new_df['Hosting_capacity(kW)'] = diff # additional load it can support

    new_df.to_csv(str(feeder_folder) + "_Additional_HostingCapacity_" + str(extra_limit[i]) + ".csv", index=False)


    ## find number of ev chargers for each node ##
    
    chargers_3_2_1 = number_of_ev_chargers.levels_of_charger(th_output_df[i])
    chargers_3_2_1.to_csv(str(feeder_folder) + "_Loadwithlevel3_2_1_" + str(extra_limit[i]) + ".csv")

