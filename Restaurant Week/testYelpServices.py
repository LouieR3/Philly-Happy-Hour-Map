import requests

url = "https://api.yelp.com/v3/businesses/a-kitchen-philadelphia-4/service_offerings"

headers = {
    "accept": "application/json",
    "Authorization": "XEmkEwex5TbqjOitZJ8xtLXTBMQQb7BrtQdzzw-hJVWwnIUysCwCzXT2X2xsMbSXR7uHxWnRkyyFIh1CxfLr6Ilj_n-xClAG_h5aKabBtAjJLVnZ9mMfdKFWlMvPZHYx"
}

response = requests.get(url, headers=headers)

print(response.text)