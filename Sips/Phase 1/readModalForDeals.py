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
from PyPDF2 import PdfReader
from io import BytesIO

# ------------------------------------------------
# This script does = Opens each sips bar modal for its information
# ------------------------------------------------

url = 'https://centercityphila.org/explore-center-city/ccd-sips/sips-list-view#lucys-bar'

# df = pd.read_csv('../Csv/AllSipsLocations.csv')

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
# Get content
content = modal.find_element(By.CSS_SELECTOR, '.apos-rich-text')

# Check if content contains a <p> with an <a> tag
try:
    link_element = content.find_element(By.CSS_SELECTOR, 'p > a')
    if link_element.text.strip() == "View SIPS menu":
        deals = link_element.get_attribute('href')  # Get the link
    else:
        deals = content.text  # Get the text content
except:
    deals = content.text  # Fallback to text content if no <a> tag is found

print(deals)
driver.quit()

AG
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
df['Cocktails'] = cocktails
df['Wine'] = wine
df['Beer'] = beer
df['Half-Priced Appetizers'] = appetizers

# Drop the original 'Deals' column
df.drop(columns=['Deals'], inplace=True)

# Write the updated DataFrame to the same CSV file
df.to_csv('../Csv/AllSipsLocations.csv', index=False)
