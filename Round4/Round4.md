# 🚀 IMC Prosperity – Round 4: "The More The Merrier"

---

## 🌍 Overview

Round 4 introduces a **major paradigm shift** from previous rounds:

> You are no longer just trading markets — you are trading **participants**.

The **Frontier Trade Watch (FTW)** now provides:
- Full **counterparty identities** (`buyer`, `seller`)
- Historical trade behavior of each participant (Mark IDs)

---

## 🎯 Core Objective

Build a trading system that:

1. **Trades:**
   - `HYDROGEL_PACK`
   - `VELVETFRUIT_EXTRACT`
   - `VELVETFRUIT_EXTRACT_VOUCHER`

2. **Incorporates:**
   - **Counterparty behavior**
   - **Market microstructure**
   - **Options pricing**

3. **Maximizes:**
   - **PnL across simulations**

---

## 🧠 Key Innovation: Counterparty Awareness

Each trade now contains:

```python
trade.buyer
trade.seller
```

👉 **This allows you to:**
- Identify who is trading
- Model their behavior
- Predict future price movement

### 👥 Counterparty Model

All participants are labeled as:
- `Mark XX`

### 🧩 Behavioral Classification

From analysis:

| Type | Behavior |
| :--- | :--- |
| 🟢 **SMART** | Trades predict future price movement |
| ⚪ **NOISE** | Random / weak signal |
| 🔴 **DUMB** | Trades are consistently wrong |

### 📊 Example Signals

| Trader | Behavior |
| :--- | :--- |
| **Mark 14** | Strong positive alpha |
| **Mark 67** | Momentum trader |
| **Mark 49** | Negative alpha |
| **Mark 22** | Extremely wrong (farmable) |
| **Mark 38** | Consistently losing |

### ⚡ Signal Interpretation

| Metric | Meaning |
| :--- | :--- |
| **T+10** | Immediate impact |
| **T+50** | Short-term movement |
| **T+100** | Medium-term movement |

---

## ⚙️ Products

### 🟢 1. Delta-1 Products
- `HYDROGEL_PACK`
- `VELVETFRUIT_EXTRACT`

👉 *Standard trading instruments (spot-like)*

### 🟣 2. Options (VEV)

All vouchers:

| Symbol | Strike |
| :--- | :--- |
| `VEV_4000` | 4000 |
| `VEV_4500` | 4500 |
| `VEV_5000` | 5000 |
| `VEV_5100` | 5100 |
| `VEV_5200` | 5200 |
| `VEV_5300` | 5300 |
| `VEV_5400` | 5400 |
| `VEV_5500` | 5500 |
| `VEV_6000` | 6000 |
| `VEV_6500` | 6500 |

### ⏳ Expiry
All VEVs:
- Total TTE = 7 days
- Round 4 start → TTE = 4 days

### 📦 Position Limits
- `HYDROGEL_PACK`: 200
- `VELVETFRUIT_EXTRACT`: 200
- Each `VEV`: 300

### ⚠️ Market Mechanics
- **Positions:**
  - Do NOT carry forward
  - Are liquidated at hidden fair value
- **Options:**
  - Cannot be exercised early

---

## 🧠 Strategy Layers

### 🔹 1. Price-Based Strategy (R3 carryover)
- Market making
- Spread capture
- Inventory management

### 🔹 2. Options Strategy
- Black-Scholes pricing
- Volatility modeling
- Mispricing detection

### 🔹 3. Counterparty Strategy (NEW)
**Core idea:**
- `IF` smart trader buys → **BUY**
- `IF` dumb trader buys → **SELL**

### 🔹 4. Hybrid Signal
```python
final_signal = (
    w1 * price_signal + 
    w2 * options_signal + 
    w3 * counterparty_signal
)
```

---

## 🔥 High-Impact Strategies

### 🟢 1. Toxic Flow Following
```python
if buyer in SMART:
    BUY
```
👉 *Follow informed traders*

### 🔴 2. Dumb Money Reversal
```python
if buyer in DUMB:
    SELL
```
👉 *Fade bad traders*

### ⚪ 3. Noise Liquidity Capture
- Provide liquidity to noise traders
- Expect mean reversion

### ⚡ 4. Time-Based Exploitation
**Example:**
- Positive at T+10
- Negative at T+100

👉 **Strategy:** Enter → exit → reverse

### 🧩 5. Per-Product Behavior
Same trader ≠ same behavior across products

👉 **Build:** `(trader, product) → signal`

---

## 🏗️ System Architecture

### 🔧 Core Loop
```python
def run(state):
    # 1. Read orderbook
    # 2. Read trades
    
    # 3. Counterparty analysis
    # 4. Price / options signals
    
    # 5. Combine signals
    
    # 6. Place orders
```

### 🔧 Counterparty Module
```python
for trade in state.market_trades[product]:
    buyer = trade.buyer
    seller = trade.seller

    if buyer in SMART:
        signal += +1
    elif buyer in DUMB:
        signal += -1
```

---

## 📊 Data Capsule Usage

**You are given:**
Historical trades with:
- `buyer`
- `seller`
- `price`
- `quantity`

### 🔍 Key Analysis Tasks

**Identify:**
- Trader profitability
- Directional accuracy

**Compute:**
- Post-trade returns (T+10, T+50, T+100)

**Classify traders:**
- SMART / NOISE / DUMB

---

## 🧠 Key Insights

- 🟢 **Insight 1:** Markets are not efficient. Some traders consistently outperform.
- 🔴 **Insight 2:** Bad traders are exploitable. Their trades predict reversals.
- ⚡ **Insight 3:** Timing advantage. Counterparty signals arrive before price moves.
- 🧩 **Insight 4:** Behavior is structured. Traders follow repeatable patterns.

---

## 🚀 Winning Strategy Philosophy

❌ **Old (R3)**
- React to price
- Assume market efficiency

✅ **New (R4)**
- React to participants
- Exploit behavioral inefficiencies

---

## 🏁 Goal

Build a system that:

**Combines:**
- Market signals
- Options pricing
- Counterparty intelligence

**Achieves:**
- Consistent positive PnL
- Low drawdowns
- Strong adaptability

---

## 💡 Final Thought

> In Round 4, the edge is not in the market.  
> The edge is in who you are trading against.