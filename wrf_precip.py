#wrf-python apply precip-prediction to wrf output

from netCDF4 import Dataset
from wrf import getvar, to_np, latlon_coords, get_cartopy, ll_to_xy, interplevel
import numpy as np
import matplotlib.pyplot as plt
import cartopy.feature as cfeature
import pandas as pd 
import lightgbm as lgb
import matplotlib.colors as mcolors
import cartopy.crs as ccrs

#bring in the data
ncfile = Dataset(".\\data\\wrfsample.nc")

#parse it to only be the region we are interested in (Upper Midwest in this case)
#this code specifically gives us the coordinates that we need to use to slice the file, while keeping it compliant with wrf-python's needs
sw_lat, sw_lon = 40.0, -97.0
ne_lat, ne_lon = 49.0, -82.0

#you cannot just cut the array by lat-lon coords necessarily, so use ll_to_xy to get nearest xy coords to need lat-lons
sw_xy = ll_to_xy(ncfile, sw_lat, sw_lon)
ne_xy = ll_to_xy(ncfile, ne_lat, ne_lon)

#convert to integers
x_start, x_end = int(sw_xy[0]), int(ne_xy[0])
y_start, y_end = int(sw_xy[1]), int(ne_xy[1])

#using the xy coordinates we obtained, slice the relevant variables
pressure = getvar(ncfile, 'p').isel(south_north=slice(y_start, y_end + 1), west_east=slice(x_start, x_end + 1))
temp_c = getvar(ncfile, 'tc').isel(south_north=slice(y_start, y_end + 1), west_east=slice(x_start, x_end + 1))
temp_d = getvar(ncfile, 'td').isel(south_north=slice(y_start, y_end + 1), west_east=slice(x_start, x_end + 1))
sfc_t = getvar(ncfile, 'T2').isel(south_north=slice(y_start, y_end + 1), west_east=slice(x_start, x_end + 1)) - 273.15
sfc_td = getvar(ncfile, 'td2').isel(south_north=slice(y_start, y_end + 1), west_east=slice(x_start, x_end + 1))

#extract the shape variables from wrf
n_lev, n_lat, n_lon = pressure.shape

#get these variables at 925 and 850 mb
#925
tc_925 = interplevel(temp_c, pressure, 925)
td_925 = interplevel(temp_d, pressure, 925)

#850
tc_850 = interplevel(temp_c, pressure, 850)
td_850 = interplevel(temp_d, pressure, 850)

#once we have these, we can get them into a form that precip_predict can use, apply it to every point in the data. Find efficient way to do this
#change each of these variables into 1d arrays that our ML model can use
data_dict = {
    'sfc_t':  to_np(sfc_t).ravel(),
    'sfc_td': to_np(sfc_td).ravel(),
    't925':   to_np(tc_925).ravel(),
    'td925':  to_np(td_925).ravel(),
    't850':   to_np(tc_850).ravel(),
    'td850':  to_np(td_850).ravel()
}

#turn it into a pandas DF
df_for_model = pd.DataFrame(data_dict)

#load the ml model and then make predictions with each
loaded_gbm = lgb.Booster(model_file='lightgbm_model_v1.txt')
probabilities = loaded_gbm.predict(df_for_model)

#reshape to work on map of Midwest
ny, nx = sfc_t.shape
pred_map = probabilities.reshape(ny, nx)

#put all these values into an array associated with lat-lon coordinates that can then be plotted
lats, lons = latlon_coords(sfc_td)
cart_proj = get_cartopy(sfc_td)

lon_min, lon_max = int(lats.min()), int(lons.max())

#plot them, heck yeah
fig = plt.figure(figsize=(10, 8))
ax = plt.axes(projection=cart_proj)

#binary color map
cmap = mcolors.ListedColormap(['green', 'blue'])
norm = mcolors.BoundaryNorm([0.0, 0.5, 1.0], cmap.N)

#plot stuffs
mesh = ax.pcolormesh(to_np(lons), to_np(lats), pred_map, transform=ccrs.PlateCarree(), cmap=cmap, norm=norm, zorder=1)

#plot map features
ax.add_feature(cfeature.STATES.with_scale('50m'), linewidth=0.8, edgecolor='black', zorder=2)
ax.add_feature(cfeature.COASTLINE.with_scale('50m'), zorder=2)
ax.add_feature(cfeature.LAKES, alpha=0.5, zorder=2)

#limit map extent, otherwise it plots the whole wide world
lon_min, lon_max = to_np(lons).min(), to_np(lons).max()
lat_min, lat_max = to_np(lats).min(), to_np(lats).max()
ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

#label and display
plt.title("Rain-Snow LightGBM Midwest Prediction")
plt.show() 

#recall, this model is NOT optimized for confidence, just getting it right. So 64% does not mean it is only 64% confident that its going to be snow

