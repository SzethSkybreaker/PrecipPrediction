import pandas as pd 
import os
import math

#for soundings
#first sounding is from 1940, so precedes synoptic obs 
#pressure (3rd column), height (4th column), temperature (5th column), dew point depression (7th column), wind direction (8th), wind speed (9th)
# a string of #USM00072645 signals the beginning of a new sounding, followed by year, month, day, 99, hhmm

#given two heights, pressures, and temperatures, calculate temperature at a chosen pressure level between
def interp_level(h1, h2, p1, p2, t1, t2, plevel): #the final param here is the intermediate level you are trying to find (in hPa)
    
    #p1 should be greater than p2
    #as such, h2 is greater than h1
    #it is assumed that heights are in meters and temperatures are in Kelvin if over 100 and Celsius if under

    if t1 < 100: #this is Celsius
        t1 = t1 + 273.15
        t2 = t2 + 273.15


    #otherwise, its Kelvin and we're chilling. Or its F and what are we doing at that point? 
    g = 9.8 #m/s
    Rd = 287 #J/kg K

    Tv = (((h2 - h1)*g)/Rd)/math.log(p1/p2)


    del_h1 = ((Tv*Rd) / g)*math.log(p1/plevel) / (h2-h1) #distance to h1 (lower level)
    del_h2 = ((Tv*Rd) / g)*math.log(plevel/p2) / (h2-h1) #distance to h2 (upper level)
    print(del_h1)
    print(t1)
    print(del_h2)
    print(t2)
    print(Tv-273.15)

    #T_level = (t1*del_h1 + t2*del_h2 + Tv)/2 #we're doing a funky sort of averaging here that is weighted based on distance
    T_level = (t1*(math.log(-0.6322*del_h2+1)+1) + t2*(math.log(-0.6322*del_h2+1)+1) + Tv*min(del_h1, del_h2))/(1.5-min(del_h1,del_h2)) #VERY rough estimation, can definitely use fine tuning. Attempt at capturing missed inversions
    #WORK IN PROGRESS, not viable formula, will take lots of work
    return T_level - 273.15

#returns a list of lists of lists, where each list is a sounding and the sub lists are levels within the sounding. Values are not removed or processed.
#they are simply read. Processing is left for another function
def read_sounding(filepath):
    all_soundings = []
    with open(filepath, "r") as file:
        lines = file.readlines()
        sounding = []
        for line in lines:
            items = line.split()
            if "#USM00072645" in items: #this line here needs to be improved
                #this is the start of a new sounding
                #append sounding and then clear
                if len(sounding) != 0:
                    all_soundings.append(sounding)
                sounding = []
                sounding.append([items[1],items[2],items[3],items[4]]) #year, month, day, hour 
            else:
                #this is data row and we need to process it
                #I hate doing this, but because of how messy it is, we kind of have to
                row_num = line[:2] 
                seconds = line[2:8]
                pressure = line[8:16]
                height = line[16:22]
                temp = line[22:28]
                rh = line[28:33]
                dew = line[33:39]
                wd = line[39:45]
                ws = line[45:51]
                all_together = [row_num, seconds, pressure, height, temp, rh, dew, wd, ws]
                sounding.append(all_together)
#col seconds pres hght    temp  rh    dew    wd    ws
#10  8030   5000 20973B -552B  208   116    36    51
#31 -9999  -9999   218 -9999 -9999 -9999   315    60 
# pressure, temperature, geopotential height, relative humidity, dew point depression, wind direction and speed, and elapsed time since launch.

    return all_soundings 

# ln ew(T) = -6096.9385 T-1 + 21.2409642 - 2.711193×10-2 T + 1.673952×10-5 T2 + 2.433502 ln T  
#equation for calculating saturation vapor pressure when temp is less than 0 C:
# ln ei(T) = -6024.5282 T-1 + 29.32707 + 1.0613868×10-2 T - 1.3198825×10-5 T2 - 0.49382577 ln T 
#from there, you can get the actual vapor pressure by multiplying Es by RH
# once you have the vapor pressure:
# Td = - B (ln (e / A) )
# A = 2.53x10^11 Pa, B = 5.37 x 10^7 K 
#given a temperature and a relative humidity
#formula gets worse the further away  you get from standard atmospheric pressure, but is within 0.1 degrees
#this is because we assume latent heat of vaporization is constant, but it actually changes with pressure
#thus, the formula has a larger and larger error with decrease in pressure
def dewpoint_cal(temp, rh):
    t = temp
    if temp > 0: #above freezing
        Es = math.e**(math.log(611.2) + (17.62*t)/(243.12+t))   
    else:
        Es = math.e**(math.log(611.2) + (22.46*t)/(272.62+t))   

    e_real = (rh/100)*Es

    constA = 2.53*10**11 #Pa
    constB = 5.42*10**3 #K
    return (-1*constB)/(math.log(e_real/constA)) - 273.15
    


#filters out those soundings that don't have pressure values
#extracts all readings from 850 and below
#these obs are written into the following structure, where each row is a time and each column is a pressure level
# "pressure level, temperature, dewpoint, wind speed, wind direction"
def filter(soundings_list):
    to_write = [] #list of lists to write to the CSV file
    for sounding in soundings_list:
        relevant_info = ""
        datetime = sounding[0]
        datetime = datetime[0]+"-"+datetime[1]+"-"+datetime[2]+"T"+datetime[3]+":00:00"
        relevant_info = relevant_info + datetime
        for i in range(len(sounding)):
            if i == 0:
                i+=1
                #do nothing else
            else:
                level = sounding[i]
                try: 
                    pressure = level[2]
                    try:
                        pressure = int(pressure)/100
                    except:
                        pressure = int(pressure[:-1])/100
                    
                    height = level[3]
                    try:
                        height = int(height)
                    except:
                        height = int(height[:-1])
                    
                    tmp = level[4]
                    try:
                        tmp = int(tmp)/10
                    except:
                        tmp = int(tmp[:-1])/10

                    rh = level[5]
                    try:
                        rh = int(rh)/10
                    except:
                        rh = int(rh[:-1])/10

                    dew = level[6]
                    try:
                        dew = int(dew)/10
                    except:
                        dew = int(dew[:-1])/10
                    
                    
                    if pressure == -99.99 or pressure <= 600: #filter out obs above 600 mb
                        i+=1
                    else:
                        column = ","+str(pressure) +" "+ str(height)+" " + str(tmp)+" " + str(dew) + " " + str(rh)
                        relevant_info = relevant_info + column
                        i+=1
                except IndexError:
                    continue
        to_write.append(relevant_info)
    return to_write

#equation for calculating saturation vapor pressure when temperature is over 0 C:
# ln ew(T) = -6096.9385 T-1 + 21.2409642 - 2.711193×10-2 T + 1.673952×10-5 T2 + 2.433502 ln T  
#equation for calculating saturation vapor pressure when temp is less than 0 C:
# ln ei(T) = -6024.5282 T-1 + 29.32707 + 1.0613868×10-2 T - 1.3198825×10-5 T2 - 0.49382577 ln T 
#from there, you can get the actual vapor pressure by multiplying Es by RH
# once you have the vapor pressure:
# Td = - B (ln (e / A) )
# A = 2.53x10^11 Pa, B = 5.37 x 10^7 K 
#note that the original equations give their answers in Pa also

#final processing phase of the sounding file puts the file into the the following form:
# datetime 925_temp 925_dew 850_temp 850_dew
def final_processing(soundings):
    rows = [] #list of lists of rows
    for snd in soundings:
        ta = []
        
        #these values hold and find the closest values to each level
        found850 = False
        found950 = False

        b850 = [] #pressure, height, t, td, rh  
        a850 = []

        found925 = False
        found925 = False

        b925 = []
        a925 = []
        

        items = snd.split(",")
        for i in range(len(items)):
            if i == 0:
                ta.append(items[i])
            else: #this is a pressure level
                level = items[i].split() #splits based on white space
                pres = level[0]
                hght = level[1]
                tmp = level[2]
                dew = level[3]
                rh = level[4]
                
        
        if len(ta) == 1:
            continue
        


        
    return 0

#values are given in: pres, hght, tmp, dew, rh
#most basic processing function. Does no calculations or gap filling. Only takes those soundings where values aren't missing
def basic_final(soundings):
    rows = []
    for snd in soundings:
        items = snd.split(",")
        l850 = [] #tmp, dew
        min8diff = 9999
        l925 = [] #tmp, dew
        min9diff = 9999
        date = []
        for i in range(len(items)):
            if i == 0:
                date = items[0]
            else: #this is a pressure level
                level = items[i].split() #splits based on white space
                pres = float(level[0])
                hght = float(level[1])
                tmp = float(level[2])
                dew = float(level[3])
                rh = float(level[4])

                diff_850 = abs(pres - 850)
                diff_925 = abs(pres - 925)

                if diff_850 < 20 : #25 mb difference:
                    if tmp > -200:
                        if dew > -200:
                            if not l850 or diff_850 < min8diff:
                                #then we have a good dew point and this is closer to 850 than previous columns
                                l850 = [tmp, tmp-dew] #we add temperature to dew because this is given in dewpoint depression
                                min8diff = diff_850
                        elif rh > -10: #then we don't have dewpoint, but we can calculate it
                            if not l850 or diff_850 < min8diff:
                                l850 = [tmp, dewpoint_cal(tmp, rh)]
                                min8diff = diff_850


                if diff_925 < 20 : #25 mb difference:
                    if tmp > -200:
                        if dew > -200:
                            if not l925 or diff_925 < min9diff:
                                #then we have a good dew point and this is closer to 850 than previous columns
                                l925 = [tmp, tmp-dew]
                                min9diff = diff_925
                        elif rh > -10: #then we don't have dewpoint, but we can calculate it
                            if not l925 or diff_925 < min9diff:
                                l925 = [tmp, dewpoint_cal(tmp, rh)]
                                min9diff = diff_925
        if l850 and l925:
            to_add = date+","+str(round(l925[0],1))+","+str(round(l925[1],1))+","+str(round(l850[0],1))+","+str(round(l850[1],1))
            rows.append(to_add)
    return rows

def main():

    print(interp_level(310, 1370, 966.2, 850, -1, 7.7, 925))
    quit()

    datapath = ".\data"
    soundings = "USM00072645-data.txt"
    snd_file = os.path.join(datapath, soundings)

    all_soundings = read_sounding(snd_file)
    contents = filter(all_soundings)
    
    filt_contents = basic_final(contents)

    with open("good_snd_obs.csv", 'w') as file:
        file.write("date,t925,td925,t850,td850\n")
        for item in filt_contents:
            file.write(item + '\n')
    return 0

if __name__=="__main__":
    main()