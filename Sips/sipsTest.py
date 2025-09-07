import pandas as pd
from yelpapi import YelpAPI
import yelpapi
import requests
import json
import html
import re
from bs4 import BeautifulSoup
import time
import numpy as np
from selenium import webdriver
from selenium.webdriver.common.by import By
from geopy.geocoders import Nominatim

# ------------------------------------------------
# This script does = Clear out old SIPS, add in the new and any new bars needed
# ------------------------------------------------
start_time = time.time()

csv_df = pd.read_csv('../Csv/MasterTable.csv')
csv_df = csv_df.loc[csv_df['SIPS_PARTICIPANT'] == 'Y']

def scrapeSipsPage():
    html = "https://centercityphila.org/explore-center-city/ccd-sips/sips-list-view"
    base_html = "https://centercityphila.org"
    source = requests.get(html).text
    soup = BeautifulSoup(source, "lxml")

    bars = []
    pages= []
    pager = soup.find('div', class_='c-pager')
    for link in pager.find_all('a'): # type: ignore
        pages.append(base_html + link['href'])
    print(pages)

    pattern = r'apos\.maps\["ccd-places"\]\.addMap\((.*?)\)'
    bar_info_list = []
    for page in pages:
        # Request and parse HTML for each page 
        page_html = requests.get(page, allow_redirects=False).text
        soupIter = BeautifulSoup(page_html, 'lxml')
        # print(soupIter.find_all('tr')[1])
        for card in soupIter.find_all('tr'):
            try:
                title = card.find('a', class_='o-text-link').text.strip("\n        ")
                url = html + card.find('a', class_='o-card-link')['href']
                address = card.find('td', attrs={'data-th': 'Address'}).text.strip()
                bars.append([title, address, url])
            except AttributeError:
                continue

    # Create dataframe  
    df = pd.DataFrame(bars, columns=['Name', 'Address', 'SIPS_URL'])

    # print(df)
    # mask = df['Address'].str.contains('Philadelphia')
    # df = df[mask]
    df = df.reset_index(drop=True)
    df = df.drop_duplicates(subset=['Name'])

    # Function to clean address strings
    def clean_address(address):
        address = address.replace("Philadelphia PA,", "Philadelphia, PA")
        address = address.replace("t Philadelphia", "t, Philadelphia")
        address = address.replace("Philadelphia PA", "Philadelphia, PA")
        address = address.replace("PA,", "PA")
        address = address.replace("St. ,", "St.,")
        address = address.replace("Philadephia", "Philadelphia")
        address = address.replace("1421 Sansom Street", "1421 Sansom St, Philadelphia, PA 19110")
        return address
    # Apply the function to the 'Address' column
    df['Address'] = df['Address'].apply(clean_address)
    # Function to clean address strings
    def clean_name(name):
        name = name.replace("*", "")
        return name
    # Apply the function to the 'Address' column
    df['Name'] = df['Name'].apply(clean_name)
    # print(df)

    pattern = r'apos\.maps\["ccd-places"\]\.addMap\((.*?)\)'
    bar_info_list = []
    for page in pages:
        page_html = requests.get(page, allow_redirects=False).text
        soupIter = BeautifulSoup(page_html, 'lxml')
        script_tags = soupIter.find_all('script', text=re.compile(pattern))

        json_data = {}
        for script_tag in script_tags:
            lines = script_tag.string.splitlines()
            for line in lines:
                if re.match(pattern, line.strip()):
                    # Extract the JSON text from the line
                    start_index = line.find('{')
                    end_index = line.rfind('}') + 1
                    json_text = line[start_index:end_index]
                    json_data = json.loads(json_text)
                    break
            if json_data is not None:
                break

        for item in json_data["items"]:
            title = item.get("title", "")
            url_website = item.get("urlWebsite", "")
            if url_website:
                url_website = url_website.rstrip('/')
            bar_info = {"Name": title, "Website": url_website}
            # print(bar_info)
            bar_info_list.append(bar_info)

    new_df = pd.DataFrame(bar_info_list)
    # Print the resulting DataFrame with the new "Bar Website" column
    merged_df = df.merge(new_df, on='Name', how='left')
    print(merged_df)
    df = merged_df

    print(df)
    return df

site_df = scrapeSipsPage()

modal_df = site_df

merge_df = modal_df.merge(csv_df, on=['Name', 'Address'], how='left', indicator=True, suffixes=('', '_csv'))
# Create sub-df for records where 'Name' and 'Address' are in both DataFrames
in_both_df = merge_df[merge_df['_merge'] == 'both'].drop(columns=[col for col in merge_df.columns if col.endswith('_csv') or col == '_merge'])
# Create sub-df for records where 'Name' and 'Address' are only in the original df
not_in_csv_df = merge_df[merge_df['_merge'] == 'left_only'].drop(columns=[col for col in merge_df.columns if col.endswith('_csv') or col == '_merge'])

# not_in_csv_df["SIPS_PARTICIPANT"] = "Y"

# Display the sub-dataframes (for verification)
print("Records in both DataFrames:")
print(in_both_df)
print("\nRecords not in the csv DataFrame:")
print(not_in_csv_df)
