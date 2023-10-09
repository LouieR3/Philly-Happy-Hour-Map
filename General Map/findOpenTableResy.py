import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin
import time 

start_time = time.time()

# Function to check for OpenTable or Resy links on a webpage
def check_links(url):
    try:
        response = requests.get(url)
        # print(response.status_code)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            open_table_link = soup.find('a', {'href': lambda x: x and 'opentable' in x.lower()})
            resy_link = soup.find('a', {'href': lambda x: x and 'resy' in x.lower()})
            third_link = soup.find('a', {'href': lambda x: x and 'exploretock' in x.lower()})
            
            if open_table_link:
                return open_table_link.get('href') # type: ignore
            elif resy_link:
                return resy_link.get('href') # type: ignore
            elif third_link:
                return third_link.get('href') # type: ignore
            else:
                # If neither OpenTable nor Resy links found, check for a reservations page
                reservations_page = soup.find('a', {'href': lambda x: x and 'reservations' in x.lower()})
                print()
                # print(reservations_page)
                if reservations_page:
                    # If a reservations page is found, try to extract links from there
                    reservations_url = reservations_page.get('href') # type: ignore
                    print(reservations_url)
                    reservations_url = urljoin(url, reservations_url) # type: ignore
                    print(reservations_url)
                    print("-------------")
                    reservations_response = requests.get(reservations_url) # type: ignore
                    # print(reservations_response.status_code)
                    if reservations_response.status_code == 200:
                        reservations_soup = BeautifulSoup(reservations_response.text, 'html.parser')
                        open_table_link = reservations_soup.find('a', {'href': lambda x: x and 'opentable' in x.lower()})
                        resy_link = reservations_soup.find('a', {'href': lambda x: x and 'resy' in x.lower()})
                        third_link = soup.find('a', {'href': lambda x: x and 'exploretock' in x.lower()})
                        if open_table_link:
                            return open_table_link.get('href') # type: ignore
                        elif resy_link:
                            return resy_link.get('href') # type: ignore
                        elif third_link:
                            return third_link.get('href') # type: ignore
                        else:
                            return reservations_url
                    else:
                        return reservations_url
            return None
        else:
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None

# List of bars with their websites
df = pd.read_csv("MasterTable.csv")

# result = check_links("http://www.akitchenandbar.com/")
# print(result)

# Check OpenTable and Resy links for each bar
for index, row in df.iterrows():
    if pd.isna(row['Open Table Link']) or row['Open Table Link'] == "":
        website_url = row['Website']
        if pd.isna(row['Website']) == False:
            result = check_links(website_url)
            time.sleep(0.2)
            if result is None:
                print(row['Name'])
                print(row['Website'])
                print("-------------")
                print(result)
                print("-------------")
                print()
            df.at[index, 'Open Table Link'] = result

df.to_csv("UpdatedMasterTable.csv", index=False)

print("Progam finished --- %s seconds ---" % (time.time() - start_time))