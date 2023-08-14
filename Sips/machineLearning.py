import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

# Sample training data
# train_data = {
#     "DrinkName": [
#         "Tully Old Fashioned",
#         "Any Given Sunday Bloody Mary",
#         "Regular Old Fashioned",
#         "Bloody Mary",
#     ],
#     "CommonDrinkType": ["Old Fashioned", "Bloody Mary", "Old Fashioned", "Bloody Mary"],
# }
train_data = {
    "DrinkName": [
        "House Red",
        "House White",
        "Philly Style Cabernet",
        "House Merlot",
        "Eola Hills Pinot Noir",
        "Vin Blanc Chardonnay",
        "Joel Gott Sauvignon Blanc",
        "Riesling",
        "Syrah/Shiraz",
        "Vino Rosso",
        "Vino Bianco",
        "White Zinfandel",
        "Prosecco",
        "Dona Paula Los Cardos Malbec",
        "Tempranillo",
        "Sangiovese",
        "Montepulciano",
        "Cantina Pinot Grigio",
        "Sutter Home Rose",
        "Chenin Blanc",
        "Gewürztraminer",
        "House Chianti",
    ],
    "CommonDrinkType": [
        "Red",
        "White",
        "Cabernet Sauvignon",
        "Merlot",
        "Pinot Noir",
        "Chardonnay",
        "Sauvignon Blanc",
        "Riesling",
        "Syrah/Shiraz",
        "Vino Rosso",
        "Vino Bianco",
        "Zinfandel",
        "Prosecco",
        "Malbec",
        "Tempranillo",
        "Sangiovese",
        "Montepulciano",
        "Pinot Grigio",
        "Rosé",
        "Chenin Blanc",
        "Gewürztraminer",
        "Chianti",
    ],
}

df_train = pd.DataFrame(train_data)

# Tokenize and vectorize drink names
vectorizer = TfidfVectorizer()
X = vectorizer.fit_transform(df_train["DrinkName"])

# Train a Logistic Regression model
model = LogisticRegression()
model.fit(X, df_train["CommonDrinkType"])

# Sample test data
# test_data = {"DrinkName": ["Tully Old Fashioned", "Gin and Tonic", "Big Bloody Mary"]}

test_data = {
    "DrinkName": [
        "Pinot Grigio Bottle",
        "Collier Creek Cabernet",
        "Cantina Pinot Grigio",
        "Oak Grove Pinot Noir",
        "Sauvignon Blanc",
        "Riesling",
        "Prosecco",
        "House Malbec",
        "Zinfandel",
        "Dona Paula Los Cardos Malbec",
        "Sycamore Lane Chardonnay 6oz glass",
        "C'est La Vie Rose",
        "Echo Bay Sauvignon Blanc",
        "Proverb Pinot Grigio",
        "Sutter Home Rose",
        "Pull Cabernet",
        "House Merlot",
        "House Chianti",
    ]
}

df_test = pd.DataFrame(test_data)

# Predict common drink types
X_test = vectorizer.transform(df_test["DrinkName"])
predicted_types = model.predict(X_test)

df_test["CommonDrinkType"] = predicted_types

print(df_test)
