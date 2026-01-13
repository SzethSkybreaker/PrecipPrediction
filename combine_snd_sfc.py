# File to combine cleaned sounding and surface obs into one big file
# Input is the output of read_integrated_sfcobs.py and read_sounding_obs.py
# Output is a file with the following columns. Note, values are comma separated
# date in UTC (YYYY-MM-DDHH:MM:SS), surface temp (C), surface dewpoint (C), 925 mb temp, 925 mb dewpoint, 850 mb temp, 850 mb dewpoint, precipitation type
# 
# Precipitation type is indicated with the values 0,1,2, where 0 indicates rain, 1 mixed precip, and 2 is frozen (snow, graupel, ice pellets, NOT hail)

import os
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

def better_combine(snd_path, sfc_path):
    #all the rows of the CSV which is to be written
    rows = []

    #read the sounding data into a Pandas dataframe, telling it to parse the 'date' column into a datetime object and then sort the values by date
    snd_df: pd.DataFrame = pd.read_csv(snd_path, dtype={'t925':float, 'td925':float, 't850':float, 'td850':float}, parse_dates=['date'])
    snd_df = snd_df.sort_values(by='date')
    #read in sfc obs. format is: row, datetime, temp, dew, precip type, similar to the sounding obs
    sfc_df: pd.DataFrame = pd.read_csv(sfc_path, dtype={'TMP[C]':float, 'DEWPOINT[C]':float, 'PRECIP_TYPE':int}, parse_dates=['DATE'])
    sfc_df = sfc_df[sfc_df['PRECIP_TYPE'] != 1]
    sfc_df.replace(to_replace={'PRECIP_TYPE':2}, value=1, inplace=True)
    sfc_df.rename(columns={'TMP[C]':'TMP', 'DEWPOINT[C]':'DEW'}, inplace=True)
    sfc_df = sfc_df.sort_values(by='DATE')

    #here's where the magic happens, we have the sounding and surface obs sorted by the dates in them
    #now we want to match surface obs to relevant sounding observations
    #we could check every single entry against every single other entry, but that takes a LOOOONNGGG time
    #instead, because these are sorted by date, when we've passed the date of the sounding in sfc_obs, then we move on as there will be no match beyond this
    start_j = 0
    for i in range(len(snd_df)):
        #iterate through each sounding, extracting the date for each
        snd_date = snd_df.iloc[i].date
        sounding = snd_df.iloc[i]
        sfc_obs_near = [] #this holds all the surface obs near in time 
        for j in range(start_j, len(sfc_df)):
            #iterate through each sfc ob, extract the date and the ob as a whole
            sfc_date = sfc_df.iloc[j].DATE
            obs = sfc_df.iloc[j]

            #check the difference between the sounding time and sfc ob time
            time_dif = abs(snd_date - sfc_date)
            if time_dif <= timedelta(hours=1):
                #if the difference is less than or equal to 1 hour, then we appened it to nearby sfc obs and update the start j
                sfc_obs_near.append([time_dif, obs.TMP, obs.DEW, obs.PRECIP_TYPE])
                start_j = j #we pick up at this point next time
                #break #think this break shouldn't be here. As we don't want to break on the first nearby ob
            
            #then we've passed all relevant obs and we should just move to the next sonde
            if time_dif >= timedelta(hours=2) and sfc_date > snd_date:
                start_j = j
                break


        #the logic on this next part is a touch complex so hang in there with me
        #essentially, we iterate through all nearby (within 1 hour) surface obs of the sounding
        #we are just checking for which is best, by finding the one that doesn't have missing obs and is closest
        #so if there is an ob on the hour, but it's missing a dewpoint, then we try and find an ob that is close but not missing the value
        precip_types = []
        nearest_temp = None
        nearest_dew = None
        temp_time = timedelta(hours=2) #initialize timedelta as 2 hours, greater than any of the sfcobs diffs should be 
        dew_time = timedelta(hours=2)
        for i in range(len(sfc_obs_near)):
            precip_types.append(sfc_obs_near[i][3])
            if sfc_obs_near[i][0] < temp_time and sfc_obs_near[i][1] < 500: #a value less than 500 indicates this is not a missing value 
                temp_time = sfc_obs_near[i][0] #NOTE: this is a timedelta, NOT a datetime value
                nearest_temp = sfc_obs_near[i][1]

            if sfc_obs_near[i][0] < dew_time and sfc_obs_near[i][2] < 500:
                dew_time = sfc_obs_near[i][0]
                nearest_dew = sfc_obs_near[i][2]

        if nearest_temp == None or nearest_dew == None:
            continue
            #we didn't find what we were looking for, move to the next sounding
        
        #however, if we did find multiple valid observations, then we need to check if there precip types are the same
        #if they are, then we have no issues. If they are not, then we indicate is mixed precip as this is a transition period
        precip_type = -1
        precip_types = set(precip_types)
        if len(precip_types) > 1:
            precip_type = 1
        else:
            precip_type = list(precip_types)[0]
        
        #write the string for the row that will be in the CSV and append it to the rows list
        row = snd_date.strftime("%Y-%m-%dT%H:00:00")+","+str(nearest_temp)+","+str(nearest_dew)+","+str(sounding.t925)+","+str(sounding.td925)+","+str(sounding.t850)+","+str(sounding.td850)+","+str(precip_type)
        rows.append(row)  

    return rows

def main():
    #path to data

    datapath = "."
    synoptic = "filtered_gb_synoptic_obs.csv"

    sfc_file = os.path.join(datapath, synoptic)

    datapath = ".\\ml_experiments"
    synoptic = "good_snd_obs.csv"
    snd_file = os.path.join(datapath, synoptic)

    all_rows = better_combine(snd_file, sfc_file)
    #open a file and write all the resulting rows to it
    with open("ultimate_dataset3.csv", 'w') as file:
         file.write("date,sfc_t,sfc_td,t925,td925,t850,td850,precip_type\n")
         for item in all_rows:
             file.write(item + '\n')
    # return 0

if __name__=="__main__":
    main()