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

# ------------------------------------------------
# This script does = Scraps the basic data from the Sips list site and get Lat and Long
# ------------------------------------------------
run_on = "ccd-sips"
# run_on = "ccd-restaurant-week"
html = "https://centercityphila.org/explore-center-city/" + run_on
base_html = "https://centercityphila.org"
source = requests.get(html).text
soup = BeautifulSoup(source, "lxml")

locations = []

pages= []
pager = soup.find('div', class_='c-pager')
for link in pager.find_all('a'): # type: ignore
    pages.append(base_html + link['href'])

print(pages)
page_number = 1
restaurant_info_list = []
while True:
    # Create the URL for the current page
    current_url = f"{html}?page={page_number}"
    # Request and parse HTML for each page 
    page_html = requests.get(current_url, allow_redirects=False).text
    soupIter = BeautifulSoup(page_html, 'lxml')
    # print(soupIter.find_all('tr')[1])
    card_media_divs = soupIter.find_all('div', class_='o-card__media')
    for card_media in card_media_divs:
        img = card_media.find('img')
        if img and img['alt'] != '':
            alt_text = img['alt'].rstrip('*')
            src_link = base_html + img['src']
            restaurant_info_list.append({'Bar Name': alt_text, 'Photo': src_link})
            # print({'alt_text': alt_text, 'src_link': src_link})
    pager = soupIter.find('div', class_='c-pager')
    next_page_link = pager.find('a', href=f"/explore-center-city/{run_on}?page={page_number + 1}") # type: ignore
    
    if not next_page_link:
        break  # No more pages, exit the loop
    else:
        page_number += 1

# Create dataframe  
df1 = pd.DataFrame(restaurant_info_list)

# Read the DataFrame from the CSV file
df2 = pd.read_csv('AllSipsLocations.csv')
df2 = pd.read_csv('RestaurantWeek.csv')

# Merge the two DataFrames on 'Restaurant Name' column
merged_df = pd.merge(df2, df1, on='Bar Name', how='inner')
# Print the resulting DataFrame with the new "Bar Website" column
print(df1)
print(merged_df)
csvName = "AllSipsLocations2.csv"
csvName = "RestaurantWeek2.csv"
merged_df.to_csv(csvName, index=False)