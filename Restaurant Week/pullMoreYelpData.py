import pandas as pd
from yelpapi import YelpAPI
import yelpapi
import requests
import json
import html
import re
from bs4 import BeautifulSoup
import time

# ------------------------------------------------
# This script does = Gets the information from each Restaurant from yelp
# ------------------------------------------------
start_time = time.time()
# Actual API Key
# yelpapiKey = "DQx0YugiFJ5inYYp8fVvDqLx0R_dVo8yXxRZtpD5jkbNK0WmAqUygKIyXnYHlfL0pYRndGHGmuvn_QCXPVndRCc0VjtZzxCSHE8MhPthoJ4YUygg65DJrhMJLu7OZHYx"

# Backup API Key
# yelpapiKey = "r9ksNtdCcwK8MhsrL9fB5BvOGkC8Habi6-S5Shhh-Xu7CXF5xCBAPRCPS04atHegmf3BOMeW9gqNxA16E32gg4xDhcuWgD0k58m9jp280IpSb5zthhBCvmeXBsnPZHYx"

# Backup backup API Key
yelpapiKey = "XEmkEwex5TbqjOitZJ8xtLXTBMQQb7BrtQdzzw-hJVWwnIUysCwCzXT2X2xsMbSXR7uHxWnRkyyFIh1CxfLr6Ilj_n-xClAG_h5aKabBtAjJLVnZ9mMfdKFWlMvPZHYx"

yelp = yelpapi.YelpAPI(yelpapiKey)

# Assuming you have the DataFrame 'df' with the 'Deals' column
df = pd.read_csv('YelpAliases.csv')
base_url = "https://www.yelp.com/biz/"
# Restaurants = yelp.search_query(location='Philadelphia', categories='Restaurants')
# print(Restaurants)

data_list = []

for index, row in df.iterrows():
    restaurant_name = row['Name']
    print("--------------------------------------------")
    print(restaurant_name)

    yelp_alias = row['Yelp Alias']
    print(yelp_alias)
    print()
    # response = yelp.business_query(id=yelp_alias) # type: ignore
    # print(response)
    url = base_url + yelp_alias
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
        "Name": restaurant_name,
        **business_properties,
        "Neighborhoods": neighborhoods_json,
        "Yelp Rating": rating,
        **hours_properties
    }
    data_list.append(df_data)

# Create a new DataFrame to store the Yelp data
yelp_df = pd.DataFrame(data_list)

# Convert 'Review Count' to int
# yelp_df['Review Count'] = yelp_df['Review Count'].fillna(0)
# yelp_df['Review Count'] = yelp_df['Review Count'].astype(int)
# Display the Yelp data DataFrame
print(yelp_df)
yelp_df.to_csv('ExtraYelp2.csv', index=False)

# Drop the unnecessary columns from the combined DataFrame
# combined_df = combined_df.drop(columns=['Rating_y', 'Review Count_y', 'Price_y', 'Categories_y'])
# combined_df['Review Count'] = combined_df['Review Count'].fillna(0)
# combined_df['Review Count'] = combined_df['Review Count'].astype(int)
# combined_df = combined_df.drop(columns=['Website']) 
# # Save the combined DataFrame to a new CSV file 'Test.csv'
# combined_df.to_csv('Test.csv', index=False)

# # Display the updated DataFrame
# print(combined_df)
print("--- %s seconds ---" % (time.time() - start_time))