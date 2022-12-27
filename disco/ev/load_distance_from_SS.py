# -*- coding: utf-8 -*-
"""
Created on Thu Sep 19 09:03:51 2019

@author: ppaudyal
"""

#import pandas as pd

def calc_dist(loadandbus_, nodeanddistance):
    
    nodeanddistance["Node_only"] = range(len(nodeanddistance))
    for i in range(len(nodeanddistance)):
        tmp = nodeanddistance["Node"][i] 
        nodeanddistance["Node_only"][i] = tmp[0:-2]
        
    nodeanddistance_ = nodeanddistance.drop_duplicates(subset = "Node_only", keep = "first") # if subset="Distance" then any two nodes could have same distance
    #print(nodeanddistance_.head(), "\n\n")
    #print(len(nodeanddistance_))
    
    nodeanddistance_.index = range(len(nodeanddistance_))
    # print(nodeanddistance_.head())

        
    loadandbus_["Distance"] = " "
    tmp_lst = (nodeanddistance_["Node_only"].tolist())
    # print(tmp_lst) # testing
    for i in range(len(loadandbus_)):
        if str(loadandbus_["Bus"][i]) in tmp_lst:
            tmp_indx = tmp_lst.index(str(loadandbus_["Bus"][i]))    #the index of that node in the list 
            dst = nodeanddistance_["Distance"][tmp_indx]
            loadandbus_["Distance"][i] = dst
        else:
            print("No ", loadandbus_["Bus"][i], "\n")
    
    loadandbus_.to_csv("Load_distance_from_SS.csv")  # save as csv if required
    return loadandbus_        