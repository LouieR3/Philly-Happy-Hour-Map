import pandas as pd
from yelpapi import YelpAPI
import yelpapi
from bs4 import BeautifulSoup
import requests
import time
import os
import json
import re
import fitz  # PyMuPDF
from io import BytesIO
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import random
from sklearn.metrics import accuracy_score
from tabulate import tabulate
import math

# ------------------------------------------------
# This script does = 
# ------------------------------------------------

df = pd.read_csv('SipsBarItems.csv', encoding='utf-8')

# Remove certain words from Menu Item values
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

keywords = ["tequila", "vodka", "rum", "gin", "whiskey", "bourbon", "pale ale", "stout", "lager", "light", "seltzer", "cider", "pilsner", "double ipa", "amber ale", "sour ale", "golden ale", "porter", "Oktoberfest ", "Hefeweizen ", "Belgian Witbier", "Doppelbock", "Blonde Ale", "California Common", "Cream Ale", "Brown Ale", "Kolsch "]

keyword_prices = {}

def x_round(x):
    return (round(x*4)/4)

for word in keywords:
  # Add leading space and convert to lowercase
  keyword = " " + word.lower()  
  
  matching = sips_deal_n_df[sips_deal_n_df["Drink"].str.lower().str.contains(keyword)]
  
  if len(matching) > 0:
    avg_price = matching["Price"].mean()
    avg_price = x_round(avg_price )
    
    keyword_prices[word] = avg_price

print(keyword_prices)

df = pd.read_csv("ComparisonResults.csv")
df["Sips Price"] = df["Sips Price"].str.replace("$", "").astype(float)
df["Normal Price"] = df["Normal Price"].str.replace("$", "").astype(float)
filtered_df = df[(df['Sips Price'].notnull()) & (df['Normal Price'].isnull())]
# print(filtered_df)
# Function to update Normal Price based on keyword mapping
def update_normal_price(row):
    drink = row['Drink'].lower()
    if not math.isnan(row['Sips Price']) and math.isnan(row['Normal Price']):
        for keyword, price in keyword_prices.items():
            if keyword in drink:
                # row['Normal Price'] = "${:.2f}".format(price)
                row['Normal Price'] = price
                comparison_result = price - row['Sips Price']
                row['Comparison Result'] = comparison_result
                break
    return row

# Apply the function to each row in the filtered DataFrame
# filtered_df = filtered_df.apply(update_normal_price, axis=1)
df = df.apply(update_normal_price, axis=1)

df["Sips Price"] = df["Sips Price"].apply(lambda x: "${:.2f}".format(x)) # type: ignore
df["Normal Price"] = df["Normal Price"].apply(lambda x: "${:.2f}".format(x)) # type: ignore
df["Sips Price"] = df["Sips Price"].replace("$nan", "") # type: ignore
df["Normal Price"] = df["Normal Price"].replace("$nan", "") # type: ignore
df = df.sort_values(by="Comparison Result", ascending=False) # type: ignore

# Save the updated DataFrame back to the CSV file
df.to_csv("ComparisonResults2.csv", index=False)