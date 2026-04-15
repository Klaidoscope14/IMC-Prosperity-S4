
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
       FV = 50% fast_EMA + 50% anchor.  MAKE the spread at FV ± offset.
       NEVER TAKE liquidity.  Use inventory skew for calm adjustments.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from datamodel import OrderDepth, TradingState, Order
from typing import List, Dict, Tuple, Optional
import jsonpickle

class Trader:

    # ╔════════════════════════════════════════════════════════════════╗
    # ║                     POSITION LIMIT                            ║
    # ╚════════════════════════════════════════════════════════════════╝

    LIMIT = 80  # Hard limit for both products (long or short)

    # ─────────────────────────────────────────────────────────────────
    #  ASH_COATED_OSMIUM (ACO) — Pure Market Maker
    #
    #  Mean-reverts around 10,000.  ~16 tick spread.
    #  FV = 50% fast EMA + 50% anchor.
    #  MAKE the spread at FV ± offset.  NEVER TAKE liquidity.
    # ─────────────────────────────────────────────────────────────────
    ACO_ANCHOR     = 10_000  # Structural mean-reversion center
    ACO_EMA_ALPHA  = 0.20    # Fast EMA — tracks local price quickly
    ACO_ANCHOR_WT  = 0.50    # FV = 50% EMA + 50% anchor
    ACO_TAKE_EDGE   = 3      # Minimum edge to cross and take liquidity
    ACO_EXTREME_BUY = 9992   # Data-driven lower dislocation threshold
    ACO_EXTREME_SELL = 10008 # Data-driven upper dislocation threshold
    ACO_EXTREME_SIZE = 36     # Aggressive take size in extreme dislocations
    ACO_MAKE_SIZE_1 = 14     # L1 passive quote size
    ACO_MAKE_SIZE_2 = 8      # L2 passive quote size
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
                    d.setdefault("ipr_last_mid", None)
                    d.setdefault("ipr_drift_ema", 0.0)
                    return d
            except Exception:
                pass
        # Only ACO needs state (EMA). IPR has no state — just buy.
        return {
            "aco_ema": None,
            "imbalance_history": {},
            "ipr_last_mid": None,
            "ipr_drift_ema": 0.0,
        }

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

    def calculate_clearing_price(self, buy_orders: Dict[int, int], sell_orders: Dict[int, int]) -> Tuple[Optional[int], int]:
        """
        Calculate auction clearing price from buy and sell order dictionaries.
        
        Returns the highest price where cumulative buy volume >= cumulative sell volume,
        and the total volume that can be executed at that price.
        """
        if not buy_orders or not sell_orders:
            return None, 0
        
        # Sort bids descending, asks ascending
        sorted_bids = sorted(buy_orders.items(), key=lambda x: x[0], reverse=True)
        sorted_asks = sorted(sell_orders.items(), key=lambda x: x[0])
        
        # Calculate cumulative volumes
        cumulative_buys = []
        running_buy_vol = 0
        for price, volume in sorted_bids:
            running_buy_vol += volume
            cumulative_buys.append((price, running_buy_vol))
        
        cumulative_sells = []
        running_sell_vol = 0
        for price, volume in sorted_asks:
            running_sell_vol += abs(volume)  # Convert negative to positive
            cumulative_sells.append((price, running_sell_vol))
        
        # Find clearing price
        clearing_price = None
        max_executable_volume = 0
        
        # Check each price level
        all_prices = sorted({price for price, _ in cumulative_buys} | {price for price, _ in cumulative_sells})
        
        for price in all_prices:
            # Get cumulative volumes at this price
            buy_vol_at_price = 0
            for bp, bv in cumulative_buys:
                if bp >= price:
                    buy_vol_at_price = bv
                    break
            
            sell_vol_at_price = 0  
            for ap, av in cumulative_sells:
                if ap <= price:
                    sell_vol_at_price = av
                    break
            
            # Clearing condition: buy volume >= sell volume
            if buy_vol_at_price >= sell_vol_at_price:
                executable_volume = min(buy_vol_at_price, sell_vol_at_price)
                if executable_volume > max_executable_volume or (executable_volume == max_executable_volume and (clearing_price is None or price > clearing_price)):
                    max_executable_volume = executable_volume
                    clearing_price = price
        
        return clearing_price, max_executable_volume

    def _calculate_auction_clearing_price(self, od: OrderDepth, our_orders: List[Order]) -> Optional[int]:
        """
        Simulate exchange auction to find clearing price.
        
        Returns the highest price where cumulative buy volume >= cumulative sell volume.
        This allows us to inject orders to shift the clearing price favorably.
        """
        if not od.buy_orders or not od.sell_orders:
            return None
        
        # ── Step 1: Create arrays of all bids and asks with our orders included ──
        # Start with existing market orders
        all_bids = list(od.buy_orders.items())  # [(price, volume), ...]
        all_asks = list(od.sell_orders.items())  # [(price, -volume), ...]
        
        # Add our own orders to the book simulation
        for order in our_orders:
            if order.quantity > 0:  # Our bid order
                all_bids.append((order.price, order.quantity))
            elif order.quantity < 0:  # Our ask order  
                all_asks.append((order.price, order.quantity))
        
        # ── Step 2: Sort and calculate cumulative volumes ──
        # Sort bids descending (highest first), asks ascending (lowest first)
        all_bids.sort(key=lambda x: x[0], reverse=True)
        all_asks.sort(key=lambda x: x[0])
        
        # Calculate cumulative buy volume at each price level
        cumulative_buys = []
        running_buy_vol = 0
        for price, volume in all_bids:
            running_buy_vol += volume
            cumulative_buys.append((price, running_buy_vol))
        
        # Calculate cumulative sell volume at each price level  
        cumulative_sells = []
        running_sell_vol = 0
        for price, volume in all_asks:
            running_sell_vol += abs(volume)  # Convert negative to positive
            cumulative_sells.append((price, running_sell_vol))
        
        # ── Step 3: Find intersection point (clearing price) ──
        clearing_price = None
        max_surplus = float('-inf')
        
        # Check each price level where we have both buy and sell data
        all_prices = sorted({price for price, _ in cumulative_buys} | {price for price, _ in cumulative_sells})
        
        for price in all_prices:
            # Get cumulative volumes at this price (or nearest)
            buy_vol_at_price = 0
            for bp, bv in cumulative_buys:
                if bp >= price:
                    buy_vol_at_price = bv
                    break
            
            sell_vol_at_price = 0  
            for ap, av in cumulative_sells:
                if ap <= price:
                    sell_vol_at_price = av
                    break
            
            # Find where buy volume >= sell volume
            if buy_vol_at_price >= sell_vol_at_price:
                surplus = buy_vol_at_price - sell_vol_at_price
                if surplus > max_surplus or (surplus == max_surplus and price > clearing_price):
                    max_surplus = surplus
                    clearing_price = price
        
        return clearing_price

    def _inject_auction_orders(self, od: OrderDepth, pos: int, product: str, base_orders: List[Order]) -> List[Order]:
        """
        Inject strategic orders to shift auction clearing price favorably.
        
        If we're too long: inject large ask to push clearing price down.
        If we're too short: inject large bid to push clearing price up.
        """
        injection_orders = []
        
        # Calculate current clearing price without our injection
        current_clearing = self._calculate_auction_clearing_price(od, base_orders)
        if current_clearing is None:
            return injection_orders
        
        # Determine injection direction based on inventory
        if pos > 40:  # Too long - want lower clearing price
            # Place large ask just above current clearing to push it down
            injection_price = current_clearing + 1
            injection_size = min(50, self.LIMIT + pos)  # Large but within limits
            injection_orders.append(Order(product, injection_price, -injection_size))
            
        elif pos < -40:  # Too short - want higher clearing price  
            # Place large bid just below current clearing to push it up
            injection_price = current_clearing - 1
            injection_size = min(50, self.LIMIT - pos)  # Large but within limits
            injection_orders.append(Order(product, injection_price, injection_size))
        
        return injection_orders

    def optimize_auction_order(self, product: str, od: OrderDepth) -> List[Order]:
        """
        Finds the maximum volume we can trade in the auction 
        WITHOUT moving the clearing price against us.
        
        Implements the "Maximum Unpunished Size" algorithm.
        """
        if not od.buy_orders or not od.sell_orders:
            return []
        
        # 1. Find the natural baseline
        base_price, _ = self.calculate_clearing_price(od.buy_orders, od.sell_orders)
        if base_price is None:
            return []
        
        best_buy_size = 0
        best_sell_size = 0
        
        # 2. Probe for maximum unpunished BUY size
        for test_size in range(1, 81):  # Test 1 to 80
            sim_buy = od.buy_orders.copy()
            # Place our test order at the base price to act as a sponge
            sim_buy[base_price] = sim_buy.get(base_price, 0) + test_size 
            
            new_price, _ = self.calculate_clearing_price(sim_buy, od.sell_orders)
            
            if new_price is not None and new_price <= base_price: 
                # The market didn't snap upwards! We can safely absorb this size.
                best_buy_size = test_size
            else:
                # The price moved against us. Stop here.
                break

        # 3. Probe for maximum unpunished SELL size
        for test_size in range(-1, -81, -1):  # Test -1 to -80
            sim_sell = od.sell_orders.copy()
            sim_sell[base_price] = sim_sell.get(base_price, 0) + test_size
            
            new_price, _ = self.calculate_clearing_price(od.buy_orders, sim_sell)
            
            if new_price is not None and new_price >= base_price:
                # The market didn't snap downwards!
                best_sell_size = test_size
            else:
                break
                
        # 4. Execute the optimal order
        orders = []
        # If the market gives us free size on the buy side, take it
        if best_buy_size > 0:
            orders.append(Order(product, base_price, best_buy_size))
        # If the market gives us free size on the sell side, take it
        elif best_sell_size < 0: 
            orders.append(Order(product, base_price, best_sell_size))
            
        return orders

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

        # Track short-horizon drift to choose a stronger refill bid when asks are thin.
        if od.buy_orders and od.sell_orders:
            ipr_mid = (max(od.buy_orders.keys()) + min(od.sell_orders.keys())) / 2.0
            if td["ipr_last_mid"] is not None:
                step = ipr_mid - td["ipr_last_mid"]
                td["ipr_drift_ema"] = 0.25 * step + 0.75 * td["ipr_drift_ema"]
            td["ipr_last_mid"] = ipr_mid

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
        #    place layered aggressive bids to re-fill quickly.
        if buy_cap > 0 and od.buy_orders:
            best_bid = max(od.buy_orders.keys())
            best_ask = min(od.sell_orders.keys()) if od.sell_orders else None
            drift_boost = 1 if td["ipr_drift_ema"] > 0 else 0

            # Anchor remainder to ask-side to avoid sitting too far below next fill.
            if best_ask is not None:
                refill_px_1 = best_ask if drift_boost > 0 else best_ask - 1
            else:
                refill_px_1 = best_bid + 1
            refill_sz_1 = min(buy_cap, 30)
            orders.append(Order(product, refill_px_1, refill_sz_1))
            buy_cap -= refill_sz_1

            if buy_cap > 0:
                if best_ask is not None:
                    refill_px_2 = best_ask - 1
                else:
                    refill_px_2 = best_bid
                orders.append(Order(product, refill_px_2, buy_cap))

        # ── NEVER SELL ─────────────────────────────────────────────
        #    No sell orders.  No trimming.  No scalping.
        #    Hold to 80.  Ride the trend.

        return orders

    # ╔════════════════════════════════════════════════════════════════╗
    # ║   ASH_COATED_OSMIUM — PURE MARKET MAKER                    ║
    # ╚════════════════════════════════════════════════════════════════╝
    #
    #  Mean-reverts around 10,000.  The edge is purely mathematical:
    #
    #  FV = 50% × fast_EMA + 50% × 10,000
    #
    #  PURE MAKE: Place passive limit orders only at FV ± offset.
    #             NEVER TAKE liquidity - avoid crossing the spread.
    #             Earn the spread when market oscillates around FV.
    #
    #  CALM INVENTORY ADJUSTMENT: When position > 40, shift FV down
    #                           to get filled passively on asks.
    #                           When < -40, shift FV up for passive fills.
    #                           This earns spread instead of paying it.
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

        # Guard against auction artifacts that print zero or near-zero mids.
        if mid < 1000:
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

        fv = float(raw_fv + skew)

        # ---- Imbalance calculation for better fills -----------------
        # Calculate order book imbalance: (bid_vol - ask_vol) / (bid_vol + ask_vol)
        # Positive imbalance = more bid pressure (upward pressure)
        # Negative imbalance = more ask pressure (downward pressure)
        bid_vol = sum(od.buy_orders.values()) if od.buy_orders else 0
        ask_vol = sum(abs(v) for v in od.sell_orders.values()) if od.sell_orders else 0
        
        imbalance = 0
        if bid_vol + ask_vol > 0:
            imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol)
            # ACO is mean-reverting; positive imbalance is contrarian bearish.
            fv -= imbalance * 0.8
        
        # ---- Step 1: Track imbalance history ----
        if product not in td["imbalance_history"]:
            td["imbalance_history"][product] = []
        
        td["imbalance_history"][product].append(imbalance)
        if len(td["imbalance_history"][product]) > 10:
            td["imbalance_history"][product].pop(0)
        
        avg_imbalance = sum(td["imbalance_history"][product]) / len(td["imbalance_history"][product])
        fv -= avg_imbalance * 0.5
        
        # Ensure fair value is always integer to avoid fractional prices
        fv = int(round(fv))

        # ---- Capacity tracking (hard limit enforcement) ------------─────────────
        buy_cap  = self.LIMIT - pos   # Max additional buy volume
        sell_cap = self.LIMIT + pos   # Max additional sell volume

        if od.buy_orders and od.sell_orders:
            best_bid = max(od.buy_orders.keys())
            best_ask = min(od.sell_orders.keys())
        else:
            best_bid = fv - 8
            best_ask = fv + 8

        # Dynamic extreme thresholds based on current fair value
        extreme_buy = fv - 8
        extreme_sell = fv + 8
        
        # Extreme-zone stat-arb take layer for strong mean-reversion dislocations.
        # This is complementary to normal edge-taking and maker quoting.
        if mid <= extreme_buy and buy_cap > 0 and od.sell_orders:
            remaining = min(buy_cap, self.ACO_EXTREME_SIZE)
            for ask_px in sorted(od.sell_orders.keys()):
                if remaining <= 0:
                    break
                if ask_px > extreme_buy + 3:
                    break
                qty = min(remaining, abs(od.sell_orders[ask_px]))
                if qty > 0:
                    orders.append(Order(product, ask_px, qty))
                    remaining -= qty
            buy_cap -= min(buy_cap, self.ACO_EXTREME_SIZE) - remaining

        if mid >= extreme_sell and sell_cap > 0 and od.buy_orders:
            remaining = min(sell_cap, self.ACO_EXTREME_SIZE)
            for bid_px in sorted(od.buy_orders.keys(), reverse=True):
                if remaining <= 0:
                    break
                if bid_px < extreme_sell - 3:
                    break
                qty = min(remaining, od.buy_orders[bid_px])
                if qty > 0:
                    orders.append(Order(product, bid_px, -qty))
                    remaining -= qty
            sell_cap -= min(sell_cap, self.ACO_EXTREME_SIZE) - remaining

        # ── Phase 1: Selective taking when clear edge exists ─────
        # We only cross when the edge is meaningfully larger than fees/noise.
        take_edge = self.ACO_TAKE_EDGE
        if best_ask <= fv - take_edge and buy_cap > 0:
            if abs(best_ask - fv) > 5:
                take_qty = min(buy_cap, abs(od.sell_orders[best_ask]), 40)
            else:
                take_qty = min(buy_cap, abs(od.sell_orders[best_ask]), 24)
            if take_qty > 0:
                orders.append(Order(product, best_ask, take_qty))
                buy_cap -= take_qty

        if best_bid >= fv + take_edge and sell_cap > 0:
            if abs(best_bid - fv) > 5:
                take_qty = min(sell_cap, od.buy_orders[best_bid], 40)
            else:
                take_qty = min(sell_cap, od.buy_orders[best_bid], 24)
            if take_qty > 0:
                orders.append(Order(product, best_bid, -take_qty))
                sell_cap -= take_qty

        # ── Phase 2: Inventory-aware passive market making ───────
        if pos > 60:
            inv_shift = -3
        elif pos > 30:
            inv_shift = -2
        elif pos < -60:
            inv_shift = 3
        elif pos < -30:
            inv_shift = 2
        else:
            inv_shift = 0

        # Spread adapts to current top-of-book width.
        spread = max(1, best_ask - best_bid)
        base_offset = 1 if spread <= 3 else 2

        make_fv = fv + inv_shift
        bid_l1 = best_bid + 1 if best_bid + 1 < make_fv else make_fv - base_offset
        ask_l1 = best_ask - 1 if best_ask - 1 > make_fv else make_fv + base_offset

        # Micro aggression in tight markets
        if spread <= 3:
            bid_l1 += 1
            ask_l1 -= 1

        # Guarantee non-crossing passive quotes.
        if bid_l1 >= ask_l1:
            bid_l1 = make_fv - 1
            ask_l1 = make_fv + 1

        # Lean size toward flattening inventory.
        size_buy = self.ACO_MAKE_SIZE_1
        size_sell = self.ACO_MAKE_SIZE_1
        if pos > 30:
            size_buy = self.ACO_MAKE_SIZE_2
            size_sell = self.ACO_MAKE_SIZE_1 + 4
        elif pos < -30:
            size_buy = self.ACO_MAKE_SIZE_1 + 4
            size_sell = self.ACO_MAKE_SIZE_2

        if buy_cap > 0:
            q = min(buy_cap, size_buy)
            orders.append(Order(product, int(bid_l1), q))
            buy_cap -= q

        if sell_cap > 0:
            q = min(sell_cap, size_sell)
            orders.append(Order(product, int(ask_l1), -q))
            sell_cap -= q

        # L2 quotes improve fill rate without overexposing size.
        if buy_cap > 0:
            q = min(buy_cap, self.ACO_MAKE_SIZE_2)
            orders.append(Order(product, int(bid_l1 - 2), q))

        if sell_cap > 0:
            q = min(sell_cap, self.ACO_MAKE_SIZE_2)
            orders.append(Order(product, int(ask_l1 + 2), -q))

        # ── AUCTION SIMULATION: Maximum Unpunished Size Algorithm ─────────────────
        auction_orders = self.optimize_auction_order(product, od)
        orders.extend(auction_orders)

        return orders