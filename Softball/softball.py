import pandas as pd

# Load the Excel file
df = pd.read_excel("Softball/Pennoni Softball.xlsx")

# Remove unnecessary columns (BB, SO) since your league doesn't use them
df = df.drop(columns=["BB", "SO"], errors='ignore')

# Ensure column names have no trailing/leading whitespace
df.columns = df.columns.str.strip()

# Calculate Total Bases (TB)
df["TB"] = df["1B"] + 2 * df["2B"] + 3 * df["3B"] + 4 * df["HR"]

# Calculate Runs Created (RC)
df["RC"] = df["H"] * (df["TB"] / df["AB"])

# Filter players with at least 3 ABs
MINIMUM_NUMBER_ABS = 6

eligible_replacement = df[df["AB"] >= MINIMUM_NUMBER_ABS].copy()

# Sort by AVG ascending to find the 5 worst hitters
replacement_pool = eligible_replacement.nsmallest(5, "AVG")

# Estimate replacement level: avg(AVG) * avg(TB) / avg(AB) => runs per AB
replacement_avg = replacement_pool["AVG"].mean()
replacement_tb_per_ab = replacement_pool["TB"].sum() / replacement_pool["AB"].sum()
replacement_rc_per_ab = replacement_avg * replacement_tb_per_ab

# Add Replacement RC for each player
df["Replacement_RC"] = df["AB"] * replacement_rc_per_ab

# Calculate WAR = (RC - Replacement_RC) / 15
df["WAR"] = (df["RC"] - df["Replacement_RC"]) / 12

# Optional: Round relevant columns
df["TB"] = df["TB"].round(1)
df["RC"] = df["RC"].round(2)
df["WAR"] = df["WAR"].round(2)

# Preview final dataframe
print(df[["Players", "AB", "H", "TB", "RC", "WAR"]])

# df.to_csv('Softball/Pennoni Softball.csv', index=False)