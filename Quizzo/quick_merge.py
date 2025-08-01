import pandas as pd


# Read the original and new quizzo CSVs
quizzo_original = pd.read_csv('public/quizzo_list.csv')
quizzo_new = pd.read_csv('Quizzo/quizzo_extra_cleaned.csv')

# Ensure BUSINESS and NEIGHBORHOOD columns are uppercase for consistent merging
quizzo_original['BUSINESS'] = quizzo_original['BUSINESS'].str.upper()
quizzo_original['NEIGHBORHOOD'] = quizzo_original['NEIGHBORHOOD'].str.upper()
quizzo_new['BUSINESS'] = quizzo_new['BUSINESS'].str.upper()
quizzo_new['NEIGHBORHOOD'] = quizzo_new['NEIGHBORHOOD'].str.upper()

# Merge the two DataFrames based on BUSINESS and NEIGHBORHOOD
merged_data = quizzo_original.merge(
    quizzo_new[['BUSINESS', 'NEIGHBORHOOD', 'TIME', 'WEEKDAY', 'PRIZE_1_TYPE', 'PRIZE_1_AMOUNT',
                'PRIZE_2_TYPE', 'PRIZE_2_AMOUNT', 'PRIZE_3_TYPE', 'PRIZE_3_AMOUNT', 'HOST', 'EVENT_TYPE']],
    on=['BUSINESS', 'NEIGHBORHOOD'],
    how='outer',
    suffixes=('_original', '_new')
)

# Consolidate columns by combining original and new values
columns_to_update = ['TIME', 'WEEKDAY', 'PRIZE_1_TYPE', 'PRIZE_1_AMOUNT', 'PRIZE_2_TYPE',
                     'PRIZE_2_AMOUNT', 'PRIZE_3_TYPE', 'PRIZE_3_AMOUNT', 'HOST', 'EVENT_TYPE']
for column in columns_to_update:
    merged_data[column] = merged_data[column + '_new'].combine_first(merged_data[column + '_original'])

# Drop the temporary columns with suffixes
merged_data.drop(columns=[col + '_original' for col in columns_to_update], inplace=True)
merged_data.drop(columns=[col + '_new' for col in columns_to_update], inplace=True)

# Drop duplicates based on BUSINESS, NEIGHBORHOOD, WEEKDAY, and TIME, keeping the last occurrence
merged_data = merged_data.drop_duplicates(subset=['BUSINESS', 'NEIGHBORHOOD', 'WEEKDAY'], keep='last')

# Print all records with duplicates for BUSINESS, sorted by BUSINESS
business_duplicates = merged_data[merged_data.duplicated(subset=['BUSINESS'], keep=False)]
business_duplicates = business_duplicates.sort_values(by=['BUSINESS'])

print("Records with duplicate BUSINESS (sorted by BUSINESS):")
print(business_duplicates)
# Sort merged_data by BUSINESS
merged_data = merged_data.sort_values(by=['BUSINESS'])

# Handle duplicates where NEIGHBORHOOD matches CITY
def resolve_city_duplicates(df):
    duplicates = df[df.duplicated(subset=['BUSINESS'], keep=False)]
    resolved_duplicates = []

    for business in duplicates['BUSINESS'].unique():
        subset = duplicates[duplicates['BUSINESS'] == business]
        if len(subset) > 1:
            # Check if NEIGHBORHOOD matches CITY and prioritize the record with CITY populated
            city_match = subset[subset['NEIGHBORHOOD'] == subset['ADDRESS_CITY']]
            if not city_match.empty:
                resolved_duplicates.append(city_match.iloc[0])
            else:
                resolved_duplicates.append(subset.iloc[0])  # Default to the first record if no match
        else:
            resolved_duplicates.append(subset.iloc[0])

    # Convert resolved duplicates back to a DataFrame
    resolved_df = pd.DataFrame(resolved_duplicates)
    return resolved_df

# Separate duplicates and non-duplicates
duplicates = merged_data[merged_data.duplicated(subset=['BUSINESS'], keep=False)]
non_duplicates = merged_data[~merged_data.duplicated(subset=['BUSINESS'], keep=False)]

# Resolve duplicates and combine with non-duplicates
resolved_duplicates = resolve_city_duplicates(duplicates)
final_data = pd.concat([non_duplicates, resolved_duplicates], ignore_index=True)

# Save the final combined DataFrame to a new CSV
final_data.to_csv('Quizzo/quizzo_combined_cleaned.csv', index=False)

print("Cleaned combined data saved to Quizzo/quizzo_combined_cleaned.csv")