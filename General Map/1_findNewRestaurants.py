import pandas as pd
from yelpapi import YelpAPI
import yelpapi
import requests
import json
import html
import re
from bs4 import BeautifulSoup
import time

# ------------------------------------------------
# This script does = Gets the information from each Restaurant from yelp
# ------------------------------------------------
start_time = time.time()
# Actual API Key
# yelpapiKey = "DQx0YugiFJ5inYYp8fVvDqLx0R_dVo8yXxRZtpD5jkbNK0WmAqUygKIyXnYHlfL0pYRndGHGmuvn_QCXPVndRCc0VjtZzxCSHE8MhPthoJ4YUygg65DJrhMJLu7OZHYx"

# Backup API Key
# yelpapiKey = "r9ksNtdCcwK8MhsrL9fB5BvOGkC8Habi6-S5Shhh-Xu7CXF5xCBAPRCPS04atHegmf3BOMeW9gqNxA16E32gg4xDhcuWgD0k58m9jp280IpSb5zthhBCvmeXBsnPZHYx"

# Backup backup API Key
yelpapiKey = "XEmkEwex5TbqjOitZJ8xtLXTBMQQb7BrtQdzzw-hJVWwnIUysCwCzXT2X2xsMbSXR7uHxWnRkyyFIh1CxfLr6Ilj_n-xClAG_h5aKabBtAjJLVnZ9mMfdKFWlMvPZHYx"

yelp = yelpapi.YelpAPI(yelpapiKey)

def checkMasterForAlias():
    # Define a function to get Yelp data
    def get_yelp_data(row):
        restaurant_name = row['Restaurant Name']
        print("--------------------------------------------")
        print(restaurant_name)
        address = row['Address']

        # Split the address into parts based on commas
        parts = address.split(', ')

        # Extract individual components
        street_address = parts[0]
        city = parts[1]
        state_zip = parts[2]

        # Split the state and ZIP code
        state, zipcode = state_zip.split(' ')

        # Use the Yelp API to search for the Restaurant by its name and location (address)
        # response = yelp.business_query(name=restaurant_name, location=address) # type: ignore
        try:
            match_response = yelp.business_match_query(name=restaurant_name, address1=street_address, city=city, state=state, country='US', postal_code=zipcode) # type: ignore
            print(match_response)
            # yelp_id = match_response.get('businesses', [{}])[0].get('id')
            yelp_alias = match_response.get('businesses', [{}])[0].get('alias')
            
            return yelp_alias
        except:
            print(f"Error retrieving data for {restaurant_name}")
            return None
        
    # Load the Yelp Aliases CSV into a DataFrame
    yelp_aliases_df = pd.read_csv('YelpAliases.csv')

    # Load the MasterTable from the original CSV
    master_table_df = pd.read_csv('../Csv/MasterTable.csv')

    # Convert all relevant columns to lowercase to ensure consistent comparison
    yelp_aliases_df['Name'] = yelp_aliases_df['Name'].str.lower()
    master_table_df['Name'] = master_table_df['Name'].str.lower()
    master_table_df['Address'] = master_table_df['Address'].str.lower()

    # Find bars in MasterTable not in Yelp Aliases CSV
    missing_bars_df = master_table_df[~master_table_df['Name'].isin(yelp_aliases_df['Name'])]
    print(missing_bars_df)
    data = missing_bars_df.apply(get_yelp_data, axis=1) # type: ignore

# Get general pull of bars and restaurants in philly
Restaurants = yelp.search_query(location='Rittenhouse Square, Philadelphia', price=2, categories='Bars', limit=50)
# Restaurants = yelp.search_query(location='Gayborhood, Philadelphia', price=2, categories='Bars', limit=50)
# Restaurants = yelp.search_query(location='Grad Hospital, Philadelphia', price=2, categories='Bars', limit=50)
# Restaurants = yelp.search_query(location='Reading Terminal, Philadelphia', price=2, categories='Bars', limit=50)
# Restaurants = yelp.search_query(location='Italian Market, Philadelphia', price=2, categories='Bars', limit=50)
# Restaurants = yelp.search_query(location='Passyunk, Philadelphia', price=2, categories='Bars', limit=50)
# Restaurants = yelp.search_query(location='Queen Village, Philadelphia', price=2, categories='Bars', limit=50)
# Restaurants = yelp.search_query(location='Point Breeze, Philadelphia', price=2, categories='Bars', limit=50)
# Restaurants = yelp.search_query(location='Grays Ferry, Philadelphia', price=2, categories='Bars', limit=50)
# Restaurants = yelp.search_query(location='Center City, Philadelphia', price=2, categories='Bars', limit=50)
# Restaurants = yelp.search_query(location='Old City, Philadelphia', price=2, categories='Bars', limit=50)
# Restaurants = yelp.search_query(location='Northern Liberties, Philadelphia', price=2, categories='Bars', limit=50)
# Restaurants = yelp.search_query(location='Fishtown, Philadelphia', price=2, categories='Bars', limit=50)
# Restaurants = yelp.search_query(location='South Philly, Philadelphia', price=2, categories='Bars', limit=50)
# Restaurants = yelp.search_query(location='Fairmount, Philadelphia', price=2, categories='Bars', limit=50)
# Restaurants = yelp.search_query(location='Chinatown, Philadelphia', price=2, categories='Bars', limit=50)
# Restaurants = yelp.search_query(location='University City, Philadelphia', price=2, categories='Bars', limit=50)
# Restaurants = yelp.search_query(location='Temple, Philadelphia', price=2, categories='Bars', limit=50)
# Restaurants = yelp.search_query(location='Port Richmond, Philadelphia', price=2, categories='Bars', limit=50)

# Load the Yelp Aliases CSV into a DataFrame
yelp_aliases_df = pd.read_csv('YelpAliases.csv')

# Check if they are in YelpAliases already
for restaurant in Restaurants["businesses"]:
    alias = restaurant['alias']
    name = restaurant['name']

    # Check if the alias is already in the Yelp Aliases DataFrame
    # print(name)
    # print(name in yelp_aliases_df['Name'].values)
    # print()
    if alias not in yelp_aliases_df['Yelp Alias'].values:
        print(name)
        # If not, add a new row to the DataFrame
        new_row = {'Name': name, 'Yelp Alias': alias}
        new_row_df = pd.DataFrame([new_row])
        yelp_aliases_df = pd.concat([yelp_aliases_df, new_row_df], ignore_index=True)

        # yelp_aliases_df = yelp_aliases_df.append(new_row, ignore_index=True) # type: ignore

# Save the updated Yelp Aliases DataFrame back to the CSV file
yelp_aliases_df.to_csv('YelpAliases.csv', index=False)

# Print the updated Yelp Aliases DataFrame
print(yelp_aliases_df)

# # Get Yelp data for the missing bars and add it to the missing_bars_df
# for index, row in missing_bars_df.iterrows():
#     yelp_data = get_yelp_data(row)
#     missing_bars_df.at[index, 'Yelp Alias'] = yelp_data['Yelp Alias']

# # Append the missing bars' data to the Yelp Aliases CSV
# missing_bars_df.to_csv('YelpAliases.csv', mode='a', header=False, index=False)

# # Print the DataFrame with missing bars and their Yelp Aliases
# print(missing_bars_df)

print("Progam finished --- %s seconds ---" % (time.time() - start_time))
