import pandas as pd
import json

data = pd.read_json("Yelp.json")
print(data)


df = pd.DataFrame(data)

# Print the DataFrame
print(df)
