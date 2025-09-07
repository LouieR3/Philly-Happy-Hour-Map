import pandas as pd
from yelpapi import YelpAPI
import yelpapi
from bs4 import BeautifulSoup
import requests
import time
import os
import json
import re

# ------------------------------------------------
# This script does = All major functions combined to pull bar menu details and calculate score
# ------------------------------------------------

# Assuming you have the DataFrame 'df' with the 'Deals' column
df = pd.read_csv('../Csv/AllSipsLocations.csv')

menu_data = []
keywords = ["beers", "bottles", "cans", "wines", "cocktails"]

def pull_yelp():
    html = "https://centercityphila.org/explore-center-city/ccd-sips/sips-list-view"
    source = requests.get(html).text
    soup = BeautifulSoup(source, "lxml")
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
                                'Drink': name,
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
                        'Drink': name,
                        'Price': price,
                        'Sips Deal': "N"
                    })
        except Exception as e:
            print(f'An error occurred for alias {alias}: {e}')
            pass
    combineCSV(menu_data)

def main():
    for index, row in df.iterrows():
        base_url = row['Bar Website']
        bar_name = row['Bar Name']
        if pd.notna(base_url):
            try:
                subpage_urls = gather_subpages(base_url)

                for url in subpage_urls:
                    print(url)
                    result = website_json(bar_name, url)
                    if not result.empty:
                        print(result)
                        print()
                        print(base_url)
                        # combineCSV(result)
                    else:
                        # result = website_html(bar_name, url)
                        if ".pdf" in url:
                            result = website_pdf(bar_name, url)
                            print(result)
                print()
            except requests.exceptions.RequestException as e:
                print(f'An error occurred for base_url {base_url}: {e}')
                print("--------------------------------------------")
                print()
                pass

def website_html(bar_name, url):
    menu_items = []
    menu_prices = []
    keywords = ["beer", "draft", "draught", "bottle", "cans", "wine", "cocktail"]

    try:
        menu_response = requests.get(url)
        soup = BeautifulSoup(menu_response.content, 'html.parser')
        for kw in keywords:
            keyword_elements = soup.find_all(string=re.compile(kw), recursive=True)

    except Exception as e:
        print(f'An error occurred for url {url}: {e}')
        pass

    menu_df = pd.DataFrame({
        'Bar': bar_name,
        'Drink': menu_items,
        'Price': menu_prices,
        'Sips Deal': "N"
    })
    return menu_df

def website_json(bar_name, url):
    menu_items = []
    menu_prices = []
    json_keywords = ["beers", "draft", "drinks"]
    keywords = ["beer", "draft", "draught", "bottle", "cans", "wine", "cocktail"]
    try:
        menu_response = requests.get(url)
        soup = BeautifulSoup(menu_response.content, 'html.parser')
        for kw in keywords:
            keyword_elements = soup.find_all(string=re.compile(kw), recursive=True)
            for json_object in keyword_elements:
                data = json.loads(json_object)
                if 'menu' in json.dumps(data).lower() and any(keyword in json.dumps(data).lower() for keyword in json_keywords):
                    entry = data['data']
                    for section in entry:
                        if any(keyword in section["name"].lower() for keyword in keywords):
                            for section in section["sections"]:
                                for item in section["items"]:
                                    menu_item = item["name"]
                                    # menu_price = item["choices"][0]["prices"]["min"]
                                    menu_price = '${:,.2f}'.format(item["choices"][0]["prices"]["min"])
                                    menu_items.append(menu_item)
                                    menu_prices.append(menu_price)
    except Exception as e:
        print(f'An error occurred for url {url}: {e}')
        pass
    menu_df = pd.DataFrame({
        'Bar': bar_name,
        'Drink': menu_items,
        'Price': menu_prices,
        'Sips Deal': "N"
    })
    return menu_df

def website_pdf(bar_name, url):
    import fitz  # PyMuPDF
    import requests
    from io import BytesIO
    import pandas as pd
    import re
    def extract_drinks_from_pdf(pdf_path):
        try:
            response = requests.get(pdf_path)
            if response.status_code == 200:
                pdf_data = BytesIO(response.content)
                pdf_document = fitz.open(stream=pdf_data, filetype="pdf") # type: ignore
                text = ""
                for page_num in range(pdf_document.page_count):
                    page = pdf_document.load_page(page_num)
                    text += page.get_text()
                pdf_document.close()
                return text
            else:
                print("Failed to fetch PDF from URL.")
        except Exception as e:
            print("An error occurred:", e)
        return None

    def create_dataframe_from_text(text):
        drinks = []
        lines = text.split('\n')
        drink_name = ""
        drink_price = ""
        for line in lines:
            if line.strip() and line.isascii():
                if "$" in line:
                    components = line.split()
                    for component in components:
                        if '$' in component:
                            drink_price = component
                            price = float(drink_price.replace("$", ""))

                            drink_name = re.sub(r'\(.+?\)', '', drink_name).strip()

                            if drink_name and drink_price and price < 24:
                                drinks.append((drink_name.strip(), drink_price.strip()))
                            drink_name = ""
                            break
                        else:
                            drink_name += component + " "
                    
        df = pd.DataFrame(drinks, columns=["Drink", "Price"])
        df.insert(0, "Bar", bar_name)
        return df
    
    extracted_text = extract_drinks_from_pdf(url)
    if extracted_text:
        menu_df = create_dataframe_from_text(extracted_text)
        # print(menu_df)
        # menu_df.insert(0, 'Bar', bar_name)
        return menu_df
    else:
        print("Failed to extract text from PDF.")
        return None

def gather_subpages(base_url):
    # List to store subpage URLs
    subpage_urls = []
    # Iterate through each link and check for keywords
    response = requests.get(base_url)
    soup = BeautifulSoup(response.content, 'html.parser')
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

    target_keyword = "philadelphia"  # You can also use "philadelphia" as the keyword

    target_url = None

    for url in subpage_urls:
        if target_keyword in url:
            target_url = url
            break

    # Modify subpage_urls to contain only the target URL if found
    if target_url is not None:
        subpage_urls = [target_url]
    return subpage_urls

def combineCSV(menu_df):
    # menu_df = pd.DataFrame(menu_data)
    print(menu_df)
    # Read '../Csv/SipsBarItems.csv' into a DataFrame
    sips_bar_items_df = pd.read_csv('../Csv/SipsBarItems.csv')

    # Combine menu_df and sips_bar_items_df
    combined_df = pd.concat([sips_bar_items_df, menu_df])

    # Drop duplicates based on 'Bar', 'Drink', and 'Price'
    combined_df.drop_duplicates(subset=['Bar', 'Drink', 'Price'], inplace=True)

    # Write the combined DataFrame to a new CSV file
    combined_df.to_csv('../Csv/SipsBarItems.csv', index=False)

def calculateDeal():
    # Read the CSV file into a DataFrame
    df = pd.read_csv("SipsBarItems.csv")
    # Remove certain words from Drink values
    words_to_remove = [" can", " beer", " draft", " bottle"]
    df = df[df["Price"] != "Price not available"]
    df["Drink"] = (
        df["Drink"]
        .str.lower()  # Convert to lowercase
        .str.replace("|".join(words_to_remove), "", regex=True)  # Remove specified words
        .str.capitalize()  # Capitalize first letter
        .str.strip()  # Clean whitespace
    )
    df["Drink"] = df["Drink"].str.split(":").str[0].str.strip()
    df["Price"] = df["Price"].str.replace("$", "").astype(float)
    # Create subdataframes for SipsDeal = Y and SipsDeal = N
    sips_deal_y_df = df[df["Sips Deal"] == "Y"]
    sips_deal_n_df = df[df["Sips Deal"] == "N"]
    # Initialize an empty results dataframe
    results_df = pd.DataFrame(
        columns=["Drink", "Sips Price", "Normal Price", "Comparison Result"]
    )

    # Compare prices for each unique Drink
    for menu_item in df["Drink"].unique():
        sips_price = sips_deal_y_df[sips_deal_y_df["Drink"] == menu_item][
            "Price"
        ].mean()
        sips_bar = (
            sips_deal_y_df[sips_deal_y_df["Drink"] == menu_item]["Bar"].iloc[0]
            if not pd.isna(sips_price)
            else ""
        )
        normal_price = sips_deal_n_df[sips_deal_n_df["Drink"] == menu_item][
            "Price"
        ].mean()

        comparison_result = None
        if sips_price is not None and normal_price is not None:
            comparison_result = normal_price - sips_price

        results_df = results_df.append(
            {
                "Drink": menu_item,
                "Sips Price": sips_price,
                "Normal Price": normal_price,
                "Comparison Result": comparison_result,
                "Sips Bar": sips_bar,
            },
            ignore_index=True,
        )  # type: ignore

    results_df = results_df.sort_values(by="Comparison Result", ascending=False)

    # Save the results dataframe to a CSV file
    results_df.to_csv("ComparisonResults.csv", index=False)

    print(results_df)

# pull_yelp()
main()

