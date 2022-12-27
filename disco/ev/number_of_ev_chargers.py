# -*- coding: utf-8 -*-
"""
Created on Wed Sep 18 16:20:21 2019

@author: ppaudyal
"""
# this function counts the number of EVs each node can support; 
# first number of xFC (350 kW), then number of level-2 charging (7.2 kW), and then number of level-1 charging (3.3 kW)

import pandas as pd

def levels_of_charger(output_file):
    load_name = []
    bus_name = []
    xfc = []
    lvl2 = []
    lvl1 = []
    for i in range(len(output_file)):
        load_ =  output_file['Load'][i]
        bus_ = output_file['Bus'][i]
        tmp_data = output_file['Maximum_kW'][i]-output_file['Initial_kW'][i]
        
        if tmp_data >= 350: #  
            num3 = tmp_data/350
            no_of_xfc = int(num3)
            
            tmp_diff = tmp_data - no_of_xfc*350
            if tmp_diff >= 7.2:
                #then count number of lvl-2
                n2 = tmp_diff/7.2
                no_of_lvl2 = int(n2)
                
                tmp_d = tmp_diff - no_of_lvl2*7.2 
                if tmp_d >= 3.3: 
                    #then number of lvl-1
                    n1 = tmp_d/3.3
                    no_of_lvl1 = int(n1)
                else:
                    no_of_lvl1 = 0
                
                    
            elif tmp_diff>= 3.3 and tmp_diff < 7.2: #then number of lvl-1 
                no_of_lvl2 = 0
                n1 = tmp_d/3.3
                no_of_lvl1 = int(n1)
            else:
                no_of_lvl2 = 0
                no_of_lvl1 = 0
            
        elif tmp_data >= 7.2 and tmp_data < 350 : # if less than 350 more than 7.2 then how many 7.2
            no_of_xfc = 0
            
            n2 = tmp_data/7.2
            no_of_lvl2 = int(n2)
            
            tmp_d = tmp_data - no_of_lvl2*7.2 
            if tmp_d >= 3.3:
                    #then number of lvl-1
                    n1 = tmp_d/3.3
                    no_of_lvl1 = int(n1)
            else:
                no_of_lvl1 = 0
    
        elif tmp_data >= 3.3 and tmp_data < 7.2 : ### # if less than 7.2 more than 3.3
            no_of_xfc = 0
            no_of_lvl2 = 0
            print(tmp_data)
            
            n1 = tmp_data/3.3
            no_of_lvl1 = int(n1)
    
        else:
            no_of_xfc = 0
            no_of_lvl2 = 0
            no_of_lvl1 = 0
            
        load_name.append(load_)
        bus_name.append(bus_)
        xfc.append(no_of_xfc)
        lvl2.append(no_of_lvl2)
        lvl1.append(no_of_lvl1)
        
    df = pd.DataFrame()
    df["load"] = load_name
    df["bus"] = bus_name
    df["no. of level3"] = xfc
    df["no. of level2"] = lvl2
    df["no. of level1"] = lvl1

    return df
        
        