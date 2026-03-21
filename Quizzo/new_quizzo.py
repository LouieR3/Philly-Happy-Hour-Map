import numpy as np
import pandas as pd
from geopy.geocoders import Nominatim
import folium
from folium import IFrame
# from folium.utilities import JsCode
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
import pandas as pd

def initial_cleanup(quizzo_list):
    # Read the Excel file

    # Rename the second column to 'Bar'
    quizzo_list.rename(columns={'Last updated 4/27/25': 'Bar'}, inplace=True)

    # Keep only columns up to 'Theme' (9th column) and drop 'id'
    quizzo_list = quizzo_list.iloc[:, 1:9]

    # Drop rows that are fully NaN
    quizzo_list = quizzo_list.dropna(how='all')

    # Remove rows after "To be confirmed"
    to_be_confirmed_idx = quizzo_list[quizzo_list['Bar'] == 'To be confirmed'].index
    if len(to_be_confirmed_idx) > 0:
        quizzo_list = quizzo_list[:to_be_confirmed_idx[0]]

    # Convert time from 24-hour to 12-hour format
    def convert_time(time_str):
        if pd.isna(time_str) or time_str == '':
            return ''
        try:
            # Handle time objects and strings
            if hasattr(time_str, 'hour'):
                # It's a time object
                return time_str.strftime('%I:%M %p').lstrip('0')
            else:
                # It's a string
                time_obj = pd.to_datetime(str(time_str), format='%H:%M:%S').time()
                return time_obj.strftime('%I:%M %p').lstrip('0')
        except Exception as e:
            return str(time_str)

    quizzo_list['Time'] = quizzo_list['Time'].apply(convert_time)

    # Ensure Time column is string type
    quizzo_list['Time'] = quizzo_list['Time'].astype(str)


    # Process Day column - remove anything after and including space
    quizzo_list['Day'] = quizzo_list['Day'].str.split(' ').str[0]

    # Process Theme column - convert to MUSIC_QUIZZO or QUIZZO
    quizzo_list['Theme'] = quizzo_list['Theme'].apply(
        lambda x: 'MUSIC_QUIZZO' if pd.notna(x) and str(x).strip().upper() == 'MUSIC' else 'QUIZZO'
    )

    # Helper function to handle suburb addresses
    def handle_suburb_address(row):
        if pd.isna(row['Address']) or row['Address'] == '':
            neighborhood = str(row['Neighborhood']).upper().strip() if pd.notna(row['Neighborhood']) and row['Neighborhood'] != '' else ''
            if neighborhood == '':
                return ''
            if 'NJ' in neighborhood:
                return neighborhood.replace(',', '')
            elif 'DE' in neighborhood:
                return neighborhood.replace(',', '')
            else:
                return f"{neighborhood}, PA"
        return row['Address']

    # Find the index of "Suburbs and New Jersey" row
    suburbs_idx = quizzo_list[quizzo_list['Bar'] == 'Suburbs and New Jersey'].index
    if len(suburbs_idx) > 0:
        suburbs_idx = suburbs_idx[0]
        
        # Process rows before "Suburbs and New Jersey" (Philadelphia)
        philly_data = quizzo_list[:suburbs_idx].copy()
        philly_data['Address'] = philly_data.apply(
            lambda row: f"{row['Neighborhood'].upper()}, PHILADELPHIA, PA" 
            if (pd.notna(row['Neighborhood']) and row['Neighborhood'] != '' and (pd.isna(row['Address']) or row['Address'] == ''))
            else (
                f"{row['Address']}, PHILADELPHIA, PA"
                if (pd.notna(row['Address']) and row['Address'] != '' and 'PHILADELPHIA' not in str(row['Address']).upper())
                else row['Address']
            ),
            axis=1
        )
        
        # Process rows after "Suburbs and New Jersey"
        suburb_data = quizzo_list[suburbs_idx+1:].copy()
        suburb_data['Address'] = suburb_data.apply(handle_suburb_address, axis=1)
        
        # Combine both datasets
        quizzo_list = pd.concat([philly_data, suburb_data], ignore_index=True)
    else:
        # If no "Suburbs and New Jersey" row, apply Philadelphia logic to all
        quizzo_list['Address'] = quizzo_list.apply(
            lambda row: f"{row['Neighborhood'].upper()}, PHILADELPHIA, PA" 
            if (pd.notna(row['Neighborhood']) and row['Neighborhood'] != '' and (pd.isna(row['Address']) or row['Address'] == ''))
            else row['Address'],
            axis=1
        )

    # Apply upper case to all columns except Theme
    for col in quizzo_list.columns:
        if col != 'Theme':
            quizzo_list[col] = quizzo_list[col].apply(
                lambda x: str(x).upper().strip() if pd.notna(x) and x != '' else ''
            )

    # Remove the "Suburbs and New Jersey" row
    quizzo_list = quizzo_list[quizzo_list['Bar'] != 'SUBURBS AND NEW JERSEY']

    # Save the cleaned DataFrame to a new file
    quizzo_list.to_csv('Quizzo/cleaned_quizzo_list.csv', index=False)

    # Print the cleaned DataFrame
    print(quizzo_list)

def update_quizzo_list(quizzo_list, quizzo_list_to_add):
    # Normalize BUSINESS column for comparison
    quizzo_list['BUSINESS_NORM'] = quizzo_list['BUSINESS'].str.upper().str.strip()
    quizzo_list_to_add['BUSINESS_NORM'] = quizzo_list_to_add['BUSINESS'].str.upper().str.strip()

    # Merge on BUSINESS to update TIME and WEEKDAY
    merged = quizzo_list.merge(
        quizzo_list_to_add[['BUSINESS_NORM', 'TIME', 'WEEKDAY']],
        on='BUSINESS_NORM',
        how='left',
        suffixes=('', '_new')
    )

    # Update TIME and WEEKDAY where they exist in quizzo_list_to_add
    quizzo_list['TIME'] = merged['TIME_new'].combine_first(merged['TIME'])
    quizzo_list['WEEKDAY'] = merged['WEEKDAY_new'].combine_first(merged['WEEKDAY'])

    # Find records in quizzo_list_to_add not in quizzo_list
    print("\n" + "="*80)
    print("RECORDS IN QUIZZO_LIST_TO_ADD NOT IN QUIZZO_LIST (will be ADDED):")
    print("="*80)
    unmatched_to_add = quizzo_list_to_add[~quizzo_list_to_add['BUSINESS_NORM'].isin(quizzo_list['BUSINESS_NORM'])]
    if not unmatched_to_add.empty:
        print(unmatched_to_add[['BUSINESS', 'NEIGHBORHOOD', 'TIME', 'WEEKDAY']].to_string())
    else:
        print("None found.")
    print(len(unmatched_to_add), "records to be added.")

    # Find records in quizzo_list not in quizzo_list_to_add
    print("\n" + "="*80)
    print("RECORDS IN QUIZZO_LIST NOT IN QUIZZO_LIST_TO_ADD (will be REMOVED):")
    print("="*80)
    unmatched_list = quizzo_list[~quizzo_list['BUSINESS_NORM'].isin(quizzo_list_to_add['BUSINESS_NORM'])]
    if not unmatched_list.empty:
        print(unmatched_list[['BUSINESS', 'NEIGHBORHOOD', 'TIME', 'WEEKDAY']].to_string())
    else:
        print("None found.")
    print(len(unmatched_list), "records to be removed.")

    # Remove records not found in quizzo_list_to_add
    quizzo_list = quizzo_list[quizzo_list['BUSINESS_NORM'].isin(quizzo_list_to_add['BUSINESS_NORM'])]

    # Add records from quizzo_list_to_add not already in quizzo_list
    quizzo_list = pd.concat([quizzo_list, unmatched_to_add], ignore_index=True)

    # Drop normalized columns
    quizzo_list.drop(columns=['BUSINESS_NORM'], inplace=True)
    quizzo_list_to_add.drop(columns=['BUSINESS_NORM'], inplace=True)

    return quizzo_list

def merge_master(master_table, updated_quizzo_list):

    # Normalize master_table Name for matching
    master_table['BUSINESS_NORM'] = master_table['Name'].str.upper().str.strip()
 
    # Only look up rows missing Latitude or Longitude
    missing_mask = updated_quizzo_list['Latitude'].isna() | updated_quizzo_list['Longitude'].isna()
 
    # Merge missing rows against master_table on normalized name
    missing = updated_quizzo_list[missing_mask].copy()
    print(missing)
    missing['BUSINESS_NORM'] = missing['BUSINESS'].str.upper().str.strip()
 
    filled = missing.merge(
        master_table[['BUSINESS_NORM', 'Latitude', 'Longitude']],
        on='BUSINESS_NORM',
        how='left',
        suffixes=('', '_master')
    )
 
    # Fill Latitude/Longitude from master_table where still missing
    filled['Latitude'] = filled['Latitude'].combine_first(filled['Latitude_master'])
    filled['Longitude'] = filled['Longitude'].combine_first(filled['Longitude_master'])
    filled.drop(columns=['BUSINESS_NORM', 'Latitude_master', 'Longitude_master'], inplace=True)
    print(filled)
    print(f"\nFilled coordinates for {missing_mask.sum() - filled['Latitude'].isna().sum()} rows using master_table.")
 
    # Write filled rows back into updated_quizzo_list
    updated_quizzo_list.loc[missing_mask] = filled.values
 
    master_table.drop(columns=['BUSINESS_NORM'], inplace=True)
 
    print(f"\n{missing_mask.sum()} rows were missing coordinates.")
    still_missing = updated_quizzo_list['Latitude'].isna() | updated_quizzo_list['Longitude'].isna()
    print(f"{still_missing.sum()} rows still missing after master_table lookup:")
    print(updated_quizzo_list[still_missing][['BUSINESS', 'Latitude', 'Longitude']])
    updated_quizzo_list.to_csv('public/quizzo_list_updated.csv', index=False)

def main():
    # STEP 1
    # quizzo_list = pd.read_excel('Quizzo/The Quizzo List.xlsx', header=1)
    # initial_cleanup(quizzo_list)

    # STEP 2
    # Load the data
    quizzo_list = pd.read_csv('public/quizzo_list.csv')
    quizzo_list_to_add = pd.read_csv('Quizzo/cleaned_quizzo_list.csv')
    master_table = pd.read_csv('Csv/MasterTable.csv')

    # STEP 2
    # updated_quizzo_list = update_quizzo_list(quizzo_list, quizzo_list_to_add)
    # # Save the updated quizzo_list
    # updated_quizzo_list.to_csv('public/quizzo_list_updated.csv', index=False)

    updated_quizzo_list = pd.read_csv('public/quizzo_list_updated.csv')

    # STEP 3
    merge_master(master_table, updated_quizzo_list)

if __name__ == '__main__':
    main()