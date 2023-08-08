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

menu_items = []
menu_prices = []

for alias in df['Yelp Alias']:
    url = f'https://www.yelp.com/menu/{alias}'
    coktail_url = f'https://www.yelp.com/menu/{alias}/drink-menu'
    food_url = f'https://www.yelp.com/menu/{alias}/main-menu'

    try:
        page = requests.get(url)
        soup = BeautifulSoup(page.content, 'html.parser')

        for item in soup.find_all('div', class_='menu-item'):
            name = item.h4.text.strip()  # Strip extra tabs and new lines
            price = item.find('li', class_='menu-item-price-amount').text.strip()
            print(name)
            print(price)
            yelp_data = {
                'Yelp Alias': alias,
                'Menu Item': name,
                'Price': price
            }
        print()
    except:
        yelp_data = {
            'Yelp Alias': alias,
            'Menu Item': None,
            'Price': None
        }

menu_df = pd.DataFrame({
  'Item': menu_items,
  'Price': menu_prices
})
print(menu_df)