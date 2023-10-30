import pandas as pd
import numpy as np

pay_types = ["Accepts Credit Cards","Accepts Android Pay","Accepts Apple Pay","Accepts Cryptocurrency"]

df = pd.DataFrame({
    'Accepts Credit Cards': [True, False, True], 
    'Accepts Android Pay': [False, True, False],
    'Accepts Apple Pay': [True, False, None],
    'Accepts Cryptocurrency': [None, True, False]  
})

# Fill NAs
df[pay_types] = df[pay_types].fillna(False)

# Create Payment column
df['Payment'] = df[pay_types].apply(lambda x: ', '.join(x.index[x]).replace('Accepts ',''), axis=1)

# Drop original columns 
df = df.drop(columns=pay_types)

print(df)