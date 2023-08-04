from bs4 import BeautifulSoup
import requests
import pandas as pd
from tabulate import tabulate
from geopy.geocoders import Nominatim
import os 

# geolocator = Nominatim(timeout=10, user_agent="my_app")
# location = geolocator.geocode("1700 Benjamin Franklin Pkwy, Philadelphia, PA 19103")
# print(location)
# print(location.latitude, location.longitude)

current_directory = os.getcwd()
print(current_directory)