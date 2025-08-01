import pandas as pd

# Read the original quizzo list and combined cleaned data
quizzo_list = pd.read_csv('public/quizzo_list.csv')
quizzo_combined_cleaned = pd.read_csv('Quizzo/quizzo_combined_cleaned.csv')

# Ensure BUSINESS and NEIGHBORHOOD columns are uppercase for consistent matching
quizzo_list['BUSINESS'] = quizzo_list['BUSINESS'].str.upper()
quizzo_list['CITY'] = quizzo_list['ADDRESS_CITY'].str.upper()
quizzo_combined_cleaned['BUSINESS'] = quizzo_combined_cleaned['BUSINESS'].str.upper()
quizzo_combined_cleaned['NEIGHBORHOOD'] = quizzo_combined_cleaned['NEIGHBORHOOD'].str.upper()

# Filter records with blank Full Address in quizzo_combined_cleaned
missing_address_records = quizzo_combined_cleaned[quizzo_combined_cleaned['Full Address'].isna()]

# Merge missing records with quizzo_list based on BUSINESS and CITY matching NEIGHBORHOOD
filled_records = missing_address_records.merge(
    quizzo_list[['BUSINESS', 'ADDRESS_CITY', 'ADDRESS_STREET', 'ADDRESS_UNIT', 'ADDRESS_STATE', 'ADDRESS_ZIP', 'Full Address', 'Latitude', 'Longitude']],
    left_on=['BUSINESS', 'NEIGHBORHOOD'],
    right_on=['BUSINESS', 'ADDRESS_CITY'],
    how='left'
)

# Update the fields in quizzo_combined_cleaned with the filled records
fields_to_update = ['ADDRESS_STREET', 'ADDRESS_UNIT', 'ADDRESS_STATE', 'ADDRESS_ZIP', 'Full Address', 'Latitude', 'Longitude']
for field in fields_to_update:
    quizzo_combined_cleaned[field] = quizzo_combined_cleaned[field].combine_first(filled_records[field])

# Save the updated DataFrame to a new CSV
quizzo_combined_cleaned.to_csv('Quizzo/quizzo_combined_filled.csv', index=False)

print("Updated data saved to Quizzo/quizzo_combined_filled.csv")