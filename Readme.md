# IMC Prosperity 4 — Algorithmic Trading Challenge

---

## Overview

IMC Prosperity is a multi-round trading competition where participants:

* Build Python-based trading algorithms
* Compete against market-making bots
* Trade multiple financial products
* Aim to maximize PnL (profit in XIRECs)

Each round introduces new products and challenges, requiring adaptive and efficient strategies.

---

## How It Works

1. You implement a `Trader` class in Python.
2. Your algorithm is deployed into a simulation engine.
3. At every iteration:

   * You receive market data (`TradingState`)
   * You return orders
4. The system evaluates your performance over thousands of iterations.

---

## Key Concepts

### Market Simulation

* Continuous iterations simulate a live market
* Bots provide liquidity and compete with your strategy
* Trades happen via an order matching engine

### Products

* Each round includes different tradable assets
* Each product has:

  * Order book (buy/sell orders)
  * Position limits
  * Market dynamics

### Objective

Maximize your total profit (PnL) while managing:

* Risk (position limits)
* Execution efficiency
* Market conditions

---

## Project Structure

```bash
.
├── trader.py          # Your main trading algorithm
├── datamodel.py       # Provided market data structures
├── utils/             # Optional helper functions
├── data/              # Sample datasets (CSV)
├── notebooks/         # Research & analysis
└── README.md
```

---

## Getting Started

### Requirements

* Python 3.12
* Allowed libraries:

  * pandas
  * numpy
  * math
  * statistics
  * typing
  * jsonpickle

---

### Basic Trader Template

```python
class Trader:
    def run(self, state):
        result = {}
        conversions = 0
        traderData = ""
        return result, conversions, traderData
```

---

### Running Locally

* Use provided `datamodel.py`
* Simulate iterations using sample data
* Analyze logs to refine strategy

---

## Input: TradingState

Your algorithm receives a `TradingState` object containing:

* order books (`order_depths`)
* your trades (`own_trades`)
* market trades (`market_trades`)
* positions (`position`)
* observations (optional signals)
* previous state (`traderData`)

---

## Output: Orders

Your algorithm must return:

```python
result, conversions, traderData
```

Where:

* `result` → dict of product → list of orders
* `conversions` → integer (optional feature)
* `traderData` → string (persistent state)

---

## Strategy Ideas

Some common approaches:

* Market Making
* Arbitrage
* Mean Reversion
* Trend Following

---

## Constraints

### Time Limit

* Each iteration must run in < 900 ms
* Recommended: < 100 ms

### Position Limits

* Each product has a max allowed position
* Exceeding limits results in all orders being rejected

### Libraries

* Only standard Python and allowed libraries
* No external imports

---

## Resources

* Sample datasets (CSV)
* Example trader implementations
* Documentation (rules, datamodel)

---

## Final Goal

Build a fast, robust, and profitable trading algorithm that adapts to changing market conditions and outperforms competitors.