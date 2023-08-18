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

df = pd.read_csv('AllSipsOriginal.csv')

map = folium.Map(location=[39.951, -75.163], zoom_start=16, tiles='CartoDB Positron')

# Create a MarkerCluster object
# marker_cluster = MarkerCluster()

for index, row in df.iterrows():
    # Create the popup content using HTML
    popup_content = f"<div style='width: auto; height: auto; font-family: Arial;'>"
    popup_content += f"<p style='text-align: center; font-size: 18px; font-weight: bold;'>"
    popup_content += f"<a style='color:darkgreen;' href='{row['Bar Website']}' target='_blank'>{row['Bar Name']}</a></p>"
    # popup_content += f"<p style='text-align: center; font-size: 16px; font-weight: bold;'>"
    # popup_content += f"<a style='color:darkgreen;'href='{row['Bar Website']}' target='_blank'>Go to their website</a></p>"
    popup_content += f"<p style='text-align: center; font-size: 14px;'>{row['Address']}</p><hr>"
    # popup_content += f"<p style='text-align: center; font-size: 20px; font-weight: bold;'>Sips Deals</p>"
    # Split the 'Deals' column by newline character and join the parts with HTML line breaks
    deals_parts = row['Deals'].split('\n')
    # Loop through the deals parts and apply bold to specific lines
    for deal in deals_parts:
        if deal.strip() in ['$7 Cocktails', '$6 Wine', '$5 Beer', 'Half-Priced Appetizers']:
            popup_content += f"<p style='text-align: center; font-weight: bold; margin: 15px 5px 5px; font-size: 18px;'>{deal}</p>"
        else:
            popup_content += f"<p style='text-align: center; margin: 4px 0; font-size: 15px;'>{deal}</p>"

    popup_content += "</div>"

    # Append the deals content to the popup
    # popup_content += f"<p style='text-align: center;'>{deals_content}</p></div>"

    # Create the popup using IFrame with custom styling
    popup = folium.Popup(IFrame(popup_content, width=280, height=470), max_width=280) # type: ignore

    # folium.Marker([row['Latitude'], row['Longitude']], popup=popup).add_to(marker_cluster)
    folium.Marker([row['Latitude'], row['Longitude']], popup=popup, icon=folium.Icon(color="darkgreen", icon="glyphicon-glass")).add_to(map)

map.save('sips_map.html')

# Add the MarkerCluster to the map
# marker_cluster.add_to(map)
