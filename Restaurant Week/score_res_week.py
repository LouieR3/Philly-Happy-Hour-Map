import pandas as pd

csvName = "MasterTable.csv"
restaurant_df = pd.read_csv(csvName)
df = pd.read_csv(csvName)
weight_reviews = 0.3  # Adjust this weight to favor number of reviews
weight_rating = 0.7   # Adjust this weight to favor average rating
weight_price = 0.6   # Adjust this weight to favor price
price_mapping = {
    '$': 1,
    '$$': 2,
    '$$$': 3,
    '$$$$': 4
}
restaurant_df['Price'] = restaurant_df['Price'].map(price_mapping)
restaurant_df['Price'].fillna(2, inplace=True)
restaurant_df['Yelp Rating'] = pd.to_numeric(restaurant_df['Yelp Rating'], errors='coerce')
# Min-Max Scaling for each factor
restaurant_df['Number_of_Reviews_Scaled'] = (restaurant_df['Review Count'] - restaurant_df['Review Count'].min()) / (restaurant_df['Review Count'].max() - restaurant_df['Review Count'].min())
restaurant_df['Average_Rating_Scaled'] = (restaurant_df['Yelp Rating'] - restaurant_df['Yelp Rating'].min()) / (restaurant_df['Yelp Rating'].max() - restaurant_df['Yelp Rating'].min())
restaurant_df['Price_Scaled'] = (restaurant_df['Price'] - restaurant_df['Price'].min()) / (restaurant_df['Price'].max() - restaurant_df['Price'].min())

# Calculate Popularity x Score with weighted factors
restaurant_df['Popularity_Score'] = (
    weight_reviews * restaurant_df['Number_of_Reviews_Scaled'] +
    weight_rating * restaurant_df['Average_Rating_Scaled'] +
    weight_price * restaurant_df['Price_Scaled']
)
df['Popularity_Score'] = (
    weight_reviews * restaurant_df['Number_of_Reviews_Scaled'] +
    weight_rating * restaurant_df['Average_Rating_Scaled'] +
    weight_price * restaurant_df['Price_Scaled']
)

# Find the minimum and maximum values of Popularity_Score
min_popularity_score = restaurant_df['Popularity_Score'].min()
max_popularity_score = restaurant_df['Popularity_Score'].max()

# Perform the linear transformation to map it to the range [1, 50]
restaurant_df['Popularity_Score'] = round(1 + (restaurant_df['Popularity_Score'] - min_popularity_score) / (max_popularity_score - min_popularity_score) * 99)
df['Restaurant Week Score'] = round(1 + (df['Popularity_Score'] - min_popularity_score) / (max_popularity_score - min_popularity_score) * 99)
df.drop(columns='Popularity_Score', inplace=True)

# Sort the DataFrame by Popularity x Score in descending order to get the best restaurants
restaurant_df.sort_values(by='Popularity_Score', ascending=False, inplace=True)

# Reset the index
restaurant_df.reset_index(drop=True, inplace=True)

# Print the DataFrame with the calculated score
print(restaurant_df[["Name", "Yelp Rating", "Review Count", "Price", "Popularity_Score", "Deals Offered"]].head(50))
print(df[["Name", "Yelp Rating", "Review Count", "Price", "Restaurant Week Score", "Deals Offered"]].head(50))
df.to_csv("Test2.csv", index=False)
