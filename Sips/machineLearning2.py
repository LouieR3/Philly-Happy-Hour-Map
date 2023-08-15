import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import random

# Load training data from quick.txt 
with open('wines.txt') as f:
    wine_types = f.read().splitlines()
with open('winesTestData.txt') as f:  
    wine_drinks = f.read().splitlines()

# Load cocktail training data    
with open('cocktails.txt') as f:
    cocktail_types = f.read().splitlines() 
with open('cocktailsTestData.txt') as f:
    cocktail_drinks = f.read().splitlines()

# Combine data
train_types = wine_types + cocktail_types 
train_drinks = wine_drinks + cocktail_drinks

df_train = pd.DataFrame({'DrinkName': train_drinks, 
                         'CommonDrinkType': train_types})

# Load test data
df_test = pd.read_csv('SipsBarItems.csv') 

# Tokenize and vectorize drink names
vectorizer = TfidfVectorizer()
X_train = vectorizer.fit_transform(df_train['DrinkName']) 

# Train model 
model = LogisticRegression()
model.fit(X_train, df_train['CommonDrinkType'])

# Vectorize test data
X_test = vectorizer.transform(df_test['Menu Item'])

# Predict types for test data
predicted_types = model.predict(X_test)
df_test['PredictedType'] = predicted_types
finalDF = pd.DataFrame()
finalDF["Menu Item"] = df_test["Menu Item"]
finalDF["PredictedType"] = df_test["PredictedType"]
print(finalDF)
finalDF.to_csv("Test.csv", index=False)