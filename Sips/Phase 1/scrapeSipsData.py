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

# ---------------------------------------------------------------------------------------
# This script does = Scraps the basic data from the Sips list site and get Lat and Long
# ---------------------------------------------------------------------------------------

html = "https://centercityphila.org/explore-center-city/ccd-sips/sips-list-view"
base_html = "https://centercityphila.org"
source = requests.get(html).text
soup = BeautifulSoup(source, "lxml")

geolocator = Nominatim(timeout=10, user_agent="my_app") # type: ignore
bars = []

pages= []
pager = soup.find('div', class_='c-pager')
for link in pager.find_all('a'): # type: ignore
    pages.append(base_html + link['href'])

print(pages)

pattern = r'apos\.maps\["ccd-places"\]\.addMap\((.*?)\)'
bar_info_list = []
for page in pages:
    # Request and parse HTML for each page 
    page_html = requests.get(page, allow_redirects=False).text
    soupIter = BeautifulSoup(page_html, 'lxml')
    # print(soupIter.find_all('tr')[1])
    for card in soupIter.find_all('tr'):
        try:
            title = card.find('a', class_='o-text-link').text.strip("\n        ")
            url = html + card.find('a', class_='o-card-link')['href']
            address = card.find('td', attrs={'data-th': 'Address'}).text.strip()

            bars.append([title, address, url])
        except AttributeError:
            # One of the classes is not present in this <tr> element
            # Skip this element and continue with the next one
            continue

# Create dataframe  
df = pd.DataFrame(bars, columns=['Name', 'Address', 'Website'])

mask = df['Address'].str.contains('Philadelphia')
df = df[mask]
df = df.reset_index(drop=True)
df = df.drop_duplicates(subset=['Name'])
print(df)

pattern = r'apos\.maps\["ccd-places"\]\.addMap\((.*?)\)'
bar_info_list = []
for page in pages:
    page_html = requests.get(page, allow_redirects=False).text
    soupIter = BeautifulSoup(page_html, 'lxml')
    script_tags = soupIter.find_all('script', text=re.compile(pattern))

    json_data = {}
    for script_tag in script_tags:
        lines = script_tag.string.splitlines()
        for line in lines:
            if re.match(pattern, line.strip()):
                # Extract the JSON text from the line
                start_index = line.find('{')
                end_index = line.rfind('}') + 1
                json_text = line[start_index:end_index]
                json_data = json.loads(json_text)
                break
        if json_data is not None:
            break

    for item in json_data["items"]:
        title = item.get("title", "")
        url_website = item.get("urlWebsite", "")
        if url_website:
            url_website = url_website.rstrip('/')
        bar_info = {"Name": title, "Website": url_website}
        # print(bar_info)
        bar_info_list.append(bar_info)

new_df = pd.DataFrame(bar_info_list)


# Print the resulting DataFrame with the new "Bar Website" column
print(new_df)

# df = pd.read_csv('../Csv/AllSipsLocations.csv')
merged_df = df.merge(new_df, on='Name', how='left')
print(merged_df)
# merged_df.to_csv("AllSipsLocations.csv", index=False)
# df = merged_df
MAX_ATTEMPTS = 5

def find_location(row):
    place = row['Address'].replace("Ben Franklin", "Benjamin Franklin")
    print(place)
    attempts = 0
    while attempts < MAX_ATTEMPTS:
        try:
            location = geolocator.geocode(place)
            # print(location)
            return location.latitude, location.longitude # type: ignore
        except:
            attempts += 1
            time.sleep(1)
    print()
    return None, None

df[['Latitude','Longitude']] = df.apply(find_location, axis="columns", result_type="expand")

print(df)

# # Get the current working directory
# current_directory = os.getcwd()

# # Combine the current directory with the filename
# file_path = os.path.join(current_directory, 'SipsLocations.csv')

# df.to_csv("AllSipsLocations.csv", index=False)
