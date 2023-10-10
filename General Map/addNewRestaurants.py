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
yelpapiKey = "r9ksNtdCcwK8MhsrL9fB5BvOGkC8Habi6-S5Shhh-Xu7CXF5xCBAPRCPS04atHegmf3BOMeW9gqNxA16E32gg4xDhcuWgD0k58m9jp280IpSb5zthhBCvmeXBsnPZHYx"

# Backup backup API Key
# yelpapiKey = "XEmkEwex5TbqjOitZJ8xtLXTBMQQb7BrtQdzzw-hJVWwnIUysCwCzXT2X2xsMbSXR7uHxWnRkyyFIh1CxfLr6Ilj_n-xClAG_h5aKabBtAjJLVnZ9mMfdKFWlMvPZHYx"

yelp = yelpapi.YelpAPI(yelpapiKey)
# Restaurants = yelp.search_query(location='Philadelphia', categories='Restaurants')
# print(Restaurants)

# print(Restaurants)
base_url = "https://www.yelp.com/biz/"

# response = yelp.business_query(id="harp-and-crown-philadelphia") # type: ignore
# print(response)
# Define a function to get Yelp data
def get_yelp_data(row):
    def find_first_rating(dictionary):
        for key, value in dictionary.items():
            if isinstance(value, dict):
                # If the value is a dictionary, recursively search within it
                result = find_first_rating(value)
                if result is not None:
                    return result
            if key == "rating":
                # If the key is "rating," return the value
                return value
        return None  # Return None if "rating" is not found
    
    # Function to search for "BusinessWebsite" and get the URL
    def find_business_website(json_obj):
        if isinstance(json_obj, dict):
            if "__typename" in json_obj and json_obj["__typename"] == "BusinessWebsite":
                return json_obj.get("url")
            for key, value in json_obj.items():
                result = find_business_website(value)
                if result:
                    return result
        elif isinstance(json_obj, list):
            for item in json_obj:
                result = find_business_website(item)
                if result:
                    return result
    yelp_alias = row['Yelp Alias']
    print(yelp_alias)
    print()
    response = yelp.business_query(id=yelp_alias) # type: ignore
    # print(response)

    # Extract categories from the details_response
    categories = [category['title'] for category in response.get('categories', [])]
    address = ', '.join(response["location"]["display_address"])

    url = base_url + yelp_alias
    yelp_response = requests.get(url)
    html = yelp_response.text
    # Parse HTML with BeautifulSoup  
    soup = BeautifulSoup(html, "html.parser")
    # Find the <script> tag
    script_tag = soup.find("script", {"data-apollo-state": True})

    if script_tag is not None:
        # Extract JSON string 
        json_str = script_tag.text # type: ignore
        # Remove <!-- and -->
        cleaned = json_str[4:-3]
        # Add outer quotes
        json_str = re.sub(r'&quot;', '"', cleaned)
        # Parse the JSON string into a Python object
        json_object = json.loads(json_str)

        business_properties = {}
        neighborhoods_json = []
        rating = None
        hours_properties = {}
        website = None
        # Parse the JSON object once
        for key, value in json_object.items():
            if isinstance(value, dict):
                if "displayText" in value:
                    display_text = value["displayText"]
                    is_active = value["isActive"]
                    if "&amp;" in display_text:
                        display_text = display_text.replace("&amp;", "and")
                    if "Not Good" in display_text:
                        display_text = display_text.replace("Not Good", "Good")
                        is_active = not is_active
                    if "Very Loud" in display_text:
                        display_text = display_text.replace("Very ", "")
                    if "Free Wi-fi" in display_text:
                        display_text = display_text.replace("Free ", "")
                    if "No " in display_text:
                        display_text = display_text.replace("No ", "")
                        is_active = not is_active
                    if "Best nights on" in display_text:
                        parts = display_text.split("Best nights on ")[1].split(',')
                        for part in parts:
                            new_display_text = "Best nights on " + part.strip()
                            business_properties[new_display_text] = is_active
                    elif "Paid Wi-Di" not in display_text:
                        display_texts = [text.strip() for text in display_text.split(',')]
                        business_properties.update({text: is_active for text in display_texts})
                if "neighborhoods" in value:
                    neighborhoods_json = value["neighborhoods"].get("json", neighborhoods_json)
                business_website_url = find_business_website(json_object)
                if business_website_url:
                    website = business_website_url.replace("&#x2F;", "/")
                # if "rating" in value:
                #     rating = value["rating"]
                if "regularHours" in value and "dayOfWeekShort" in value:
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

        def check_links(url):
            try:
                response = requests.get(url)
                # print(response.status_code)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    open_table_link = soup.find('a', {'href': lambda x: x and 'opentable' in x.lower()})
                    resy_link = soup.find('a', {'href': lambda x: x and 'resy' in x.lower()})
                    third_link = soup.find('a', {'href': lambda x: x and 'exploretock' in x.lower()})
                    
                    if open_table_link:
                        return open_table_link.get('href') # type: ignore
                    elif resy_link:
                        return resy_link.get('href') # type: ignore
                    elif third_link:
                        return third_link.get('href') # type: ignore
                    else:
                        # If neither OpenTable nor Resy links found, check for a reservations page
                        reservations_page = soup.find('a', {'href': lambda x: x and 'reservations' in x.lower()})
                        print()
                        # print(reservations_page)
                        if reservations_page:
                            # If a reservations page is found, try to extract links from there
                            reservations_url = reservations_page.get('href') # type: ignore
                            print(reservations_url)
                            reservations_url = urljoin(url, reservations_url) # type: ignore
                            print(reservations_url)
                            print("-------------")
                            reservations_response = requests.get(reservations_url) # type: ignore
                            # print(reservations_response.status_code)
                            if reservations_response.status_code == 200:
                                reservations_soup = BeautifulSoup(reservations_response.text, 'html.parser')
                                open_table_link = reservations_soup.find('a', {'href': lambda x: x and 'opentable' in x.lower()})
                                resy_link = reservations_soup.find('a', {'href': lambda x: x and 'resy' in x.lower()})
                                third_link = soup.find('a', {'href': lambda x: x and 'exploretock' in x.lower()})
                                if open_table_link:
                                    return open_table_link.get('href') # type: ignore
                                elif resy_link:
                                    return resy_link.get('href') # type: ignore
                                elif third_link:
                                    return third_link.get('href') # type: ignore
                                else:
                                    return reservations_url
                            else:
                                return reservations_url
                    return None
                else:
                    return None
            except Exception as e:
                print(f"Error: {e}")
                return None
        res_link = None
        if pd.isna(website) == False:
            res_link = check_links(website)
        restaurant_name = row['Name']
        rating = find_first_rating(json_object)
        # Extract relevant data from the Yelp response (customize based on your needs)
        yelp_data = {
            'Name': restaurant_name,
            'Open Table Link': res_link,
            'Address': address,
            'Latitude': response["coordinates"]["latitude"],
            'Longitude': response["coordinates"]["longitude"],
            "Website": website,
            'Review Count': response.get('review_count'),
            'Price': response.get('price'),
            # 'Yelp URL': response.get('url'),
            'Categories': categories,
            **business_properties,
            "Neighborhoods": neighborhoods_json,
            **hours_properties,
            "Yelp Rating": rating,
            "Sips Participant": "N",
            "Restaurant Week Participant": "N",
        }
        return yelp_data
    else:
        print("Did not work for: " + row['Name'])
        return None
    
# Load the Yelp Aliases CSV into a DataFrame
yelp_aliases_df = pd.read_csv('YelpAliases.csv')

# Load the MasterTable from the original CSV
master_table_df = pd.read_csv('MasterTable.csv')

# Convert all relevant columns to lowercase to ensure consistent comparison
# yelp_aliases_df['Name'] = yelp_aliases_df['Name'].str.lower()
# master_table_df['Name'] = master_table_df['Name'].str.lower()
# master_table_df['Address'] = master_table_df['Address'].str.lower()

# Find bars in MasterTable not in Yelp Aliases CSV
missing_bars_df = yelp_aliases_df[~yelp_aliases_df['Name'].isin(master_table_df['Name'])]
print(missing_bars_df)
# Process only the first 100 rows of missing_bars_df
limited_missing_bars_df = missing_bars_df.iloc[:100]
# data = missing_bars_df.apply(get_yelp_data, axis=1) # type: ignore

# Initialize an empty list to collect data for the first 100 rows
data = []

# Process each row in the limited_missing_bars_df and add the result to the master_table_df
for index, row in limited_missing_bars_df.iterrows():
    yelp_data = get_yelp_data(row)
    if yelp_data is not None:
        data.append(yelp_data)

# Convert the list of dictionaries into a DataFrame
data_df = pd.DataFrame(data)
data_df.to_json('output2.json', orient='records', lines=True)
# Merge data_df with the master_table_df based on the 'Name' column
print(master_table_df)
print(data_df)
print()
# master_table_df = master_table_df.merge(data_df, on='Name', how='left')
master_table_df = master_table_df.append(data_df, ignore_index=True) # type: ignore
print(master_table_df)
# Save the updated master_table_df to a CSV file or perform further processing as needed
master_table_df.to_csv('UpdatedMasterTable.csv', index=False)
# If not:
#   Pull yelp api data
#   Pull the extra yelp data
#   Enter in nulls for RW and Sips data
#   Calculate scores or other fields