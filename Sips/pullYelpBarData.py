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

# bars = yelp.search_query(location='Philadelphia', categories='bars')
# print(bars)

# Function to get Yelp data for each bar
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

    print(yelp_alias)
    print()
    response = yelp.business_query(id=yelp_alias) # type: ignore
    print(response)

    # Extract categories from the details_response
    categories = [category['title'] for category in response.get('categories', [])]
    # Extract relevant data from the Yelp response (customize based on your needs)
    yelp_data = {
        'Bar Name': bar_name,
        'Rating': response.get('rating'),
        'Review Count': response.get('review_count'),
        'Price': response.get('price'),
        # 'Yelp URL': response.get('url'),
        'Categories': categories,
        'Website': website
        # Add more Yelp data as needed
    }
    return yelp_data

# Create a new DataFrame to store the Yelp data
data = df.apply(get_yelp_data, axis=1)
yelp_df = pd.DataFrame(data)
# Display the Yelp data DataFrame
print(yelp_df)
yelp_df.to_csv('Yelp.csv', index=False)

# Merge the two DataFrames on the 'Bar Name' column
combined_df = df.merge(yelp_df, on='Bar Name', how='left')

# Update the desired columns in df with data from yelp_df
combined_df['Rating'] = combined_df['Rating_y']
combined_df['Review Count'] = combined_df['Review Count_y']
combined_df['Price'] = combined_df['Price_y']
combined_df['Categories'] = combined_df['Categories_y']

# Drop the unnecessary columns from the combined DataFrame
combined_df = combined_df.drop(columns=['Rating_y', 'Review Count_y', 'Price_y', 'Categories_y'])

# Save the combined DataFrame to a new CSV file 'Test.csv'
combined_df.to_csv('Test.csv', index=False)

# Display the updated DataFrame
print(combined_df)


# # Replace newlines with newline characters '\n' in the 'Deals' column
# # df['Deals'] = df['Deals'].str.replace('\\n', ' ')
# for index, row in df.iterrows():
#     deals_parts = row['Deals'].split('\n')
#     # Loop through the deals parts and apply bold to specific lines
#     for deal in deals_parts:
#         print(deal.strip())
#         print(deal)
#         if deal.strip() in ['$7 Cocktails', '$6 Wine', '$5 Beer', 'Half-Priced Appetizers']:
#             popup_content = f"<p style='text-align: center; font-weight: bold;'>{deal}</p>"
#         else:
#             popup_content = f"<p style='text-align: center;'>{deal}</p>"
#         print(popup_content)
#         print()

# Save the updated DataFrame back to the CSV file
# df.to_csv('Test2.csv', index=False)