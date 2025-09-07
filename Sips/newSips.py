from io import BytesIO
import PyPDF2
import fitz
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
geolocator = Nominatim(timeout=10, user_agent="my_app") # type: ignore

def clearOldSips(df):
    # List of columns to be updated
    columns_to_update = [
        'SIPS_URL',
        'SIPS_COCKTAILS',
        'SIPS_WINE',
        'SIPS_BEER',
        'SIPS_HALFPRICEDAPPS'
    ]

    # Update specified columns to empty strings where SIPS_PARTICIPANT is "Y"
    df.loc[df['SIPS_PARTICIPANT'] == 'Y', columns_to_update] = np.nan
    # Change SIPS_PARTICIPANT from "Y" to "N"
    df.loc[df['SIPS_PARTICIPANT'] == 'Y', 'SIPS_PARTICIPANT'] = 'N'
    # Optionally, save the modified DataFrame back to a CSV file
    # df.to_csv('../Csv/ModifiedMasterTable.csv', index=False)
    # Display the modified DataFrame (for verification)
    return df

csv_df = clearOldSips(csv_df)

def scrapeSipsPage(geolocator):
    html = "https://centercityphila.org/explore-center-city/ccd-sips/sips-list-view"
    base_html = "https://centercityphila.org"

    bars = []
    pages= []
    pages = set()
    page_number = 1
    while True:
        source = requests.get(html + f"?page={page_number}").text
        soup = BeautifulSoup(source, "lxml")
        pager = soup.find('div', class_='c-pager')

        if not pager:
            break  # Exit loop if there's no pager
        for link in pager.find_all('a'): # type: ignore
            pages.add(base_html + link['href'])

        page_number += 1
    # Convert URLs to integers, sort, and convert back to strings
    pages = sorted(pages, key=lambda x: int(x.split("=")[-1]))
    print(pages)
    # pages = ['https://centercityphila.org/explore-center-city/ccd-sips/sips-list-view?page=5']

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
    # Print the resulting DataFrame with the new "Website" column
    # print(new_df)
    # df = pd.read_csv('../Csv/AllSipsLocations.csv')
    merged_df = df.merge(new_df, on='Name', how='left')
    print(merged_df)
    merged_df.to_csv("AllSipsLocations.csv", index=False)
    df = merged_df

    MAX_ATTEMPTS = 5
    def find_location(row):
        place = row['Address'].replace("Ben Franklin", "Benjamin Franklin")
        print(place)
        attempts = 0
        while attempts < MAX_ATTEMPTS:
            try:
                location = geolocator.geocode(place)
                # print(location)
                return location.latitude, location.longitude # type: ignore
            except:
                attempts += 1
                time.sleep(1)
        print()
        return None, None
    df[['Latitude','Longitude']] = df.apply(find_location, axis="columns", result_type="expand")
    print(df)
    return df

site_df = scrapeSipsPage(geolocator)

def readModalForDeals(df):
    # url = 'https://centercityphila.org/explore-center-city/ccd-sips/sips-list-view#lucys-bar'
    # driver = webdriver.Chrome()
    # Create an empty list to store the extracted "Deals" content
    deals_list = []

    # Loop through each row in the DataFrame
    for index, row in df.iterrows():
        # Get the URL value for each row
        url = row['SIPS_URL']
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
        # Check if content contains a <p> with an <a> tag
        try:
            link_element = content.find_element(By.CSS_SELECTOR, 'p > a')
            if "View SIPS menu" in link_element.text.strip():
                deals = link_element.get_attribute('href')  # Get the link
            else:
                deals = content.text  # Get the text content
        except:
            deals = content.text  # Fallback to text content if no <a> tag is found

        # Append the extracted "Deals" content to the list
        deals_list.append(deals)
        driver.quit()

    # Add the "Deals" content to the DataFrame as a new column
    df['Deals'] = deals_list

    # Save the updated DataFrame back to the CSV file with the same name
    # df.to_csv('../Csv/AllSipsLocations.csv', index=False)
    # df = pd.read_csv('AllSipsOriginal.csv')
    # Initialize empty lists for each deal type
    cocktails = []
    wine = []
    beer = []
    appetizers = []

    # Iterate through each row in the DataFrame
    for row in df.itertuples():
        # Use regular expressions to extract data for each deal type
        cocktails_match = re.search(r'\$7 Cocktails(.*?)\$6 Wine', row.Deals, re.DOTALL) # type: ignore
        wine_match = re.search(r'\$6 Wine(.*?)\$5 Beer', row.Deals, re.DOTALL) # type: ignore
        beer_match = re.search(r'\$5 Beer(.*?)Half-Priced Appetizers', row.Deals, re.DOTALL) # type: ignore
        appetizers_match = re.search(r'Half-Priced Appetizers(.*?)$', row.Deals, re.DOTALL) # type: ignore
        # Append extracted data to respective lists
        if cocktails_match:
            cocktails.append(cocktails_match.group(1).strip())
        else:
            cocktails.append(None)
        if wine_match:
            wine.append(wine_match.group(1).strip())
        else:
            wine.append(None)
        if beer_match:
            beer.append(beer_match.group(1).strip())
        else:
            beer.append(None)
        if appetizers_match:
            appetizers.append(appetizers_match.group(1).strip())
        else:
            appetizers.append(None)

    # Create a new DataFrame with the extracted data
    # Add the new columns to the DataFrame
    df['SIPS_COCKTAILS'] = cocktails
    df['SIPS_WINE'] = wine
    df['SIPS_BEER'] = beer
    df['SIPS_HALFPRICEDAPPS'] = appetizers

    # Drop the original 'Deals' column
    df.drop(columns=['Deals'], inplace=True)

    return df

def extract_pdf_text(pdf_url):
    """
    Download and extract text from PDF URL
    """
    try:
        # Download PDF
        response = requests.get(pdf_url, timeout=30)
        response.raise_for_status()
        
        # Try PyMuPDF first (better text extraction)
        try:
            pdf_document = fitz.open(stream=response.content, filetype="pdf")
            text = ""
            for page_num in range(pdf_document.page_count):
                page = pdf_document.load_page(page_num)
                text += page.get_text() # type: ignore
            pdf_document.close()
            return text
        except:
            # Fallback to PyPDF2
            pdf_file = BytesIO(response.content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
            
    except Exception as e:
        print(f"Error extracting PDF text from {pdf_url}: {str(e)}")
        return ""

def parse_sips_deals(text):
    """
    Parse SIPS deals from PDF text using regex patterns
    """
    # Clean up text - remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Initialize results
    cocktails = []
    wine = []
    beer = []
    appetizers = []
    
    # Pattern for cocktails - look for $7 cocktail mentions
    cocktail_patterns = [
        r'Cocktail[^$]*\$7[^|]*\|[^$]*\$7[^A-Z]*([A-Z][^$]*?)(?=Wine|\$6|Beer|\$5|Appetizer|\$7\.95|$)',
        r'\$7[^|]*Cocktail[^A-Z]*([A-Z][^$]*?)(?=Wine|\$6|Beer|\$5|Appetizer|\$7\.95|$)',
        r'(\w+\s+\w+)\s+[^$]*\$7[^|]*\|[^$]*\$7(?=.*Cocktail)',
    ]
    
    # Pattern for wine - look for $6 wine mentions
    wine_patterns = [
        r'Wine[^$]*\$6[^A-Z]*([A-Z][^$]*?)(?=Beer|\$5|Appetizer|\$7\.95|Cocktail|\$7|$)',
        r'\$6[^|]*Wine[^A-Z]*([A-Z][^$]*?)(?=Beer|\$5|Appetizer|\$7\.95|Cocktail|\$7|$)',
        r'([A-Z][^$]*?)(?=Beer|\$5|Appetizer|\$7\.95).*Wine[^$]*\$6',
    ]
    
    # Pattern for beer - look for $5 beer mentions
    beer_patterns = [
        r'Beer[^$]*\$5[^A-Z]*([A-Z][^$]*?)(?=Appetizer|\$7\.95|Wine|\$6|Cocktail|\$7|$)',
        r'\$5[^|]*Beer[^A-Z]*([A-Z][^$]*?)(?=Appetizer|\$7\.95|Wine|\$6|Cocktail|\$7|$)',
        r'([A-Z][^$]*?)(?=Wine|\$6|Cocktail|\$7|Appetizer|\$7\.95).*Beer[^$]*\$5',
    ]
    
    # Pattern for appetizers - look for appetizer mentions with prices
    appetizer_patterns = [
        r'Appetizer[^$]*\$[0-9]+\.?[0-9]*[^A-Z]*([A-Z][^$]*?)(?=Wine|\$6|Beer|\$5|Cocktail|\$7|$)',
        r'\$[0-9]+\.?[0-9]*[^|]*Appetizer[^A-Z]*([A-Z][^$]*?)(?=Wine|\$6|Beer|\$5|Cocktail|\$7|$)',
        r'([A-Z][^$]*?)(?=Wine|\$6|Beer|\$5|Cocktail|\$7).*Appetizer[^$]*\$[0-9]+\.?[0-9]*',
    ]
    
    # Extract cocktails
    for pattern in cocktail_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
        if matches:
            cocktails.extend([match.strip() for match in matches if match.strip()])
    
    # Extract wine
    for pattern in wine_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
        if matches:
            wine.extend([match.strip() for match in matches if match.strip()])
    
    # Extract beer
    for pattern in beer_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
        if matches:
            beer.extend([match.strip() for match in matches if match.strip()])
    
    # Extract appetizers
    for pattern in appetizer_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
        if matches:
            appetizers.extend([match.strip() for match in matches if match.strip()])
    
    # If regex fails, try simpler keyword-based extraction
    if not any([cocktails, wine, beer, appetizers]):
        lines = text.split('\n')
        current_category = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for category headers
            if re.search(r'cocktail.*\$7|\$7.*cocktail', line, re.IGNORECASE):
                current_category = 'cocktails'
            elif re.search(r'wine.*\$6|\$6.*wine', line, re.IGNORECASE):
                current_category = 'wine'
            elif re.search(r'beer.*\$5|\$5.*beer', line, re.IGNORECASE):
                current_category = 'beer'
            elif re.search(r'appetizer.*\$[0-9]+\.?[0-9]*|\$[0-9]+\.?[0-9]*.*appetizer', line, re.IGNORECASE):
                current_category = 'appetizers'
            elif current_category and line and not re.search(r'\$[0-9]+\.?[0-9]*', line):
                # This might be a product name
                if current_category == 'cocktails':
                    cocktails.append(line)
                elif current_category == 'wine':
                    wine.append(line)
                elif current_category == 'beer':
                    beer.append(line)
                elif current_category == 'appetizers':
                    appetizers.append(line)
    
    return {
        'cocktails': ' | '.join(cocktails) if cocktails else None,
        'wine': ' | '.join(wine) if wine else None,
        'beer': ' | '.join(beer) if beer else None,
        'appetizers': ' | '.join(appetizers) if appetizers else None
    }

def readModalForPDF(df):
    """
    Updated function to read modal content and extract PDF data
    """
    # Create empty lists to store the extracted deal content
    cocktails_list = []
    wine_list = []
    beer_list = []
    appetizers_list = []

    # Loop through each row in the DataFrame
    for index, row in df.iterrows():
        # Get the URL value for each row
        url = row['SIPS_URL']
        
        # Initialize variables for this row
        deals_data = {
            'cocktails': None,
            'wine': None,
            'beer': None,
            'appetizers': None
        }
        
        try:
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
            print(f"Processing: {bar}")
            
            # Get content
            content = modal.find_element(By.CSS_SELECTOR, '.apos-rich-text')
            
            # Check if content contains a <p> with an <a> tag for PDF link
            try:
                link_element = content.find_element(By.CSS_SELECTOR, 'p > a')
                if "View SIPS menu" in link_element.text.strip():
                    deal_link = link_element.get_attribute('href')
                    print(f"Found PDF link: {deal_link}")
                    
                    # Extract text from PDF
                    pdf_text = extract_pdf_text(deal_link)
                    
                    if pdf_text:
                        # Parse the PDF text to extract deals
                        deals_data = parse_sips_deals(pdf_text)
                        print(f"Extracted deals: {deals_data}")
                    else:
                        print("Failed to extract PDF text")
                        
                else:
                    # Fallback to HTML content if no PDF link
                    deals_text = content.text
                    deals_data = parse_sips_deals(deals_text)
                    
            except Exception as e:
                print(f"Error processing link for {bar}: {str(e)}")
                # Fallback to text content if no <a> tag is found
                deals_text = content.text
                deals_data = parse_sips_deals(deals_text)
            
            driver.quit()
            
        except Exception as e:
            print(f"Error processing {url}: {str(e)}")
            if 'driver' in locals():
                driver.quit()
        
        # Append the extracted deal data to respective lists
        cocktails_list.append(deals_data['cocktails'])
        wine_list.append(deals_data['wine'])
        beer_list.append(deals_data['beer'])
        appetizers_list.append(deals_data['appetizers'])

    # Add the new columns to the DataFrame
    df['SIPS_COCKTAILS'] = cocktails_list
    df['SIPS_WINE'] = wine_list
    df['SIPS_BEER'] = beer_list
    df['SIPS_HALFPRICEDAPPS'] = appetizers_list

    return df

# modal_df = readModalForDeals(site_df)
modal_df = readModalForPDF(site_df)
# modal_df = pd.read_csv("Sips2024.csv")
# modal_df = site_df
modal_df.to_csv("Sips2025.csv", index=False)

def scrapePhotos(modal_df):
    run_on = "ccd-sips"
    html = "https://centercityphila.org/explore-center-city/" + run_on
    base_html = "https://centercityphila.org"
    source = requests.get(html).text
    soup = BeautifulSoup(source, "lxml")

    page_number = 1
    restaurant_info_list = []
    while True:
        # Create the URL for the current page
        current_url = f"{html}?page={page_number}"
        # Request and parse HTML for each page 
        page_html = requests.get(current_url, allow_redirects=False).text
        soupIter = BeautifulSoup(page_html, 'lxml')
        # print(soupIter.find_all('tr')[1])
        card_media_divs = soupIter.find_all('div', class_='o-card__media')
        for card_media in card_media_divs:
            img = card_media.find('img')
            if img and img['alt'] != '':
                alt_text = img['alt'].rstrip('*')
                src_link = base_html + img['src']
                restaurant_info_list.append({'Name': alt_text, 'RW_PHOTO': src_link})
                # print({'alt_text': alt_text, 'src_link': src_link})
        pager = soupIter.find('div', class_='c-pager')
        next_page_link = pager.find('a', href=f"/explore-center-city/{run_on}?page={page_number + 1}") # type: ignore
        
        if not next_page_link:
            break  # No more pages, exit the loop
        else:
            page_number += 1

    # Create dataframe  
    df1 = pd.DataFrame(restaurant_info_list)

    # Merge the two DataFrames on 'Restaurant Name' column
    merged_df = modal_df.merge(df1[['Name', 'RW_PHOTO']], on='Name', how='left')

    # Print the resulting DataFrame with the new "Website" column
    print(df1)
    print(merged_df)
    return merged_df

merged_df = scrapePhotos(modal_df)
merged_df.to_csv("Sips2025.csv", index=False, mode='a', header=False)
# merged_df = pd.read_csv("Sips2024.csv")
# merged_df = pd.read_csv("Test.csv")

def mergeData(csv_df, modal_df):
    # Merge the two DataFrames on 'Name' and 'Address' to find common records
    merge_df = modal_df.merge(csv_df, on=['Name', 'Address'], how='left', indicator=True, suffixes=('', '_csv'))
    merge_df["SIPS_PARTICIPANT"] = "Y"
    # Create sub-df for records where 'Name' and 'Address' are in both DataFrames
    in_both_df = merge_df[merge_df['_merge'] == 'both'].drop(columns=[col for col in merge_df.columns if col.endswith('_csv') or col == '_merge'])
    # in_both_df["SIPS_PARTICIPANT"] = "Y"
    # Create sub-df for records where 'Name' and 'Address' are only in the original df
    not_in_csv_df = merge_df[merge_df['_merge'] == 'left_only'].drop(columns=[col for col in merge_df.columns if col.endswith('_csv') or col == '_merge'])

    # not_in_csv_df["SIPS_PARTICIPANT"] = "Y"

    # Display the sub-dataframes (for verification)
    print("Records in both DataFrames:")
    print(in_both_df)
    print("\nRecords not in the csv DataFrame:")
    print(not_in_csv_df)

    print(csv_df[["Name", "SIPS_BEER", "SIPS_PARTICIPANT"]])
    # Update records in csv_df with those in in_both_df

    # # Merge DataFrames ensuring matching rows
    # merged_df = csv_df.merge(modal_df, how='inner', on=['Name', 'Address'])
    # # Update csv_df with modal_df values for matching rows
    # csv_df.update(merged_df[modal_df.columns])

    for i, row in in_both_df.iterrows():
        csv_df.loc[(csv_df['Name'] == row['Name']) & (csv_df['Address'] == row['Address']), row.index] = row.values
    # Add records from not_in_csv_df to csv_df
    csv_df = pd.concat([csv_df, not_in_csv_df], ignore_index=True)
    csv_df = csv_df.drop_duplicates(subset=['Name', 'Address'])

    csv_df.to_csv("MasterTableNew.csv", index=False)
    return csv_df

csv_df = pd.read_csv('../Csv/MasterTable.csv')
csv_df = mergeData(csv_df, merged_df)
df = csv_df.loc[csv_df['SIPS_PARTICIPANT'] == 'Y']
print(df)
sdfg
# df = csv_df.loc[csv_df['RW_PARTICIPANT'].isna()]
# print(df)

def pullBasicYelp(df, csv_df):
    # Actual API Key
    # yelpapiKey = "DQx0YugiFJ5inYYp8fVvDqLx0R_dVo8yXxRZtpD5jkbNK0WmAqUygKIyXnYHlfL0pYRndGHGmuvn_QCXPVndRCc0VjtZzxCSHE8MhPthoJ4YUygg65DJrhMJLu7OZHYx"

    # Backup API Key
    # yelpapiKey = "r9ksNtdCcwK8MhsrL9fB5BvOGkC8Habi6-S5Shhh-Xu7CXF5xCBAPRCPS04atHegmf3BOMeW9gqNxA16E32gg4xDhcuWgD0k58m9jp280IpSb5zthhBCvmeXBsnPZHYx"

    # Backup backup API Key
    yelpapiKey = "XEmkEwex5TbqjOitZJ8xtLXTBMQQb7BrtQdzzw-hJVWwnIUysCwCzXT2X2xsMbSXR7uHxWnRkyyFIh1CxfLr6Ilj_n-xClAG_h5aKabBtAjJLVnZ9mMfdKFWlMvPZHYx"

    yelp = yelpapi.YelpAPI(yelpapiKey)

    # Assuming you have the DataFrame 'df' with the 'Deals' column
    # df = pd.read_csv('../Csv/AllSipsLocations.csv')

    # bars = yelp.search_query(location='Philadelphia', categories='bars')
    # print(bars)
    base_url = "https://www.yelp.com/biz/"

    # Function to get Yelp data for each bar
    def get_yelp_data(row):
        def find_first_rating(dictionary):
            for key, value in dictionary.items():
                if isinstance(value, dict):
                    # If the value is a dictionary, recursively search within it
                    result = find_first_rating(value)
                    if result is not None:
                        return result
                if key == "rating":
                    # If the key is "rating," return the value
                    return value
            return None  # Return None if "rating" is not found
        
        # Function to search for "BusinessWebsite" and get the URL
        def find_business_website(json_obj):
            if isinstance(json_obj, dict):
                if "__typename" in json_obj and json_obj["__typename"] == "BusinessWebsite":
                    return json_obj.get("url")
                for key, value in json_obj.items():
                    result = find_business_website(value)
                    if result:
                        return result
            elif isinstance(json_obj, list):
                for item in json_obj:
                    result = find_business_website(item)
                    if result:
                        return result
        yelp_alias = row['Yelp Alias']
        print(yelp_alias)
        print()
        response = yelp.business_query(id=yelp_alias) # type: ignore
        # print(response)

        # Extract categories from the details_response
        categories = [category['title'] for category in response.get('categories', [])]
        address = ', '.join(response["location"]["display_address"])

        url = base_url + yelp_alias
        yelp_response = requests.get(url)
        html = yelp_response.text
        # Parse HTML with BeautifulSoup  
        soup = BeautifulSoup(html, "html.parser")
        # Find the <script> tag
        script_tag = soup.find("script", {"data-apollo-state": True})

        if script_tag is not None:
            # Extract JSON string 
            json_str = script_tag.text # type: ignore
            # Remove <!-- and -->
            cleaned = json_str[4:-3]
            # Add outer quotes
            json_str = re.sub(r'&quot;', '"', cleaned)
            # Parse the JSON string into a Python object
            json_object = json.loads(json_str)

            business_properties = {}
            neighborhoods_json = []
            rating = None
            hours_properties = {}
            website = None
            # Parse the JSON object once
            for key, value in json_object.items():
                if isinstance(value, dict):
                    if "displayText" in value:
                        display_text = value["displayText"]
                        is_active = value["isActive"]
                        if "&amp;" in display_text:
                            display_text = display_text.replace("&amp;", "and")
                        if "Not Good" in display_text:
                            display_text = display_text.replace("Not Good", "Good")
                            is_active = not is_active
                        if "Not Wheelchair Accessible" in display_text:
                            display_text = display_text.replace("Not ", "")
                            is_active = not is_active
                        if "Dogs Not Allowed" in display_text:
                            display_text = display_text.replace("Not ", "")
                            is_active = not is_active
                        if "Very Loud" in display_text:
                            display_text = display_text.replace("Very ", "")
                        if "Free Wi-fi" in display_text:
                            display_text = display_text.replace("Free ", "")
                        if "Smoking Allowed" in display_text:
                            display_text = display_text.replace(" Allowed", "")
                        if "Happy Hour Specials" in display_text:
                            display_text = display_text.replace(" Specials", "")
                        if "Reservations" == display_text:
                            display_text = "Takes " + display_text
                        if "Happy Hour Specials" in display_text:
                            display_text = display_text.replace(" Specials", "")
                        if "Takes Reservations" in display_text:
                            display_text = display_text.replace("Takes ", "")
                        if "Many Vegetarian Options" in display_text:
                            display_text = display_text.replace("Many ", "")
                        if "Casual Dress" in display_text:
                            display_text = display_text.replace(" Dress", "")
                        if "No " in display_text:
                            display_text = display_text.replace("No ", "")
                            is_active = not is_active
                        if "Best nights on" in display_text:
                            parts = display_text.split("Best nights on ")[1].split(',')
                            for part in parts:
                                new_display_text = "Best nights on " + part.strip()
                                business_properties[new_display_text] = is_active
                        elif "Paid Wi-Fi" not in display_text:
                            display_texts = [text.strip() for text in display_text.split(',')]
                            business_properties.update({text: is_active for text in display_texts})
                    if "neighborhoods" in value:
                        neighborhoods_json = value["neighborhoods"].get("json", neighborhoods_json)
                    business_website_url = find_business_website(json_object)
                    if business_website_url:
                        website = business_website_url.replace("&#x2F;", "/")
                    # if "rating" in value:
                    #     rating = value["rating"]
                    if "regularHours" in value and "dayOfWeekShort" in value:
                        Hours = value["regularHours"].get("json", [])[0]
                        day = value["dayOfWeekShort"]
                        if day == "Mon":
                            day += "day"
                        elif day == "Tue":
                            day += "sday"
                        elif day == "Wed":
                            day += "nesday"
                        elif day == "Thu":
                            day += "rsday"
                        elif day == "Fri":
                            day += "day"
                        elif day == "Sat":
                            day += "urday"
                        elif day == "Sun":
                            day += "day"
                        hours_properties[day] = Hours

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
            res_link = None
            if pd.isna(website) == False:
                res_link = check_links(website)
            restaurant_name = row['Name']
            rating = find_first_rating(json_object)
            # Extract relevant data from the Yelp response (customize based on your needs)
            yelp_data = {
                'Name': restaurant_name,
                'Open Table Link': res_link,
                'Address': address,
                'Latitude': response["coordinates"]["latitude"],
                'Longitude': response["coordinates"]["longitude"],
                "Website": website,
                'Review Count': response.get('review_count'),
                'Price': response.get('price'),
                # 'Yelp URL': response.get('url'),
                'Categories': categories,
                **business_properties,
                "Neighborhoods": neighborhoods_json,
                **hours_properties,
                "Yelp Rating": rating,
                "Sips Participant": "N",
                "Restaurant Week Participant": "N",
            }
            return yelp_data
        else:
            print("Did not work for: " + row['Name'])
            return None

    # Create a list to store Yelp data for all bars
    # all_yelp_data = []

    # # Apply the function to each row and append data to the list
    # for index, row in df.iterrows():
    #     yelp_data = get_yelp_data(row)
    #     all_yelp_data.append(yelp_data)

    # # Create a DataFrame from the list of dictionaries
    # yelp_df = pd.DataFrame(all_yelp_data)
    # # Display the Yelp data DataFrame
    # print(yelp_df)
    # yelp_df.to_csv('../Csv/Yelp.csv', index=False)
    yelp_df = pd.read_csv("Yelp.csv")

    # Merge the two DataFrames on the 'Name' column
    suffixes = ('_df', '')  # Keep suffixes empty for the left table (df) and '_df' for the right table (yelp_df)

    # Perform left join on Name
    combined_df = df.merge(yelp_df, on='Name', how='left', suffixes=suffixes)

    # Drop columns with '_df' suffix (assuming the merged DataFrame is stored in 'combined_df')
    dropped_df = combined_df.select_dtypes(exclude='object').filter(like='_df')  # Filter for '_df' and exclude object dtype
    combined_df = combined_df.drop(dropped_df.columns, axis=1)  # Drop the filtered columns

    print(combined_df)

    columns_to_update = ['Yelp_Rating', 'Review_Count', 'Price', 'Categories']

    # Update records in csv_df with those in in_both_df for specific columns
    for i, row in combined_df.iterrows():
        for column in columns_to_update:
            csv_df.loc[(csv_df['Name'] == row['Name']) & (csv_df['Address'] == row['Address']), column] = row[column]


    # csv_df = pd.concat([csv_df, combined_df], ignore_index=True)
    # csv_df = csv_df.drop_duplicates(subset=['Name', 'Address'])

    csv_df.to_csv("MasterTableNew.csv", index=False)
    # Display the updated DataFrame
    print(csv_df[["Name", 'Yelp_Rating', 'Review_Count', 'Price', 'Categories']])
    # print(csv_df)

pullBasicYelp(df, csv_df)

def reformatYelpColumns(df):
    # -------------- PARKING -----------------
    parking_types = ['Street Parking', 'Bike Parking', 'Valet Parking', 'Validated Parking', 'Garage Parking', 'Private Lot Parking']
    df[parking_types] = df[parking_types].fillna(False)
    df['Parking'] = df[parking_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
    df.drop(columns=parking_types, inplace=True)
    # =========================================

    # -------------- BEST NIGHTS -----------------
    night_types = ["Best nights on Monday","Best nights on Tuesday","Best nights on Wednesday","Best nights on Thursday","Best nights on Friday","Best nights on Saturday","Best nights on Sunday"]
    df[night_types] = df[night_types].fillna(False)
    df['Best_Nights'] = df[night_types].apply(lambda x: ', '.join(x.index[x]).replace('Best nights on ',''), axis=1)  # type: ignore
    df.drop(columns=night_types, inplace=True)
    # =========================================

    # -------------- PAYMENT -----------------
    # def combine_payment(row):
    #     pay_types = ["Accepts Credit Cards","Accepts Android Pay","Accepts Apple Pay","Accepts Cryptocurrency"]
    #     for pay_type in pay_types:
    #         if row[pay_type]:
    #             return pay_type.split("Accepts ")[1]
    #     return None
    # # Apply the function to create the column
    # df['Payment'] = df.apply(combine_payment, axis=1) # type: ignore
    pay_types = ["Accepts Credit Cards","Accepts Android Pay","Accepts Apple Pay","Accepts Cryptocurrency"]
    df[pay_types] = df[pay_types].fillna(False)
    df['Payment'] = df[pay_types].apply(lambda x: ', '.join(x.index[x]).replace('Accepts ',''), axis=1)  # type: ignore
    df.drop(columns=pay_types, inplace=True)
    # =========================================

    # -------------- MINORITY OWNED -----------------
    minority_types = ["Women-owned","Latinx-owned","Asian-owned","Black-owned","Veteran-owned","LGBTQ-owned"]
    df[minority_types] = df[minority_types].fillna(False)
    df['Minority_Owned'] = df[minority_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
    df.drop(columns=minority_types, inplace=True)
    # =========================================

    # -------------- GOOD FOR -----------------
    df['Good For Groups'] = df['Good For Groups'].fillna(df['Good for Groups'])
    df.drop(columns='Good for Groups', inplace=True)
    df.drop(columns='Good For Working.1', inplace=True)
    def good_for(row):
        good_for_types = ["Good For Dinner","Good For Kids","Good For Lunch","Good For Dancing","Good For Working","Good For Brunch","Good For Dessert","Good For Breakfast","Good For Groups","Good For Late Night", "All Ages", "Late Night"]
        for good_for in good_for_types:
            if row[good_for]:
                return good_for.split("Good For ")[1]
        return None
    # Apply the function to create the column
    df['Good_For'] = df.apply(good_for, axis=1) # type: ignore
    good_for_types = ["Good For Dinner","Good For Kids","Good For Lunch","Good For Dancing","Good For Working","Good For Brunch","Good For Dessert","Good For Breakfast","Good For Groups","Good For Late Night", "All Ages", "Late Night"]
    # df[good_for_types] = df[good_for_types].fillna(False)
    # df['Good_For'] = df[good_for_types].apply(lambda x: ', '.join(x.index[x]).replace('Good For ',''), axis=1)  # type: ignore
    df.drop(columns=good_for_types, inplace=True)
    # =========================================

    # -------------- OFFERS -----------------
    df['Offers Delivery'] = df['Offers Delivery'].fillna(df['Delivery'])
    df.drop(columns='Delivery', inplace=True)
    df['Offers Takeout'] = df['Offers Takeout'].fillna(df['Takeout'])
    df.drop(columns='Takeout', inplace=True)

    # def offers(row):
    #     offers_types = ["Offers Delivery","Offers Takeout","Offers Catering","Offers Military Discount"]
    #     for offer in offers_types:
    #         if row[offer]:
    #             return offer.split("Offers ")[1]
    #     return None
    # # Apply the function to create the column
    # df['Offers'] = df.apply(offers, axis=1) # type: ignore
    offers_types = ["Offers Delivery","Offers Takeout","Offers Catering","Offers Military Discount","Online ordering-only"]
    df[offers_types] = df[offers_types].fillna(False)
    df['Offers'] = df[offers_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
    df.drop(columns=offers_types, inplace=True)
    # =========================================

    # -------------- OPTIONS -----------------
    df['Vegetarian Options'] = df['Vegetarian Options'].fillna(df['Many Vegetarian Options'])
    df.drop(columns='Many Vegetarian Options', inplace=True)
    # def options(row):
    #     options_types = ["Vegan Options","Limited Vegetarian Options","Pescatarian Options","Keto Options","Vegetarian Options","Soy-Free Options","Dairy-Free Options","Gluten-Free Options"]
    #     for option in options_types:
    #         if row[option]:
    #             return option.split(" Options")[0]
    #     return None
    # # Apply the function to create the column
    # df['Options'] = df.apply(options, axis=1) # type: ignore
    options_types = ["Vegan Options","Limited Vegetarian Options","Pescatarian Options","Keto Options","Vegetarian Options","Soy-Free Options","Dairy-Free Options","Gluten-Free Options"]
    df[options_types] = df[options_types].fillna(False)
    df['Options'] = df[options_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
    df.drop(columns=options_types, inplace=True)
    # =========================================

    # -------------- VIBES -----------------
    df['Casual'] = df['Casual'].fillna(df['Casual Dress'])
    df.drop(columns='Casual Dress', inplace=True)
    vibes_types = ["Trendy", "Classy", "Intimate", "Romantic", "Upscale", "Dressy", "Hipster", "Touristy", "Divey", "Casual", "Quiet", "Loud", "Moderate Noise"]
    df[vibes_types] = df[vibes_types].fillna(False)
    df['Vibes'] = df[vibes_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
    df.drop(columns=vibes_types, inplace=True)
    # =========================================

    # -------------- ACCESSIBILITY -----------------
    df['Wheelchair Accessible'] = df['Wheelchair Accessible'] | ~df['Not Wheelchair Accessible'].fillna(False)
    df['Wheelchair Accessible'] = df['Wheelchair Accessible'].mask(df['Wheelchair Accessible'] == False, np.nan)
    df.drop(columns='Not Wheelchair Accessible', inplace=True)
    access_types = ["Open to All", "Wheelchair Accessible", "Gender-neutral restrooms"]
    df[access_types] = df[access_types].fillna(False)
    df['Accessibility'] = df[access_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
    df.drop(columns=access_types, inplace=True)
    # =========================================

    # -------------- DOGS -----------------
    df['Dogs Allowed'] = df['Dogs Allowed'] | ~df['Dogs Not Allowed'].fillna(False)
    df['Dogs_Allowed'] = df['Dogs Allowed'].mask(df['Dogs Allowed'] == False, np.nan)
    df.drop(columns=['Dogs Not Allowed', 'Dogs Allowed'], inplace=True)
    # =========================================

    # -------------- SMOKING -----------------
    df['Smoking'] = df['Smoking'].fillna(df['Smoking Allowed'])
    df.drop(columns=['Smoking Allowed', "Smoking Outside Only"], inplace=True)
    # =========================================

    # -------------- PACKING -----------------
    package_types = ["Plastic-free packaging", "Provides reusable tableware", "Compostable containers available", "Bring your own container allowed"]
    df[package_types] = df[package_types].fillna(False)
    df['Packaging'] = df[package_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
    df.drop(columns=package_types, inplace=True)
    # =========================================

    # -------------- RESERVATION TYPE -----------------
    df['Takes Reservations'] = df['Takes Reservations'].fillna(df['Reservations'])
    df.drop(columns='Reservations', inplace=True)
    res_types = ["By Appointment Only", "Walk-ins Welcome", "Takes Reservations"]
    df[res_types] = df[res_types].fillna(False)
    df['Reservation_Type'] = df[res_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
    df.drop(columns=res_types, inplace=True)
    # =========================================

    # -------------- SEATING -----------------
    seating_types = ["Outdoor Seating", "Heated Outdoor Seating", "Covered Outdoor Seating", "Private Dining", "Drive-Thru"]
    df[seating_types] = df[seating_types].fillna(False)
    df['Seating'] = df[seating_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
    df.drop(columns=seating_types, inplace=True)
    # =========================================

    # def service(row):
    #     service_types = ["Plastic-free packaging", "Provides reusable tableware", "Compostable containers available", "Bring your own container allowed"]
    #     for serv in service_types:
    #         if row[serv]:
    #             return serv
    #     return None
    # # Apply the function to create the column
    # df['Options'] = df.apply(service, axis=1) # type: ignore
    # service_types = ["Outdoor Seating", "TV", "Waiter Service", "Wi-Fi"]
    # # Drop the original columns
    # df.drop(columns=service_types, inplace=True)

    # -------------- MEAL -----------------
    # food_types = ["Lunch", "Dessert", "Brunch", "Dinner", "Breakfast"]
    food_types = ["Lunch", "Dessert", "Brunch", "Dinner"]
    df[food_types] = df[food_types].fillna(False)
    df['Meal_Types'] = df[food_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
    df.drop(columns=food_types, inplace=True)
    # =========================================

    # -------------- MUSIC -----------------
    music_types = ["Live Music", "DJ", "Background Music", "Juke Box", "Karaoke"]
    df[music_types] = df[music_types].fillna(False)
    df['Music'] = df[music_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
    df.drop(columns=music_types, inplace=True)
    # =========================================

    # -------------- HAPPY HOUR -----------------
    df['Happy Hour'] = df['Happy Hour'].fillna(df['Happy Hour Specials'])
    df.drop(columns='Happy Hour Specials', inplace=True)
    alc_types = ["Alcohol", "Happy Hour", "Beer and Wine Only", "Full Bar"]
    df[alc_types] = df[alc_types].fillna(False)
    df['Alcohol_Options'] = df[alc_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
    df.drop(columns=alc_types, inplace=True)
    # =========================================

    # -------------- AMENITIES -----------------
    amenity_types = ["TV", "Pool Table", "Wi-Fi", "EV charging station available"]
    df[amenity_types] = df[amenity_types].fillna(False)
    df['Amenities'] = df[amenity_types].apply(lambda x: ', '.join(x.index[x]), axis=1)
    df.drop(columns=amenity_types, inplace=True)
    df.drop(columns="Virtual restaurant", inplace=True)
    df.drop(columns="Waiter Service", inplace=True)
    # =========================================
