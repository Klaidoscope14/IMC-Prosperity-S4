from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import json
import math

class Trader:
    """Round 3 model built around:
    - microprice / wall-mid fair value for underlyings
    - mean-reverting terminal pricing for vouchers
    - strike smile shaping from historical IVs
    - inventory-aware quote skew
    - delta hedging with a cost threshold
    - drawdown-aware sizing
    """

    # =========================
    # Limits / instruments
    # =========================
    LIMITS = {
        "HYDROGEL_PACK": 200,
        "VELVETFRUIT_EXTRACT": 200,
        "VEV_4000": 300, "VEV_4500": 300,
        "VEV_5000": 300, "VEV_5100": 300, "VEV_5200": 300,
        "VEV_5300": 300, "VEV_5400": 300, "VEV_5500": 300,
        "VEV_6000": 300, "VEV_6500": 300,
    }

    STRIKES = {
        "VEV_4000": 4000, "VEV_4500": 4500, "VEV_5000": 5000,
        "VEV_5100": 5100, "VEV_5200": 5200, "VEV_5300": 5300,
        "VEV_5400": 5400, "VEV_5500": 5500, "VEV_6000": 6000,
        "VEV_6500": 6500,
    }

    UNDERLYINGS = {"HYDROGEL_PACK", "VELVETFRUIT_EXTRACT"}
    OPTIONS = set(STRIKES.keys())

    # VEV_4000/4500/5000: mean-reversion intrinsic-value trading
    MR_VEVS = {"VEV_4000", "VEV_4500", "VEV_5000"}
    BS_VEVS = {"VEV_5100", "VEV_5200", "VEV_5300", "VEV_5400", "VEV_5500"}
    SKIP_VEVS = {"VEV_6000", "VEV_6500"}
    DEEP_ITM = set()  # no longer skipped — traded via MR engine

    # FIX 6: Hard cap on total portfolio delta to prevent runaway exposure
    MAX_PORTFOLIO_DELTA = 120.0

    # ── HYDROGEL_PACK parameters (from 67.py) ──
    # Signal Weights
    OBI_WEIGHT = 3.0
    MR_WEIGHT = 2.5
    PAIRS_WEIGHT = 4.0
    
    # Counterparty Params
    M38_HP_OFFSET = 7
    INTERCEPT_SIZE = 80
    
    # Time Windows
    FAST_WINDOW = 30
    SLOW_WINDOW = 150
    
    # ── Mean-reversion parameters (from data analysis) ──
    # HYDROGEL: W=20, thresh=16 → 76% WR, +3.70 avg return at H=10
    HP_MR_LOOKBACK = 20
    HP_MR_THRESHOLD = 16.0
    HP_MR_AGGRESSION = 0.5      # fraction of deviation to fade
    # Per-strike MR configs: (window, threshold, base_size)
    # VEV_4000: W=5, T=6 → 97% WR, +5.29 avg (incredibly strong)
    # VEV_4500: W=5, T=5 → 94% WR, +3.95 avg (very strong)
    # VEV_5000: W=75, T=5 → 52% WR, +0.49 avg (weak — wide quotes only)
    MR_VEV_CONFIGS = {
        "VEV_4000": {"window": 5,  "threshold": 6.0, "size": 12, "edge": 2.0},
        "VEV_4500": {"window": 5,  "threshold": 5.0, "size": 10, "edge": 1.5},
        "VEV_5000": {"window": 75, "threshold": 5.0, "size": 5,  "edge": 0.5},
    }
    MR_VEV_QUOTE_WIDTH = 1

    # ── VELVETFRUIT_EXTRACT dual-mode strategy params (from 505708.py) ──
    # -- Trend detection --
    VE_EMA_FAST_ALPHA = 0.12     # fast EMA for trend signal
    VE_EMA_SLOW_ALPHA = 0.003    # slow EMA anchor
    VE_TREND_ALPHA = 0.005       # trend EMA
    VE_TREND_DIVERGE = 3.0       # fast-trend diverge threshold
    VE_MOMENTUM_WINDOW = 10      # ticks to measure momentum
    VE_MOMENTUM_THRESH = 3.0     # min pts over window to confirm trend

    # -- Trend-following mode --
    VE_TREND_TARGET_POS = 25     # target position size WITH the trend
    VE_TREND_SIZE = 12           # order size in trend mode
    VE_TREND_TAKE_EDGE = 0.5     # min edge to cross spread in trend
    VE_TREND_HOLD_FRAC = 0.7     # hold position until trend weakens to this

    # -- Mean-reversion mode (ranging market) --
    VE_MR_LOOKBACK = 20          # rolling mean window
    VE_MR_THRESHOLD = 3.0        # deviation threshold for MR signal
    VE_MR_FADE_FRACTION = 0.4    # how much of deviation to fade
    VE_MR_SIZE = 6               # order size in MR mode

    # -- Risk / position management --
    VE_MAX_POSITION = 40         # hard cap (never exceed)
    VE_INVENTORY_SKEW_K = 4.0    # inventory skew for passive quotes

    # Round 3 starts with 5 days to expiry in the final sim.
    TTE_START_DAYS = 4.0
    TICKS_PER_DAY = 1_000_000

    # Anchors / smoothing
    HP_ANCHOR_INIT = 10_000.0
    VE_ANCHOR_INIT = 5_250.0
    ALPHA_FAST = 0.20
    ALPHA_SLOW = 0.001
    # FIX 1: Faster VE anchor (was 0.0001 -> moved 1.4pts in 1000 ticks, now 14pts)
    ALPHA_VE_SLOW = 0.001

    # Order generation knobs
    MIN_EDGE = 1.0
    EDGE_BUFFER_UNDERLYING = 1.0
    # FIX 8: Wider option edge buffer to avoid over-trading thin edges
    EDGE_BUFFER_OPTION = 1.2
    BASE_SIZE_UNDERLYING = 12
    # FIX 3: Smaller option sizes (was 8 -> 80 lots/tick across 10 strikes)
    BASE_SIZE_OPTION = 5
    MAX_SIZE_FRACTION = 0.18
    # FIX 2: Much cheaper hedging - only hedge when truly exposed
    HEDGE_MIN_EXPOSURE = 45.0
    HEDGE_FRACTION = 0.40
    HEDGE_COST_PER_UNIT = 0.50

    # Risk control
    HISTORY_LEN = 240
    IV_HISTORY_LEN = 360
    # FIX 7: Faster risk response - cut size sooner in drawdown
    DD_K = 6.0
    VOL_K = 1.8
    HARD_DD_FRAC = 0.06

    # Strike priors used for smile shaping
    IV_PRIORS = {
        "VEV_5000": 0.233,
        "VEV_5100": 0.231,
        "VEV_5200": 0.233,
        "VEV_5300": 0.236,
        "VEV_5400": 0.221,
        "VEV_5500": 0.240,
    }

    # =========================
    # Helpers
    # =========================
    @staticmethod
    def _norm_cdf(x: float) -> float:
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    @staticmethod
    def _norm_pdf(x: float) -> float:
        return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)

    @staticmethod
    def _clip(x: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, x))

    @staticmethod
    def _pos(state: TradingState, product: str) -> int:
        return state.position.get(product, 0)

    @staticmethod
    def _mid(od: Optional[OrderDepth]) -> Optional[float]:
        if od is None or not od.buy_orders or not od.sell_orders:
            return None
        return (max(od.buy_orders) + min(od.sell_orders)) / 2.0

    @staticmethod
    def _best_bid(od: Optional[OrderDepth]) -> Optional[int]:
        if od is None or not od.buy_orders:
            return None
        return max(od.buy_orders)

    @staticmethod
    def _best_ask(od: Optional[OrderDepth]) -> Optional[int]:
        if od is None or not od.sell_orders:
            return None
        return min(od.sell_orders)

    @staticmethod
    def _spread(od: Optional[OrderDepth]) -> float:
        bb = Trader._best_bid(od)
        ba = Trader._best_ask(od)
        if bb is None or ba is None:
            return 2.0
        return float(max(1, ba - bb))

    @staticmethod
    def _clean(obj):
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return 0.0
            return round(obj, 10)
        if isinstance(obj, dict):
            return {k: Trader._clean(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [Trader._clean(v) for v in obj]
        return obj

    def _load(self, raw: str) -> dict:
        defaults = {
            "hp_ema": None,
            "hp_anchor": float(self.HP_ANCHOR_INIT),
            "ve_ema": None,
            "ve_anchor": float(self.VE_ANCHOR_INIT),
            "ve_ema_slow": None,
            "mid_hist": defaultdict(list),
            "iv_hist": defaultdict(list),
            "spot_hist": [],
            "cash": 0.0,
            "peak_equity": -1e18,
            "equity_ewma": 0.0,
            "equity_vol": 0.0,
            "last_equity": None,
            "m38_active": 0,
            "m38_dir": 0,
            "ve_mr_fast": None,
            "ve_mr_slow": None,
            "ve_trend_ema": None,
        }
        if raw and raw.strip():
            try:
                x = json.loads(raw)
                if isinstance(x, dict):
                    for k in ["hp_ema", "hp_anchor", "ve_ema", "ve_anchor", "ve_ema_slow", "spot_hist", "cash", "peak_equity", "equity_ewma", "equity_vol", "last_equity", "m38_active", "m38_dir", "ve_mr_fast", "ve_mr_slow", "ve_trend_ema"]:
                        if k in x:
                            defaults[k] = x[k]
                    for k in ["mid_hist", "iv_hist"]:
                        if k in x and isinstance(x[k], dict):
                            dd = defaultdict(list)
                            for kk, vv in x[k].items():
                                dd[kk] = list(vv)
                            defaults[k] = dd
            except Exception:
                pass
        if not isinstance(defaults["mid_hist"], defaultdict):
            defaults["mid_hist"] = defaultdict(list, defaults["mid_hist"])
        if not isinstance(defaults["iv_hist"], defaultdict):
            defaults["iv_hist"] = defaultdict(list, defaults["iv_hist"])
        if not isinstance(defaults["spot_hist"], list):
            defaults["spot_hist"] = []
        return defaults

    def _save(self, td: dict) -> str:
        try:
            pack = dict(td)
            pack["mid_hist"] = dict(pack.get("mid_hist", {}))
            pack["iv_hist"] = dict(pack.get("iv_hist", {}))
            return json.dumps(self._clean(pack), separators=(",", ":"))
        except Exception:
            return ""

    def _update_ema(self, prev: Optional[float], x: float, alpha: float) -> float:
        if prev is None:
            return x
        return alpha * x + (1.0 - alpha) * prev

    def _hist_push(self, td: dict, key: str, product: str, value: float, cap: int) -> None:
        arr = td[key][product]
        arr.append(float(value))
        if len(arr) > cap:
            del arr[:-cap]

    def _microprice(self, od: OrderDepth) -> Optional[float]:
        if not od.buy_orders or not od.sell_orders:
            return None
        bb = max(od.buy_orders)
        ba = min(od.sell_orders)
        bid_vol = abs(od.buy_orders[bb])
        ask_vol = abs(od.sell_orders[ba])
        denom = bid_vol + ask_vol
        if denom <= 0:
            return 0.5 * (bb + ba)
        return (bb * ask_vol + ba * bid_vol) / denom

    def _wall_mid(self, od: OrderDepth) -> Optional[float]:
        """Weighted midpoint of the strongest few visible levels on each side."""
        if not od.buy_orders or not od.sell_orders:
            return None
        bids = sorted(od.buy_orders.items(), key=lambda kv: kv[0], reverse=True)[:3]
        asks = sorted(od.sell_orders.items(), key=lambda kv: kv[0])[:3]
        bid_den = sum(abs(q) for _, q in bids)
        ask_den = sum(abs(q) for _, q in asks)
        if bid_den <= 0 or ask_den <= 0:
            return None
        bid_wall = sum(px * abs(q) for px, q in bids) / bid_den
        ask_wall = sum(px * abs(q) for px, q in asks) / ask_den
        return 0.5 * (bid_wall + ask_wall)

    def _imbalance(self, od: OrderDepth) -> float:
        if not od.buy_orders or not od.sell_orders:
            return 0.0
        bb = max(od.buy_orders)
        ba = min(od.sell_orders)
        bid_vol = abs(od.buy_orders[bb])
        ask_vol = abs(od.sell_orders[ba])
        denom = bid_vol + ask_vol
        if denom <= 0:
            return 0.0
        return (bid_vol - ask_vol) / denom

    def _returns(self, xs: List[float]) -> List[float]:
        if len(xs) < 2:
            return []
        return [xs[i] - xs[i - 1] for i in range(1, len(xs))]

    def _realized_vol(self, xs: List[float]) -> float:
        rets = self._returns(xs)
        if len(rets) < 2:
            return 1.0
        mu = sum(rets) / len(rets)
        var = sum((r - mu) ** 2 for r in rets) / max(1, len(rets) - 1)
        return math.sqrt(max(var, 1e-9))

    def _trend_score(self, xs: List[float]) -> float:
        rets = self._returns(xs)
        if len(rets) < 6:
            return 0.0
        tail = rets[-12:]
        vol = self._realized_vol(xs)
        if vol <= 1e-9:
            return 0.0
        return sum(tail) / (len(tail) * vol)

    def _bachelier_call(self, mean_T: float, sd_T: float, strike: float) -> float:
        sd_T = max(sd_T, 1e-8)
        d = (mean_T - strike) / sd_T
        return (mean_T - strike) * self._norm_cdf(d) + sd_T * self._norm_pdf(d)

    def _ou_terminal(self, spot: float, mu: float, sigma_day: float, kappa_day: float, t_days: float) -> Tuple[float, float]:
        """Exact terminal mean/std of OU with day units."""
        t_days = max(t_days, 1e-8)
        kappa_day = max(kappa_day, 1e-6)
        mean_T = mu + (spot - mu) * math.exp(-kappa_day * t_days)
        var_T = (sigma_day * sigma_day) * (1.0 - math.exp(-2.0 * kappa_day * t_days)) / (2.0 * kappa_day)
        return mean_T, math.sqrt(max(var_T, 1e-8))

    def _bs_call(self, S: float, K: float, T: float, sigma: float) -> float:
        if S <= 0 or K <= 0:
            return max(S - K, 0.0)
        if T <= 1e-10:
            return max(S - K, 0.0)
        sigma = max(sigma, 1e-8)
        try:
            srt = math.sqrt(T)
            sig = sigma * srt
            d1 = (math.log(S / K) + 0.5 * sigma * sigma * T) / sig
            d2 = d1 - sig
            return S * self._norm_cdf(d1) - K * self._norm_cdf(d2)
        except Exception:
            return max(S - K, 0.0)

    def _bs_delta(self, S: float, K: float, T: float, sigma: float) -> float:
        if S <= 0 or K <= 0:
            return 1.0 if S > K else 0.0
        if T <= 1e-10:
            return 1.0 if S > K else 0.0
        sigma = max(sigma, 1e-8)
        try:
            d1 = (math.log(S / K) + 0.5 * sigma * sigma * T) / (sigma * math.sqrt(T))
            return self._norm_cdf(d1)
        except Exception:
            return 1.0 if S > K else 0.0

    def _implied_vol(self, price: float, S: float, K: float, T: float) -> float:
        intrinsic = max(S - K, 0.0)
        if price <= intrinsic + 1e-9:
            return 1e-6
        lo, hi = 1e-4, 4.0
        for _ in range(60):
            mid = (lo + hi) / 2.0
            p = self._bs_call(S, K, T, mid)
            if p < price:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    # =========================
    # Underlying fair value
    # =========================
    def _underlying_state(self, td: dict, product: str, od: Optional[OrderDepth]) -> Tuple[float, float, float, float, float, float, float, float]:
        """Returns fair, mid, micro, wall, spread, imbalance, trend, confidence."""
        if product == "HYDROGEL_PACK":
            ema = td["hp_ema"] if td["hp_ema"] is not None else self.HP_ANCHOR_INIT
            anchor = td["hp_anchor"] if td["hp_anchor"] is not None else self.HP_ANCHOR_INIT
        else:
            ema = td["ve_ema"] if td["ve_ema"] is not None else self.VE_ANCHOR_INIT
            anchor = td["ve_anchor"] if td["ve_anchor"] is not None else self.VE_ANCHOR_INIT

        if od is None:
            base = 0.55 * ema + 0.45 * anchor
            return base, base, base, base, 2.0, 0.0, 0.0, 0.0

        mid = self._mid(od)
        micro = self._microprice(od)
        wall = self._wall_mid(od)
        spread = self._spread(od)
        imbalance = self._imbalance(od)
        hist = td["mid_hist"][product]
        trend = self._trend_score(hist)

        raw = wall if wall is not None else (micro if micro is not None else mid if mid is not None else ema)
        fair = 0.75 * raw + 0.15 * float(ema) + 0.10 * (mid if mid is not None else raw)
        fair += 0.15 * imbalance * max(1.0, spread)
        fair = round(fair)

        conf = self._clip(1.2 / max(spread, 1.0) + 0.25 * abs(imbalance) - 0.08 * abs(trend), 0.0, 1.0)
        return fair, float(mid if mid is not None else fair), float(micro if micro is not None else fair), float(wall if wall is not None else fair), spread, imbalance, trend, conf

    # =========================
    # Option fair value
    # =========================
    def _option_state(self, td: dict, product: str, spot_fair: float, t_days: float, od: Optional[OrderDepth]) -> Tuple[float, float, float, float, float, float, float]:
        """Returns fair_price, model_delta, model_iv, market_iv, sigma_day, mean_T, sd_T."""
        strike = self.STRIKES[product]
        spot_hist = td["mid_hist"]["VELVETFRUIT_EXTRACT"]
        slow_ema = td.get("ve_ema_slow")
        mu = float(slow_ema if slow_ema is not None else self.VE_ANCHOR_INIT)

        # Price volatility in price units/day, not returns
        base_sigma = self._realized_vol(spot_hist[-80:])
        # FIX 4: Tighter sigma bounds to prevent extreme terminal distributions
        base_sigma = self._clip(base_sigma, 20.0, 120.0)

        # Strike smile shaping: a mild convex smile with slight skew works well in this market.
        x = (strike - 5250.0) / 500.0
        smile_mult = self._clip(1.0 + 0.055 * x * x - 0.012 * x, 0.85, 1.18)
        sigma_day = base_sigma * smile_mult

        trend = self._trend_score(spot_hist)
        # Faster or slower mean reversion depending on regime; strong trend -> less reversion.
        # FIX 5: Tighter kappa bounds - avoid extremes of too-weak or too-strong reversion
        kappa_day = self._clip(0.075 + 0.0007 * abs(spot_fair - mu) / max(sigma_day, 1.0) + 0.02 * max(0.0, -trend), 0.06, 0.18)

        mean_T, sd_T = self._ou_terminal(spot_fair, mu, sigma_day, kappa_day, t_days)
        fair_price = self._bachelier_call(mean_T, sd_T, strike)
        fair_price = max(fair_price, max(spot_fair - strike, 0.0))

        t_years = max(t_days / 365.0, 1e-8)
        model_iv = self._implied_vol(max(fair_price, max(spot_fair - strike, 0.0) + 1e-6), spot_fair, strike, t_years)

        market_iv = self.IV_PRIORS.get(product, 0.233)
        if od is not None:
            mid = self._mid(od)
            if mid is not None:
                market_iv = self._implied_vol(max(mid, max(spot_fair - strike, 0.0) + 1e-6), spot_fair, strike, t_years)

        delta = math.exp(-kappa_day * t_days) * self._norm_cdf((mean_T - strike) / max(sd_T, 1e-8))
        return fair_price, delta, model_iv, market_iv, sigma_day, mean_T, sd_T

    # =========================
    # Risk management
    # =========================
    def _update_cash_from_trades(self, td: dict, state: TradingState) -> None:
        own = getattr(state, "own_trades", None)
        if not own:
            return
        for _, trades in own.items():
            if not trades:
                continue
            for tr in trades:
                qty = getattr(tr, "quantity", 0)
                price = getattr(tr, "price", 0)
                buyer = getattr(tr, "buyer", "")
                seller = getattr(tr, "seller", "")
                if buyer == "SUBMISSION":
                    signed_qty = abs(qty)
                elif seller == "SUBMISSION":
                    signed_qty = -abs(qty)
                else:
                    signed_qty = qty
                td["cash"] -= signed_qty * price

    def _equity_proxy(self, td: dict, state: TradingState, fair_values: Dict[str, float]) -> float:
        eq = float(td.get("cash", 0.0))
        for p, fv in fair_values.items():
            eq += self._pos(state, p) * fv
        return eq

    def _risk_multiplier(self, td: dict, equity: float) -> float:
        peak = float(td.get("peak_equity", equity))
        peak = max(peak, equity)
        td["peak_equity"] = peak
        drawdown = max(0.0, peak - equity)
        dd_frac = drawdown / max(abs(peak), 100000.0)

        prev = td.get("last_equity")
        delta = 0.0 if prev is None else equity - float(prev)
        td["last_equity"] = equity

        td["equity_ewma"] = 0.96 * float(td.get("equity_ewma", 0.0)) + 0.04 * equity
        td["equity_vol"] = 0.96 * float(td.get("equity_vol", 0.0)) + 0.04 * abs(delta)
        vol_norm = td["equity_vol"] / max(abs(td["equity_ewma"]), 1000.0)

        risk_dd = math.exp(-self.DD_K * max(0.0, dd_frac - 0.01))
        risk_vol = 1.0 / (1.0 + self.VOL_K * max(0.0, vol_norm - 0.002))
        risk = self._clip(risk_dd * risk_vol, 0.15, 1.0)
        if dd_frac > self.HARD_DD_FRAC:
            risk = min(risk, 0.25)
        return risk

    # =========================
    # Trading helpers
    # =========================
    def _quote_size(self, limit: int, confidence: float, risk_mult: float, base: int) -> int:
        raw = base + confidence * limit * self.MAX_SIZE_FRACTION * risk_mult
        return max(1, min(limit, int(round(raw))))

    def _trade_underlying(self, state: TradingState, td: dict, product: str, fair: float, risk_mult: float, conf: float) -> List[Order]:
        od = state.order_depths.get(product)
        if od is None:
            return []

        pos = self._pos(state, product)
        limit = self.LIMITS[product]
        bb = self._best_bid(od)
        ba = self._best_ask(od)
        spread = self._spread(od)
        mid = self._mid(od)
        micro = self._microprice(od)
        ref = micro if micro is not None else mid if mid is not None else fair
        gap = fair - ref
        hist = td["mid_hist"].get(product, [])
        trend = self._trend_score(hist)
        imbalance = self._imbalance(od)

        # ── HYDROGEL mean-reversion overlay (W=20, T=16, 76% WR) ──
        mr_bias = 0.0
        if product == "HYDROGEL_PACK" and len(hist) >= self.HP_MR_LOOKBACK:
            lookback = hist[-self.HP_MR_LOOKBACK:]
            rolling_mean = sum(lookback) / len(lookback)
            # Current mid vs rolling mean
            cur_mid = mid if mid is not None else fair
            deviation = cur_mid - rolling_mean
            if abs(deviation) > self.HP_MR_THRESHOLD:
                # Price overextended from rolling mean — fade it
                mr_bias = -deviation * self.HP_MR_AGGRESSION
                fair = fair + mr_bias

        # If the book is strongly one-sided, fade less aggressively.
        anti_mr = (imbalance > 0.15 and gap < 0) or (imbalance < -0.15 and gap > 0)
        anti_mr = anti_mr or (trend > 1.0 and gap < 0) or (trend < -1.0 and gap > 0)
        hard_de_risk = risk_mult <= 0.30

        buy_cap = max(0, limit - pos)
        sell_cap = max(0, limit + pos)
        orders: List[Order] = []

        buy_thresh = fair - self.EDGE_BUFFER_UNDERLYING
        sell_thresh = fair + self.EDGE_BUFFER_UNDERLYING
        if anti_mr:
            buy_thresh -= 1.0
            sell_thresh += 1.0

        if od.sell_orders and buy_cap > 0 and not hard_de_risk:
            for ask in sorted(od.sell_orders.keys()):
                if ask > buy_thresh:
                    break
                qty = min(abs(od.sell_orders[ask]), buy_cap)
                qty = min(qty, self._quote_size(limit, conf, risk_mult, self.BASE_SIZE_UNDERLYING))
                if qty > 0:
                    orders.append(Order(product, ask, qty))
                    buy_cap -= qty
                    if buy_cap <= 0:
                        break

        if od.buy_orders and sell_cap > 0 and not hard_de_risk:
            for bid in sorted(od.buy_orders.keys(), reverse=True):
                if bid < sell_thresh:
                    break
                qty = min(abs(od.buy_orders[bid]), sell_cap)
                qty = min(qty, self._quote_size(limit, conf, risk_mult, self.BASE_SIZE_UNDERLYING))
                if qty > 0:
                    orders.append(Order(product, bid, -qty))
                    sell_cap -= qty
                    if sell_cap <= 0:
                        break

        if bb is not None and ba is not None:
            bid_px = min(bb + 1, int(math.floor(fair)) - 1)
            ask_px = max(ba - 1, int(math.ceil(fair)) + 1)
        else:
            bid_px = int(math.floor(fair)) - 1
            ask_px = int(math.ceil(fair)) + 1

        # Shift the whole quote band in inventory direction to help unwind positions.
        # For HYDROGEL with MR active, increase inventory skew to unwind faster
        skew_mult = 3.0 if (product == "HYDROGEL_PACK" and abs(mr_bias) > 0.5) else 2.0
        inventory_skew = int((pos / max(limit, 1)) * skew_mult)
        bid_px -= inventory_skew
        ask_px -= inventory_skew

        if anti_mr:
            bid_px -= 1
            ask_px += 1

        if ask_px <= bid_px:
            ask_px = bid_px + 1

        size = self._quote_size(limit, conf, risk_mult, self.BASE_SIZE_UNDERLYING)
        if buy_cap > 0 and bid_px >= 1:
            orders.append(Order(product, bid_px, min(size, buy_cap)))
        if sell_cap > 0 and ask_px >= 1:
            orders.append(Order(product, ask_px, -min(size, sell_cap)))
        return orders

    def _trade_hydrogel(self, state: TradingState, td: dict, risk_mult: float) -> List[Order]:
        """Advanced HYDROGEL_PACK Specialist (from 67.py).
        Features:
        1. Microprice-based Fair Value.
        2. Order Book Imbalance (OBI) Signals.
        3. Counterparty (Mark 38) Detection and Reaction.
        4. Dynamic Spreads based on Volatility.
        5. Trend-aware Inventory Skew.
        """
        product = "HYDROGEL_PACK"
        od = state.order_depths.get(product)
        if not od:
            return []

        # 1. Microstructure Analysis
        bb_list = sorted(od.buy_orders.keys(), reverse=True)
        ba_list = sorted(od.sell_orders.keys())
        if not bb_list or not ba_list:
            return []
        
        bb, ba = bb_list[0], ba_list[0]
        bv = abs(od.buy_orders[bb])
        av = abs(od.sell_orders[ba])
        mid = (bb + ba) / 2.0
        
        # Microprice (Weighted by imbalance)
        mp = (bb * av + ba * bv) / (av + bv) if (av + bv) > 0 else mid
        obi = (bv - av) / (bv + av) if (av + bv) > 0 else 0.0
        
        # 2. Update History & Rolling Stats
        hist = td.get("mid_hist", {}).get(product, [])
        hist.append(mid)
        if len(hist) > 300: hist = hist[-300:]
        if "mid_hist" not in td: td["mid_hist"] = {}
        td["mid_hist"][product] = hist
        
        # 3. Counterparty Detection (Mark 38)
        # Look for trades at mid +/- 8 in market_trades
        m38_signal = 0
        for t in state.market_trades.get(product, []):
            offset = t.price - mid
            if abs(offset) >= 7.5:
                # Detected dumb money sweep!
                m38_signal = -1 if offset > 0 else 1 # Fade them
                td["m38_active"] = 3 # Signal stays active for 3 ticks
        
        if td.get("m38_active", 0) > 0:
            td["m38_active"] -= 1
            if m38_signal == 0: # If not detected this tick, use persistence
                # We need to remember the direction from previous tick
                m38_signal = td.get("m38_dir", 0)
        td["m38_dir"] = m38_signal

        # 4. Pairs Signal (VE/HP correlation)
        ve_od = state.order_depths.get("VELVETFRUIT_EXTRACT")
        pairs_sig = 0
        if ve_od:
            ve_bb = max(ve_od.buy_orders.keys()) if ve_od.buy_orders else None
            ve_ba = min(ve_od.sell_orders.keys()) if ve_od.sell_orders else None
            if ve_bb and ve_ba:
                ve_mid = (ve_bb + ve_ba) / 2.0
                hp_fair_from_ve = ve_mid / 0.5250
                pairs_sig = hp_fair_from_ve - mid
        
        # 5. Signal Composition
        # Mean Reversion
        mr_sig = 0
        if len(hist) >= self.FAST_WINDOW:
            ma = sum(hist[-self.FAST_WINDOW:]) / self.FAST_WINDOW
            mr_sig = ma - mid
            
        combined_signal = (mr_sig * self.MR_WEIGHT) + (obi * self.OBI_WEIGHT) + (m38_signal * 6.0) + (pairs_sig * self.PAIRS_WEIGHT)
        
        # 6. Inventory Management
        pos = self._pos(state, product)
        limit = self.LIMITS[product]
        inv_frac = pos / limit
        
        # Fair Value Adjustment
        fair = mp + (combined_signal * 0.4)
        # Non-linear inventory skew
        fair -= math.copysign(abs(inv_frac)**1.1, inv_frac) * 10.0 
        
        orders = []
        buy_cap = limit - pos
        sell_cap = limit + pos
        
        # 7. Order Placement
        # Layer 1: Passive Intercept (The high-alpha Mark 38 hook)
        # Protected from skew to keep the alpha
        i_buy_px = int(round(mid - self.M38_HP_OFFSET))
        i_sell_px = int(round(mid + self.M38_HP_OFFSET))
        
        if abs(inv_frac) < 0.8: # Only skip if near hard limit
            if buy_cap > 0:
                orders.append(Order(product, i_buy_px, min(self.INTERCEPT_SIZE, buy_cap)))
                buy_cap -= min(self.INTERCEPT_SIZE, buy_cap)
            if sell_cap > 0:
                orders.append(Order(product, i_sell_px, -min(self.INTERCEPT_SIZE, sell_cap)))
                sell_cap -= min(self.INTERCEPT_SIZE, sell_cap)

        # Layer 2: Signal-based MM
        # Quote around fair value
        bid_px = min(int(math.floor(fair - 1)), bb + 1)
        ask_px = max(int(math.ceil(fair + 1)), ba - 1)
        
        if bid_px >= ba: bid_px = ba - 1
        if ask_px <= bb: ask_px = bb + 1
        
        if buy_cap > 0:
            orders.append(Order(product, bid_px, min(40, buy_cap)))
        if sell_cap > 0:
            orders.append(Order(product, ask_px, -min(40, sell_cap)))

        # Layer 3: Aggressive Taking (Cross spread)
        # Lower threshold if bot is active
        take_thresh = 6.0 if td.get("m38_active", 0) > 0 else 9.0
        if combined_signal > take_thresh and ba <= fair - 2 and buy_cap > 0:
            orders.append(Order(product, ba, min(25, buy_cap)))
        elif combined_signal < -take_thresh and bb >= fair + 2 and sell_cap > 0:
            orders.append(Order(product, bb, -min(25, sell_cap)))

        return orders

    def _trade_velvetfruit(self, state: TradingState, td: dict, risk_mult: float) -> List[Order]:
        """VELVETFRUIT_EXTRACT dual-mode strategy (from 505708.py).

        Two operating modes based on regime detection:
        - TREND MODE: build position WITH the trend, cross spread to enter,
          hold until trend exhausts. This is where the big PnL comes from.
        - MR MODE: fade deviations from rolling mean in choppy/range-bound
          conditions. Small size, passive quoting. Harvests spread.
        """
        product = "VELVETFRUIT_EXTRACT"
        od = state.order_depths.get(product)
        if od is None:
            return []

        bb = self._best_bid(od)
        ba = self._best_ask(od)
        mid = self._mid(od)
        if bb is None or ba is None or mid is None:
            return []

        pos = self._pos(state, product)
        limit = self.LIMITS[product]
        spread = self._spread(od)
        micro = self._microprice(od)
        imbalance = self._imbalance(od)

        # ── Update EMAs ──
        ve_fast = td.get("ve_mr_fast")
        ve_slow_mr = td.get("ve_mr_slow")
        ve_trend = td.get("ve_trend_ema")
        ve_fast = self._update_ema(ve_fast, float(mid), self.VE_EMA_FAST_ALPHA)
        ve_slow_mr = self._update_ema(ve_slow_mr, float(mid), self.VE_EMA_SLOW_ALPHA)
        ve_trend = self._update_ema(ve_trend, float(mid), self.VE_TREND_ALPHA)
        td["ve_mr_fast"] = ve_fast
        td["ve_mr_slow"] = ve_slow_mr
        td["ve_trend_ema"] = ve_trend

        # ── Regime detection ──
        # 1. EMA divergence: fast vs trend
        in_downtrend = False
        in_uptrend = False
        trend_strength = 0.0
        if ve_fast is not None and ve_trend is not None:
            trend_strength = ve_fast - ve_trend
            if trend_strength < -self.VE_TREND_DIVERGE:
                in_downtrend = True
            elif trend_strength > self.VE_TREND_DIVERGE:
                in_uptrend = True

        # 2. Momentum confirmation: recent price movement over N ticks
        hist = td["mid_hist"].get(product, [])
        momentum = 0.0
        if len(hist) >= self.VE_MOMENTUM_WINDOW:
            momentum = float(mid) - hist[-self.VE_MOMENTUM_WINDOW]

        # Confirm trend with momentum (both must agree)
        trend_confirmed = False
        if in_downtrend and momentum < -self.VE_MOMENTUM_THRESH:
            trend_confirmed = True
        elif in_uptrend and momentum > self.VE_MOMENTUM_THRESH:
            trend_confirmed = True

        # Also activate trend mode on strong momentum alone
        # (catches trends before the slow EMA diverges)
        if not trend_confirmed and abs(momentum) > self.VE_MOMENTUM_THRESH * 1.5:
            if momentum < 0:
                in_downtrend = True
                trend_confirmed = True
            else:
                in_uptrend = True
                trend_confirmed = True

        in_trend = in_downtrend or in_uptrend

        # ── Hard position limits ──
        max_pos = self.VE_MAX_POSITION
        buy_cap = max(0, max_pos - pos)
        sell_cap = max(0, max_pos + pos)

        orders: List[Order] = []

        # ═══════════════════════════════════════════
        # MODE 1: TREND-FOLLOWING
        # ═══════════════════════════════════════════
        if in_trend and trend_confirmed:
            trend_dir = -1 if in_downtrend else +1  # -1=short, +1=long
            target_pos = trend_dir * self.VE_TREND_TARGET_POS
            size = max(1, int(self.VE_TREND_SIZE * risk_mult))

            # How far are we from target?
            pos_deficit = target_pos - pos  # negative = need to sell more

            # ── AGGRESSIVE TAKE: cross spread to build position ──
            if pos_deficit < 0 and od.buy_orders and sell_cap > 0:
                # Need to sell → take bids
                for bid in sorted(od.buy_orders.keys(), reverse=True):
                    edge = float(bid) - float(mid) + 1.0  # we expect price to drop further
                    if in_downtrend and edge >= -self.VE_TREND_TAKE_EDGE:
                        qty = min(abs(od.buy_orders[bid]), sell_cap, size, abs(pos_deficit))
                        if qty > 0:
                            orders.append(Order(product, bid, -qty))
                            sell_cap -= qty
                            pos_deficit += qty
                            if sell_cap <= 0 or pos_deficit >= 0:
                                break

            elif pos_deficit > 0 and od.sell_orders and buy_cap > 0:
                # Need to buy → take asks
                for ask in sorted(od.sell_orders.keys()):
                    edge = float(mid) - float(ask) + 1.0  # we expect price to rise further
                    if in_uptrend and edge >= -self.VE_TREND_TAKE_EDGE:
                        qty = min(abs(od.sell_orders[ask]), buy_cap, size, abs(pos_deficit))
                        if qty > 0:
                            orders.append(Order(product, ask, qty))
                            buy_cap -= qty
                            pos_deficit -= qty
                            if buy_cap <= 0 or pos_deficit <= 0:
                                break

            # ── PASSIVE QUOTING: also place limit orders to build position ──
            if spread > 2:
                bid_px = bb + 1
                ask_px = ba - 1
            else:
                bid_px = bb
                ask_px = ba

            # In downtrend: aggressive ask, suppress bid
            # In uptrend: aggressive bid, suppress ask
            if in_downtrend:
                # Tighten ask to get filled selling
                ask_px = max(ask_px - 1, bb + 1)
                if sell_cap > 0 and ask_px >= 1:
                    qty = max(1, min(size, sell_cap))
                    orders.append(Order(product, ask_px, -qty))
                # Only post bid if we need to UNWIND a wrong-way position
                if pos > 0 and buy_cap > 0:
                    # We're long in a downtrend — don't add to it
                    pass
                # No bid at all in downtrend (don't accumulate long)
            else:  # in_uptrend
                # Tighten bid to get filled buying
                bid_px = min(bid_px + 1, ba - 1)
                if buy_cap > 0 and bid_px >= 1:
                    qty = max(1, min(size, buy_cap))
                    orders.append(Order(product, bid_px, qty))
                # No ask in uptrend (don't accumulate short)

        # ═══════════════════════════════════════════
        # MODE 2: MEAN-REVERSION (ranging market)
        # ═══════════════════════════════════════════
        else:
            # ── Rolling mean signal ──
            rolling_mean = None
            deviation = 0.0
            signal = 0

            if len(hist) >= self.VE_MR_LOOKBACK:
                window = hist[-self.VE_MR_LOOKBACK:]
                rolling_mean = sum(window) / len(window)
                deviation = mid - rolling_mean

                if deviation > self.VE_MR_THRESHOLD:
                    signal = -1  # price above mean → sell
                elif deviation < -self.VE_MR_THRESHOLD:
                    signal = +1  # price below mean → buy

            # ── Fair value ──
            ref = float(micro if micro is not None else mid)
            fair = ref
            if rolling_mean is not None and abs(deviation) > self.VE_MR_THRESHOLD:
                fair = ref - deviation * self.VE_MR_FADE_FRACTION
            fair += imbalance * 0.3
            fair = round(fair)

            size = max(1, int(self.VE_MR_SIZE * risk_mult))

            # ── If holding trend position in flat market, UNWIND it ──
            if abs(pos) > 5:
                # We have leftover trend position — unwind passively
                if pos > 0:
                    # Long position to unwind — sell
                    sell_px = max(ba - 1, int(fair)) if spread > 2 else ba
                    unwind_size = min(size * 2, sell_cap, abs(pos))
                    if unwind_size > 0 and sell_px >= 1:
                        orders.append(Order(product, sell_px, -unwind_size))
                        sell_cap -= unwind_size
                elif pos < 0:
                    # Short position to unwind — buy
                    buy_px = min(bb + 1, int(fair)) if spread > 2 else bb
                    unwind_size = min(size * 2, buy_cap, abs(pos))
                    if unwind_size > 0 and buy_px >= 1:
                        orders.append(Order(product, buy_px, unwind_size))
                        buy_cap -= unwind_size

            # ── Passive MR quoting ──
            if spread > 2:
                bid_px = bb + 1
                ask_px = ba - 1
            else:
                bid_px = bb
                ask_px = ba

            # Signal bias
            if signal > 0:
                bid_px = min(bid_px + 1, int(fair))
            elif signal < 0:
                ask_px = max(ask_px - 1, int(fair))

            # Inventory skew
            inv_frac = pos / max(limit, 1)
            inventory_skew = int(inv_frac * self.VE_INVENTORY_SKEW_K)
            bid_px -= inventory_skew
            ask_px -= inventory_skew

            if ask_px <= bid_px:
                ask_px = bid_px + 1

            buy_quote_size = max(1, min(size, buy_cap))
            sell_quote_size = max(1, min(size, sell_cap))

            # Reduce quoting when inventory building up
            if pos > max_pos * 0.5:
                buy_quote_size = max(1, buy_quote_size // 2)
            elif pos < -max_pos * 0.5:
                sell_quote_size = max(1, sell_quote_size // 2)

            if buy_cap > 0 and bid_px >= 1:
                orders.append(Order(product, bid_px, buy_quote_size))
            if sell_cap > 0 and ask_px >= 1:
                orders.append(Order(product, ask_px, -sell_quote_size))

        return orders

    def _trade_mr_option(self, state: TradingState, td: dict, product: str, spot_fair: float, risk_mult: float) -> List[Order]:
        """Rolling-mean mean-reversion for VEV_4000/4500/5000.
        Uses per-strike window/threshold from data analysis.
        VEV_4000: W=5, T=6 → 97% WR    VEV_4500: W=5, T=5 → 94% WR
        VEV_5000: W=75, T=5 → 52% WR (weak, wide quotes only)"""
        od = state.order_depths.get(product)
        if od is None:
            return []

        cfg = self.MR_VEV_CONFIGS.get(product)
        if cfg is None:
            return []

        W = cfg["window"]
        thresh = cfg["threshold"]
        base_size = cfg["size"]
        edge = cfg["edge"]

        bb = self._best_bid(od)
        ba = self._best_ask(od)
        mid = self._mid(od)
        if bb is None or ba is None or mid is None:
            return []

        # Build rolling mean from mid_hist for this option
        hist = td["mid_hist"].get(product, [])
        self._hist_push(td, "mid_hist", product, float(mid), self.HISTORY_LEN)

        pos = self._pos(state, product)
        limit = self.LIMITS[product]
        buy_cap = max(0, limit - pos)
        sell_cap = max(0, limit + pos)
        orders: List[Order] = []
        spread = self._spread(od)

        # Compute rolling mean and signal
        signal = 0  # -1 = sell (price high), +1 = buy (price low)
        if len(hist) >= W:
            rolling_mean = sum(hist[-W:]) / W
            deviation = mid - rolling_mean
            if deviation > thresh:
                signal = -1  # price above mean → expect reversion down → sell
            elif deviation < -thresh:
                signal = +1  # price below mean → expect reversion up → buy

        # Size scales with risk_mult
        size = max(1, int(base_size * risk_mult))

        # ── Take mispriced book levels ──
        if signal >= 0 and od.sell_orders and buy_cap > 0:
            # Willing to buy: take asks below fair
            strike = self.STRIKES[product]
            intrinsic = max(spot_fair - strike, 0.0)
            fair_px = intrinsic + 3.0  # rough fair for taking
            for ask in sorted(od.sell_orders.keys()):
                if ask > fair_px - edge:
                    break
                qty = min(abs(od.sell_orders[ask]), buy_cap, size)
                if qty > 0:
                    orders.append(Order(product, ask, qty))
                    buy_cap -= qty
                    if buy_cap <= 0:
                        break

        if signal <= 0 and od.buy_orders and sell_cap > 0:
            strike = self.STRIKES[product]
            intrinsic = max(spot_fair - strike, 0.0)
            fair_px = intrinsic + 3.0
            for bid in sorted(od.buy_orders.keys(), reverse=True):
                if bid < fair_px + edge:
                    break
                qty = min(abs(od.buy_orders[bid]), sell_cap, size)
                if qty > 0:
                    orders.append(Order(product, bid, -qty))
                    sell_cap -= qty
                    if sell_cap <= 0:
                        break

        # ── Passive quotes — biased by signal + inventory ──
        w = self.MR_VEV_QUOTE_WIDTH
        bid_px = bb + 1 if spread > 2 else bb
        ask_px = ba - 1 if spread > 2 else ba

        # Signal bias: lean into the MR direction
        if signal > 0:    # bullish → tighten bid, widen ask
            bid_px = min(bid_px + 1, ba - 1)
        elif signal < 0:  # bearish → tighten ask, widen bid
            ask_px = max(ask_px - 1, bb + 1)

        # Inventory skew
        inventory_skew = int((pos / max(limit, 1)) * 2.0)
        bid_px -= inventory_skew
        ask_px -= inventory_skew

        if ask_px <= bid_px:
            ask_px = bid_px + 1

        if buy_cap > 0 and bid_px >= 1:
            orders.append(Order(product, bid_px, min(size, buy_cap)))
        if sell_cap > 0 and ask_px >= 1:
            orders.append(Order(product, ask_px, -min(size, sell_cap)))
        return orders

    def _trade_option(self, state: TradingState, td: dict, product: str, spot_fair: float, t_days: float, risk_mult: float) -> List[Order]:
        od = state.order_depths.get(product)
        if od is None:
            return []

        strike = self.STRIKES[product]
        fair_px, model_delta, model_iv, market_iv, sigma_day, mean_T, sd_T = self._option_state(td, product, spot_fair, t_days, od)
        if fair_px <= 0:
            return []

        mid = self._mid(od)
        bb = self._best_bid(od)
        ba = self._best_ask(od)
        spread = self._spread(od)
        pos = self._pos(state, product)
        limit = self.LIMITS[product]
        buy_cap = max(0, limit - pos)
        sell_cap = max(0, limit + pos)

        if product in self.SKIP_VEVS and fair_px < 0.8:
            return []
        # MR_VEVS are handled by _trade_mr_option, not here
        if product in self.MR_VEVS:
            return []

        px_edge = fair_px - (mid if mid is not None else fair_px)
        iv_edge = model_iv - market_iv
        confidence = self._clip(abs(px_edge) / max(spread, 1.0) + 0.5 * abs(iv_edge) / 0.02, 0.0, 1.0)

        # Stronger edge means more willingness to take; otherwise just make.
        direction = 1 if px_edge > 0 else -1 if px_edge < 0 else (1 if iv_edge > 0 else -1)
        edge_thresh = self.EDGE_BUFFER_OPTION
        if product in self.DEEP_ITM:
            edge_thresh = 0.8

        orders: List[Order] = []

        # TAKE if market is clearly below/above fair.
        if od.sell_orders and buy_cap > 0 and direction > 0:
            for ask in sorted(od.sell_orders.keys()):
                if ask > fair_px - edge_thresh:
                    break
                qty = min(abs(od.sell_orders[ask]), buy_cap)
                qty = min(qty, self._quote_size(limit, confidence, risk_mult, self.BASE_SIZE_OPTION))
                if qty > 0:
                    orders.append(Order(product, ask, qty))
                    buy_cap -= qty
                    if buy_cap <= 0:
                        break

        if od.buy_orders and sell_cap > 0 and direction < 0:
            for bid in sorted(od.buy_orders.keys(), reverse=True):
                if bid < fair_px + edge_thresh:
                    break
                qty = min(abs(od.buy_orders[bid]), sell_cap)
                qty = min(qty, self._quote_size(limit, confidence, risk_mult, self.BASE_SIZE_OPTION))
                if qty > 0:
                    orders.append(Order(product, bid, -qty))
                    sell_cap -= qty
                    if sell_cap <= 0:
                        break

        # Passive quoting around fair, skewed by inventory.
        if bb is not None and ba is not None:
            bid_px = min(bb + 1, int(math.floor(fair_px)) - 1)
            ask_px = max(ba - 1, int(math.ceil(fair_px)) + 1)
        else:
            bid_px = int(math.floor(fair_px)) - 1
            ask_px = int(math.ceil(fair_px)) + 1

        inventory_skew = int((pos / max(limit, 1)) * 2.0)
        bid_px -= inventory_skew
        ask_px -= inventory_skew

        if ask_px <= bid_px:
            ask_px = bid_px + 1

        if confidence < 0.15:
            # weak edge -> quote smaller and only if spread is reasonable
            quote_size = max(1, self.BASE_SIZE_OPTION // 2)
        else:
            quote_size = self._quote_size(limit, confidence, risk_mult, self.BASE_SIZE_OPTION)

        if buy_cap > 0 and bid_px >= 1:
            orders.append(Order(product, bid_px, min(quote_size, buy_cap)))
        if sell_cap > 0 and ask_px >= 1:
            orders.append(Order(product, ask_px, -min(quote_size, sell_cap)))

        # Save implied vols for later smile estimation / diagnostics.
        if mid is not None:
            t_years = max(t_days / 365.0, 1e-8)
            obs_iv = self._implied_vol(max(mid, max(spot_fair - strike, 0.0) + 1e-6), spot_fair, strike, t_years)
            self._hist_push(td, "iv_hist", product, obs_iv, self.IV_HISTORY_LEN)

        return orders

    def _delta_hedge(self, state: TradingState, td: dict, spot_product: str, spot_fair: float, t_days: float, risk_mult: float) -> List[Order]:
        od = state.order_depths.get(spot_product)
        if od is None:
            return []

        total_delta = float(self._pos(state, spot_product))
        for p in self.OPTIONS:
            pos = self._pos(state, p)
            if pos == 0:
                continue
            if p in self.SKIP_VEVS:
                continue
            if p in self.MR_VEVS:
                opt_delta = 1.0 if spot_fair > self.STRIKES[p] + 50 else (0.5 if spot_fair > self.STRIKES[p] else 0.0)
            else:
                fair_px, model_delta, _, _, _, _, _ = self._option_state(td, p, spot_fair, t_days, state.order_depths.get(p))
                _ = fair_px
                opt_delta = model_delta
            total_delta += pos * opt_delta

        exposure = abs(total_delta)
        if exposure < self.HEDGE_MIN_EXPOSURE:
            return []

        hedge_qty = int(round(exposure * self.HEDGE_FRACTION * risk_mult))
        if hedge_qty <= 0:
            return []

        bb = self._best_bid(od)
        ba = self._best_ask(od)
        if bb is None or ba is None:
            return []

        # FIX 2b: Scale benefit check by how far over threshold we are
        excess_ratio = exposure / max(self.HEDGE_MIN_EXPOSURE, 1.0)
        expected_benefit = 0.50 * hedge_qty * min(excess_ratio, 2.0)
        spread_now = self._spread(od)
        expected_cost = (spread_now / 2.0) * hedge_qty
        if expected_benefit <= expected_cost:
            return []

        # FIX 2c: Cap hedge quantity to avoid overshooting
        hedge_qty = min(hedge_qty, 25)

        pos = self._pos(state, spot_product)
        limit = self.LIMITS[spot_product]
        orders: List[Order] = []
        if total_delta > 0:
            qty = min(hedge_qty, limit + pos)
            if qty > 0:
                orders.append(Order(spot_product, bb, -qty))
        else:
            qty = min(hedge_qty, limit - pos)
            if qty > 0:
                orders.append(Order(spot_product, ba, qty))
        return orders

    # =========================
    # Entry point
    # =========================
    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:
        result: Dict[str, List[Order]] = {}
        conversions = 0
        td = self._load(state.traderData)

        self._update_cash_from_trades(td, state)

        hp_od = state.order_depths.get("HYDROGEL_PACK")
        ve_od = state.order_depths.get("VELVETFRUIT_EXTRACT")

        hp_fair, hp_mid, hp_micro, hp_wall, hp_spread, hp_imb, hp_trend, hp_conf = self._underlying_state(td, "HYDROGEL_PACK", hp_od)
        ve_fair, ve_mid, ve_micro, ve_wall, ve_spread, ve_imb, ve_trend, ve_conf = self._underlying_state(td, "VELVETFRUIT_EXTRACT", ve_od)

        hp_mid_now = self._mid(hp_od) if hp_od is not None else None
        ve_mid_now = self._mid(ve_od) if ve_od is not None else None

        if hp_mid_now is not None:
            self._hist_push(td, "mid_hist", "HYDROGEL_PACK", float(hp_mid_now), self.HISTORY_LEN)
            td["hp_ema"] = self._update_ema(td.get("hp_ema"), float(hp_mid_now), self.ALPHA_FAST)
            td["hp_anchor"] = self._update_ema(td.get("hp_anchor"), float(hp_mid_now), self.ALPHA_SLOW)

        if ve_mid_now is not None:
            self._hist_push(td, "mid_hist", "VELVETFRUIT_EXTRACT", float(ve_mid_now), self.HISTORY_LEN)
            td["ve_ema"] = self._update_ema(td.get("ve_ema"), float(ve_mid_now), self.ALPHA_FAST)
            td["ve_anchor"] = self._update_ema(td.get("ve_anchor"), float(ve_mid_now), self.ALPHA_SLOW)
            td["ve_ema_slow"] = self._update_ema(td.get("ve_ema_slow"), float(ve_mid_now), self.ALPHA_VE_SLOW)

            td["spot_hist"].append(float(ve_mid_now))
            if len(td["spot_hist"]) > self.HISTORY_LEN:
                del td["spot_hist"][:-self.HISTORY_LEN]

        # Time to expiry in days / years
        t_days = max(self.TTE_START_DAYS - state.timestamp / self.TICKS_PER_DAY, 1e-6)
        t_years = max(t_days / 365.0, 1e-8)

        # Mark-to-market equity proxy for drawdown control.
        fair_values = {
            "HYDROGEL_PACK": hp_fair,
            "VELVETFRUIT_EXTRACT": ve_fair,
        }
        equity = self._equity_proxy(td, state, fair_values)
        risk_mult = self._risk_multiplier(td, equity)

        # Underlyings: use specialized strategies
        result["HYDROGEL_PACK"] = [] if hp_od is None else self._trade_hydrogel(state, td, risk_mult)
        result["VELVETFRUIT_EXTRACT"] = [] if ve_od is None else self._trade_velvetfruit(state, td, risk_mult)

        # Options: terminal pricing from OU + Bachelier, with strike smile shaping.
        spot_for_options = ve_fair if ve_fair is not None else ve_mid
        if spot_for_options is None:
            spot_for_options = self.VE_ANCHOR_INIT

        # FIX 6: Compute total portfolio delta BEFORE trading options
        # to enforce the hard cap
        total_opt_delta = 0.0
        for p in self.OPTIONS:
            opos = self._pos(state, p)
            if opos != 0 and p not in self.SKIP_VEVS:
                if p in self.MR_VEVS:
                    od_tmp = 1.0 if spot_for_options > self.STRIKES[p] + 50 else (0.5 if spot_for_options > self.STRIKES[p] else 0.0)
                else:
                    _, od_tmp, _, _, _, _, _ = self._option_state(td, p, spot_for_options, t_days, state.order_depths.get(p))
                total_opt_delta += opos * od_tmp
        ve_pos = self._pos(state, "VELVETFRUIT_EXTRACT")
        portfolio_delta = abs(total_opt_delta + ve_pos)
        delta_room = max(0.0, self.MAX_PORTFOLIO_DELTA - portfolio_delta)
        # Scale risk_mult down if we're near delta cap
        delta_scale = self._clip(delta_room / max(self.MAX_PORTFOLIO_DELTA * 0.3, 1.0), 0.1, 1.0)
        opt_risk = risk_mult * delta_scale

        for p in self.OPTIONS:
            if p not in state.order_depths:
                result[p] = []
                continue
            if p in self.SKIP_VEVS and t_days > 0.6:
                result[p] = []
                continue
            # Route MR_VEVS to the mean-reversion option engine
            if p in self.MR_VEVS:
                result[p] = self._trade_mr_option(state, td, p, spot_for_options, opt_risk)
            else:
                result[p] = self._trade_option(state, td, p, spot_for_options, t_days, opt_risk)

        # Delta hedge with the underlying only when worth it.
        if ve_od is not None:
            hedge_orders = self._delta_hedge(state, td, "VELVETFRUIT_EXTRACT", spot_for_options, t_days, risk_mult)
            if hedge_orders:
                result.setdefault("VELVETFRUIT_EXTRACT", [])
                result["VELVETFRUIT_EXTRACT"].extend(hedge_orders)

        # Clean empty lists.
        for k, v in list(result.items()):
            if not v:
                result[k] = []

        return result, conversions, self._save(td)