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

# Read the CSV file into a DataFrame
df = pd.read_csv('AllSipsLocations.csv')

# Function to get Yelp data for each bar and return the Yelp Alias
def get_yelp_data(row):
    bar_name = row['Bar Name']
    address = row['Address']

    # Split the address into parts based on commas
    parts = address.split(', ')

    # Extract individual components
    street_address = parts[0]
    city = parts[1]
    state_zip = parts[2]

    # Split the state and ZIP code
    state, zipcode = state_zip.split(' ')

    # Use the Yelp API to search for the bar by its name and location (address)
    try:
        match_response = yelp.business_match_query(name=bar_name, address1=street_address, city=city, state=state, country='US', postal_code=zipcode)
        yelp_alias = match_response.get('businesses', [{}])[0].get('alias')
        return yelp_alias
    except Exception as e:
        # If there is an error fetching the Yelp Alias, return None
        return None

# Apply the function to each row in the DataFrame to get the Yelp Alias
df['Yelp Alias'] = df.apply(get_yelp_data, axis=1)

# Save the updated DataFrame to a new CSV file
df.to_csv('AllSipsLocations2.csv', index=False)