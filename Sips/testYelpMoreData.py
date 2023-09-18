import requests
import json
from yelpapi import YelpAPI
import yelpapi
import pandas as pd
from bs4 import BeautifulSoup
import re
# Backup backup API Key
yelpapiKey = "XEmkEwex5TbqjOitZJ8xtLXTBMQQb7BrtQdzzw-hJVWwnIUysCwCzXT2X2xsMbSXR7uHxWnRkyyFIh1CxfLr6Ilj_n-xClAG_h5aKabBtAjJLVnZ9mMfdKFWlMvPZHYx"

yelp = yelpapi.YelpAPI(yelpapiKey)


# List of business aliases 
aliases = ['1518-bar-and-grill-philadelphia', 'cavanaughs-rittenhouse-philadelphia-2']
alias = "veda-modern-indian-bistro-philadelphia-3"
alias = "amada-philadelphia"
alias = "chubby-cattle-philadelphia-5"
# alias = "bistro-romano-philadelphia"

base_url = "https://www.yelp.com/biz/"
url = base_url + alias
response = requests.get(url)
html = response.text

# Parse HTML with BeautifulSoup  
soup = BeautifulSoup(html, "html.parser")

# Find the <script> tag
script_tag = soup.find("script", {"data-apollo-state": True})
# Extract JSON string 
json_str = script_tag.text # type: ignore
# Remove <!-- and -->
cleaned = json_str[4:-3]
# Add outer quotes
json_str = re.sub(r'&quot;', '"', cleaned)

# Parse the JSON string into a Python object
json_object = json.loads(json_str)

# Find business properties without specifying "encid"
business_properties = {}
for key, value in json_object.items():
    if isinstance(value, dict) and "displayText" in value:
        # Store in business_properties
        display_text = value["displayText"]
        is_active = value["isActive"]
        if "&amp;" in display_text:
            display_text = display_text.replace("&amp;", "and")

        if "Not Good" in display_text:
            display_text = display_text.replace("Not Good", "Good")
            is_active = not is_active

        if "No " in display_text:
            display_text = display_text.replace("No ", "")
            is_active = not is_active

        # Check if "Best nights on" is present
        if "Best nights on" in display_text:
            # Split by "Best nights on " and then split by comma
            parts = display_text.split("Best nights on ")[1].split(',')
            for part in parts:
                # Construct the new display text with the day and is_active value
                new_display_text = "Best nights on " + part.strip()
                business_properties[new_display_text] = is_active
        else:
            display_texts = [text.strip() for text in display_text.split(',')]
            for text in display_texts:
                business_properties[text] = is_active
        # business_properties[display_text] = is_active
# print(business_properties)
for key, value in business_properties.items():
    print(key, ":", value)
neighborhoods_json = None
for key, value in json_object.items():
    if isinstance(value, dict) and "neighborhoods" in value:
        neighborhoods_json = value["neighborhoods"].get("json", [])
        break

rating = None
for key, value in json_object.items():
    if isinstance(value, dict) and "rating" in value:
        rating = value["rating"]
        break

hours_properties = {}
for key, value in json_object.items():
    if isinstance(value, dict) and "regularHours" in value and "dayOfWeekShort" in value:
        Hours = value["regularHours"].get("json", [])[0]
        day = value["dayOfWeekShort"]
        if day == "Mon":
            day += "day"
        elif day == "Tue":
            day += "sday"
        elif day == "Wed":
            day += "nesday"
        elif day == "Thu":
            day += "rsday"
        elif day == "Fri":
            day += "day"
        elif day == "Sat":
            day += "urday"
        elif day == "Sun":
            day += "day"
        hours_properties[day] = Hours

df_data = {
    "Name": alias,
    **business_properties,
    "Neighborhoods": neighborhoods_json,
    "Rating": rating,
    **hours_properties
}
print(df_data)




# response = yelp.business_query(id=alias) # type: ignore
# print(response)

# # Format the 'hours' field as a list of Mon-Sun with formatted dates
# formatted_hours = [
#     f"{day}: {time['start']} - {time['end']}"
#     for day, time in enumerate(response['hours'][0]['open'])
# ]

# # Replace 'hours' field with the formatted list
# response['hours'] = formatted_hours

# # Replace 'transactions' with a formatted string
# formatted_transactions = ', '.join(response['transactions'])
# response['transactions'] = formatted_transactions

# # Create a responseFrame
# df = pd.responseFrame([response]) # type: ignore

# # Select the desired columns
# df = df[['name', 'alias', 'hours', 'transactions']]

# # Print the responseFrame
# print(df)
# # Search for business IDs
# business_ids = []
# for alias in aliases:
#   response = yelp.business_query(id=alias) # type: ignore
#   print(response)
