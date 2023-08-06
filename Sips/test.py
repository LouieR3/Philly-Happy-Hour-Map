import pandas as pd
from yelpapi import YelpAPI
import yelpapi
from ast import literal_eval

df = pd.read_csv('Test.csv')
df = df.drop(['Website'], axis=1)
print(df)

# Function to safely convert a string to a list using literal_eval
def safe_literal_eval(x):
    try:
        return literal_eval(x)
    except (ValueError, SyntaxError):
        return []
df['Categories'] = df['Categories'].apply(safe_literal_eval)
df['Review Count'] = pd.to_numeric(df['Review Count'], errors='coerce').fillna(0).astype(int)
print(df)
print()
print(df["Categories"][0])
# makeList = list(df["Categories"][0])
# print(makeList)
print(type(df["Categories"][0]))

# df = pd.read_csv('Test.csv', converters={'Categories': eval})
# print(df["Categories"])
# print()
# print(df["Categories"][0])
# print(type(df["Categories"][0]))

df.to_csv('Test2.csv', index=False)