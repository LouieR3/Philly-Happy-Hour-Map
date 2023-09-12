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

url = 'https://centercityphila.org/explore-center-city/ccd-restaurant-week/list-view#barbuzzo'
# url = 'https://centercityphila.org/explore-center-city/ccd-restaurant-week/list-view#blume-food-cocktail'

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


# Get the HTML content of the modal element
modal_html = modal.get_attribute("outerHTML")

# Use Beautiful Soup to parse the HTML content
soup = BeautifulSoup(modal_html, "html.parser") # type: ignore

# Now you can search and manipulate the HTML content using Beautiful Soup
# For example, to find all <a> elements within the modal:
open_table_links = soup.find_all('a', class_='o-button--openTable')
# print(open_table_links)
print(open_table_links[0].get('href'))
# Loop through the links and print their text and href attributes
rich_text = soup.select_one('.apos-rich-text')
if rich_text:
    rich_text_links = rich_text.find_all('a')

    # print(rich_text_links)
    print(rich_text_links[0].get('href'))