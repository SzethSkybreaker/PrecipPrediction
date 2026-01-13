On Versions
- most of the scripts in this repo were written with Python 3.13.7, and the associated packages compatible with this version
	These include numpy, scipy, LightGBM, pandas, and matplotlib
- However, wrf_precip.py must be run in Python 3.10, as it uses wrf-python, which has not been updated to run with newer versions
	of Python. This is a small inconvenience and only affects the visualization, not the data processing scripts

The data folder contains synoptic obs and soundings from Green Bay, WI. Additionally, wrfsample.nc is just wrf output as a netCDF file, 
	which wrf_precip.py can be run on as proof of concept. However, given the date and time, it will predict all rain as precipitation type.

for the data reading scripts, you specify the input and output file names/paths within the script itself

read_integrated_sfcobs.py: takes synoptic obs from https://www.ncei.noaa.gov/access/search/data-search/global-hourly which gives access
	to hourly surface obs globally. The output is a CSV file with date/time, temperature, dewpoint, and precip type as columns.

read_sounding_obs.py: takes aggregated sounding obs from the Integrated Global Radiosonde Archive 
	(https://www.ncei.noaa.gov/products/weather-balloon/integrated-global-radiosonde-archive) 
	Outputs a csv where each row is a sounding. Columns are date/time followed by pressure/height/temp (C)/dewpoint (C)
	Dewpoint is calculated from RH in older soundings

combine_snd_sfc.py: takes the output of the sfc and sounding obs processors and combines them into one big file for use by lightgbm

lightgbm_model.py: uses the lightgbm module to break the data into features and classifiers and train the model on combined data

precipitation_prediction.py: applies trained model to realtime soundings obs in the midwest and predicts expected precip type at sounding points

wrf_precip.py: takes standard NetCDF wrf output and makes a continuous plot of the upper midwest and precip type