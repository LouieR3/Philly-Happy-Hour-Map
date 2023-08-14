import requests
from bs4 import BeautifulSoup
import pandas as pd

# Replace this with the actual URL of the bar's website
base_url = 'https://www.doubleknotphilly.com'
base_url = 'http://www.drinkersrittenhouse.com/'

df = pd.read_csv('AllSipsLocations.csv')

html = "https://centercityphila.org/explore-center-city/ccd-sips/sips-list-view"
base_html = "https://www.yelp.com/menu/"
source = requests.get(html).text
soup = BeautifulSoup(source, "lxml")

menu_data = []
keywords = ["beers", "bottles", "cans", "wines", "cocktails"]

for base_url in df['Bar Website']:
    if pd.notna(base_url):
        print(base_url)
        try:
            # Make a request to the bar's website
            response = requests.get(base_url)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find all links on the page
            links = soup.find_all('a')
            # print(links)
            # Keywords to identify potential menu or drinks subpages
            menu_keywords = ['menu', 'drinks', 'happy hour', 'happy-hour']
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
                        subpage_urls.append(subpage_url)
                except:
                    pass
            subpage_urls = list(set(subpage_urls))
            # Print the identified subpage URLs
            for url in subpage_urls:
                print(url)
                try:
                    menu_response = requests.get(url)
                    soup = BeautifulSoup(menu_response.content, 'html.parser')
                except Exception as e:
                    print(f'An error occurred for url {url}: {e}')
                    pass
            print()
        except requests.exceptions.RequestException as e:
            print(f'An error occurred for base_url {base_url}: {e}')
            print("--------------------------------------------")
            print()
            pass