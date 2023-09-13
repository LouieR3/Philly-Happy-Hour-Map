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
# ------------------------------------------------
# This script does = Opens each sips bar modal for its information
# ------------------------------------------------

# url = 'https://centercityphila.org/explore-center-city/ccd-sips/list-view#cavanaugh-s-rittenhouse'

csvName = "RestaurantWeek.csv"
df = pd.read_csv(csvName)

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

    # Extract "Details" and "Deals Offered"
    start_index_details = deals.find("Restaurant Week Details\n") + len("Restaurant Week Details\n")
    end_index_details = deals.find("\n", start_index_details)
    details = deals[start_index_details:end_index_details]

    # Find the start index of "RESTAURANT WEEK MENU:"
    start_index_deals = deals.find("RESTAURANT WEEK MENU: ")
    
    if start_index_deals != -1:
        start_index_deals += len("RESTAURANT WEEK MENU: ")
        # Check if there is a newline character after "RESTAURANT WEEK MENU:"
        end_index_deals = deals.find("\n", start_index_deals)
        if end_index_deals != -1:
            deals_offered = deals[start_index_deals:end_index_deals]
        else:
            # If there is no newline character, take the substring until the end of the string
            deals_offered = deals[start_index_deals:]
    else:
        deals_offered = None

    modal_html = modal.get_attribute("outerHTML")
    # Use Beautiful Soup to parse the HTML content
    soup = BeautifulSoup(modal_html, "html.parser") # type: ignore
    # Get open table link
    open_table_links = soup.find_all('a', class_='o-button--openTable')
    try:
        open_table_link = open_table_links[0].get('href')
    except:
        open_table_link = None

    # Get menu link  
    rich_text = soup.select_one('.apos-rich-text')
    if rich_text:
        rich_text_links = rich_text.find_all('a')
        try:
            deal_website = rich_text_links[0].get('href')
        except:
            deal_website = None
    else:
        deal_website = None


    # Append the extracted information to the list
    deals_list.append({
        'Restaurant Name': bar,
        'Details': details,
        'Deals Offered': deals_offered,
        'Deal Website': deal_website,
        'Open Table Link': open_table_link
    })

    print({
        'Restaurant Name': bar,
        'Details': details,
        'Deals Offered': deals_offered,
        'Deal Website': deal_website,
        'Open Table Link': open_table_link
    })

    driver.quit()
# driver.quit()
csvName = "RestaurantWeek.csv"
df = pd.read_csv(csvName)
new_df = pd.DataFrame(deals_list)
merged_df = df.merge(new_df, on='Restaurant Name', how='left')
# Write the updated DataFrame to the same CSV file
merged_df.to_csv("RestaurantWeek2.csv", index=False)