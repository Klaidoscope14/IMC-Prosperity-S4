# IMC Prosperity R2 – Strategy Improvement Plan

This document compiles **robust, non-overfitted improvements** to the current strategy (12k PnL baseline).
The focus is on **execution quality, stability, and exploiting structural edges** rather than adding fragile signals.

---

# 🔧 Improvements (Numbered)

## 4. Replace Hard Inventory Thresholds with Smooth Skew

* Current:

  * Step changes at +40, +70, etc.
* Replace with:

  * Gradual skew function (linear or mild nonlinear)
* Result:

  * Smoother behavior
  * Less abrupt PnL drops
  * More robust across datasets

---

## 5. Make ACO Quoting Spread-Aware

* ACO spread is usually wide (~16 ticks).
* Strategy:

  * Prefer passive quoting inside spread
  * Only take liquidity when edge is clearly large
* Avoid unnecessary crossing → reduces cost leakage.

---

## 6. Tighten ACO Taker Logic

* Current taker condition is slightly aggressive.
* Improve:

  * Only take when expected edge > execution cost + buffer
* Reason:

  * ACO edge = spread capture, not aggressive trading.

---

## 7. Improve IPR Execution (Keep Same Core Idea)

* Keep:

  * Buy-to-80 ASAP
  * Never sell (structural trend)
* Improve:

  * Dynamically size orders based on actual ask liquidity
  * Avoid rigid batch sequence

---

## 8. Slightly Reduce Aggression Near Max Position (IPR)

* Early phase → aggressive buying
* Near position limit:

  * Be slightly more selective
* Reduces overpaying while preserving most drift gains.

---

## 9. Optimize MAF Bid (CRITICAL FOR R2)

* Current:

  ```python
  def bid(self):
      return 10000
  ```
* Replace with:

  * Expected value model:

    * Value of +25% quotes
    * Probability of winning
    * Cost of MAF
* This is a **major missing edge** in current system.

---

## 10. Simplify Auction Manipulation Logic

* Current auction injection logic is:

  * Complex
  * Potentially overfit
* Recommendation:

  * Keep **"maximum unpunished size"**
  * Remove or simplify price manipulation logic
* Focus on:

  * Safe volume extraction, not forcing price

---

## 11. Add Confidence-Based Position Sizing

* Reduce size when:

  * Spread is narrow
  * Book is thin
  * Mid is unstable
* For IPR:

  * Only reduce when liquidity is poor or near limit
* Prevents tail-risk scenarios.

---

## 12. Keep State Minimal and Stable

* Avoid adding too many indicators.
* Maintain:

  * EMA
  * Anchor
  * Last valid mid
  * Minimal inventory state
* Simpler models generalize better.

---

## 13. Improve Fill Probability via Better Queue Positioning

* Slightly more aggressive overbidding/undercutting when needed.
* Ensure:

  * Higher queue priority
  * Better fill rate
* This directly improves realized PnL without changing alpha.

---

## 14. Prefer Passive Edge Over Active Trading (ACO)

* Reinforce philosophy:

  * Earn spread, don’t pay it
* Active trades only when:

  * Clear mispricing exists

---

## 15. Incremental Testing Strategy

Apply improvements in order:

1. ACO execution improvements
2. IPR execution improvements
3. MAF bidding logic

* Evaluate impact step-by-step.
* Avoid stacking multiple changes blindly.

---

# 🧠 Core Philosophy (Unchanged)

* **ACO** → Mean-reversion + spread capture
* **IPR** → Deterministic trend exploitation
* **R2 Edge** → Auction / MAF optimization

---

# 🎯 Goal

Transform strategy from:

```
GOOD MODEL + GOOD LOGIC
```

to:

```
GOOD MODEL + ELITE EXECUTION + AUCTION EDGE
```

---

# 🚀 Expected Outcome

* Higher fill efficiency (ACO)
* Faster drift capture (IPR)
* Additional edge via MAF (R2-specific)
* Improved robustness across datasets

---

End of document.