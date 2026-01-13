#file to combine relevant data into one file from synoptic obs and soundings obs
import pandas as pd
import os 

#DATE tells date/time (1950-01-01T00:00:00), 
#columns AT1 through AT8 are the relevant ones. Can be none or 8 entries here. Could be snow and rain and freezing rain in last hour.
#  04 = Ice pellets, sleet, snow pellets or small hail
#  13 = Mist
#  14 = Drizzle
#  15 = Freezing drizzle
#  16 = Rain
#  17 = Freezing rain
#  18 = Snow, snow pellets, snow grains or ice crystals
#as such, we are interested in 04, 14, 15, 16, 17, and 18
#columsn AU1-AU9 also contain precip info
# 00 = No Precipitation
#  01 = Drizzle (DZ)
#  02 = Rain (RA)
#  03 = Snow (SN)
#  04 = Snow Grains (SG)
#  05 = Ice Crystals (IC)
#  06 = Ice Pellets (PL)
#  07 = Hail (GR)
#  08 = Small Hail and/or Snow Pellets (GS)
#  09 = Unknown Precipitation (UP)
#  99 = Missing
#
#AW1-AW4 also have valuable information if they are included. Far more detailed than the previous two

#Report type should not be SOD (summary of day)

#data processing rules:
# we will take reports of precip within 1 hour of the sounding obs as training data. 
# Could potentially go broader, but precip type can change so fast, I'm not comfortable beyond that. 

#function to be applied to the temp columns, as they contain multiple values, the first of which is the temperature in C
def process_temp(temp):
    values = temp.split(",")
    temperature = float(values[0])/10
    #convert to float
    return temperature

#function which extracts the precipitation type from a given synoptic obs row
def precip_type(row):
    mw_rain = ["20","21","23","25","80","81","82"] + [str(i) for i in range(50,68,1)]
    mw_mixed = ["23","26","68","69","83","84"]
    mw_frozen = ["22","85","86"] + [str(i) for i in range(70,80,1)] 

    #list of corresponding values for aw readings
    aw_rain = ["23","25","43","44","81","82","83","84"] + [str(i) for i in range(50,67,1)]
    aw_mixed = ["67","68"]
    aw_frozen = ["24","45","46","85","86","87"] + [str(i) for i in range(70,79,1)] 

    qc_bad_codes = ["3","7"]

    all_obs = [] #AWs and MWs

    #check auto obs for precip type, will be majority in later years
    AWs = [row["AW1"], row["AW2"], row["AW3"], row["AW4"]]
    for aw in AWs:
        aw = aw.split(",")
        if aw[0] != "":
            if aw[1] in qc_bad_codes: #if it is a bad code, then we append -1. We could just skip, but it could be a useful stat to know missing  obs
                all_obs.append(-1)
            else:
                if aw[0] in aw_rain:
                    all_obs.append(0)
                elif aw[0] in aw_mixed:
                    all_obs.append(1)
                elif aw[0] in aw_frozen:
                    all_obs.append(2)
                else:
                    all_obs.append(-1)
        else:
            continue
                
         
    MWs = [row["MW1"], row["MW2"], row["MW3"], row["MW4"], row["MW5"], row["MW6"]]

    #now we search through the manual obs for precip observation
    for aw in MWs:
        aw = aw.split(",")
        if aw[0] != "":
            if aw[1] in qc_bad_codes: 
                all_obs.append(-1)
            else:
                if aw[0] in mw_rain:
                    all_obs.append(0)
                elif aw[0] in mw_mixed:
                    all_obs.append(1)
                elif aw[0] in mw_frozen:
                    all_obs.append(2)
                else:
                    all_obs.append(-1)
        else:
            continue

    #precip_type being 0 is rain, 1 is mixed, and 2 is snow. -1 indicates erroneous data, based on QC
    set_precip = list(set(all_obs))
    #check  if there are multiple precip types and if so, determine what value to choose
    if len(set_precip) == 1:
        return str(set_precip[0])
    elif len(set_precip) == 0: #not sure how exactly this would happen, but added the line just in case
        return "-1"
    else:
        if -1 in set_precip:
            if len(set_precip) == 2:
                if set_precip[0] != -1:
                    return str(set_precip[0])
                else:
                    return str(set_precip[1])
            else:
                return "1"
        else:
            return "1"

def read_synoptic(filepath):
    syn_data = pd.read_csv(filepath, sep=',', header=0, dtype=str)

    #clean up the data and make it all strings

    #select only columns of interest and drop those without relevant info
    #also want: MW1-7 (manual reporting), AW1-4 (automatic current cond reporting)
    useful_data = syn_data[["DATE", "TMP", "DEW", "REPORT_TYPE", "AW1", "AW2", "AW3", "AW4", "MW1", "MW2", "MW3", "MW4", "MW5", "MW6"]]
    cleaned_df = useful_data.dropna(subset=['DATE', 'TMP', "DEW"])
    cleaned_df = cleaned_df[cleaned_df["REPORT_TYPE"] != "SOD"]
    cleaned_df = cleaned_df.dropna(subset=["AW1", "MW1"], how="all")
    
    cleaned_df = cleaned_df.fillna("")
    #ensure zero whitespace on front or end
    cleaned_df = cleaned_df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    cleaned_df["TMP_FLT"] = cleaned_df["TMP"].apply(process_temp)
    cleaned_df["DEW_FLT"] = cleaned_df["DEW"].apply(process_temp)
    cleaned_df["PRECIP_TYPE"] = cleaned_df.apply(precip_type, axis=1)

    #drop those with erroneous precip values
    cleaned_df = cleaned_df[cleaned_df["PRECIP_TYPE"] != "-1"]
    
    return cleaned_df

def main():
    #path to data
    datapath = ".\data"
    synoptic = "gb_synoptic.csv"
    syn_file = os.path.join(datapath, synoptic)
    
    #run processing functions
    syn_df: pd.DataFrame = read_synoptic(syn_file)

    simple_df = syn_df[["DATE","TMP_FLT","DEW_FLT", "PRECIP_TYPE"]]

    simple_df.rename(columns={"DATE":"DATE", "TMP_FLT":"TMP[C]","DEW_FLT":"DEWPOINT[C]","PRECIP_TYPE":"PRECIP_TYPE"}, inplace=True)

    #write output to a CSV file
    simple_df.to_csv("filtered_gb_synoptic_obs.csv")

    print(syn_df.info)

    return 0

if __name__=="__main__":
    main()
