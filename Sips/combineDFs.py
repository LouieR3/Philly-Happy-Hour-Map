import pandas as pd
from yelpapi import YelpAPI
import yelpapi


# yelpapiKey = "DQx0YugiFJ5inYYp8fVvDqLx0R_dVo8yXxRZtpD5jkbNK0WmAqUygKIyXnYHlfL0pYRndGHGmuvn_QCXPVndRCc0VjtZzxCSHE8MhPthoJ4YUygg65DJrhMJLu7OZHYx"

# yelp = yelpapi.YelpAPI(yelpapiKey)

# bar_name = "Fahrenheit 451 Pizza and Bar"
# print("--------------------------------------------")
# print(bar_name)
# address = "1815 John F Kennedy Blvd., Philadelphia, PA 19103"

# # Split the address into parts based on commas
# parts = address.split(", ")

# # Extract individual components
# street_address = parts[0]
# city = parts[1]
# state_zip = parts[2]

# # Split the state and ZIP code
# state, zipcode = state_zip.split(' ')

# # Use the Yelp API to search for the bar by its name and location (address)
# # response = yelp.business_query(name=bar_name, location=address) # type: ignore
# match_response = yelp.business_match_query(name=bar_name, address1=street_address, city=city, state=state, country='US", postal_code=zipcode) # type: ignore
# print(match_response)
df = pd.read_csv('AllSipsLocations.csv')
# Your object containing 70 dictionaries
data = [
{"Bar Name": "1225 Raw Sushi and Sake Lounge*", "Rating": 3.5, "Review Count": 580, "Price": "$$", "Categories": ["Japanese", "Sushi Bars", "Korean"], "Website": "https://1225rawnledas.com"},
{"Bar Name": "1518 Bar and Grill", "Rating": 4.0, "Review Count": 251, "Price": "$$", "Categories": ["Bars", "American (Traditional)"], "Website": "http://www.1518barandgrill.com"},
{"Bar Name": "Air Grille Garden at Dilworth Park", "Rating": 4.0, "Review Count": 64, "Price": None, "Categories": ["Parks"], "Website": "http://dilworthpark.org/dining"},
{"Bar Name": "Ancient Spirits & Grille", "Rating": 3.5, "Review Count": 72, "Price": "$$", "Categories": ["Lounges", "Cocktail Bars", "Modern European"], "Website": "https://asgphilly.com"},
{"Bar Name": "ArtBar at Sonesta Hotel", "Rating": 3.0, "Review Count": 38, "Price": "$$", "Categories": ["Hotels", "Coffee & Tea", "Lounges"], "Website": "https://www.sonesta.com/sonesta-hotels-resorts/pa/philadelphia/sonesta-philadelphia-rittenhouse-square#hoteldetails_dining"},
{"Bar Name": "The Balcony Bar at the Kimmel Center", "Rating": 3.5, "Review Count": 10, "Price": None, "Categories": ["Pop-Up Restaurants"], "Website": None},
{"Bar Name": "Bank and Bourbon*", "Rating": 3.5, "Review Count": 431, "Price": "$$$", "Categories": ["American (New)", "Gastropubs"], "Website": "http://bankandbourbon.com"},
{"Bar Name": "Bar Bombón", "Rating": 4.0, "Review Count": 825, "Price": "$$", "Categories": ["Vegetarian", "Latin American"], "Website": "http://barbombon.com"},
{"Bar Name": "Bar-Ly Chinatown", "Rating": 4.0, "Review Count": 453, "Price": "$$", "Categories": ["Sports Bars", "Tapas Bars", "Gastropubs"], "Website": "http://www.Bar-Ly.com"},
{"Bar Name": "Barbuzzo", "Rating": 4.5, "Review Count": 3178, "Price": "$$", "Categories": ["Mediterranean", "Pizza", "Italian"], "Website": "http://www.barbuzzo.com"},
{"Bar Name": "Barstool Sansom Street", "Rating": 2.5, "Review Count": 49, "Price": None, "Categories": ["Sports Bars", "Chicken Wings", "Cocktail Bars"], "Website": "http://barstoolsansomstreet.com"},
{"Bar Name": "The Black Sheep", "Rating": 3.5, "Review Count": 371, "Price": "$$", "Categories": ["Irish Pub", "Sports Bars"], "Website": "http://www.theblacksheeppub.com"},
{"Bar Name": "Blume Burger", "Rating": 2.5, "Review Count": 200, "Price": "$$", "Categories": ["Bars", "Breakfast & Brunch", "Burgers"], "Website": "http://blumephilly.com"},
{"Bar Name": "Bodega Taco Bar", "Rating": 3.5, "Review Count": 98, "Price": "$$", "Categories": ["Latin American", "Cocktail Bars", "Cuban"], "Website": "https://www.bodegaphilly.com"},
{"Bar Name": "Brü Craft & Wurst", "Rating": 3.5, "Review Count": 553, "Price": "$$", "Categories": ["Bars", "German"], "Website": "http://www.bruphilly.com"},
{"Bar Name": "Buca D'oro Ristorante", "Rating": 3.5, "Review Count": 118, "Price": "$$$", "Categories": ["Italian", "Wine Bars", "Seafood"], "Website": "http://bucadororistorante.com"},
{"Bar Name": "Butcher Bar", "Rating": 4.0, "Review Count": 752, "Price": "$$", "Categories": ["Steakhouses", "Bars", "Comfort Food"], "Website": "http://www.butcherbarphilly.com"},
{"Bar Name": "Capriccio Café and Bar", "Rating": 3.0, "Review Count": 145, "Price": "$", "Categories": ["Coffee & Tea", "Breakfast & Brunch", "Beer, Wine & Spirits"], "Website": "http://capricciocafe.com"},
{"Bar Name": "The Cauldron Philly", "Rating": 4.0, "Review Count": 103, "Price": None, "Categories": ["Bars"], "Website": "https://thecauldron.io/philly"},
{"Bar Name": "Cavanaugh's Rittenhouse", "Rating": 3.5, "Review Count": 250, "Price": "$$", "Categories": ["Sports Bars", "Gastropubs", "Burgers"], "Website": "http://www.cavsrittenhouse.com"},
{"Bar Name": "City Tap House Logan Square", "Rating": 2.5, "Review Count": 127, "Price": "$$", "Categories": ["Bars"], "Website": "http://citytaphouselogan.com"},
{"Bar Name": "Con Murphy's Irish Pub", "Rating": 3.5, "Review Count": 348, "Price": "$$", "Categories": ["Irish", "Pubs", "Sports Bars"], "Website": "http://www.conmurphyspub.com"},
{"Bar Name": "Continental Midtown", "Rating": 3.5, "Review Count": 1844, "Price": "$$", "Categories": ["American (New)", "Breakfast & Brunch", "Cocktail Bars"], "Website": "https://continentalmidtown.com"},
{"Bar Name": "Craftsman Row Saloon", "Rating": 3.5, "Review Count": 309, "Price": "$$", "Categories": ["Pubs"], "Website": "http://www.craftsmanrowsaloon.com"},
{"Bar Name": "Darling Jack's Tavern", "Rating": 4.5, "Review Count": 23, "Price": None, "Categories": ["American (New)", "American (Traditional)", "Wine Bars"], "Website": "http://www.darlingjacks.com"},
{"Bar Name": "Devil's Alley", "Rating": 3.5, "Review Count": 856, "Price": "$$", "Categories": ["American (New)", "Bars", "Breakfast & Brunch"], "Website": "http://www.devilsalleybarandgrill.com"},
{"Bar Name": "Dim Sum House by Jane G's*", "Rating": 4.0, "Review Count": 554, "Price": "$$", "Categories": ["Szechuan", "Dim Sum", "Cantonese"], "Website": "http://dimsum.house"},
{"Bar Name": "Dolce Italian", "Rating": 4.0, "Review Count": 36, "Price": None, "Categories": ["Italian", "Pizza", "Breakfast & Brunch"], "Website": "http://www.dolceitalianrestaurant.com/location/philadelphia"},
{"Bar Name": "Double Knot", "Rating": 4.5, "Review Count": 1329, "Price": "$$$", "Categories": ["Sushi Bars", "Bars", "Japanese"], "Website": "https://www.doubleknotphilly.com"},
{"Bar Name": "Drinker's Pub", "Rating": 3.5, "Review Count": 320, "Price": "$", "Categories": ["Pubs", "Gastropubs"], "Website": "http://www.drinkersrittenhouse.com"},
{"Bar Name": "Drury Beer Garden (DBG)", "Rating": 3.5, "Review Count": 91, "Price": "$$", "Categories": ["Bars"], "Website": "http://www.drurybeergarden.com"},
{"Bar Name": "Fado Irish Pub", "Rating": 3.5, "Review Count": 483, "Price": "$$", "Categories": ["Irish", "Irish Pub"], "Website": "http://fadoirishpub.com/philadelphia"},
{"Bar Name": "Fahrenheit 451 Pizza and Bar", "Rating": 3.0, "Review Count": 12, "Price": None, "Categories": ["Pizza", "Bars"], "Website": "https://www.fahrenheit451pizzaandbar.com"},
{"Bar Name": "Finn McCools Ale House", "Rating": 3.5, "Review Count": 171, "Price": "$$", "Categories": ["Pubs", "Sports Bars", "American (Traditional)"], "Website": "http://www.finnmccoolsphilly.com"},
{"Bar Name": "Flambo Caribbean Restaurant*", "Rating": 3.0, "Review Count": 19, "Price": None, "Categories": ["Trinidadian"], "Website": "http://www.flamboh.com"},
{"Bar Name": "Giovani's Bar & Grill", "Rating": 4.0, "Review Count": 257, "Price": "$", "Categories": ["Sports Bars", "Mediterranean", "Pizza"], "Website": "http://giovanibarandgrill.com"},
{"Bar Name": "Giuseppe and Sons", "Rating": 4.0, "Review Count": 403, "Price": "$$", "Categories": ["Italian", "Bars"], "Website": "https://giuseppesons.com"},
{"Bar Name": "The Goat Rittenhouse", "Rating": 3.5, "Review Count": 45, "Price": None, "Categories": ["Bars", "American (Traditional)"], "Website": "https://www.thegoatrittenhouse.com"},
{"Bar Name": "Gran Caffe L'Aquila", "Rating": 4.5, "Review Count": 1385, "Price": "$$", "Categories": ["Coffee & Tea", "Italian", "Gelato"], "Website": "http://grancaffelaquila.com"},
{"Bar Name": "Hard Rock Cafe", "Rating": 2.5, "Review Count": 438, "Price": "$$", "Categories": ["American (Traditional)", "Burgers"], "Website": "https://www.hardrockcafe.com/location/philadelphia"},
{"Bar Name": "Harp & Crown", "Rating": 4.0, "Review Count": 1103, "Price": "$$", "Categories": ["American (New)", "Gastropubs"], "Website": "http://harpcrown.com"},
{"Bar Name": "The Hayes", "Rating": 4.0, "Review Count": 10, "Price": "$$", "Categories": ["American (New)", "Desserts", "Cocktail Bars"], "Website": "http://www.thehayesphl.com"},
{"Bar Name": "Independence Beer Garden", "Rating": 3.5, "Review Count": 552, "Price": "$$", "Categories": ["Beer Gardens", "Barbeque"], "Website": "http://phlbeergarden.com"},
{"Bar Name": "Iron Hill Brewery & Restaurant", "Rating": 4.0, "Review Count": 463, "Price": "$$", "Categories": ["American (Traditional)", "Brewpubs"], "Website": "https://www.ironhillbrewery.com/center-city-pa"},
{"Bar Name": "Kook Burger & Bar", "Rating": 3.5, "Review Count": 58, "Price": None, "Categories": ["Burgers", "Juice Bars & Smoothies", "Beer Bar"], "Website": "https://www.kookburgerbar.com"},
{"Bar Name": "Ladder 15", "Rating": 3.0, "Review Count": 335, "Price": "$$", "Categories": ["American (New)"], "Website": "http://www.ladder15philly.com"},
{"Bar Name": "Leda and the Swan Cocktail Lounge", "Rating": 3.5, "Review Count": 43, "Price": None, "Categories": ["Cocktail Bars", "Lounges", "Music Venues"], "Website": "http://www.lnsphilly.com"},
{"Bar Name": "Little Nonna's", "Rating": 4.0, "Review Count": 1326, "Price": "$$", "Categories": ["Italian"], "Website": "http://www.littlenonnas.com"},
{"Bar Name": "Marathon 16th & Sansom", "Rating": 3.5, "Review Count": 647, "Price": "$$", "Categories": ["American (New)", "Breakfast & Brunch", "Sandwiches"], "Website": "http://www.eatmarathon.com"},
{"Bar Name": "Misconduct Tavern", "Rating": 3.0, "Review Count": 156, "Price": "$$", "Categories": ["American (New)", "Bars"], "Website": "http://misconducttavern.com"},
{"Bar Name": "The Mulberry on Arch", "Rating": 4.0, "Review Count": 65, "Price": None, "Categories": ["American (Traditional)", "Pubs"], "Website": "https://www.themulberryphl.com"},
{"Bar Name": "Pagano's Market and Bar", "Rating": 3.0, "Review Count": 85, "Price": "$$", "Categories": ["Sandwiches", "Italian", "Cocktail Bars"], "Website": "http://www.paganosmarketandbar.com"},
{"Bar Name": "Patchwork", "Rating": 4.0, "Review Count": 32, "Price": None, "Categories": ["American (New)", "Bars", "Breakfast & Brunch"], "Website": "https://patchworkphilly.com"},
{"Bar Name": "The Patio @ Thirteen Restaurant", "Rating": None, "Review Count": None, "Price": None, "Categories": None, "Website": "https://www.marriott.com/en-us/hotels/phldt-philadelphia-marriott-downtown/dining"},
{"Bar Name": "Pearl & Mary", "Rating": 4.5, "Review Count": 105, "Price": None, "Categories": ["Bars", "Seafood", "Sandwiches"], "Website": "https://www.pearlandmary.com"},
{"Bar Name": "Prunella", "Rating": 4.5, "Review Count": 150, "Price": "$$", "Categories": ["Italian", "Pizza", "Wine Bars"], "Website": "https://prunellaphl.com"},
{"Bar Name": "Sampan", "Rating": 4.0, "Review Count": 2200, "Price": "$$", "Categories": ["Asian Fusion", "Chinese"], "Website": "http://www.sampanphilly.com"},
{"Bar Name": "Sueno", "Rating": 3.5, "Review Count": 135, "Price": None, "Categories": ["Cocktail Bars", "Mexican"], "Website": "http://suenophilly.com"},
{"Bar Name": "Thanal Indian Tavern", "Rating": 4.5, "Review Count": 295, "Price": "$$", "Categories": ["Indian"], "Website": "https://www.thanalphilly.com"},
{"Bar Name": "Time Restaurant", "Rating": 4.0, "Review Count": 626, "Price": "$$", "Categories": ["American (New)", "Music Venues", "Cocktail Bars"], "Website": "http://www.timerestaurant.net"},
{"Bar Name": "Tir Na Nog Irish Bar & Grill", "Rating": 3.5, "Review Count": 267, "Price": "$$", "Categories": ["Irish Pub", "American (New)"], "Website": "http://www.tirnanogphilly.com"},
{"Bar Name": "Top Tomato Bar & Pizza", "Rating": 3.5, "Review Count": 284, "Price": "$", "Categories": ["Pizza", "Italian", "Bars"], "Website": "https://www.toptomatophilly.com"},
{"Bar Name": "Tradesman's", "Rating": 3.0, "Review Count": 235, "Price": "$$", "Categories": ["Barbeque", "Whiskey Bars", "Beer Bar"], "Website": "https://tradesmansphl.com"},
{"Bar Name": "Uptown Beer Garden", "Rating": 2.5, "Review Count": 32, "Price": None, "Categories": ["Beer Gardens"], "Website": "http://www.bruphilly.com"},
{"Bar Name": "Veda - Modern Indian Bistro", "Rating": 4.0, "Review Count": 542, "Price": "$$", "Categories": ["Indian", "Breakfast & Brunch"], "Website": "http://vedaphilly.com"},
{"Bar Name": "Via Locusta", "Rating": 4.5, "Review Count": 282, "Price": "$$$", "Categories": ["Italian", "Tapas/Small Plates", "Cocktail Bars"], "Website": "https://www.vialocusta.com"},
{"Bar Name": "Vintage Wine Bar & Bistro", "Rating": 4.0, "Review Count": 432, "Price": "$$", "Categories": ["Wine Bars", "French"], "Website": "http://www.vintage-philadelphia.com"},
{"Bar Name": "Walnut Garden - Temporarily Closed", "Rating": 4.0, "Review Count": 1, "Price": None, "Categories": ["Beer Gardens", "Ice Cream & Frozen Yogurt", "Cocktail Bars"], "Website": "https://www.walnutphl.com"},
{"Bar Name": "The Wayward", "Rating": 4.0, "Review Count": 140, "Price": "$$$", "Categories": ["Brasseries", "American (New)", "French"], "Website": "https://www.thewayward.com"},
{"Bar Name": "Wicked Wolf", "Rating": 3.5, "Review Count": 14, "Price": None, "Categories": ["Sports Bars"], "Website": "http://wicketwolfphiladelphia.com"},
{"Bar Name": "Wrap Shack", "Rating": 3.5, "Review Count": 99, "Price": "$$", "Categories": ["Wraps", "Tacos", "American (Traditional)"], "Website": "http://wrapshackpa.com"}
]
print(df.columns)

# Create the DataFrame
yelp_df = pd.DataFrame(data)
print(yelp_df.columns)
print()

print(yelp_df)
print()

combined_df = df.merge(yelp_df, on='Bar Name', how='left')
print(combined_df)
print(combined_df.columns)
print()

# Update the desired columns in df with data from yelp_df
# combined_df['Rating'] = combined_df['Rating_y']
# combined_df['Review Count'] = combined_df['Review Count_y']
# combined_df['Price'] = combined_df['Price_y']
# combined_df['Categories'] = combined_df['Categories_y']

# Drop the unnecessary columns from the combined DataFrame
# combined_df = combined_df.drop(columns=['Rating_y', 'Review Count_y', 'Price_y', 'Categories_y'])

# Save the combined DataFrame to a new CSV file 'Test.csv'
combined_df.to_csv('Test.csv', index=False)

# Display the updated DataFrame
print(combined_df)