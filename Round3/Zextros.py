"""
IMC Prosperity 4 – Round 3: "Gloves Off"
==========================================
Products:
  • HYDROGEL_PACK              (Limit: 200) → Mean-Revert Market Maker
  • VELVETFRUIT_EXTRACT        (Limit: 200) → Light MM + Delta Hedge
  • VEV_4000..VEV_6500         (Limit: 300) → BS Options Market Maker

Strategy:
  HP  → FV anchor at 10,000, spread=16, layered passive quotes + inventory skew
  VEV → Black-Scholes fair value (σ≈0.30), market-make near-ATM, arb deep ITM
  VE  → Track EMA, light MM, bias orders to delta-hedge VEV exposure
"""

from datamodel import OrderDepth, TradingState, Order
from typing import List, Dict, Tuple, Optional
import json
import math

# ─── Black-Scholes helpers (no external deps) ────────────────────────────────

def _norm_cdf(x: float) -> float:
    """Standard normal CDF via math.erf."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)

def _bs_call(S: float, K: float, T: float, sigma: float) -> float:
    """European call price (r=0)."""
    if T <= 1e-12 or sigma <= 1e-12 or S <= 0:
        return max(0.0, S - K)
    sqrtT = math.sqrt(T)
    d1 = (math.log(S / K) + 0.5 * sigma * sigma * T) / (sigma * sqrtT)
    d2 = d1 - sigma * sqrtT
    return S * _norm_cdf(d1) - K * _norm_cdf(d2)

def _bs_delta(S: float, K: float, T: float, sigma: float) -> float:
    """BS call delta N(d1)."""
    if T <= 1e-12 or sigma <= 1e-12:
        return 1.0 if S > K else 0.0
    sqrtT = math.sqrt(T)
    d1 = (math.log(S / K) + 0.5 * sigma * sigma * T) / (sigma * sqrtT)
    return _norm_cdf(d1)

def _bs_vega(S: float, K: float, T: float, sigma: float) -> float:
    """BS vega for IV solver."""
    if T <= 1e-12 or sigma <= 1e-12 or S <= 0:
        return 0.0
    sqrtT = math.sqrt(T)
    d1 = (math.log(S / K) + 0.5 * sigma * sigma * T) / (sigma * sqrtT)
    return S * _norm_pdf(d1) * sqrtT

def _implied_vol(mkt_price: float, S: float, K: float, T: float,
                 tol: float = 1e-4, max_iter: int = 40) -> Optional[float]:
    """Newton-Raphson IV solver. Returns None if no convergence."""
    intrinsic = max(0.0, S - K)
    if mkt_price <= intrinsic + 0.01:
        return None
    sigma = 0.30
    for _ in range(max_iter):
        price = _bs_call(S, K, T, sigma)
        vega = _bs_vega(S, K, T, sigma)
        if vega < 1e-12:
            return None
        sigma -= (price - mkt_price) / vega
        if sigma <= 0.01:
            sigma = 0.01
        if abs(price - mkt_price) < tol:
            return sigma
    return sigma


# ═════════════════════════════════════════════════════════════════════════════
class Trader:

    # ── Position limits ──────────────────────────────────────────────────────
    HP_LIMIT  = 200
    VE_LIMIT  = 200
    VEV_LIMIT = 300

    # ── HP parameters ────────────────────────────────────────────────────────
    HP_ANCHOR_BASE = 10000
    HP_EMA_ALPHA   = 0.20
    HP_ANCHOR_ALPHA = 0.001
    HP_SKEW_TICKS  = 3        # max skew at full inventory

    # ── VE parameters ────────────────────────────────────────────────────────
    VE_EMA_ALPHA    = 0.15
    VE_ANCHOR_ALPHA = 0.001

    # ── VEV parameters ───────────────────────────────────────────────────────
    VEV_SIGMA       = 0.30    # fixed IV for pricing
    VEV_ACTIVE      = ["VEV_5200", "VEV_5300", "VEV_5400", "VEV_5500"]
    VEV_ARB         = ["VEV_4000"]
    VEV_ALL_STRIKES = {
        "VEV_4000": 4000, "VEV_4500": 4500, "VEV_5000": 5000,
        "VEV_5100": 5100, "VEV_5200": 5200, "VEV_5300": 5300,
        "VEV_5400": 5400, "VEV_5500": 5500, "VEV_6000": 6000,
        "VEV_6500": 6500,
    }
    # Half-spreads for active MM strikes (from data analysis)
    VEV_HALF_SPREAD = {
        "VEV_5200": 2, "VEV_5300": 1, "VEV_5400": 1, "VEV_5500": 1,
    }
    VEV_MM_SIZE = 8          # quote size per side per strike (was 20 → too aggressive)
    VEV_SOFT_POS_CAP = 50    # soft cap per strike to keep delta hedgeable
    VEV_MAX_TOTAL_DELTA = 150 # hard cap: never exceed this aggregate delta

    # ── TTE: Round 3 starts at 5 days ────────────────────────────────────────
    TTE_START_DAYS  = 5.0
    TICKS_PER_DAY   = 10000
    TICK_INTERVAL    = 100

    # ╔════════════════════════════════════════════════════════════════════════╗
    # ║                         ENTRY POINT                                  ║
    # ╚════════════════════════════════════════════════════════════════════════╝

    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:
        result: Dict[str, List[Order]] = {}
        conversions = 0
        td = self._load(state.traderData)

        # Track time for TTE calculation
        ts = state.timestamp
        td["tick_count"] = td.get("tick_count", 0) + 1

        # Get VE mid-price for options pricing (needed by VEV module)
        ve_mid = self._get_mid(state, "VELVETFRUIT_EXTRACT")
        if ve_mid is not None:
            td["last_ve_mid"] = ve_mid

        # 1. HYDROGEL_PACK — independent MM
        result["HYDROGEL_PACK"] = self._trade_hp(state, td)

        # 2. VEV options — compute orders + net delta
        vev_orders, net_delta = self._trade_vevs(state, td)
        result.update(vev_orders)

        # 3. VELVETFRUIT_EXTRACT — MM + delta hedge
        result["VELVETFRUIT_EXTRACT"] = self._trade_ve(state, td, net_delta)

        return result, conversions, self._save(td)

    # ╔════════════════════════════════════════════════════════════════════════╗
    # ║                      STATE MANAGEMENT                                ║
    # ╚════════════════════════════════════════════════════════════════════════╝

    def _load(self, raw: str) -> dict:
        defaults = {
            "hp_ema": None, "hp_anchor": None,
            "ve_ema": None, "ve_anchor": None,
            "last_ve_mid": None,
            "tick_count": 0,
        }
        if raw and raw.strip():
            try:
                x = json.loads(raw)
                if isinstance(x, dict):
                    defaults.update(x)
            except Exception:
                pass
        return defaults

    def _save(self, td: dict) -> str:
        try:
            return json.dumps(self._clean(td), separators=(",", ":"))
        except Exception:
            return ""

    def _clean(self, obj):
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return 0.0
            return round(obj, 10)
        if isinstance(obj, dict):
            return {k: self._clean(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._clean(v) for v in obj]
        return obj

    # ╔════════════════════════════════════════════════════════════════════════╗
    # ║                        UTILITY HELPERS                               ║
    # ╚════════════════════════════════════════════════════════════════════════╝

    @staticmethod
    def _pos(state: TradingState, product: str) -> int:
        return state.position.get(product, 0)

    @staticmethod
    def _mid(od: OrderDepth) -> Optional[float]:
        if not od.buy_orders or not od.sell_orders:
            return None
        return (max(od.buy_orders.keys()) + min(od.sell_orders.keys())) / 2.0

    def _get_mid(self, state: TradingState, product: str) -> Optional[float]:
        if product not in state.order_depths:
            return None
        return self._mid(state.order_depths[product])

    def _tte(self, td: dict) -> float:
        """Time to expiry in years. Day 0 tick 0 → 5/365, decays each tick."""
        elapsed_days = td["tick_count"] / self.TICKS_PER_DAY
        remaining = max(0.001, self.TTE_START_DAYS - elapsed_days)
        return remaining / 365.0

    # ╔════════════════════════════════════════════════════════════════════════╗
    # ║      MODULE 1: HYDROGEL_PACK — MEAN-REVERSION MARKET MAKER          ║
    # ╚════════════════════════════════════════════════════════════════════════╝

    def _trade_hp(self, state: TradingState, td: dict) -> List[Order]:
        product = "HYDROGEL_PACK"
        orders: List[Order] = []
        if product not in state.order_depths:
            return orders

        od  = state.order_depths[product]
        pos = self._pos(state, product)
        buy_cap  = self.HP_LIMIT - pos
        sell_cap = self.HP_LIMIT + pos

        # ── Update EMA / Anchor ──
        mid = self._mid(od)
        if td["hp_ema"] is None:
            td["hp_ema"] = mid if mid is not None else self.HP_ANCHOR_BASE
        elif mid is not None:
            td["hp_ema"] = self.HP_EMA_ALPHA * mid + (1 - self.HP_EMA_ALPHA) * td["hp_ema"]

        if td["hp_anchor"] is None:
            td["hp_anchor"] = float(self.HP_ANCHOR_BASE)
        elif mid is not None:
            td["hp_anchor"] = self.HP_ANCHOR_ALPHA * mid + (1 - self.HP_ANCHOR_ALPHA) * td["hp_anchor"]

        # ── Fair value with smooth inventory skew ──
        raw_fv = 0.50 * td["hp_ema"] + 0.50 * td["hp_anchor"]
        
        # ── Stronger Inventory Skew to reduce M2M drawdown ──
        inv_skew = -pos * (8.0 / self.HP_LIMIT)
        FV = round(raw_fv + inv_skew)

        # ── Phase 1: Take mispriced liquidity ──
        buy_up_to  = FV - 1   # only buy asks strictly below FV
        sell_down_to = FV + 1 # only sell bids strictly above FV

        # Relax thresholds when inventory is extended
        inv_ratio = abs(pos) / self.HP_LIMIT
        if pos > 0 and inv_ratio > 0.5:
            sell_down_to = FV - int(inv_ratio * 2)
        if pos < 0 and inv_ratio > 0.5:
            buy_up_to = FV + int(inv_ratio * 2)

        if od.sell_orders:
            for ask_px in sorted(od.sell_orders.keys()):
                if ask_px > buy_up_to or buy_cap <= 0:
                    break
                qty = min(abs(od.sell_orders[ask_px]), buy_cap)
                if qty > 0:
                    orders.append(Order(product, ask_px, qty))
                    buy_cap -= qty

        if od.buy_orders:
            for bid_px in sorted(od.buy_orders.keys(), reverse=True):
                if bid_px < sell_down_to or sell_cap <= 0:
                    break
                qty = min(od.buy_orders[bid_px], sell_cap)
                if qty > 0:
                    orders.append(Order(product, bid_px, -qty))
                    sell_cap -= qty

        # ── Phase 2: Passive quotes inside spread ──
        best_bid = max(od.buy_orders.keys()) if od.buy_orders else FV - 100
        best_ask = min(od.sell_orders.keys()) if od.sell_orders else FV + 100

        our_bid = min(best_bid + 1, FV - 1)
        our_ask = max(best_ask - 1, FV + 1)

        if buy_cap > 0:
            orders.append(Order(product, our_bid, buy_cap))
        if sell_cap > 0:
            orders.append(Order(product, our_ask, -sell_cap))

        return orders

    # ╔════════════════════════════════════════════════════════════════════════╗
    # ║      MODULE 2: VEV OPTIONS — BLACK-SCHOLES MARKET MAKER             ║
    # ╚════════════════════════════════════════════════════════════════════════╝

    def _trade_vevs(self, state: TradingState, td: dict) -> Tuple[Dict[str, List[Order]], float]:
        """Returns (dict of VEV orders, net portfolio delta for hedging)."""
        vev_orders: Dict[str, List[Order]] = {}
        net_delta = 0.0

        S = td.get("last_ve_mid")
        if S is None or S <= 0:
            return vev_orders, net_delta

        T = self._tte(td)
        sigma = self.VEV_SIGMA

        # ── Pre-compute current aggregate delta across ALL VEV positions ──
        current_total_delta = 0.0
        for vev_name, K in self.VEV_ALL_STRIKES.items():
            p = self._pos(state, vev_name)
            if p != 0:
                current_total_delta += p * _bs_delta(S, K, T, sigma)

        # ── Tier 1: DISABLED — near-ATM MM creates unhedgeable risk ──
        # VEV positions accumulate gamma/theta exposure that causes 16K+ drawdowns.
        # 4 strikes × 50 cap = 200 options delta vs VE hedge limit of 200 units.
        # The risk/reward is negative: spread capture < theta + adverse selection.
        # TODO: Re-enable with much tighter controls once HP+VE profitability is proven.

        # Just compute delta for existing positions (from previous fills or manual)
        for vev in self.VEV_ACTIVE:
            pos = self._pos(state, vev)
            if pos != 0:
                K = self.VEV_ALL_STRIKES[vev]
                net_delta += pos * _bs_delta(S, K, T, sigma)

        # ── Tier 2: Deep ITM arb (VEV_4000) ──
        for vev in self.VEV_ARB:
            if vev not in state.order_depths:
                continue

            K = self.VEV_ALL_STRIKES[vev]
            od = state.order_depths[vev]
            pos = self._pos(state, vev)
            buy_cap  = self.VEV_LIMIT - pos
            sell_cap = self.VEV_LIMIT + pos
            delta = _bs_delta(S, K, T, sigma)
            net_delta += pos * delta

            intrinsic = max(0.0, S - K)
            orders: List[Order] = []

            # Buy VEV if ask < intrinsic (free money)
            if od.sell_orders:
                for ask_px in sorted(od.sell_orders.keys()):
                    if ask_px >= intrinsic - 1 or buy_cap <= 0:
                        break
                    qty = min(abs(od.sell_orders[ask_px]), buy_cap, 30)
                    if qty > 0:
                        orders.append(Order(vev, ask_px, qty))
                        buy_cap -= qty

            # Sell VEV if bid > intrinsic (free money)
            if od.buy_orders:
                for bid_px in sorted(od.buy_orders.keys(), reverse=True):
                    if bid_px <= intrinsic + 1 or sell_cap <= 0:
                        break
                    qty = min(od.buy_orders[bid_px], sell_cap, 30)
                    if qty > 0:
                        orders.append(Order(vev, bid_px, -qty))
                        sell_cap -= qty

            # Passive quotes around intrinsic (small size — arb only)
            bid_p = int(math.floor(intrinsic - 1))
            ask_p = int(math.ceil(intrinsic + 1))
            if bid_p >= ask_p:
                ask_p = bid_p + 1

            q = min(8, buy_cap)
            if q > 0:
                orders.append(Order(vev, bid_p, q))
            q = min(8, sell_cap)
            if q > 0:
                orders.append(Order(vev, ask_p, -q))

            vev_orders[vev] = orders

        # ── Compute delta for remaining (non-traded) VEV positions ──
        for vev, K in self.VEV_ALL_STRIKES.items():
            if vev in self.VEV_ACTIVE or vev in self.VEV_ARB:
                continue
            pos = self._pos(state, vev)
            if pos != 0:
                delta = _bs_delta(S, K, T, sigma)
                net_delta += pos * delta

        return vev_orders, net_delta

    # ╔════════════════════════════════════════════════════════════════════════╗
    # ║   MODULE 3: VELVETFRUIT_EXTRACT — PURE MM + SIZE-BASED HEDGE        ║
    # ╚════════════════════════════════════════════════════════════════════════╝
    #
    #  CRITICAL LESSON: FV-distortion hedging caused -100K death spiral.
    #  Skewing FV by 50+ ticks made every taker trade lose money, and the
    #  position oscillated max-long to max-short paying the spread each way.
    #
    #  NEW APPROACH: Pure MM (same proven logic as HP). Delta hedge ONLY
    #  through passive quote SIZE bias — never distort FV or taker logic.
    #

    def _trade_ve(self, state: TradingState, td: dict,
                  target_delta: float) -> List[Order]:
        product = "VELVETFRUIT_EXTRACT"
        orders: List[Order] = []
        if product not in state.order_depths:
            return orders

        od  = state.order_depths[product]
        pos = self._pos(state, product)
        buy_cap  = self.VE_LIMIT - pos
        sell_cap = self.VE_LIMIT + pos

        # ── Update EMA ──
        mid = self._mid(od)
        if td["ve_ema"] is None:
            td["ve_ema"] = mid if mid is not None else 5250.0
        elif mid is not None:
            td["ve_ema"] = self.VE_EMA_ALPHA * mid + (1 - self.VE_EMA_ALPHA) * td["ve_ema"]

        if td["ve_anchor"] is None:
            td["ve_anchor"] = mid if mid is not None else 5250.0
        elif mid is not None:
            td["ve_anchor"] = self.VE_ANCHOR_ALPHA * mid + (1 - self.VE_ANCHOR_ALPHA) * td["ve_anchor"]

        raw_fv = 0.50 * td["ve_ema"] + 0.50 * td["ve_anchor"]

        # ── Stronger pure inventory skew (NO hedge distortion of FV) ──
        skew = -pos * (6.0 / self.VE_LIMIT)  # max ±6 ticks at limit
        FV = round(raw_fv + skew)

        # ── Phase 1: Take only clearly mispriced liquidity ──
        # Same conservative logic as HP — never distort thresholds for hedging
        buy_up_to  = FV - 1
        sell_down_to = FV + 1

        if od.sell_orders:
            for ask_px in sorted(od.sell_orders.keys()):
                if ask_px > buy_up_to or buy_cap <= 0:
                    break
                qty = min(abs(od.sell_orders[ask_px]), buy_cap)
                if qty > 0:
                    orders.append(Order(product, ask_px, qty))
                    buy_cap -= qty

        if od.buy_orders:
            for bid_px in sorted(od.buy_orders.keys(), reverse=True):
                if bid_px < sell_down_to or sell_cap <= 0:
                    break
                qty = min(od.buy_orders[bid_px], sell_cap)
                if qty > 0:
                    orders.append(Order(product, bid_px, -qty))
                    sell_cap -= qty

        # ── Phase 2: Passive quotes with SIZE-based delta hedge ──
        best_bid = max(od.buy_orders.keys()) if od.buy_orders else FV - 100
        best_ask = min(od.sell_orders.keys()) if od.sell_orders else FV + 100

        our_bid = min(best_bid + 1, FV - 1)
        our_ask = max(best_ask - 1, FV + 1)

        # Delta hedge through SIZE bias (not FV distortion):
        # If we need to buy to hedge (hedge_err > 0), quote MORE on bid side
        # If we need to sell to hedge (hedge_err < 0), quote MORE on ask side
        ideal_hedge_pos = -target_delta * 0.5  # conservative: only hedge 50%
        hedge_err = ideal_hedge_pos - pos

        # Clamp hedge bias to avoid extreme one-sided quoting
        bid_bias = max(0, min(hedge_err, 30))      # extra bid size (0 to 30)
        ask_bias = max(0, min(-hedge_err, 30))      # extra ask size (0 to 30)

        bid_sz = min(buy_cap, max(1, int(buy_cap * 0.5 + bid_bias)))
        ask_sz = min(sell_cap, max(1, int(sell_cap * 0.5 + ask_bias)))

        if bid_sz > 0:
            orders.append(Order(product, our_bid, bid_sz))
        if ask_sz > 0:
            orders.append(Order(product, our_ask, -ask_sz))

        return orders