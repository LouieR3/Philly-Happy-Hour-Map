import pandas as pd

# Assuming you have the DataFrame 'df' with the 'Deals' column
df = pd.read_csv('Test.csv')

# Replace newlines with newline characters '\n' in the 'Deals' column
# df['Deals'] = df['Deals'].str.replace('\\n', ' ')
for index, row in df.iterrows():
    deals_parts = row['Deals'].split('\n')
    # Loop through the deals parts and apply bold to specific lines
    for deal in deals_parts:
        print(deal.strip())
        print(deal)
        if deal.strip() in ['$7 Cocktails', '$6 Wine', '$5 Beer', 'Half-Priced Appetizers']:
            popup_content = f"<p style='text-align: center; font-weight: bold;'>{deal}</p>"
        else:
            popup_content = f"<p style='text-align: center;'>{deal}</p>"
        print(popup_content)
        print()

# Save the updated DataFrame back to the CSV file
# df.to_csv('Test2.csv', index=False)