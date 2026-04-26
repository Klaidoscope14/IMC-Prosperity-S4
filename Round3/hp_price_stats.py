import csv
BASE = "/Users/chaitanyasaagar/Desktop/IMC Prosperity/Round3"
prices = []
with open(f"{BASE}/prices_round_3_day_0.csv") as f:
    for r in csv.DictReader(f, delimiter=";"):
        if r["product"] == "HYDROGEL_PACK" and r["mid_price"]:
            prices.append(float(r["mid_price"]))

print(f"HP Day 0: Min {min(prices):.1f}, Max {max(prices):.1f}, Range {max(prices)-min(prices):.1f}")

prices1 = []
with open(f"{BASE}/prices_round_3_day_1.csv") as f:
    for r in csv.DictReader(f, delimiter=";"):
        if r["product"] == "HYDROGEL_PACK" and r["mid_price"]:
            prices1.append(float(r["mid_price"]))
print(f"HP Day 1: Min {min(prices1):.1f}, Max {max(prices1):.1f}, Range {max(prices1)-min(prices1):.1f}")
