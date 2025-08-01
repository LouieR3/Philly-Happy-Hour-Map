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
from PyPDF2 import PdfReader
from io import BytesIO

deals = "https://centercityphila.org/uploads/attachments/cm9ral94oc62ysyqd606myqmn-pizzeria-vetri-sips-menu.pdf"
deals = "https://centercityphila.org/uploads/attachments/cmc95cyl6rrncsyqd7yxed2o7-thirteen.jpg"
deals = "https://centercityphila.org/uploads/attachments/cmbibwguujt5vvfqded5jvi1w-tir-na-nog.pdf"
# Fetch the PDF content directly
response = requests.get(deals)
response.raise_for_status()  # Raise an error if the request fails

# Read the PDF content from the response
pdf_file = BytesIO(response.content)  # Create a file-like object from the response content
reader = PdfReader(pdf_file)
pdf_text = ""
for page in reader.pages:
    pdf_text += page.extract_text()

print("PDF Content:")
print(pdf_text)