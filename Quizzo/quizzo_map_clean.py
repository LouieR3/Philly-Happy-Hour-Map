import pandas as pd

# Read the transformed quizzo_extra CSV
quizzo_extra = pd.read_csv('Quizzo/quizzo_extra_transformed.csv')
# quizzo_extra = pd.read_csv('Quizzo/quizzo_extra_cleaned.csv')

# Split PRIZE_1_AMOUNT into PRIZE_1_AMOUNT, PRIZE_2_AMOUNT, and PRIZE_3_AMOUNT
quizzo_extra[['PRIZE_1_AMOUNT', 'PRIZE_2_AMOUNT', 'PRIZE_3_AMOUNT']] = quizzo_extra['PRIZE_1_AMOUNT'].str.split(',', expand=True).iloc[:, :3]

# Clean WEEKDAY column by removing anything after "DAY"
quizzo_extra['WEEKDAY'] = quizzo_extra['WEEKDAY'].str.extract(r'(\bDAY\b.*)')[0].str.strip()

# Replace 'X' in EVENT_TYPE with an empty string
quizzo_extra['EVENT_TYPE'] = quizzo_extra['EVENT_TYPE'].replace('X', '')

# Read quizzo_list and master_list
quizzo_list = pd.read_csv('public/quizzo_list.csv')
master_list = pd.read_csv('MasterTable.csv')

# Ensure BUSINESS and NEIGHBORHOOD columns are uppercase for merging
quizzo_extra['BUSINESS'] = quizzo_extra['BUSINESS'].str.upper()
quizzo_extra['NEIGHBORHOOD'] = quizzo_extra['NEIGHBORHOOD'].str.upper()
quizzo_list['BUSINESS'] = quizzo_list['BUSINESS'].str.upper()
quizzo_list['NEIGHBORHOOD'] = quizzo_list['NEIGHBORHOOD'].str.upper()
master_list['Name'] = master_list['Name'].str.upper()

# Merge missing Full Address and Lat/Long from quizzo_list
def fuzzy_merge(df1, df2, key1, key2, neighborhood_key, columns_to_merge):
    merged_data = []
    for _, row in df1.iterrows():
        business = row[key1]
        neighborhood = row[neighborhood_key]
        match = df2[
            (df2[key2].str.contains(business, na=False)) & (df2[neighborhood_key] == neighborhood)
        ]
        if not match.empty:
            merged_data.append(match.iloc[0][columns_to_merge].to_dict())
        else:
            merged_data.append({col: None for col in columns_to_merge})
    return pd.DataFrame(merged_data)

# First merge from quizzo_list
quizzo_list_columns = ['Full Address', 'Latitude', 'Longitude']
quizzo_list_merged = fuzzy_merge(
    quizzo_extra, quizzo_list, 'BUSINESS', 'BUSINESS', 'NEIGHBORHOOD', quizzo_list_columns
)
quizzo_extra[quizzo_list_columns] = quizzo_extra[quizzo_list_columns].combine_first(quizzo_list_merged)

# Then merge from master_list
master_list_columns = ['Address', 'Latitude', 'Longitude']
master_list_merged = fuzzy_merge(
    quizzo_extra, master_list, 'BUSINESS', 'Name', 'NEIGHBORHOOD', master_list_columns
)
quizzo_extra['Full Address'] = quizzo_extra['Full Address'].combine_first(master_list_merged['Address'])
quizzo_extra['Latitude'] = quizzo_extra['Latitude'].combine_first(master_list_merged['Latitude'])
quizzo_extra['Longitude'] = quizzo_extra['Longitude'].combine_first(master_list_merged['Longitude'])

# Drop unnecessary columns from merging
quizzo_extra.drop(columns=['Address'], inplace=True)

# Save the cleaned data back to a CSV
quizzo_extra.to_csv('Quizzo/quizzo_extra_cleaned.csv', index=False)

print("Cleaned data saved to Quizzo/quizzo_extra_cleaned.csv")
