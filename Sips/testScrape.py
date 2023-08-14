import requests
from bs4 import BeautifulSoup

# Replace this with the actual URL of the bar's website
base_url = 'https://www.doubleknotphilly.com'
base_url = 'http://vedaphilly.com'

# Make a request to the bar's website
response = requests.get(base_url)
soup = BeautifulSoup(response.content, 'html.parser')

# Find all links on the page
links = soup.find_all('a')
# print(links)
# Keywords to identify potential menu or drinks subpages
menu_keywords = ['menu', 'drinks', 'happy hour', 'happy-hour']

# List to store subpage URLs
subpage_urls = []

# Iterate through each link and check for keywords
for link in links:
    try:
        href = link.get('href')
        if any(keyword in href.lower() for keyword in menu_keywords):
            # Construct the full URL of the subpage
            subpage_url =  href
            subpage_urls.append(subpage_url)
    except:
        pass
subpage_urls = list(set(subpage_urls))
# Print the identified subpage URLs
for url in subpage_urls:
    url = url.replace(".com//", ".com/")
    print(url)
    menu_response = requests.get(url)
    soup = BeautifulSoup(menu_response.content, 'html.parser')