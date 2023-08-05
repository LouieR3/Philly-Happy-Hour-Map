from bs4 import BeautifulSoup
import requests
import pandas as pd
from tabulate import tabulate
from geopy.geocoders import Nominatim
import folium
from folium import IFrame
from folium.plugins import MarkerCluster
import json


# Read the CSV file into a DataFrame
df = pd.read_csv('AllSipsLocations.csv')

# Create the Folium map
map = folium.Map(location=[39.95, -75.16], zoom_start=15, tiles='CartoDB Positron')

# Create a dictionary to store popup HTML for each marker
popups = {}

# Loop through each row in the DataFrame and add markers to the map
for index, row in df.iterrows():
    # Create the popup content using HTML with centered content inside iframe
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

    # Add the popup content to the dictionary with the bar name as the key
    popups[row['Bar Name']] = popup_content

    # Create the popup using IFrame with custom styling
    popup = folium.Popup(IFrame(popup_content, width=230, height=155), max_width=230) # type: ignore

    # Create the marker and add it to the map
    marker = folium.Marker([row['Latitude'], row['Longitude']], popup=popup)
    marker.add_to(map)

# Create a sidebar HTML with a table containing bar names
sidebar_html = """<!DOCTYPE html>
<html>
<head>
<style>
    table {
        width: 200px;
        font-family: Arial;
    }
    th {
        background-color: #f2f2f2;
        text-align: center;
    }
    td {
        cursor: pointer;
    }
</style>
</head>
<body>
    <table>
        <tr><th>Bars</th></tr>
        {% for bar_name in bar_names %}
        <tr>
            <td onclick="openPopup('{{bar_name}}')">{{bar_name}}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""

# Create a list of bar names for the sidebar table
bar_names = df['Bar Name'].tolist()

# Render the sidebar HTML using the bar names
sidebar = folium.Html(sidebar_html.replace('\n', ''), script=True)
popup_sidebar = folium.Popup(sidebar, max_width=250) # type: ignore

# Create a Div icon with the sidebar HTML
icon_sidebar = folium.DivIcon(html=popup_sidebar, icon_size=(250, 400))

# Add the sidebar as an overlay on the map
marker_sidebar = folium.Marker(
    location=[39.955, -75.162],
    icon=icon_sidebar
)
marker_sidebar.add_to(map)

# Create a JavaScript function to open the corresponding popup on the map when a bar name is clicked
js = """
function openPopup(barName) {
    var popupContent = popups[barName];
    var iframe = document.createElement('iframe');
    iframe.setAttribute('style', 'width: 230px; height: 155px; border: none;');
    iframe.srcdoc = popupContent;
    var popup = L.popup().setContent(iframe);
    var marker = markers[barName];
    marker.bindPopup(popup).openPopup();
}
"""

# Add the JavaScript to the map
folium.Marker(
    location=[39.955, -75.162],
    icon=folium.DivIcon(html='<div></div>', icon_size=(0, 0)),
    popup=folium.Popup().add_child(folium.Element(js))
).add_to(map)

# Save the map as an HTML file
map.save('sips_map.html')