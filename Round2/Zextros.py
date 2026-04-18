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

  ACO: Mean-reverts around 10,001.  The edge is in the math:
       FV = 50% fast_EMA + 50% slow_anchor.  MAKE the spread at FV ± offset.
       NEVER TAKE liquidity.  Use inventory skew for calm adjustments.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from datamodel import OrderDepth, TradingState, Order
from typing import List, Dict, Tuple, Optional
import json
import math

class Trader:

    # ╔════════════════════════════════════════════════════════════════╗
    # ║                     POSITION LIMIT                             ║
    # ╚════════════════════════════════════════════════════════════════╝

    LIMIT = 80  # Hard limit for both products (long or short)
    MAX_LOT = 12  # Max lots per individual order

    # ── ACO: Book-Relative Market Making ────────────────────────────
    ACO_ANCHOR = 10001
    ACO_SKEW_TICKS = 3
    ACO_TAKER_QTY = 15
    ACO_BUY_ZONE = 9995
    ACO_SELL_ZONE = 10005
    ACO_OBI_GATE = 0.3
    ACO_L1_OFF = 1
    ACO_L2_OFF = 2
    ACO_L3_OFF = 5
    ACO_L4_OFF = 9
    ACO_L1_SZ = 20
    ACO_L2_SZ = 20
    ACO_L3_SZ = 20

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
        return 10001

    # ╔════════════════════════════════════════════════════════════════╗
    # ║                    STATE MANAGEMENT                           ║
    # ╚════════════════════════════════════════════════════════════════╝

    def _defaults(self):
        return {
            "aco_ema": None,
            "aco_anchor": None,
            "ipr_last_mid": None,
            "ipr_drift_ema": 0.0,
            "ipr_batch_idx": 0,
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

    def _mid(self, od: OrderDepth, product: str, td: dict) -> Optional[float]:
        """Calculates mid-price, gracefully handling one-sided/empty books."""
        raw_mid = None
        if od.buy_orders and od.sell_orders:
            raw_mid = (max(od.buy_orders.keys()) + min(od.sell_orders.keys())) / 2.0
            
        key_last = f"{product}_last_valid_mid"
        key_stale = f"{product}_mid_stale"
        
        if raw_mid is not None:
            td[key_last] = raw_mid
            td[key_stale] = 0
            return raw_mid
            
        # Carry forward the last valid mid for a short window
        td[key_stale] = td.get(key_stale, 0) + 1
        stale = td[key_stale]
        last_mid = td.get(key_last)
        
        if last_mid is not None and stale < 15:
            # Constrain by visible book sides to keep stability without inventing signal
            adj_mid = last_mid
            if od.buy_orders:
                adj_mid = max(adj_mid, max(od.buy_orders.keys()) + 0.5)
            if od.sell_orders:
                adj_mid = min(adj_mid, min(od.sell_orders.keys()) - 0.5)
            return adj_mid
            
        return None

    @staticmethod
    def _obi(od: OrderDepth) -> float:
        """Order book imbalance in [-1, +1]."""
        bv = sum(od.buy_orders.values()) if od.buy_orders else 0
        av = sum(abs(v) for v in od.sell_orders.values()) if od.sell_orders else 0
        return (bv - av) / (bv + av) if (bv + av) > 0 else 0.0

    def _lot(self, want: int, cap: int) -> int:
        """Clamp order size to MAX_LOT and remaining capacity."""
        return max(0, min(abs(want), self.MAX_LOT, cap))

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
                if executable_volume > max_executable_volume:
                    max_executable_volume = executable_volume
                    clearing_price = price
                elif (
                    executable_volume == max_executable_volume
                    and clearing_price is not None
                    and price > clearing_price
                ):
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
                if (
                    surplus > max_surplus
                    or (surplus == max_surplus and clearing_price is not None and price > clearing_price)
                ):
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

        # ── AUCTION SIMULATION: Maximum Unpunished Size Algorithm ──
        is_auction_state = (len(state.own_trades.get(product, [])) == 0 and state.timestamp == 0)
        if is_auction_state:
            auction_orders = self.optimize_auction_order(product, od)
            if auction_orders:
                orders.extend(auction_orders)
                for o in auction_orders:
                    pos += o.quantity

        # Track short-horizon drift to choose a stronger refill bid when asks are thin.
        ipr_mid = self._mid(od, product, td)
        if ipr_mid is not None:
            if td["ipr_last_mid"] is not None and td.get(f"{product}_mid_stale", 0) == 0:
                step = ipr_mid - td["ipr_last_mid"]
                # Only update drift on entirely fresh data
                td["ipr_drift_ema"] = 0.25 * step + 0.75 * td["ipr_drift_ema"]
            td["ipr_last_mid"] = ipr_mid

        # How much more can we buy? (Hard limit enforcement)
        # Increase avg batch from 8.0 → 11.5 to match mean L1 ask volume (11.5 lots).
        # Every tick at pos < 80 costs ~8 XIRECs in missed drift. Fill faster.
        batch_sequence = [11, 12, 11, 12]
        idx = td.get("ipr_batch_idx", 0)
        batch_size = batch_sequence[idx % len(batch_sequence)]
        
        total_missing = self.LIMIT - pos
        buy_cap = min(total_missing, batch_size)
        
        if total_missing > 0:
            td["ipr_batch_idx"] = idx + 1

        # Nothing to do if already max long
        if total_missing <= 0:
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

            # When drift is positive (almost always for IPR), don't wait for ask-1.
            # The 1-tick saving costs more in missed fill probability vs a +0.1/tick trend.
            if best_ask is not None:
                refill_px_1 = best_ask   # was: best_ask if drift_boost > 0 else best_ask - 1
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
    #  Mean-reverts around 10,001.  The edge is purely mathematical:
    #
    #  FV = 50% × fast_EMA + 50% × slow_anchor
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
        orders: List[Order] = []
        product = "ASH_COATED_OSMIUM"

        if product not in state.order_depths:
            return orders

        od = state.order_depths[product]
        pos = state.position.get(product, 0)
        buy_cap = self.LIMIT - pos
        sell_cap = self.LIMIT + pos

        # Slow anchor EMA — only updates 10% of the EMA per ~500 ticks
        ANCHOR_BASE = 10001
        ANCHOR_ALPHA = 0.001   # very slow, avoids chasing noise
        
        # Update EMA and anchor
        mid = self._mid(od, product, td)
        
        # decay confidence slowly (if staleness > 0, EMA alpha drops)
        stale = td.get(f"{product}_mid_stale", 0)
        alpha = 0.20 if stale == 0 else max(0.01, 0.20 * (0.8 ** stale))
        a_alpha = ANCHOR_ALPHA if stale == 0 else max(0.0001, ANCHOR_ALPHA * (0.8 ** stale))

        if td.get("aco_ema") is None:
            td["aco_ema"] = mid if mid is not None else ANCHOR_BASE
        elif mid is not None:
            td["aco_ema"] = alpha * mid + (1 - alpha) * td["aco_ema"]
            
        if td.get("aco_anchor") is None:
            td["aco_anchor"] = ANCHOR_BASE
        elif mid is not None:
            td["aco_anchor"] = a_alpha * mid + (1 - a_alpha) * td["aco_anchor"]

        anchor = td["aco_anchor"]
        FV = round(0.50 * td["aco_ema"] + 0.50 * anchor)

        # Phase 1: take mispriced liquidity.
        # Addition: when inventory is extended, also accept break-even
        # or slightly negative-edge trades to free capacity faster.
        buy_up_to = FV
        sell_down_to = FV

        if pos > 40:  sell_down_to = FV - 1    # also sell bids >= 10000 (if FV=10001)
        if pos > 70:  sell_down_to = FV - 2    # also sell bids >= 9999
        if pos < -40: buy_up_to = FV + 1       # also buy asks <= 10002
        if pos < -70: buy_up_to = FV + 2       # also buy asks <= 10003

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

        # Phase 2: book-relative maker quotes capped at fair value edges.
        # PROVEN LOGIC — unchanged. All capacity at single best level.
        best_bid = max(od.buy_orders.keys()) if od.buy_orders else FV - 100
        best_ask = min(od.sell_orders.keys()) if od.sell_orders else FV + 100

        our_bid = min(best_bid + 1, FV - 1)
        our_ask = max(best_ask - 1, FV + 1)

        if buy_cap > 0:
            orders.append(Order(product, our_bid, buy_cap))
            buy_cap = 0

        if sell_cap > 0:
            orders.append(Order(product, our_ask, -sell_cap))
            sell_cap = 0

        return orders