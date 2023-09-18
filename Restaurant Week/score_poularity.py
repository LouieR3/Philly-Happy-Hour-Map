import pandas as pd

csvName = "MasterTable.csv"
df = pd.read_csv(csvName)
df = pd.read_csv(csvName)
weight_reviews = 0.3  # Adjust this weight to favor number of reviews
weight_rating = 0.7   # Adjust this weight to favor average rating
df['Yelp Rating'] = pd.to_numeric(df['Yelp Rating'], errors='coerce')
# df['Yelp Rating'] = df['Yelp Rating'] * 3
# Min-Max Scaling for each factor
df['Number_of_Reviews_Scaled'] = (df['Review Count'] - df['Review Count'].min()) / (df['Review Count'].max() - df['Review Count'].min())
df['Average_Rating_Scaled'] = (df['Yelp Rating'] - df['Yelp Rating'].min()) / (df['Yelp Rating'].max() - df['Yelp Rating'].min())
# df['Price_Scaled'] = (df['Price'] - df['Price'].min()) / (df['Price'].max() - df['Price'].min())

# Calculate Popularity x Score with weighted factors
df['Popularity Score'] = (
    weight_reviews * df['Number_of_Reviews_Scaled'] +
    weight_rating * df['Average_Rating_Scaled']
)
# df['Popularity Score'] = round(df['Popularity Score'] * 40)

# Find the minimum and maximum values of Popularity Score
min_Popularity_Score = df['Popularity Score'].min()
max_Popularity_Score = df['Popularity Score'].max()

# Perform the linear transformation to map it to the range [1, 50]
df['Popularity Score'] = round(1 + (df['Popularity Score'] - min_Popularity_Score) / (max_Popularity_Score - min_Popularity_Score) * 99)
df.drop(columns=['Average_Rating_Scaled', 'Number_of_Reviews_Scaled'], inplace=True)

# Sort the DataFrame by Popularity x Score in descending order to get the best restaurants
df.sort_values(by='Popularity Score', ascending=False, inplace=True)

# Reset the index
df.reset_index(drop=True, inplace=True)

# Print the DataFrame with the calculated score
print(df[["Name", "Yelp Rating", "Review Count", "Price", "Popularity Score", "Deals Offered"]].head(50))
print(df[["Name", "Yelp Rating", "Review Count", "Price", "Popularity Score", "Deals Offered"]])
df.to_csv("MasterTable.csv", index=False)
