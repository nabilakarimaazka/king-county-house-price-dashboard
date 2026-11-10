"""
Usage:
    python analysis/verify_findings.py data/kc_house_data.csv

The dashboard excludes sales priced above about $1.49M (about 2.5% of sales)
so that a few luxury homes do not distort averages. The same rule is applied here.
"""
import sys

import pandas as pd

PRICE_CAP = 1_490_000
MIN_SALES_PER_ZIP = 50

path = sys.argv[1] if len(sys.argv) > 1 else "data/kc_house_data.csv"
raw = pd.read_csv(path)
raw = raw.loc[:, ~raw.columns.str.startswith("Unnamed")]
raw["date"] = pd.to_datetime(raw["date"].astype(str).str[:8], format="%Y%m%d")

print("== Data checks ==")
print(f"Rows: {len(raw):,} | period: {raw.date.min():%d %b %Y} to {raw.date.max():%d %b %Y}")
print(f"Houses sold more than once in the period: {raw.id.duplicated().sum()}")
print(f"Max bedrooms: {raw.bedrooms.max():.0f} (sqft_living of that row: "
      f"{raw.loc[raw.bedrooms.idxmax(), 'sqft_living']})")
print(f"Median price, all sales: ${raw.price.median():,.0f}")

df = raw[raw.price <= PRICE_CAP].copy()
excluded = len(raw) - len(df)
print(f"Sales above ${PRICE_CAP:,}: {excluded} ({excluded / len(raw):.1%}) -> excluded")
df["price_per_sqft"] = df.price / df.sqft_living

print("\n== 1. Price level ==")
print(f"Median ${df.price.median():,.0f} | mean ${df.price.mean():,.0f} | "
      f"middle 50%: ${df.price.quantile(.25):,.0f} to ${df.price.quantile(.75):,.0f}")
print(f"Median price per sqft: ${df.price_per_sqft.median():,.0f}")

print("\n== 2. Timing ==")
monthly = df.groupby(df.date.dt.to_period("M")).agg(
    sales=("price", "size"), median_price=("price", "median"))
print(monthly)
weekend = df.date.dt.dayofweek >= 5
print(f"Share of sales on weekends: {weekend.mean():.1%}")
daily = df.groupby(df.date.dt.date).price.size()
print(f"Sales per day: median {daily.median():.0f}, min {daily.min()}")

print("\n== 3. Location ==")
z = df.groupby("zipcode").agg(sales=("price", "size"), median_price=("price", "median"),
                              price_per_sqft=("price_per_sqft", "median"))
z = z[z.sales >= MIN_SALES_PER_ZIP]
print(z.sort_values("median_price", ascending=False).head(5))
print(z.sort_values("median_price").head(5))
print(f"Top vs bottom zip median price: {z.median_price.max() / z.median_price.min():.1f}x")
print(f"Top vs bottom zip price per sqft: {z.price_per_sqft.max() / z.price_per_sqft.min():.1f}x")

print("\n== 4. Property features ==")
cols = ["sqft_living", "grade", "bathrooms", "lat", "bedrooms", "view", "condition", "yr_built"]
print("Correlation with price:")
print(df[cols].corrwith(df.price).round(2).sort_values(ascending=False))
for col in ["grade", "view", "condition", "waterfront", "bedrooms"]:
    print(f"\nBy {col}:")
    print(df.groupby(col).agg(sales=("price", "size"), median_price=("price", "median"),
                              price_per_sqft=("price_per_sqft", "median")).round(0))
