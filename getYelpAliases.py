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

# Load the Yelp Aliases CSV into a DataFrame
yelp_aliases_df = pd.read_csv('YelpAliases.csv')

# Load the MasterTable from the original CSV
master_table_df = pd.read_csv('MasterTable.csv')

# Convert all relevant columns to lowercase to ensure consistent comparison
yelp_aliases_df['Name'] = yelp_aliases_df['Name'].str.lower()
master_table_df['Name'] = master_table_df['Name'].str.lower()
master_table_df['Address'] = master_table_df['Address'].str.lower()

# Find bars in MasterTable not in Yelp Aliases CSV
missing_bars_df = master_table_df[~master_table_df['Name'].isin(yelp_aliases_df['Name'])]
print(missing_bars_df)
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

# data = missing_bars_df.apply(get_yelp_data, axis=1)

# # Get Yelp data for the missing bars and add it to the missing_bars_df
# for index, row in missing_bars_df.iterrows():
#     yelp_data = get_yelp_data(row)
#     missing_bars_df.at[index, 'Yelp Alias'] = yelp_data['Yelp Alias']

# # Append the missing bars' data to the Yelp Aliases CSV
# missing_bars_df.to_csv('YelpAliases.csv', mode='a', header=False, index=False)

# # Print the DataFrame with missing bars and their Yelp Aliases
# print(missing_bars_df)