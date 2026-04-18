"""
IMC Prosperity 4 - Round 2 - Optimized Dual Strategy
================================================================
Products:
  - ASH_COATED_OSMIUM   (Limit: 80) -> Single-EMA Market Maker
  - INTARIAN_PEPPER_ROOT (Limit: 80) -> Aggressive Buy-and-Hold

MAF: bid() returns 2500 XIRECs to secure top-50% Market Access Fee
     and gain 25% more quote volume.

IPR: Trends up +1,000/day. Aggressive every-tick accumulation to
     reach 80 units ASAP and capture maximum drift PnL.

ACO: Mean-reverts around ~10,001. Single slow EMA for FV.
     Take mispriced liquidity with widened thresholds.
     Make with inventory-skewed ladder at 3-tick spacing.
"""

from datamodel import OrderDepth, TradingState, Order
from typing import List, Dict, Tuple, Optional
import json
import math

class Trader:

    # ╔════════════════════════════════════════════════════════════════╗
    # ║                     POSITION LIMIT                             ║
    # ╚════════════════════════════════════════════════════════════════╝

    LIMIT = 80    # Hard limit for both products (long or short)
    MAX_LOT = 20  # Max lots per individual order (up from 12)


    # ╔════════════════════════════════════════════════════════════════╗
    # ║                       ENTRY POINT                              ║
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
        """
        Market Access Fee (MAF) for Round 2.
        Top 50% of MAFs win access to 25% more quote volume.
        2500 is calibrated to likely win while preserving most of
        the additional ~3,000-5,000 XIRECs/day profit from extra volume.
        """
        return 2500

    # ╔════════════════════════════════════════════════════════════════╗
    # ║                    STATE MANAGEMENT                           ║
    # ╚════════════════════════════════════════════════════════════════╝

    def _defaults(self):
        return {
            "aco_ema": None,
        }

    def _clean(self, obj):
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return 0.0
            return round(float(obj), 10)

        if isinstance(obj, dict):
            return {k: self._clean(v) for k, v in obj.items()}

        if isinstance(obj, list):
            return [self._clean(v) for v in obj]

        return obj

    def _load(self, raw: str) -> dict:
        d = self._defaults()
        if raw and raw.strip():
            try:
                x = json.loads(raw)
                if isinstance(x, dict):
                    d.update(x)
            except Exception:
                return d
        return d

    def _save(self, td: dict) -> str:
        try:
            safe = self._clean(td)
            return json.dumps(safe, separators=(",", ":"))
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
    # ║   INTARIAN_PEPPER_ROOT — MULTI-LEVEL SWEEP ACCUMULATOR       ║
    # ╚════════════════════════════════════════════════════════════════╝
    #
    #  Asset trends up +1,000/day (+0.10/tick). Must hold 80 long ASAP.
    #
    #  BUG 1 FIX: Old code placed 1 order at best_ask. If L1 had < cap
    #  lots (L1 mean = 11.6), the remainder was lost that tick.
    #  Fix: sweep ALL ask levels (L1→L2→L3) up to cap, then place a
    #  backstop passive bid at best_ask for any residual.
    #
    # ═══════════════════════════════════════════════════════════════════

    IPR_CAP = 12  # Just above L1 ask mean of 11.6 (data §4.7)

    def _trade_ipr(self, state: TradingState, td: dict) -> List[Order]:
        product = "INTARIAN_PEPPER_ROOT"
        orders: List[Order] = []

        if product not in state.order_depths:
            return orders

        od  = state.order_depths[product]
        pos = self._pos(state, product)

        total_missing = self.LIMIT - pos
        if total_missing <= 0:
            return orders

        buy_cap = min(total_missing, self.IPR_CAP)

        # ── Handle empty-ask-side ticks ──
        if not od.sell_orders:
            if od.buy_orders:
                best_bid = max(od.buy_orders.keys())
                orders.append(Order(product, best_bid + 1, buy_cap))
            return orders

        # ── Sweep ALL ask levels up to cap ──
        for ask_px in sorted(od.sell_orders.keys()):
            if buy_cap <= 0:
                break
            avail = abs(od.sell_orders[ask_px])
            take  = min(avail, buy_cap)
            if take > 0:
                orders.append(Order(product, ask_px, take))
                buy_cap -= take

        # ── Backstop bid for any residual ──
        if buy_cap > 0:
            best_ask = min(od.sell_orders.keys())
            orders.append(Order(product, best_ask, buy_cap))

        return orders


    # ╔════════════════════════════════════════════════════════════════╗
    # ║   ASH_COATED_OSMIUM — SINGLE-EMA MARKET MAKER               ║
    # ╚════════════════════════════════════════════════════════════════╝
    #
    #  Data-driven parameters:
    #    - FV anchor: 10,001 (data shows slight positive bias)
    #    - Single EMA alpha = 0.005 (adapts to genuine drift, ignores noise)
    #    - Autocorrelation = -0.50 → strong mean-reversion edge
    #
    #  TAKE: Widened thresholds — buy asks <= FV+1, sell bids >= FV-1
    #        (vs. old: only < FV / > FV). More fills from 16-tick spread.
    #        Inventory-based widening for risk management.
    #
    #  MAKE: Inventory-skewed ladder at 3-tick spacing.
    #        When long: tighten asks, widen bids (encourage selling).
    #        When short: tighten bids, widen asks (encourage buying).
    #
    # ═══════════════════════════════════════════════════════════════════

    ACO_ANCHOR = 10001     # Data-proven mean (slight positive bias)
    ACO_EMA_ALPHA = 0.005  # Slow EMA — adapts to drift, ignores noise

    def _trade_aco(self, state: TradingState, td: dict) -> List[Order]:
        orders: List[Order] = []
        product = "ASH_COATED_OSMIUM"

        if product not in state.order_depths:
            return orders

        od = state.order_depths[product]
        pos = state.position.get(product, 0)
        buy_cap = self.LIMIT - pos
        sell_cap = self.LIMIT + pos

        # ── Single EMA Fair Value ──
        mid = self._mid(od)
        if td.get("aco_ema") is None:
            td["aco_ema"] = mid if mid is not None else self.ACO_ANCHOR
        elif mid is not None:
            td["aco_ema"] = self.ACO_EMA_ALPHA * mid + (1 - self.ACO_EMA_ALPHA) * td["aco_ema"]

        FV = round(td["aco_ema"])

        # ═══════════════════════════════════════════════════════════
        #  PHASE 1: TAKE MISPRICED LIQUIDITY
        # ═══════════════════════════════════════════════════════════
        #
        #  BUG 2 FIX — monotonic inventory thresholds:
        #
        #  The loop checks: ask_px >= buy_up_to (break) / bid_px <= sell_down_to (break)
        #  So buy_up_to is the EXCLUSIVE upper bound — we take asks < buy_up_to
        #  And sell_down_to is the EXCLUSIVE lower bound — we sell bids > sell_down_to
        #
        #  DEFAULT (neutral): take asks <= FV-1, sell bids >= FV+1
        #  LONG:  sell_down_to DECREASES (sell at worse prices to free capacity)
        #  SHORT: buy_up_to INCREASES (buy at worse prices to free capacity)

        buy_up_to    = FV       # default: take asks < FV  (i.e. asks <= FV-1)
        sell_down_to = FV       # default: sell bids > FV  (i.e. bids >= FV+1)

        # Long inventory → progressively accept worse sell prices
        if pos > 20:  sell_down_to = FV - 1    # also sell bids >= FV
        if pos > 40:  sell_down_to = FV - 2    # also sell bids >= FV-1
        if pos > 60:  sell_down_to = FV - 3    # also sell bids >= FV-2

        # Short inventory → progressively accept worse buy prices
        if pos < -20: buy_up_to = FV + 1       # also buy asks <= FV
        if pos < -40: buy_up_to = FV + 2       # also buy asks <= FV+1
        if pos < -60: buy_up_to = FV + 3       # also buy asks <= FV+2

        if od.sell_orders:
            for ask_px in sorted(od.sell_orders.keys()):
                if ask_px >= buy_up_to or buy_cap <= 0:
                    break
                qty = min(abs(od.sell_orders[ask_px]), buy_cap)
                if qty > 0:
                    orders.append(Order(product, ask_px, qty))
                    buy_cap -= qty

        if od.buy_orders:
            for bid_px in sorted(od.buy_orders.keys(), reverse=True):
                if bid_px <= sell_down_to or sell_cap <= 0:
                    break
                qty = min(od.buy_orders[bid_px], sell_cap)
                if qty > 0:
                    orders.append(Order(product, bid_px, -qty))
                    sell_cap -= qty

        # ═══════════════════════════════════════════════════════════
        #  PHASE 2: INVENTORY-SKEWED MAKER QUOTES
        # ═══════════════════════════════════════════════════════════
        #
        # Penny the book, capped at FV edges.
        # Inventory skew: shift quotes to encourage mean-reversion.
        #   Long  inventory → tighten ask (sell faster), widen bid
        #   Short inventory → tighten bid (buy faster), widen ask

        best_bid = max(od.buy_orders.keys()) if od.buy_orders else FV - 100
        best_ask = min(od.sell_orders.keys()) if od.sell_orders else FV + 100

        # Base quotes: penny the book, capped at FV edges
        our_bid = min(best_bid + 1, FV - 1)
        our_ask = max(best_ask - 1, FV + 1)

        # Inventory skew (shift quotes by 0-2 ticks based on position)
        inv_skew = 0
        if pos > 30:   inv_skew = -1   # Long → lower bid, lower ask
        if pos > 60:   inv_skew = -2
        if pos < -30:  inv_skew = 1    # Short → raise bid, raise ask
        if pos < -60:  inv_skew = 2

        our_bid += inv_skew
        our_ask += inv_skew

        # ═══════════════════════════════════════════════════════════
        #  ORDER LADDERING (3-tick spacing, matches L1→L2 gap)
        # ═══════════════════════════════════════════════════════════

        TICK_STEP = 3  # Matches observed L1→L2 gap of 2.75 ticks

        # ─── BID LADDERING ─────────────────────────────────────────
        if buy_cap > 0:
            # Level 1: Front of book
            qty1 = min(buy_cap, self.MAX_LOT)
            orders.append(Order(product, our_bid, qty1))
            buy_cap -= qty1

        if buy_cap > 0:
            # Level 2: Medium depth
            qty2 = min(buy_cap, self.MAX_LOT)
            orders.append(Order(product, our_bid - TICK_STEP, qty2))
            buy_cap -= qty2

        if buy_cap > 0:
            # Level 3: Deep sponge — all remaining capacity
            orders.append(Order(product, our_bid - (TICK_STEP * 2), buy_cap))
            buy_cap = 0

        # ─── ASK LADDERING ─────────────────────────────────────────
        if sell_cap > 0:
            # Level 1
            qty1 = min(sell_cap, self.MAX_LOT)
            orders.append(Order(product, our_ask, -qty1))
            sell_cap -= qty1

        if sell_cap > 0:
            # Level 2
            qty2 = min(sell_cap, self.MAX_LOT)
            orders.append(Order(product, our_ask + TICK_STEP, -qty2))
            sell_cap -= qty2

        if sell_cap > 0:
            # Level 3
            orders.append(Order(product, our_ask + (TICK_STEP * 2), -sell_cap))
            sell_cap = 0

        return orders