
import pandas as pd

# Read the CSV file
df = pd.read_csv('SipsBarItems.csv')
df = df.drop_duplicates(subset=['Menu Item'])
# Filter rows where price is "$5"
filtered_df = df[df['Price'] == '$5']

# Extract the "Menu Item" values
menu_items = filtered_df['Menu Item'].tolist()

# Write menu items to a text file
with open('beers.txt', 'w') as f:
    for item in menu_items:
        f.write(item + '\n')