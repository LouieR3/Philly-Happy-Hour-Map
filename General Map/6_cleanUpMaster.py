import pandas as pd
from yelpapi import YelpAPI
import yelpapi
import requests
import json
import html
import re
from bs4 import BeautifulSoup
import time

# ------------------------------------------------
# This script does = Gets the information from each Restaurant from yelp
# ------------------------------------------------
start_time = time.time()

# Load the MasterTable from the original CSV
df = pd.read_csv('../Csv/MasterTable.csv')
print(df)
df['Sips Participant'].fillna('N', inplace=True)
df['Restaurant Week Participant'].fillna('N', inplace=True)
df.drop(columns=['Paid Wi-Fi'], inplace=True)
df['Wi-Fi'] = df['Wi-Fi'].fillna(df['Free Wi-Fi'])
df.drop(columns=['Free Wi-Fi'], inplace=True)
df['Loud'] = df['Loud'].fillna(df['Very Loud'])
df.drop(columns=['Very Loud'], inplace=True)

print()
print(df)

df.to_csv('UpdatedMasterTable.csv', index=False)
