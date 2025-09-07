from arcgis.gis import GIS
from arcgis import GeoAccessor
from arcgis.features import Feature
import requests
import json
from arcgis import features
from arcgis.features import FeatureLayer
from arcgis.geocoding import get_geocoders, batch_geocode
from arcgis.features.managers import FeatureLayerCollectionManager
import pandas as pd
from datetime import date
from datetime import timedelta
from arcgis.geometry import SpatialReference
import time
import os
import csv

# Get time the script started so you know how long it ran
start_time = time.time()

# Initialize GIS connection
gisUser, gisPass = "LouieAndAva", "esriUClover1!"
gis = GIS("https://mappy-hour.maps.arcgis.com/", gisUser, gisPass)

# target_portal = "gis.pennoni.com/portal/"
# target_admin = "gis_integration"
# target_admin_password = "P3NNON!G!S"
# target = GIS(
#     "https://" + target_portal,
#     target_admin,
#     target_admin_password,
#     verify_cert=False,
# )

df = pd.read_csv("MasterTable.csv")

# df = df.loc[df['SIPS_PARTICIPANT'] == 'Y']
# df = pd.read_csv("UpdatedMasterTable.csv")
# pull the feature layer to append to

# TEST LAYER
# lyr = gis.content.get("f51d537b0ef34adc960fb1833d91ea99").layers[0]
# lyr = gis.content.get("08d602f3932243d3a27d1237f0753b7e").layers[0]

# PROD LAYER
lyr = gis.content.get("8fe4839f300c45ca8deab275998f4632").layers[0]

# SIPS LAYER
# lyr = gis.content.get("b145d298c4b34f77b1c3cff9c6db0dc2").layers[0]

lyr_df = lyr.query().sdf
# print(lyr_df)
# GeoAccessor class adds a spatial namespace that performs spatial operations on the given Pandas DataFrame
sdf = GeoAccessor.from_xy(df, "Longitude", "Latitude")
print(sdf)
# Find bars in MasterTable not in lyr_df
# missing_bars_df = df[~df['Name'].isin(lyr_df['NAME'])]
# print(missing_bars_df)
# truncate all records from the feature layer
lyr.manager.truncate()

# apply new records to layer in 200-feature chunks
i = 0
while i < len(sdf):
    fs = sdf.loc[i : i + 199].spatial.to_featureset()
    updt = lyr.edit_features(adds=fs)
    msg = updt["addResults"][0]
    print(msg)
    # print(f"Rows {i:4} - {i+199:4} : {msg['success']}")
    if "error" in msg:
        print(f"Rows {i:4} - {i+199:4} : {msg['success']}")
        print(msg["error"]["description"])
    i += 200

print("Program finished --- %s seconds ---" % (time.time() - start_time))
