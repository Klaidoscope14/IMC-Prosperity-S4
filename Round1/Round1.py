from typing import Dict, List, Tuple
import json
from collections import defaultdict
import statistics

class Order:
    def __init__(self, symbol: str, price: int, quantity: int):
        self.symbol = symbol
        self.price = price
        self.quantity = quantity

class Trader:
    POSITION_LIMITS = {
        'ASH_COATED_OSMIUM': 20,
        'INTARIAN_PEPPER_ROOT': 20,
    }

    # Minimum edge we want to capture over mid-price
    MIN_EDGE = 10
    
    def __init__(self):
        # Price history for fair value calculation
        self.price_history = defaultdict(list)
        self.max_history_length = 50
        
        # Dynamic spread parameters
        self.base_spreads = {
            'ASH_COATED_OSMIUM': 10,
            'INTARIAN_PEPPER_ROOT': 15
        } 

    def run(self, state) -> Tuple[Dict[str, List[Order]], int, str]:
        # Load saved data
        if state.traderData:
            saved_data = json.loads(state.traderData)
            self.price_history = defaultdict(list, saved_data.get('price_history', {}))
        
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
                
        # Save data for next iteration
        traderData = json.dumps({'price_history': dict(self.price_history)})
        return result, 0, traderData

    def _compute_orders(self, product: str, depth, position: int) -> List[Order]:
        orders = []
        limit = self.POSITION_LIMITS[product]

        # 1. Calculate Mid-Price (Fair Value)
        # Using the best bid/ask as a proxy for fair value
        if not depth.buy_orders or not depth.sell_orders:
            return []

        best_bid = max(depth.buy_orders.keys())
        best_ask = min(depth.sell_orders.keys())
        
        # Micro-price adjustment: Weighting mid-price by volume to anticipate movement
        bid_vol = depth.buy_orders[best_bid]
        ask_vol = abs(depth.sell_orders[best_ask])
        mid_price = (best_bid * ask_vol + best_ask * bid_vol) / (bid_vol + ask_vol)
        
        # Update price history
        self.price_history[product].append(mid_price)
        if len(self.price_history[product]) > self.max_history_length:
            self.price_history[product].pop(0)
        
        # Enhanced fair value with historical context
        if len(self.price_history[product]) > 10:
            historical_avg = statistics.mean(self.price_history[product][-10:])
            fair_value = 0.7 * mid_price + 0.3 * historical_avg
        else:
            fair_value = mid_price

        # 2. Inventory Skewing
        # If we are long (+), we lower our "personal" fair value to encourage selling.
        # If we are short (-), we raise it to encourage buying.
        inventory_ratio = position / limit
        skew = -0.5 * inventory_ratio  # More conservative skew based on Round1 analysis
        fair_value = fair_value + skew
        
        # 3. Calculate Dynamic Spread
        dynamic_spread = self._calculate_dynamic_spread(product, depth, position, limit)

        # 3. Aggressive Market Taking
        # Buy from asks that are below our calculated fair value
        for ask, vol in sorted(depth.sell_orders.items()):
            if ask <= (fair_value - dynamic_spread) and position < limit:
                buy_qty = min(abs(vol), limit - position)
                orders.append(Order(product, ask, buy_qty))
                position += buy_qty

        # Sell to bids that are above our calculated fair value
        for bid, vol in sorted(depth.buy_orders.items(), reverse=True):
            if bid >= (fair_value + dynamic_spread) and position > -limit:
                sell_qty = min(abs(vol), limit + position)
                orders.append(Order(product, bid, -sell_qty))
                position -= sell_qty

        # 4. Passive Market Making (Quoting)
        # Place a bid and an ask to capture spread if we have remaining capacity
        bid_price = int(round(fair_value - dynamic_spread))
        ask_price = int(round(fair_value + dynamic_spread))
        
        # More conservative order sizing
        max_order_size = min(5, limit // 3)
        
        if position < limit:
            buy_qty = min(max_order_size, limit - position)
            orders.append(Order(product, min(bid_price, best_bid + 1), buy_qty))
        if position > -limit:
            sell_qty = min(max_order_size, limit + position)
            orders.append(Order(product, max(ask_price, best_ask - 1), -sell_qty))

        return orders
    
    def _calculate_dynamic_spread(self, product: str, depth, position: int, limit: int) -> float:
        """Calculate dynamic spread based on market conditions"""
        base_spread = self.base_spreads[product]
        
        # 1. Market spread component
        if depth.buy_orders and depth.sell_orders:
            best_bid = max(depth.buy_orders.keys())
            best_ask = min(depth.sell_orders.keys())
            market_spread = best_ask - best_bid
        else:
            market_spread = base_spread
        
        # 2. Volatility component
        volatility_spread = self._calculate_volatility_spread(product)
        
        # 3. Inventory component (widen spread when near limits)
        inventory_ratio = abs(position) / limit
        inventory_multiplier = 1 + inventory_ratio * 0.5  # 50% wider at max position
        
        # 4. Combine components
        dynamic_spread = max(
            base_spread,
            market_spread * 0.8,  # Be slightly tighter than market
            volatility_spread
        ) * inventory_multiplier
        
        # Cap maximum spread to reasonable level
        max_spread = base_spread * 3  # Max 3x base spread
        dynamic_spread = min(dynamic_spread, max_spread)
        
        return dynamic_spread
    
    def _calculate_volatility_spread(self, product: str) -> float:
        """Calculate spread component based on price volatility"""
        history = self.price_history[product]
        
        if len(history) < 10:
            return self.base_spreads[product]
        
        # Calculate recent volatility using standard deviation of returns
        recent_prices = history[-20:]  # Last 20 price points
        
        if len(recent_prices) < 2:
            return self.base_spreads[product]
        
        # Calculate returns
        returns = []
        for i in range(1, len(recent_prices)):
            if recent_prices[i-1] > 0:
                ret = (recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1]
                returns.append(ret)
        
        if not returns:
            return self.base_spreads[product]
        
        # Calculate volatility (standard deviation of returns)
        volatility = statistics.stdev(returns) if len(returns) > 1 else 0
        
        # Convert volatility to spread component
        avg_price = statistics.mean(recent_prices)
        volatility_spread = volatility * avg_price * 0.5  # Scale factor
        
        return max(self.base_spreads[product], volatility_spread)