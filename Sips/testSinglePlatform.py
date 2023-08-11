# import requests
# import hashlib
# import hmac
# import urllib.parse
# import base64

# # Replace these with your actual values
# client_id = "cn3l4kmhdcxejosjf6chfjoiq"
# signing_key = "QRFYeaX2m4gGlsmG-B5sqhS4DQS3wwpC-QupqYaxBoU"
# resource_path = "/locations/test-pizzeria/actions/"
# url_parameters = "type=foodordering"
# client_param = f"client={client_id}"

# # Construct the signature base string
# base_string = f"{resource_path}?{url_parameters}&{client_param}"

# # Calculate the signature
# hashed = hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1)
# signature = base64.b64encode(hashed.digest()).decode()

# # Percent-encode the signature
# encoded_signature = urllib.parse.quote(signature, safe='')

# # Construct the final URL
# final_url = f"http://singleapi.com{base_string}&signature={encoded_signature}"

# print(final_url)

# response = requests.get(final_url, params='type=foodordering')
# print(response)
# if response.status_code == 200:
#     print(response.json())
# else:
#     print(None)

import requests

# Constructed URL from the previous step
constructed_url = "http://singleapi.com/locations/test-pizzeria/actions/?type=foodordering&client=cn3l4kmhdcxejosjf6chfjoiq&signature=cuP%2BjQO57X7E1rCT%2BvEoKxN2LNg%3D"

# Send a GET request to the constructed URL
response = requests.get(constructed_url)

# Check if the request was successful
if response.status_code == 200:
    data = response.json()
    print(data)
else:
    print(f"Request failed with status code: {response.status_code}")