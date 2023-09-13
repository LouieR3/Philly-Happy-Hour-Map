from bs4 import BeautifulSoup
import requests
import pandas as pd
from tabulate import tabulate
from geopy.geocoders import Nominatim
import folium
from folium import IFrame
from folium.plugins import MarkerCluster

# ------------------------------------------------
# This script does = Created the folium map for the csv
# ------------------------------------------------

df = pd.read_csv('RestaurantWeek.csv')

map = folium.Map(location=[39.951, -75.163], zoom_start=15, tiles='CartoDB Positron')

# Create a MarkerCluster object
# marker_cluster = MarkerCluster()

for index, row in df.iterrows():
    # Create the popup content using HTML
    popup_content = f"<div style='width: auto; height: auto; font-family: Arial;'>"
    popup_content += f"<p style='text-align: center; font-size: 18px; font-weight: bold;'>"
    popup_content += f"<a style='color:darkgreen;' href='{row['Restaurant Website']}' target='_blank'>{row['Restaurant Name']}</a></p>"
    # popup_content += f"<p style='text-align: center; font-size: 16px; font-weight: bold;'>"
    # popup_content += f"<a style='color:darkgreen;'href='{row['Restaurant Website']}' target='_blank'>Go to their website</a></p>"
    popup_content += f"<p style='text-align: center; font-size: 14px;'>{row['Address']}</p><hr>"
    # popup_content += f"<p style='text-align: center; font-size: 20px; font-weight: bold;'>Sips Deals</p>"
    popup_content += f"<p style='text-align: center; font-size: 16px;'>{row['Details']}</p>"
    popup_content += f"<p style='text-align: center; font-size: 16px;'>{row['Deals Offered']}</p>"


    popup_content += "</div>"

    # Append the deals content to the popup
    # popup_content += f"<p style='text-align: center;'>{deals_content}</p></div>"

    # Create the popup using IFrame with custom styling
    popup = folium.Popup(IFrame(popup_content, width=280, height=240), max_width=280) # type: ignore

    # folium.Marker([row['Latitude'], row['Longitude']], popup=popup).add_to(marker_cluster)
    folium.Marker([row['Latitude'], row['Longitude']], popup=popup, icon=folium.Icon(color="darkgreen", icon="glyphicon-glass")).add_to(map)

map.save('rw_map.html')

# Add the MarkerCluster to the map
# marker_cluster.add_to(map)
