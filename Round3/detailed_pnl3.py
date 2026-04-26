import csv

BASE = "/Users/chaitanyasaagar/Desktop/IMC Prosperity/Round3"
prices = []
with open(f"{BASE}/prices_round_3_day_0.csv") as f:
    for r in csv.DictReader(f, delimiter=";"):
        if r["product"] == "HYDROGEL_PACK" and r["mid_price"]:
            prices.append((int(r["timestamp"]), float(r["mid_price"])))

print(f"Start price: {prices[0][1]}")
for ts, mid in prices:
    if ts % 100000 == 0:
        print(f"TS {ts}: {mid}")
print(f"End price: {prices[-1][1]}")

prices_ve = []
with open(f"{BASE}/prices_round_3_day_0.csv") as f:
    for r in csv.DictReader(f, delimiter=";"):
        if r["product"] == "VELVETFRUIT_EXTRACT" and r["mid_price"]:
            prices_ve.append((int(r["timestamp"]), float(r["mid_price"])))

print("VE:")
print(f"Start price: {prices_ve[0][1]}")
for ts, mid in prices_ve:
    if ts % 100000 == 0:
        print(f"TS {ts}: {mid}")
print(f"End price: {prices_ve[-1][1]}")

