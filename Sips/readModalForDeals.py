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

url = 'https://centercityphila.org/explore-center-city/ccd-sips/sips-list-view#cavanaugh-s-rittenhouse'

df = pd.read_csv('AllSipsLocations.csv')

# driver = webdriver.Chrome()

# Create an empty list to store the extracted "Deals" content
deals_list = []

# Loop through each row in the DataFrame
for index, row in df.iterrows():
    # Get the URL value for each row
    url = row['Url']

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
df.to_csv('Test.csv', index=False)