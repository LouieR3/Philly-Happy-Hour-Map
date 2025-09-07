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

# ------------------------------------------------
# This script does = Opens each sips bar modal for its information
# ------------------------------------------------

url = 'https://centercityphila.org/explore-center-city/ccd-sips/sips-list-view#cavanaugh-s-rittenhouse'

df = pd.read_csv('../Csv/Sips2024.csv')
print(df[["Name", "SIPS_BEER", "SIPS_COCKTAILS"]].head(3))
df = pd.read_csv('../Csv/MasterTableApr.csv')
print(df[["Name", "SIPS_BEER", "SIPS_COCKTAILS"]].head(3))
df = pd.read_csv('../Csv/MasterTable.csv')
print(df[["Name", "SIPS_BEER", "SIPS_COCKTAILS"]].head(3))


dsfg
df = df.head(1)

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

# driver.quit()

# Add the "Deals" content to the DataFrame as a new column
df['Deals'] = deals_list

# Save the updated DataFrame back to the CSV file with the same name
# df.to_csv('../Csv/AllSipsLocations.csv', index=False)
# df = pd.read_csv('AllSipsOriginal.csv')
# Initialize empty lists for each deal type
cocktails = []
wine = []
beer = []
appetizers = []

def prepare_for_csv(text):
    # Replace commas with " + " in cocktail text
    text = re.sub(r', ', ' + ', text)
    # Enclose the text in double quotes and escape existing double quotes
    return f'''"{text.replace('"', '""')}"'''

# Iterate through each row in the DataFrame
for row in df.itertuples():
    # Use regular expressions to extract data for each deal type
    cocktails_match = re.search(r'\$7 Cocktails(.*?)\$6 Wine', row.Deals, re.DOTALL) # type: ignore
    wine_match = re.search(r'\$6 Wine(.*?)\$5 Beer', row.Deals, re.DOTALL) # type: ignore
    beer_match = re.search(r'\$5 Beer(.*?)Half-Priced Appetizers', row.Deals, re.DOTALL) # type: ignore
    appetizers_match = re.search(r'Half-Priced Appetizers(.*?)$', row.Deals, re.DOTALL) # type: ignore
    # Append extracted data to respective lists
    if cocktails_match:
        cocktails_text = cocktails_match.group(1).strip()
        # Replace commas with " + "
        cocktails_text = prepare_for_csv(cocktails_text)
        # Append to the cocktails list
        cocktails.append(cocktails_text)
        print(cocktails_text)
    else:
        cocktails.append(None)
    if wine_match:
        wine_text = wine_match.group(1).strip()
        # Replace commas with " + "
        wine_text = prepare_for_csv(wine_text)
        # Append to the cocktails list
        wine.append(wine_text)
    else:
        wine.append(None)
    if beer_match:
        beer_text = beer_match.group(1).strip()
        # Replace commas with " + "
        beer_text = prepare_for_csv(beer_text)
        # Append to the cocktails list
        beer.append(beer_text)
    else:
        beer.append(None)
    if appetizers_match:
        app_text = appetizers_match.group(1).strip()
        # Replace commas with " + "
        app_text = prepare_for_csv(app_text)
        # Append to the cocktails list
        appetizers.append(app_text)
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

print(df)

# Write the updated DataFrame to the same CSV file
df.to_csv('../Csv/TestModal.csv', index=False)
