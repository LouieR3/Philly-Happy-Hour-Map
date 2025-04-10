import numpy as np
import pandas as pd
from geopy.geocoders import Nominatim
import folium
from folium import IFrame
from folium.utilities import JsCode
from folium.features import GeoJsonPopup
from folium.plugins import TimestampedGeoJson, TimeSliderChoropleth, TagFilterButton, MarkerCluster
from geopy.extra.rate_limiter import RateLimiter
import time
import pandas as pd
from tabulate import tabulate
from folium import IFrame
import json

def geocode_addresses():
    # Read the CSV file
    df = pd.read_csv('The Quizzo List - PHL Geocoded.csv')
    df = pd.read_csv('The Quizzo List - PHL.csv')
    print(df)
    # Combine all ADDRESS fields into a comma-separated address string
    df['Full Address'] = df.apply(lambda row: f"{row['ADDRESS_STREET']}, {row['ADDRESS_CITY']}, {row['ADDRESS_STATE']}, {row['ADDRESS_ZIP']}" if pd.isna(row['ADDRESS_UNIT']) else f"{row['ADDRESS_STREET']}, {row['ADDRESS_UNIT']}, {row['ADDRESS_CITY']}, {row['ADDRESS_STATE']}, {row['ADDRESS_ZIP']}", axis=1)
    print(df['Full Address'])

    # Initialize geocoder
    geolocator = Nominatim(timeout=10, user_agent="my_app") # type: ignore

    MAX_ATTEMPTS = 5

    def find_location(row):
        # First attempt with the full address
        place = row['Full Address']
        print(f"Trying full address: {place}")
        attempts = 0

        while attempts < MAX_ATTEMPTS:
            try:
                location = geolocator.geocode(place)
                if location:
                    print(f"Geocoded (Full Address): {location.latitude}, {location.longitude}") # type: ignore
                    return location.latitude, location.longitude # type: ignore
            except:
                pass  # Continue to retry
            attempts += 1
            time.sleep(1)

        # If the full address fails, attempt with a simplified address
        place = f"{row['ADDRESS_STREET']}, {row['ADDRESS_STATE']}, {row['ADDRESS_ZIP']}"
        print(f"Trying simplified address: {place}")
        attempts = 0

        while attempts < MAX_ATTEMPTS:
            try:
                location = geolocator.geocode(place)
                if location:
                    print(f"Geocoded (Simplified): {location.latitude}, {location.longitude}") # type: ignore
                    return location.latitude, location.longitude # type: ignore
            except:
                pass  # Continue to retry
            attempts += 1
            time.sleep(1)

        print("Geocoding failed for this record.")
        return None, None  # If both attempts fail

    # Geocode addresses and add latitude and longitude columns
    df[['Latitude','Longitude']] = df.apply(find_location, axis="columns", result_type="expand")

    # Save the updated DataFrame to a new CSV file
    df.to_csv('The Quizzo List - PHL FINAL.csv', index=False)

# geocode_addresses()

def create_map():
    df = pd.read_csv('The Quizzo List - PHL FINAL.csv')
    # Create a list of unique weekdays and order them by the days of the week
    weekdays_order = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']
    weekdays = sorted(df['WEEKDAY'].unique().tolist(), key=lambda x: weekdays_order.index(x))
    # Create a list of unique times
    times = df['TIME'].unique().tolist()
    # times = sorted(df['TIME'].unique().tolist(), key=lambda x: pd.to_datetime(x, format='%I:%M %p'))

    map = folium.Map(location=[39.951, -75.163], zoom_start=10, tiles='CartoDB Positron')
    # marker_cluster =  MarkerCluster().add_to(map)

    for index, row in df.iterrows():
        popup_content = f"<div style='width: auto; height: auto; font-family: Arial;'>"
        popup_content += f"<p style='text-align: center; font-size: 18px; font-weight: bold;'>{row['BUSINESS']}</p>"
        popup_content += f"<p style='text-align: center; font-size: 16px;'>{row['ADDRESS_STREET']}, {row['ADDRESS_CITY']}, {row['ADDRESS_STATE']} {row['ADDRESS_ZIP']}</p>"
        popup_content += f"<p style='text-align: center; font-size: 16px;'>{row['WEEKDAY']} - {row['TIME']}</p>"
        if pd.notna(row['HOST']) and row['HOST'] != '':
            popup_content += f"<p style='text-align: center; font-size: 16px;'>Host: {row['HOST']} <br> Event Type: {row['EVENT_TYPE']}</p>"
        else:
            popup_content += f"<p style='text-align: center; font-size: 16px;'>Event Type: {row['EVENT_TYPE']}</p>"

        if pd.notna(row['PRIZE_1_TYPE']) and row['PRIZE_1_TYPE'] != '':
            popup_content += f"<p style='text-align: center; font-size: 16px;'>First Prize: {row['PRIZE_1_TYPE']} - {row['PRIZE_1_AMOUNT']}"
        if pd.notna(row['PRIZE_2_TYPE']) and row['PRIZE_2_TYPE'] != '':
            popup_content += f"<br> Second Prize: {row['PRIZE_2_TYPE']} - {row['PRIZE_2_AMOUNT']}</p>"
        else:
            popup_content += f"</p>"
        popup_content += "</div>"

        popup = folium.Popup(IFrame(popup_content, width=280, height=240), lazy=True, max_width=280) # type: ignore
        
        folium.Marker(
                [row['Latitude'], row['Longitude']],
                popup=popup,
                icon=folium.Icon(color="darkgreen", icon="glyphicon-glass"),
                tags=[row['WEEKDAY'], row['TIME']]
            ).add_to(map)

    # Add the TagFilterButton to the map
    TagFilterButton(weekdays).add_to(map)
    # Add the TagFilterButton for times to the map
    TagFilterButton(times).add_to(map)

    
    # Add custom JavaScript and CSS for toggling and alignment
    custom_css = """
    <style>
    .tag-filter-button {
        display: inline-block;
        margin-right: 10px;
    }
    </style>
    """
    custom_js = """
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        const buttons = document.querySelectorAll('.tag-filter-button');
        buttons.forEach(button => {
            button.addEventListener('click', function() {
                buttons.forEach(btn => {
                    if (btn !== button) {
                        btn.classList.remove('active');
                    }
                });
                button.classList.toggle('active');
            });
        });
    });
    </script>
    """
    map.get_root().html.add_child(folium.Element(custom_css + custom_js)) # type: ignore

    map.save('public/quizzo_map.html')
# create_map()

def get_yelp_data():
    print()

df = pd.read_csv('quizzo_list.csv')

