import pandas as pd
import re

# Read the CSV file into a DataFrame
df = pd.read_csv('AllSipsOriginal.csv')

# Initialize empty lists for each deal type
cocktails = []
wine = []
beer = []
appetizers = []

# Iterate through each row in the DataFrame
for row in df.itertuples():
    # Use regular expressions to extract data for each deal type
    cocktails_match = re.search(r'\$7 Cocktails(.*?)\$6 Wine', row.Deals, re.DOTALL)
    wine_match = re.search(r'\$6 Wine(.*?)\$5 Beer', row.Deals, re.DOTALL)
    beer_match = re.search(r'\$5 Beer(.*?)Half-Priced Appetizers', row.Deals, re.DOTALL)
    appetizers_match = re.search(r'Half-Priced Appetizers(.*?)$', row.Deals, re.DOTALL)

    # Append extracted data to respective lists
    if cocktails_match:
        cocktails.append(cocktails_match.group(1).strip())
    else:
        cocktails.append(None)
    if wine_match:
        wine.append(wine_match.group(1).strip())
    else:
        wine.append(None)
    if beer_match:
        beer.append(beer_match.group(1).strip())
    else:
        beer.append(None)
    if appetizers_match:
        appetizers.append(appetizers_match.group(1).strip())
    else:
        appetizers.append(None)

# Create a new DataFrame with the extracted data
# Add the new columns to the DataFrame
df['Cocktails'] = cocktails
df['Wine'] = wine
df['Beer'] = beer
df['Half-Priced Appetizers'] = appetizers

# Drop the original 'Deals' column
df.drop(columns=['Deals'], inplace=True)

# Write the updated DataFrame to the same CSV file
df.to_csv('AllSipsLocations.csv', index=False)