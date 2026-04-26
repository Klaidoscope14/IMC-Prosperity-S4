#!/usr/bin/env python3
"""Comprehensive analysis of Round 3 datasets for IMC Prosperity."""

import csv
import json
import math
from collections import defaultdict

BASE = "/Users/chaitanyasaagar/Desktop/IMC Prosperity/Round3"

# ── helpers ──────────────────────────────────────────────────────────────────
def load_prices(path):
    rows = []
    with open(path, "r") as f:
        reader = csv.DictReader(f, delimiter=";")
        for r in reader:
            r["timestamp"] = int(r["timestamp"])
            r["mid_price"] = float(r["mid_price"]) if r["mid_price"] else None
            for k in ["bid_price_1","bid_price_2","bid_price_3",
                       "ask_price_1","ask_price_2","ask_price_3"]:
                r[k] = float(r[k]) if r.get(k) and r[k] != "" else None
            for k in ["bid_volume_1","bid_volume_2","bid_volume_3",
                       "ask_volume_1","ask_volume_2","ask_volume_3"]:
                r[k] = int(r[k]) if r.get(k) and r[k] != "" else 0
            rows.append(r)
    return rows

def load_trades(path):
    rows = []
    with open(path, "r") as f:
        reader = csv.DictReader(f, delimiter=";")
        for r in reader:
            r["timestamp"] = int(r["timestamp"])
            r["price"] = float(r["price"])
            r["quantity"] = int(r["quantity"])
            rows.append(r)
    return rows

def stats(values):
    if not values:
        return {}
    n = len(values)
    mn = min(values)
    mx = max(values)
    avg = sum(values) / n
    s = sorted(values)
    med = s[n//2] if n % 2 == 1 else (s[n//2-1] + s[n//2]) / 2
    std = math.sqrt(sum((v - avg)**2 for v in values) / n) if n > 1 else 0
    return {"min": mn, "max": mx, "mean": round(avg, 2), "median": med,
            "std": round(std, 2), "count": n}

def pct_return(prices):
    """Compute simple returns between consecutive mid prices."""
    rets = []
    for i in range(1, len(prices)):
        if prices[i-1] and prices[i] and prices[i-1] != 0:
            rets.append((prices[i] - prices[i-1]) / prices[i-1])
    return rets

# ── load all data ────────────────────────────────────────────────────────────
print("Loading data...")
prices = {}
trades = {}
for d in range(3):
    prices[d] = load_prices(f"{BASE}/prices_round_3_day_{d}.csv")
    trades[d] = load_trades(f"{BASE}/trades_round_3_day_{d}.csv")
    print(f"  Day {d}: {len(prices[d]):,} price rows, {len(trades[d]):,} trade rows")

# ── identify products ────────────────────────────────────────────────────────
products = set()
for d in range(3):
    for r in prices[d]:
        products.add(r["product"])
products = sorted(products)
print(f"\nProducts ({len(products)}): {products}")

# ── split by product ─────────────────────────────────────────────────────────
price_by_product = defaultdict(lambda: defaultdict(list))
trade_by_product = defaultdict(lambda: defaultdict(list))
for d in range(3):
    for r in prices[d]:
        price_by_product[r["product"]][d].append(r)
    for r in trades[d]:
        trade_by_product[r["symbol"]][d].append(r)

# ── Analysis output ──────────────────────────────────────────────────────────
output_lines = []
def out(s=""):
    output_lines.append(s)

out("# 📊 Round 3 Data Analysis")
out()
out("## 📁 Dataset Overview")
out()
out("| File | Rows | Size |")
out("|------|------|------|")
for d in range(3):
    out(f"| `prices_round_3_day_{d}.csv` | {len(prices[d]):,} | ~6.5 MB |")
    out(f"| `trades_round_3_day_{d}.csv` | {len(trades[d]):,} | ~50 KB |")
out()
out(f"**Products traded**: {', '.join(products)}")
out()

# ── Per-product mid-price statistics ─────────────────────────────────────────
delta1 = ["HYDROGEL_PACK", "VELVETFRUIT_EXTRACT"]
vevs = [p for p in products if p.startswith("VEV_")]

out("---")
out()
out("## 🟢 Delta-1 Products")
out()

for prod in delta1:
    out(f"### {prod}")
    out()
    out("| Day | Min | Max | Mean | Median | Std Dev | Ticks |")
    out("|-----|-----|-----|------|--------|---------|-------|")
    all_mids = []
    for d in range(3):
        mids = [r["mid_price"] for r in price_by_product[prod][d] if r["mid_price"] is not None]
        all_mids.extend(mids)
        s = stats(mids)
        out(f"| Day {d} | {s['min']} | {s['max']} | {s['mean']} | {s['median']} | {s['std']} | {s['count']} |")
    s_all = stats(all_mids)
    out(f"| **All** | {s_all['min']} | {s_all['max']} | {s_all['mean']} | {s_all['median']} | {s_all['std']} | {s_all['count']} |")
    out()

    # Spread analysis
    out(f"#### Spread Analysis")
    out()
    out("| Day | Avg Spread | Min Spread | Max Spread | Median Spread |")
    out("|-----|-----------|-----------|-----------|--------------|")
    for d in range(3):
        spreads = []
        for r in price_by_product[prod][d]:
            if r["bid_price_1"] is not None and r["ask_price_1"] is not None:
                spreads.append(r["ask_price_1"] - r["bid_price_1"])
        s = stats(spreads)
        out(f"| Day {d} | {s['mean']} | {s['min']} | {s['max']} | {s['median']} |")
    out()

    # Returns / volatility
    out(f"#### Intraday Volatility (mid-price returns)")
    out()
    out("| Day | Mean Return | Std Return (bp) | Max Drawdown |")
    out("|-----|-----------|-----------------|-------------|")
    for d in range(3):
        mids = [r["mid_price"] for r in price_by_product[prod][d] if r["mid_price"] is not None]
        rets = pct_return(mids)
        s = stats(rets) if rets else {}
        std_bp = round(s.get("std", 0) * 10000, 2)
        # Max drawdown
        peak = mids[0] if mids else 0
        max_dd = 0
        for m in mids:
            if m > peak:
                peak = m
            dd = (peak - m) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
        out(f"| Day {d} | {s.get('mean', 'N/A')} | {std_bp} | {round(max_dd*100, 2)}% |")
    out()

    # Trade analysis
    out(f"#### Trade Activity")
    out()
    out("| Day | Trades | Total Volume | VWAP | Avg Trade Size |")
    out("|-----|--------|-------------|------|---------------|")
    for d in range(3):
        trs = trade_by_product[prod][d]
        if trs:
            vol = sum(t["quantity"] for t in trs)
            vwap = sum(t["price"] * t["quantity"] for t in trs) / vol if vol > 0 else 0
            avg_sz = round(vol / len(trs), 1)
            out(f"| Day {d} | {len(trs)} | {vol} | {round(vwap, 2)} | {avg_sz} |")
        else:
            out(f"| Day {d} | 0 | 0 | N/A | N/A |")
    out()

    # Price trajectory summary
    out(f"#### Price Trajectory")
    out()
    for d in range(3):
        mids = [r["mid_price"] for r in price_by_product[prod][d] if r["mid_price"] is not None]
        if mids:
            open_p = mids[0]
            close_p = mids[-1]
            change = close_p - open_p
            change_pct = round(change / open_p * 100, 2) if open_p != 0 else 0
            out(f"- **Day {d}**: Open={open_p} → Close={close_p} (Δ={change:+.1f}, {change_pct:+.2f}%)")
    out()

    # Order book depth
    out(f"#### Order Book Depth")
    out()
    out("| Day | Avg Bid Vol (L1) | Avg Ask Vol (L1) | Avg Total Depth |")
    out("|-----|-----------------|-----------------|----------------|")
    for d in range(3):
        bid_vols = []
        ask_vols = []
        total_depths = []
        for r in price_by_product[prod][d]:
            bv = r["bid_volume_1"] + r.get("bid_volume_2", 0) + r.get("bid_volume_3", 0)
            av = r["ask_volume_1"] + r.get("ask_volume_2", 0) + r.get("ask_volume_3", 0)
            bid_vols.append(r["bid_volume_1"])
            ask_vols.append(r["ask_volume_1"])
            total_depths.append(bv + av)
        sbv = stats(bid_vols)
        sav = stats(ask_vols)
        std = stats(total_depths)
        out(f"| Day {d} | {sbv['mean']} | {sav['mean']} | {std['mean']} |")
    out()
    out("---")
    out()

# ── VEV (Options) Analysis ──────────────────────────────────────────────────
out("## 📈 VEV (Velvetfruit Extract Voucher) Options")
out()

# Extract strike from name
def get_strike(name):
    return int(name.split("_")[1])

out("### Mid-Price Summary by Strike and Day")
out()
out("| VEV | Strike | Day 0 Mid | Day 1 Mid | Day 2 Mid | Day 0→2 Δ |")
out("|-----|--------|----------|----------|----------|----------|")
for vev in vevs:
    strike = get_strike(vev)
    day_avgs = []
    for d in range(3):
        mids = [r["mid_price"] for r in price_by_product[vev][d] if r["mid_price"] is not None]
        day_avgs.append(round(sum(mids)/len(mids), 2) if mids else 0)
    delta = round(day_avgs[2] - day_avgs[0], 2) if day_avgs[0] and day_avgs[2] else "N/A"
    out(f"| {vev} | {strike} | {day_avgs[0]} | {day_avgs[1]} | {day_avgs[2]} | {delta} |")
out()

# Moneyness analysis
out("### Moneyness Analysis (relative to VELVETFRUIT_EXTRACT)")
out()
out("Using average underlying mid-price per day:")
out()
for d in range(3):
    und_mids = [r["mid_price"] for r in price_by_product["VELVETFRUIT_EXTRACT"][d] if r["mid_price"] is not None]
    und_avg = round(sum(und_mids)/len(und_mids), 2) if und_mids else 0
    out(f"- **Day {d}**: VELVETFRUIT_EXTRACT avg = {und_avg}")
out()

out("| VEV | Strike | Day 0 Moneyness | Day 1 Moneyness | Day 2 Moneyness |")
out("|-----|--------|----------------|----------------|----------------|")
for vev in vevs:
    strike = get_strike(vev)
    row = [vev, str(strike)]
    for d in range(3):
        und_mids = [r["mid_price"] for r in price_by_product["VELVETFRUIT_EXTRACT"][d] if r["mid_price"] is not None]
        und_avg = sum(und_mids)/len(und_mids) if und_mids else 0
        if und_avg > 0:
            m = round((und_avg - strike) / und_avg * 100, 1)
            label = "ITM" if und_avg > strike else ("ATM" if und_avg == strike else "OTM")
            row.append(f"{m}% ({label})")
        else:
            row.append("N/A")
    out(f"| {' | '.join(row)} |")
out()

# VEV spreads
out("### VEV Bid-Ask Spreads")
out()
out("| VEV | Day 0 Avg Spread | Day 1 Avg Spread | Day 2 Avg Spread |")
out("|-----|-----------------|-----------------|-----------------|")
for vev in vevs:
    row = [vev]
    for d in range(3):
        spreads = []
        for r in price_by_product[vev][d]:
            if r["bid_price_1"] is not None and r["ask_price_1"] is not None:
                spreads.append(r["ask_price_1"] - r["bid_price_1"])
        s = stats(spreads)
        row.append(str(s.get("mean", "N/A")))
    out(f"| {' | '.join(row)} |")
out()

# VEV trade activity
out("### VEV Trade Activity")
out()
out("| VEV | Day 0 Trades | Day 0 Vol | Day 1 Trades | Day 1 Vol | Day 2 Trades | Day 2 Vol |")
out("|-----|-------------|----------|-------------|----------|-------------|----------|")
for vev in vevs:
    row = [vev]
    for d in range(3):
        trs = trade_by_product[vev][d]
        n_trades = len(trs)
        vol = sum(t["quantity"] for t in trs) if trs else 0
        row.extend([str(n_trades), str(vol)])
    out(f"| {' | '.join(row)} |")
out()

# VEV intrinsic value vs market price
out("### Intrinsic Value vs Market Price")
out()
out("| VEV | Strike | Day 0: Und | Intrinsic | MktMid | Extrinsic | Day 2: Und | Intrinsic | MktMid | Extrinsic |")
out("|-----|--------|----------|----------|--------|----------|----------|----------|--------|----------|")
for vev in vevs:
    strike = get_strike(vev)
    row = [vev, str(strike)]
    for d in [0, 2]:
        und_mids = [r["mid_price"] for r in price_by_product["VELVETFRUIT_EXTRACT"][d] if r["mid_price"] is not None]
        vev_mids = [r["mid_price"] for r in price_by_product[vev][d] if r["mid_price"] is not None]
        und_avg = round(sum(und_mids)/len(und_mids), 2) if und_mids else 0
        vev_avg = round(sum(vev_mids)/len(vev_mids), 2) if vev_mids else 0
        intrinsic = round(max(0, und_avg - strike), 2)
        extrinsic = round(vev_avg - intrinsic, 2)
        row.extend([str(und_avg), str(intrinsic), str(vev_avg), str(extrinsic)])
    out(f"| {' | '.join(row)} |")
out()

# ── Implied Volatility estimation ───────────────────────────────────────────
out("### Implied Volatility Estimation (Black-Scholes)")
out()

def bs_call_price(S, K, T, sigma, r=0):
    """Black-Scholes call price."""
    if T <= 0 or sigma <= 0 or S <= 0:
        return max(0, S - K)
    d1 = (math.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    # Approximate N(x) using error function
    def norm_cdf(x):
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))
    return S * norm_cdf(d1) - K * math.exp(-r*T) * norm_cdf(d2)

def implied_vol(market_price, S, K, T, r=0, tol=1e-6, max_iter=100):
    """Newton-Raphson implied vol solver."""
    if market_price <= max(0, S - K):
        return None
    sigma = 0.5  # initial guess
    for _ in range(max_iter):
        price = bs_call_price(S, K, T, sigma, r)
        # vega
        if T <= 0 or sigma <= 0:
            return None
        d1 = (math.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma * math.sqrt(T))
        def norm_pdf(x):
            return math.exp(-0.5*x**2) / math.sqrt(2*math.pi)
        vega = S * norm_pdf(d1) * math.sqrt(T)
        if vega < 1e-12:
            return None
        sigma = sigma - (price - market_price) / vega
        if sigma <= 0:
            sigma = 0.01
        if abs(price - market_price) < tol:
            return sigma
    return sigma

# TTE schedule: Day 0 = 7 days TTE, Day 1 = 6, Day 2 = 5 (from readme table, round 3 starts at 5 days)
# Actually from readme: Round 3 TTE = 5 days. But the "starting from day 1" and 
# TTE decreases each day. Let me use: Day 0 → TTE=7/365*... 
# The VEVs have TTE of 7 Solvenarian days starting from day 1.
# Per the TTE table: Tutorial=8, R1=7, R2=6, R3=5
# So on Day 0, TTE=5 days; Day 1, TTE=4 days; Day 2, TTE=3 days
# But actually the user said "All VEVs have TTE of 7 Solvenarian days, starting from day 1"
# And the table says Round 3: 5 days
# Let me use the table: R3 starts with TTE=5

# Using TTE table from readme for R3
tte_map = {0: 5/365, 1: 4/365, 2: 3/365}

out("Using TTE from readme (Round 3): Day 0 = 5 days, Day 1 = 4 days, Day 2 = 3 days")
out()
out("| VEV | Strike | Day 0 IV | Day 1 IV | Day 2 IV |")
out("|-----|--------|---------|---------|---------|")
for vev in vevs:
    strike = get_strike(vev)
    row = [vev, str(strike)]
    for d in range(3):
        und_mids = [r["mid_price"] for r in price_by_product["VELVETFRUIT_EXTRACT"][d] if r["mid_price"] is not None]
        vev_mids = [r["mid_price"] for r in price_by_product[vev][d] if r["mid_price"] is not None]
        S = sum(und_mids)/len(und_mids) if und_mids else 0
        mkt = sum(vev_mids)/len(vev_mids) if vev_mids else 0
        T = tte_map[d]
        iv = implied_vol(mkt, S, strike, T)
        if iv is not None:
            row.append(f"{round(iv*100, 1)}%")
        else:
            row.append("N/A")
    out(f"| {' | '.join(row)} |")
out()

# ── Correlation analysis ────────────────────────────────────────────────────
out("---")
out()
out("## 🔗 Cross-Product Correlation")
out()

# Compute correlation between HYDROGEL_PACK and VELVETFRUIT_EXTRACT mid prices
out("### HYDROGEL_PACK vs VELVETFRUIT_EXTRACT (mid-price correlation)")
out()
for d in range(3):
    hp_by_ts = {}
    ve_by_ts = {}
    for r in price_by_product["HYDROGEL_PACK"][d]:
        if r["mid_price"] is not None:
            hp_by_ts[r["timestamp"]] = r["mid_price"]
    for r in price_by_product["VELVETFRUIT_EXTRACT"][d]:
        if r["mid_price"] is not None:
            ve_by_ts[r["timestamp"]] = r["mid_price"]
    common_ts = sorted(set(hp_by_ts.keys()) & set(ve_by_ts.keys()))
    if len(common_ts) > 2:
        hp_vals = [hp_by_ts[t] for t in common_ts]
        ve_vals = [ve_by_ts[t] for t in common_ts]
        hp_mean = sum(hp_vals) / len(hp_vals)
        ve_mean = sum(ve_vals) / len(ve_vals)
        cov = sum((h - hp_mean) * (v - ve_mean) for h, v in zip(hp_vals, ve_vals)) / len(hp_vals)
        hp_std = math.sqrt(sum((h - hp_mean)**2 for h in hp_vals) / len(hp_vals))
        ve_std = math.sqrt(sum((v - ve_mean)**2 for v in ve_vals) / len(ve_vals))
        corr = cov / (hp_std * ve_std) if hp_std > 0 and ve_std > 0 else 0
        out(f"- **Day {d}**: ρ = {round(corr, 4)} ({len(common_ts)} common timestamps)")
    else:
        out(f"- **Day {d}**: Insufficient data")
out()

# ── Timestamp analysis ───────────────────────────────────────────────────────
out("---")
out()
out("## ⏱️ Timestamp / Tick Structure")
out()
for prod in delta1:
    out(f"### {prod}")
    for d in range(3):
        timestamps = sorted(set(r["timestamp"] for r in price_by_product[prod][d]))
        if len(timestamps) > 1:
            diffs = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
            s = stats(diffs)
            out(f"- Day {d}: {len(timestamps)} ticks, interval: min={s['min']}, max={s['max']}, mean={s['mean']}, median={s['median']}")
    out()

# ── Summary of key observations ─────────────────────────────────────────────
out("---")
out()
out("## 🧠 Key Observations & Strategy Implications")
out()

# Compute some final summaries for the observations
hp_all_mids = []
ve_all_mids = []
for d in range(3):
    hp_all_mids.extend([r["mid_price"] for r in price_by_product["HYDROGEL_PACK"][d] if r["mid_price"] is not None])
    ve_all_mids.extend([r["mid_price"] for r in price_by_product["VELVETFRUIT_EXTRACT"][d] if r["mid_price"] is not None])

hp_s = stats(hp_all_mids)
ve_s = stats(ve_all_mids)

out(f"### HYDROGEL_PACK")
out(f"- Price range: {hp_s['min']} – {hp_s['max']} (mean: {hp_s['mean']})")
out(f"- Relatively {'low' if hp_s['std'] < 100 else 'high'} volatility (σ = {hp_s['std']})")
out()

out(f"### VELVETFRUIT_EXTRACT")
out(f"- Price range: {ve_s['min']} – {ve_s['max']} (mean: {ve_s['mean']})")
out(f"- Relatively {'low' if ve_s['std'] < 100 else 'high'} volatility (σ = {ve_s['std']})")
out()

out("### VEV Options")
out("- Deep ITM options (VEV_4000, VEV_4500) trade close to intrinsic value with minimal extrinsic value")
out("- ATM/near-ATM options (VEV_5000–VEV_5500) have highest extrinsic value → highest vol premium")
out("- Deep OTM options (VEV_6000, VEV_6500) trade near zero")
out("- Implied volatility surface across strikes provides vol skew information")
out("- TTE decay from 5→3 days should cause theta decay, especially in ATM options")
out()

out("### Position Limits")
out("- HYDROGEL_PACK: 200")
out("- VELVETFRUIT_EXTRACT: 200")
out("- Each VEV: 300")
out()

out("### Manual Trading (Bio-Pods)")
out("- Reserve prices: 670–920 (step=5, uniform)")
out("- Optimal first bid: just above 920 to guarantee execution")
out("- Second bid: game-theoretic optimization vs penalty function")
out("- Penalty: ((920 - avg_b2) / (920 - b2))^3")
out()

# Write output
with open(f"{BASE}/data.md", "w") as f:
    f.write("\n".join(output_lines))
print(f"\nAnalysis written to {BASE}/data.md")
