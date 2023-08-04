from bs4 import BeautifulSoup
import requests
import pandas as pd
from tabulate import tabulate
from geopy.geocoders import Nominatim
import time
import os

html = "https://centercityphila.org/explore-center-city/ccd-sips"
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

for page in pages:
    # Request and parse HTML for each page 
    page_html = requests.get(page, allow_redirects=False).text
    soupIter = BeautifulSoup(page_html, 'lxml')

    for card in soupIter.find_all('div', class_='o-card__container'):
        title = card.find('h3', class_='o-card__title').text
        address = card.find('p', class_='o-card__lede').text

        bars.append([title, address])

# Create dataframe  
df = pd.DataFrame(bars, columns=['Bar Name', 'Address'])

mask = df['Address'].str.contains('Philadelphia')
df = df[mask]
df = df.reset_index(drop=True)
df = df.drop_duplicates(subset=['Bar Name'])
print(df)

# def find_location(row):
#     place = row['Address']
#     print(place)
#     location = geolocator.geocode(place)
#     print(location)
#     print()
#     if location != None:
#         return location.latitude, location.longitude
#     else:
#         return 0


MAX_ATTEMPTS = 5

def find_location(row):
    place = row['Address'].replace("Ben Franklin", "Benjamin Franklin")
    print(place)
    attempts = 0
    while attempts < MAX_ATTEMPTS:
        try:
            location = geolocator.geocode(place)
            print(location)
            return location.latitude, location.longitude # type: ignore
        except:
            attempts += 1
            time.sleep(1)
    print()
    return None, None

df[['Latitude','Longitude']] = df.apply(find_location, axis="columns", result_type="expand")

print(df)

# Get the current working directory
current_directory = os.getcwd()

# Combine the current directory with the filename
file_path = os.path.join(current_directory, 'SipsLocations.csv')

df.to_csv("SipsLocations.csv", index=False)
# location = geolocator.geocode("1801 John F Kennedy Blvd, Philadelphia, PA 19103")
# print(location.latitude, location.longitude)