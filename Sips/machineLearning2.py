import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import random
from sklearn.metrics import accuracy_score

# Load training data from quick.txt 
with open('wines.txt', encoding='utf-8') as f:
    wine_types = f.read().splitlines()
with open('winesTestData.txt', encoding='utf-8') as f:  
    wine_drinks = f.read().splitlines()

# Load cocktail training data    
with open('cocktails.txt', encoding='utf-8') as f:
    cocktail_types = f.read().splitlines() 
with open('cocktailsTestData.txt', encoding='utf-8') as f:
    cocktail_drinks = f.read().splitlines()

# Load cocktail training data    
with open('beers.txt', encoding='utf-8') as f:
    beer_types = f.read().splitlines() 
with open('beersTestData.txt', encoding='utf-8') as f:
    beer_drinks = f.read().splitlines()

# Combine data
train_types = wine_types + cocktail_types + beer_types 
train_drinks = wine_drinks + cocktail_drinks + beer_drinks 

df_train = pd.DataFrame({'DrinkName': train_drinks, 
                         'CommonDrinkType': train_types})

# Load test data
df_test = pd.read_csv('SipsBarItems.csv', encoding='utf-8') 

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

# df_test['Predicted Item'] = predicted_types
finalDF = pd.DataFrame()
# finalDF["Menu Item"] = df_test["Menu Item"]
# finalDF["PredictedType"] = df_test["PredictedType"]
print(finalDF)
df_test.insert(2, 'Predicted Item', predicted_types)
df_test.to_csv("SipsBarItems.csv", index=False, encoding='utf-8')