import requests
import json

# API key and endpoint
API_KEY = "XEmkEwex5TbqjOitZJ8xtLXTBMQQb7BrtQdzzw-hJVWwnIUysCwCzXT2X2xsMbSXR7uHxWnRkyyFIh1CxfLr6Ilj_n-xClAG_h5aKabBtAjJLVnZ9mMfdKFWlMvPZHYx"

API_HOST = 'https://api.yelp.com'
SEARCH_PATH = '/v3/businesses/matches' 
MENU_PATH = '/v3/businesses/{id}/menu'

# List of business aliases 
aliases = ['1518-bar-and-grill-philadelphia', 'cavanaughs-rittenhouse-philadelphia-2']

# Search for business IDs
business_ids = []
for alias in aliases:
    search_url = f"{API_HOST}{SEARCH_PATH}?name={alias}"

    response = requests.get(search_url, 
                            headers={'Authorization': f'Bearer {API_KEY}'})
    print(response)
    business = response.json()[0]
    business_ids.append(business['id'])

# Get menu data
menu_data = []  
for business_id in business_ids:

  menu_url = API_HOST + MENU_PATH.format(id=business_id)
  
  response = requests.get(menu_url, 
                          headers={'Authorization': f'Bearer {API_KEY}'})
                          
  menu = response.json()
  menu_data.append(menu)

print(menu_data)