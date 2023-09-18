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

geolocator = Nominatim(timeout=10, user_agent="my_app") # type: ignore

MAX_ATTEMPTS = 5
place = "1518 Sansom St, Philadelphia, PA 19102"
place = "247 S 17th St, Philadelphia, PA 19103"
place = "300 S Broad St, Philadelphia, PA 19102"
print(place)
attempts = 0
while attempts < MAX_ATTEMPTS:
    try:
        location = geolocator.geocode(place)
        print(location)
        print(location.raw) # type: ignore
        # return location.latitude, location.longitude # type: ignore
    except:
        attempts += 1
        time.sleep(1)
print()