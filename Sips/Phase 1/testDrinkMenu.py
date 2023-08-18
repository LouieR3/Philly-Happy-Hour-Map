import pandas as pd
from yelpapi import YelpAPI
import yelpapi
from bs4 import BeautifulSoup
import requests
import time
import os

# Assuming you have the DataFrame 'df' with the 'Deals' column
df = pd.read_csv('AllSipsLocations2.csv')

html = "https://centercityphila.org/explore-center-city/ccd-sips/sips-list-view"
base_html = "https://www.yelp.com/menu/"
source = requests.get(html).text
soup = BeautifulSoup(source, "lxml")
alias = "cavanaughs-rittenhouse-philadelphia-2"
alias = "the-black-sheep-pub-and-restaurant-philadelphia"
cocktail_url = f'https://www.yelp.com/menu/{alias}/drink-menu'
try:
    cocktail_page = requests.get(cocktail_url, allow_redirects=False)
    if cocktail_page.status_code != 301 and 'location' in cocktail_page.headers:
        cocktail_soup = BeautifulSoup(cocktail_page.content, 'html.parser')
        print(cocktail_soup)
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 301:
        print(f"Redirect encountered for {cocktail_url}. Skipping...")
    else:
        print(f'An error occurred for alias {alias}: {e}')