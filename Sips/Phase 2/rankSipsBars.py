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

# Initialize an empty results dataframe
results_df = pd.DataFrame(
    columns=["Drink", "Sips Price", "Normal Price", "Comparison Result"]
)

for sips_bar in sips_deal_y_df["Bar"].unique():
    bar_deals = sips_deal_y_df[sips_deal_y_df["Bar"] == sips_bar]
    print(bar_deals)
    print()
    new_df = pd.DataFrame(
        columns=["Bar", "Drink", "Sips Price", "Normal Price", "Comparison Result", "Comparison Fraction"]
    )
    for menu_item in bar_deals["Predicted Item"]:
        sips_price = sips_deal_y_df[sips_deal_y_df["Predicted Item"] == menu_item][
            "Price"
        ].mean()
        sips_price = round(sips_price, 2)
        sips_bar2 = (
            sips_deal_y_df[sips_deal_y_df["Predicted Item"] == menu_item]["Bar"].iloc[0]
            if not pd.isna(sips_price)
            else ""
        )
        normal_price = sips_deal_n_df[sips_deal_n_df["Predicted Item"] == menu_item][
            "Price"
        ].mean()
        sips_price = round(sips_price, 2)
        normal_price = round(normal_price, 2)
        comparison_result = None
        if not math.isnan(sips_price) and not math.isnan(normal_price):
            comparison_result = normal_price - sips_price
            comparison_result = round(comparison_result, 2)

            comparison_frac = (1 - (sips_price / normal_price)) * 100
            comparison_frac = round(comparison_frac)
            results_df = results_df.append(
                {
                    "Drink": menu_item,
                    "Sips Price": "${:.2f}".format(sips_price),
                    "Normal Price": "${:.2f}".format(normal_price),
                    "Comparison Result": comparison_result,
                    # "Comparison Fraction": "{}%".format(comparison_frac),
                    "Comparison Fraction": comparison_frac,
                    "Sips Bar": sips_bar,
                }, ignore_index=True, )  # type: ignore
            new_df = new_df.append({
                "Bar": sips_bar,
                "Drink": menu_item,
                "Sips Price": "${:.2f}".format(sips_price),
                "Normal Price": "${:.2f}".format(normal_price),
                "Comparison Result": comparison_result,
                # "Comparison Fraction": "{}%".format(comparison_frac),
                "Comparison Fraction": comparison_frac,
            }, ignore_index=True, ) # type: ignore
    print(new_df)
    print()

    # Calculate total comparsion for each bar 
    # bar_totals = new_df.groupby('Bar').agg({'Comparison Result':'sum', 'Comparison Fraction':'mean'})

    # # Get min/max for normalization 
    # min_result = bar_totals['Comparison Result'].min()
    # max_result = bar_totals['Comparison Result'].max()
    # min_fraction = bar_totals['Comparison Fraction'].min() 
    # max_fraction = bar_totals['Comparison Fraction'].max()

    # # Normalize to 0-9.9
    # bar_totals['Result Score'] = (bar_totals['Comparison Result'] - min_result) / (max_result - min_result) * 9.9
    # bar_totals['Fraction Score'] = (bar_totals['Comparison Fraction'] - min_fraction) / (max_fraction - min_fraction) * 9.9

    # # Average the two scores
    # bar_totals['Deal Score'] = (bar_totals['Result Score'] + bar_totals['Fraction Score']) / 2

    # # Round score
    # bar_totals['Deal Score'] = bar_totals['Deal Score'].round(1)

    # print(bar_totals.sort_values('Deal Score', ascending=False))
print(results_df)

# Calculate total comparsion for each bar 
bar_totals = results_df.groupby('Sips Bar').agg({'Comparison Result':'sum', 'Comparison Fraction':'mean'})

bar_totals['Deal Count'] = results_df.groupby('Sips Bar')['Drink'].count()
bar_totals['Deal Weight'] = bar_totals['Deal Count'] / bar_totals['Deal Count'].max()

# Get min/max for normalization 
min_result = bar_totals['Comparison Result'].min()
max_result = bar_totals['Comparison Result'].max()
min_fraction = bar_totals['Comparison Fraction'].min() 
max_fraction = bar_totals['Comparison Fraction'].max()

# Normalize to 0-9.9
bar_totals['Result Score'] = (bar_totals['Comparison Result'] - min_result) / (max_result - min_result) * 9.9
bar_totals['Fraction Score'] = (bar_totals['Comparison Fraction'] - min_fraction) / (max_fraction - min_fraction) * 9.9

# Average the two scores
bar_totals['Deal Score'] = (
  bar_totals['Result Score'] * bar_totals['Deal Weight'] +
  bar_totals['Fraction Score'] * bar_totals['Deal Weight']  
) / 2
bar_totals['Deal Score'] = bar_totals['Deal Score'].fillna(2)

# Round score
bar_totals['Deal Score'] = bar_totals['Deal Score'].round(1)

print(bar_totals.sort_values('Deal Score', ascending=False))

# Get list of all bars
all_bars = pd.read_csv('AllSipsLocations.csv')['Bar Name']

# Fill missing with default
bar_totals = bar_totals.reindex(all_bars, fill_value=5)

bar_totals['Sips Bar'] = bar_totals['Deal Score'].round(1)
results_df.to_csv("ComparisonResults2.csv", index=False)
# bar_totals.to_csv("ComparisonResults2.csv")
# Compare prices for each unique Drink
# for menu_item in df["Predicted Item"].unique():
#     sips_price = sips_deal_y_df[sips_deal_y_df["Predicted Item"] == menu_item][
#         "Price"
#     ].mean()
#     sips_price = round(sips_price, 2)
#     sips_bar = (
#         sips_deal_y_df[sips_deal_y_df["Predicted Item"] == menu_item]["Bar"].iloc[0]
#         if not pd.isna(sips_price)
#         else ""
#     )
#     normal_price = sips_deal_n_df[sips_deal_n_df["Predicted Item"] == menu_item][
#         "Price"
#     ].mean()
#     sips_price = round(sips_price, 2)
#     normal_price = round(normal_price, 2)
#     comparison_result = None
#     if sips_price is not None and normal_price is not None:
#         comparison_result = normal_price - sips_price
#         comparison_result = round(comparison_result, 2)

#     results_df = results_df.append(
#         {
#             "Drink": menu_item,
#             "Sips Price": "${:.2f}".format(sips_price),
#             "Normal Price": "${:.2f}".format(normal_price),
#             "Comparison Result": comparison_result,
#             "Sips Bar": sips_bar,
#         },
#         ignore_index=True,
#     )  # type: ignore

# results_df = results_df.sort_values(by="Comparison Result", ascending=False)
# results_df["Sips Price"] = results_df["Sips Price"].replace("$nan", "")
# results_df["Normal Price"] = results_df["Normal Price"].replace("$nan", "")

# results_by_bar = results_df.groupby('Sips Bar').agg({'Comparison Result': 'sum'}).reset_index()

# # Get total comparison for each bar
# for bar in results_by_bar['Sips Bar'].unique():
#     total = results_by_bar[results_by_bar['Sips Bar'] == bar]['Comparison Result'].sum()
#     print(f"{bar} total: {total}")

# # Save the results dataframe to a CSV file
# # results_df.to_csv("ComparisonResults.csv", index=False)

# print(results_df)
