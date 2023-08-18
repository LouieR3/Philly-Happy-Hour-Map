from bs4 import BeautifulSoup
import pandas as pd
from ast import literal_eval

# ------------------------------------------------
# This script does = Turns the csv of bar data to a HTML datatable
# ------------------------------------------------

# Read the existing HTML file
with open('test.html', 'r') as file:
    html_content = file.read()

# Parse the HTML content using BeautifulSoup
soup = BeautifulSoup(html_content, 'html.parser')

# Create or load your DataFrame
# For this example, let's create a simple DataFrame
df = pd.read_csv('AllSipsOriginal.csv', encoding='utf-8')

# Drop the 'Latitude' and 'Longitude' columns
df.drop(columns=['Latitude', 'Longitude'], inplace=True)

def safe_literal_eval(x):
    try:
        return literal_eval(x)
    except (ValueError, SyntaxError):
        return []
df['Categories'] = df['Categories'].apply(safe_literal_eval)
def join_categories(categories):
    return ', '.join(categories)

# Apply the function to the 'Categories' column
df['Categories'] = df['Categories'].apply(join_categories)

df['Reviews'] = pd.to_numeric(df['Reviews'], errors='coerce').fillna(0).astype(int)
df['Price'].fillna('', inplace=True)
# Function to convert URLs into HTML anchor tags
def url_to_link(url):
    if pd.notnull(url):
        return f'<a href="{url}" target="_blank">Website</a>'
    return ''

# Apply the function to 'Sips Url' and 'Bar Website' columns
df['Bar Website'] = df['Bar Website'].apply(url_to_link)

# Function to split the 'Deals' column into separate columns
def split_deals(deals):
    cocktails = []
    wine = []
    beer = []
    appetizers = []
    current_list = None

    for item in deals.split('\n'):
        if item.startswith('$7 Cocktails'):
            current_list = cocktails
        elif item.startswith('$6 Wine'):
            current_list = wine
        elif item.startswith('$5 Beer'):
            current_list = beer
        elif item.startswith('Half-Priced Appetizers'):
            current_list = appetizers
        elif current_list is not None:
            current_list.append(item.replace('\r', ''))  # Replace '\r' with <br>

    return {
        '$5 Beer': '<br>'.join(beer),  # Use <br> instead of '\n'
        '$6 Wine': '<br>'.join(wine),  # Use <br> instead of '\n'
        '$7 Cocktails': '<br>'.join(cocktails),  # Use <br> instead of '\n'
        'Half-Priced Appetizers': '<br>'.join(appetizers)  # Use <br> instead of '\n'
    }

# Split the 'Deals' column into new columns
df[['$5 Beer', '$6 Wine', '$7 Cocktails', 'Half-Priced Appetizers']] = df['Deals'].apply(split_deals).apply(pd.Series)

# Drop the original 'Deals' column
df.drop(columns=['Deals', 'Sips Url', 'Reviews', 'Half-Priced Appetizers'], inplace=True)

# Convert the DataFrame to an HTML table
df_html = df.to_html(index=False, table_id="table_sort", escape=False, classes="table table-responsive table-striped table-bordered w-90 center text-center", justify='center') # type: ignore

# Find the specific location in the HTML where you want to insert the DataFrame
# For this example, let's assume there's a <div> with id 'insert_here' in the HTML
insert_location = soup.find('div', {'id': 'insert_here'})

# Create a new BeautifulSoup object for the DataFrame HTML
df_soup = BeautifulSoup(df_html, 'html.parser')

# Check if the insert_location is not None before attempting to insert the DataFrame
if insert_location is not None:
    insert_location.insert_after(df_soup)
else:
    # If the insert_location is None, you can use the append method to add the DataFrame
    # at the end of the HTML
    soup.append(df_soup)

# Save the modified HTML back to the file
with open('test.html', 'w', encoding='utf-8') as file:
    file.write(soup.prettify())