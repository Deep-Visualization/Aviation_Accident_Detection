"""
Build Accidents.json for the web page from "NTSB Cleaned dataset.xlsx".

Run from the project folder:
    python Build_data.py

The JSON stores one column per field (compact codes plus lookup lists),
so the browser can filter all ~88,000 records instantly.
"""
import json
import pandas as pd

SOURCE = "NTSB Cleaned dataset.xlsx"
OUTPUT = "Accidents.json"

df = pd.read_excel(SOURCE)

# Aircraft damage: merge spelling variants; everything else becomes "Other / unknown"
damage_map = {"destroyed": "Destroyed", "substantial": "Substantial", "minor": "Minor"}
df["damage"] = df["Aircraft Damage"].str.strip().str.lower().map(damage_map).fillna("Other / unknown")

# Weather: VMC = visual (good visibility), IMC = instrument (poor visibility / cloud)
df["weather"] = df["Weather Condition"].fillna("Unknown").str.strip()

# Keep the most common categories; group the rest as "Other"
def top(series, n):
    keep = series.value_counts().index[:n]
    return series.where(series.isin(keep), "Other")

df["purpose"] = top(df["Purpose Of Flight"].fillna("Unknown").str.strip(), 9)
df["engine"] = top(df["Engine Type"].fillna("unknown").str.strip().str.capitalize(), 6)
df["place"] = df["Place"].fillna("unknown").str.strip().str.capitalize()

# Only years with a full set of records (1982 onward; earlier years have 1-2 records each)
df = df[df["Event Year"] >= 1982].copy()

columns = {
    "damage": ["Destroyed", "Substantial", "Minor", "Other / unknown"],
    "weather": ["VMC", "IMC", "Unknown"],
    "purpose": sorted(df["purpose"].unique(), key=lambda v: (v == "Other", v == "Unknown", -int((df["purpose"] == v).sum()))),
    "engine": sorted(df["engine"].unique(), key=lambda v: (v == "Other", -int((df["engine"] == v).sum()))),
    "place": ["Airport", "Mountain", "Sea", "Unknown"],
}

def codes(col):
    lookup = {v: i for i, v in enumerate(columns[col])}
    return df[col].map(lookup).astype(int).tolist()

out = {
    "source": "NTSB Aviation Accident Database (cleaned)",
    "count": int(len(df)),
    "labels": columns,
    "year": df["Event Year"].astype(int).tolist(),
    "month": df["Event Month"].astype(int).tolist(),
    "damage": codes("damage"),
    "weather": codes("weather"),
    "purpose": codes("purpose"),
    "engine": codes("engine"),
    "place": codes("place"),
    "fatal": df["Total Fatal Injuries"].astype(int).tolist(),
    "people": df["Total Person"].astype(int).tolist(),
}

with open(OUTPUT, "w") as f:
    json.dump(out, f, separators=(",", ":"))

print(f"Saved {len(df):,} records to {OUTPUT}")
