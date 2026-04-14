from typing import Dict, List
import json
from collections import defaultdict
import statistics

# Order and TradingState classes as per competition requirements
class Order:
    def __init__(self, symbol: str, price: int, quantity: int):
        self.symbol = symbol
        self.price = price
        self.quantity = quantity

class OrderDepth:
    def __init__(self):
        self.buy_orders = {}
        self.sell_orders = {}

class TradingState:
    def __init__(self):
        self.order_depths = {}
        self.own_trades = {}
        self.market_trades = {}
        self.position = {}
        self.observations = None
        self.traderData = ""

class Trader:
    def __init__(self):
        # Position limits for each product
        self.position_limits = {
            'ASH_COATED_OSMIUM': 20,
            'INTARIAN_PEPPER_ROOT': 20
        }
        
        # Strategy parameters
        self.base_spreads = {
            'ASH_COATED_OSMIUM': 10,
            'INTARIAN_PEPPER_ROOT': 15
        }
        
        self.max_order_size = 5
        self.inventory_skew_factor = 0.002
        
        # Price history for fair price calculation
        self.price_history = defaultdict(list)
        self.max_history_length = 50
        
    def run(self, state: TradingState) -> tuple:
        """
        Main trading logic called every iteration
        Returns: (result, conversions, traderData)
        """
        # Load saved data
        if state.traderData != "":
            saved_data = json.loads(state.traderData)
            self.price_history = defaultdict(list, saved_data.get('price_history', {}))
        
        # Initialize result dictionary
        result = {}
        
        # Process each product
        for product in state.order_depths:
            if product in self.position_limits:
                orders = self.process_product(product, state)
                if orders:
                    result[product] = orders
        
        # Save data for next iteration
        traderData = json.dumps({
            'price_history': dict(self.price_history)
        })
        
        # Return format: (orders_dict, conversions, trader_data)
        return result, 0, traderData
    
    def process_product(self, product: str, state: TradingState) -> List[Order]:
        """Process trading logic for a single product"""
        order_depth = state.order_depths[product]
        current_position = state.position.get(product, 0)
        
        # Get best bid and ask prices
        best_bid = max(order_depth.buy_orders.keys()) if order_depth.buy_orders else None
        best_ask = min(order_depth.sell_orders.keys()) if order_depth.sell_orders else None
        
        if best_bid is None or best_ask is None:
            return []
        
        # Calculate mid price
        mid_price = (best_bid + best_ask) / 2
        
        # Update price history
        self.price_history[product].append(mid_price)
        if len(self.price_history[product]) > self.max_history_length:
            self.price_history[product].pop(0)
        
        # Calculate fair price
        fair_price = self.calculate_fair_price(product, mid_price, current_position)
        
        # Calculate optimal spread
        optimal_spread = self.calculate_optimal_spread(product, order_depth)
        
        # Generate orders
        orders = self.generate_orders(product, fair_price, optimal_spread, 
                                     current_position, best_bid, best_ask)
        
        return orders
    
    def calculate_fair_price(self, product: str, current_mid: float, 
                           current_position: int) -> float:
        """Calculate fair price using historical data and inventory management"""
        history = self.price_history[product]
        
        if len(history) < 5:
            return current_mid
        
        # Use simple moving average of recent prices
        fair_price = statistics.mean(history[-10:])
        
        # Apply inventory skew
        position_limit = self.position_limits[product]
        position_ratio = current_position / position_limit
        
        # Only apply skew if position is significant (> 40% of limit)
        if abs(position_ratio) > 0.4:
            skew_adjustment = (1 if position_ratio > 0 else -1) * abs(position_ratio) * current_mid * self.inventory_skew_factor
            fair_price -= skew_adjustment
        
        # Ensure fair price stays within reasonable bounds
        max_deviation = current_mid * 0.01  # 1% max deviation from mid
        fair_price = max(current_mid - max_deviation, 
                        min(fair_price, current_mid + max_deviation))
        
        return fair_price
    
    def calculate_optimal_spread(self, product: str, order_depth: OrderDepth) -> float:
        """Calculate optimal bid-ask spread"""
        base_spread = self.base_spreads[product]
        
        # Get current market spread
        if order_depth.buy_orders and order_depth.sell_orders:
            best_bid = max(order_depth.buy_orders.keys())
            best_ask = min(order_depth.sell_orders.keys())
            market_spread = best_ask - best_bid
        else:
            market_spread = base_spread
        
        # Use the larger of base spread or market spread
        optimal_spread = max(base_spread, market_spread)
        
        # Cap spread to reasonable maximum (0.5% of price)
        if order_depth.buy_orders and order_depth.sell_orders:
            avg_price = (max(order_depth.buy_orders.keys()) + min(order_depth.sell_orders.keys())) / 2
            max_spread = avg_price * 0.005
            optimal_spread = min(optimal_spread, max_spread)
        
        return optimal_spread
    
    def generate_orders(self, product: str, fair_price: float, optimal_spread: float,
                       current_position: int, best_bid: float, best_ask: float) -> List[Order]:
        """Generate buy and sell orders"""
        orders = []
        position_limit = self.position_limits[product]
        
        # Calculate bid and ask prices
        half_spread = optimal_spread / 2
        bid_price = fair_price - half_spread
        ask_price = fair_price + half_spread
        
        # Ensure our prices are competitive
        bid_price = min(bid_price, best_bid + 1)  # Be slightly aggressive on bid
        ask_price = max(ask_price, best_ask - 1)  # Be slightly aggressive on ask
        
        # Calculate order sizes
        max_buy = min(self.max_order_size, 
                     position_limit - current_position,
                     max(1, position_limit // 3))
        
        max_sell = min(self.max_order_size, 
                      position_limit + current_position,
                      max(1, position_limit // 3))
        
        # Generate buy order
        if max_buy > 0 and bid_price > 0:
            buy_order = Order(product, bid_price, max_buy)
            orders.append(buy_order)
        
        # Generate sell order
        if max_sell > 0 and ask_price > 0:
            sell_order = Order(product, ask_price, -max_sell)
            orders.append(sell_order)
        
        return orders
