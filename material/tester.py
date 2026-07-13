import pandas as pd
import numpy as np

# ── BUILD TEST DATA ──────────────────────────────────────────────
# 3 prediction market symbols, 5 dates, multiple price/volume rows per day

symbols = ['EAGLES_WIN', 'CHIEFS_WIN', 'OVER_45']
dates   = pd.date_range('2024-01-15', periods=5, freq='D')

rows = []
for symbol in symbols:
    base_price = {'EAGLES_WIN': 0.45, 'CHIEFS_WIN': 0.52, 'OVER_45': 0.38}[symbol]
    for date in dates:
        # 4 price ticks per symbol per day
        for minute in [0, 15, 30, 45]:
            rows.append({
                'symbol': symbol,
                'date':   date.date(),
                'time':   pd.Timestamp(date) + pd.Timedelta(hours=9, minutes=minute),
                'price':  round(np.clip(base_price + np.random.normal(0, 0.04), 0.01, 0.99), 4),
                'volume': int(np.random.randint(100, 2000))
            })

df = pd.DataFrame(rows)
df['date'] = pd.to_datetime(df['date'])
print("Shape:", df.shape)
print(df.head(12))
print()

# Exercise 1 — GroupBy + Transform:
# Using the df above, add a column price_percentile that shows, for each symbol, 
# what percentile the current price is relative to all prices for that symbol. 
# (Hint: transform with a lambda and pd.Series.rank(pct=True))

df['price_percentile'] = df.groupby('symbol')['price'].transform(lambda x: x.rank(pct=True)) * 100

# Exercise 2 — Resample:
# Resample the data to daily frequency per symbol and produce a proper OHLC table (open, high, low, close price) 
# plus total daily volume. Then add a column showing the daily price range (high minus low).
rs = df
rs.set_index('time', inplace=True)

rs = df.groupby('symbol')['price'].resample('D').agg(open_price='first', close_price='last', high='max', low='min')

rs = (
    df.set_index('time')
    .groupby('symbol')
    .resample('D')
    .agg(
        open_price  = ('price',  'first'),
        close_price = ('price',  'last'),
        high        = ('price',  'max'),
        low         = ('price',  'min'),
        total_vol   = ('volume', 'sum')   # ← you missed this
    )
)
rs['daily_range'] = rs['high'] - rs['low']
rs['daily_price_range'] = rs['high'] - rs['low']
print(rs)

# Exercise 3 — merge_asof:
# Create a second DataFrame called news with 4 rows: a timestamp and a headline string. Make the timestamps fall between your price ticks 
# (not matching exactly). Use merge_asof to join each price row to the most recent news headline that preceded it. 
# Then add tolerance so that any price row more than 20 minutes after the last headline gets NaN instead.

news = pd.DataFrame({
    'time': pd.to_datetime([
        '2024-01-15 09:11', 
        '2024-01-15 09:32', 
        '2024-01-16 9:03', 
        '2024-01-17 9:38'
    ]),
    'headline': [
        'Eagles sign new quarterback',
        'Chiefs star player injured',
        'Weather delays game start',
        'Eagles score first touchdown'
    ]
})

result = pd.merge_asof(df.sort_values('time'), news.sort_values('time'), on='time', tolerance=pd.Timedelta('20min'), direction='backward')
print(result)
print()
print()
# Exercise 4 — Combined:
# For each symbol, compute a 3-observation rolling average price. Then create a signals DataFrame with 6 rows — two signal timestamps 
# per symbol where you want to know what the rolling average was at that moment. Use merge_asof grouped by symbol to join the rolling 
# average onto the signals table.

df['rolling_avg_price'] = df.groupby('symbol')['price'].transform(lambda x: x.rolling(3, min_periods=1).mean())

signals = pd.DataFrame({
    'time': pd.to_datetime([
        '2024-01-15 09:30', 
        '2024-01-15 09:45', 
        '2024-01-16 09:15', 
        '2024-01-16 09:30', 
        '2024-01-17 09:00', 
        '2024-01-17 09:45'
    ]),
    'symbol': [
        'EAGLES_WIN', 
        'EAGLES_WIN', 
        'CHIEFS_WIN', 
        'CHIEFS_WIN', 
        'OVER_45', 
        'OVER_45'
    ]
})
df.reset_index(inplace=True)
result = pd.merge_asof(
    signals.sort_values('time'),
    df[['time', 'symbol', 'rolling_avg_price']].sort_values('time'),
    on='time',
    by='symbol',
    direction='backward'
)
print(result)