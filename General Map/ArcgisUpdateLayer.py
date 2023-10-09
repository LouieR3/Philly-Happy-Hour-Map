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
gisUser, gisPass = "GIS_Pennoni", "P3NNON!G!S"
gis = GIS("https://pennoni.maps.arcgis.com/", gisUser, gisPass)

target_portal = "gis.pennoni.com/portal/"
target_admin = "gis_integration"
target_admin_password = "P3NNON!G!S"
target = GIS(
    "https://" + target_portal,
    target_admin,
    target_admin_password,
    verify_cert=False,
)

merged_df = pd.read_csv("DeltekOffices.csv")
# pull the feature layer to append to
lyr = target.content.get("336a2c5f0c584621960e64d29881cc7a").layers[0]
# GeoAccessor class adds a spatial namespace that performs spatial operations on the given Pandas DataFrame
sdf = GeoAccessor.from_xy(merged_df, "Longitude", "Latitude")

# truncate all records from the feature layer
lyr.manager.truncate()

# apply new records to layer in 200-feature chunks
i = 0
while i < len(sdf):
    fs = sdf.loc[i : i + 199].spatial.to_featureset()
    updt = lyr.edit_features(adds=fs)
    msg = updt["addResults"][0]
    # print(fs)
    # print(updt)
    print(msg)
    print()
    # print(f"Rows {i:4} - {i+199:4} : {msg['success']}")
    if "error" in msg:
        print(f"Rows {i:4} - {i+199:4} : {msg['success']}")
        print(msg["error"]["description"])
    i += 200

print("Program finished --- %s seconds ---" % (time.time() - start_time))