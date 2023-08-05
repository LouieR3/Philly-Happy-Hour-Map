import pandas as pd
import re

# Read the CSV file into a DataFrame
# df = pd.read_csv('AllSipsLocations.csv')
df = pd.read_csv('Test2.csv')

# Function to extract the prices for beers, wines, and cocktails from the "Deals" column
def extract_prices(deals):
    cocktail_price = re.search(r'\$7 Cocktails\n(.+?)\n\$6 Wine', deals, re.DOTALL)
    wine_price = re.search(r'\$6 Wine\n(.+?)\n\$5 Beer', deals, re.DOTALL)
    beer_price = re.search(r'\$5 Beer\n(.+?)\nHalf-Priced Appetizers', deals, re.DOTALL)
    appetizers = re.findall(r'Half-Priced Appetizers\n(.+)', deals, re.DOTALL)
    print(cocktail_price)
    if cocktail_price:
        cocktails = cocktail_price.group(1).strip().split('\n')
    else:
        cocktails = []

    if wine_price:
        wine = wine_price.group(1).strip().split('\n')
    else:
        wine = []

    if beer_price:
        beer = beer_price.group(1).strip().split('\n')
    else:
        beer = []

    if appetizers:
        appetizers = appetizers[0].strip().split('\n')
    else:
        appetizers = []

    return cocktails, wine, beer, appetizers

# Create new columns for Cocktails, Wine, Beer, and Appetizers
df['Cocktails'], df['Wine'], df['Beer'], df['Appetizers'] = zip(*df['Deals'].apply(extract_prices))

# Display the DataFrame with extracted prices
print(df[['Bar Name', 'Cocktails', 'Wine', 'Beer', 'Appetizers']])

# Define the general prices of beers, wines, and cocktails outside of happy hour
general_beer_price = 6.0
general_wine_price = 8.0
general_cocktail_price = 10.0

# Calculate scores for each bar based on the comparison of Sips deals with general prices
df['Beer Score'] = (general_beer_price - df['Beer Price']).fillna(0)
df['Wine Score'] = (general_wine_price - df['Wine Price']).fillna(0)
df['Cocktail Score'] = (general_cocktail_price - df['Cocktail Price']).fillna(0)

# Calculate the overall score for each bar by summing the individual scores
df['Overall Score'] = df['Beer Score'] + df['Wine Score'] + df['Cocktail Score']

# Rank the bars by the overall score to get the best deals
ranked_bars = df.sort_values(by='Overall Score', ascending=False)

# Display the ranked bars
print(ranked_bars[['Bar Name', 'Overall Score']])
