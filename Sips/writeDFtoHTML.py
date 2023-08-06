from bs4 import BeautifulSoup
import pandas as pd
from ast import literal_eval

# Read the existing HTML file
with open('test.html', 'r') as file:
    html_content = file.read()

# Parse the HTML content using BeautifulSoup
soup = BeautifulSoup(html_content, 'html.parser')

# Create or load your DataFrame
# For this example, let's create a simple DataFrame
df = pd.read_csv('Test.csv')

# Drop the 'Latitude' and 'Longitude' columns
df.drop(columns=['Latitude', 'Longitude'], inplace=True)

def safe_literal_eval(x):
    try:
        return literal_eval(x)
    except (ValueError, SyntaxError):
        return []
df['Categories'] = df['Categories'].apply(safe_literal_eval)
df['Reviews'] = pd.to_numeric(df['Reviews'], errors='coerce').fillna(0).astype(int)
df['Price'].fillna('', inplace=True)
# Function to convert URLs into HTML anchor tags
def url_to_link(url):
    if pd.notnull(url):
        return f'<a href="{url}" target="_blank">Go to website</a>'
    return ''
def url_to_sips(url):
    if pd.notnull(url):
        return f'<a href="{url}" target="_blank">Go to Sips page</a>'
    return ''

# Apply the function to 'Sips Url' and 'Bar Website' columns
df['Sips Url'] = df['Sips Url'].apply(url_to_sips)
df['Bar Website'] = df['Bar Website'].apply(url_to_link)

# Convert the DataFrame to an HTML table
df_html = df.to_html(index=False, escape=False, classes="table table-responsive table-striped table-bordered", justify='center') # type: ignore

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
with open('test.html', 'w') as file:
    file.write(soup.prettify())