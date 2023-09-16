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


sip_df = pd.read_csv('AllSipsLocations.csv')

rw_df = pd.read_csv('RestaurantWeek.csv')

sip_columns = sip_df.columns

rw_columns = rw_df.columns

# Merge sip_df and rw_df on 'Name'
merged_df = pd.merge(sip_df, rw_df, on='Name', how='outer', suffixes=('_sip', '_rw'))
print(merged_df.head)
# Use Review Count from rw_df if available

# Use Photo from sip_df if available
merged_df['Address'] = merged_df['Address_rw'].fillna(merged_df['Address_sip'])
merged_df['Latitude'] = merged_df['Latitude_rw'].fillna(merged_df['Latitude_sip'])
merged_df['Longitude'] = merged_df['Longitude_rw'].fillna(merged_df['Longitude_sip'])
merged_df['Website'] = merged_df['Website_rw'].fillna(merged_df['Website_sip'])
merged_df['Categories'] = merged_df['Categories_rw'].fillna(merged_df['Categories_sip'])
merged_df['Price'] = merged_df['Price_rw'].fillna(merged_df['Price_sip'])
merged_df['Yelp Rating'] = merged_df['Yelp Rating_rw'].fillna(merged_df['Yelp Rating_sip'])
merged_df['Review Count'] = merged_df['Review Count_rw'].fillna(merged_df['Review Count_sip'])
merged_df['Photo'] = merged_df['Photo_sip'].fillna(merged_df['Photo_rw'])

# Create 'Sips Participant' and 'Restaurant Week Participant' columns
merged_df['Sips Participant'] = merged_df['Sips Url'].notnull().apply(lambda x: 'Y' if x else 'N')
merged_df['Restaurant Week Participant'] = merged_df['RW Url'].notnull().apply(lambda x: 'Y' if x else 'N')
print(merged_df.head)

# Select the desired columns
# merged_df = merged_df[sip_columns + rw_columns]
columns_to_keep = [col for col in merged_df.columns if not (col.endswith("_rw") or col.endswith("_sip"))]
merged_df = merged_df[columns_to_keep]
# Print the merged DataFrame
print(merged_df)
merged_df.to_csv("Test.csv", index=False)