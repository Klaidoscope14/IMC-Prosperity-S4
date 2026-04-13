# IMC Prosperity 4 — Rules & Guide

## 1. Overview

* You must build a **Python trading algorithm**.
* Your algorithm trades on a simulated exchange against bots.
* Goal: **maximize profit (XIRECs)**.
* The competition runs in **multiple rounds** with different products.

---

## 2. Core Structure

### Trader Class (Your Main Code)

You must implement a `Trader` class with:

#### `run(state: TradingState)`

* Called every iteration.
* Contains your trading logic.
* Returns:

  ```python
  result, conversions, traderData
  ```

#### `bid()` (Only for Round 2)

* Optional for other rounds.
* Ignored except in Round 2.

---

## 3. Simulation Flow

* Simulation runs many iterations:

  * ~1000 (testing)
  * ~10,000 (final evaluation)
* Each iteration:

  1. You receive a `TradingState`
  2. You process it
  3. You return orders

---

## 4. TradingState (Market Data)

This is your **main input**.

Contains:

* `order_depths` → current buy/sell orders (order book)
* `own_trades` → your previous trades
* `market_trades` → trades by others
* `position` → your current holdings
* `observations` → extra signals (optional)
* `traderData` → your saved state (string)

---

## 5. Orders

Each order has:

* **symbol** → product name
* **price** → price you want
* **quantity**:

  * `+ve` → BUY
  * `-ve` → SELL

### Example

```python
Order("PRODUCT1", 100, 5)   # Buy 5
Order("PRODUCT1", 100, -5)  # Sell 5
```

---

## 6. Order Matching

* Orders are matched **instantly**.
* If your price matches existing orders → trade happens.
* If partially matched → remaining stays in market.
* If no one matches → order is **cancelled next iteration**.

---

## 7. Order Book (OrderDepth)

* `buy_orders`: {price → quantity}
* `sell_orders`: {price → quantity (negative)}

### Key Rule

* Buy prices < Sell prices
* Otherwise, trades would already have happened.

---

## 8. Positions

* Position = how many units you hold.
* Positive → long
* Negative → short

### Example

* Buy 3 → position = +3
* Sell 5 → position = -2

---

## 9. Position Limits ⚠️

* Each product has a **max position limit**.
* You cannot exceed:

  ```
  -limit ≤ position ≤ +limit
  ```

### Important Rule

* If your orders *could* exceed limit → **ALL orders rejected**

### Example

* Limit = 10, current = 3
* Max you can buy = 7

---

## 10. Conversions (Advanced)

* Used to convert between assets (optional).
* Controlled via `conversions` return value.

### Rules:

* Must already hold position
* Cannot exceed holdings
* Includes costs:

  * transport fees
  * import/export tariffs
* Not mandatory (can return 0)

---

## 11. traderData (State Storage)

* Used to **store data across iterations**
* Must be a **string**
* Useful because:

  * System is stateless (AWS Lambda)
* Max size: **50,000 characters**

---

## 12. Execution Behavior

* No latency → all orders processed instantly
* Bots cannot “beat” your order timing
* Matching happens immediately if possible

---

## 13. Technical Constraints

* Only allowed libraries (Python 3.12 standard):

  * pandas
  * numpy
  * math
  * statistics
  * typing
  * jsonpickle

❌ No external libraries

---

## 14. Performance Constraints

* Each `run()` call must finish in:

  * **< 900 ms**
  * Recommended: **< 100 ms**

---

## 15. Debugging

* Logs are provided after simulation
* Includes:

  * print outputs
  * trade results

---

## 16. Strategy Basics (What You Should Do)

Typical approach:

1. Estimate **fair price**
2. Compare with market:

   * Buy if price < fair value
   * Sell if price > fair value
3. Respect:

   * position limits
   * liquidity (order book)

---

## 17. Key Takeaways

* Think like a **market maker / trader**
* Use:

  * order book data
  * trade history
* Always:

  * manage risk (position limits)
  * keep algorithm fast

---

## 18. Minimal Return Format

```python
return result, conversions, traderData
```

Where:

* `result`: dict → product → list of orders
* `conversions`: int
* `traderData`: str

---

## 19. Simple Example Output

```python
result = {
    "PRODUCT1": [Order("PRODUCT1", 12, 7)],
    "PRODUCT2": [Order("PRODUCT2", 143, -5)]
}
```

---