import pandas as pd

# Read the CSV file into a DataFrame
df = pd.read_csv("SipsBarItems.csv")

# Remove certain words from Menu Item values
words_to_remove = [" can", " beer", " draft", " bottle"]
df = df[df["Price"] != "Price not available"]
df["Menu Item"] = (
    df["Menu Item"]
    .str.lower()  # Convert to lowercase
    .str.replace("|".join(words_to_remove), "", regex=True)  # Remove specified words
    .str.capitalize()  # Capitalize first letter
    .str.strip()  # Clean whitespace
)
df["Menu Item"] = df["Menu Item"].str.split(":").str[0].str.strip()
df["Price"] = df["Price"].str.replace("$", "").astype(float)

# Create subdataframes for SipsDeal = Y and SipsDeal = N
sips_deal_y_df = df[df["Sips Deal"] == "Y"]
sips_deal_n_df = df[df["Sips Deal"] == "N"]

# Initialize an empty results dataframe
results_df = pd.DataFrame(
    columns=["Menu Item", "Sips Price", "Normal Price", "Comparison Result"]
)

# Compare prices for each unique Menu Item
for menu_item in df["Menu Item"].unique():
    sips_price = sips_deal_y_df[sips_deal_y_df["Menu Item"] == menu_item][
        "Price"
    ].mean()
    sips_bar = (
        sips_deal_y_df[sips_deal_y_df["Menu Item"] == menu_item]["Bar"].iloc[0]
        if not pd.isna(sips_price)
        else ""
    )
    normal_price = sips_deal_n_df[sips_deal_n_df["Menu Item"] == menu_item][
        "Price"
    ].mean()

    comparison_result = None
    if sips_price is not None and normal_price is not None:
        comparison_result = normal_price - sips_price

    results_df = results_df.append(
        {
            "Menu Item": menu_item,
            "Sips Price": sips_price,
            "Normal Price": normal_price,
            "Comparison Result": comparison_result,
            "Sips Bar": sips_bar,
        },
        ignore_index=True,
    )  # type: ignore

results_df = results_df.sort_values(by="Comparison Result", ascending=False)

# Save the results dataframe to a CSV file
results_df.to_csv("ComparisonResults.csv", index=False)

print(results_df)
