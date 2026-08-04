import pandas as pd
import numpy as np

np.random.seed(42)

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
# print(df)
# print()

# ════════════════════════════════════════════════════════════════
# GROUPBY — PIECE BY PIECE
# Mental model: SPLIT into buckets → APPLY function → COMBINE results
# ════════════════════════════════════════════════════════════════

# ── STEP 0: What does groupby actually create? ──
g = df.groupby('symbol')
print("Groups:", list(g.groups.keys()))
# {'CHIEFS_WIN': [indices...], 'EAGLES_WIN': [...], 'OVER_45': [...]}
# It's just an instruction — nothing computed yet until you call agg/apply/etc

# Peek inside one bucket:
print(g.get_group('EAGLES_WIN').head())
print()

# ── STEP 1: Single column, single function ──
# "What is the average price for each symbol across ALL rows?"
result = df.groupby('symbol')['price'].mean()
print("── STEP 1: mean per symbol ──")
print(result)
# CHIEFS_WIN    0.521
# EAGLES_WIN    0.448
# OVER_45       0.379
# One row per symbol. The 20 rows per symbol collapsed to 1.
print()

# ── STEP 2: Single column, multiple functions ──
result = df.groupby('symbol')['price'].agg(['mean', 'std', 'min', 'max', 'last'])
print("── STEP 2: agg per symbol ──")
print(result)
# Still one row per symbol, but now 5 columns instead of 1
print()

# ── STEP 3: Multi-column groupby ──
# "Total volume per symbol per day" — two-level bucket
result = df.groupby(['symbol', 'date'])['volume'].sum()
print("── STEP 3: volume per symbol per day ──")
print(result)
# Index is now (symbol, date) pairs — 15 rows (3 symbols × 5 days)
# Each row = total volume for that symbol on that day
print()

# Unstack to see it as a table (symbols as rows, dates as columns)
print("── STEP 4: Unstack to see it as a table ──")
print(result.unstack())
print()

# ════════════════════════════════════════════════════════════════
# TRANSFORM vs AGG — the most important distinction
# AGG:       N rows → 1 row per group (reduces)
# TRANSFORM: N rows → N rows (same shape, value replaced)
# ════════════════════════════════════════════════════════════════

# ── AGG: collapses rows ──
agg_result = df.groupby('symbol')['price'].mean()
print("AGG shape:", agg_result.shape)   # (3,) — one per symbol
print(agg_result)
print()

# ── TRANSFORM: keeps all rows, fills in the group value ──
df['symbol_mean_price'] = df.groupby('symbol')['price'].transform('mean')
print("TRANSFORM shape:", df['symbol_mean_price'].shape)  # (60,) — same as df
print(df[['symbol', 'price', 'symbol_mean_price']].head(12))
# Every EAGLES_WIN row gets 0.448 in symbol_mean_price
# Every CHIEFS_WIN row gets 0.521
# This lets you do row-level comparisons against the group average:
print()

df['vs_mean']   = df['price'] - df['symbol_mean_price']
df['normalized'] = df['vs_mean'] / df.groupby('symbol')['price'].transform('std')
# normalized > 0: this price tick is above average for this symbol
# normalized < 0: below average
print(df[['symbol', 'date', 'price', 'symbol_mean_price', 'vs_mean', 'normalized']].head(12))
print()

# ── RANK within group ──
# "For each date, rank the symbols by volume — who traded most?"
df['vol_rank'] = df.groupby('date')['volume'].rank(ascending=False)
# rank=1 means highest volume on that date
print(df[['date', 'symbol', 'volume', 'vol_rank']].sort_values(['date', 'vol_rank']).head(12))
print()

# ════════════════════════════════════════════════════════════════
# APPLY with custom function
# Use when built-in agg functions aren't enough
# ════════════════════════════════════════════════════════════════

def top_n(group, n=2):
    # group is a DataFrame containing just one symbol's rows
    # return the n rows with highest volume
    return group.nlargest(n, 'volume')

result = df.groupby('symbol').apply(top_n, n=2)
print("── top 2 volume rows per symbol ──")
print(result[['symbol', 'date', 'price', 'volume']])
# 6 rows total (2 per symbol) — the peak volume moments for each market
print()

# ════════════════════════════════════════════════════════════════
# CUMULATIVE OPERATIONS within groups
# "Running" metrics that update row by row, resetting per group
# ════════════════════════════════════════════════════════════════

df = df.sort_values(['symbol', 'time']).reset_index(drop=True)

df['cumvol']      = df.groupby('symbol')['volume'].cumsum()
df['running_max'] = df.groupby('symbol')['price'].cummax()
df['running_min'] = df.groupby('symbol')['price'].cummin()

print("── cumulative volume + running price range ──")
print(df[['symbol', 'time', 'price', 'volume', 'cumvol', 'running_max', 'running_min']].head(16))
# Watch cumvol reset to small numbers each time symbol changes
# running_max only ever goes up — it's the highest price seen SO FAR
print()