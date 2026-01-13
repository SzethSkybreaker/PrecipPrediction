from siphon.simplewebservice.wyoming import WyomingUpperAir
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
from time import sleep
import pandas as pd
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from urllib.error import HTTPError
import lightgbm as lgb

# General format
# request sounding data from various stations around the country for the most recent time
# once they are in data sounding get lat-lon, sfc, 925, and 850 params. Will only work for midwest stations
# run ML model on each sounding location to get prob of precip
# associate prob with a lat-lon location, create list of these
# plot each of these locations with a color on the map

#load our model
loaded_gbm = lgb.Booster(model_file='lightgbm_model_v1.txt')
sounding_ids = ["APX", "INL","MPX","DVN","ILX","ILN","DTX", "KSGF", "KGRB", "KTOP"]
COLOR_MAP = {'rain': 'green', 'snow': 'blue', 'mixed': 'purple'}

#gets nearest datetime
def nearest_sounding_time():
    utc_tz = ZoneInfo("Europe/London")
    now = datetime.now(utc_tz)
    hour_mod = now.hour // 14
    now_year = now.year
    now_month = now.month
    now_day = now.day
    use_hour = None
    if hour_mod == 1:
        #then this is 14z or later and we can use the 12z soundings
        use_hour = 12
    else:
        use_hour = 0

    return datetime(now_year, now_month, now_day, use_hour)

#takes a list of station ids, returns relevant info for each
def get_observed_sounding_data(obsdate, stations):
    all_soundings = []
    for station in stations:
        gotsound = True
        nosound = True
        while gotsound:
            try:
                df = WyomingUpperAir.request_data(obsdate, station)
                gotsound = False
                nosound = False
            except HTTPError:
                sleep(1)
            except ValueError as e:
                print(e)
                gotsound = False
                continue
        if nosound:
            continue
        lat, lon = df['latitude'].iloc[0], df['longitude'].iloc[0]
        pressures = df['pressure'].values
        max_pres = max(pressures)
        good_levels = False
        if 925 in pressures and 850 in pressures:
            good_levels = True
        if good_levels: 
            sfc_df = df.where(df['pressure'] == max_pres).dropna(subset=('temperature', 'dewpoint'), how='all').reset_index(drop=True).iloc[0]
            df925 = df.where(df['pressure'] == 925.0).dropna(subset=('temperature', 'dewpoint'), how='all').reset_index(drop=True).iloc[0]
            df850 = df.where(df['pressure'] == 850.0).dropna(subset=('temperature', 'dewpoint'), how='all').reset_index(drop=True).iloc[0]
            relevant_info = [lat, lon, sfc_df['temperature'], sfc_df['dewpoint'], df925['temperature'], df925['dewpoint'],df850['temperature'],df850['dewpoint']]
            all_soundings.append(relevant_info)
        else:
            continue

    #returns list of dataframes
    return all_soundings

#takes a list of obs and makes a prediction using lightgbm on them
def predict_precip(obs_list):
    all_predictions = [] #list of lists
    for ob in obs_list:
        lat = float(ob[0])
        lon = float(ob[1])
        sfc_t = float(ob[2])
        sfc_td = float(ob[3])
        t925 = float(ob[4])
        td925 = float(ob[5])
        t850 = float(ob[6])
        td850 = float(ob[7])
        predict_df = pd.DataFrame({'sfct':[sfc_t], 'sfctd':[sfc_td], 't925':[t925], 'td925':[td925], 't850':[t850], 'td850':[td850]})
        prediction = loaded_gbm.predict(predict_df)[0]
        print(ob)
        print(prediction)
        #convert to something useable
        if prediction > 0.6:
            prediction = 'snow'
        elif prediction < 0.4:
            prediction = 'rain'
        else:
            prediction = 'mixed'
        all_predictions.append([lat, lon, prediction])

    return all_predictions
        
def plot_predictions(pred_list, time):
    plt.figure(figsize=(10, 8))
    ax = plt.axes(projection=ccrs.PlateCarree())

    #features
    ax.add_feature(cfeature.LAND, facecolor='#f5f5f5')
    ax.add_feature(cfeature.OCEAN, facecolor='#cce6ff')
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_feature(cfeature.LAKES, alpha=0.5)
    
    #state lines
    states_provinces = cfeature.NaturalEarthFeature(
        category='cultural',
        name='admin_1_states_provinces_lines',
        scale='50m',
        facecolor='none'
    )
    ax.add_feature(states_provinces, edgecolor='gray')

    #set map extent, roughly the Midwest with: [-95, -80, 36, 50]
    ax.set_extent([-95, -80, 36, 50], crs=ccrs.PlateCarree())

    # plot each station
    for lat, lon, precip_type in pred_list:
        color = COLOR_MAP.get(precip_type, 'black')
        ax.plot(lon, lat, marker='o', color=color, markersize=8,
                transform=ccrs.PlateCarree(), linestyle='None')

    #legend
    handles = [
        mlines.Line2D([], [], color='green', marker='o', linestyle='None', label='Rain'),
        mlines.Line2D([], [], color='blue', marker='o', linestyle='None', label='Snow'),
        mlines.Line2D([], [], color='purple', marker='o', linestyle='None', label='Mixed')
    ]
    plt.legend(handles=handles, loc='upper right', title="Precipitation")

    plt.title(f"Sounding Analysis for {time.year}-{time.month}-{time.day} {time.hour} UTC")
    plt.show()

#just running all the functions
time = nearest_sounding_time()
#time = datetime(2025, 11, 18, 0)
all_stats = get_observed_sounding_data(time, sounding_ids)  
predictions = predict_precip(all_stats) 

plot_predictions(predictions, time)
