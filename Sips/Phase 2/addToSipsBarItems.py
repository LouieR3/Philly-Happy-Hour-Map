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

# ------------------------------------------------
# This script does = dfToAdd can be swapped out for a new method of getting a bars menu and then you can add it to SipsBarItems and then to ComparisonResults after
# ------------------------------------------------

df = pd.read_csv('SipsBarItems.csv', encoding='utf-8')

def dfToAdd(pdf_path):
    def extract_drinks_from_pdf(pdf_path):
        try:
            response = requests.get(pdf_path)
            # print(response.content)
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
                            drink_price = '${:,.2f}'.format(price)

                            drink_name = re.sub(r'\(.+?\)', '', drink_name).strip()

                            if drink_name and drink_price and price < 24:
                                drinks.append((drink_name.strip(), drink_price.strip()))
                            drink_name = ""
                            break
                        else:
                            drink_name += component + " "
                    
        df = pd.DataFrame(drinks, columns=["Drink", "Price"])
        bar_name = "Barbuzzo"
        df.insert(0, "Bar", bar_name)
        return df
    
    extracted_text = extract_drinks_from_pdf(pdf_path)
    if extracted_text:
        # print(extracted_text)
        menu_df = create_dataframe_from_text(extracted_text)
        return menu_df
    else:
        print("Failed to extract text from PDF.")
        menu_df = pd.DataFrame()
        return menu_df

def combineCSV(menu_df):
    # menu_df = pd.DataFrame(menu_data)
    print(menu_df)
    # Read 'SipsBarItems.csv' into a DataFrame
    sips_bar_items_df = pd.read_csv('SipsBarItems.csv')

    # Combine menu_df and sips_bar_items_df
    combined_df = pd.concat([sips_bar_items_df, menu_df])

    # Drop duplicates based on 'Bar', 'Drink', and 'Price'
    combined_df.drop_duplicates(subset=['Bar', 'Drink', 'Price'], inplace=True)

    # Write the combined DataFrame to a new CSV file
    combined_df.to_csv('SipsBarItems.csv', index=False)

def machineLearning(menu_df):
    # Load training data from quick.txt 
    with open('wines.txt', encoding='utf-8') as f:
        wine_types = f.read().splitlines()
    with open('winesTestData.txt', encoding='utf-8') as f:  
        wine_drinks = f.read().splitlines()
    # Load cocktail training data    
    with open('cocktails.txt', encoding='utf-8') as f:
        cocktail_types = f.read().splitlines() 
    with open('cocktailsTestData.txt', encoding='utf-8') as f:
        cocktail_drinks = f.read().splitlines()
    # Load cocktail training data    
    with open('beers.txt', encoding='utf-8') as f:
        beer_types = f.read().splitlines() 
    with open('beersTestData.txt', encoding='utf-8') as f:
        beer_drinks = f.read().splitlines()

    # Combine data
    train_types = wine_types + cocktail_types + beer_types 
    train_drinks = wine_drinks + cocktail_drinks + beer_drinks 
    df_train = pd.DataFrame({'Drink': train_drinks, 
                            'CommonDrinkType': train_types})

    # Load test data
    df_test = menu_df

    df_train['Drink'] = df_train['Drink'].str.lower()
    df_test['DrinkTest'] = df_test['Drink'].str.lower()
    extra_words = ["can", "draft", "bottle", "house"]
    df_train['Drink'] = df_train['Drink'].apply(lambda x: ' '.join([word for word in x.split() if word not in extra_words]))
    df_test['DrinkTest'] = df_test['Drink'].apply(lambda x: ' '.join([word for word in x.split() if word not in extra_words]))

    # Tokenize and vectorize drink names
    vectorizer = TfidfVectorizer()
    X_train = vectorizer.fit_transform(df_train['Drink']) 
    # Train model 
    model = LogisticRegression()
    model.fit(X_train, df_train['CommonDrinkType'])
    # Vectorize test data
    X_test = vectorizer.transform(df_test['DrinkTest'])
    df_test = df_test.drop(['DrinkTest'], axis=1)
    # Predict types for test data
    predicted_types = model.predict(X_test)
    # Predict probabilities for test data
    predicted_probs = model.predict_proba(X_test)
    # Get the certainty for the predicted class
    certainty = predicted_probs.max(axis=1)  # Max probability along columns

    # Add certainty column to the dataframe
    newDrinks = []
    for pred_type in df_test['Drink']:
        if pred_type not in beer_types and pred_type not in wine_types and pred_type not in cocktail_types:
            newDrinks.append(pred_type)
    print()
    print(newDrinks)
    print()

    # df_test['Predicted Item'] = predicted_types
    df_test.insert(2, "Predicted Item", predicted_types)
    # df_test['Certainty'] = certainty
    # df_test.to_csv("Test.csv", index=False, encoding='utf-8')
    # df_test.to_csv("SipsBarItems.csv", index=False, encoding='utf-8')
    return df_test

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
    for menu_item in df["Predicted Item"].unique():
        sips_price = sips_deal_y_df[sips_deal_y_df["Predicted Item"] == menu_item][
            "Price"
        ].mean()
        sips_bar = (
            sips_deal_y_df[sips_deal_y_df["Predicted Item"] == menu_item]["Bar"].iloc[0]
            if not pd.isna(sips_price)
            else ""
        )
        normal_price = sips_deal_n_df[sips_deal_n_df["Predicted Item"] == menu_item][
            "Price"
        ].mean()

        comparison_result = None
        if sips_price is not None and normal_price is not None:
            comparison_result = normal_price - sips_price
            comparison_result = round(comparison_result, 2)
            
        results_df = results_df.append(
            {
                "Drink": menu_item,
                "Sips Price": "${:.2f}".format(sips_price),
                "Normal Price": "${:.2f}".format(normal_price),
                "Comparison Result": comparison_result,
                "Sips Bar": sips_bar,
            },
            ignore_index=True,
        )  # type: ignore
    results_df = results_df.sort_values(by="Comparison Result", ascending=False)
    # Save the results dataframe to a CSV file
    results_df["Sips Price"] = results_df["Sips Price"].replace("$nan", "")
    results_df["Normal Price"] = results_df["Normal Price"].replace("$nan", "")
    results_df.to_csv("ComparisonResults.csv", index=False)
    print(results_df)

menu_df = dfToAdd("http://www.barbuzzo.com/Pdfs/barbuzzoBEVERAGE_MENU.pdf")
if not menu_df.empty:
    menu_df["Sips Deal"] = "N"
    # print(menu_df)
    final_df = machineLearning(menu_df)
    print(final_df)
    if not final_df.empty:
        combineCSV(final_df)
        calculateDeal()