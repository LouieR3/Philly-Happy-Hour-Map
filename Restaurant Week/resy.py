import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys

# Step 1: Import the necessary libraries

# Step 2: Read the CSV file using Pandas
df = pd.read_csv('../Csv/MasterTable.csv')  # Replace 'your_csv_file.csv' with your actual CSV file path

# Step 3: Process the 'name' column
def process_name(name):
    # Make it all lowercase
    name = name.lower()
    
    # Replace spaces with -
    name = name.replace(' ', '-')
    
    # Replace + with and
    name = name.replace('+', 'and')
    
    # Remove any other characters
    name = ''.join(e for e in name if e.isalnum() or e == '-')
    
    return name

df['processed_name'] = df['Name'].apply(process_name)

# Step 4: Generate the URLs
base_url = "https://resy.com/cities/pha/"
df['url'] = base_url + df['processed_name']
driver = webdriver.Chrome()  # Replace with the path to your webdriver executable

# Step 5: Use requests to fetch the HTML content of the URLs
for url in df['url']:
    driver.get(url)
    
    # Wait for the page to load (you may need to adjust the sleep time or use more sophisticated waits)
    import time
    time.sleep(3)  # Wait for 5 seconds (adjust as needed)
    
    # Get the page source after it has loaded
    page_source = driver.page_source
    
    # Step 6: Parse the HTML using BeautifulSoup
    soup = BeautifulSoup(page_source, 'html.parser')
    
    # Now you can work with the soup object to extract information from the web page.
    # You can use various BeautifulSoup methods to locate and extract specific data.
    
    # Example: Print the title of the page
    title = soup.title
    print(url)
    h1_element = soup.find('h1', class_='VenuePage__venue-title')
    if h1_element:
        print("Venue Title:", h1_element.text)
    # else:
    #     print("Venue Title not found on", url)
    
    # Example: Find and print specific elements on the page
    # Replace 'your_selector' with the actual selector you need.
    specific_element = soup.select('your_selector')
    print("Specific Element:", specific_element)

# Close the WebDriver when done
driver.quit()
