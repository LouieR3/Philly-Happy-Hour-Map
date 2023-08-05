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
    popup_content = f"<div style='width: auto; height: auto; font-family: Arial;'>"
    popup_content += f"<p style='text-align: center; font-size: 18px; font-weight: bold; color:DodgerBlue;'>"
    popup_content += f"<a href='{row['Url']}' target='_blank'>{row['Bar Name']}</a></p>"
    popup_content += f"<p style='text-align: center; font-size: 16px; font-weight: bold; color:DodgerBlue;'>"
    popup_content += f"<a href='{row['Bar Website']}' target='_blank'>Go to their website</a></p>"
    popup_content += f"<p style='text-align: center;'>{row['Address']}</p><hr>"
    # popup_content += f"<p style='text-align: center;'>{row['Deals']}</p></div>"
    # Split the 'Deals' column by newline character and join the parts with HTML line breaks
    deals_parts = row['Deals'].split('\n')
    # Loop through the deals parts and apply bold to specific lines
    for deal in deals_parts:
        if deal.strip() in ['$7 Cocktails', '$6 Wine', '$5 Beer', 'Half-Priced Appetizers']:
            popup_content += f"<p style='text-align: center; font-weight: bold; margin: 10px 5px; font-size: 18px;'>{deal}</p>"
        else:
            popup_content += f"<p style='text-align: center; margin: 4px 0; font-size: 15px;'>{deal}</p>"

    popup_content += "</div>"

    # Append the deals content to the popup
    # popup_content += f"<p style='text-align: center;'>{deals_content}</p></div>"
    
    
    # Create the popup using IFrame with custom styling
    popup = folium.Popup(IFrame(popup_content, width=260, height=300), max_width=260) # type: ignore

    # folium.Marker([row['Latitude'], row['Longitude']], popup=popup).add_to(marker_cluster)
    folium.Marker([row['Latitude'], row['Longitude']], popup=popup, icon=folium.Icon(icon="glyphicon-glass")).add_to(map)

# Add the MarkerCluster to the map
# marker_cluster.add_to(map)

map.save('sips_map.html')