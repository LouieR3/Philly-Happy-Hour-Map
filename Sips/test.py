import pandas as pd
from yelpapi import YelpAPI
import yelpapi
from ast import literal_eval

df = pd.read_csv('Test.csv')
print(df)




# df = pd.read_csv('Test.csv', converters={'Categories': eval})
# print(df["Categories"])
print(df)
# print(df["Categories"][0])
# print(type(df["Categories"][0]))

# df.to_csv('Test2.csv', index=False)