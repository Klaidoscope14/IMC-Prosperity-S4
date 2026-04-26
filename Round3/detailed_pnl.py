import csv
from collections import defaultdict

BASE = "/Users/chaitanyasaagar/Desktop/IMC Prosperity/Round3"

def load_prices(path):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f, delimiter=";"):
            r["timestamp"] = int(r["timestamp"])
            for k in ["bid_price_1","bid_price_2","bid_price_3","ask_price_1","ask_price_2","ask_price_3","mid_price"]:
                r[k] = float(r[k]) if r.get(k) and r[k] != "" else None
            for k in ["bid_volume_1","bid_volume_2","bid_volume_3","ask_volume_1","ask_volume_2","ask_volume_3"]:
                r[k] = int(r[k]) if r.get(k) and r[k] != "" else 0
            rows.append(r)
    return rows

prices = load_prices(f"{BASE}/prices_round_3_day_0.csv")
by_prod = defaultdict(list)
for r in prices:
    by_prod[r["product"]].append(r)

# Simulate HP
def sim_hp():
    pos = 0
    pnl = 0
    ema = None
    anchor = 10000
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
        
        buy_cap = 200 - pos
        sell_cap = 200 + pos
        bid1, ask1 = r["bid_price_1"], r["ask_price_1"]
        
        if ask1 is not None and ask1 < fv - 1 and buy_cap > 0:
            qty = min(r["ask_volume_1"], buy_cap, 12)
            pnl -= ask1 * qty
            pos += qty
        if bid1 is not None and bid1 > fv + 1 and sell_cap > 0:
            qty = min(r["bid_volume_1"], sell_cap, 12)
            pnl += bid1 * qty
            pos -= qty
        
        m2m = pnl + pos * mid
        pnl_history.append(m2m)
    return pnl_history

# Simulate VE
def sim_ve():
    pos = 0
    pnl = 0
    ema = None
    anchor = 5250
    pnl_history = []
    for r in by_prod["VELVETFRUIT_EXTRACT"]:
        mid = r["mid_price"]
        if mid is None: continue
        if ema is None: ema = mid
        else:
            ema = 0.15 * mid + 0.85 * ema
            anchor = 0.001 * mid + 0.999 * anchor
        skew = -pos * (2.0 / 200)
        fv = round(0.50 * ema + 0.50 * anchor + skew)
        
        buy_cap = 200 - pos
        sell_cap = 200 + pos
        bid1, ask1 = r["bid_price_1"], r["ask_price_1"]
        
        if ask1 is not None and ask1 < fv - 1 and buy_cap > 0:
            qty = min(r["ask_volume_1"], buy_cap, 12)
            pnl -= ask1 * qty
            pos += qty
        if bid1 is not None and bid1 > fv + 1 and sell_cap > 0:
            qty = min(r["bid_volume_1"], sell_cap, 12)
            pnl += bid1 * qty
            pos -= qty
            
        m2m = pnl + pos * mid
        pnl_history.append(m2m)
    return pnl_history

hp_pnl = sim_hp()
ve_pnl = sim_ve()

import builtins
def print_stats(name, hist):
    print(f"{name}: Min M2M: {min(hist):.0f}, Max M2M: {max(hist):.0f}, Final: {hist[-1]:.0f}")

print_stats("HP", hp_pnl)
print_stats("VE", ve_pnl)
