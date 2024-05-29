import pandas as pd

csvName = "MasterTable.csv"
restaurant_df = pd.read_csv(csvName)
df = pd.read_csv(csvName)
main_df = pd.read_csv(csvName)
weight_reviews = 0.3  # Adjust this weight to favor number of reviews
weight_rating = 0.7   # Adjust this weight to favor average rating
weight_price = 0.7   # Adjust this weight to favor price
price_mapping = {
    '$': 1,
    '$$': 2,
    '$$$': 3,
    '$$$$': 4
}
restaurant_df['Price'] = restaurant_df['Price'].map(price_mapping)
restaurant_df['Price'].fillna(2, inplace=True)
restaurant_df['Yelp_Rating'] = pd.to_numeric(restaurant_df['Yelp_Rating'], errors='coerce')
# Min-Max Scaling for each factor
restaurant_df['Number_of_Reviews_Scaled'] = (restaurant_df['Review_Count'] - restaurant_df['Review_Count'].min()) / (restaurant_df['Review_Count'].max() - restaurant_df['Review_Count'].min())
restaurant_df['Average_Rating_Scaled'] = (restaurant_df['Yelp_Rating'] - restaurant_df['Yelp_Rating'].min()) / (restaurant_df['Yelp_Rating'].max() - restaurant_df['Yelp_Rating'].min())
restaurant_df['Price_Scaled'] = (restaurant_df['Price'] - restaurant_df['Price'].min()) / (restaurant_df['Price'].max() - restaurant_df['Price'].min())

# Calculate Popularity x Score with weighted factors
restaurant_df['Popularity'] = (
    weight_reviews * restaurant_df['Number_of_Reviews_Scaled'] +
    weight_rating * restaurant_df['Average_Rating_Scaled'] +
    weight_price * restaurant_df['Price_Scaled']
)
df['Popularity'] = (
    weight_reviews * restaurant_df['Number_of_Reviews_Scaled'] +
    weight_rating * restaurant_df['Average_Rating_Scaled'] +
    weight_price * restaurant_df['Price_Scaled']
)

# Find the minimum and maximum values of Popularity
min_popularity_score = restaurant_df['Popularity'].min()
max_popularity_score = restaurant_df['Popularity'].max()

# Perform the linear transformation to map it to the range [1, 50]
restaurant_df['Popularity'] = round(1 + (restaurant_df['Popularity'] - min_popularity_score) / (max_popularity_score - min_popularity_score) * 99)
df['RW_Score'] = round(1 + (df['Popularity'] - min_popularity_score) / (max_popularity_score - min_popularity_score) * 99)
df.drop(columns='Popularity', inplace=True)

# Sort the DataFrame by Popularity x Score in descending order to get the best restaurants
restaurant_df.sort_values(by='Popularity', ascending=False, inplace=True)

# Reset the index
restaurant_df.reset_index(drop=True, inplace=True)

# Print the DataFrame with the calculated score
print(restaurant_df[["Name", "Yelp_Rating", "Review_Count", "Price", "Popularity"]].head(50))
df['Popularity'] = restaurant_df['Popularity']
df.sort_values(by='RW_Score', ascending=False, inplace=True)
print(df[["Name", "Yelp_Rating", "Review_Count", "Price", "RW_Score", "Popularity"]].head(50))

# Replace values in main_df based on matching 'Name' column
for index, row in df.iterrows():
    name = row['Name']
    restaurant_week_score = row['RW_Score']
    popularity_score = row['Popularity']

    # Find the row in main_df with the matching 'Name' and update the scores
    main_df.loc[main_df['Name'] == name, 'RW_Score'] = restaurant_week_score
    main_df.loc[main_df['Name'] == name, 'Popularity'] = popularity_score

# main_df.to_csv("UpdatedMasterTable.csv", index=False)
