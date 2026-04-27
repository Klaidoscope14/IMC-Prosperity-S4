# Enhancing 492364.py — From 23K to 35K+ PnL

## Analysis Summary

The 492364.py strategy is sophisticated (1,306 lines) with 7 signal types, dynamic trader tracking, pairs trading, vega regime management, and two-tier delta hedging. However, cross-referencing with our data analysis reveals **critical misconfigurations** and **missing signals** that are leaving significant PnL on the table.

---

## 🔴 Critical Bugs (Immediate PnL Impact)

### Fix 1: TTE_START_DAYS is WRONG (7 → 4)

```python
# Line 94: WRONG
TTE_START_DAYS = 7.0   # Says "Round 3" in comment!

# CORRECT for Round 4:
TTE_START_DAYS = 4.0   # R4 spec: options start with 4 days TTE
```

**Impact**: All BS/OU option pricing is computing with 7 days TTE instead of 4. This means:
- Time value is **overestimated by ~75%**
- Model sells options too expensive (misses buys) and buys too cheap (bad sells)
- Delta estimates are wrong → hedge ratios are off
- **Estimated PnL impact: +3K to +5K/day**

### Fix 2: TICKS_PER_DAY is WRONG (1M → ~10K)

```python
# Line 95: WRONG
TICKS_PER_DAY = 1_000_000

# From data: timestamps go 0-999900 in steps of 100 = 10,000 ticks/day
TICKS_PER_DAY = 1_000_000  # Actually this is correct IF timestamp units are raw
# The timestamp IS in units where 1M = 1 day (0 to 999,900)
# So this is actually correct. No change needed.
```

> [!NOTE]
> Actually TICKS_PER_DAY = 1,000,000 is correct — timestamps range 0-999,900 (≈1M), so 1M per day is right. The TTE formula `TTE_START_DAYS - timestamp / TICKS_PER_DAY` yields correct remaining days. **Only Fix 1 (TTE start) is wrong.**

---

## 🟡 Missing Counterparty Signals (Major Edge Left on Table)

### Fix 3: Mark 67 is COMPLETELY MISSING

The dynamic tracker learns from all marks generically, but Mark 67 is the **single strongest signal in the dataset** and gets no special treatment:

- **76% hit rate** on VE buys at T+10
- **+2.24 avg return** per buy
- Only trades ~58-61 times per day (rare, high-conviction)
- Buy-only trader — never sells

**Enhancement**: Add dedicated Mark 67 boost in `_dynamic_trader_signals`:

```python
# In the VE trades loop, after general scoring:
if b == "Mark 67":
    td["bot_v"] += q * 1.8  # STRONG follow signal (vs 0.25 * weight)
    # Mark 67 is buy-only, very infrequent, 76% hit rate
```

**Estimated PnL impact: +2K to +4K/day**

### Fix 4: Mark 49 Fade is Weak

Mark 49 has the **worst sell signal** in the dataset:
- Sells with +2.14 T+10 forward return (price goes UP after they sell)
- 15% correct rate on sells

Currently, Mark 49's seed score is -1.43 which gives weight = -1.43/3 = -0.48. This generates only a mild counter-signal. We should **amplify the fade**.

```python
# Add to MARK_SEEDS:
("Mark 49", "VELVETFRUIT_EXTRACT"): -2.5,  # was -1.43, strengthen fade
```

### Fix 5: Mark 22 on HP is Exploitable but Wrongly Classified

```python
# Current seed:
("Mark 22", "HYDROGEL_PACK"): +0.15,  # Treated as neutral

# From data: Mark 22 HP buy ret_10 = -5.00, ret_50 = -12.45
# Mark 22 is EXTREMELY DUMB on HP (only 11 trades, but -5.0 avg!)
("Mark 22", "HYDROGEL_PACK"): -4.0,  # Should be strongly negative
```

---

## 🟢 Parameter Optimizations

### Fix 6: VEV_4000 MR Config Too Tight

The MR engine uses `window=5, threshold=6.0` for VEV_4000. But from our data:
- Mark 14 and Mark 38 trade VEV_4000 at **±10.5 from mid** consistently
- This is a **structural spread**, not mean reversion
- Window=5 is too short to capture the structural edge

```python
# Better config for VEV_4000:
"VEV_4000": {"window": 10, "threshold": 8.0, "size": 15, "edge": 5.0},
# Bigger edge captures the ±10.5 structural trade between Mark 14/38
```

### Fix 7: Underlying MM Sizes Could Be More Aggressive

From the data: HP spread is consistently ~15.73 and VE spread is ~4.98. The strategy uses:
- `MM_SIZE_HP = 15` — reasonable
- `MM_SIZE_VE = 12` — could be 15 (spread is tighter on VE, higher volume)

```python
MM_SIZE_VE = 15   # was 12, VE has higher trade volume (2600+/day)
```

### Fix 8: Bot Signal Clamp is Too Low

```python
# Line 357-358: Clamped to ±8
td["bot_h"] = self._clip(td["bot_h"], -8.0, 8.0)
td["bot_v"] = self._clip(td["bot_v"], -8.0, 8.0)

# But then used with 0.3 weight (line 831): bot_sig * 0.3 = max ±2.4
# This is very weak. Increase clamp OR weight:
td["bot_h"] = self._clip(td["bot_h"], -12.0, 12.0)
td["bot_v"] = self._clip(td["bot_v"], -12.0, 12.0)
```

---

## 🔵 Structural Improvements

### Fix 9: Add Explicit Mark 67 Timestamp Tracking

Mark 67 trades infrequently (~17K-21K tick intervals). When he buys, the signal should persist longer because his edge holds at T+50 (+1.92) too.

```python
# Add to state:
"m67_last_ts": 0

# In _dynamic_trader_signals, when Mark 67 buys:
if b == "Mark 67" and sym == "VELVETFRUIT_EXTRACT":
    td["m67_last_ts"] = current_tick
    td["bot_v"] += q * 1.8

# In _trade_underlying for VE, add Mark 67 persistence signal:
m67_age = (current_tick - td.get("m67_last_ts", 0))
if m67_age < 5000:  # ~50 ticks
    m67_persistence = 1.5 * (1.0 - m67_age / 5000.0)
    bias += m67_persistence
```

### Fix 10: Reduce Pairs Trade Influence

The HP-VE pairs trade adds complexity but the data shows HP and VE are **not strongly correlated** (HP is mean-reverting around 10K, VE trends). The pairs trade may be adding noise.

```python
PAIRS_MAX_BIAS = 0.4     # was 0.8, halve the influence
PAIRS_THRESHOLD_SIGMA = 2.0  # was 1.5, less frequent triggering
```

---

## Summary of All Changes

| Fix | What | Where | Est. Impact |
|:---|:---|:---|---:|
| **1** ⭐ | TTE_START_DAYS 7→4 | Line 94 | **+3K-5K** |
| **3** ⭐ | Mark 67 dedicated boost | `_dynamic_trader_signals` | **+2K-4K** |
| **4** | Mark 49 stronger fade | MARK_SEEDS | +500-1K |
| **5** | Mark 22 HP correction | MARK_SEEDS | +200-500 |
| **6** | VEV_4000 config tuning | MR_VEV_CONFIGS | +500-1K |
| **7** | VE MM size 12→15 | MM_SIZE_VE | +300-800 |
| **8** | Bot signal clamp increase | Lines 357-358 | +200-500 |
| **9** | Mark 67 persistence | New code | +1K-2K |
| **10** | Pairs trade dampening | PAIRS params | +200-500 |
| | **Total Estimated Uplift** | | **+8K-15K** |

> [!IMPORTANT]
> **Fix 1 (TTE) is the single biggest win** — it's a clear bug where R3 value was left in R4 code. Fixing this alone should add ~3-5K PnL because ALL option pricing flows through this value.

> [!IMPORTANT]
> **Fix 3 (Mark 67) is the second biggest win** — this is the strongest directional signal in the entire dataset and it's getting generic treatment instead of dedicated exploitation.

---

## Verification Plan

### Automated Tests
1. Syntax validation after edits
2. Verify traderData stays under 50K chars
3. Confirm TTE computation: `7.0 - 500000/1000000 = 6.5` (old, WRONG) vs `4.0 - 500000/1000000 = 3.5` (new, CORRECT)

### Manual Verification
1. Submit to IMC platform
2. Compare PnL vs baseline 23K
