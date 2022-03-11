'''
Python imports
'''
import datetime
import pandas as pd
#import numpy as np


def _getToday():
    return datetime.datetime.today().strftime("%Y%m%d%H%M%S")


filename = "%s_%s.%s" % ("./output/CBA_result", _getToday(), "csv")


# load data frames
df = pd.read_csv('data/powers_table.csv')
dfcosts = pd.read_csv('data/costs.csv')


def sumproduct(filtro, columna):
    """ multiplies columns with the same name in the
    df (i.e., powers table) and dfcosts (i.e., cost table) data frames
    returns the sum of all the multiplied values
    """
    filterptable = df.loc[filtro, columna]
    # print(len(filterptable))
    # print(len(dfcosts[columna]))
    costtable = dfcosts[columna]
    series = costtable.mul(filterptable.to_numpy())
    return series


# shortening column names
COMM_LOAD = 'Loads__Powers__commercial (kWh)'
RES_LOAD = 'Loads__Powers__residential (kWh)'
PVCOMM_OUT = 'PVSystems__Powers__commercial (kWh)'
PVRES_OUT = 'PVSystems__Powers__residential (kWh)'
SUB_POWER = 'Circuits__TotalPower (kWh)'
SUB_LOSS = 'Circuits__Losses (kWh)'
PVCOMM_CURT = 'PVSystems__Curtailment__commercial (kWh)'
PVRES_CURT = 'PVSystems__Curtailment__residential (kWh)'
CR1 = 'Commercial power ($)'
CR2 = 'Residential power ($)'
CR3 = 'Commercial PV ($)'
CR4 = 'Residential PV ($)'
CR5 = 'Substation power ($)'
CR6 = 'Substation losses ($)'
CR7 = 'Commercial curtailment ($)'
CR8 = 'Residential curtailment ($)'

col_list = [COMM_LOAD, RES_LOAD, PVCOMM_OUT, PVRES_OUT,
            SUB_POWER, SUB_LOSS, PVCOMM_CURT, PVRES_CURT]
array = []

namesofcolumns = df['name'].unique()
print(namesofcolumns)

# this will eventually iterate through all runs
# colname = 'p1uhs21_1247__p1udt5257__-1__-1__-1'
# colscen = ['control_mode', 'pf1']
colscen = df['scenario'].unique()

for colname in namesofcolumns:
    for item in colscen:
        concatena = colname + '_' + item
        cost_list = [concatena]
        filt = (df['name'] == colname) & (df['scenario'] == item)

        if len(df.loc[filt]) == 8760:
            for item2 in col_list:
                resultado = sumproduct(filt, item2)
                cost_list.append(resultado.sum())
            array.append(cost_list)  # use a dataframe
        else:
            pass



resultdf = pd.DataFrame(
    array, columns=['Scenario', CR1, CR2, CR3, CR4, CR5, CR6, CR7, CR8])
print(resultdf)
resultdf.to_csv(filename, index=False)
