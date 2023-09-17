import requests
import json
from yelpapi import YelpAPI
import yelpapi
import pandas as pd

# Backup backup API Key
yelpapiKey = "XEmkEwex5TbqjOitZJ8xtLXTBMQQb7BrtQdzzw-hJVWwnIUysCwCzXT2X2xsMbSXR7uHxWnRkyyFIh1CxfLr6Ilj_n-xClAG_h5aKabBtAjJLVnZ9mMfdKFWlMvPZHYx"

yelp = yelpapi.YelpAPI(yelpapiKey)


# List of business aliases 
aliases = ['1518-bar-and-grill-philadelphia', 'cavanaughs-rittenhouse-philadelphia-2']
alias = "a-kitchen-philadelphia-4"
response = yelp.business_query(id=alias) # type: ignore
print(response)

# Format the 'hours' field as a list of Mon-Sun with formatted dates
formatted_hours = [
    f"{day}: {time['start']} - {time['end']}"
    for day, time in enumerate(response['hours'][0]['open'])
]

# Replace 'hours' field with the formatted list
response['hours'] = formatted_hours

# Replace 'transactions' with a formatted string
formatted_transactions = ', '.join(response['transactions'])
response['transactions'] = formatted_transactions

# Create a responseFrame
df = pd.responseFrame([response]) # type: ignore

# Select the desired columns
df = df[['name', 'alias', 'hours', 'transactions']]

# Print the responseFrame
print(df)
# Search for business IDs
# business_ids = []
# for alias in aliases:
#   response = yelp.business_query(id=alias) # type: ignore
#   print(response)

# print(menu_response)