import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import time
from dataclasses import dataclass
from enum import Enum

class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"

@dataclass
class Order:
    product: str
    side: OrderSide
    price: float
    quantity: int
    timestamp: int
    order_id: str = None

@dataclass
class Position:
    product: str
    quantity: int
    avg_price: float
    unrealized_pnl: float = 0.0

class SimpleTradingBot:
    def __init__(self):
        self.products = ['ASH_COATED_OSMIUM', 'INTARIAN_PEPPER_ROOT']
        self.positions = {product: Position(product, 0, 0.0) for product in self.products}
        self.orders = []
        self.position_limits = {'ASH_COATED_OSMIUM': 20, 'INTARIAN_PEPPER_ROOT': 20}
        self.max_order_size = 10
        self.spread_target = {'ASH_COATED_OSMIUM': 15, 'INTARIAN_PEPPER_ROOT': 20}
        self.inventory_skew_factor = 0.001
        
        # Market data
        self.market_data = {}
        self.price_history = {product: [] for product in self.products}
        
    def update_market_data(self, timestamp: int, product: str, bid_price: float, 
                          ask_price: float, bid_volume: int, ask_volume: int):
        """Update market data for a product"""
        mid_price = (bid_price + ask_price) / 2 if bid_price > 0 and ask_price > 0 else 0
        
        self.market_data[product] = {
            'timestamp': timestamp,
            'bid_price': bid_price,
            'ask_price': ask_price,
            'bid_volume': bid_volume,
            'ask_volume': ask_volume,
            'mid_price': mid_price,
            'spread': ask_price - bid_price if bid_price > 0 and ask_price > 0 else 0
        }
        
        # Update price history (keep last 100 points)
        self.price_history[product].append(mid_price)
        if len(self.price_history[product]) > 100:
            self.price_history[product].pop(0)
    
    def calculate_fair_price(self, product: str) -> float:
        """Calculate fair price using recent price history"""
        if product not in self.market_data:
            return 0.0
        
        current_mid = self.market_data[product]['mid_price']
        history = self.price_history[product]
        
        if len(history) < 2:
            return current_mid
        
        # Use exponential weighted moving average
        weights = np.exp(-np.arange(len(history)) * 0.1)
        weights = weights / weights.sum()
        fair_price = np.average(history, weights=weights)
        
        # Apply inventory skew
        position = self.positions[product]
        position_ratio = position.quantity / self.position_limits[product]
        skew_adjustment = position_ratio * current_mid * self.inventory_skew_factor
        fair_price -= skew_adjustment
        
        return fair_price
    
    def calculate_optimal_spread(self, product: str) -> float:
        """Calculate optimal bid-ask spread"""
        if product not in self.market_data:
            return self.spread_target[product]
        
        current_spread = self.market_data[product]['spread']
        history = self.price_history[product]
        
        if len(history) < 10:
            return max(self.spread_target[product], current_spread)
        
        # Calculate volatility
        returns = np.diff(history) / history[:-1]
        volatility = np.std(returns) * np.sqrt(len(history))
        
        # Base spread on volatility
        base_spread = self.spread_target[product]
        volatility_adjustment = volatility * self.market_data[product]['mid_price'] * 0.5
        
        # Inventory adjustment
        position_ratio = abs(self.positions[product].quantity) / self.position_limits[product]
        inventory_multiplier = 1 + position_ratio * 0.5
        
        optimal_spread = max(base_spread, volatility_adjustment) * inventory_multiplier
        
        return optimal_spread
    
    def generate_orders(self, timestamp: int) -> List[Order]:
        """Generate market making orders"""
        new_orders = []
        
        for product in self.products:
            if product not in self.market_data:
                continue
            
            fair_price = self.calculate_fair_price(product)
            optimal_spread = self.calculate_optimal_spread(product)
            
            half_spread = optimal_spread / 2
            bid_price = fair_price - half_spread
            ask_price = fair_price + half_spread
            
            # Calculate order sizes based on position limits
            position = self.positions[product]
            max_buy = min(self.max_order_size, self.position_limits[product] - position.quantity)
            max_sell = min(self.max_order_size, self.position_limits[product] + position.quantity)
            
            # Generate buy order
            if max_buy > 0 and bid_price > 0:
                buy_order = Order(
                    product=product,
                    side=OrderSide.BUY,
                    price=bid_price,
                    quantity=max_buy,
                    timestamp=timestamp,
                    order_id=f"BUY_{product}_{timestamp}"
                )
                new_orders.append(buy_order)
            
            # Generate sell order
            if max_sell > 0 and ask_price > 0:
                sell_order = Order(
                    product=product,
                    side=OrderSide.SELL,
                    price=ask_price,
                    quantity=max_sell,
                    timestamp=timestamp,
                    order_id=f"SELL_{product}_{timestamp}"
                )
                new_orders.append(sell_order)
        
        return new_orders
    
    def execute_order(self, order: Order, execution_price: float) -> bool:
        """Execute an order and update positions"""
        position = self.positions[order.product]
        
        try:
            if order.side == OrderSide.BUY:
                # Calculate new average price
                total_cost = position.quantity * position.avg_price + order.quantity * execution_price
                position.quantity += order.quantity
                position.avg_price = total_cost / position.quantity if position.quantity != 0 else 0
            else:  # SELL
                position.quantity -= order.quantity
                # Realized PnL calculation would go here
            
            # Update unrealized PnL
            if order.product in self.market_data:
                current_mid = self.market_data[order.product]['mid_price']
                position.unrealized_pnl = position.quantity * (current_mid - position.avg_price)
            
            return True
        except Exception as e:
            print(f"Error executing order: {e}")
            return False
    
    def get_portfolio_status(self) -> Dict:
        """Get current portfolio status"""
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        
        status = {
            'total_unrealized_pnl': total_unrealized_pnl,
            'positions': {}
        }
        
        for product, position in self.positions.items():
            status['positions'][product] = {
                'quantity': position.quantity,
                'avg_price': position.avg_price,
                'unrealized_pnl': position.unrealized_pnl,
                'position_limit': self.position_limits[product],
                'utilization': abs(position.quantity) / self.position_limits[product]
            }
        
        return status
    
    def run_simulation(self, price_data_file: str, trades_data_file: str):
        """Run simulation on historical data"""
        print(f"Loading data from {price_data_file}...")
        
        # Load price data
        df_prices = pd.read_csv(price_data_file, sep=';')
        df_trades = pd.read_csv(trades_data_file, sep=';')
        
        print(f"Loaded {len(df_prices)} price rows and {len(df_trades)} trade rows")
        
        # Process each timestamp
        timestamps = sorted(df_prices['timestamp'].unique())
        
        for i, timestamp in enumerate(timestamps):
            if i % 1000 == 0:
                print(f"Processing timestamp {timestamp} ({i}/{len(timestamps)})")
            
            # Update market data for all products
            timestamp_data = df_prices[df_prices['timestamp'] == timestamp]
            
            for _, row in timestamp_data.iterrows():
                product = row['product']
                if product in self.products:
                    bid_price = row.get('bid_price_1', 0)
                    ask_price = row.get('ask_price_1', 0)
                    bid_volume = row.get('bid_volume_1', 0)
                    ask_volume = row.get('ask_volume_1', 0)
                    
                    self.update_market_data(timestamp, product, bid_price, ask_price, 
                                          bid_volume, ask_volume)
            
            # Generate orders
            new_orders = self.generate_orders(timestamp)
            
            # Simulate order execution (simplified)
            for order in new_orders:
                # Simple execution logic: execute if price is favorable
                market_data = self.market_data.get(order.product)
                if market_data:
                    if order.side == OrderSide.BUY and order.price >= market_data['bid_price']:
                        self.execute_order(order, market_data['bid_price'])
                    elif order.side == OrderSide.SELL and order.price <= market_data['ask_price']:
                        self.execute_order(order, market_data['ask_price'])
        
        # Print final results
        print("\n=== Simulation Results ===")
        portfolio_status = self.get_portfolio_status()
        
        print(f"Total Unrealized PnL: {portfolio_status['total_unrealized_pnl']:.2f}")
        
        for product, status in portfolio_status['positions'].items():
            print(f"\n{product}:")
            print(f"  Position: {status['quantity']} units")
            print(f"  Average Price: {status['avg_price']:.2f}")
            print(f"  Unrealized PnL: {status['unrealized_pnl']:.2f}")
            print(f"  Position Utilization: {status['utilization']:.2%}")

def main():
    """Main function to run the trading bot"""
    bot = SimpleTradingBot()
    
    # Run simulation on day -2 data
    price_file = "Round1/prices_round_1_day_-2.csv"
    trade_file = "Round1/trades_round_1_day_-2.csv"
    
    bot.run_simulation(price_file, trade_file)

if __name__ == "__main__":
    main()
