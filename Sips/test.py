import pandas as pd
from yelpapi import YelpAPI
import yelpapi
from ast import literal_eval

df = pd.read_csv('Test.csv')
print(df)

# Function to safely convert a string to a list using literal_eval
def safe_literal_eval(x):
    try:
        return literal_eval(x)
    except (ValueError, SyntaxError):
        return []
df['Categories'] = df['Categories'].apply(safe_literal_eval)
df['Reviews'] = pd.to_numeric(df['Reviews'], errors='coerce').fillna(0).astype(int)
print(df)
print()
print(df["Categories"][0])
# makeList = list(df["Categories"][0])
# print(makeList)
print(type(df["Categories"][0]))
# Function to join categories into a comma-separated string
def join_categories(categories):
    return ', '.join(categories)

# Apply the function to the 'Categories' column
df['Categories'] = df['Categories'].apply(join_categories)


# df = pd.read_csv('Test.csv', converters={'Categories': eval})
# print(df["Categories"])
print(df)
# print(df["Categories"][0])
# print(type(df["Categories"][0]))

# df.to_csv('Test2.csv', index=False)