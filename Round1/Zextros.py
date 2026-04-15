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
                if executable_volume > max_executable_volume or (executable_volume == max_executable_volume and price > clearing_price):
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
        
        # Ensure fair value is always integer to avoid fractional prices
        fv = int(round(fv))

        # ---- Capacity tracking (hard limit enforcement) ------------─────────────
        buy_cap  = self.LIMIT - pos   # Max additional buy volume
        sell_cap = self.LIMIT + pos   # Max additional sell volume

        # ═══════════════════════════════════════════════════════════
        #  PURE MAKE — Earn the spread around fair value
        #
        #  Place passive limit orders only:
        #    BID = FV - offset   (buy below fair value)
        #    ASK = FV + offset   (sell above fair value)
        #
        #  NEVER TAKE liquidity - avoid crossing the spread.
        #  Earn spread when market oscillates around FV.
        #
        #  Inventory skew provides calm position adjustments.
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

        # ── AUCTION SIMULATION: Maximum Unpunished Size Algorithm ─────────────────
        #    Only run during auction periods to avoid damaging PnL during continuous trading
        is_auction_state = (len(state.own_trades.get(product, [])) == 0 and state.timestamp == 0)
        
        if is_auction_state:
            auction_orders = self.optimize_auction_order(product, od)
            orders.extend(auction_orders)

        # ── Sponge: absorb remaining capacity at wide prices ──────
        #    FV ± 8 — catches flash crashes/spikes.  Rarely fills
        #    but costs nothing to have on the book.
        if buy_cap > 0:
            orders.append(Order(product, int(bid_price - offset * 2), buy_cap))

        if sell_cap > 0:
            orders.append(Order(product, int(ask_price + offset * 2), -sell_cap))

        return orders