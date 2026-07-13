import pandas as pd
import numpy as np
np.random.seed(0)

# ── TABLE 1: market_prices ──
# Prediction market prices sampled every 5 minutes for 3 markets
markets   = ['DEM_WIN', 'REP_WIN', 'THIRD_PARTY']
times     = pd.date_range('2024-11-05 06:00', periods=72, freq='5min')

price_data = []
for m in markets:
    base = {'DEM_WIN': 0.48, 'REP_WIN': 0.47, 'THIRD_PARTY': 0.05}[m]
    prices_arr = np.clip(
        base + np.cumsum(np.random.normal(0, 0.008, 72)), 0.01, 0.99
    )
    for t, p in zip(times, prices_arr):
        price_data.append({
            'market':  m,
            'time':    t,
            'price':   round(p, 4),
            'volume':  np.random.randint(500, 5000)
        })

market_prices = pd.DataFrame(price_data).sort_values(['market', 'time'])

# ── TABLE 2: state_results ──
# Results coming in from key states at irregular timestamps
state_results = pd.DataFrame({
    'time': pd.to_datetime([
        '2024-11-05 07:23:11',
        '2024-11-05 08:01:45',
        '2024-11-05 08:47:03',
        '2024-11-05 09:15:22',
        '2024-11-05 09:52:40',
        '2024-11-05 10:30:00',
    ]),
    'state':          ['Florida', 'Ohio', 'Pennsylvania', 'Michigan', 'Arizona', 'Nevada'],
    'dem_votes_pct':  [0.48, 0.45, 0.52, 0.53, 0.50, 0.51],
    'called_for':     ['REP_WIN', 'REP_WIN', 'DEM_WIN', 'DEM_WIN', 'DEM_WIN', 'DEM_WIN']
})

print("market_prices shape:", market_prices.shape)
# print(market_prices.head(8))
print(market_prices)
print()
print("state_results:")
print(state_results)

# "Using these two tables, complete the following:"
# Part 1: For each market, compute the 6-observation rolling average price and the cumulative volume traded. 
# Add both as columns to market_prices.

market_prices['rolling_avg_price'] = (
    market_prices
    .groupby('market')['price']
    .transform(lambda x: x.rolling(6, min_periods=1).mean())
)
market_prices['cum_volume'] = market_prices.groupby('market')['volume'].cumsum()
print(market_prices)

# Part 2: For each state result, find the price of each market at the moment just before that result was announced. 
# Return a table showing the state, the time it was called, and the price of all three markets at that moment.
# ── PIVOT market_prices so each market is its own column ──
# Before pivot: 216 rows, one row per (market, time)
# After pivot:  72 rows, one row per time, three price columns

prices_wide = market_prices.pivot_table(
    index='time',
    columns='market',
    values='price'
).reset_index()
# Flatten the column names
prices_wide.columns.name = None
prices_wide = prices_wide.rename(columns={
    'DEM_WIN':     'price_DEM',
    'REP_WIN':     'price_REP',
    'THIRD_PARTY': 'price_THIRD'
})
# ── PART 2 FIXED ──
part2 = pd.merge_asof(
    state_results.sort_values('time'),
    prices_wide.sort_values('time'),
    on='time',
    direction='backward'
)
print("── Part 2: Prices just before each state result ──")
print(part2[['state', 'time', 'called_for', 'price_DEM', 'price_REP', 'price_THIRD']])
print()
# Part 3: Compute the price change for DEM_WIN in the 15 minutes after each state result — 
# i.e., what was the price just before and just after the result, and what was the difference?

# ── PART 3 FIXED ──
# Price just BEFORE each result (backward = most recent row before event)
before = pd.merge_asof(
    state_results.sort_values('time'),
    prices_wide.sort_values('time'),
    on='time',
    direction='backward'
).rename(columns={
    'price_DEM':   'dem_before',
    'price_REP':   'rep_before',
    'price_THIRD': 'third_before'
})

# Price 15 minutes AFTER — shift event times forward then merge_asof backward
after_times = state_results.copy()
after_times['time'] = after_times['time'] + pd.Timedelta('15min')

after = pd.merge_asof(
    after_times.sort_values('time'),
    prices_wide.sort_values('time'),
    on='time',
    direction='backward'
).rename(columns={
    'price_DEM':   'dem_after',
    'price_REP':   'rep_after',
    'price_THIRD': 'third_after'
})

# Combine into one table
part3 = before[['state', 'time', 'called_for', 'dem_before', 'rep_before', 'third_before']].copy()
part3['dem_after']   = after['dem_after'].values
part3['rep_after']   = after['rep_after'].values
part3['third_after'] = after['third_after'].values

# Compute changes
part3['dem_change']   = part3['dem_after']   - part3['dem_before']
part3['rep_change']   = part3['rep_after']   - part3['rep_before']
part3['third_change'] = part3['third_after'] - part3['third_before']

print("── Part 3: Price changes 15min after each state result ──")
print(part3[['state', 'called_for', 'dem_before', 'dem_after', 'dem_change']].to_string())

# Exercise 5 — Resample + merge_asof together:
# Using market_prices, resample each market to 15-minute OHLC bars (open, high, low, close) plus total volume. 
# Then for each state result in state_results, find the 15-minute bar that was in progress just before the result was
#  announced and attach the open and close price of that bar to the state result. 
# Which states were called during a bar where DEM_WIN's close was higher than its open (bullish bar)?
market_prices.set_index('time', inplace=True)
ohlc = (
    market_prices
    .groupby('market')
    .resample('15min')
    .agg(
        open_price  = ('price',  'first'),
        high_price  = ('price',  'max'),
        low_price   = ('price',  'min'),
        close_price = ('price',  'last'),
        total_vol   = ('volume', 'sum')
    )
)

print(state_results)
print("── Part 5: OHLC bars for each market ──")
print(ohlc.head(12))
state_results_with_ohlc = pd.merge_asof(
    state_results.sort_values('time'),
    ohlc.reset_index().sort_values('time'),
    on='time',
    direction='backward'
)
print("── Part 5: State results with OHLC bars ──")
print(state_results_with_ohlc[['state', 'time', 'called_for', 'market', 'open_price', 'close_price']])
print("Bullish bars (DEM_WIN close > open):")
bullish_bars = state_results_with_ohlc[ (state_results_with_ohlc['market'] == 'DEM_WIN') & (state_results_with_ohlc['close_price'] > state_results_with_ohlc['open_price']) ]
print(bullish_bars[['state', 'time', 'called_for', 'open_price', 'close_price']])
print()

# Exercise 6 — Multi-step groupby pipeline:
# Using market_prices, for each market:
# Compute a 6-observation rolling average (you've done this)
# Add a column signal that is 'above' when price is above rolling avg and 'below' when below
# Count how many consecutive rows each market has been in the same signal state — 
# i.e. a "streak" column that resets to 1 each time signal changes
market_prices['rolling_avg'] = market_prices.groupby('market')['price'].transform(lambda x: x.rolling(6, min_periods=1).mean())
market_prices['signal'] = np.where(
    market_prices['price'] > market_prices['rolling_avg'],
    'above',
    'below'
)
market_prices.reset_index(inplace=True)
print(market_prices[['market', 'price', 'rolling_avg', 'signal']].head(25))
# market_prices['streak'] = (
#     market_prices.groupby('market')['signal']
#     .apply(lambda x: (x != x.shift()).cumsum())
# )
print("── Part 6: Market prices with rolling avg, signal, and streak ──")
# print(market_prices[['market', 'time', 'price', 'rolling_avg', 'signal', 'streak']].head(12))
# The streak part is the hard bit. Hint: look up cumsum() on a boolean Series and how it can be used to 
# create group IDs for consecutive runs.

# Exercise 7 — Pivot + groupby combined:
# Starting from scratch with market_prices:

# Pivot to wide format (one column per market)
# Add a column leading_market that shows which market has the highest price at each timestamp
# Add a column dem_rep_spread showing price_DEM - price_REP at each timestamp
# Resample to 30-minute intervals and show how the spread evolved over the day — open spread, close spread, max spread, 
# min spread per window
markets_wide = market_prices.pivot_table(index='time', columns='market', values='price')
print("── Part 7: Market prices pivoted to wide format ──")
print(markets_wide.head(12))
markets_wide['leading_market'] = markets_wide.idxmax(axis=1)
markets_wide['dem_rep_spread'] = markets_wide['DEM_WIN'] - markets_wide['REP_WIN']
spread_resampled = (
    markets_wide[['dem_rep_spread']]
    .resample('30min')['dem_rep_spread']
    .agg(
        open_spread  = 'first',
        close_spread = 'last',
        max_spread   = 'max',
        min_spread   = 'min'
    )
)
print("── Part 7: Spread resampled to 30-minute intervals ──")
print(markets_wide)
print()
print(spread_resampled)

# Exercise 8 — The hardest one, closest to interview style:
# You're given market_prices and a new DataFrame called trades:
trades = pd.DataFrame({
    'time': pd.to_datetime([
        '2024-11-05 06:12:33',
        '2024-11-05 07:45:01',
        '2024-11-05 08:30:15',
        '2024-11-05 09:10:44',
        '2024-11-05 10:05:22',
        '2024-11-05 11:20:09',
    ]),
    'market':    ['DEM_WIN', 'REP_WIN', 'DEM_WIN', 'THIRD_PARTY', 'REP_WIN', 'DEM_WIN'],
    'direction': ['BUY', 'SELL', 'BUY', 'BUY', 'BUY', 'SELL'],
    'quantity':  [500, 300, 800, 200, 600, 400]
})
print("---------")
print("── Part 8: Trades DataFrame ──")
print(trades)

markets   = ['DEM_WIN', 'REP_WIN', 'THIRD_PARTY']
times     = pd.date_range('2024-11-05 06:00', periods=72, freq='5min')

price_data = []
for m in markets:
    base = {'DEM_WIN': 0.48, 'REP_WIN': 0.47, 'THIRD_PARTY': 0.05}[m]
    prices_arr = np.clip(
        base + np.cumsum(np.random.normal(0, 0.008, 72)), 0.01, 0.99
    )
    for t, p in zip(times, prices_arr):
        price_data.append({
            'market':  m,
            'time':    t,
            'price':   round(p, 4),
            'volume':  np.random.randint(500, 5000)
        })

market_prices = pd.DataFrame(price_data).sort_values(['market', 'time'])
print(market_prices.head(12))
# Complete all of the following:


# ── Step 1: entry price ──
entry = pd.merge_asof(
    trades.sort_values('time'),
    market_prices[['time', 'market', 'price']].sort_values('time'),
    on='time',
    by='market',
    direction='backward'
).rename(columns={'price': 'entry_price'})

entry['trade_value'] = entry['quantity'] * entry['entry_price']
print("── Entry prices ──")
print(entry[['time', 'market', 'direction', 'quantity', 'entry_price', 'trade_value']])
print()

# ── Step 2: price 30 min later ──
# Shift time forward, merge_asof backward to find nearest price at that point
entry['time_30'] = entry['time'] + pd.Timedelta('30min')

later = pd.merge_asof(
    entry.sort_values('time_30'),
    market_prices[['time', 'market', 'price']].sort_values('time'),
    left_on='time_30',
    right_on='time',
    by='market',
    direction='backward'
).rename(columns={'price': 'price_30min_later'})

print("── With 30min later price ──")
print(later[['time_x', 'market', 'direction', 'quantity', 
             'entry_price', 'price_30min_later']])
print()

# ── Step 3: PnL ──
# BUY profits when price goes up, SELL profits when price goes down
later['pnl'] = np.where(
    later['direction'] == 'BUY',
    (later['price_30min_later'] - later['entry_price']) * later['quantity'],
    (later['entry_price'] - later['price_30min_later']) * later['quantity']
)

print("── With PnL ──")
print(later[['time_x', 'market', 'direction', 'quantity',
             'entry_price', 'price_30min_later', 'pnl']].round(2))
print()

# ── Step 4: GroupBy — total pnl and volume per market ──
summary = later.groupby('market').agg(
    total_pnl      = ('pnl',      'sum'),
    total_quantity = ('quantity', 'sum'),
    num_trades     = ('pnl',      'count')
).round(2)
print("── PnL summary by market ──")
print(summary)
print()

# ── Step 5: Best and worst trade ──
print("── Best trade ──")
print(later.loc[later['pnl'].idxmax(),
      ['time_x', 'market', 'direction', 'quantity', 'entry_price', 
       'price_30min_later', 'pnl']])
print()
print("── Worst trade ──")
print(later.loc[later['pnl'].idxmin(),
      ['time_x', 'market', 'direction', 'quantity', 'entry_price', 
       'price_30min_later', 'pnl']])
# Compute pnl — if direction is BUY, pnl = (price_30min_later - entry_price) × quantity. If SELL, pnl = (entry_price - price_30min_later) × quantity

# Group the completed trades by market and compute total pnl and total quantity traded per market

# Finally — which single trade had the best pnl? Which had the worst?