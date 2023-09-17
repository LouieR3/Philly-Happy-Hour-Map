from bs4 import BeautifulSoup
import requests
import json
import html
import re

url = "https://www.yelp.com/biz/ocean-prime-philadelphia"

# Fetch page HTML
response = requests.get(url)
html = response.text

# Parse HTML with BeautifulSoup  
soup = BeautifulSoup(html, "html.parser")

# Find the <script> tag
script_tag = soup.find("script", {"data-apollo-state": True})
# Extract JSON string 
json_str = script_tag.text # type: ignore

# Remove <!-- and -->
cleaned = json_str[4:-3]
# Add outer quotes
# cleaned = cleaned.replace('\\&quot;', '"')
# cleaned = cleaned.replace('&quot;', '"')
# cleaned = f'"{cleaned}"'
json_str = re.sub(r'&quot;', '"', cleaned)

# Parse the JSON string into a Python object
json_object = json.loads(json_str)

# Now you can work with the JSON object in Python
print(json_object)

file_name = "output2.json"

# Write the JSON data to the file
with open(file_name, "w") as json_file:
    json.dump(json_object, json_file, indent=4)

print(f"JSON data has been saved to {file_name}")
# Replace unescaped double quotes 
# cleaned = cleaned.replace('"', '\\"')
# cleaned = cleaned.replace('&quot;', '"')
# cleaned = f'"{cleaned}"'
# # cleaned = cleaned.replace('\\', '')
# print(cleaned)

# # Parse into JSON
# json_obj = json.loads(cleaned)

# print(json_obj)