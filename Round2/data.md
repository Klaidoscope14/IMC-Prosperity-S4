# Round 2 — Comprehensive Data Analysis

## 1. Data Overview

### Files

| File | Rows | Size |
|------|------|------|
| `prices_round_2_day_-1.csv` | 20,000 | 1.5 MB |
| `prices_round_2_day_0.csv` | 20,000 | 1.5 MB |
| `prices_round_2_day_1.csv` | 20,000 | 1.5 MB |
| `trades_round_2_day_-1.csv` | 790 | 35 KB |
| `trades_round_2_day_0.csv` | 803 | 36 KB |
| `trades_round_2_day_1.csv` | 798 | 36 KB |
| `trader.py` | 536 lines | 24 KB |

### Products

Same two products as Round 1:

| Product | Position Limit | Behaviour |
|---------|---------------|-----------|
| **ASH_COATED_OSMIUM (ACO)** | 80 | Mean-reverting around ~10,000 |
| **INTARIAN_PEPPER_ROOT (IPR)** | 80 | Trending upward ~+1,000/day |

### Tick Structure

- **10,000 ticks per day** per product (20,000 rows total per day)
- **Tick spacing**: Uniform 100ms gaps (timestamps 0 → 999,900)
- **3 days of data**: Day -1, Day 0, Day 1

> **IMPORTANT**: **Round 2 introduces the `bid()` method** — only relevant for Round 2 per `Rules.md`. The current `trader.py` returns `bid() → 10000`. This likely relates to an **auction clearing price mechanism** for ACO.

---

## 2. Round 1 vs Round 2 Comparison

> **NOTE**: **Round 2 data is NOT identical to Round 1** — they are different market realizations drawn from the same underlying distributions. Despite having overlapping day labels (Day -1, Day 0), every row differs in price levels and volumes.

### Key Metric Comparison

| Metric | Round 1 (3 days) | Round 2 (3 days) | Change |
|--------|:---:|:---:|:---:|
| **ACO Mean Price** | ~10,000 | ~10,001 | **Same** |
| **ACO Tick-to-Tick Std** | 3.72–3.77 | 3.69–3.70 | **Same** |
| **ACO Mean Spread** | 16.15–16.19 | 16.22–16.25 | **Same** |
| **IPR Daily Drift** | +999 to +1,003 | +998 to +1,002 | **Same** |
| **IPR Tick-to-Tick Std** | 2.82–3.33 | 3.11–3.58 | **Slightly higher** |
| **IPR Mean Spread** | 11.99–14.13 | 13.07–15.18 | **Slightly wider** |

**Conclusion**: The market microstructure is identical across rounds. **IPR spread widens as price increases** (approximately +1 per 1,000 in price).

---

## 3. ASH_COATED_OSMIUM (ACO) — Detailed Analysis

### 3.1 Price Statistics (excluding empty-book ticks)

| Metric | Day -1 | Day 0 | Day 1 |
|--------|:---:|:---:|:---:|
| **N (valid ticks)** | 9,985 | 9,984 | 9,978 |
| **Mean** | 10,000.83 | 10,001.61 | 10,000.21 |
| **Median** | 10,001.00 | 10,002.00 | 10,000.00 |
| **Min** | 9,981.00 | 9,979.00 | 9,980.00 |
| **Max** | 10,020.00 | 10,023.00 | 10,019.00 |
| **Open** | 9,991.00 | 10,003.00 | 10,008.00 |
| **Close** | 10,002.00 | 10,008.00 | 9,993.00 |
| **Intraday Drift** | +11.00 | +5.00 | -15.00 |

### 3.2 Price Distribution Around 10,000

| Day | Above 10k | At 10k | Below 10k | Mean Deviation |
|-----|:---------:|:------:|:---------:|:--------------:|
| -1 | 55.4% | 8.2% | 36.4% | +0.83 |
| 0 | 62.7% | 5.6% | 31.7% | +1.61 |
| 1 | 48.7% | 6.5% | 44.8% | +0.21 |

> **TIP**: ACO has a **slight positive bias** (mean consistently above 10,000). Consider setting anchor at **10,001** instead of 10,000.

### 3.3 Percentile Distribution

| Percentile | Day -1 | Day 0 | Day 1 |
|:----------:|:------:|:-----:|:-----:|
| 1% | 9,990 | 9,987 | 9,989 |
| 5% | 9,993 | 9,992 | 9,992 |
| 25% | 9,998 | 9,999 | 9,997 |
| **50%** | **10,001** | **10,002** | **10,000** |
| 75% | 10,004 | 10,005 | 10,004 |
| 95% | 10,008 | 10,011 | 10,009 |
| 99% | 10,012 | 10,015 | 10,012 |

> **NOTE**: **99% of prices fall within [9,987 – 10,015]** — a ~28-tick range. The IQR is approximately **6–7 ticks wide**.

### 3.4 Volatility

| Metric | Day -1 | Day 0 | Day 1 |
|--------|:------:|:-----:|:-----:|
| **Std (tick returns)** | 3.70 | 3.69 | 3.69 |
| **Mean \|Return\|** | 2.23 | 2.21 | 2.22 |
| **Max Up** | +21.00 | +21.00 | +19.00 |
| **Max Down** | -18.00 | -21.00 | -19.00 |
| **Lag-1 Autocorrelation** | **-0.506** | **-0.506** | **-0.491** |

> **⚠️ CRITICAL FINDING**: **Strong mean-reversion signal** — Lag-1 autocorrelation is approximately **-0.50** across all days. This means each tick return is ~50% reversed on the next tick. This is the strongest statistical edge in the data.

### 3.5 Bid-Ask Spread

| Day | Mean | Median | Min | Max |
|-----|:----:|:------:|:---:|:---:|
| -1 | 16.22 | 16.00 | 5 | 21 |
| 0 | 16.25 | 16.00 | 5 | 21 |
| 1 | 16.23 | 16.00 | 5 | 22 |

#### Spread Distribution (all days combined)

| Spread | Frequency | % |
|:------:|:---------:|:---:|
| **16** | 17,644 | **58.8%** |
| **18** | 3,477 | 11.6% |
| **19** | 3,599 | 12.0% |
| **21** | 717 | 2.4% |
| **10** | 607 | 2.0% |
| 5-9 | ~1,100 | 3.7% |
| Others | ~2,856 | 9.5% |

> **NOTE**: The **modal spread is exactly 16** (58.8% of the time). This is the market maker's "natural" spread. Tight spreads (5-9) occur ~4% of the time, representing potential liquidity-taking opportunities.

### 3.6 Top Bid/Ask Price Levels (all days)

**Most Frequent Bids:**

| Price | Count |
|:-----:|:-----:|
| 9,993 | 2,896 |
| 9,994 | 2,767 |
| 9,992 | 2,589 |
| 9,991 | 2,314 |
| 9,995 | 2,217 |

**Most Frequent Asks:**

| Price | Count |
|:-----:|:-----:|
| 10,010 | 2,934 |
| 10,009 | 2,842 |
| 10,011 | 2,491 |
| 10,008 | 2,437 |
| 10,012 | 2,089 |

> **TIP**: The book is **asymmetric**: bids cluster at 9,991-9,995 while asks cluster at 10,008-10,012. The gap between bid and ask clusters (~13-17 ticks) confirms the wide natural spread. **Best quoting zone**: bid at 9,996-9,999, ask at 10,001-10,007 (inside the natural spread).

### 3.7 Order Book Depth

| Metric | Day -1 | Day 0 | Day 1 |
|--------|:------:|:-----:|:-----:|
| L1 Bid Volume (mean) | 14.2 | 14.3 | 14.2 |
| L1 Ask Volume (mean) | 14.2 | 14.2 | 14.2 |
| Total Bid Volume (mean) | 30.2 | 30.1 | 30.2 |
| Total Ask Volume (mean) | 30.1 | 30.4 | 30.4 |
| **L2 present** | 87.6% | 87.9% | 88.5% |
| **L3 present** | 4.9% | 4.8% | 4.7% |

**Level gap structure:**

| Gap | Mean (Bid) | Mean (Ask) |
|-----|:----------:|:----------:|
| L1 → L2 | 2.75 ticks | 2.82 ticks |
| L2 → L3 | 2.51 ticks | 2.54 ticks |

### 3.8 Order Book Imbalance (OBI)

| Day | Mean OBI | Std OBI | Min | Max |
|-----|:--------:|:-------:|:---:|:---:|
| -1 | +0.001 | 0.377 | -1.000 | +1.000 |
| 0 | -0.005 | 0.375 | -1.000 | +1.000 |
| 1 | -0.004 | 0.378 | -1.000 | +1.000 |

> **NOTE**: OBI is centered around zero with high variance (std ≈ 0.38). **OBI is not a reliable signal for ACO** — the mean is essentially zero across all days. The imbalance swings from -1 to +1 regularly.

### 3.9 One-Sided Book Events

| Day | Both Sides | Bid Only | Ask Only | Neither | Total |
|-----|:----------:|:--------:|:--------:|:-------:|:-----:|
| -1 | 9,237 | 375 | 373 | 15 | 10,000 |
| 0 | 9,257 | 357 | 370 | 16 | 10,000 |
| 1 | 9,214 | 364 | 400 | 22 | 10,000 |

> **WARNING**: **~7.5% of ticks have a one-sided book** (only bids or only asks present). This means `mid_price` is unreliable on those ticks. Your algorithm must handle missing bid or ask gracefully.

### 3.10 Cross-Day Continuity

| Transition | Gap |
|------------|:---:|
| Day -1 close → Day 0 open | +1.00 |
| Day 0 close → Day 1 open | 0.00 |

> **TIP**: **ACO has near-perfect cross-day continuity** — virtually no overnight gaps. The anchor can persist across days without reset.

---

## 4. INTARIAN_PEPPER_ROOT (IPR) — Detailed Analysis

### 4.1 Price Statistics (excluding empty-book ticks)

| Metric | Day -1 | Day 0 | Day 1 |
|--------|:------:|:-----:|:-----:|
| **N (valid ticks)** | 9,987 | 9,982 | 9,984 |
| **Mean** | 11,500.12 | 12,499.87 | 13,500.06 |
| **Median** | 11,500.00 | 12,500.00 | 13,500.50 |
| **Min** | 10,998.00 | 11,996.00 | 12,995.00 |
| **Max** | 12,001.50 | 13,008.00 | 14,003.00 |
| **Open** | 11,001.50 | 11,998.50 | 13,000.00 |
| **Close** | 11,999.50 | 13,000.00 | 13,999.50 |
| **Intraday Drift** | **+998.00** | **+1,001.50** | **+999.50** |

### 4.2 Daily Drift Analysis

| Day | Open | Close | Drift | Drift/tick |
|-----|:----:|:-----:|:-----:|:----------:|
| -1 | 11,001.50 | 11,999.50 | +998.00 | +0.100 |
| 0 | 11,998.50 | 13,000.00 | +1,001.50 | +0.100 |
| 1 | 13,000.00 | 13,999.50 | +999.50 | +0.100 |

> **⚠️ CRITICAL**: **IPR drifts almost exactly +1,000/day** (+0.100/tick). This is extremely predictable. The optimal strategy is to **hold max long (80 units)** throughout the day.

### 4.3 Cross-Day Continuity

| Transition | Gap |
|------------|:---:|
| Day -1 close → Day 0 open | **-1.00** |
| Day 0 close → Day 1 open | **0.00** |

> **TIP**: **Perfect cross-day continuity** with negligible gaps. IPR price is continuous across days.

### 4.4 Percentile Distribution

| Percentile | Day -1 | Day 0 | Day 1 |
|:----------:|:------:|:-----:|:-----:|
| 1% | 11,010 | 12,010 | 13,010 |
| 5% | 11,049 | 12,049 | 13,048 |
| 25% | 11,251 | 12,249 | 13,251 |
| **50%** | **11,500** | **12,500** | **13,501** |
| 75% | 11,750 | 12,750 | 13,751 |
| 95% | 11,950 | 12,950 | 13,951 |
| 99% | 11,990 | 12,990 | 13,990 |

> **NOTE**: The distribution is **nearly perfectly uniform** within each day due to the linear trend. IQR spans ~500 ticks (half the daily range).

### 4.5 Volatility

| Metric | Day -1 | Day 0 | Day 1 |
|--------|:------:|:-----:|:-----:|
| **Std (tick returns)** | 3.11 | 3.32 | 3.58 |
| **Mean \|Return\|** | 1.88 | 2.00 | 2.16 |
| **Max Up** | +18.00 | +17.00 | +21.00 |
| **Max Down** | -15.50 | -17.00 | -18.00 |
| **Lag-1 Autocorrelation** | **-0.498** | **-0.489** | **-0.508** |

> **NOTE**: IPR also shows **strong mean-reversion** (autocorr ≈ -0.50), but with a dominant upward drift. Volatility **increases with price level** (~+0.25 std per 1,000 in price).

### 4.6 Bid-Ask Spread

| Day | Mean | Median | Min | Max |
|-----|:----:|:------:|:---:|:---:|
| -1 | 13.07 | 13.00 | 2 | 19 |
| 0 | 14.12 | 14.00 | 2 | 21 |
| 1 | 15.18 | 15.00 | 2 | 22 |

> **IMPORTANT**: **IPR spread widens as price increases** — approximately **+1 tick per 1,000 in price** (13 → 14 → 15). This means at higher price levels (Day 1), there is slightly less edge per trade.

#### Spread Distribution (Day -1 example)

| Spread | Frequency | % |
|:------:|:---------:|:---:|
| **12** | 3,020 | 30.2% |
| **13** | 3,067 | 30.7% |
| **15** | 1,426 | 14.3% |
| **16** | 996 | 10.0% |
| 2-7 | 312 | 3.1% |
| Others | ~1,179 | 11.7% |

> **NOTE**: IPR has a **bimodal spread** around 12-13 ticks (combined ~61%), narrower than ACO's 16-tick mode. Tight spreads below 5 occur only ~2% of the time.

### 4.7 Order Book Depth

| Metric | Day -1 | Day 0 | Day 1 |
|--------|:------:|:-----:|:-----:|
| L1 Bid Volume (mean) | 11.6 | 11.6 | 11.6 |
| L1 Ask Volume (mean) | 11.6 | 11.6 | 11.6 |
| Total Bid Volume (mean) | 24.2 | 24.1 | 24.3 |
| Total Ask Volume (mean) | 24.0 | 24.1 | 24.2 |
| **L2 present** | 87.1% | 87.0% | 87.5% |
| **L3 present** | 3.0% | 2.8% | 3.0% |

**Level gap structure:**

| Day | Bid L1→L2 | Ask L1→L2 |
|-----|:---------:|:---------:|
| -1 | 3.04 | 3.08 |
| 0 | 3.32 | 3.34 |
| 1 | 3.58 | 3.59 |

> **NOTE**: IPR book depth is **thinner than ACO** (24 total vs 30 total). Level gaps also widen with price (same scaling as the spread).

### 4.8 Order Book Imbalance (OBI)

| Day | Mean OBI | Std OBI |
|-----|:--------:|:-------:|
| -1 | +0.006 | 0.377 |
| 0 | -0.002 | 0.378 |
| 1 | +0.007 | 0.374 |

> **NOTE**: OBI centered at zero despite the strong upward trend. **OBI does not predict IPR direction**.

### 4.9 One-Sided Book Events

| Day | Both Sides | Bid Only | Ask Only | Neither | Total |
|-----|:----------:|:--------:|:--------:|:-------:|:-----:|
| -1 | 9,246 | 383 | 358 | 13 | 10,000 |
| 0 | 9,230 | 361 | 391 | 18 | 10,000 |
| 1 | 9,248 | 398 | 338 | 16 | 10,000 |

---

## 5. Trades Data Analysis

### 5.1 Trade Counts & Volumes

| Day | ACO Trades | ACO Volume | IPR Trades | IPR Volume |
|-----|:----------:|:----------:|:----------:|:----------:|
| -1 | 459 | 2,348 | 331 | 1,669 |
| 0 | 471 | 2,404 | 332 | 1,671 |
| 1 | 465 | 2,375 | 333 | 1,693 |

### 5.2 Trade Price Statistics

| Product | Day | Mean Px | VWAP | Min | Max | Mean(trade-mid) |
|---------|-----|:-------:|:----:|:---:|:---:|:---------------:|
| **ACO** | -1 | 10,000.88 | 10,001.05 | 9,982 | 10,019 | -0.34 |
| **ACO** | 0 | 10,000.98 | 10,001.11 | 9,979 | 10,020 | -0.25 |
| **ACO** | 1 | 10,000.09 | 10,000.29 | 9,980 | 10,018 | -0.08 |
| **IPR** | -1 | 11,540.49 | 11,542.42 | 10,996 | 11,998 | +0.20 |
| **IPR** | 0 | 12,535.24 | 12,538.56 | 11,998 | 12,987 | +0.04 |
| **IPR** | 1 | 13,526.27 | 13,524.38 | 12,998 | 13,999 | -0.08 |

> **NOTE**: **ACO trades happen slightly below mid-price** (mean trade-mid = -0.22), suggesting sellers are slightly more aggressive. **IPR trades are roughly balanced** around mid.

### 5.3 Trade Size Distribution

**ACO:**

| Size | Count/Day | % |
|:----:|:---------:|:---:|
| 2 | ~66 | 14.2% |
| 3 | ~60 | 12.9% |
| 4 | ~70 | 15.1% |
| **5** | **~83** | **17.9%** |
| **6** | **~79** | **17.0%** |
| 7 | 25 | 5.4% |
| 8 | ~36 | 7.7% |
| 9 | ~22 | 4.7% |
| 10 | ~23 | 5.0% |

**IPR:**

| Size | Count/Day | % |
|:----:|:---------:|:---:|
| 3 | ~74 | 22.4% |
| 4 | ~60 | 18.1% |
| 5 | ~62 | 18.7% |
| 6 | ~60 | 18.1% |
| 7 | ~61 | 18.4% |
| 8 | ~15 | 4.5% |

> **NOTE**: ACO trade sizes span **2–10** with mode at 5-6. IPR sizes span **3–8** with a nearly uniform distribution from 3–7. **No buyer/seller identity** is provided in the trade data (both fields are blank).

### 5.4 Trade Timing

| Product | Day | Trade Count | Mean Gap | Min Gap | Max Gap | First Trade | Last Trade |
|---------|-----|:----------:|:--------:|:-------:|:-------:|:-----------:|:----------:|
| **ACO** | -1 | 459 | 2,206 | 100 | 12,100 | t=0 | t=997,000 |
| **ACO** | 0 | 471 | 2,136 | 100 | 10,200 | t=0 | t=995,200 |
| **ACO** | 1 | 465 | 2,187 | 100 | 10,900 | t=0 | t=997,200 |
| **IPR** | -1 | 331 | 3,011 | 100 | 23,400 | t=4,400 | t=995,100 |
| **IPR** | 0 | 332 | 3,009 | 100 | 18,300 | t=4,400 | t=994,400 |
| **IPR** | 1 | 333 | 3,002 | 100 | 20,000 | t=4,400 | t=995,100 |

> **NOTE**:
> - ACO trades roughly every **~22 ticks**. IPR trades every **~30 ticks**.
> - IPR first trade is always at **t=4,400** (never at t=0), suggesting a warm-up period.
> - Trade gaps can be up to **120+ ticks** (12,100 ms), indicating periods of low activity.

---

## 6. Key Strategic Observations

### 6.1 ACO Strategy Implications

| Finding | Implication |
|---------|-------------|
| **Mean ≈ 10,001** (slight positive bias) | Anchor at 10,001 instead of 10,000 |
| **Lag-1 autocorr = -0.50** | Strong mean-reversion; penny-the-book market making is optimal |
| **Modal spread = 16** | Midpoint ≈ 8 ticks of theoretical edge per trade |
| **Bid cluster: 9,991-9,995** | Quote bids at 9,996-9,999 to be inside the natural spread |
| **Ask cluster: 10,008-10,012** | Quote asks at 10,001-10,007 to be inside the natural spread |
| **L2 gap ≈ 2.8 ticks** | Order laddering at 2-3 tick intervals is well-calibrated |
| **7.5% one-sided book** | Must handle missing bids/asks gracefully |
| **Trade-mid bias = -0.22** | Sellers slightly more aggressive; slight buy-side edge |
| **`bid()` method returns 10,000** | Auction clearing mechanism; optimize for favorable clearing price |

### 6.2 IPR Strategy Implications

| Finding | Implication |
|---------|-------------|
| **+1,000/day drift (perfectly linear)** | Hold max long (80 units) ASAP |
| **Drift = +0.10/tick** | Every tick held long earns +0.10 per unit |
| **80 units × 0.10/tick × 10,000 ticks = +80,000/day** | Theoretical max PnL from holding |
| **First trade at t=4,400** | No liquidity in first 44 ticks; accumulate starting from t=0 |
| **Spread = 13-15 ticks** | Accumulation cost: ~6.5-7.5 ticks per unit |
| **80 × 7 = 560 ticks of entry cost** | Negligible vs 80,000/day earnings |
| **Sizes 3-8** | Can accumulate 8 units/execution |
| **Spread widens with price** | Later rounds will have slightly higher entry costs |

### 6.3 Round 2 New Feature: `bid()` Method

> **WARNING**: The `bid()` method is **only relevant in Round 2**. The `trader.py` includes sophisticated auction-related code:
> - `calculate_clearing_price()` — finds auction equilibrium
> - `_calculate_auction_clearing_price()` — simulates clearing with injected orders
> - `_inject_auction_orders()` — strategic order injection to move clearing price
> - `optimize_auction_order()` — finds max volume without adverse price impact
>
> The current `bid()` returns a static 10,000. This may be a **sealed-bid auction** where your bid influences the clearing price of ACO.

---

## 7. Data Quality Notes

| Issue | Count | Impact |
|-------|:-----:|--------|
| **Empty book ticks** (both sides missing) | 15-22/day per product | `mid_price = 0.0`; must filter |
| **One-sided book** (bid only or ask only) | ~370/day per product | Unreliable mid; fallback pricing needed |
| **Missing buyer/seller IDs** | All trades | Cannot identify counterparty patterns |
| **PnL always 0** | All rows | This is bot-perspective data (no positions taken) |

---

## 8. Summary of Critical Numbers

```
ACO Fair Value:     ~10,001 (slight positive bias)  
ACO Spread:         16 ticks (modal), 5-21 range  
ACO Volatility:     3.70 std tick-to-tick  
ACO Autocorrelation: -0.50 (strong mean-reversion)  
ACO Book Depth:     30 lots total (14 at L1)  

IPR Daily Drift:    +1,000/day (+0.10/tick)  
IPR Spread:         13-15 ticks (scales with price)  
IPR Volatility:     3.1-3.6 std tick-to-tick  
IPR Autocorrelation: -0.50 (mean-reverting with drift)  
IPR Book Depth:     24 lots total (12 at L1)  

Position Limit:     80 (both products)  
Ticks/Day:          10,000  
Tick Spacing:       100ms  
```