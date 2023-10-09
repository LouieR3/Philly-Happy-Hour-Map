import json

# Load the JSON object from the "output.json" file
with open("output.json", "r") as json_file:
    json_object = json.load(json_file)
# with open("output-talulas-garden-philadelphia.json", "r") as json_file:
#     json_object = json.load(json_file)

business_properties = {}
neighborhoods_json = []
rating = None
website = None
hours_properties = {}

# Parse the JSON object once
for key, value in json_object.items():
    if isinstance(value, dict):
        if "displayText" in value:
            display_text = value["displayText"]
            is_active = value["isActive"]
            if "&amp;" in display_text:
                display_text = display_text.replace("&amp;", "and")
            if "Not Good" in display_text:
                display_text = display_text.replace("Not Good", "Good")
                is_active = not is_active
            if "No " in display_text:
                display_text = display_text.replace("No ", "")
                is_active = not is_active
            if "Best nights on" in display_text:
                parts = display_text.split("Best nights on ")[1].split(',')
                for part in parts:
                    new_display_text = "Best nights on " + part.strip()
                    business_properties[new_display_text] = is_active
            else:
                display_texts = [text.strip() for text in display_text.split(',')]
                business_properties.update({text: is_active for text in display_texts})

        if "neighborhoods" in value:
            neighborhoods_json = value["neighborhoods"].get("json", neighborhoods_json)

        if "rating" in value and isinstance(value["rating"], float):
            rating = value["rating"]

        if "displayUrl" in value and value["displayUrl"] is not None:
            website = value["displayUrl"].replace("&#x2F;", "/")

        if "regularHours" in value and "dayOfWeekShort" in value:
            Hours = value["regularHours"].get("json", [])[0]
            day = value["dayOfWeekShort"]
            if day == "Mon":
                day += "day"
            elif day == "Tue":
                day += "sday"
            elif day == "Wed":
                day += "nesday"
            elif day == "Thu":
                day += "rsday"
            elif day == "Fri":
                day += "day"
            elif day == "Sat":
                day += "urday"
            elif day == "Sun":
                day += "day"
            hours_properties[day] = Hours

restaurant_name = "a kitchen"
df_data = {
    "Name": restaurant_name,
    "Neighborhoods": neighborhoods_json,
    "Yelp Rating": rating,
    "Website": website,
}
for key, value in df_data.items():
    print(f"{key}: {value}")

def find_first_rating(dictionary):
    for key, value in dictionary.items():
        if isinstance(value, dict):
            # If the value is a dictionary, recursively search within it
            result = find_first_rating(value)
            if result is not None:
                return result
        if key == "rating":
            # If the key is "rating," return the value
            return value
    return None  # Return None if "rating" is not found

first_rating = find_first_rating(json_object)
print("First Rating:", first_rating)

# Key to search for
search_key = "externalResources.website"

# Function to search for "BusinessWebsite" and get the URL
def find_business_website(json_obj):
    if isinstance(json_obj, dict):
        if "__typename" in json_obj and json_obj["__typename"] == "BusinessWebsite":
            return json_obj.get("url")
        for key, value in json_obj.items():
            result = find_business_website(value)
            if result:
                return result
    elif isinstance(json_obj, list):
        for item in json_obj:
            result = find_business_website(item)
            if result:
                return result

# Find the URL with "__typename" as "BusinessWebsite"
business_website_url = find_business_website(json_object)
if business_website_url:
    business_website_url = business_website_url.replace("&#x2F;", "/")
    print(business_website_url)
else:
    print("Business Website not found.")