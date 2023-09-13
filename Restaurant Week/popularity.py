import pandas as pd

csvName = "RestaurantWeek.csv"
restaurant_df = pd.read_csv(csvName)

weight_reviews = 0.4  # Adjust this weight to favor number of reviews
weight_rating = 0.6   # Adjust this weight to favor average rating
weight_price = 0.5   # Adjust this weight to favor price
price_mapping = {
    '$': 1,
    '$$': 2,
    '$$$': 3,
    '$$$$': 4
}
restaurant_df['Price'] = restaurant_df['Price'].map(price_mapping)
restaurant_df['Price'].fillna(2.5, inplace=True)

# Min-Max Scaling for each factor
restaurant_df['Number_of_Reviews_Scaled'] = (restaurant_df['Review Count'] - restaurant_df['Review Count'].min()) / (restaurant_df['Review Count'].max() - restaurant_df['Review Count'].min())
restaurant_df['Average_Rating_Scaled'] = (restaurant_df['Rating'] - restaurant_df['Rating'].min()) / (restaurant_df['Rating'].max() - restaurant_df['Rating'].min())
restaurant_df['Price_Scaled'] = (restaurant_df['Price'] - restaurant_df['Price'].min()) / (restaurant_df['Price'].max() - restaurant_df['Price'].min())

# Calculate Popularity x Score with weighted factors
restaurant_df['Popularity_x_Score'] = (
    weight_reviews * restaurant_df['Number_of_Reviews_Scaled'] +
    weight_rating * restaurant_df['Average_Rating_Scaled'] +
    weight_price * restaurant_df['Price_Scaled']
)

# Sort the DataFrame by Popularity x Score in descending order to get the best restaurants
restaurant_df.sort_values(by='Popularity_x_Score', ascending=False, inplace=True)

# Reset the index
restaurant_df.reset_index(drop=True, inplace=True)

# Print the DataFrame with the calculated score
print(restaurant_df[["Restaurant Name", "Rating", "Review Count", "Price", "Average_Rating_Scaled", "Popularity_x_Score", ]])