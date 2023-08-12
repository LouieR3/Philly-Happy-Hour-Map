import requests

url = "https://www.thecocktaildb.com/api/json/v1/1/popular.php"
response = requests.get(url)
data = response.json()
print(data)
if "drinks" in data:
    popular_cocktails = [drink["strDrink"] for drink in data["drinks"]]
    print(popular_cocktails)
else:
    print("No data available.")
