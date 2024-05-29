from bs4 import BeautifulSoup
import requests
import pandas as pd
from tabulate import tabulate
from geopy.geocoders import Nominatim
import time
import os
import folium
import re
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from yelpapi import YelpAPI
import yelpapi
import numpy as np


master_df = pd.read_csv('MasterTable.csv')
yelp_df = pd.read_csv('YelpAliases.csv')
not_in_master = yelp_df[~yelp_df['Name'].isin(master_df['Name'])]

print(not_in_master)

# Actual API Key
yelpapiKey = "DQx0YugiFJ5inYYp8fVvDqLx0R_dVo8yXxRZtpD5jkbNK0WmAqUygKIyXnYHlfL0pYRndGHGmuvn_QCXPVndRCc0VjtZzxCSHE8MhPthoJ4YUygg65DJrhMJLu7OZHYx"

# Backup API Key
# yelpapiKey = "r9ksNtdCcwK8MhsrL9fB5BvOGkC8Habi6-S5Shhh-Xu7CXF5xCBAPRCPS04atHegmf3BOMeW9gqNxA16E32gg4xDhcuWgD0k58m9jp280IpSb5zthhBCvmeXBsnPZHYx"

# Backup backup API Key
# yelpapiKey = "XEmkEwex5TbqjOitZJ8xtLXTBMQQb7BrtQdzzw-hJVWwnIUysCwCzXT2X2xsMbSXR7uHxWnRkyyFIh1CxfLr6Ilj_n-xClAG_h5aKabBtAjJLVnZ9mMfdKFWlMvPZHYx"

yelp = yelpapi.YelpAPI(yelpapiKey)

# Add the new restaurants yelp aliases to the master list so that they can be retrieve easier in the future
def addNewYelpAliases():
    try:
        existing_yelp_data = pd.read_csv("YelpAliases.csv")
    except FileNotFoundError:
        existing_yelp_data = pd.DataFrame(columns=['Name', 'Yelp Alias'])

    # Function to get Yelp data for each Restaurant
    def get_yelp_alias(row):
        restaurant_name = row['Name']
        print("--------------------------------------------")
        print(restaurant_name)
        address = row['Address']
        print(address)
        parts = address.split(', ')
        # Extract individual components
        street_address = parts[0]
        city = parts[1]
        state_zip = parts[2]
        # Split the state and ZIP code
        state, zipcode = state_zip.split(' ')
        try:
            match_response = yelp.business_match_query(name=restaurant_name, address1=street_address, city=city, state=state, country='US', postal_code=zipcode)
            print(match_response)
            yelp_alias = match_response.get('businesses', [{}])[0].get('alias')
            return pd.Series({'Name': restaurant_name, 'Yelp Alias': yelp_alias})
        except:
            print(f"Error retrieving data for {restaurant_name}")
            return pd.Series({'Name': restaurant_name, 'Yelp Alias': None})

    # Create a new DataFrame for new Yelp data
    new_yelp_data = not_in_master.apply(get_yelp_alias, axis=1)
    # Combine new data with existing data
    updated_yelp_data = pd.concat([existing_yelp_data, new_yelp_data], ignore_index=True)
    # Save the updated Yelp data to the CSV file
    updated_yelp_data.to_csv("YelpAliases.csv", index=False)
# addNewYelpAliases()

print()
# print(not_in_master)
print("Before pullYelpData")
def pullYelpData(not_in_master):
    yelp_df = pd.read_csv('YelpAliases.csv')
    add_from_yelp = not_in_master[~not_in_master['Name'].isin(yelp_df['Name'])]
    add_from_yelp = yelp_df[yelp_df['Name'].isin(not_in_master['Name'])]
    add_from_yelp.reset_index()
    print(add_from_yelp)
    asd

    base_url = "https://www.yelp.com/biz/"
    data_list = []
    for index, row in add_from_yelp.iterrows():
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

        max_retries = 3
        retry_count = 0
        json_str = ""

        while retry_count < max_retries:
            try:
                # Your existing code
                script_tag = soup.find("script", {"data-apollo-state": True})
                json_str = script_tag.text  # type: ignore

                # If the script_tag is found and json_str is extracted successfully, exit the loop
                break
            except AttributeError:
                # If an AttributeError occurs, print an error message and increment the retry_count
                print("Error: 'NoneType' object has no attribute 'text'")
                retry_count += 1
                if retry_count < max_retries:
                    print(f"Retrying... Attempt {retry_count}")
                else:
                    print("Max retries reached. Exiting loop.")
                    # If max_retries is reached, you may want to handle it accordingly
                    break

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
    new_data_df = pd.DataFrame(data_list)
    print()
    print(new_data_df)
    print()

    def fixColumns(df):
        # -------------- PARKING -----------------
        parking_types = ['Street Parking', 'Bike Parking', 'Valet Parking', 'Validated Parking', 'Garage Parking', 'Private Lot Parking']
        existing_columns = [col for col in parking_types if col in df.columns]
        if existing_columns:
            # Fill NaN values with False for the selected parking types
            df[existing_columns] = df[existing_columns].fillna(False)
            # Concatenate parking types into a single column
            df['Parking'] = df[existing_columns].apply(lambda x: ', '.join(x.index[x]), axis=1)
            # Drop the original parking types columns
            df.drop(columns=existing_columns, inplace=True)
        print(df)
        # =========================================

        # -------------- BEST NIGHTS -----------------
        night_types = ["Best nights on Monday","Best nights on Tuesday","Best nights on Wednesday","Best nights on Thursday","Best nights on Friday","Best nights on Saturday","Best nights on Sunday"]
        existing_columns2 = [col for col in night_types if col in df.columns]
        if existing_columns2:
            # Fill NaN values with False for the selected parking types
            df[existing_columns2] = df[existing_columns2].fillna(False)
            # Concatenate parking types into a single column
            df['Best_Nights'] = df[existing_columns2].apply(lambda x: ', '.join(x.index[x]).replace('Best nights on ',''), axis=1)  # type: ignore
            # Drop the original parking types columns
            df.drop(columns=existing_columns2, inplace=True)
        # =========================================

        # -------------- PAYMENT -----------------
        pay_types = ["Accepts Credit Cards","Accepts Android Pay","Accepts Apple Pay","Accepts Cryptocurrency"]
        existing_columns3 = [col for col in pay_types if col in df.columns]
        if existing_columns3:
            # Fill NaN values with False for the selected parking types
            df[existing_columns3] = df[existing_columns3].fillna(False)
            # Concatenate parking types into a single column
            df['Payment'] = df[existing_columns3].apply(lambda x: ', '.join(x.index[x]).replace('Accepts ',''), axis=1)  # type: ignore
            # Drop the original parking types columns
            df.drop(columns=existing_columns3, inplace=True)
        # =========================================

        # -------------- MINORITY OWNED -----------------
        minority_types = ["Women-owned","Latinx-owned","Asian-owned","Black-owned","Veteran-owned","LGBTQ-owned"]
        existing_columns4 = [col for col in minority_types if col in df.columns]
        if existing_columns4:
            # Fill NaN values with False for the selected parking types
            df[existing_columns4] = df[existing_columns4].fillna(False)
            # Concatenate parking types into a single column
            df['Minority_Owned'] = df[existing_columns4].apply(lambda x: ', '.join(x.index[x]), axis=1)
            # Drop the original parking types columns
            df.drop(columns=existing_columns4, inplace=True)
        # =========================================

        # -------------- GOOD FOR -----------------
        if 'Good For Groups' in df.columns:
            df['Good For Groups'] = df['Good For Groups'].fillna(df['Good for Groups'])
        if 'Good for Groups' in df.columns:
            df.drop(columns='Good for Groups', inplace=True)
        if 'Good For Working.1' in df.columns:
            df.drop(columns='Good For Working.1', inplace=True)

        good_for_types = ["Good For Dinner","Good For Kids","Good For Lunch","Good for Lunch","Good For Dancing","Good For Working","Good for Dinner","Good for Brunch","Good For Brunch","Good For Dessert","Good For Breakfast","Good For Groups","Good For Late Night", "All Ages", "Late Night"]
        existing_columnsz = [col for col in good_for_types if col in df.columns]
        if existing_columnsz:
            # Fill NaN values with False for the selected parking types
            df[existing_columnsz] = df[existing_columnsz].fillna(False)
            # Concatenate parking types into a single column
            df['Good_For'] = df[existing_columnsz].apply(lambda x: ', '.join(x.index[x].str.replace('Good For ', '')), axis=1)
            # Drop the original parking types columns
            df.drop(columns=existing_columnsz, inplace=True)

        # df.drop(columns=good_for_types, inplace=True)
        # =========================================

        # -------------- OFFERS -----------------
        if 'Offers Delivery' in df.columns:
            df['Offers Delivery'] = df['Offers Delivery'].fillna(df['Delivery'])
        df.drop(columns='Delivery', inplace=True)
        if 'Offers Takeout' in df.columns:
            df['Offers Takeout'] = df['Offers Takeout'].fillna(df['Takeout'])
        df.drop(columns='Takeout', inplace=True)


        offers_types = ["Offers Delivery","Offers Takeout","Offers Catering","Offers Military Discount","Online ordering-only"]
        # df[offers_types] = df[offers_types].fillna(False)
        # df['Offers'] = df[offers_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
        # df.drop(columns=offers_types, inplace=True)
        
        existing_columns5 = [col for col in offers_types if col in df.columns]
        if existing_columns5:
            # Fill NaN values with False for the selected parking types
            df[existing_columns5] = df[existing_columns5].fillna(False)
            # Concatenate parking types into a single column
            df['Offers'] = df[existing_columns5].apply(lambda x: ', '.join(x.index[x]), axis=1)
            # Drop the original parking types columns
            df.drop(columns=existing_columns5, inplace=True)
        # =========================================

        # -------------- OPTIONS -----------------
        if 'Vegetarian Options' in df.columns:
            df['Vegetarian Options'] = df['Vegetarian Options'].fillna(df['Many Vegetarian Options'])
        df.drop(columns='Many Vegetarian Options', inplace=True)

        options_types = ["Vegan Options","Limited Vegetarian Options","Pescatarian Options","Keto Options","Vegetarian Options","Soy-Free Options","Dairy-Free Options","Gluten-Free Options"]
        # df[options_types] = df[options_types].fillna(False)
        # df['Options'] = df[options_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
        # df.drop(columns=options_types, inplace=True)

        existing_columns6 = [col for col in options_types if col in df.columns]
        if existing_columns6:
            # Fill NaN values with False for the selected parking types
            df[existing_columns6] = df[existing_columns6].fillna(False)
            # Concatenate parking types into a single column
            df['Options'] = df[existing_columns6].apply(lambda x: ', '.join(x.index[x]), axis=1)
            # Drop the original parking types columns
            df.drop(columns=existing_columns6, inplace=True)
        # =========================================

        # -------------- VIBES -----------------
        if 'Casual' in df.columns:
            df['Casual'] = df['Casual'].fillna(df['Casual Dress'])
        df.drop(columns='Casual Dress', inplace=True)
        vibes_types = ["Trendy", "Classy", "Intimate", "Romantic", "Upscale", "Dressy", "Hipster", "Touristy", "Divey", "Casual", "Quiet", "Loud", "Moderate Noise"]
        # df[vibes_types] = df[vibes_types].fillna(False)
        # df['Vibes'] = df[vibes_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
        # df.drop(columns=vibes_types, inplace=True)

        existing_columns7 = [col for col in vibes_types if col in df.columns]
        if existing_columns7:
            # Fill NaN values with False for the selected parking types
            df[existing_columns7] = df[existing_columns7].fillna(False)
            # Concatenate parking types into a single column
            df['Vibes'] = df[existing_columns7].apply(lambda x: ', '.join(x.index[x]), axis=1)
            # Drop the original parking types columns
            df.drop(columns=existing_columns7, inplace=True)
        # =========================================

        # -------------- ACCESSIBILITY -----------------
        if 'Wheelchair Accessible' in df.columns:
            if 'Not Wheelchair Accessible' in df.columns:
                df['Wheelchair Accessible'] = df['Wheelchair Accessible'] | ~df['Not Wheelchair Accessible'].fillna(False)
            df['Wheelchair Accessible'] = df['Wheelchair Accessible'].mask(df['Wheelchair Accessible'] == False, np.nan)
        if 'Not Wheelchair Accessible' in df.columns:
            df.drop(columns='Not Wheelchair Accessible', inplace=True)
        access_types = ["Open to All", "Wheelchair Accessible", "Gender-neutral restrooms"]
        # df[access_types] = df[access_types].fillna(False)
        # df['Accessibility'] = df[access_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
        # df.drop(columns=access_types, inplace=True)

        existing_columns8 = [col for col in access_types if col in df.columns]
        if existing_columns8:
            # Fill NaN values with False for the selected parking types
            df[existing_columns8] = df[existing_columns8].fillna(False)
            # Concatenate parking types into a single column
            df['Accessibility'] = df[existing_columns8].apply(lambda x: ', '.join(x.index[x]), axis=1)
            # Drop the original parking types columns
            df.drop(columns=existing_columns8, inplace=True)
        # =========================================

        # -------------- DOGS -----------------
        if 'Dogs Allowed' in df.columns:
            df['Dogs Allowed'] = df['Dogs Allowed'] | ~df['Dogs Not Allowed'].fillna(False)
        df['Dogs_Allowed'] = df['Dogs Allowed'].mask(df['Dogs Allowed'] == False, np.nan)
        df.drop(columns=['Dogs Not Allowed', 'Dogs Allowed'], inplace=True)
        # =========================================

        # -------------- SMOKING -----------------
        if 'Smoking' in df.columns:
            if 'Smoking Allowed' in df.columns:
                df['Smoking'] = df['Smoking'].fillna(df['Smoking Allowed'])
            else:
                df['Smoking'] = df['Smoking']
        if 'Smoking Outside Onlyd' in df.columns:
            df.drop(columns=["Smoking Outside Only"], inplace=True)
        if 'Smoking Allowed' in df.columns:
            df.drop(columns=['Smoking Allowed'], inplace=True)
        # =========================================

        # -------------- PACKING -----------------
        package_types = ["Plastic-free packaging", "Provides reusable tableware", "Compostable containers available", "Bring your own container allowed"]
        # df[package_types] = df[package_types].fillna(False)
        # df['Packaging'] = df[package_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
        # df.drop(columns=package_types, inplace=True)

        existing_columns9 = [col for col in package_types if col in df.columns]
        if existing_columns9:
            # Fill NaN values with False for the selected parking types
            df[existing_columns9] = df[existing_columns9].fillna(False)
            # Concatenate parking types into a single column
            df['Packaging'] = df[existing_columns9].apply(lambda x: ', '.join(x.index[x]), axis=1)
            # Drop the original parking types columns
            df.drop(columns=existing_columns9, inplace=True)
        # =========================================

        # -------------- RESERVATION TYPE -----------------
        if 'Takes Reservations' in df.columns:
            df['Takes Reservations'] = df['Takes Reservations'].fillna(df['Reservations'])
        df.drop(columns='Reservations', inplace=True)
        res_types = ["By Appointment Only", "Walk-ins Welcome", "Takes Reservations"]
        # df[res_types] = df[res_types].fillna(False)
        # df['Reservation_Type'] = df[res_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
        # df.drop(columns=res_types, inplace=True)

        existing_columns10 = [col for col in res_types if col in df.columns]
        if existing_columns10:
            # Fill NaN values with False for the selected parking types
            df[existing_columns10] = df[existing_columns10].fillna(False)
            # Concatenate parking types into a single column
            df['Reservation_Type'] = df[existing_columns10].apply(lambda x: ', '.join(x.index[x]), axis=1)
            # Drop the original parking types columns
            df.drop(columns=existing_columns10, inplace=True)
        # =========================================

        # -------------- SEATING -----------------
        seating_types = ["Outdoor Seating", "Heated Outdoor Seating", "Covered Outdoor Seating", "Private Dining", "Drive-Thru"]
        # df[seating_types] = df[seating_types].fillna(False)
        # df['Seating'] = df[seating_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
        # df.drop(columns=seating_types, inplace=True)

        existing_columns11 = [col for col in seating_types if col in df.columns]
        if existing_columns11:
            # Fill NaN values with False for the selected parking types
            df[existing_columns11] = df[existing_columns11].fillna(False)
            # Concatenate parking types into a single column
            df['Seating'] = df[existing_columns11].apply(lambda x: ', '.join(x.index[x]), axis=1)
            # Drop the original parking types columns
            df.drop(columns=existing_columns11, inplace=True)
        # =========================================

        # def service(row):
        #     service_types = ["Plastic-free packaging", "Provides reusable tableware", "Compostable containers available", "Bring your own container allowed"]
        #     for serv in service_types:
        #         if row[serv]:
        #             return serv
        #     return None
        # # Apply the function to create the column
        # df['Options'] = df.apply(service, axis=1) # type: ignore
        # service_types = ["Outdoor Seating", "TV", "Waiter Service", "Wi-Fi"]
        # # Drop the original columns
        # df.drop(columns=service_types, inplace=True)

        # -------------- MEAL -----------------
        # food_types = ["Lunch", "Dessert", "Brunch", "Dinner", "Breakfast"]
        food_types = ["Lunch", "Dessert", "Brunch", "Dinner"]
        # df[food_types] = df[food_types].fillna(False)
        # df['Meal_Types'] = df[food_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
        # df.drop(columns=food_types, inplace=True)

        existing_columns12 = [col for col in food_types if col in df.columns]
        if existing_columns12:
            # Fill NaN values with False for the selected parking types
            df[existing_columns12] = df[existing_columns12].fillna(False)
            # Concatenate parking types into a single column
            df['Meal_Types'] = df[existing_columns12].apply(lambda x: ', '.join(x.index[x]), axis=1)
            # Drop the original parking types columns
            df.drop(columns=existing_columns12, inplace=True)
        # =========================================

        # -------------- MUSIC -----------------
        music_types = ["Live Music", "DJ", "Background Music", "Juke Box", "Karaoke"]
        # df[music_types] = df[music_types].fillna(False)
        # df['Music'] = df[music_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
        # df.drop(columns=music_types, inplace=True)
        
        existing_columns13 = [col for col in music_types if col in df.columns]
        if existing_columns13:
            # Fill NaN values with False for the selected parking types
            df[existing_columns13] = df[existing_columns13].fillna(False)
            # Concatenate parking types into a single column
            df['Music'] = df[existing_columns13].apply(lambda x: ', '.join(x.index[x]), axis=1)
            # Drop the original parking types columns
            df.drop(columns=existing_columns13, inplace=True)
        # =========================================

        # -------------- HAPPY HOUR -----------------
        if 'Happy Hour' in df.columns:
            df['Happy Hour'] = df['Happy Hour'].fillna(df['Happy Hour Specials'])
        if 'Happy Hour Specials' in df.columns:
            df.drop(columns='Happy Hour Specials', inplace=True)
        alc_types = ["Alcohol", "Happy Hour", "Beer and Wine Only", "Full Bar"]
        # df[alc_types] = df[alc_types].fillna(False)
        # df['Alcohol_Options'] = df[alc_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
        # df.drop(columns=alc_types, inplace=True)
        
        existing_columns14 = [col for col in alc_types if col in df.columns]
        if existing_columns14:
            # Fill NaN values with False for the selected parking types
            df[existing_columns14] = df[existing_columns14].fillna(False)
            # Concatenate parking types into a single column
            df['Alcohol_Options'] = df[existing_columns14].apply(lambda x: ', '.join(x.index[x]), axis=1)
            # Drop the original parking types columns
            df.drop(columns=existing_columns14, inplace=True)
        # =========================================

        # -------------- AMENITIES -----------------
        if 'Free Wi-Fi' in df.columns and 'Wi-Fi' in df.columns:
            df['Wi-Fi'] = df['Wi-Fi'].fillna(df['Free Wi-Fi'])
            df.drop(columns='Free Wi-Fi', inplace=True)
        amenity_types = ["TV", "Pool Table", "Wi-Fi", "EV charging station available"]
        # df[amenity_types] = df[amenity_types].fillna(False)
        # df['Amenities'] = df[amenity_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
        # df.drop(columns=amenity_types, inplace=True)
        
        existing_columns15 = [col for col in amenity_types if col in df.columns]
        if existing_columns15:
            # Fill NaN values with False for the selected parking types
            df[existing_columns15] = df[existing_columns15].fillna(False)
            # Concatenate parking types into a single column
            df['Amenities'] = df[existing_columns15].apply(lambda x: ', '.join(x.index[x]), axis=1)
            # Drop the original parking types columns
            df.drop(columns=existing_columns15, inplace=True)
        if 'Virtual restaurant' in df.columns:
            df.drop(columns="Virtual restaurant", inplace=True)
        if 'Waiter Service' in df.columns:
            df.drop(columns="Waiter Service", inplace=True)
        # =========================================

        # -------------- RENAME -----------------
        column_mapping = {
            "Sips Url": "SIPS_URL",
            "Cocktails": "SIPS_COCKTAILS",
            "Wine": "SIPS_WINE",
            "Beer": "SIPS_BEER",
            "Half-Priced Appetizers": "SIPS_HALFPRICEDAPPS",
            "RW Url": "RW_URL",
            "Details": "RW_DETAILS",
            "Deals Offered": "RW_DEALS",
            "Deal Website": "RW_MENU",
            "Photo": "RW_PHOTO",
            "Sips Participant": "SIPS_PARTICIPANT",
            "Restaurant Week Participant": "RW_PARTICIPANT",
            "Open Table Link": "RESERVATION_LINK",
            "Yelp Rating": "Yelp_Rating",
            "Review Count": "Review_Count",
            "Restaurant Week Score": "RW_Score",
            "Popularity Score": "Popularity"
        }
        df.rename(columns=column_mapping, inplace=True)
        # print(df)
        return df

    new_data_df = fixColumns(new_data_df)
    # print()
    # print(new_data_df)
    # print(new_data_df.columns)
    # Get the latitude and longitude of the bar if it is new
    def getLatLong(not_in_master):
        MAX_ATTEMPTS = 5
        geolocator = Nominatim(timeout=10, user_agent="my_app") # type: ignore

        def find_location(row):
            place = row['Address'].replace("Ben Franklin", "Benjamin Franklin")
            print(place)
            attempts = 0
            while attempts < MAX_ATTEMPTS:
                try:
                    location = geolocator.geocode(place)
                    # print(location)
                    return location.latitude, location.longitude # type: ignore
                except:
                    attempts += 1
                    time.sleep(1)
            print()
            return None, None

        not_in_master[['Latitude','Longitude']] = not_in_master.apply(find_location, axis="columns", result_type="expand")
        return not_in_master
    not_in_master = getLatLong(not_in_master)
    print(not_in_master)

    # Assuming 'Name' is the common column in both DataFrames
    merged_df = pd.merge(not_in_master, new_data_df, on='Name', how='inner')

    # 'how' parameter can be adjusted based on your requirements: 'inner', 'outer', 'left', 'right'

    # Display the merged DataFrame
    print(merged_df)

    existing_master_data = pd.read_csv("MasterTableNew.csv")
    print(existing_master_data)
    # Combine new data with existing data
    updated_yelp_data = pd.concat([existing_master_data, merged_df], ignore_index=True)
    print(updated_yelp_data)
    # Save the updated Yelp data to the CSV file
    updated_yelp_data.to_csv("MasterTableNew.csv", index=False)
pullYelpData(not_in_master)