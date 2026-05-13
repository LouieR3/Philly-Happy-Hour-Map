import pandas as pd
import numpy as np

# Path to your Excel file
file_path = r"C:\Users\louie.rodriguez\OneDrive - Pennoni\Desktop\repo\DeltekMapScirpts\Pennoni_Softball.xlsx"

# Load all sheets except the first one
all_sheets = pd.read_excel(file_path, sheet_name=None)  # Returns dict of {sheet_name: df}
sheet_names = list(all_sheets.keys())[1:]  # Skip the first sheet

# Initialize master DataFrame
master_df = pd.DataFrame()

# Combine all game sheets into master
for sheet_name in sheet_names:
    game_df = all_sheets[sheet_name]
    game_df.columns = game_df.columns.str.strip()  # Clean column names

    # Keep only relevant columns if they exist
    relevant_cols = ["Players","AB","H","1B","2B","3B","HR","RBI","R","BB","SO"]
    game_df = game_df[[col for col in relevant_cols if col in game_df.columns]]

    # Add a 'Games' column to count games played
    game_df["Games"] = 1

    # Append to master, grouping by player later
    master_df = pd.concat([master_df, game_df], ignore_index=True)

# Aggregate stats for each player
agg_cols = ["AB","H","1B","2B","3B","HR","RBI","R","BB","SO","Games"]
master_stats = master_df.groupby("Players", as_index=False)[agg_cols].sum()

# Calculate derived stats safely
master_stats["TB"] = master_stats["1B"] + 2 * master_stats["2B"] + 3 * master_stats["3B"] + 4 * master_stats["HR"]

# Avoid division by zero
master_stats["AVG"] = (master_stats["H"] / master_stats["AB"].replace(0, np.nan)).fillna(0)
master_stats["SLG %"] = (master_stats["TB"] / master_stats["AB"].replace(0, np.nan)).fillna(0)
master_stats["OBP %"] = ((master_stats["H"] + master_stats["BB"]) / 
                         (master_stats["AB"] + master_stats["BB"]).replace(0, np.nan)).fillna(0)
master_stats["OPS %"] = master_stats["SLG %"] + master_stats["OBP %"]
master_stats["RC"] = (master_stats["H"] * (master_stats["TB"] / master_stats["AB"].replace(0, np.nan))).fillna(0)

# Calculate Replacement RC and WAR
MINIMUM_NUMBER_ABS = 6
eligible_replacement = master_stats[master_stats["AB"] >= MINIMUM_NUMBER_ABS].copy()
replacement_pool = eligible_replacement.nsmallest(5, "AVG")
replacement_avg = replacement_pool["AVG"].mean()
replacement_tb_per_ab = replacement_pool["TB"].sum() / replacement_pool["AB"].sum()
replacement_rc_per_ab = replacement_avg * replacement_tb_per_ab
master_stats["Replacement_RC"] = master_stats["AB"] * replacement_rc_per_ab
master_stats["WAR"] = (master_stats["RC"] - master_stats["Replacement_RC"]) / 12

# Round relevant columns
round_cols = ["TB","RC","WAR","AVG","SLG %","OBP %","OPS %"]
master_stats[round_cols] = master_stats[round_cols].round(3)

# Save master stats back to Excel
with pd.ExcelWriter(file_path, mode="a", if_sheet_exists="replace", engine="openpyxl") as writer:
    master_stats.to_excel(writer, sheet_name="Master Stats", index=False)
print("Master stats sheet created successfully.")
