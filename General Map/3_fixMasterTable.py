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

# ------------------------------------------------
# This script does = Gets the information from each Restaurant from yelp
# ------------------------------------------------
start_time = time.time()

df = pd.read_csv('../Csv/MasterTable.csv')
print(df.columns)

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
# df[minority_types] = df[minority_types].fillna(False)
# df['Minority_Owned'] = df[minority_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
df.drop(columns=minority_types, inplace=True)
# =========================================

# -------------- GOOD FOR -----------------
df['Good For Groups'] = df['Good For Groups'].fillna(df['Good for Groups'])
df.drop(columns='Good for Groups', inplace=True)
df.drop(columns='Good For Working.1', inplace=True)
# def good_for(row):
#     good_for_types = ["Good For Dinner","Good For Kids","Good For Lunch","Good For Dancing","Good For Working","Good For Brunch","Good For Dessert","Good For Breakfast","Good For Groups","Good For Late Night", "All Ages", "Late Night"]
#     for good_for in good_for_types:
#         if row[good_for]:
#             return good_for.split("Good For ")[1]
#     return None
# # Apply the function to create the column
# df['Good_For'] = df.apply(good_for, axis=1) # type: ignore
good_for_types = ["Good For Dinner","Good For Kids","Good For Lunch","Good For Dancing","Good For Working","Good For Brunch","Good For Dessert","Good For Breakfast","Good For Groups","Good For Late Night", "All Ages", "Late Night"]

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
# df[package_types] = df[package_types].fillna(False)
# df['Packaging'] = df[package_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
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
print(df)
print(df.columns)
# =========================================

df.to_csv("MasterTableNew.csv", index=False)

print("Progam finished --- %s seconds ---" % (time.time() - start_time))
