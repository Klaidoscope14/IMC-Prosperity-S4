# 📊 IMC Prosperity Round 3 — Complete Data Analysis

## 📁 Dataset Overview

| File | Rows | Size |
|------|------|------|
| `prices_round_3_day_0.csv` | 120,000 | ~6.5 MB |
| `trades_round_3_day_0.csv` | 1,308 | ~50 KB |
| `prices_round_3_day_1.csv` | 120,000 | ~6.5 MB |
| `trades_round_3_day_1.csv` | 1,407 | ~50 KB |
| `prices_round_3_day_2.csv` | 120,000 | ~6.5 MB |
| `trades_round_3_day_2.csv` | 1,333 | ~50 KB |

- **12 products**: HYDROGEL_PACK, VELVETFRUIT_EXTRACT, VEV_4000, VEV_4500, VEV_5000, VEV_5100, VEV_5200, VEV_5300, VEV_5400, VEV_5500, VEV_6000, VEV_6500
- **10,000 ticks/product/day** at **100 ms intervals** (uniform across all products)
- **Trades are sparse** (~300–500 trades/day for delta-1, much fewer for most VEVs)

---

## 🟢 Delta-1 Products

### HYDROGEL_PACK

#### Mid-Price Statistics

| Day | Min | Max | Mean | Median | Std Dev | Ticks |
|-----|-----|-----|------|--------|---------|-------|
| Day 0 | 9,928 | 10,071 | 9,990.96 | 9,991 | 25.33 | 10,000 |
| Day 1 | 9,908.5 | 10,079 | 9,992.06 | 9,999 | 37.61 | 10,000 |
| Day 2 | 9,891 | 10,051 | 9,989.4 | 9,993 | 31.62 | 10,000 |
| **All** | **9,891** | **10,079** | **9,990.81** | **9,994** | **31.93** | **30,000** |

> [!IMPORTANT]
> HYDROGEL_PACK is **mean-reverting around ~10,000**. All three days cluster tightly around this level with σ ≈ 32. This is very similar to the ACO (ASH_COATED_OSMIUM) pattern from Round 2 — a classic **market-making target**.

#### Spread Analysis

| Day | Avg Spread | Min Spread | Max Spread | Median Spread |
|-----|-----------|-----------|-----------|--------------|
| Day 0 | 15.70 | 7.0 | 17.0 | 16.0 |
| Day 1 | 15.73 | 7.0 | 17.0 | 16.0 |
| Day 2 | 15.73 | 7.0 | 17.0 | 16.0 |

> [!NOTE]
> The **modal spread is 16 ticks** — extremely consistent across all days. Min spread of 7 occurs rarely. This is a wide spread to capture via market-making.

#### Intraday Volatility

| Day | Max Drawdown |
|-----|-------------|
| Day 0 | 1.42% |
| Day 1 | 1.25% |
| Day 2 | 1.42% |

#### Trade Activity

| Day | Trades | Total Volume | VWAP | Avg Trade Size |
|-----|--------|-------------|------|---------------|
| Day 0 | 324 | 1,349 | 9,990.34 | 4.2 |
| Day 1 | 375 | 1,485 | 9,994.29 | 4.0 |
| Day 2 | 311 | 1,244 | 9,986.96 | 4.0 |

> [!TIP]
> Small trade sizes (~4 units) suggest bots trading in small increments. VWAP tracks very close to mid-price (≈10,000), confirming mean-reverting nature.

#### Price Trajectory

- **Day 0**: Open=10,000 → Close=9,958 (Δ=−42, −0.42%)
- **Day 1**: Open=9,958 → Close=10,015 (Δ=+57, +0.57%)
- **Day 2**: Open=10,011 → Close=10,010 (Δ=−1, −0.01%)

> [!NOTE]
> Clear mean-reversion: Day 0 drops, Day 1 recovers past 10k, Day 2 flat at 10k. **Anchor FV at 10,000.**

#### Order Book Depth

| Day | Avg Bid Vol (L1) | Avg Ask Vol (L1) | Avg Total Depth |
|-----|-----------------|-----------------|----------------|
| Day 0 | 12.37 | 12.36 | 75.19 |
| Day 1 | 12.40 | 12.40 | 75.29 |
| Day 2 | 12.44 | 12.42 | 75.31 |

> [!NOTE]
> Very symmetric L1 book (~12 units each side). Total depth ~75 units. Position limit is 200, so max position ≈ 2.7× total visible depth.

---

### VELVETFRUIT_EXTRACT

#### Mid-Price Statistics

| Day | Min | Max | Mean | Median | Std Dev | Ticks |
|-----|-----|-----|------|--------|---------|-------|
| Day 0 | 5,216.5 | 5,284.5 | 5,246.51 | 5,244.5 | 13.68 | 10,000 |
| Day 1 | 5,198 | 5,283 | 5,248.39 | 5,248.5 | 14.61 | 10,000 |
| Day 2 | 5,207 | 5,300 | 5,255.39 | 5,257.5 | 16.98 | 10,000 |
| **All** | **5,198** | **5,300** | **5,250.10** | **5,249.5** | **15.63** | **30,000** |

> [!IMPORTANT]
> VELVETFRUIT_EXTRACT hovers around **5,250** but shows a **slight upward drift** (Day 0→2: +9 on average). This is the **underlying for all VEV options**, so its trajectory directly drives option pricing.

#### Spread Analysis

| Day | Avg Spread | Min Spread | Max Spread | Median Spread |
|-----|-----------|-----------|-----------|--------------|
| Day 0 | 4.99 | 1.0 | 6.0 | 5.0 |
| Day 1 | 4.98 | 1.0 | 6.0 | 5.0 |
| Day 2 | 4.99 | 1.0 | 6.0 | 5.0 |

> [!TIP]
> Tighter spread than HYDROGEL_PACK (5 vs 16). This means **less room for market-making** but also a more liquid instrument. Consider delta-hedging VEVs with the underlying.

#### Intraday Volatility

| Day | Max Drawdown |
|-----|-------------|
| Day 0 | 1.28% |
| Day 1 | 1.51% |
| Day 2 | 1.57% |

> [!NOTE]
> Volatility is **increasing** day-over-day (drawdown growing). This could be relevant for option pricing — rising realized vol may push up IV.

#### Trade Activity

| Day | Trades | Total Volume | VWAP | Avg Trade Size |
|-----|--------|-------------|------|---------------|
| Day 0 | 445 | 2,689 | 5,246.19 | 6.0 |
| Day 1 | 450 | 2,685 | 5,246.96 | 6.0 |
| Day 2 | 477 | 2,895 | 5,257.57 | 6.1 |

#### Price Trajectory

- **Day 0**: Open=5,250 → Close=5,244 (Δ=−6, −0.11%)
- **Day 1**: Open=5,245 → Close=5,265.5 (Δ=+20.5, +0.39%)
- **Day 2**: Open=5,267.5 → Close=5,295.5 (Δ=+28, +0.53%)

> [!WARNING]
> **Accelerating upward drift**: VE is gaining momentum toward the upper end of its range. By Day 2 close, it's at 5,295.5 — pushing VEV_5200 deeper ITM and VEV_5300 toward ATM.

#### Order Book Depth

| Day | Avg Bid Vol (L1) | Avg Ask Vol (L1) | Avg Total Depth |
|-----|-----------------|-----------------|----------------|
| Day 0 | 37.87 | 37.87 | 120.62 |
| Day 1 | 37.81 | 37.75 | 120.91 |
| Day 2 | 37.80 | 37.79 | 120.66 |

> [!NOTE]
> **3× deeper book** than HYDROGEL_PACK. Very symmetric. Good liquidity for delta-hedging.

---

## 📈 VEV (Velvetfruit Extract Voucher) Options

### Mid-Price Summary by Strike and Day

| VEV | Strike | Day 0 Mid | Day 1 Mid | Day 2 Mid | Day 0→2 Δ |
|-----|--------|----------|----------|----------|----------|
| VEV_4000 | 4,000 | 1,246.52 | 1,248.41 | 1,255.40 | +8.88 |
| VEV_4500 | 4,500 | 746.52 | 748.41 | 755.40 | +8.88 |
| VEV_5000 | 5,000 | 253.26 | 253.26 | 258.54 | +5.28 |
| VEV_5100 | 5,100 | 168.11 | 164.98 | 167.33 | −0.78 |
| VEV_5200 | 5,200 | 97.47 | 95.13 | 94.05 | −3.42 |
| VEV_5300 | 5,300 | 48.89 | 46.91 | 44.48 | −4.41 |
| VEV_5400 | 5,400 | 18.47 | 15.65 | 13.73 | −4.74 |
| VEV_5500 | 5,500 | 8.06 | 6.57 | 5.29 | −2.77 |
| VEV_6000 | 6,000 | 0.50 | 0.50 | 0.50 | 0.00 |
| VEV_6500 | 6,500 | 0.50 | 0.50 | 0.50 | 0.00 |

> [!IMPORTANT]
> **Two distinct regimes:**
> - **Deep ITM (4000, 4500)**: Price tracks underlying 1:1 (delta ≈ 1.0). Gaining value as VE drifts up.
> - **Near ATM (5200–5400)**: Losing value from theta decay despite underlying drift. This is the **battleground** for options trading.
> - **Deep OTM (6000, 6500)**: Pinned at 0.50 (minimum quote). No real trading value.

---

### Moneyness Analysis (relative to VELVETFRUIT_EXTRACT)

Average underlying: Day 0 = 5,246.51 | Day 1 = 5,248.39 | Day 2 = 5,255.39

| VEV | Strike | Day 0 | Day 1 | Day 2 |
|-----|--------|-------|-------|-------|
| VEV_4000 | 4,000 | 23.8% ITM | 23.8% ITM | 23.9% ITM |
| VEV_4500 | 4,500 | 14.2% ITM | 14.3% ITM | 14.4% ITM |
| VEV_5000 | 5,000 | 4.7% ITM | 4.7% ITM | 4.9% ITM |
| VEV_5100 | 5,100 | 2.8% ITM | 2.8% ITM | 3.0% ITM |
| VEV_5200 | 5,200 | 0.9% ITM | 0.9% ITM | 1.1% ITM |
| VEV_5300 | 5,300 | 1.0% OTM | 1.0% OTM | 0.8% OTM |
| VEV_5400 | 5,400 | 2.9% OTM | 2.9% OTM | 2.8% OTM |
| VEV_5500 | 5,500 | 4.8% OTM | 4.8% OTM | 4.7% OTM |
| VEV_6000 | 6,000 | 14.4% OTM | 14.3% OTM | 14.2% OTM |
| VEV_6500 | 6,500 | 23.9% OTM | 23.8% OTM | 23.7% OTM |

> [!NOTE]
> The **ATM boundary** lies between VEV_5200 (slightly ITM) and VEV_5300 (slightly OTM). These are the most interesting for vol trading.

---

### Intrinsic Value vs Market Price (Extrinsic Decomposition)

| VEV | Strike | Day 0 Intrinsic | Day 0 MktMid | Day 0 Extrinsic | Day 2 Intrinsic | Day 2 MktMid | Day 2 Extrinsic |
|-----|--------|---------------|-------------|----------------|---------------|-------------|----------------|
| VEV_4000 | 4,000 | 1,246.51 | 1,246.52 | **0.01** | 1,255.39 | 1,255.40 | **0.01** |
| VEV_4500 | 4,500 | 746.51 | 746.52 | **0.01** | 755.39 | 755.40 | **0.01** |
| VEV_5000 | 5,000 | 246.51 | 253.26 | **6.75** | 255.39 | 258.54 | **3.15** |
| VEV_5100 | 5,100 | 146.51 | 168.11 | **21.60** | 155.39 | 167.33 | **11.94** |
| VEV_5200 | 5,200 | 46.51 | 97.47 | **50.96** | 55.39 | 94.05 | **38.66** |
| VEV_5300 | 5,300 | 0.00 | 48.89 | **48.89** | 0.00 | 44.48 | **44.48** |
| VEV_5400 | 5,400 | 0.00 | 18.47 | **18.47** | 0.00 | 13.73 | **13.73** |
| VEV_5500 | 5,500 | 0.00 | 8.06 | **8.06** | 0.00 | 5.29 | **5.29** |
| VEV_6000 | 6,000 | 0.00 | 0.50 | **0.50** | 0.00 | 0.50 | **0.50** |
| VEV_6500 | 6,500 | 0.00 | 0.50 | **0.50** | 0.00 | 0.50 | **0.50** |

> [!TIP]
> **Theta decay is clearly visible**: VEV_5200 extrinsic dropped from 50.96 → 38.66 (−24%) over 2 days. VEV_5100 dropped from 21.60 → 11.94 (−45%). This creates opportunities for **selling** overpriced time value near ATM.

---

### Implied Volatility Estimation (Black-Scholes)

TTE schedule (Round 3): Day 0 = 5 days, Day 1 = 4 days, Day 2 = 3 days

| VEV | Strike | Day 0 IV | Day 1 IV | Day 2 IV |
|-----|--------|---------|---------|---------|
| VEV_4000 | 4,000 | 64.5% | N/A | N/A |
| VEV_4500 | 4,500 | 37.2% | 42.2% | 48.1% |
| VEV_5000 | 5,000 | 29.7% | 30.9% | 33.2% |
| VEV_5100 | 5,100 | 30.0% | 30.5% | 32.2% |
| VEV_5200 | 5,200 | 29.5% | 31.3% | 33.0% |
| VEV_5300 | 5,300 | 29.5% | 31.6% | 33.7% |
| VEV_5400 | 5,400 | 28.2% | 29.4% | 31.4% |
| VEV_5500 | 5,500 | 30.2% | 31.9% | 34.2% |
| VEV_6000 | 6,000 | 44.9% | 50.1% | 57.3% |
| VEV_6500 | 6,500 | 67.9% | 75.8% | N/A |

> [!IMPORTANT]
> **Key IV observations:**
> 1. **ATM IV ≈ 29–31%** on Day 0, rising to **32–34%** by Day 2 → **implied vol is increasing**
> 2. **Vol smile**: Deep ITM and OTM strikes have inflated IV (64%, 68%) vs ATM (29%). Classic volatility smile.
> 3. **IV is rising across all strikes** day-over-day → market pricing in more uncertainty as TTE shortens (or realized vol is picking up)
> 4. The "flat" ATM region (5000–5500) gives us a clean **~30% IV anchor** for pricing

---

### VEV Bid-Ask Spreads

| VEV | Day 0 Spread | Day 1 Spread | Day 2 Spread |
|-----|-------------|-------------|-------------|
| VEV_4000 | 20.77 | 20.77 | 20.90 |
| VEV_4500 | 15.78 | 15.81 | 15.96 |
| VEV_5000 | 6.00 | 6.01 | 6.12 |
| VEV_5100 | 4.32 | 4.26 | 4.31 |
| VEV_5200 | 2.93 | 2.88 | 2.86 |
| VEV_5300 | 2.16 | 2.11 | 2.05 |
| VEV_5400 | 1.43 | 1.39 | 1.33 |
| VEV_5500 | 1.18 | 1.15 | 1.12 |
| VEV_6000 | 1.00 | 1.00 | 1.00 |
| VEV_6500 | 1.00 | 1.00 | 1.00 |

> [!TIP]
> Spreads scale with option value. **VEV_5200–VEV_5500** have the tightest meaningful spreads (1–3 ticks) and are the most liquid option strikes for market-making.

---

### VEV Trade Activity

| VEV | Day 0 Trades / Vol | Day 1 Trades / Vol | Day 2 Trades / Vol |
|-----|-------------------|-------------------|-------------------|
| VEV_4000 | 172 / 351 | 164 / 333 | 128 / 256 |
| VEV_4500 | 0 / 0 | 1 / 1 | 0 / 0 |
| VEV_5000 | 0 / 0 | 1 / 1 | 0 / 0 |
| VEV_5100 | 0 / 0 | 1 / 1 | 0 / 0 |
| VEV_5200 | 3 / 15 | 7 / 22 | 8 / 26 |
| VEV_5300 | 37 / 128 | 39 / 130 | 45 / 162 |
| VEV_5400 | 64 / 218 | 81 / 286 | 80 / 283 |
| VEV_5500 | 81 / 281 | 92 / 321 | 94 / 335 |
| VEV_6000 | 91 / 320 | 98 / 345 | 95 / 337 |
| VEV_6500 | 91 / 320 | 98 / 345 | 95 / 337 |

> [!WARNING]
> **Extreme liquidity concentration**: VEV_4000 is heavily traded (high volume, deep ITM — delta-1 proxy). VEV_4500/5000/5100 are almost completely **illiquid** (0–1 trades/day). The OTM options (5300–6500) are where the bot activity concentrates. **VEV_6000 and VEV_6500 trade identically** — likely paired bot activity.

---

## 🔗 Cross-Product Correlation

### HYDROGEL_PACK vs VELVETFRUIT_EXTRACT (mid-price correlation)

| Day | Correlation (ρ) | Timestamps |
|-----|----------------|-----------|
| Day 0 | **+0.5001** | 10,000 |
| Day 1 | **+0.1837** | 10,000 |
| Day 2 | **−0.2220** | 10,000 |

> [!IMPORTANT]
> Correlation is **unstable** — ranging from +0.50 to −0.22 across days. These products should be treated as **independent** for position management. No reliable pairs-trading signal.

---

## ⏱️ Timestamp / Tick Structure

- All products: **10,000 ticks per day** at **100 ms intervals** (uniform, no gaps)
- Timestamps: 0 to 999,900

---

## 🧠 Key Observations & Strategy Implications

### 1. HYDROGEL_PACK → **Market-Making**

| Property | Value |
|----------|-------|
| Fair Value Anchor | ~10,000 |
| Spread (modal) | 16 ticks |
| Volatility (σ) | ~32 |
| Position Limit | 200 |
| Mean-Reverting? | ✅ Strong |

**Strategy**: Classic market-making with FV anchor at 10,000. Quote both sides with inventory skew. The 16-tick spread gives ample room for passive edge. Very similar to Round 2's ACO product.

### 2. VELVETFRUIT_EXTRACT → **Delta Hedging + Directional**

| Property | Value |
|----------|-------|
| Price Range | 5,198 – 5,300 |
| Mean | ~5,250 |
| Spread (modal) | 5 ticks |
| Trend | Slight upward drift (+9 avg over 3 days) |
| Position Limit | 200 |

**Strategy**: Primary use is as **delta hedge** for VEV positions. Tighter spread (5 vs 16) means less market-making edge but better for hedging. The upward drift favors long delta exposure.

### 3. VEV Options → **Vol Surface Market-Making**

| Insight | Detail |
|---------|--------|
| ATM IV | ~30% (Day 0) → ~33% (Day 2) |
| Vol Smile | Present — wings elevated |
| Theta Decay | Clearly visible in near-ATM extrinsic |
| Most Liquid | VEV_5300, VEV_5400, VEV_5500 (OTM) |
| Dead Strikes | VEV_4500, VEV_5000, VEV_5100 (no trades) |
| Best Opportunities | VEV_5200–VEV_5400 (highest extrinsic, active trading) |

**Strategy**: 
- Price VEVs using Black-Scholes with **σ ≈ 30%** and TTE decaying each day
- Market-make near-ATM strikes (5200–5400) by quoting around BS fair value
- Capture theta decay by selling overpriced time value
- Delta-hedge with VELVETFRUIT_EXTRACT positions
- Avoid illiquid strikes (4500, 5000, 5100)
- Deep ITM (4000) can be arb'd against underlying if mispriced

### 4. Manual Trading (Bio-Pods)

| Property | Value |
|----------|-------|
| Reserve Price Range | 670 – 920 |
| Step Size | 5 |
| Distribution | Uniform |
| Bids Allowed | 2 |
| Penalty | ((920 − avg_b2) / (920 − b2))³ |

**Strategy**:
- **Bid 1**: Set at 920 (guarantees execution on all reserve prices)
- **Bid 2**: Game theory — need to be above avg(second bids) to avoid penalty. The cubic penalty is severe for bids far below average.
- **Optimal b2**: Slightly above expected average of all participants' second bids. If most are rational, expect convergence around 795–800 (midpoint of reserve range).
