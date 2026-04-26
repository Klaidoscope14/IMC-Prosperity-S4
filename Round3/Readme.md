# 🚀 IMC Prosperity 3 – Round 3: "Gloves Off"

## 🌍 Overview

Welcome to **Solvenar** — a technologically advanced planet known for innovation, a strong economy, and thriving culture.

Round 3 begins the **Great Orbital Ascension Trials (GOAT)**:
- All teams start with **zero PnL**
- Leaderboard is **reset**
- Compete for the title of **Trading Champion of the Galaxy**

---

## 🎯 Round Objective

### 🧠 Algorithmic Trading

Build a Python trading system to trade:

- `HYDROGEL_PACK`
- `VELVETFRUIT_EXTRACT`
- `VELVETFRUIT_EXTRACT_VOUCHER`

Goal:
- Maximize **PnL**
- Handle both **spot assets** and **options**

---

### 🌱 Manual Trading (Bio-Pods)

- Trade **Ornamental Bio-Pods** with the **Celestial Gardeners’ Guild**
- You may submit **2 bids**
- Purchased Bio-Pods are automatically converted to **profit**

---

## ⚙️ Products & Market Structure

### 🟢 Asset Classes

#### 1. Delta-1 Products
- `HYDROGEL_PACK`
- `VELVETFRUIT_EXTRACT`

👉 These behave like standard tradable assets.

---

#### 2. Options (Vouchers)

`VELVETFRUIT_EXTRACT_VOUCHER`

Available instruments:
VEV_4000, VEV_4500, VEV_5000, VEV_5100, VEV_5200,
VEV_5300, VEV_5400, VEV_5500, VEV_6000, VEV_6500


- Each voucher is an **option on Velvetfruit Extract**
- The number represents the **strike price**
- Expiry = **7 days**

---

## ⏳ Time to Expiry (TTE)

| Round        | TTE |
|-------------|-----|
| Tutorial     | 8 days |
| Round 1      | 7 days |
| Round 2      | 6 days |
| Round 3      | 5 days |

---

## 📦 Position Limits

- `HYDROGEL_PACK`: **200**
- `VELVETFRUIT_EXTRACT`: **200**
- Each voucher: **300**

---

## ⚠️ Important Rules

- Vouchers **cannot be exercised early**
- Positions **do NOT carry forward**
- All positions are:
  - Automatically liquidated
  - At a **hidden fair value**

---

## 🧠 Algorithmic Challenge: "Options Require Decisions"

- Options depend on:
  - Underlying price
  - Strike price
  - Time to expiry

👉 Products are traded independently but are **interrelated in value**

---

## 🌱 Manual Trading Challenge: "Celestial Gardeners’ Guild"

### 📊 Market Setup

- Reserve prices range from **670 to 920**
- Step size: **5**
- Distribution: **Uniform**

Example:
- Valid: 675, 680
- Invalid: 676, 677

---

## 💰 Bidding Rules

You may submit **2 bids**:

### 🥇 First Bid
- If `bid1 > reserve price` → trade executes at **bid1**

---

### 🥈 Second Bid

Conditions:
- Must be greater than reserve price

Outcomes:

- If `bid2 > avg(second bids)`:
  - Trade executes normally

- If `bid2 ≤ avg(second bids)`:
  - Trade executes
  - **PnL is penalized**

---

## 📉 Penalty Function
((920 - avg_b2) / (920 - b2))^3


👉 Lower second bid relative to market → **higher penalty**

---

## 💡 Strategy Insight

- First bid → ensures execution
- Second bid → optimizes profit
- Balance:
  - Aggressiveness
  - Penalty risk

---

## ⏱️ Trading Constraints

- Each round lasts **48 hours**
- You can modify bids anytime
- Final submission is used at round end

---

## 📌 Submission

- Submit bids in the **Manual Challenge UI**
- Last submitted bids are final

---

## 🧠 Key Takeaways

- Combine:
  - Market making
  - Options pricing
  - Game theory

- Optimize for:
  - Execution probability
  - Risk-adjusted returns
  - End-of-round liquidation

---

## 🏁 Goal

Maximize your **PnL** and dominate the **GOAT leaderboard**