import pandas as pd
from yelpapi import YelpAPI
import yelpapi

# ------------------------------------------------
# This script does = Gets the information from each Restaurant from yelp
# ------------------------------------------------

# Actual API Key
# yelpapiKey = "DQx0YugiFJ5inYYp8fVvDqLx0R_dVo8yXxRZtpD5jkbNK0WmAqUygKIyXnYHlfL0pYRndGHGmuvn_QCXPVndRCc0VjtZzxCSHE8MhPthoJ4YUygg65DJrhMJLu7OZHYx"

# Backup API Key
# yelpapiKey = "r9ksNtdCcwK8MhsrL9fB5BvOGkC8Habi6-S5Shhh-Xu7CXF5xCBAPRCPS04atHegmf3BOMeW9gqNxA16E32gg4xDhcuWgD0k58m9jp280IpSb5zthhBCvmeXBsnPZHYx"

# Backup backup API Key
yelpapiKey = "XEmkEwex5TbqjOitZJ8xtLXTBMQQb7BrtQdzzw-hJVWwnIUysCwCzXT2X2xsMbSXR7uHxWnRkyyFIh1CxfLr6Ilj_n-xClAG_h5aKabBtAjJLVnZ9mMfdKFWlMvPZHYx"

yelp = yelpapi.YelpAPI(yelpapiKey)

# Assuming you have the DataFrame 'df' with the 'Deals' column
df = pd.read_csv('MasterTable.csv')

# Restaurants = yelp.search_query(location='Philadelphia', categories='Restaurants')
# print(Restaurants)

# Function to get Yelp data for each Restaurant
def get_yelp_data(row):
    restaurant_name = row['Name']
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

    try:
        match_response = yelp.business_match_query(name=restaurant_name, address1=street_address, city=city, state=state, country='US', postal_code=zipcode)
        print(match_response)
        yelp_alias = match_response.get('businesses', [{}])[0].get('alias')
        return pd.Series({'Name': restaurant_name, 'Yelp Alias': yelp_alias})
    except:
        print(f"Error retrieving data for {restaurant_name}")
        return pd.Series({'Name': restaurant_name, 'Yelp Alias': None})

# Create a new dataframe from df with 'Name' and 'Yelp Alias' columns
yelp_df = df.apply(get_yelp_data, axis=1)

# Print the resulting Yelp dataframe
print(yelp_df)
yelp_df.to_csv("YelpAliases.csv", index=False)