import json
import pandas as pd

with open('output.json') as f:
  data = json.load(f)

# Extract "displayText" and "isActive" for all elements with the specified key pattern
elements_to_search = [key for key in data.keys() if key.startswith("$ROOT_QUERY.business({\"encid\":\"3eJMsl41qwhcYlvoTF1ElQ\"}).")]

# Find business properties without specifying "encid"
business_properties = {}
prefix_to_search = "$ROOT_QUERY.business.organizedProperties({\"clientPlatform\":\"WWW\"}).0.properties"
for key, value in data.items():
    if isinstance(value, dict) and "displayText" in value:
        # Store in business_properties
        display_text = value["displayText"]
        is_active = value["isActive"]
        business_properties[display_text] = is_active

# Print the modified business_properties
print("Modified Business Properties:")
for key, value in business_properties.items():
    print(key, ":", value)


neighborhoods_json = None
for key, value in data.items():
    if isinstance(value, dict) and "neighborhoods" in value:
        neighborhoods_json = value["neighborhoods"].get("json", [])
        break

# Print the extracted neighborhoods
print("Neighborhoods:", neighborhoods_json)

rating = None
for key, value in data.items():
    if isinstance(value, dict) and "rating" in value:
        rating = value["rating"]
        break

# Print the extracted neighborhoods
print("Rating:", rating)

hours_properties = {}
for key, value in data.items():
    if isinstance(value, dict) and "regularHours" in value and "dayOfWeekShort" in value:
        Hours = value["regularHours"].get("json", [])[0]
        day = value["dayOfWeekShort"]
        hours_properties[day] = Hours
print("Modified Hours Properties:")
for key, value in business_properties.items():
    print(key, ":", value)


df_data = {
    "Name": [business_properties.get("Name", "")],
    **business_properties,
    "Neighborhoods": [neighborhoods_json],
    "Rating": [rating],
    **hours_properties
}

df = pd.DataFrame(df_data)

# Print the DataFrame
print(df)
