from typing import Dict, List, Tuple

class Order:
    def __init__(self, symbol: str, price: int, quantity: int):
        self.symbol = symbol
        self.price = price
        self.quantity = quantity

class Trader:
    POSITION_LIMITS = {
        'ASH_COATED_OSMIUM': 50,
        'INTARIAN_PEPPER_ROOT': 50,
    }

    # Minimum edge we want to capture over the mid-price
    MIN_EDGE = 2 

    def run(self, state) -> Tuple[Dict[str, List[Order]], int, str]:
        result = {}
        for product in self.POSITION_LIMITS:
            if product not in state.order_depths:
                continue
            
            orders = self._compute_orders(
                product,
                state.order_depths[product],
                state.position.get(product, 0)
            )
            if orders:
                result[product] = orders
                
        return result, 0, ""

    def _compute_orders(self, product: str, depth, position: int) -> List[Order]:
        orders = []
        limit = self.POSITION_LIMITS[product]

        # 1. Calculate Mid-Price (Fair Value)
        # Using the best bid/ask as a proxy for fair value
        if not depth.buy_orders or not depth.sell_orders:
            return []

        best_bid = max(depth.buy_orders.keys())
        best_ask = min(depth.sell_orders.keys())
        
        # Micro-price adjustment: Weighting the mid-price by volume to anticipate movement
        bid_vol = depth.buy_orders[best_bid]
        ask_vol = abs(depth.sell_orders[best_ask])
        mid_price = (best_bid * ask_vol + best_ask * bid_vol) / (bid_vol + ask_vol)

        # 2. Inventory Skewing
        # If we are long (+), we lower our "personal" fair value to encourage selling.
        # If we are short (-), we raise it to encourage buying.
        inventory_ratio = position / limit
        skew = -2.0 * inventory_ratio  # Adjust the 2.0 based on volatility
        fair_value = mid_price + skew

        # 3. Aggressive Market Taking
        # Buy from asks that are below our calculated fair value
        for ask, vol in sorted(depth.sell_orders.items()):
            if ask <= (fair_value - self.MIN_EDGE) and position < limit:
                buy_qty = min(abs(vol), limit - position)
                orders.append(Order(product, ask, buy_qty))
                position += buy_qty

        # Sell to bids that are above our calculated fair value
        for bid, vol in sorted(depth.buy_orders.items(), reverse=True):
            if bid >= (fair_value + self.MIN_EDGE) and position > -limit:
                sell_qty = min(abs(vol), limit + position)
                orders.append(Order(product, bid, -sell_qty))
                position -= sell_qty

        # 4. Passive Market Making (Quoting)
        # Place a bid and an ask to capture the spread if we have remaining capacity
        bid_price = int(round(fair_value - self.MIN_EDGE))
        ask_price = int(round(fair_value + self.MIN_EDGE))

        if position < limit:
            orders.append(Order(product, min(bid_price, best_bid + 1), limit - position))
        if position > -limit:
            orders.append(Order(product, max(ask_price, best_ask - 1), -(limit + position)))

        return orders