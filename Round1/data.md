# Round 1 — Complete Data Analysis
> **Datasets**: 6 files (3 price CSVs + 3 trade CSVs) covering Days -2, -1, and 0  
> **Products**: ASH_COATED_OSMIUM (ACO) · INTARIAN_PEPPER_ROOT (IPR)  
> **Position limit**: 80 per product  
> **Tick interval**: 100ms (timestamps 0 → 999,900 = 10,000 ticks per day)

---

## 1. Dataset Structure

### Price Files (`prices_round_1_day_X.csv`)
Columns: `day`, `timestamp`, `product`, `bid_price_1-3`, `bid_volume_1-3`, `ask_price_1-3`, `ask_volume_1-3`, `mid_price`, `profit_and_loss`

- ~10,000 rows per product per day (one per tick)
- Up to 3 levels of order book depth per side
- `profit_and_loss` column reads 0.0 for all rows (reference data, not our bot)

### Trade Files (`trades_round_1_day_X.csv`)
Columns: `timestamp`, `buyer`, `seller`, `symbol`, `currency`, `price`, `quantity`

- `buyer`/`seller` fields are blank in all rows (anonymized)
- Currency is always `XIRECS`

---

## 2. ASH_COATED_OSMIUM (ACO) — Detailed Analysis

### 2.1 Price Distribution

| Metric | Day -2 | Day -1 | Day 0 | Cross-day |
|--------|--------|--------|-------|-----------|
| **N ticks** | 9,982 | 9,983 | 9,986 | 29,951 |
| **Mean** | 9,998.17 | 10,000.83 | 10,001.61 | ~10,000.2 |
| **Median** | 9,998.0 | 10,001.0 | 10,002.0 | — |
| **Std dev** | 5.22 | 4.45 | 5.68 | — |
| **Min** | 9,979.0 | 9,982.0 | 9,977.0 | 9,977.0 |
| **Max** | 10,019.0 | 10,019.0 | 10,023.0 | 10,023.0 |

> [!IMPORTANT]
> The daily mean varies from **9,998 to 10,002** across days. A fixed anchor at 10,000 is close but not exact. The mean drifts by ±2 ticks day-to-day. This is small relative to the 16-tick spread.

### 2.2 Mid-Price CDF (Cumulative Distribution)

| Threshold | Day -2 | Day -1 | Day 0 |
|-----------|--------|--------|-------|
| mid ≤ 9,992 | 13.1% | 3.5% | 6.5% |
| mid ≤ 9,994 | 24.0% | 7.3% | 10.8% |
| mid ≤ 9,996 | 39.2% | 14.3% | 16.0% |
| mid ≤ 9,998 | 54.3% | 26.5% | 25.6% |
| mid ≤ 10,000 | 66.4% | 44.3% | 37.2% |
| mid ≤ 10,002 | 78.1% | 66.2% | 56.2% |
| mid ≤ 10,004 | 87.7% | 81.6% | 71.0% |
| mid ≤ 10,006 | 94.2% | 90.0% | 82.0% |
| mid ≤ 10,008 | 97.5% | 95.5% | 89.0% |

Day -2 skews below 10,000 (median 9,998), Day 0 skews above (median 10,002).

### 2.3 Autocorrelation Structure

| Lag | Day -2 | Day -1 | Day 0 | Interpretation |
|-----|--------|--------|-------|----------------|
| **1** | **-0.5002** | **-0.4978** | **-0.4869** | Strong mean reversion |
| 2 | 0.0107 | -0.0012 | -0.0154 | No signal |
| 5 | -0.0034 | -0.0074 | -0.0036 | No signal |
| 10 | 0.0138 | -0.0120 | -0.0188 | No signal |

> [!TIP]
> **The lag-1 autocorrelation of -0.50 is the single most important statistical property of ACO.** It means every price move is expected to reverse by 50% on the next tick. This is extremely favorable for market making — fills on one side predict profitable fills on the other side within 1-2 ticks. Lag ≥2 autocorrelation is essentially zero, meaning there is no multi-step predictability.

### 2.4 Return Distribution

| Metric | Day -2 | Day -1 | Day 0 |
|--------|--------|--------|-------|
| Mean return | -0.0017 | -0.0001 | -0.0006 |
| Std dev | 3.77 | 3.72 | 3.69 |
| Min | -21 | -21 | -19 |
| Max | +21 | +19 | +20 |
| \|return\| > 5 | 15.99% | 15.95% | 15.68% |
| \|return\| > 10 | 1.88% | 1.68% | 1.82% |
| Skewness | 0.004 | -0.084 | -0.010 |
| Excess kurtosis | 2.955 | 2.862 | 2.822 |

> [!NOTE]
> Returns are symmetric (skew ≈ 0) with **fat tails** (excess kurtosis ~2.9, well above the normal distribution's 0). This means large moves (>10 ticks) occur ~1.8% of the time — roughly 180 ticks per day. The fat tails justify having wide L3/L4 backstop quotes to capture extreme dislocations.

### 2.5 Mean Reversion Speed

When price deviates from the daily mean, how many ticks until it reverts?

| Deviation | Day -2 | Day -1 | Day 0 |
|-----------|--------|--------|-------|
| ≥ 2 ticks | 15.7 ticks | 13.0 ticks | 17.7 ticks |
| ≥ 4 ticks | 9.4 ticks | 8.0 ticks | 13.3 ticks |
| ≥ 6 ticks | 7.1 ticks | 5.5 ticks | 12.0 ticks |
| ≥ 8 ticks | 3.9 ticks | 2.2 ticks | 10.5 ticks |

Larger deviations revert *faster* (in fewer ticks), confirming the mean-reversion structure. Day 0 shows slower reversion — possibly higher volatility regime.

### 2.6 Intraday Patterns (by Time Quartile)

| | Day -2 | Day -1 | Day 0 |
|--|--------|--------|-------|
| **Q1** (0–25%) | mean=10,000.1, σ=4.57 | mean=10,000.2, σ=3.60 | mean=10,001.1, σ=4.10 |
| **Q2** (25–50%) | mean=9,998.1, σ=5.73 | mean=10,002.5, σ=3.97 | mean=10,001.6, σ=3.60 |
| **Q3** (50–75%) | mean=9,995.4, σ=4.00 | mean=10,001.9, σ=4.74 | mean=10,000.4, σ=7.96 |
| **Q4** (75–100%) | mean=9,999.1, σ=5.19 | mean=9,998.8, σ=4.44 | mean=10,003.3, σ=5.64 |

No consistent intraday drift pattern — the mean wanders within ±4 ticks of 10,000 across all quartiles. Day 0 Q3 shows elevated volatility (σ=7.96).

---

## 3. ACO Order Book Microstructure

### 3.1 Spread Distribution

| Spread (ticks) | Frequency | % |
|----------------|-----------|---|
| 5 | 154 | 0.6% |
| 6 | 328 | 1.2% |
| 7 | 164 | 0.6% |
| 9 | 375 | 1.4% |
| 10 | 639 | 2.3% |
| 11 | 323 | 1.2% |
| 13 | 156 | 0.6% |
| **16** | **17,599** | **63.7%** |
| 18 | 3,452 | 12.5% |
| 19 | 3,514 | 12.7% |
| 21 | 666 | 2.4% |

> [!IMPORTANT]
> **The spread is 16 ticks in 64% of observations.** This is the "resting" state of the order book. Tight spreads (<16) occur only 8.4% of the time and represent moments when a market participant has stepped inside.

### 3.2 L1 Volume

| Metric | Day -2 | Day -1 | Day 0 |
|--------|--------|--------|-------|
| L1 bid size (mean) | 13.5 | 13.6 | 13.6 |
| L1 bid size (median) | 13 | 13 | 13 |
| L1 ask size (mean) | 13.6 | 13.6 | 13.6 |
| L1 ask size (median) | 13 | 13 | 13 |

L1 volume is symmetric and stable at ~13 lots per side.

### 3.3 Most Frequent Bid/Ask Price Levels

**Day -2** (mean=9,998): Bids cluster at 9986–9994, asks at 10002–10009  
**Day -1** (mean=10,001): Bids cluster at 9991–9996, asks at 10007–10012  
**Day 0** (mean=10,002): Bids cluster at 9991–9997, asks at 10008–10014  

The bid/ask clusters shift with the daily mean, confirming the mean-reversion center drifts.

### 3.4 Bid at Various Prices — Fill Probability

How often is the market's best bid at or above a given price (proxy for passive fill probability):

| Price | Day -2 | Day -1 | Day 0 |
|-------|--------|--------|-------|
| 9,993 | 31.1% | 50.7% | 58.6% |
| 9,994 | 25.0% | 39.9% | 49.3% |
| 9,995 | 19.2% | 29.0% | 39.1% |
| 9,996 | 14.3% | 21.0% | 30.9% |
| 9,997 | 10.0% | 14.7% | 25.6% |
| 9,998 | 6.7% | 10.8% | 19.9% |
| 9,999 | 4.3% | 7.6% | 15.4% |
| 10,000 | 2.8% | 4.9% | 11.9% |

> [!TIP]
> A bid placed at 9,993 (= typical best_bid + 1) has a 31-59% chance of being at/above the best bid, giving it priority queue position. This is why L1 at best_bid+1 is the optimal placement — it minimizes opportunity cost while maintaining good edge (7 ticks from FV=10,000).

---

## 4. ACO Trading Signal Analysis

### 4.1 Order Book Imbalance

**Definition**: `imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol)`

Does imbalance predict the next-tick price move?

| Threshold | Day -2 | Day -1 | Day 0 | Interpretation |
|-----------|--------|--------|-------|----------------|
| \|imb\| > 0.1 | 48.0% | 46.1% | 46.1% | ❌ **Anti-predictive** |
| \|imb\| > 0.2 | 57.6% | 55.1% | 56.1% | ⚠️ Barely predictive |
| \|imb\| > 0.3 | **70.7%** | **69.4%** | **70.4%** | ✅ Clearly predictive |
| \|imb\| > 0.5 | **76.4%** | **75.4%** | **75.3%** | ✅ Strongly predictive |

> [!WARNING]
> At low thresholds (\|imb\| < 0.2), the imbalance signal is **worse than random** (46% accuracy). Using it ungated adds noise to the fair value estimate. Gating at \|imb\| > 0.3 ensures we only act on signals with **70%+ accuracy**, which is stable across all 3 days.

**Signal volume per day**: ~4,400 signals at >0.1, ~2,300 at >0.3, ~1,300 at >0.5

### 4.2 Extreme Zone Mean Reversion (Buy Side)

Expected future return when mid falls to various thresholds:

| Threshold | Day -2 (n) | +1 tick | +10 ticks | +50 ticks |
|-----------|-----------|---------|-----------|-----------|
| mid ≤ 9,994 | 2,392 | +1.59 | +1.65 | +2.01 |
| mid ≤ 9,995 | 3,072 | +1.31 | +1.35 | +1.64 |
| mid ≤ 9,996 | 3,900 | +1.11 | +1.18 | +1.44 |
| mid ≤ 9,997 | 4,718 | +0.95 | +0.97 | +1.24 |

| Threshold | Day -1 (n) | +1 tick | +10 ticks | +50 ticks |
|-----------|-----------|---------|-----------|-----------|
| mid ≤ 9,994 | 724 | +3.61 | +3.78 | +4.51 |
| mid ≤ 9,995 | 1,009 | +2.91 | +3.22 | +3.72 |
| mid ≤ 9,996 | 1,430 | +2.37 | +2.56 | +3.14 |
| mid ≤ 9,997 | 1,988 | +1.84 | +2.05 | +2.59 |

| Threshold | Day 0 (n) | +1 tick | +10 ticks | +50 ticks |
|-----------|----------|---------|-----------|-----------|
| mid ≤ 9,994 | 1,074 | +2.09 | +2.26 | +2.57 |
| mid ≤ 9,995 | 1,289 | +2.04 | +2.17 | +2.49 |
| mid ≤ 9,996 | 1,600 | +1.86 | +2.03 | +2.35 |
| mid ≤ 9,997 | 2,044 | +1.63 | +1.74 | +2.15 |

> [!TIP]
> Buying when mid ≤ 9,996 has a consistent positive expected return of +1.1 to +2.4 at +1 tick and +1.4 to +3.1 at +50 ticks. This confirms the extreme zone's stat-arb edge is **genuine and robust** across all days.

### 4.3 Extreme Zone Mean Reversion (Sell Side)

Expected future return when mid rises to various thresholds:

| Threshold | Day -2 (n) | +1 tick | +10 ticks | +50 ticks |
|-----------|-----------|---------|-----------|-----------|
| mid ≥ 10,004 | 1,611 | -1.91 | -1.99 | -2.42 |
| mid ≥ 10,005 | 1,154 | -2.34 | -2.46 | -3.05 |
| mid ≥ 10,006 | 814 | -2.82 | -2.94 | -3.67 |
| mid ≥ 10,007 | 537 | -3.44 | -3.48 | -4.45 |

| Threshold | Day -1 (n) | +1 tick | +10 ticks | +50 ticks |
|-----------|-----------|---------|-----------|-----------|
| mid ≥ 10,004 | 2,348 | -1.80 | -1.88 | -2.41 |
| mid ≥ 10,005 | 1,720 | -2.27 | -2.39 | -2.90 |
| mid ≥ 10,006 | 1,281 | -2.67 | -2.78 | -3.27 |
| mid ≥ 10,007 | 930 | -3.26 | -3.29 | -3.72 |

| Threshold | Day 0 (n) | +1 tick | +10 ticks | +50 ticks |
|-----------|----------|---------|-----------|-----------|
| mid ≥ 10,004 | 3,352 | -1.16 | -1.31 | -1.67 |
| mid ≥ 10,005 | 2,739 | -1.29 | -1.48 | -1.79 |
| mid ≥ 10,006 | 2,170 | -1.51 | -1.68 | -2.05 |
| mid ≥ 10,007 | 1,702 | -1.77 | -1.85 | -2.27 |

Both sides show consistent mean reversion. Negative returns after high mids and positive returns after low mids confirm the stat-arb structure.

### 4.4 Extreme Zone Firing Frequency

| Zone | Day -2 | Day -1 | Day 0 |
|------|--------|--------|-------|
| mid ≤ 9,996 (buy) | 3,909 (39.2%) | 1,430 (14.3%) | 1,600 (16.0%) |
| mid ≥ 10,006 (sell) | 814 (8.2%) | 1,281 (12.8%) | 2,179 (21.8%) |

> [!NOTE]
> The buy zone fires **much more** on Day -2 (mean=9,998) and the sell zone fires **much more** on Day 0 (mean=10,002). The asymmetry tracks the daily mean drift. This is inherent to fixed-threshold zones around 10,000.

### 4.5 Take-Edge Layer Frequency

How often does `best_ask ≤ FV - edge` or `best_bid ≥ FV + edge` trigger?

| Edge | Day -2 | Day -1 | Day 0 |
|------|--------|--------|-------|
| 1 tick | 103 (1.1%) | 72 (0.8%) | 105 (1.1%) |
| **2 ticks** (current) | **63 (0.7%)** | **41 (0.4%)** | **72 (0.8%)** |
| 3 ticks | 27 (0.3%) | 14 (0.2%) | 38 (0.4%) |

The take-edge layer fires on <1% of ticks. It's a rare but profitable event (2+ tick guaranteed edge).

---

## 5. ACO Quote Placement Analysis

### 5.1 Current V6 Quote Levels (typical spread=16)

With `best_bid=9992`, `best_ask=10008`, `FV≈10000`:

| Level | Bid | Ask | Spread | Edge/side |
|-------|-----|-----|--------|-----------|
| **L1** | 9,993 | 10,007 | 14 | 7 |
| **L2** | 9,991 | 10,009 | 18 | 9 |
| **L3** | 9,989 | 10,011 | 22 | 11 |
| **L4** | 9,987 | 10,013 | 26 | 13 |

### 5.2 Quote Sizing and Capacity

| Level | Size per side | Cumulative | Utilization |
|-------|-------------|------------|-------------|
| L1 | 30 | 30 / 80 | 37.5% |
| L2 | 18 | 48 / 80 | 60.0% |
| L3 | 12 | 60 / 80 | 75.0% |
| L4 | remaining (~20) | 80 / 80 | **100%** |

> [!NOTE]
> V4 used only 55/80 lots per side (69% utilization). V6 adds L4 to capture the remaining 25 lots at a very wide spread (26 ticks). These have minimal fill probability but capture extreme tail events for **zero marginal cost**.

### 5.3 Why Behind-Book L2/L3 Works Better Than Inside-Spread

With autocorrelation = **-0.50**, behind-book quotes are optimal:

1. When someone sells to our L2 bid at 9,991 (pushing price down), the next tick **rebounds** up with 50% probability.
2. Our ask at 10,009 becomes more likely to fill → completing a round trip at **18-tick edge**.
3. The wider the quote spread, the **more edge per round trip**.

**V5 failed** by placing L2 inside the spread at fv±3 (9,996/10,004):
- Only 8-tick spread → 4 edge per side (half of behind-book)
- These quotes became the **first target** for aggressive participants (adverse selection)
- Easy to fill on one side, hard to complete the round trip

---

## 6. INTARIAN_PEPPER_ROOT (IPR) — Detailed Analysis

### 6.1 Price Trajectory

| Metric | Day -2 | Day -1 | Day 0 |
|--------|--------|--------|-------|
| Start mid | 9,998.5 | 10,998.5 | 11,998.5 |
| End mid | 11,001.5 | 11,998.0 | 13,000.0 |
| **Daily drift** | **+1,003.0** | **+999.5** | **+1,001.5** |
| Drift per tick | +0.1005 | +0.1001 | +0.1004 |

> [!IMPORTANT]
> IPR trends **up by exactly ~1,000 per day** with extraordinary consistency. The drift rate is 0.100 per tick (±0.0005 variance across days). This is a pure trending asset — the only optimal strategy is **buy-and-hold at maximum position (80 units)**.

### 6.2 Spread & Volume

| Metric | Day -2 | Day -1 | Day 0 |
|--------|--------|--------|-------|
| Mean spread | 12.0 | 13.0 | 14.1 |
| Median spread | 12 | 13 | 14 |
| Min spread | 2 | 2 | 2 |
| Max spread | 18 | 19 | 21 |
| L1 bid vol (mean) | 11.5 | 11.5 | 11.6 |
| L1 ask vol (mean) | 11.5 | 11.5 | 11.5 |

IPR spreads **widen over days** (12 → 14), tracking the increasing price level. L1 volume is stable at ~11.5 lots per side.

### 6.3 Buy-and-Hold PnL (Theoretical Maximum)

| Day | First ask | Final mid | Gain/unit | 80-unit PnL |
|-----|-----------|-----------|-----------|-------------|
| -2 | 10,005 | 11,002 | 996 | 79,720 |
| -1 | 11,006 | 11,998 | 992 | 79,360 |
| 0 | 12,006 | 13,000 | 994 | 79,520 |

The theoretical maximum from IPR (buying 80 at first ask, holding to end) is ~79,500 per day. Any strategy that fails to reach max position quickly leaves significant value on the table.

---

## 7. Trade Activity Analysis

### 7.1 Trade Volume

| Product | Total trades (3 days) | Avg size | Total volume | Max size |
|---------|----------------------|----------|--------------|----------|
| ACO | 1,265 | 5.2 | 6,593 | 10 |
| IPR | 1,011 | 5.2 | 5,230 | 8 |

### 7.2 Trade Size Distribution

**ACO:**

| Size | Count | % |
|------|-------|---|
| 2 | 160 | 12.6% |
| 3 | 179 | 14.2% |
| 4 | 172 | 13.6% |
| 5 | 224 | 17.7% |
| 6 | 230 | 18.2% |
| 7 | 78 | 6.2% |
| 8 | 71 | 5.6% |
| 9 | 76 | 6.0% |
| 10 | 75 | 5.9% |

**IPR:**

| Size | Count | % |
|------|-------|---|
| 3 | 198 | 19.6% |
| 4 | 161 | 15.9% |
| 5 | 195 | 19.3% |
| 6 | 219 | 21.7% |
| 7 | 195 | 19.3% |
| 8 | 42 | 4.2% |

ACO trades range 2-10 lots (uniform-ish), IPR trades range 3-8 lots (peaked at 6). These are likely **bot-to-bot fills** from the competition's market-making bots.

### 7.3 Trade Timing

| Day | Product | Trades | First trade | Last trade | Avg gap |
|-----|---------|--------|-------------|------------|---------|
| -2 | ACO | 429 | t=700 | t=995,300 | 2,346 |
| -2 | IPR | 344 | t=1,000 | t=997,500 | 2,922 |
| -1 | ACO | 425 | t=2,800 | t=997,800 | 2,380 |
| -1 | IPR | 335 | t=3,000 | t=998,300 | 2,980 |
| 0 | ACO | 411 | t=6,300 | t=998,400 | 2,438 |
| 0 | IPR | 332 | t=200 | t=998,400 | 3,034 |

Trades occur roughly every **2,300–3,000 ticks** (~every 4-5 minutes of simulated time). ACO trades slightly more frequently than IPR.

---

## 8. Key Strategic Insights

### 8.1 ACO Market Making — What Matters

1. **Autocorrelation = -0.50** is the primary edge. Every price move reverses by 50% on the next tick. This guarantees profitable round trips when quoting on both sides.

2. **Spread = 16 (64%)** is the natural resting state. Quoting at best_bid+1/best_ask-1 gives a 14-tick spread (7 per side edge). This is the optimal L1 placement.

3. **Behind-book L2/L3** outperform inside-spread quotes because the autocorrelation rewards wide spreads — fills at extreme prices revert strongly, enabling high-edge round trips.

4. **Extreme zones (mid ≤ 9,996 / ≥ 10,006)** have genuine stat-arb edge of +1.1 to +3.6 ticks at +1 tick (consistent across all days).

5. **Imbalance signal** is only useful when \|imbalance\| > 0.3 (70%+ accuracy). Below that, it's anti-predictive and adds noise.

### 8.2 IPR Trending — What Matters

1. **Drift = +0.100/tick** is perfectly consistent across all 3 days.
2. **Every tick not at max position (80) costs ~8 XIRECs** (80 × 0.1) in missed gains.
3. **Buy immediately, hold forever, never sell** is the only rational strategy.
4. **Backstop bids** at ask level ensure fastest possible re-fill when the ask book is thin.

### 8.3 Robustness Considerations for Unseen Data

| Property | Observed stability | Risk on unseen data |
|----------|-------------------|---------------------|
| ACO autocorr ≈ -0.50 | ±0.01 across 3 days | **Low** — structural market property |
| ACO mean ≈ 10,000 | ±2 across 3 days | **Low** — 50% anchor weight handles this |
| ACO spread = 16 | 64% consistency | **Low** — market structure |
| IPR drift = +1,000/day | ±3.5 across 3 days | **Low** — extremely stable |
| Imbalance gate at 0.3 | 69-71% accuracy | **Low** — stable across all days |
| L1 volume ≈ 13 lots | ±0.5 across days | **Low** — symmetric and stable |

---

## 9. FV Estimation Error Analysis

Fair Value is computed as `FV = 0.50 × 10,000 + 0.50 × EMA(α=0.20)`

Mean absolute error of FV from the true daily mean:

| Anchor strategy | Day -2 | Day -1 | Day 0 |
|-----------------|--------|--------|-------|
| Fixed 10,000 | 1.975 | 1.459 | 2.032 |
| Running mean | 2.275 | 1.582 | 1.979 |
| Slow EMA (α=0.005) | 3.034 | 1.980 | 2.879 |

> [!NOTE]
> The **fixed anchor at 10,000 actually outperforms** adaptive anchors on Days -2 and -1, and is competitive on Day 0. This is because the daily mean stays within ±2 of 10,000, and the EMA component (50% weight) already provides short-term tracking. No anchor change is warranted.

---

## 10. File Summary

| File | Size | Rows (ACO) | Rows (IPR) |
|------|------|------------|------------|
| `prices_round_1_day_-2.csv` | 1.50 MB | 9,982 | 9,984 |
| `prices_round_1_day_-1.csv` | 1.49 MB | 9,983 | 9,983 |
| `prices_round_1_day_0.csv` | 1.48 MB | 9,986 | 9,979 |
| `trades_round_1_day_-2.csv` | 34 KB | 429 | 344 |
| `trades_round_1_day_-1.csv` | 35 KB | 425 | 335 |
| `trades_round_1_day_0.csv` | 33 KB | 411 | 332 |
