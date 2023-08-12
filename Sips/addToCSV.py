import pandas as pd
from yelpapi import YelpAPI
import yelpapi
from bs4 import BeautifulSoup
import requests
import time
import os
import re

df = pd.read_csv("AllSipsLocations.csv")
print(df)
menu_data = []

for index, row in df.iterrows():
    deals = row["Deals"]
    # deals = deals.replace('\r\n', ' ')

    half_priced_appetizers_index = deals.find("Half-Priced Appetizer")
    if half_priced_appetizers_index != -1:
        deals = deals[:half_priced_appetizers_index]

    sections = re.split(r"(\$[0-9]+\s\w+)", deals)
    sections = [s.strip() for s in sections if s.strip() != ""]
    print(row["Bar Name"])
    # Remove any empty or null sections
    # print(sections)
    sections = [s.split("Half-Priced Appetizers")[0] for s in sections if s]
    print(sections)
    for i in range(0, len(sections) - 1, 2):
        # print(re.sub(r'^\$', '', sections[i]).strip())
        drink_type = (
            sections[i].replace("$", "").strip().split("Half-Priced Appetizers")[0]
        )
        if drink_type == "Half-Priced Appetizers":
            break
        price = f'${drink_type.split(" ")[0]}'
        menu_items = sections[i + 1].split("\n")
        menu_items = [item.strip() for item in menu_items if item.strip() != ""]
        menu_items = [
            item
            for item in menu_items
            if "all beer" not in item.lower()
            and "all wine" not in item.lower()
            and "all house wine" not in item.lower()
            and "rotating" not in item.lower()
            and "select drafts" not in item.lower()
            and "selection" not in item.lower()
            and "domestic beer" not in item.lower()
            and "domestic draft" not in item.lower()
            and "featured draft" not in item.lower()
            and "draft beer" not in item.lower()
        ]

        # Exclude "rotating draft"
        menu_items = [
            item
            for item in menu_items
            if "rotating draft" and "15% off dinner!" not in item.lower()
        ]
        menu_items = [item.split("-")[0].strip() for item in menu_items]

        individual_menu_items = []
        if "beer" in drink_type.lower() or "wine" in drink_type.lower():
            print(drink_type)
            print(menu_items)
            print("+++++")
            for menu_item in menu_items:
                if "," in menu_item:
                    individual_menu_items.append(menu_item.split(",")[0].strip())
                else:
                    individual_menu_items.append(menu_item.strip())
        else:
            for menu_item in menu_items:
                individual_menu_items.append(menu_item.strip())

        print(individual_menu_items)
        # for menu_item in menu_items:
        for menu_item in individual_menu_items:
            menu_data.append(
                {
                    "Bar": row["Bar Name"],
                    "Menu Item": menu_item.strip(),
                    "Price": price,
                    "Sips Deal": "Y",
                }
            )
    print()

menu_df = pd.DataFrame(menu_data)
print(menu_df)
menu_df.to_csv("TestMenu.csv", index=False)
