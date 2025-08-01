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
from yelpapi import YelpAPI
import yelpapi
from geopy.geocoders import Nominatim

def geocode_addresses():
    # Read the CSV file
    # df = pd.read_csv('The Quizzo List - PHL Geocoded.csv')
    df = pd.read_csv('public/quizzo_list.csv')
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
    df.to_csv('public/quizzo_list.csv', index=False)
# geocode_addresses()

def create_map():
    df = pd.read_csv('public/quizzo_list.csv')
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

df = pd.read_csv('public/quizzo_list.csv')

# Geopy setup
geolocator = Nominatim(user_agent="quizzo_geocoder", timeout=10) # type: ignore

# STEP 1 - READ AND PREPARE THE DATA
def merge_and_geocode_quizzo():
    # Load the quizzo list and quizzo extra CSVs
    quizzo_list = pd.read_csv('public/quizzo_list.csv')
    quizzo_extra = pd.read_csv('Quizzo/quizzo_extra.csv')

    # Standardize column names to match quizzo_list
    quizzo_extra.rename(columns={
        'Bar': 'BUSINESS',
        'Time': 'TIME',
        'Day': 'WEEKDAY',
        'Neighborhood': 'NEIGHBORHOOD',
        'Prize': 'PRIZE_1_AMOUNT',
        'Host': 'HOST',
        'Address': 'ADDRESS_STREET',
        'Theme': 'EVENT_TYPE'
    }, inplace=True)

    # Add missing columns with default values
    missing_columns = [
        'BUSINESS_TAGS', 'OCCURRENCE_TYPES', 'ADDRESS_UNIT', 'ADDRESS_CITY', 
        'ADDRESS_STATE', 'ADDRESS_ZIP', 'PRIZE_1_TYPE', 'PRIZE_2_TYPE', 
        'PRIZE_2_AMOUNT', 'PRIZE_3_TYPE', 'PRIZE_3_AMOUNT', 'Full Address', 
        'Latitude', 'Longitude'
    ]
    for col in missing_columns:
        quizzo_extra[col] = None

    # Standardize WEEKDAY values (remove extra text and trailing 's')
    quizzo_extra['WEEKDAY'] = quizzo_extra['WEEKDAY'].str.upper().str.replace(r"'S|S\b", "", regex=True).str.strip()

    # Standardize all values to uppercase
    quizzo_extra = quizzo_extra.applymap(lambda x: x.upper() if isinstance(x, str) else x) # type: ignore

    # Split ADDRESS_STREET into components (if applicable)
    quizzo_extra[['ADDRESS_CITY', 'ADDRESS_STATE', 'ADDRESS_ZIP']] = quizzo_extra['ADDRESS_STREET'].str.extract(
        r',\s*([^,]+),\s*([A-Z]{2})\s*(\d{5})$'
    )
    quizzo_extra['ADDRESS_STREET'] = quizzo_extra['ADDRESS_STREET'].str.extract(r'^(.*?),')[0]

    # Populate PRIZE_1_TYPE based on PRIZE_1_AMOUNT
    quizzo_extra['PRIZE_1_TYPE'] = quizzo_extra['PRIZE_1_AMOUNT'].apply(
        lambda x: 'GIFT_CARD' if pd.notna(x) else None
    )

    # Generate Full Address
    quizzo_extra['Full Address'] = quizzo_extra.apply(
        lambda row: f"{row['ADDRESS_STREET']}, {row['ADDRESS_CITY']}, {row['ADDRESS_STATE']}, {row['ADDRESS_ZIP']}"
        if pd.notna(row['ADDRESS_STREET']) else None,
        axis=1
    )

    # Geocode missing Latitude and Longitude
    latitudes = []
    longitudes = []
    for _, row in quizzo_extra.iterrows():
        if pd.notna(row['Full Address']):
            attempts = 0
            latitude, longitude = None, None
            while attempts < 5:
                try:
                    location = geolocator.geocode(row['Full Address'])
                    if location:
                        latitude, longitude = location.latitude, location.longitude # type: ignore
                        break
                except Exception as e:
                    print(f"Geocoding error for {row['BUSINESS']}: {e}")
                attempts += 1
                time.sleep(1)
            latitudes.append(latitude)
            longitudes.append(longitude)
        else:
            latitudes.append(None)
            longitudes.append(None)

    quizzo_extra['Latitude'] = latitudes
    quizzo_extra['Longitude'] = longitudes

    # Save the transformed data to a new CSV
    quizzo_extra.to_csv('Quizzo/quizzo_extra_transformed.csv', index=False)
    print("Transformed quizzo_extra.csv saved as quizzo_extra_transformed.csv.")

# merge_and_geocode_quizzo()

# Read the transformed quizzo_extra CSV
quizzo_extra = pd.read_csv('Quizzo/quizzo_extra_transformed.csv')

# STEP 2 - BIG CLEAN OF DATA
def quzizo_cleaning(quizzo_extra):
    # Split PRIZE_1_AMOUNT into PRIZE_1_AMOUNT, PRIZE_2_AMOUNT, and PRIZE_3_AMOUNT
    quizzo_extra[['PRIZE_1_AMOUNT', 'PRIZE_2_AMOUNT', 'PRIZE_3_AMOUNT']] = quizzo_extra['PRIZE_1_AMOUNT'].str.split(',', expand=True).iloc[:, :3]

    # Clean WEEKDAY column by removing anything after "DAY"
    quizzo_extra['WEEKDAY'] = quizzo_extra['WEEKDAY'].str.extract(r'(\bDAY\b.*)')[0].str.strip()

    # Replace 'X' in EVENT_TYPE with an empty string
    quizzo_extra['EVENT_TYPE'] = quizzo_extra['EVENT_TYPE'].replace('X', '')

    # Read quizzo_list and master_list
    quizzo_list = pd.read_csv('public/quizzo_list.csv')
    master_list = pd.read_csv('MasterTable.csv')

    # Ensure BUSINESS and NEIGHBORHOOD columns are uppercase for merging
    quizzo_extra['BUSINESS'] = quizzo_extra['BUSINESS'].str.upper()
    quizzo_extra['NEIGHBORHOOD'] = quizzo_extra['NEIGHBORHOOD'].str.upper()
    quizzo_list['BUSINESS'] = quizzo_list['BUSINESS'].str.upper()
    quizzo_list['NEIGHBORHOOD'] = quizzo_list['NEIGHBORHOOD'].str.upper()
    master_list['Name'] = master_list['Name'].str.upper()

    # Merge missing Full Address and Lat/Long from quizzo_list
    def fuzzy_merge(df1, df2, key1, key2, neighborhood_key, columns_to_merge):
        merged_data = []
        for _, row in df1.iterrows():
            business = row[key1]
            neighborhood = row[neighborhood_key]
            match = df2[
                (df2[key2].str.contains(business, na=False)) & (df2[neighborhood_key] == neighborhood)
            ]
            if not match.empty:
                merged_data.append(match.iloc[0][columns_to_merge].to_dict())
            else:
                merged_data.append({col: None for col in columns_to_merge})
        return pd.DataFrame(merged_data)

    # First merge from quizzo_list
    quizzo_list_columns = ['Full Address', 'Latitude', 'Longitude']
    quizzo_list_merged = fuzzy_merge(
        quizzo_extra, quizzo_list, 'BUSINESS', 'BUSINESS', 'NEIGHBORHOOD', quizzo_list_columns
    )
    quizzo_extra[quizzo_list_columns] = quizzo_extra[quizzo_list_columns].combine_first(quizzo_list_merged)

    # Then merge from master_list
    master_list_columns = ['Address', 'Latitude', 'Longitude']
    master_list_merged = fuzzy_merge(
        quizzo_extra, master_list, 'BUSINESS', 'Name', 'NEIGHBORHOOD', master_list_columns
    )
    quizzo_extra['Full Address'] = quizzo_extra['Full Address'].combine_first(master_list_merged['Address'])
    quizzo_extra['Latitude'] = quizzo_extra['Latitude'].combine_first(master_list_merged['Latitude'])
    quizzo_extra['Longitude'] = quizzo_extra['Longitude'].combine_first(master_list_merged['Longitude'])

    # Drop unnecessary columns from merging
    quizzo_extra.drop(columns=['Address'], inplace=True)

    # Save the cleaned data back to a CSV
    quizzo_extra.to_csv('Quizzo/quizzo_extra_cleaned.csv', index=False)

    print("Cleaned data saved to Quizzo/quizzo_extra_cleaned.csv")

# quzizo_cleaning(quizzo_extra)

quizzo_extra = pd.read_csv('Quizzo/quizzo_extra_cleaned.csv')
# # Drop unnecessary columns
# quizzo_extra.drop(columns=['Full Address_quizzo_list', 'Latitude_quizzo_list', 'Longitude_quizzo_list', 'BUSINESS_TAGS', 'OCCURRENCE_TYPES'], inplace=True)
# # Rearrange columns to the desired order
# column_order = [
#     'BUSINESS', 'TIME', 'WEEKDAY', 'NEIGHBORHOOD', 'ADDRESS_STREET', 'ADDRESS_UNIT', 'ADDRESS_CITY', 'ADDRESS_STATE', 'ADDRESS_ZIP',
#     'PRIZE_1_TYPE', 'PRIZE_1_AMOUNT', 'PRIZE_2_TYPE', 'PRIZE_2_AMOUNT', 'PRIZE_3_TYPE', 'PRIZE_3_AMOUNT',
#     'HOST', 'EVENT_TYPE', 'Full Address', 'Latitude', 'Longitude',
# ]
# quizzo_extra = quizzo_extra[column_order]
# quizzo_extra.to_csv("Quizzo/quizzo_extra_cleaned.csv", index=False)

def quizzo_yelp_data():
    # Filter records where Full Address is empty
    quizzo_yelp_df = quizzo_extra[quizzo_extra['Full Address'].isna()]
    print(f"Number of records with missing Full Address: {len(quizzo_yelp_df)}")

    # Actual API Key
    # yelpapiKey = "DQx0YugiFJ5inYYp8fVvDqLx0R_dVo8yXxRZtpD5jkbNK0WmAqUygKIyXnYHlfL0pYRndGHGmuvn_QCXPVndRCc0VjtZzxCSHE8MhPthoJ4YUygg65DJrhMJLu7OZHYx"

    # Backup API Key
    # yelpapiKey = "r9ksNtdCcwK8MhsrL9fB5BvOGkC8Habi6-S5Shhh-Xu7CXF5xCBAPRCPS04atHegmf3BOMeW9gqNxA16E32gg4xDhcuWgD0k58m9jp280IpSb5zthhBCvmeXBsnPZHYx"

    # Backup backup API Key
    yelpapiKey = "XEmkEwex5TbqjOitZJ8xtLXTBMQQb7BrtQdzzw-hJVWwnIUysCwCzXT2X2xsMbSXR7uHxWnRkyyFIh1CxfLr6Ilj_n-xClAG_h5aKabBtAjJLVnZ9mMfdKFWlMvPZHYx"

    yelp = yelpapi.YelpAPI(yelpapiKey)
    base_url = "https://www.yelp.com/biz/"

    # Function to get Yelp data for each record
    def get_yelp_data(row):
        business_name = row['BUSINESS']
        neighborhood = row['NEIGHBORHOOD']
        print(f"Processing: {business_name} in {neighborhood}")

        # Default location
        location = f"{neighborhood}, Philadelphia, PA"

        # Handle missing NEIGHBORHOOD values
        if pd.isna(neighborhood):
            print(f"Skipping {business_name} due to missing NEIGHBORHOOD.")
            return pd.Series({'BUSINESS': business_name, 'Yelp Alias': None})

        # Adjust location if NEIGHBORHOOD contains ' NJ'
        if ' NJ' in neighborhood:
            neighborhood = neighborhood.replace(',', '').replace(' NJ', '')
            location = f"{neighborhood}, NJ"

        print("Business Name:", business_name)
        print("Location:", location)
        print()
        try:
            # Perform Yelp search query
            search_response = yelp.search_query(
                term=business_name,
                location=location,
                limit=1
            )
            yelp_alias = search_response.get('businesses', [{}])[0].get('alias')
            print(f"Yelp Response for {business_name}: {yelp_alias}")
            business_data = search_response.get('businesses', [{}])[0]

            # Extract relevant fields from the Yelp response
            address = business_data.get('location', {})
            return pd.Series({
                'BUSINESS': business_name,
                'ADDRESS_STREET': address.get('address1', ''),
                'Yelp Alias': yelp_alias,
                'ADDRESS_CITY': address.get('city', ''),
                'ADDRESS_STATE': address.get('state', ''),
                'ADDRESS_ZIP': address.get('zip_code', ''),
                'Full Address': ', '.join(address.get('display_address', [])),
                'Latitude': business_data.get('coordinates', {}).get('latitude', None),
                'Longitude': business_data.get('coordinates', {}).get('longitude', None),
                'EVENT_TYPE': '',  # Default empty
                'BUSINESS_TAGS': '',  # Default empty
                'OCCURRENCE_TYPES': '',  # Default empty
                'ADDRESS_UNIT': '',  # Default empty
                'PRIZE_1_TYPE': '',  # Default empty
                'PRIZE_2_TYPE': '',  # Default empty
                'PRIZE_2_AMOUNT': '',  # Default empty
                'PRIZE_3_TYPE': '',  # Default empty
                'PRIZE_3_AMOUNT': ''  # Default empty
            })
            # return pd.Series({'BUSINESS': business_name, 'Yelp Alias': yelp_alias})
        except Exception as e:
            print(f"Error retrieving data for {business_name}: {e}")
            return pd.Series({
                'BUSINESS': business_name,
                'ADDRESS_STREET': None,
                'Yelp Alias': None,
                'ADDRESS_CITY': None,
                'ADDRESS_STATE': None,
                'ADDRESS_ZIP': None,
                'Full Address': None,
                'Latitude': None,
                'Longitude': None,
                'EVENT_TYPE': None,
                'BUSINESS_TAGS': None,
                'OCCURRENCE_TYPES': None,
                'ADDRESS_UNIT': None,
                'PRIZE_1_TYPE': None,
                'PRIZE_2_TYPE': None,
                'PRIZE_2_AMOUNT': None,
                'PRIZE_3_TYPE': None,
                'PRIZE_3_AMOUNT': None
            })

    # Apply the function to quizzo_yelp_df
    yelp_results = quizzo_yelp_df.apply(get_yelp_data, axis=1)

    # Load existing YelpAliases.csv if it exists, otherwise create a new DataFrame
    try:
        yelp_aliases = pd.read_csv("YelpAliases.csv")
    except FileNotFoundError:
        yelp_aliases = pd.DataFrame(columns=['BUSINESS', 'Yelp Alias'])

    # Append new results to the existing YelpAliases.csv
    yelp_aliases = pd.concat([yelp_aliases, yelp_results], ignore_index=True)
    # Drop duplicates based on Yelp Alias
    yelp_aliases.drop_duplicates(subset=['Yelp Alias'], inplace=True)

    # Save the updated YelpAliases.csv
    yelp_aliases.to_csv("YelpAliases.csv", index=False)

    print("Updated YelpAliases.csv with new data.")

quizzo_yelp_data()