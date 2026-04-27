import pandas as pd
import numpy as np

DATA_DIR = "/Users/chaitanyasaagar/Desktop/IMC Prosperity/Round4"

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
all_traders = sorted(set(trades_df.buyer.unique()) | set(trades_df.seller.unique()))
products_main = ['HYDROGEL_PACK', 'VELVETFRUIT_EXTRACT']

mid_lookup = {}
for _, row in prices_df.iterrows():
    mid_lookup[(row['day'], row['product'], row['timestamp'])] = row['mid_price']

def get_mid(day, product, ts):
    return mid_lookup.get((day, product, ts), None)

results = []
for _, trade in trades_df.iterrows():
    day = trade['day']
    sym = trade['symbol']
    ts = trade['timestamp']
    mid_now = get_mid(day, sym, ts)
    if mid_now is None:
        candidates = [k[2] for k in mid_lookup if k[0]==day and k[1]==sym]
        if candidates:
            closest = min(candidates, key=lambda x: abs(x-ts))
            mid_now = mid_lookup[(day, sym, closest)]
        else:
            continue
    fwd = {}
    for horizon in [10, 50, 100]:
        target_ts = ts + horizon * 100
        mid_fwd = get_mid(day, sym, target_ts)
        if mid_fwd is not None:
            fwd[f'ret_{horizon}'] = mid_fwd - mid_now
        else:
            fwd[f'ret_{horizon}'] = None
    results.append({
        'day': day, 'timestamp': ts, 'buyer': trade['buyer'], 'seller': trade['seller'],
        'symbol': sym, 'price': trade['price'], 'quantity': trade['quantity'], 'mid_now': mid_now,
        **fwd
    })

ret_df = pd.DataFrame(results)

print("="*80)
print("SECTION 12: AGGREGATE TRADER CLASSIFICATION")
print("="*80)

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
        if len(returns.dropna()) > 10:
            ac1 = returns.dropna().autocorr(lag=1)
            ac5 = returns.dropna().autocorr(lag=5)
            print(f"    Autocorr lag1={ac1:.4f}, lag5={ac5:.4f}")

print("\n\n" + "="*80)
print("SECTION 14: COUNTERPARTY EDGE ANALYSIS")
print("="*80)

# For each trade, compute edge = trade price vs mid
for sym in main_syms:
    print(f"\n--- {sym} ---")
    sym_trades = ret_df[ret_df.symbol == sym]
    for trader in all_traders:
        buys = sym_trades[sym_trades.buyer == trader]
        sells = sym_trades[sym_trades.seller == trader]
        if len(buys) > 0:
            buy_edge = (buys['mid_now'] - buys['price'])  # positive = bought below mid
            print(f"  {trader} BUY edge: mean={buy_edge.mean():.2f}, vol_wt={(buy_edge*buys['quantity']).sum()/buys['quantity'].sum():.2f}, n={len(buys)}")
        if len(sells) > 0:
            sell_edge = (sells['price'] - sells['mid_now'])  # positive = sold above mid
            print(f"  {trader} SELL edge: mean={sell_edge.mean():.2f}, vol_wt={(sell_edge*sells['quantity']).sum()/sells['quantity'].sum():.2f}, n={len(sells)}")

print("\n\n" + "="*80)
print("SECTION 15: AGGREGATED TOTAL PnL PER TRADER PER DAY")
print("="*80)

for trader in all_traders:
    total = 0
    for day in [1,2,3]:
        day_pnl = 0
        for sym in sorted(trades_df.symbol.unique()):
            tday = trades_df[(trades_df.day == day)]
            buys = tday[(tday.buyer == trader) & (tday.symbol == sym)]
            sells = tday[(tday.seller == trader) & (tday.symbol == sym)]
            if len(buys) == 0 and len(sells) == 0:
                continue
            cash = -(buys.price * buys.quantity).sum() + (sells.price * sells.quantity).sum()
            net_pos = buys.quantity.sum() - sells.quantity.sum()
            pday = prices_df[(prices_df.day == day) & (prices_df['product'] == sym)]
            final_mid = pday.mid_price.iloc[-1] if len(pday) > 0 else 0
            pnl = cash + net_pos * final_mid
            day_pnl += pnl
        total += day_pnl
        print(f"  {trader} Day {day}: total_pnl={day_pnl:.0f}")
    print(f"  {trader} TOTAL 3-DAY: {total:.0f}")
    print()

print("\n\n" + "="*80)
print("SECTION 16: VEV INTRINSIC VALUE vs MID PRICE")
print("="*80)

# VE underlying mid at each timestamp
for day in [1,2,3]:
    ve_mid_close = prices_df[(prices_df['product']=='VELVETFRUIT_EXTRACT') & (prices_df.day==day)].mid_price.iloc[-1]
    print(f"\nDay {day}: VE close mid = {ve_mid_close}")
    for strike in [4000, 4500, 5000, 5100, 5200, 5300, 5400, 5500, 6000, 6500]:
        vev = f"VEV_{strike}"
        vev_close = prices_df[(prices_df['product']==vev) & (prices_df.day==day)].mid_price.iloc[-1]
        intrinsic = max(ve_mid_close - strike, 0)
        time_value = vev_close - intrinsic
        print(f"  {vev}: close_mid={vev_close:.1f}, intrinsic={intrinsic:.1f}, time_value={time_value:.1f}")

print("\n\nDONE")
