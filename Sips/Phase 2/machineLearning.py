import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import random
from sklearn.metrics import accuracy_score
from tabulate import tabulate
from fuzzywuzzy import fuzz
from Levenshtein import distance

# ------------------------------------------------
# This script does = reads SispBarItems and uses machine learning to tell what a drink is from its long name and the general name I gave it
# ------------------------------------------------

def fuzzy_match(str1, str2):
  ratio = fuzz.ratio(str1.lower(), str2.lower())
  dist = distance(str1.lower(), str2.lower())
  return ratio > 70 or dist <= 3

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

df_train = pd.DataFrame({'Drink': train_drinks, 
                         'CommonDrinkType': train_types})

# Load test data
df_test = pd.read_csv('../Csv/SipsBarItems.csv', encoding='utf-8')

df_train['Drink'] = df_train['Drink'].str.lower()
df_test['DrinkTest'] = df_test['Drink'].str.lower()

extra_words = ["can", "draft", "bottle", "house"]
df_train['Drink'] = df_train['Drink'].apply(lambda x: ' '.join([word for word in x.split() if word not in extra_words]))
df_test['DrinkTest'] = df_test['Drink'].apply(lambda x: ' '.join([word for word in x.split() if word not in extra_words]))

# Tokenize and vectorize drink names
vectorizer = TfidfVectorizer()
X_train = vectorizer.fit_transform(df_train['Drink']) 

# Train model 
model = LogisticRegression()
model.fit(X_train, df_train['CommonDrinkType'])

# Vectorize test data
X_test = vectorizer.transform(df_test['DrinkTest'])
df_test = df_test.drop(['DrinkTest'], axis=1)
# Predict types for test data
predicted_types = model.predict(X_test)

# Check for fuzzy match to training labels
fuzzy_matches = []

for i in range(len(predicted_types)):
  if fuzzy_match(df_test['Drink'][i], 
                df_train[df_train['CommonDrinkType'] == predicted_types[i]]['Drink'].values[0]):
    fuzzy_matches.append(True)
  else:
    fuzzy_matches.append(False)

# Mark fuzzy matches    
df_test['Fuzzy Match'] = fuzzy_matches

# Predict probabilities for test data
predicted_probs = model.predict_proba(X_test)

# Get the certainty for the predicted class
certainty = predicted_probs.max(axis=1)  # Max probability along columns

# Add certainty column to the dataframe

newDrinks = []
for pred_type in predicted_types:
    if pred_type not in beer_types and pred_type not in wine_types and pred_type not in cocktail_types:
        newDrinks.append(pred_type)
print(newDrinks)

df_test['Predicted Item'] = predicted_types
# df_test.insert(2, "Predicted Item", predicted_types)
df_test['Certainty'] = certainty
print(df_test)
df_test.to_csv("Test.csv", index=False, encoding='utf-8')
# df_test.to_csv("SipsBarItems.csv", index=False, encoding='utf-8')
# print(tabulate(df_test, headers='keys', tablefmt='pretty')) # type: ignore
