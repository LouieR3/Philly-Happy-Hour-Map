import pandas as pd

# Read the original quizzo list and combined cleaned data
quizzo_list = pd.read_csv('Quizzo/quizzo_list.csv')
quizzo_combined_cleaned = pd.read_csv('Quizzo/quizzo_combined_cleaned.csv')

# Ensure BUSINESS and NEIGHBORHOOD columns are uppercase for consistent matching
quizzo_list['BUSINESS'] = quizzo_list['BUSINESS'].str.upper()
quizzo_list['CITY'] = quizzo_list['ADDRESS_CITY'].str.upper()
quizzo_combined_cleaned['BUSINESS'] = quizzo_combined_cleaned['BUSINESS'].str.upper()
quizzo_combined_cleaned['NEIGHBORHOOD'] = quizzo_combined_cleaned['NEIGHBORHOOD'].str.upper()

# Filter records with blank Full Address in quizzo_combined_cleaned
missing_address_records = quizzo_combined_cleaned[quizzo_combined_cleaned['Full Address'].isna()]
print(f"Found {len(missing_address_records)} records with missing Full Address.")

# Merge missing records with quizzo_list based on BUSINESS and CITY matching NEIGHBORHOOD
filled_records = missing_address_records.merge(
    quizzo_list[['BUSINESS', 'ADDRESS_CITY', 'ADDRESS_STREET', 'ADDRESS_UNIT', 'ADDRESS_STATE', 'ADDRESS_ZIP', 'Full Address', 'Latitude', 'Longitude']],
    left_on=['BUSINESS', 'NEIGHBORHOOD'],
    right_on=['BUSINESS', 'ADDRESS_CITY'],
    how='left'
)
print(filled_records)

# Use the `_y` version of the columns and remove the suffix
for column in filled_records.columns:
    if column.endswith('_y'):
        new_column_name = column[:-2]  # Remove the `_y` suffix
        filled_records.rename(columns={column: new_column_name}, inplace=True)

# Drop the `_x` columns
columns_to_drop = [column for column in filled_records.columns if column.endswith('_x')]
filled_records.drop(columns=columns_to_drop, inplace=True)

print(filled_records)


# Merge filled_records back into quizzo_combined_cleaned to update missing values
quizzo_combined_cleaned = quizzo_combined_cleaned.merge(
    filled_records[['BUSINESS', 'ADDRESS_STREET', 'ADDRESS_UNIT', 'ADDRESS_STATE', 'ADDRESS_ZIP', 'Full Address', 'Latitude', 'Longitude']],
    on='BUSINESS',
    how='left',
    suffixes=('', '_updated')
)

# Update missing values in quizzo_combined_cleaned with the updated columns
fields_to_update = ['ADDRESS_STREET', 'ADDRESS_UNIT', 'ADDRESS_STATE', 'ADDRESS_ZIP', 'Full Address', 'Latitude', 'Longitude']
for field in fields_to_update:
    updated_field = f"{field}_updated"
    if updated_field in quizzo_combined_cleaned.columns:
        quizzo_combined_cleaned[field] = quizzo_combined_cleaned[field].combine_first(quizzo_combined_cleaned[updated_field])
        quizzo_combined_cleaned.drop(columns=[updated_field], inplace=True)

# Debug: Check if the fields were updated
print(quizzo_combined_cleaned[fields_to_update].head())

# Save the updated DataFrame to a new CSV
quizzo_combined_cleaned.to_csv('Quizzo/quizzo_combined_filled.csv', index=False)

print("Updated data saved to Quizzo/quizzo_combined_filled.csv")