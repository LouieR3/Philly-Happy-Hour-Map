from bs4 import BeautifulSoup
import requests
import pandas as pd
from tabulate import tabulate
from geopy.geocoders import Nominatim
import folium
from folium import IFrame
from folium.plugins import MarkerCluster

df = pd.read_csv('AllSipsLocations.csv')

map = folium.Map(location=[39.95, -75.16], zoom_start=15, tiles='CartoDB Positron')

# Create a MarkerCluster object
# marker_cluster = MarkerCluster()

for index, row in df.iterrows():
    # Create the popup content using HTML
    # popup_content = f"<div style='width: auto; height: auto; text-align: center; font-family: Arial;'>"
    # popup_content += f"<a href='{row['Url']}' target='_blank' style='font-size: 18px; font-weight: bold; color:DodgerBlue; font-family: Arial;'>{row['Bar Name']}</a><br><br>"
    # popup_content += f"<a href='{row['Bar Website']}' target='_blank' style='font-size: 18px; font-weight: bold; color:DodgerBlue; font-family: Arial;'>Go to their website</a><br><br>"
    # popup_content += f"{row['Address']}</div>"
    popup_content = f"<div style='width: auto; height: auto; font-family: Arial;'>"
    popup_content += f"<p style='text-align: center; font-size: 18px; font-weight: bold; color:DodgerBlue;'>"
    popup_content += f"<a href='{row['Url']}' target='_blank'>{row['Bar Name']}</a></p>"
    popup_content += f"<p style='text-align: center; font-size: 16px; font-weight: bold; color:DodgerBlue;'>"
    popup_content += f"<a href='{row['Bar Website']}' target='_blank'>Go to their website</a></p>"
    popup_content += f"<p style='text-align: center;'>{row['Address']}</p></div>"
    
    # Create the popup using IFrame with custom styling
    popup = folium.Popup(IFrame(popup_content, width=230, height=155), max_width=230) # type: ignore

    # folium.Marker([row['Latitude'], row['Longitude']], popup=popup).add_to(marker_cluster)
    folium.Marker([row['Latitude'], row['Longitude']], popup=popup).add_to(map)

# Add the MarkerCluster to the map
# marker_cluster.add_to(map)

map.save('sips_map.html')