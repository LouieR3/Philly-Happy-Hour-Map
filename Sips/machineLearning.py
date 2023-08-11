import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

# Sample training data
train_data = {
    'DrinkName': ['Tully Old Fashioned', 'Any Given Sunday Bloody Mary', 'Regular Old Fashioned', 'Bloody Mary'],
    'CommonDrinkType': ['Old Fashioned', 'Bloody Mary', 'Old Fashioned', 'Bloody Mary']
}

df_train = pd.DataFrame(train_data)

# Tokenize and vectorize drink names
vectorizer = TfidfVectorizer()
X = vectorizer.fit_transform(df_train['DrinkName'])

# Train a Logistic Regression model
model = LogisticRegression()
model.fit(X, df_train['CommonDrinkType'])

# Sample test data
test_data = {
    'DrinkName': ['Tully Old Fashioned', 'Gin and Tonic', 'Big Bloody Mary']
}

df_test = pd.DataFrame(test_data)

# Predict common drink types
X_test = vectorizer.transform(df_test['DrinkName'])
predicted_types = model.predict(X_test)

df_test['CommonDrinkType'] = predicted_types

print(df_test)