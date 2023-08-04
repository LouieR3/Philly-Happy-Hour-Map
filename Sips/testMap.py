from bs4 import BeautifulSoup
import requests
import pandas as pd
from tabulate import tabulate
from geopy.geocoders import Nominatim
import folium
from folium import IFrame
from folium.plugins import MarkerCluster

df = pd.read_csv('AllSipsLocations.csv')

map = folium.Map(location=[39.95, -75.16], zoom_start=16, tiles='CartoDB Positron')

# Create a MarkerCluster object
# marker_cluster = MarkerCluster()

for index, row in df.iterrows():
    # Create the popup content using HTML
    popup_content = f"<div style='width: auto; height: auto; text-align: center; font-family: Arial;'>"
    popup_content += f"<a href='{row['Url']}' target='_blank' style='font-size: 18px; font-weight: bold; color:DodgerBlue; font-family: Arial;'>{row['Bar Name']}</a><br><br>"
    popup_content += f"{row['Address']}</div>"
    
    # Create the popup using IFrame with custom styling
    popup = folium.Popup(IFrame(popup_content, width=200, height=130), max_width=200) # type: ignore

    # folium.Marker([row['Latitude'], row['Longitude']], popup=popup).add_to(marker_cluster)
    folium.Marker([row['Latitude'], row['Longitude']], popup=popup).add_to(map)

# Add the MarkerCluster to the map
# marker_cluster.add_to(map)

map.save('sips_map.html')