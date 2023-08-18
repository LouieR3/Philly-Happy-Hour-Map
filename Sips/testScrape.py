import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import json
import PyPDF2

# Replace this with the actual URL of the bar's website
# base_url = 'https://www.doubleknotphilly.com'
base_url = 'http://www.barbuzzo.com/'
bar_name = "Uptown"
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
# response = requests.get("http://www.barbuzzo.com/Pdfs/barbuzzoBEVERAGE_MENU.pdf")
# soup = BeautifulSoup(response.content, 'html.parser')

# Find all links on the page
links = soup.find_all('a')
# Keywords to identify potential menu or drinks subpages
menu_keywords = ['menu', 'drinks', 'happy hour', 'happy-hour', 'beer', 'wine', 'cocktail', 'bier', 'beverage']
exclude_keywords = ['food', 'lunch', 'brunch', 'dinner', 'breakfast', 'entre', 'banquet', 'catering', 'dining', 'dessert']

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
print(subpage_urls)

target_keyword = "philadelphia"  # You can also use "philadelphia" as the keyword

target_url = None

for url in subpage_urls:
    if target_keyword in url:
        target_url = url
        break

# Modify subpage_urls to contain only the target URL if found
if target_url is not None:
    subpage_urls = [target_url]


# menu_items = []
# menu_prices = []
# bar_names = []
# json_keywords = ["beers", "draft", "drinks"]
# keywords = ["beers", "draft", "draught", "bottle", "cans", "wine", "cocktail"]
# for url in subpage_urls:
#     try:
#         menu_response = requests.get(url)
#         soup = BeautifulSoup(menu_response.content, 'html.parser')
#         for kw in keywords:
#             keyword_elements = soup.find_all(string=re.compile(kw), recursive=True)
#             print(keyword_elements)
#             for json_object in keyword_elements:
#                 data = json.loads(json_object)
#                 print(data)
#                 for keyword in json_keywords:
#                     print(keyword)
#                     print(keyword in json.dumps(data).lower())
#                 print()
#                 # print(matches)
#                 if 'menu' in json.dumps(data).lower() and any(keyword in json.dumps(data).lower() for keyword in json_keywords):
#                     print(url)
#                     print("---------------")
#                     print(data)
#                     entry = data['data']
#                     for section in entry:
#                         if any(keyword in section["name"].lower() for keyword in keywords):
#                             for section in section["sections"]:
#                                 for item in section["items"]:
#                                     menu_item = item["name"]
#                                     # menu_price = item["choices"][0]["prices"]["min"]
#                                     menu_price = '${:,.2f}'.format(item["choices"][0]["prices"]["min"])
#                                     menu_items.append(menu_item)
#                                     menu_prices.append(menu_price)
#     except Exception as e:
#         print(f'An error occurred for url {url}: {e}')
#         pass

# for url in subpage_urls:
#     print(url)
#     print()
#     try:
#         menu_response = requests.get(url)
#         soup = BeautifulSoup(menu_response.content, 'html.parser')

#         divs_with_item_class = soup.find_all('div', class_=lambda cls: cls and 'item' in cls)

#         # Print the found divs
#         for div in divs_with_item_class:
#             print(div)
#         # print(soup)
#         tags = soup.find_all(['h1', 'h2', 'h3', 'div'])

#         for tag in tags:
#             if any(keyword in tag.text.lower() for keyword in menu_keywords):
#                 next_elem = tag.find_next_sibling()
#                 if next_elem:
#                     # Get menu items from li, p, div tags
#                     items = next_elem.find_all(['li', 'p', 'div'])
#                     menu_items.extend([item.text for item in items])

#                     # Get prices from span + li, p, div tags 
#                     prices = next_elem.find_all(['span', 'li', 'p', 'div'], class_='price')
#                     menu_prices.extend([price.text for price in prices])
                
#         bar_names.extend([bar_name] * len(menu_items))
#         # Extract prices
#         # for item in beers:
#         #     price = item.find_next(class_='price').text
#         #     menu_items.append(item.text)  
#         #     menu_prices.append(price)
#         #     bar_names.append(bar_name)
#     except Exception as e:
#         print(f'An error occurred for url {url}: {e}')
#         pass
# print()
# print(bar_names)

# Create a dataframe from the collected data
# menu_df = pd.DataFrame({
#     'Bar': bar_name,
#     'Drink': menu_items,
#     'Price': menu_prices
# })

# # Display the dataframe
# print(menu_df)