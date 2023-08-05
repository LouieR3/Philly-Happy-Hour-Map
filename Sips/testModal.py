from bs4 import BeautifulSoup
import requests
import pandas as pd
from tabulate import tabulate
from geopy.geocoders import Nominatim
import time
import os
import folium
import re
import json
from selenium import webdriver
from selenium.webdriver.common.by import By

url = 'https://centercityphila.org/explore-center-city/ccd-sips/sips-list-view#cavanaugh-s-rittenhouse'

driver = webdriver.Chrome()
driver.get(url)

# Wait for modal to load
driver.implicitly_wait(10) 

# Switch to modal iframe
iframe = driver.find_element(By.TAG_NAME, 'iframe')
driver.switch_to.frame(iframe)

# Now scrape content inside modal...
content = driver.page_source
print(content)
driver.quit()