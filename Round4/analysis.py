import pandas as pd
import numpy as np
import json, sys

DATA_DIR = "/Users/chaitanyasaagar/Desktop/IMC Prosperity/Round4"

# Load all data
prices = []
trades = []
for day in [1, 2, 3]:
    p = pd.read_csv(f"{DATA_DIR}/prices_round_4_day_{day}.csv", sep=";")
    p['day'] = day
    prices.append(p)
    t = pd.read_csv(f"{DATA_DIR}/trades_round_4_day_{day}.csv", sep=";")
    t['day'] = day
    trades.append(t)

prices_df = pd.concat(prices, ignore_index=True)
trades_df = pd.concat(trades, ignore_index=True)

print("="*80)
print("SECTION 1: DATASET OVERVIEW")
print("="*80)

for day in [1,2,3]:
    p = prices_df[prices_df.day==day]
    t = trades_df[trades_df.day==day]
    print(f"\n--- Day {day} ---")
    print(f"  Price rows: {len(p)}")
    print(f"  Trade rows: {len(t)}")
    print(f"  Price timestamp range: {p.timestamp.min()} - {p.timestamp.max()}")
    print(f"  Trade timestamp range: {t.timestamp.min()} - {t.timestamp.max()}")
    print(f"  Products in prices: {sorted(p['product'].unique())}")
    print(f"  Symbols in trades: {sorted(t['symbol'].unique())}")

print("\n\nUnique traders (buyers):", sorted(trades_df.buyer.unique()))
print("Unique traders (sellers):", sorted(trades_df.seller.unique()))
all_traders = sorted(set(trades_df.buyer.unique()) | set(trades_df.seller.unique()))
print("All unique traders:", all_traders)

print("\n\n" + "="*80)
print("SECTION 2: PRICE STATISTICS PER PRODUCT")
print("="*80)

products_main = ['HYDROGEL_PACK', 'VELVETFRUIT_EXTRACT']
products_vev = [c for c in sorted(prices_df['product'].unique()) if c.startswith('VEV')]

for prod in products_main + products_vev:
    pdf = prices_df[prices_df['product'] == prod]
    print(f"\n--- {prod} ---")
    print(f"  Mid price: mean={pdf.mid_price.mean():.2f}, std={pdf.mid_price.std():.2f}, "
          f"min={pdf.mid_price.min():.2f}, max={pdf.mid_price.max():.2f}")
    if pdf.bid_price_1.notna().any():
        spreads = pdf.ask_price_1 - pdf.bid_price_1
        spreads = spreads.dropna()
        if len(spreads) > 0:
            print(f"  Spread (ask1-bid1): mean={spreads.mean():.2f}, std={spreads.std():.2f}, "
                  f"min={spreads.min():.2f}, max={spreads.max():.2f}")
    # Per-day stats
    for day in [1,2,3]:
        dpdf = pdf[pdf.day == day]
        if len(dpdf) > 0:
            print(f"  Day {day}: open={dpdf.mid_price.iloc[0]:.2f}, close={dpdf.mid_price.iloc[-1]:.2f}, "
                  f"range={dpdf.mid_price.max()-dpdf.mid_price.min():.2f}")

print("\n\n" + "="*80)
print("SECTION 3: TRADE VOLUME ANALYSIS")
print("="*80)

for day in [1,2,3]:
    tday = trades_df[trades_df.day == day]
    print(f"\n--- Day {day} ---")
    grp = tday.groupby('symbol').agg(
        num_trades=('quantity','count'),
        total_volume=('quantity','sum'),
        avg_qty=('quantity','mean'),
        avg_price=('price','mean')
    ).sort_values('total_volume', ascending=False)
    print(grp.to_string())

print("\n\n" + "="*80)
print("SECTION 4: TRADER ACTIVITY SUMMARY")
print("="*80)

for trader in all_traders:
    buys = trades_df[trades_df.buyer == trader]
    sells = trades_df[trades_df.seller == trader]
    print(f"\n--- {trader} ---")
    print(f"  Total buy trades: {len(buys)}, total sell trades: {len(sells)}")
    print(f"  Buy volume: {buys.quantity.sum()}, Sell volume: {sells.quantity.sum()}")
    
    # By symbol
    buy_by_sym = buys.groupby('symbol').agg(n=('quantity','count'), vol=('quantity','sum'), 
                                             avg_px=('price','mean')).to_dict('index')
    sell_by_sym = sells.groupby('symbol').agg(n=('quantity','count'), vol=('quantity','sum'),
                                               avg_px=('price','mean')).to_dict('index')
    all_syms = sorted(set(list(buy_by_sym.keys()) + list(sell_by_sym.keys())))
    for sym in all_syms:
        b = buy_by_sym.get(sym, {'n':0, 'vol':0, 'avg_px':0})
        s = sell_by_sym.get(sym, {'n':0, 'vol':0, 'avg_px':0})
        print(f"    {sym}: Buy({b['n']} trades, {b['vol']} vol, avg_px={b['avg_px']:.1f}) | "
              f"Sell({s['n']} trades, {s['vol']} vol, avg_px={s['avg_px']:.1f})")

print("\n\n" + "="*80)
print("SECTION 5: COUNTERPARTY PAIR ANALYSIS")
print("="*80)

pair_stats = trades_df.groupby(['buyer','seller']).agg(
    n_trades=('quantity','count'),
    total_vol=('quantity','sum'),
    symbols=('symbol', lambda x: sorted(x.unique().tolist()))
).sort_values('total_vol', ascending=False)
print(pair_stats.to_string())

print("\n\n" + "="*80)
print("SECTION 6: POST-TRADE RETURN ANALYSIS (T+10, T+50, T+100)")
print("="*80)

# Build mid-price lookup per (day, product, timestamp)
mid_lookup = {}
for _, row in prices_df.iterrows():
    mid_lookup[(row['day'], row['product'], row['timestamp'])] = row['mid_price']

def get_mid(day, product, ts):
    return mid_lookup.get((day, product, ts), None)

# For each trade, compute forward returns
results = []
for _, trade in trades_df.iterrows():
    day = trade['day']
    sym = trade['symbol']
    ts = trade['timestamp']
    px = trade['price']
    
    mid_now = get_mid(day, sym, ts)
    if mid_now is None:
        # Try closest timestamp
        candidates = [k[2] for k in mid_lookup if k[0]==day and k[1]==sym]
        if candidates:
            closest = min(candidates, key=lambda x: abs(x-ts))
            mid_now = mid_lookup[(day, sym, closest)]
        else:
            continue
    
    fwd = {}
    for horizon in [10, 50, 100]:
        target_ts = ts + horizon * 100  # timestamps are in 100s
        mid_fwd = get_mid(day, sym, target_ts)
        if mid_fwd is not None:
            fwd[f'ret_{horizon}'] = mid_fwd - mid_now
        else:
            fwd[f'ret_{horizon}'] = None
    
    results.append({
        'day': day, 'timestamp': ts, 'buyer': trade['buyer'], 'seller': trade['seller'],
        'symbol': sym, 'price': px, 'quantity': trade['quantity'], 'mid_now': mid_now,
        **fwd
    })

ret_df = pd.DataFrame(results)
print(f"Total trades with return data: {len(ret_df)}")

# Trader-level forward returns
print("\n--- BUYER forward returns (positive = price went UP after they bought) ---")
for trader in all_traders:
    tdf = ret_df[ret_df.buyer == trader]
    if len(tdf) == 0:
        continue
    print(f"\n  {trader} (n={len(tdf)} buy trades):")
    for sym in sorted(tdf.symbol.unique()):
        sdf = tdf[tdf.symbol == sym]
        for h in ['ret_10','ret_50','ret_100']:
            vals = sdf[h].dropna()
            if len(vals) > 0:
                # Volume-weighted
                weights = sdf.loc[vals.index, 'quantity']
                vw = (vals * weights).sum() / weights.sum() if weights.sum() > 0 else 0
                print(f"    {sym} {h}: mean={vals.mean():.4f}, vw_mean={vw:.4f}, n={len(vals)}")

print("\n--- SELLER forward returns (negative = price went DOWN after they sold, i.e. good sell) ---")
for trader in all_traders:
    tdf = ret_df[ret_df.seller == trader]
    if len(tdf) == 0:
        continue
    print(f"\n  {trader} (n={len(tdf)} sell trades):")
    for sym in sorted(tdf.symbol.unique()):
        sdf = tdf[tdf.symbol == sym]
        for h in ['ret_10','ret_50','ret_100']:
            vals = sdf[h].dropna()
            if len(vals) > 0:
                weights = sdf.loc[vals.index, 'quantity']
                vw = (vals * weights).sum() / weights.sum() if weights.sum() > 0 else 0
                print(f"    {sym} {h}: mean={vals.mean():.4f}, vw_mean={vw:.4f}, n={len(vals)}")

print("\n\n" + "="*80)
print("SECTION 7: TRADER PnL ESTIMATION")
print("="*80)

# Estimate PnL: buy at price, mark-to-market at mid
# For each trader, net PnL = sum(sells*px) - sum(buys*px) + position * final_mid
for trader in all_traders:
    print(f"\n--- {trader} ---")
    for day in [1,2,3]:
        for sym in sorted(trades_df.symbol.unique()):
            tday = trades_df[(trades_df.day == day)]
            buys = tday[(tday.buyer == trader) & (tday.symbol == sym)]
            sells = tday[(tday.seller == trader) & (tday.symbol == sym)]
            if len(buys) == 0 and len(sells) == 0:
                continue
            
            cash = -(buys.price * buys.quantity).sum() + (sells.price * sells.quantity).sum()
            net_pos = buys.quantity.sum() - sells.quantity.sum()
            
            # Get final mid price
            final_mid = None
            pday = prices_df[(prices_df.day == day) & (prices_df['product'] == sym)]
            if len(pday) > 0:
                final_mid = pday.mid_price.iloc[-1]
            
            if final_mid is not None:
                pnl = cash + net_pos * final_mid
            else:
                pnl = cash  # can't mark to market
            
            print(f"  Day {day} {sym}: buys={buys.quantity.sum()}, sells={sells.quantity.sum()}, "
                  f"net_pos={net_pos}, cash={cash:.0f}, final_mid={final_mid}, est_pnl={pnl:.0f}")

print("\n\n" + "="*80)
print("SECTION 8: VEV OPTIONS ANALYSIS")
print("="*80)

# Analyze VEV mid prices over time
for vev in products_vev:
    vpdf = prices_df[prices_df['product'] == vev]
    print(f"\n--- {vev} ---")
    for day in [1,2,3]:
        dvpdf = vpdf[vpdf.day == day]
        if len(dvpdf) > 0:
            print(f"  Day {day}: open_mid={dvpdf.mid_price.iloc[0]:.2f}, close_mid={dvpdf.mid_price.iloc[-1]:.2f}, "
                  f"mean={dvpdf.mid_price.mean():.2f}, std={dvpdf.mid_price.std():.2f}")

# VEV trades pricing vs mid
print("\n--- VEV Trade Pricing Analysis ---")
vev_trades = trades_df[trades_df.symbol.str.startswith('VEV')]
for _, t in vev_trades.iterrows():
    mid = get_mid(t['day'], t['symbol'], t['timestamp'])
    if mid is not None:
        diff = t['price'] - mid
        print(f"  {t['symbol']} Day{t['day']} t={t['timestamp']}: trade_px={t['price']:.1f}, "
              f"mid={mid:.1f}, diff={diff:.1f}, buyer={t['buyer']}, seller={t['seller']}, qty={t['quantity']}")

print("\n\n" + "="*80)
print("SECTION 9: TRADER TIMING ANALYSIS")
print("="*80)

# When do traders trade?
for trader in all_traders:
    tdf = trades_df[(trades_df.buyer == trader) | (trades_df.seller == trader)]
    if len(tdf) == 0:
        continue
    print(f"\n--- {trader} ---")
    for day in [1,2,3]:
        ddf = tdf[tdf.day == day]
        if len(ddf) > 0:
            print(f"  Day {day}: first_trade={ddf.timestamp.min()}, last_trade={ddf.timestamp.max()}, "
                  f"n_trades={len(ddf)}, avg_interval={ddf.timestamp.diff().mean():.0f}")

print("\n\n" + "="*80)
print("SECTION 10: VELVETFRUIT_EXTRACT DEEP DIVE")
print("="*80)

ve_trades = trades_df[trades_df.symbol == 'VELVETFRUIT_EXTRACT'].copy()
print(f"Total VE trades: {len(ve_trades)}")
print(f"\nPer-day breakdown:")
for day in [1,2,3]:
    dve = ve_trades[ve_trades.day == day]
    print(f"  Day {day}: {len(dve)} trades, volume={dve.quantity.sum()}")
    # buyer-seller pairs
    for _, t in dve.iterrows():
        mid = get_mid(t['day'], t['symbol'], t['timestamp'])
        edge = t['price'] - mid if mid else None
        print(f"    t={t['timestamp']:>6}: {t['buyer']:>8} buys from {t['seller']:>8}, "
              f"px={t['price']:.0f}, mid={mid:.0f if mid else 0}, edge={edge:.1f if edge else 'N/A'}, qty={t['quantity']}")

print("\n\n" + "="*80)
print("SECTION 11: HYDROGEL_PACK DEEP DIVE")
print("="*80)

hp_trades = trades_df[trades_df.symbol == 'HYDROGEL_PACK'].copy()
print(f"Total HP trades: {len(hp_trades)}")
for day in [1,2,3]:
    dhp = hp_trades[hp_trades.day == day]
    print(f"\n  Day {day}: {len(dhp)} trades, volume={dhp.quantity.sum()}")
    for _, t in dhp.iterrows():
        mid = get_mid(t['day'], t['symbol'], t['timestamp'])
        edge = t['price'] - mid if mid else None
        print(f"    t={t['timestamp']:>6}: {t['buyer']:>8} buys from {t['seller']:>8}, "
              f"px={t['price']:.0f}, mid={mid:.0f if mid else 0}, edge={edge:.1f if edge else 'N/A'}, qty={t['quantity']}")

print("\n\n" + "="*80)
print("SECTION 12: AGGREGATE TRADER CLASSIFICATION")
print("="*80)

# For main products only
main_syms = ['HYDROGEL_PACK', 'VELVETFRUIT_EXTRACT']
for trader in all_traders:
    print(f"\n--- {trader} ---")
    for sym in main_syms:
        buy_tdf = ret_df[(ret_df.buyer == trader) & (ret_df.symbol == sym)]
        sell_tdf = ret_df[(ret_df.seller == trader) & (ret_df.symbol == sym)]
        
        if len(buy_tdf) > 0:
            for h in ['ret_10', 'ret_50', 'ret_100']:
                vals = buy_tdf[h].dropna()
                if len(vals) > 0:
                    pct_positive = (vals > 0).sum() / len(vals) * 100
                    print(f"  {sym} BUY {h}: mean={vals.mean():.2f}, hit_rate={pct_positive:.0f}%, n={len(vals)}")
        
        if len(sell_tdf) > 0:
            for h in ['ret_10', 'ret_50', 'ret_100']:
                vals = sell_tdf[h].dropna()
                if len(vals) > 0:
                    pct_negative = (vals < 0).sum() / len(vals) * 100
                    print(f"  {sym} SELL {h}: mean={vals.mean():.2f}, correct_rate={pct_negative:.0f}%, n={len(vals)}")

print("\n\n" + "="*80)
print("SECTION 13: PRICE VOLATILITY & TREND ANALYSIS")
print("="*80)

for prod in products_main:
    print(f"\n--- {prod} ---")
    for day in [1,2,3]:
        pdf = prices_df[(prices_df['product'] == prod) & (prices_df.day == day)].copy()
        pdf = pdf.sort_values('timestamp')
        returns = pdf.mid_price.diff()
        print(f"  Day {day}:")
        print(f"    Tick returns: mean={returns.mean():.4f}, std={returns.std():.4f}")
        print(f"    Total move: {pdf.mid_price.iloc[-1] - pdf.mid_price.iloc[0]:.2f}")
        print(f"    Max drawdown from peak: {(pdf.mid_price - pdf.mid_price.cummax()).min():.2f}")
        # Autocorrelation
        if len(returns.dropna()) > 10:
            ac1 = returns.dropna().autocorr(lag=1)
            ac5 = returns.dropna().autocorr(lag=5)
            print(f"    Autocorr lag1={ac1:.4f}, lag5={ac5:.4f}")

print("\n\nDONE")
