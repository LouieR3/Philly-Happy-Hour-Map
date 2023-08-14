import pandas as pd
from yelpapi import YelpAPI
import yelpapi
from bs4 import BeautifulSoup
import requests
import time
import os

# Assuming you have the DataFrame 'df' with the 'Deals' column
df = pd.read_csv('AllSipsLocations.csv')

html = "https://centercityphila.org/explore-center-city/ccd-sips/sips-list-view"
base_html = "https://www.yelp.com/menu/"
source = requests.get(html).text
soup = BeautifulSoup(source, "lxml")

menu_data = []
keywords = ["beers", "bottles", "cans", "wines", "cocktails"]

for alias in df['Yelp Alias']:
    url = f'https://www.yelp.com/menu/{alias}'
    cocktail_url = f'https://www.yelp.com/menu/{alias}/drink-menu'
    
    try:
        page = requests.get(url)
        soup = BeautifulSoup(page.content, 'html.parser')
        print(f"Soup created successfully for {url}")
        print("------------------------")
        test = soup.find_all("h2", class_="alternate")
        print(test)
        for keyword in keywords:
            keyword_section = soup.find("h2", text=lambda text: keyword in text.lower(), class_="alternate")
            if keyword_section:
                section_divs = keyword_section.find_all_next("div", class_="menu-item menu-item-no-photo menu-item-placeholder-photo")
                for section_div in section_divs:
                    print(section_div.find_all('div', class_='menu-item-details')) # type: ignore
                    for item in section_div.find_all('div', class_='menu-item-details'): # type: ignore
                        print()
                        name = item.h4.text.strip()  # Strip extra tabs and new lines
                        prices_div = item.find_next_sibling('div', class_='menu-item-prices')
                        if prices_div:
                            price_elem = prices_div.find('li', class_='menu-item-price-amount')
                            price = price_elem.text.strip() if price_elem else "Price not available"
                        else:
                            price = "Price not available"
                        menu_data.append({
                            'Bar': df.loc[df['Yelp Alias'] == alias, 'Bar Name'].iloc[0], # type: ignore
                            'Menu Item': name,
                            'Price': price
                        })
    except Exception as e:
        print(f'An error occurred for alias {alias}: {e}')
        pass

    try:
        cocktail_page = requests.get(cocktail_url)
        if cocktail_page.status_code != 301 and 'location' in cocktail_page.headers:
            cocktail_soup = BeautifulSoup(cocktail_page.content, 'html.parser')
            print(f"Soup created successfully for {cocktail_url}")

            for item in cocktail_soup.find_all('div', class_='menu-item-details'): # type: ignore
                print("==================================")
                print()
                name = item.h4.text.strip()  # Strip extra tabs and new lines
                prices_div = item.find_next_sibling('div', class_='menu-item-prices')
                if prices_div:
                    price_elem = prices_div.find('li', class_='menu-item-price-amount')
                    price = price_elem.text.strip() if price_elem else "Price not available"
                else:
                    price = "Price not available"
                menu_data.append({
                    'Bar': df.loc[df['Yelp Alias'] == alias, 'Bar Name'].iloc[0], # type: ignore
                    'Menu Item': name,
                    'Price': price
                })
    except Exception as e:
        print(f'An error occurred for alias {alias}: {e}')
        pass

menu_df = pd.DataFrame(menu_data)
# Read 'SipsBarItems.csv' into a DataFrame
sips_bar_items_df = pd.read_csv('SipsBarItems.csv')

# Combine menu_df and sips_bar_items_df
combined_df = pd.concat([sips_bar_items_df, menu_df])

# Drop duplicates based on 'Bar', 'Menu Item', and 'Price'
combined_df.drop_duplicates(subset=['Bar', 'Menu Item', 'Price'], inplace=True)

# Write the combined DataFrame to a new CSV file
combined_df.to_csv('SipsBarItems.csv', index=False)
print(menu_df)