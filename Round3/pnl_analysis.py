#!/usr/bin/env python3
"""
Per-product PnL analysis using historical data.
Simulates simplified MM strategies to understand where edge exists.
"""
import csv, math
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

def load_trades(path):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f, delimiter=";"):
            r["timestamp"] = int(r["timestamp"])
            r["price"] = float(r["price"])
            r["quantity"] = int(r["quantity"])
            rows.append(r)
    return rows

# ─── Load all data ───────────────────────────────────────────────────────────
print("Loading data...")
all_prices = {}
all_trades = {}
for d in range(3):
    all_prices[d] = load_prices(f"{BASE}/prices_round_3_day_{d}.csv")
    all_trades[d] = load_trades(f"{BASE}/trades_round_3_day_{d}.csv")

# Group by product
price_by_product = defaultdict(lambda: defaultdict(list))
trade_by_product = defaultdict(lambda: defaultdict(list))
for d in range(3):
    for r in all_prices[d]:
        price_by_product[r["product"]][d].append(r)
    for r in all_trades[d]:
        trade_by_product[r["symbol"]][d].append(r)

products = sorted(set(r["product"] for d in range(3) for r in all_prices[d]))

# ═════════════════════════════════════════════════════════════════════════════
# ANALYSIS 1: Per-product spread capture potential
# ═════════════════════════════════════════════════════════════════════════════
print("\n" + "="*80)
print("ANALYSIS 1: SPREAD CAPTURE POTENTIAL (theoretical max)")
print("="*80)

for prod in ["HYDROGEL_PACK", "VELVETFRUIT_EXTRACT"]:
    print(f"\n{'─'*60}")
    print(f"  {prod}")
    print(f"{'─'*60}")
    for d in range(3):
        rows = price_by_product[prod][d]
        spreads = []
        half_spread_profits = []
        for r in rows:
            if r["bid_price_1"] is not None and r["ask_price_1"] is not None:
                spread = r["ask_price_1"] - r["bid_price_1"]
                spreads.append(spread)
                # If we quote at bid+1 and ask-1, our spread capture per unit is spread-2
                # But we only profit if filled on BOTH sides (round trip)
                half_spread_profits.append(max(0, spread - 2) / 2)  # per unit per fill

        avg_spread = sum(spreads) / len(spreads) if spreads else 0
        avg_hsp = sum(half_spread_profits) / len(half_spread_profits) if half_spread_profits else 0

        # Estimate fills: use trade volume as proxy for market activity
        trades = trade_by_product[prod][d]
        total_vol = sum(t["quantity"] for t in trades)
        # Assume we capture ~30% of market volume as MM
        est_fills = total_vol * 0.3
        est_daily_pnl = est_fills * avg_hsp

        print(f"  Day {d}: spread={avg_spread:.1f}, half_spread_profit/unit={avg_hsp:.2f}")
        print(f"          trades={len(trades)}, volume={total_vol}, est_fills={est_fills:.0f}")
        print(f"          EST DAILY PnL = {est_daily_pnl:.0f}")

# ═════════════════════════════════════════════════════════════════════════════
# ANALYSIS 2: Mean-reversion profitability (HP)
# ═════════════════════════════════════════════════════════════════════════════
print("\n" + "="*80)
print("ANALYSIS 2: HP MEAN-REVERSION MM SIMULATION")
print("="*80)

FV_ANCHOR = 10000
LIMIT = 200

for d in range(3):
    rows = price_by_product["HYDROGEL_PACK"][d]
    pos = 0
    pnl = 0
    ema = None
    anchor = FV_ANCHOR
    trades_executed = 0
    max_pos = 0

    for r in rows:
        mid = r["mid_price"]
        if mid is None:
            continue

        # Update EMA
        if ema is None:
            ema = mid
        else:
            ema = 0.20 * mid + 0.80 * ema
            anchor = 0.001 * mid + 0.999 * anchor

        skew = -pos * (3.0 / LIMIT)
        FV = round(0.50 * ema + 0.50 * anchor + skew)

        bid1 = r["bid_price_1"]
        ask1 = r["ask_price_1"]
        if bid1 is None or ask1 is None:
            continue

        # Simulate taker: buy below FV-1, sell above FV+1
        buy_cap = LIMIT - pos
        sell_cap = LIMIT + pos

        if ask1 < FV - 1 and buy_cap > 0:
            qty = min(r["ask_volume_1"], buy_cap, 12)
            pnl -= ask1 * qty
            pos += qty
            trades_executed += 1

        if bid1 > FV + 1 and sell_cap > 0:
            qty = min(r["bid_volume_1"], sell_cap, 12)
            pnl += bid1 * qty
            pos -= qty
            trades_executed += 1

        max_pos = max(max_pos, abs(pos))

    # Mark to market at end
    final_mid = rows[-1]["mid_price"] if rows[-1]["mid_price"] else FV_ANCHOR
    pnl += pos * final_mid  # liquidate at mid
    print(f"  Day {d}: trades={trades_executed}, max_pos={max_pos}, final_pos={pos}")
    print(f"          realized+unrealized PnL = {pnl:.0f}")

# ═════════════════════════════════════════════════════════════════════════════
# ANALYSIS 3: VE Simple MM simulation
# ═════════════════════════════════════════════════════════════════════════════
print("\n" + "="*80)
print("ANALYSIS 3: VE SIMPLE MM SIMULATION")
print("="*80)

VE_LIMIT = 200

for d in range(3):
    rows = price_by_product["VELVETFRUIT_EXTRACT"][d]
    pos = 0
    pnl = 0
    ema = None
    anchor = None
    trades_executed = 0

    for r in rows:
        mid = r["mid_price"]
        if mid is None:
            continue

        if ema is None:
            ema = mid
            anchor = mid
        else:
            ema = 0.15 * mid + 0.85 * ema
            anchor = 0.001 * mid + 0.999 * anchor

        skew = -pos * (2.0 / VE_LIMIT)
        FV = round(0.50 * ema + 0.50 * anchor + skew)

        bid1 = r["bid_price_1"]
        ask1 = r["ask_price_1"]
        if bid1 is None or ask1 is None:
            continue

        buy_cap = VE_LIMIT - pos
        sell_cap = VE_LIMIT + pos

        if ask1 < FV - 1 and buy_cap > 0:
            qty = min(r["ask_volume_1"], buy_cap, 12)
            pnl -= ask1 * qty
            pos += qty
            trades_executed += 1

        if bid1 > FV + 1 and sell_cap > 0:
            qty = min(r["bid_volume_1"], sell_cap, 12)
            pnl += bid1 * qty
            pos -= qty
            trades_executed += 1

    final_mid = rows[-1]["mid_price"] if rows[-1]["mid_price"] else 5250
    pnl += pos * final_mid
    print(f"  Day {d}: trades={trades_executed}, final_pos={pos}")
    print(f"          realized+unrealized PnL = {pnl:.0f}")

# ═════════════════════════════════════════════════════════════════════════════
# ANALYSIS 4: VEV_4000 deep ITM arb potential
# ═════════════════════════════════════════════════════════════════════════════
print("\n" + "="*80)
print("ANALYSIS 4: VEV_4000 DEEP ITM ARB POTENTIAL")
print("="*80)

for d in range(3):
    vev_rows = price_by_product["VEV_4000"][d]
    ve_rows = price_by_product["VELVETFRUIT_EXTRACT"][d]

    # Build VE mid lookup by timestamp
    ve_by_ts = {}
    for r in ve_rows:
        if r["mid_price"] is not None:
            ve_by_ts[r["timestamp"]] = r["mid_price"]

    arb_opportunities = 0
    total_arb_edge = 0
    max_arb = 0

    for r in vev_rows:
        ts = r["timestamp"]
        ve_mid = ve_by_ts.get(ts)
        if ve_mid is None or r["bid_price_1"] is None or r["ask_price_1"] is None:
            continue

        intrinsic = max(0, ve_mid - 4000)
        vev_mid = r["mid_price"]
        if vev_mid is None:
            continue

        # Arb: buy VEV below intrinsic, sell above
        if r["ask_price_1"] < intrinsic - 1:
            edge = intrinsic - r["ask_price_1"] - 1  # minus spread cost
            arb_opportunities += 1
            total_arb_edge += edge * r["ask_volume_1"]
            max_arb = max(max_arb, edge)

        if r["bid_price_1"] > intrinsic + 1:
            edge = r["bid_price_1"] - intrinsic - 1
            arb_opportunities += 1
            total_arb_edge += edge * r["bid_volume_1"]
            max_arb = max(max_arb, edge)

    print(f"  Day {d}: arb_opportunities={arb_opportunities}, total_edge={total_arb_edge:.0f}, max_single_edge={max_arb:.1f}")

# ═════════════════════════════════════════════════════════════════════════════
# ANALYSIS 5: VEV near-ATM options — what's the ACTUAL edge?
# ═════════════════════════════════════════════════════════════════════════════
print("\n" + "="*80)
print("ANALYSIS 5: VEV NEAR-ATM OPTIONS — SPREAD + THETA + TREND ANALYSIS")
print("="*80)

def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def bs_call(S, K, T, sigma):
    if T <= 1e-12 or sigma <= 1e-12 or S <= 0:
        return max(0.0, S - K)
    sqrtT = math.sqrt(T)
    d1 = (math.log(S / K) + 0.5 * sigma * sigma * T) / (sigma * sqrtT)
    d2 = d1 - sigma * sqrtT
    return S * norm_cdf(d1) - K * norm_cdf(d2)

for vev in ["VEV_5200", "VEV_5300", "VEV_5400", "VEV_5500"]:
    K = int(vev.split("_")[1])
    print(f"\n{'─'*60}")
    print(f"  {vev} (Strike={K})")
    print(f"{'─'*60}")

    for d in range(3):
        vev_rows = price_by_product[vev][d]
        ve_rows = price_by_product["VELVETFRUIT_EXTRACT"][d]

        ve_by_ts = {}
        for r in ve_rows:
            if r["mid_price"] is not None:
                ve_by_ts[r["timestamp"]] = r["mid_price"]

        # Track BS FV vs market price
        bs_errors = []
        spread_values = []
        mispricing_buys = 0
        mispricing_sells = 0
        total_buy_edge = 0
        total_sell_edge = 0

        for i, r in enumerate(vev_rows):
            ts = r["timestamp"]
            ve_mid = ve_by_ts.get(ts)
            if ve_mid is None or r["mid_price"] is None:
                continue

            # TTE: day d, tick i out of 10000
            tte_days = 5.0 - d - (i / 10000.0)
            T = max(0.001, tte_days) / 365.0
            sigma = 0.30

            bs_fv = bs_call(ve_mid, K, T, sigma)
            mkt_mid = r["mid_price"]
            error = mkt_mid - bs_fv
            bs_errors.append(error)

            if r["bid_price_1"] is not None and r["ask_price_1"] is not None:
                spread_values.append(r["ask_price_1"] - r["bid_price_1"])

                # Would our MM logic trigger?
                if r["ask_price_1"] < bs_fv - 1:
                    mispricing_buys += 1
                    total_buy_edge += bs_fv - r["ask_price_1"]
                if r["bid_price_1"] > bs_fv + 1:
                    mispricing_sells += 1
                    total_sell_edge += r["bid_price_1"] - bs_fv

        if bs_errors:
            avg_err = sum(bs_errors) / len(bs_errors)
            abs_err = sum(abs(e) for e in bs_errors) / len(bs_errors)
            max_err = max(abs(e) for e in bs_errors)
            avg_sp = sum(spread_values) / len(spread_values) if spread_values else 0
            print(f"  Day {d}: BS_error avg={avg_err:+.2f}, |error|={abs_err:.2f}, max={max_err:.2f}")
            print(f"          spread={avg_sp:.2f}")
            print(f"          buys_below_FV={mispricing_buys} (edge={total_buy_edge:.0f})")
            print(f"          sells_above_FV={mispricing_sells} (edge={total_sell_edge:.0f})")

            # Theta: how much does BS FV change from start to end of day?
            start_fv = bs_errors[0] + price_by_product[vev][d][0]["mid_price"] if price_by_product[vev][d][0]["mid_price"] else 0
            end_fv = bs_errors[-1] + price_by_product[vev][d][-1]["mid_price"] if price_by_product[vev][d][-1]["mid_price"] else 0

# ═════════════════════════════════════════════════════════════════════════════
# ANALYSIS 6: Directional edge — does VE have a trend we can exploit?
# ═════════════════════════════════════════════════════════════════════════════
print("\n" + "="*80)
print("ANALYSIS 6: VE DIRECTIONAL TREND ANALYSIS")
print("="*80)

for d in range(3):
    rows = price_by_product["VELVETFRUIT_EXTRACT"][d]
    mids = [r["mid_price"] for r in rows if r["mid_price"] is not None]
    if not mids:
        continue

    open_p = mids[0]
    close_p = mids[-1]
    change = close_p - open_p
    max_p = max(mids)
    min_p = min(mids)

    # Auto-correlation of returns (is it trending or mean-reverting?)
    rets = [mids[i] - mids[i-1] for i in range(1, len(mids))]
    if len(rets) > 2:
        mean_ret = sum(rets) / len(rets)
        # Lag-1 auto-correlation
        num = sum((rets[i] - mean_ret) * (rets[i-1] - mean_ret) for i in range(1, len(rets)))
        den = sum((r - mean_ret)**2 for r in rets)
        autocorr = num / den if den > 0 else 0

        # Is it trending (positive autocorr) or mean-reverting (negative)?
        regime = "TRENDING" if autocorr > 0.05 else ("MEAN-REVERTING" if autocorr < -0.05 else "RANDOM")
        print(f"  Day {d}: open={open_p}, close={close_p}, change={change:+.1f}")
        print(f"          range=[{min_p}, {max_p}], autocorr={autocorr:.4f} → {regime}")

# Same for HP
print("\n  HP Autocorrelation:")
for d in range(3):
    rows = price_by_product["HYDROGEL_PACK"][d]
    mids = [r["mid_price"] for r in rows if r["mid_price"] is not None]
    rets = [mids[i] - mids[i-1] for i in range(1, len(mids))]
    if len(rets) > 2:
        mean_ret = sum(rets) / len(rets)
        num = sum((rets[i] - mean_ret) * (rets[i-1] - mean_ret) for i in range(1, len(rets)))
        den = sum((r - mean_ret)**2 for r in rets)
        autocorr = num / den if den > 0 else 0
        regime = "TRENDING" if autocorr > 0.05 else ("MEAN-REVERTING" if autocorr < -0.05 else "RANDOM")
        print(f"  Day {d}: autocorr={autocorr:.4f} → {regime}")

# ═════════════════════════════════════════════════════════════════════════════
# ANALYSIS 7: How much PnL from passive quoting (bid+1/ask-1)?
# ═════════════════════════════════════════════════════════════════════════════
print("\n" + "="*80)
print("ANALYSIS 7: PASSIVE QUOTING FILL SIMULATION")
print("="*80)

for prod in ["HYDROGEL_PACK", "VELVETFRUIT_EXTRACT"]:
    print(f"\n  {prod}:")
    for d in range(3):
        rows = price_by_product[prod][d]
        # Track when price crosses our quote levels
        pnl = 0
        pos = 0
        limit = 200
        fills = 0

        for i in range(1, len(rows)):
            prev = rows[i-1]
            curr = rows[i]
            if prev["bid_price_1"] is None or curr["bid_price_1"] is None:
                continue

            # Our quotes at prev tick: bid = prev_bid+1, ask = prev_ask-1
            our_bid = prev["bid_price_1"] + 1
            our_ask = prev["ask_price_1"] - 1

            if our_bid >= our_ask:
                continue

            buy_cap = limit - pos
            sell_cap = limit + pos

            # Did someone sell to our bid? (market moved down through our bid)
            if curr["bid_price_1"] <= our_bid and buy_cap > 0:
                qty = min(5, buy_cap)  # assume small fills
                pnl -= our_bid * qty
                pos += qty
                fills += 1

            # Did someone buy our ask? (market moved up through our ask)
            if curr["ask_price_1"] >= our_ask and sell_cap > 0:
                qty = min(5, sell_cap)
                pnl += our_ask * qty
                pos -= qty
                fills += 1

        # M2M
        final_mid = rows[-1]["mid_price"] if rows[-1]["mid_price"] else 10000
        pnl += pos * final_mid
        print(f"    Day {d}: fills={fills}, final_pos={pos}, PnL={pnl:.0f}")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80)
