import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import json

# Replace this with the actual URL of the bar's website
base_url = 'https://www.doubleknotphilly.com'
base_url = 'http://www.tirnanogphilly.com'
bar_name = "Tir Na Nog Irish Bar & Grill"
# Make a request to the bar's website
response = requests.get(base_url)
soup = BeautifulSoup(response.content, 'html.parser')

# Find all links on the page
links = soup.find_all('a')
# print(links)
# Keywords to identify potential menu or drinks subpages
keywords = ["beer", "draft", "draught", "bottle", "cans", "wine", "cocktail"]

# List to store subpage URLs
subpage_urls = []

# Iterate through each link and check for keywords
response = requests.get(base_url)
soup = BeautifulSoup(response.content, 'html.parser')

# Find all links on the page
links = soup.find_all('a')
# Keywords to identify potential menu or drinks subpages
menu_keywords = ['menu', 'drinks', 'happy hour', 'happy-hour', 'beer', 'wine', 'cocktail']
exclude_keywords = ['food', 'lunch', 'dinner', 'breakfast', 'entre', 'banquet', 'catering', 'dining', 'dessert']

# List to store subpage URLs
subpage_urls = []
# Iterate through each link and check for keywords
for link in links:
    try:
        href = link.get('href')
        if any(keyword in href.lower() for keyword in menu_keywords) and not any(exclude_keyword in href.lower() for exclude_keyword in exclude_keywords):
            # Construct the full URL of the subpage
            if "http" in href:
                subpage_url = href
            else:
                if href and not href.startswith('/'):
                    href = '/' + href
                subpage_url = base_url + href
            subpage_url = subpage_url.rstrip("/")
            subpage_urls.append(subpage_url)
    except:
        pass

if len(subpage_urls) == 0:
    subpage_urls.append(base_url)

subpage_urls = list(set(subpage_urls))

menu_items = []
menu_prices = []
bar_names = []
# Print the identified subpage URLs
for url in subpage_urls:
    print(url)
    print()
    try:
        menu_response = requests.get(url)
        soup = BeautifulSoup(menu_response.content, 'html.parser')
        for kw in keywords:
            keyword_elements = soup.find_all(string=re.compile(kw), recursive=True)
            print(kw)
            print("-----------")
            # print(keyword_elements)
            print()
            for json_object in keyword_elements:
                data = json.loads(json_object)
                # print(json_data)
                print(type(data))
                if 'menu' in json.dumps(data).lower():
                    entry = data['data']
                    for section in entry:
                        if any(keyword in section["name"].lower() for keyword in keywords):
                            for section in section["sections"]:
                                for item in section["items"]:
                                    menu_item = item["name"]
                                    # menu_price = "$" + str(float(item["choices"][0]["prices"]["min"]))
                                    menu_price = '${:,.2f}'.format(item["choices"][0]["prices"]["min"])
                                    menu_items.append(menu_item)
                                    menu_prices.append(menu_price)

                # print(data['data'])
                # for section in entry["sections"]:
                #     if any(keyword in section["name"].lower() for keyword in keywords):
                #         for item in section["items"]:
                #             menu_item = item["name"]
                #             menu_price = item["choices"][0]["prices"]["min"]
                #             menu_items.append(menu_item)
                #             menu_prices.append(menu_price)



        # for element in keyword_elements:
        #     # Get the parent element that contains the item and price
        #     parent_element = element.parent
        #     if parent_element:
        #         menu_item = parent_element.get_text(strip=True)
        #         menu_price = parent_element.find_next('span', class_='price').get_text(strip=True)
        #         menu_items.append(menu_item)
        #         menu_prices.append(menu_price)

        # for kw in keywords:
        #     keyword_elements = soup.find_all(string=re.compile(kw), recursive=True)
        #     print(kw)
        #     print("-----------")
        #     print(keyword_elements)
        #     print()
        #     print(type(keyword_elements))
        #     for element in keyword_elements:
        #         # Get the parent element that contains the item and price
        #         parent_element = element.parent
        #         if parent_element:
        #             menu_item = parent_element.get_text(strip=True)
        #             menu_price = parent_element.find_next('span', class_='price').get_text(strip=True)
        #             menu_items.append(menu_item)
        #             menu_prices.append(menu_price)
    except Exception as e:
        print(f'An error occurred for url {url}: {e}')
        pass

# Create a dataframe from the collected data
menu_df = pd.DataFrame({
    'Bar': bar_name,
    'Menu Item': menu_items,
    'Price': menu_prices
})

# Display the dataframe
print(menu_df)