import pandas as pd
from yelpapi import YelpAPI
import yelpapi
import requests
import json
import html
import re
from bs4 import BeautifulSoup
import time
import numpy as np
from selenium import webdriver
from selenium.webdriver.common.by import By
from geopy.geocoders import Nominatim

# ------------------------------------------------
# This script does = Clear out old SIPS, add in the new and any new bars needed
# ------------------------------------------------
start_time = time.time()

# csv_df = pd.read_csv('MasterTable.csv')
# geolocator = Nominatim(timeout=10, user_agent="my_app") # type: ignore

def clearOldSips(df):
    # List of columns to be updated
    columns_to_update = [
        'SIPS_URL',
        'SIPS_COCKTAILS',
        'SIPS_WINE',
        'SIPS_BEER',
        'SIPS_HALFPRICEDAPPS'
    ]

    # Update specified columns to empty strings where SIPS_PARTICIPANT is "Y"
    df.loc[df['SIPS_PARTICIPANT'] == 'Y', columns_to_update] = np.nan
    # Change SIPS_PARTICIPANT from "Y" to "N"
    df.loc[df['SIPS_PARTICIPANT'] == 'Y', 'SIPS_PARTICIPANT'] = 'N'
    # Optionally, save the modified DataFrame back to a CSV file
    # df.to_csv('ModifiedMasterTable.csv', index=False)
    # Display the modified DataFrame (for verification)
    return df

# csv_df = clearOldSips(csv_df)

def scrapeSipsPage(geolocator):
    html = "https://centercityphila.org/explore-center-city/ccd-sips/sips-list-view"
    base_html = "https://centercityphila.org"
    source = requests.get(html).text
    soup = BeautifulSoup(source, "lxml")

    bars = []
    pages= []
    pager = soup.find('div', class_='c-pager')
    for link in pager.find_all('a'): # type: ignore
        pages.append(base_html + link['href'])
    print(pages)

    pattern = r'apos\.maps\["ccd-places"\]\.addMap\((.*?)\)'
    bar_info_list = []
    for page in pages:
        # Request and parse HTML for each page 
        page_html = requests.get(page, allow_redirects=False).text
        soupIter = BeautifulSoup(page_html, 'lxml')
        # print(soupIter.find_all('tr')[1])
        for card in soupIter.find_all('tr'):
            try:
                title = card.find('a', class_='o-text-link').text.strip("\n        ")
                url = html + card.find('a', class_='o-card-link')['href']
                address = card.find('td', attrs={'data-th': 'Address'}).text.strip()
                bars.append([title, address, url])
            except AttributeError:
                continue

    # Create dataframe  
    df = pd.DataFrame(bars, columns=['Name', 'Address', 'SIPS_URL'])

    # print(df)
    # mask = df['Address'].str.contains('Philadelphia')
    # df = df[mask]
    df = df.reset_index(drop=True)
    df = df.drop_duplicates(subset=['Name'])

    # Function to clean address strings
    def clean_address(address):
        address = address.replace("Philadelphia PA,", "Philadelphia, PA")
        address = address.replace("t Philadelphia", "t, Philadelphia")
        address = address.replace("Philadelphia PA", "Philadelphia, PA")
        address = address.replace("PA,", "PA")
        address = address.replace("St. ,", "St.,")
        address = address.replace("Philadephia", "Philadelphia")
        address = address.replace("1421 Sansom Street", "1421 Sansom St, Philadelphia, PA 19110")
        return address
    # Apply the function to the 'Address' column
    df['Address'] = df['Address'].apply(clean_address)
    # Function to clean address strings
    def clean_name(name):
        name = name.replace("*", "")
        return name
    # Apply the function to the 'Address' column
    df['Name'] = df['Name'].apply(clean_name)
    # print(df)

    pattern = r'apos\.maps\["ccd-places"\]\.addMap\((.*?)\)'
    bar_info_list = []
    for page in pages:
        page_html = requests.get(page, allow_redirects=False).text
        soupIter = BeautifulSoup(page_html, 'lxml')
        script_tags = soupIter.find_all('script', text=re.compile(pattern))

        json_data = {}
        for script_tag in script_tags:
            lines = script_tag.string.splitlines()
            for line in lines:
                if re.match(pattern, line.strip()):
                    # Extract the JSON text from the line
                    start_index = line.find('{')
                    end_index = line.rfind('}') + 1
                    json_text = line[start_index:end_index]
                    json_data = json.loads(json_text)
                    break
            if json_data is not None:
                break

        for item in json_data["items"]:
            title = item.get("title", "")
            url_website = item.get("urlWebsite", "")
            if url_website:
                url_website = url_website.rstrip('/')
            bar_info = {"Name": title, "Website": url_website}
            # print(bar_info)
            bar_info_list.append(bar_info)

    new_df = pd.DataFrame(bar_info_list)
    # Print the resulting DataFrame with the new "Bar Website" column
    # print(new_df)
    # df = pd.read_csv('AllSipsLocations.csv')
    merged_df = df.merge(new_df, on='Name', how='left')
    print(merged_df)
    # merged_df.to_csv("AllSipsLocations.csv", index=False)
    df = merged_df

    MAX_ATTEMPTS = 5
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
    df[['Latitude','Longitude']] = df.apply(find_location, axis="columns", result_type="expand")
    print(df)
    return df

# site_df = scrapeSipsPage(geolocator)

def readModalForDeals(df):
    url = 'https://centercityphila.org/explore-center-city/ccd-sips/sips-list-view#cavanaugh-s-rittenhouse'
    # driver = webdriver.Chrome()
    # Create an empty list to store the extracted "Deals" content
    deals_list = []

    # Loop through each row in the DataFrame
    for index, row in df.iterrows():
        # Get the URL value for each row
        url = row['SIPS_URL']
        # Open the URL with the webdriver
        driver = webdriver.Chrome()
        driver.get(url)
        # Wait for modal to load
        driver.implicitly_wait(2) 
        # Find modal div
        modal = driver.find_element(By.CSS_SELECTOR, '.c-modal[data-role="modal-viewport"]')
        # Find title 
        title = modal.find_element(By.CSS_SELECTOR, '.c-modal__title')
        bar = title.text
        print(bar)
        # Get content
        content = modal.find_element(By.CSS_SELECTOR, '.apos-rich-text')
        deals = content.text
        print(deals)
        # Append the extracted "Deals" content to the list
        deals_list.append(deals)
        driver.quit()

    # Add the "Deals" content to the DataFrame as a new column
    df['Deals'] = deals_list

    # Save the updated DataFrame back to the CSV file with the same name
    # df.to_csv('AllSipsLocations.csv', index=False)
    # df = pd.read_csv('AllSipsOriginal.csv')
    # Initialize empty lists for each deal type
    cocktails = []
    wine = []
    beer = []
    appetizers = []

    # Iterate through each row in the DataFrame
    for row in df.itertuples():
        # Use regular expressions to extract data for each deal type
        cocktails_match = re.search(r'\$7 Cocktails(.*?)\$6 Wine', row.Deals, re.DOTALL) # type: ignore
        wine_match = re.search(r'\$6 Wine(.*?)\$5 Beer', row.Deals, re.DOTALL) # type: ignore
        beer_match = re.search(r'\$5 Beer(.*?)Half-Priced Appetizers', row.Deals, re.DOTALL) # type: ignore
        appetizers_match = re.search(r'Half-Priced Appetizers(.*?)$', row.Deals, re.DOTALL) # type: ignore
        # Append extracted data to respective lists
        if cocktails_match:
            cocktails.append(cocktails_match.group(1).strip())
        else:
            cocktails.append(None)
        if wine_match:
            wine.append(wine_match.group(1).strip())
        else:
            wine.append(None)
        if beer_match:
            beer.append(beer_match.group(1).strip())
        else:
            beer.append(None)
        if appetizers_match:
            appetizers.append(appetizers_match.group(1).strip())
        else:
            appetizers.append(None)

    # Create a new DataFrame with the extracted data
    # Add the new columns to the DataFrame
    df['SIPS_COCKTAILS'] = cocktails
    df['SIPS_WINE'] = wine
    df['SIPS_BEER'] = beer
    df['SIPS_HALFPRICEDAPPS'] = appetizers

    # Drop the original 'Deals' column
    df.drop(columns=['Deals'], inplace=True)

    return df

# modal_df = readModalForDeals(site_df)
# site_df = pd.read_csv("Sips2024.csv")
# modal_df = site_df
# modal_df.to_csv("Sips2024.csv", index=False)

def mergeData(csv_df):
    # Merge the two DataFrames on 'Name' and 'Address' to find common records
    merge_df = modal_df.merge(csv_df, on=['Name', 'Address'], how='left', indicator=True, suffixes=('', '_csv'))
    merge_df["SIPS_PARTICIPANT"] = "Y"
    # Create sub-df for records where 'Name' and 'Address' are in both DataFrames
    in_both_df = merge_df[merge_df['_merge'] == 'both'].drop(columns=[col for col in merge_df.columns if col.endswith('_csv') or col == '_merge'])
    # in_both_df["SIPS_PARTICIPANT"] = "Y"
    # Create sub-df for records where 'Name' and 'Address' are only in the original df
    not_in_csv_df = merge_df[merge_df['_merge'] == 'left_only'].drop(columns=[col for col in merge_df.columns if col.endswith('_csv') or col == '_merge'])

    # not_in_csv_df["SIPS_PARTICIPANT"] = "Y"

    # Display the sub-dataframes (for verification)
    print("Records in both DataFrames:")
    print(in_both_df)
    print("\nRecords not in the csv DataFrame:")
    print(not_in_csv_df)

    print(csv_df[["Name", "SIPS_BEER", "SIPS_PARTICIPANT"]])
    # Update records in csv_df with those in in_both_df

    csv_df.update(in_both_df)
    # Add records from not_in_csv_df to csv_df
    csv_df = pd.concat([csv_df, not_in_csv_df], ignore_index=True)

    csv_df.to_csv("MasterTable.csv", index=False)
    return csv_df

# csv_df = mergeData(csv_df)
csv_df = pd.read_csv('MasterTable.csv')

def reformatYelpColumns(df):
    # -------------- PARKING -----------------
    parking_types = ['Street Parking', 'Bike Parking', 'Valet Parking', 'Validated Parking', 'Garage Parking', 'Private Lot Parking']
    df[parking_types] = df[parking_types].fillna(False)
    df['Parking'] = df[parking_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
    df.drop(columns=parking_types, inplace=True)
    # =========================================

    # -------------- BEST NIGHTS -----------------
    night_types = ["Best nights on Monday","Best nights on Tuesday","Best nights on Wednesday","Best nights on Thursday","Best nights on Friday","Best nights on Saturday","Best nights on Sunday"]
    df[night_types] = df[night_types].fillna(False)
    df['Best_Nights'] = df[night_types].apply(lambda x: ', '.join(x.index[x]).replace('Best nights on ',''), axis=1)  # type: ignore
    df.drop(columns=night_types, inplace=True)
    # =========================================

    # -------------- PAYMENT -----------------
    # def combine_payment(row):
    #     pay_types = ["Accepts Credit Cards","Accepts Android Pay","Accepts Apple Pay","Accepts Cryptocurrency"]
    #     for pay_type in pay_types:
    #         if row[pay_type]:
    #             return pay_type.split("Accepts ")[1]
    #     return None
    # # Apply the function to create the column
    # df['Payment'] = df.apply(combine_payment, axis=1) # type: ignore
    pay_types = ["Accepts Credit Cards","Accepts Android Pay","Accepts Apple Pay","Accepts Cryptocurrency"]
    df[pay_types] = df[pay_types].fillna(False)
    df['Payment'] = df[pay_types].apply(lambda x: ', '.join(x.index[x]).replace('Accepts ',''), axis=1)  # type: ignore
    df.drop(columns=pay_types, inplace=True)
    # =========================================

    # -------------- MINORITY OWNED -----------------
    minority_types = ["Women-owned","Latinx-owned","Asian-owned","Black-owned","Veteran-owned","LGBTQ-owned"]
    df[minority_types] = df[minority_types].fillna(False)
    df['Minority_Owned'] = df[minority_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
    df.drop(columns=minority_types, inplace=True)
    # =========================================

    # -------------- GOOD FOR -----------------
    df['Good For Groups'] = df['Good For Groups'].fillna(df['Good for Groups'])
    df.drop(columns='Good for Groups', inplace=True)
    df.drop(columns='Good For Working.1', inplace=True)
    def good_for(row):
        good_for_types = ["Good For Dinner","Good For Kids","Good For Lunch","Good For Dancing","Good For Working","Good For Brunch","Good For Dessert","Good For Breakfast","Good For Groups","Good For Late Night", "All Ages", "Late Night"]
        for good_for in good_for_types:
            if row[good_for]:
                return good_for.split("Good For ")[1]
        return None
    # Apply the function to create the column
    df['Good_For'] = df.apply(good_for, axis=1) # type: ignore
    good_for_types = ["Good For Dinner","Good For Kids","Good For Lunch","Good For Dancing","Good For Working","Good For Brunch","Good For Dessert","Good For Breakfast","Good For Groups","Good For Late Night", "All Ages", "Late Night"]
    # df[good_for_types] = df[good_for_types].fillna(False)
    # df['Good_For'] = df[good_for_types].apply(lambda x: ', '.join(x.index[x]).replace('Good For ',''), axis=1)  # type: ignore
    df.drop(columns=good_for_types, inplace=True)
    # =========================================

    # -------------- OFFERS -----------------
    df['Offers Delivery'] = df['Offers Delivery'].fillna(df['Delivery'])
    df.drop(columns='Delivery', inplace=True)
    df['Offers Takeout'] = df['Offers Takeout'].fillna(df['Takeout'])
    df.drop(columns='Takeout', inplace=True)

    # def offers(row):
    #     offers_types = ["Offers Delivery","Offers Takeout","Offers Catering","Offers Military Discount"]
    #     for offer in offers_types:
    #         if row[offer]:
    #             return offer.split("Offers ")[1]
    #     return None
    # # Apply the function to create the column
    # df['Offers'] = df.apply(offers, axis=1) # type: ignore
    offers_types = ["Offers Delivery","Offers Takeout","Offers Catering","Offers Military Discount","Online ordering-only"]
    df[offers_types] = df[offers_types].fillna(False)
    df['Offers'] = df[offers_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
    df.drop(columns=offers_types, inplace=True)
    # =========================================

    # -------------- OPTIONS -----------------
    df['Vegetarian Options'] = df['Vegetarian Options'].fillna(df['Many Vegetarian Options'])
    df.drop(columns='Many Vegetarian Options', inplace=True)
    # def options(row):
    #     options_types = ["Vegan Options","Limited Vegetarian Options","Pescatarian Options","Keto Options","Vegetarian Options","Soy-Free Options","Dairy-Free Options","Gluten-Free Options"]
    #     for option in options_types:
    #         if row[option]:
    #             return option.split(" Options")[0]
    #     return None
    # # Apply the function to create the column
    # df['Options'] = df.apply(options, axis=1) # type: ignore
    options_types = ["Vegan Options","Limited Vegetarian Options","Pescatarian Options","Keto Options","Vegetarian Options","Soy-Free Options","Dairy-Free Options","Gluten-Free Options"]
    df[options_types] = df[options_types].fillna(False)
    df['Options'] = df[options_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
    df.drop(columns=options_types, inplace=True)
    # =========================================

    # -------------- VIBES -----------------
    df['Casual'] = df['Casual'].fillna(df['Casual Dress'])
    df.drop(columns='Casual Dress', inplace=True)
    vibes_types = ["Trendy", "Classy", "Intimate", "Romantic", "Upscale", "Dressy", "Hipster", "Touristy", "Divey", "Casual", "Quiet", "Loud", "Moderate Noise"]
    df[vibes_types] = df[vibes_types].fillna(False)
    df['Vibes'] = df[vibes_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
    df.drop(columns=vibes_types, inplace=True)
    # =========================================

    # -------------- ACCESSIBILITY -----------------
    df['Wheelchair Accessible'] = df['Wheelchair Accessible'] | ~df['Not Wheelchair Accessible'].fillna(False)
    df['Wheelchair Accessible'] = df['Wheelchair Accessible'].mask(df['Wheelchair Accessible'] == False, np.nan)
    df.drop(columns='Not Wheelchair Accessible', inplace=True)
    access_types = ["Open to All", "Wheelchair Accessible", "Gender-neutral restrooms"]
    df[access_types] = df[access_types].fillna(False)
    df['Accessibility'] = df[access_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
    df.drop(columns=access_types, inplace=True)
    # =========================================

    # -------------- DOGS -----------------
    df['Dogs Allowed'] = df['Dogs Allowed'] | ~df['Dogs Not Allowed'].fillna(False)
    df['Dogs_Allowed'] = df['Dogs Allowed'].mask(df['Dogs Allowed'] == False, np.nan)
    df.drop(columns=['Dogs Not Allowed', 'Dogs Allowed'], inplace=True)
    # =========================================

    # -------------- SMOKING -----------------
    df['Smoking'] = df['Smoking'].fillna(df['Smoking Allowed'])
    df.drop(columns=['Smoking Allowed', "Smoking Outside Only"], inplace=True)
    # =========================================

    # -------------- PACKING -----------------
    package_types = ["Plastic-free packaging", "Provides reusable tableware", "Compostable containers available", "Bring your own container allowed"]
    df[package_types] = df[package_types].fillna(False)
    df['Packaging'] = df[package_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
    df.drop(columns=package_types, inplace=True)
    # =========================================

    # -------------- RESERVATION TYPE -----------------
    df['Takes Reservations'] = df['Takes Reservations'].fillna(df['Reservations'])
    df.drop(columns='Reservations', inplace=True)
    res_types = ["By Appointment Only", "Walk-ins Welcome", "Takes Reservations"]
    df[res_types] = df[res_types].fillna(False)
    df['Reservation_Type'] = df[res_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
    df.drop(columns=res_types, inplace=True)
    # =========================================

    # -------------- SEATING -----------------
    seating_types = ["Outdoor Seating", "Heated Outdoor Seating", "Covered Outdoor Seating", "Private Dining", "Drive-Thru"]
    df[seating_types] = df[seating_types].fillna(False)
    df['Seating'] = df[seating_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
    df.drop(columns=seating_types, inplace=True)
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
    df[food_types] = df[food_types].fillna(False)
    df['Meal_Types'] = df[food_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
    df.drop(columns=food_types, inplace=True)
    # =========================================

    # -------------- MUSIC -----------------
    music_types = ["Live Music", "DJ", "Background Music", "Juke Box", "Karaoke"]
    df[music_types] = df[music_types].fillna(False)
    df['Music'] = df[music_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
    df.drop(columns=music_types, inplace=True)
    # =========================================

    # -------------- HAPPY HOUR -----------------
    df['Happy Hour'] = df['Happy Hour'].fillna(df['Happy Hour Specials'])
    df.drop(columns='Happy Hour Specials', inplace=True)
    alc_types = ["Alcohol", "Happy Hour", "Beer and Wine Only", "Full Bar"]
    df[alc_types] = df[alc_types].fillna(False)
    df['Alcohol_Options'] = df[alc_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
    df.drop(columns=alc_types, inplace=True)
    # =========================================

    # -------------- AMENITIES -----------------
    amenity_types = ["TV", "Pool Table", "Wi-Fi", "EV charging station available"]
    df[amenity_types] = df[amenity_types].fillna(False)
    df['Amenities'] = df[amenity_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
    df.drop(columns=amenity_types, inplace=True)
    df.drop(columns="Virtual restaurant", inplace=True)
    df.drop(columns="Waiter Service", inplace=True)
    # =========================================