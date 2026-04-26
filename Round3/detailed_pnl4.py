import csv

BASE = "/Users/chaitanyasaagar/Desktop/IMC Prosperity/Round3"
prices = []
with open(f"{BASE}/prices_round_3_day_0.csv") as f:
    for r in csv.DictReader(f, delimiter=";"):
        if int(r["timestamp"]) <= 100000:
            r["timestamp"] = int(r["timestamp"])
            for k in ["bid_price_1","ask_price_1","mid_price"]:
                r[k] = float(r[k]) if r.get(k) and r[k] != "" else None
            for k in ["bid_volume_1","ask_volume_1"]:
                r[k] = int(r[k]) if r.get(k) and r[k] != "" else 0
            prices.append(r)

from collections import defaultdict
by_prod = defaultdict(list)
for r in prices:
    by_prod[r["product"]].append(r)

def sim_hp():
    pos = 0; pnl = 0; ema = None; anchor = 10000
    pnl_history = []
    for r in by_prod["HYDROGEL_PACK"]:
        mid = r["mid_price"]
        if mid is None: continue
        if ema is None: ema = mid
        else:
            ema = 0.20 * mid + 0.80 * ema
            anchor = 0.001 * mid + 0.999 * anchor
        skew = -pos * (3.0 / 200)
        fv = round(0.50 * ema + 0.50 * anchor + skew)
        
        buy_cap = 200 - pos; sell_cap = 200 + pos
        bid1, ask1 = r["bid_price_1"], r["ask_price_1"]
        
        if ask1 is not None and ask1 < fv - 1 and buy_cap > 0:
            qty = min(r["ask_volume_1"], buy_cap, 12)
            pnl -= ask1 * qty; pos += qty
        if bid1 is not None and bid1 > fv + 1 and sell_cap > 0:
            qty = min(r["bid_volume_1"], sell_cap, 12)
            pnl += bid1 * qty; pos -= qty
            
        m2m = pnl + pos * mid
        pnl_history.append(m2m)
    return pnl_history

print("HP M2M at TS 100,000:", sim_hp()[-1])
