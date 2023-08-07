import pandas as pd
from yelpapi import YelpAPI
import yelpapi

# Actual API Key
# yelpapiKey = "DQx0YugiFJ5inYYp8fVvDqLx0R_dVo8yXxRZtpD5jkbNK0WmAqUygKIyXnYHlfL0pYRndGHGmuvn_QCXPVndRCc0VjtZzxCSHE8MhPthoJ4YUygg65DJrhMJLu7OZHYx"

# Backup API Key
# yelpapiKey = "r9ksNtdCcwK8MhsrL9fB5BvOGkC8Habi6-S5Shhh-Xu7CXF5xCBAPRCPS04atHegmf3BOMeW9gqNxA16E32gg4xDhcuWgD0k58m9jp280IpSb5zthhBCvmeXBsnPZHYx"

# Backup backup API Key
yelpapiKey = "XEmkEwex5TbqjOitZJ8xtLXTBMQQb7BrtQdzzw-hJVWwnIUysCwCzXT2X2xsMbSXR7uHxWnRkyyFIh1CxfLr6Ilj_n-xClAG_h5aKabBtAjJLVnZ9mMfdKFWlMvPZHYx"

yelp = yelpapi.YelpAPI(yelpapiKey)

# Assuming you have the DataFrame 'df' with the 'Deals' column
df = pd.read_csv('AllSipsLocations.csv')

def get_yelp_data(row):
    bar_name = row['Bar Name']
    print("--------------------------------------------")
    print(bar_name)
    address = row['Address']

    # Split the address into parts based on commas
    parts = address.split(', ')

    # Extract individual components
    street_address = parts[0]
    city = parts[1]
    state_zip = parts[2]

    # Split the state and ZIP code
    state, zipcode = state_zip.split(' ')

    website = row['Bar Website']

    # Use the Yelp API to search for the bar by its name and location (address)
    # response = yelp.business_query(name=bar_name, location=address) # type: ignore
    try:
        match_response = yelp.business_match_query(name=bar_name, address1=street_address, city=city, state=state, country='US', postal_code=zipcode) # type: ignore
        print(match_response)
        # yelp_id = match_response.get('businesses', [{}])[0].get('id')
        yelp_alias = match_response.get('businesses', [{}])[0].get('alias')
    except:
        print(f"Error retrieving data for {bar_name}")
        yelp_data = {
            'Bar Name': bar_name,
            'Rating': None,
            'Review Count': None,
            'Price': None,
            'Yelp URL': None,
            'Categories': None,
            'Website': website
            # Add more Yelp data as needed
        }
        return yelp_data
