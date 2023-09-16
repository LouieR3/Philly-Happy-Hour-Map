import requests
import json
from yelpapi import YelpAPI
import yelpapi

# Backup backup API Key
yelpapiKey = "XEmkEwex5TbqjOitZJ8xtLXTBMQQb7BrtQdzzw-hJVWwnIUysCwCzXT2X2xsMbSXR7uHxWnRkyyFIh1CxfLr6Ilj_n-xClAG_h5aKabBtAjJLVnZ9mMfdKFWlMvPZHYx"

yelp = yelpapi.YelpAPI(yelpapiKey)


# List of business aliases 
aliases = ['1518-bar-and-grill-philadelphia', 'cavanaughs-rittenhouse-philadelphia-2']

# Search for business IDs
business_ids = []
for alias in aliases:
  response = yelp.business_query(id=alias) # type: ignore
  print(response)

# print(menu_data)