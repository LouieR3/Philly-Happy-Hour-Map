import pandas as pd
from yelpapi import YelpAPI
import yelpapi
import requests
import json
import html
import re
from bs4 import BeautifulSoup
import time
import numpy as np

# ------------------------------------------------
# This script does = Gets the information from each Restaurant from yelp
# ------------------------------------------------
start_time = time.time()

df = pd.read_csv('MasterTable.csv')
print(df.columns)

day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
df[day_names] = df[day_names].fillna('Closed')
# Define a function to clean and convert the time strings to datetime
def clean_and_convert(time_str):
    # Remove "(Next day)" and "Closed", if present
    time_str = time_str.replace(" (Next day)", "").replace("Closed", "")
    print(time_str)
    print(pd.to_datetime(time_str, format='%I:%M %p'))
    print()
    # Convert to datetime
    return pd.to_datetime(time_str, format='%I:%M %p', errors='coerce')

# Apply the function to all columns
for day in day_names:
    df[day] = df[day].apply(clean_and_convert)

print(df[day_names])