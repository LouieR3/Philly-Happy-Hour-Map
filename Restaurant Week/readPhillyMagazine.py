import pandas as pd
from bs4 import BeautifulSoup
import requests
from geopy.geocoders import Nominatim
import time
geolocator = Nominatim(timeout=10, user_agent="my_app") # type: ignore

url = "https://www.phillymag.com/foobooz/50-best-restaurants/"
html = requests.get(url).text
soup = BeautifulSoup(html, 'lxml')
# print(soup)
# print()
data = []

for h2 in soup.find_all('h2'):
    try:
        rank = h2.find('span', class_='shorenumbers').text.split(" ")[0].replace(".", "")
    except:
        rank = None
        
    try:    
        name = h2.find('a').text
    except:
        name = None
        
    # Find next p tag
    p = h2.find_next('p').find_next('p')
    print(name)
    print(p)
    print()
    
    # Get cuisine, neighborhood, address
    try:
        info = p.find('strong').text.split('|')
        cuisine = info[1].strip()
        neighborhood = info[0].strip()
        website = p.find('a')['href']

        address = p.find('em').text
    except:
        website = None
        cuisine = None
        neighborhood = None
        address = None
    
    data.append({'Rank': rank, 'Name': name, 'Cuisine': cuisine, 'Neighborhood': neighborhood, 'Website': website, 'Address': address})

MAX_ATTEMPTS = 5
df = pd.DataFrame(data)
print(df)
# Drop rows with missing Rank 
df = df[df['Rank'].notna()]

def find_location(row):
    place = row['Address'].replace("Ben Franklin", "Benjamin Franklin") + ", Philadelphia, PA"
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

# Write to CSV file
df.to_csv('restaurants.csv', index=False)