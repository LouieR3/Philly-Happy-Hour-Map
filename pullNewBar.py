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

# Get general pull of bars and restaurants in philly
Restaurants = yelp.search_query(location='Philadelphia', categories='Restaurants', limit=50)
# print(Restaurants)

# response = yelp.business_query(id="harp-and-crown-philadelphia") # type: ignore
# print(response)

# Load the Yelp Aliases CSV into a DataFrame
yelp_aliases_df = pd.read_csv('YelpAliases.csv')

# Check if they are in YelpAliases already
for restaurant in Restaurants["businesses"]:
    alias = restaurant['alias']
    name = restaurant['name']

    # Check if the alias is already in the Yelp Aliases DataFrame
    if alias not in yelp_aliases_df['Yelp Alias'].values:
        # If not, add a new row to the DataFrame
        new_row = {'Name': name, 'Yelp Alias': alias}
        yelp_aliases_df = yelp_aliases_df.append(new_row, ignore_index=True) # type: ignore


# Save the updated Yelp Aliases DataFrame back to the CSV file
yelp_aliases_df.to_csv('YelpAliases.csv', index=False)

# Print the updated Yelp Aliases DataFrame
print(yelp_aliases_df)

# If not:
#   Pull yelp api data
#   Pull the extra yelp data
#   Enter in nulls for RW and Sips data
#   Calculate scores or other fields