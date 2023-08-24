import pandas as pd
import math

# ------------------------------------------------
# This script does = Creates ComparisonResults, uses SipsBarItems to calculate the diff between avg sips price for that item from its general name 
# to the avg price of that item on the regular bar menus I have
# ------------------------------------------------

# Read the CSV file into a DataFrame
df = pd.read_csv("SipsBarItems.csv")

# Remove certain words from Menu Item values
words_to_remove = [" can", " beer", " draft", " bottle"]
df = df[df["Price"] != "Price not available"]
df["Drink"] = (
    df["Drink"]
    .str.lower()  # Convert to lowercase
    .str.replace("|".join(words_to_remove), "", regex=True)  # Remove specified words
    .str.capitalize()  # Capitalize first letter
    .str.strip()  # Clean whitespace
)
df["Drink"] = df["Drink"].str.split(":").str[0].str.strip()
df["Price"] = df["Price"].str.replace("$", "").astype(float)

# Create subdataframes for SipsDeal = Y and SipsDeal = N
sips_deal_y_df = df[df["Sips Deal"] == "Y"]
sips_deal_n_df = df[df["Sips Deal"] == "N"]

keywords = ["tequila", "vodka", "rum", "gin", "whiskey", "bourbon", "pale ale", "stout", "lager", "light", "seltzer", "cider", "pilsner", "double ipa", "amber ale", "sour ale", "golden ale", "porter", "Oktoberfest ", "Hefeweizen ", "Belgian Witbier", "Doppelbock", "Blonde Ale", "California Common", "Cream Ale", "Brown Ale", "Kolsch "]

keyword_prices = {}

def x_round(x):
    return (round(x*4)/4)

def frac_round(x, base=5):
    return (base * round(x/base))

for word in keywords:
  # Add leading space and convert to lowercase
  keyword = " " + word.lower()  
  
  matching = sips_deal_n_df[sips_deal_n_df["Drink"].str.lower().str.contains(keyword)]
  
  if len(matching) > 0:
    avg_price = matching["Price"].mean()
    avg_price = x_round(avg_price)
    
    keyword_prices[word] = avg_price

print(keyword_prices)

# Initialize an empty results dataframe
results_df = pd.DataFrame(
    columns=["Drink", "Sips Price", "Normal Price", "Comparison Result"]
)

# Compare prices for each unique Drink
for menu_item in df["Predicted Item"].unique():
    sips_price = sips_deal_y_df[sips_deal_y_df["Predicted Item"] == menu_item][
        "Price"
    ].mean()
    sips_price = round(sips_price, 2)
    sips_bar = (
        sips_deal_y_df[sips_deal_y_df["Predicted Item"] == menu_item]["Bar"].iloc[0]
        if not pd.isna(sips_price)
        else ""
    )
    normal_price = sips_deal_n_df[sips_deal_n_df["Predicted Item"] == menu_item][
        "Price"
    ].mean()
    sips_price = round(sips_price, 2)
    normal_price = round(normal_price, 2)
    comparison_result = None
    comparison_frac = None
    if not math.isnan(sips_price) and not math.isnan(normal_price):
        comparison_result = normal_price - sips_price
        comparison_result = round(comparison_result, 2)

        comparison_frac = (1 - (sips_price / normal_price)) * 100
        # comparison_frac = round(comparison_frac)
        comparison_frac = frac_round(comparison_frac, base=5)

    results_df = results_df.append(
        {
            "Drink": menu_item,
            "Sips Price": "${:.2f}".format(sips_price),
            "Normal Price": "${:.2f}".format(normal_price),
            "Comparison Result": comparison_result,
            "Comparison Fraction": comparison_frac,
            "Sips Bar": sips_bar,
        },
        ignore_index=True,
    )  # type: ignore

results_df = results_df.sort_values(by="Comparison Result", ascending=False)
results_df["Sips Price"] = results_df["Sips Price"].replace("$nan", "")
results_df["Normal Price"] = results_df["Normal Price"].replace("$nan", "")
# Save the results dataframe to a CSV file
results_df.to_csv("ComparisonResults2.csv", index=False)

print(results_df)
