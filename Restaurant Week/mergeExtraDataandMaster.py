from bs4 import BeautifulSoup
import requests
import pandas as pd
from tabulate import tabulate
from geopy.geocoders import Nominatim
import time
import os
import folium
import re
import json


extra_df = pd.read_csv('ExtraYelp2.csv')
extra_df['Good For Groups'] = extra_df['Good For Groups'].fillna(extra_df['Good for Groups'])
extra_df['Good For Working'] = extra_df['Good For Working'].fillna(extra_df['Good for Working'])
extra_df['Loud'] = extra_df['Loud'].fillna(extra_df['Very Loud'])
columns_to_drop = ["Good for Working", "Good for Groups", "Very Loud"]
extra_df.drop(columns=columns_to_drop, inplace=True)
# Loop through columns and count non-null values
for column in extra_df.columns:
    non_null_count = extra_df[column].count()
    if non_null_count < 3:
        extra_df.drop(columns=column, inplace=True)

mt_df = pd.read_csv('MasterTableOld.csv')

extra_columns = extra_df.columns

mt_columns = mt_df.columns

# Merge sip_df and rw_df on 'Name'
merged_df = pd.merge(mt_df, extra_df, on='Name', how='inner', suffixes=('_mt', '_xtra'))
print(merged_df.head)
# Use Review Count from rw_df if available

# Use Photo from sip_df if available

merged_df['Yelp Rating'] = merged_df['Yelp Rating_xtra'].fillna(merged_df['Yelp Rating_mt'])
print(merged_df.head)

# Select the desired columns
columns_to_keep = [col for col in merged_df.columns if not (col.endswith("_mt") or col.endswith("_xtra"))]
merged_df = merged_df[columns_to_keep]
# Print the merged DataFrame
print(merged_df)
merged_df.to_csv("Test.csv", index=False)