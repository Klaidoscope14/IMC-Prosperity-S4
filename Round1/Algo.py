"""
IMC Prosperity 4 – Round 1 – V4: Aggressive Mathematical Edges
================================================================
Products:
  • ASH_COATED_OSMIUM   (Limit: 80) → Hybrid Take/Make Market Maker
  • INTARIAN_PEPPER_ROOT (Limit: 80) → Aggressive Buy-and-Hold

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
V4 PHILOSOPHY — "EXECUTE ON THE MATH"

V1 (7,200 PnL):  Basic MM + trend hold.  Decent baseline.
V2 (5,000 PnL):  Over-engineered OBI, scalping, complexity.
V3 (worse):      Passive joining → adverse selection.
                  EMA spike detection → false-positive panic sells.

V4 corrects BOTH failure modes:

  IPR: The asset goes up +1,000/day.  Period.  There is no edge in
       being passive, no edge in selling, no edge in EMA math.
       BUY TO 80 IMMEDIATELY.  HOLD FOREVER.  NEVER SELL.

  ACO: Mean-reverts around 10,000.  The edge is in the math:
       FV = 50% fast_EMA + 50% anchor.  TAKE anything mispriced
       vs FV.  MAKE the spread at FV ± 2 with inventory skew.
       No passive joining.  No multi-layer nonsense.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List, Dict, Tuple, Optional
import jsonpickle
import math


class Trader:

    # ╔════════════════════════════════════════════════════════════════╗
    # ║                     POSITION LIMIT                            ║
    # ╚════════════════════════════════════════════════════════════════╝

    LIMIT = 80  # Hard limit for both products (long or short)

    # ─────────────────────────────────────────────────────────────────
    #  ASH_COATED_OSMIUM (ACO) — Hybrid Take/Make Market Maker
    #
    #  Mean-reverts around 10,000.  ~16 tick spread.
    #  FV = 50% fast EMA + 50% anchor.
    #  TAKE any mispricing vs FV.  MAKE the spread at FV ± 2.
    # ─────────────────────────────────────────────────────────────────
    ACO_ANCHOR     = 10_000  # Structural mean-reversion center
    ACO_EMA_ALPHA  = 0.20    # Fast EMA — tracks local price quickly
    ACO_ANCHOR_WT  = 0.50    # FV = 50% EMA + 50% anchor
    ACO_MAKE_OFFSET = 2      # Quote spread: FV ± 2 ticks
    ACO_MAKE_SIZE   = 15     # Size per make quote
    ACO_INV_THRESH  = 40     # Position threshold for inventory skew
    ACO_INV_SKEW_1  = 1      # Skew ticks when |pos| > 40
    ACO_INV_SKEW_2  = 2      # Skew ticks when |pos| > 60

    # ╔════════════════════════════════════════════════════════════════╗
    # ║                       ENTRY POINT                             ║
    # ╚════════════════════════════════════════════════════════════════╝

    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:
        """Called every tick by the exchange engine."""
        result: Dict[str, List[Order]] = {}
        conversions = 0

        # ── Restore persistent state ──
        td = self._load(state.traderData)

        # ── Execute each strategy ──
        result["ASH_COATED_OSMIUM"]    = self._trade_aco(state, td)
        result["INTARIAN_PEPPER_ROOT"] = self._trade_ipr(state, td)

        # ── Persist state and return ──
        return result, conversions, self._save(td)

    def bid(self) -> int:
        """Stub required by some engine versions."""
        return 0

    # ╔════════════════════════════════════════════════════════════════╗
    # ║                    STATE MANAGEMENT                           ║
    # ╚════════════════════════════════════════════════════════════════╝

    def _load(self, raw: str) -> dict:
        """Deserialize traderData. Returns clean defaults on Day 0."""
        if raw and raw.strip():
            try:
                d = jsonpickle.decode(raw)
                if isinstance(d, dict):
                    d.setdefault("aco_ema", None)
                    d.setdefault("imbalance_history", {})
                    return d
            except Exception:
                pass
        # Only ACO needs state (EMA). IPR has no state — just buy.
        return {"aco_ema": None, "imbalance_history": {}}

    @staticmethod
    def _save(td: dict) -> str:
        """Serialize state. Returns empty string on failure."""
        try:
            return jsonpickle.encode(td)
        except Exception:
            return ""

    # ╔════════════════════════════════════════════════════════════════╗
    # ║                     UTILITY HELPERS                           ║
    # ╚════════════════════════════════════════════════════════════════╝

    @staticmethod
    def _pos(state: TradingState, product: str) -> int:
        """Current position in a product (0 if none)."""
        return state.position.get(product, 0)

    @staticmethod
    def _mid(od: OrderDepth) -> Optional[float]:
        """Simple mid-price: (best_bid + best_ask) / 2."""
        if not od.buy_orders or not od.sell_orders:
            return None
        return (max(od.buy_orders.keys()) + min(od.sell_orders.keys())) / 2.0

    # ╔════════════════════════════════════════════════════════════════╗
    # ║   INTARIAN_PEPPER_ROOT — AGGRESSIVE BUY AND HOLD             ║
    # ╚════════════════════════════════════════════════════════════════╝
    #
    #  The asset trends up +1,000 per day.  Every tick we are not
    #  max long, we are leaving money on the table.
    #
    #  Logic:
    #    1. buy_cap = 80 - position
    #    2. If buy_cap > 0, TAKE every ask in the book until full.
    #    3. NEVER sell.  No EMA.  No spike detection.  No trimming.
    #
    #  This is the simplest possible strategy for a trending asset.
    #  V3 failed by being "clever" with EMAs and spike detection,
    #  which caused false-positive sells into a relentless uptrend.
    #
    # ═══════════════════════════════════════════════════════════════════

    def _trade_ipr(self, state: TradingState, td: dict) -> List[Order]:
        product = "INTARIAN_PEPPER_ROOT"
        orders: List[Order] = []

        if product not in state.order_depths:
            return orders

        od  = state.order_depths[product]
        pos = self._pos(state, product)

        # How much more can we buy? (Hard limit enforcement)
        buy_cap = self.LIMIT - pos

        # Nothing to do if already max long
        if buy_cap <= 0:
            return orders

        # Take every ask
        if od.sell_orders:
            for ask_px in sorted(od.sell_orders.keys()):
                if buy_cap <= 0:
                    break
                # sell_orders values are negative; abs() for volume
                avail = abs(od.sell_orders[ask_px])
                take  = min(avail, buy_cap)
                orders.append(Order(product, ask_px, take))
                buy_cap -= take

        # Backstop bid
        # ── BACKSTOP BID ───────────────────────────────────────────
        #    If the ask side was thin and we couldn't fill entirely,
        #    place the remaining capacity as a bid at best_bid + 1
        #    to catch any incoming sell flow next tick.
        if buy_cap > 0 and od.buy_orders:
            best_bid = max(od.buy_orders.keys())
            orders.append(Order(product, best_bid + 1, buy_cap))

        # ── NEVER SELL ─────────────────────────────────────────────
        #    No sell orders.  No trimming.  No scalping.
        #    Hold to 80.  Ride the trend.

        return orders

    # ╔════════════════════════════════════════════════════════════════╗
    # ║   ASH_COATED_OSMIUM — HYBRID TAKE/MAKE MARKET MAKER          ║
    # ╚════════════════════════════════════════════════════════════════╝
    #
    #  Mean-reverts around 10,000.  The edge is purely mathematical:
    #
    #  FV = 50% × fast_EMA + 50% × 10,000
    #
    #  PHASE 1 (TAKE): If best_ask < FV → buy it (it's cheap).
    #                   If best_bid > FV → sell it (it's rich).
    #                   This captures mispricings aggressively.
    #
    #  PHASE 2 (MAKE): Place bids at FV-2, asks at FV+2.
    #                   This earns the spread when the market
    #                   oscillates around fair value.
    #
    #  INVENTORY SKEW: When position > 40, shift FV down 1-2 ticks
    #                   to encourage selling.  When < -40, shift up.
    #                   This prevents inventory blowouts.
    #
    # ═══════════════════════════════════════════════════════════════════

    def _trade_aco(self, state: TradingState, td: dict) -> List[Order]:
        product = "ASH_COATED_OSMIUM"
        orders: List[Order] = []

        if product not in state.order_depths:
            return orders

        od  = state.order_depths[product]
        pos = self._pos(state, product)

        mid = self._mid(od)
        if mid is None:
            return orders

        # ── Step 1: Update fast EMA ────────────────────────────────
        #    alpha = 0.20 → responsive to recent moves, but not noise.
        if td["aco_ema"] is None:
            td["aco_ema"] = mid
        else:
            td["aco_ema"] = (
                self.ACO_EMA_ALPHA * mid
                + (1.0 - self.ACO_EMA_ALPHA) * td["aco_ema"]
            )

        # ── Step 2: Compute Fair Value ─────────────────────────────
        #    FV = 50% EMA + 50% anchor.
        #    The heavy anchor weight ensures we always trade toward
        #    10,000, which is where this asset mean-reverts to.
        raw_fv = self.ACO_ANCHOR_WT * self.ACO_ANCHOR + (1.0 - self.ACO_ANCHOR_WT) * td["aco_ema"]

        # ── Step 3: Inventory skew ─────────────────────────────────
        #    When we are too long, shift FV down to make our asks
        #    more attractive and bids less aggressive.  Vice versa.
        #
        #    |pos| > 60 → 2 tick skew (urgent)
        #    |pos| > 40 → 1 tick skew (gentle)
        #    else       → 0 (neutral)
        skew = 0
        if pos > 60:
            skew = -self.ACO_INV_SKEW_2       # Shift FV down 2 → sell more
        elif pos > self.ACO_INV_THRESH:
            skew = -self.ACO_INV_SKEW_1       # Shift FV down 1
        elif pos < -60:
            skew = self.ACO_INV_SKEW_2        # Shift FV up 2 → buy more
        elif pos < -self.ACO_INV_THRESH:
            skew = self.ACO_INV_SKEW_1        # Shift FV up 1

        fv = round(raw_fv + skew)

        # ---- Imbalance calculation for better fills -----------------
        # Calculate order book imbalance: (bid_vol - ask_vol) / (bid_vol + ask_vol)
        # Positive imbalance = more bid pressure (upward pressure)
        # Negative imbalance = more ask pressure (downward pressure)
        bid_vol = sum(od.buy_orders.values()) if od.buy_orders else 0
        ask_vol = sum(abs(v) for v in od.sell_orders.values()) if od.sell_orders else 0
        
        imbalance = 0
        if bid_vol + ask_vol > 0:
            imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol)
            fv += imbalance * 1  # Small nudge toward imbalance direction
        
        # ---- Step 1: Track imbalance history ----
        if product not in td["imbalance_history"]:
            td["imbalance_history"][product] = []
        
        td["imbalance_history"][product].append(imbalance)
        if len(td["imbalance_history"][product]) > 10:
            td["imbalance_history"][product].pop(0)
        
        # ---- Step 2: Detect persistent bias ----
        avg_imbalance = sum(td["imbalance_history"][product]) / len(td["imbalance_history"][product])
        
        # ---- Step 3: Use it ONLY when consistent ----
        trend = "neutral"
        if avg_imbalance > 0.25:
            trend = "up"
        elif avg_imbalance < -0.25:
            trend = "down"
        
        # ---- 🚀 UPGRADE 1: Add "price influence mode" ----
        # When imbalance is strong → push clearing price
        influence = False
        if abs(avg_imbalance) > 0.35:
            influence = True
        
        # Ensure fair value is always integer to avoid fractional prices
        fv = int(round(fv))

        # ---- Capacity tracking (hard limit enforcement) ------------─────────────
        buy_cap  = self.LIMIT - pos   # Max additional buy volume
        sell_cap = self.LIMIT + pos   # Max additional sell volume

        # ═══════════════════════════════════════════════════════════
        #  PHASE 1: TAKE — Aggressively capture mispricings
        #
        #  If the market is offering prices BETTER than FV, take them.
        #    • best_ask < FV  →  the ask is cheap, BUY it
        #    • best_bid > FV  →  the bid is rich, SELL into it
        #
        #  We sweep ALL mispriced levels, not just the top of book.
        # ═══════════════════════════════════════════════════════════

        # ── Take cheap asks (price <= FV + 1) ───────────────────────
        if od.sell_orders and buy_cap > 0:
            for ask_px in sorted(od.sell_orders.keys()):
                if buy_cap <= 0:
                    break
                if ask_px <= fv + 1:
                    # This ask is at or below fair value + 1 — take it
                    avail = abs(od.sell_orders[ask_px])
                    take  = min(avail, buy_cap)
                    orders.append(Order(product, ask_px, take))
                    buy_cap -= take
                else:
                    break  # Sorted ascending; no more cheap asks

        # ── Take rich bids (price >= FV - 1) ────────────────────────
        if od.buy_orders and sell_cap > 0:
            for bid_px in sorted(od.buy_orders.keys(), reverse=True):
                if sell_cap <= 0:
                    break
                if bid_px >= fv - 1:
                    # This bid is at or above fair value - 1 — sell into it
                    avail = od.buy_orders[bid_px]
                    take  = min(avail, sell_cap)
                    orders.append(Order(product, bid_px, -take))
                    sell_cap -= take
                else:
                    break  # Sorted descending; no more rich bids

        # ═══════════════════════════════════════════════════════════
        #  PHASE 2: MAKE — Earn the spread around fair value
        #
        #  Place limit orders at:
        #    BID = FV - offset   (buy below fair value)
        #    ASK = FV + offset   (sell above fair value)
        #
        #  When both sides fill, we capture 2×offset ticks of spread.
        #  Size is capped at ACO_MAKE_SIZE (15) per side.
        #
        #  Remaining capacity goes one level deeper (FV ± offset×2)
        #  to catch bigger dislocations.
        # ═══════════════════════════════════════════════════════════

        # Calculate adaptive spread based on market spread
        spread = 0
        if od.buy_orders and od.sell_orders:
            best_bid = max(od.buy_orders.keys())
            best_ask = min(od.sell_orders.keys())
            spread = best_ask - best_bid
        
        # Adaptive offset based on market spread
        if spread >= 12:
            offset = 3
        elif spread >= 8:
            offset = 2
        else:
            offset = 1
        
        bid_price = int(fv - offset)
        ask_price = int(fv + offset)

        # ── Dynamic size scaling based on position ───────────────────────
        if abs(pos) < 30:
            size = 20
        elif abs(pos) < 60:
            size = 12
        else:
            size = 6
        
        # ---- Trend-based behavior adjustments ----
        # 🚀 Use trend for behavior adjustment, NOT heavy FV changes
        
        # 🔹 Case 1: Upward "vibe"
        if trend == "up":
            # be more aggressive buyer
            bid_price += 1
            size = int(size * 1.3)
        
        # 🔹 Case 2: Downward "vibe"
        if trend == "down":
            # be more aggressive seller
            ask_price -= 1
            size = int(size * 1.3)

        # ---- 🚀 UPGRADE 2: Concentrate size (CRITICAL) ----
        # Replace L1 + L2 + sponge with concentrated size when influence is detected
        
        if influence:
            # concentrate size near one side
            # 🔹 Case: upward pressure
            if trend == "up":
                aggressive_bid = int(fv + 1)
                size = min(buy_cap, int(self.LIMIT * 0.6))
                orders.append(Order(product, aggressive_bid, size))
                return orders
            
            # 🔹 Case: downward pressure
            if trend == "down":
                aggressive_ask = int(fv - 1)
                size = min(sell_cap, int(self.LIMIT * 0.6))
                orders.append(Order(product, aggressive_ask, -size))
                return orders
        
        # ---- Normal multi-layer quoting (when no influence) ----
        # ── L1 Make: FV ± 2 ───────────────────────────────────────
        if buy_cap > 0:
            l1_bid = min(buy_cap, size)
            orders.append(Order(product, bid_price, l1_bid))
            buy_cap -= l1_bid

        if sell_cap > 0:
            l1_ask = min(sell_cap, size)
            orders.append(Order(product, ask_price, -l1_ask))
            sell_cap -= l1_ask

        # ── L2 Make: FV ± 2*offset (deeper liquidity) ────────────────────
        if buy_cap > 0:
            l2_bid = min(buy_cap, size)
            orders.append(Order(product, int(bid_price - offset), l2_bid))
            buy_cap -= l2_bid

        if sell_cap > 0:
            l2_ask = min(sell_cap, size)
            orders.append(Order(product, int(ask_price + offset), -l2_ask))
            sell_cap -= l2_ask

        # ── Sponge: absorb remaining capacity at wide prices ──────
        #    FV ± 8 — catches flash crashes/spikes.  Rarely fills
        #    but costs nothing to have on the book.
        if buy_cap > 0:
            orders.append(Order(product, int(bid_price - offset * 2), buy_cap))

        if sell_cap > 0:
            orders.append(Order(product, int(ask_price + offset * 2), -sell_cap))

        return orders