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
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0

class ImprovedTradingBot:
    def __init__(self):
        self.products = ['ASH_COATED_OSMIUM', 'INTARIAN_PEPPER_ROOT']
        self.positions = {product: Position(product, 0, 0.0) for product in self.products}
        self.orders = []
        self.position_limits = {'ASH_COATED_OSMIUM': 15, 'INTARIAN_PEPPER_ROOT': 15}
        self.max_order_size = 5
        self.base_spread = {'ASH_COATED_OSMIUM': 10, 'INTARIAN_PEPPER_ROOT': 15}
        self.inventory_skew_factor = 0.002
        self.stop_loss_threshold = 0.05  # 5% stop loss
        
        # Market data
        self.market_data = {}
        self.price_history = {product: [] for product in self.products}
        self.trade_history = []
        
        # Performance tracking
        self.total_trades = 0
        self.successful_trades = 0
        
    def update_market_data(self, timestamp: int, product: str, bid_price: float, 
                          ask_price: float, bid_volume: int, ask_volume: int):
        """Update market data for a product"""
        if bid_price <= 0 or ask_price <= 0:
            return
            
        mid_price = (bid_price + ask_price) / 2
        
        self.market_data[product] = {
            'timestamp': timestamp,
            'bid_price': bid_price,
            'ask_price': ask_price,
            'bid_volume': bid_volume,
            'ask_volume': ask_volume,
            'mid_price': mid_price,
            'spread': ask_price - bid_price
        }
        
        # Update price history (keep last 50 points)
        self.price_history[product].append(mid_price)
        if len(self.price_history[product]) > 50:
            self.price_history[product].pop(0)
    
    def calculate_fair_price(self, product: str) -> float:
        """Calculate fair price using recent price history and inventory management"""
        if product not in self.market_data:
            return 0.0
        
        current_mid = self.market_data[product]['mid_price']
        history = self.price_history[product]
        
        if len(history) < 5:
            return current_mid
        
        # Use simple moving average of recent prices
        fair_price = np.mean(history[-10:])  # Last 10 points
        
        # Apply inventory skew more conservatively
        position = self.positions[product]
        position_ratio = position.quantity / self.position_limits[product]
        
        # Only apply skew if position is significant (> 40% of limit)
        if abs(position_ratio) > 0.4:
            skew_adjustment = np.sign(position_ratio) * abs(position_ratio) * current_mid * self.inventory_skew_factor
            fair_price -= skew_adjustment
        
        # Ensure fair price stays within reasonable bounds
        max_deviation = current_mid * 0.01  # 1% max deviation from mid
        fair_price = np.clip(fair_price, current_mid - max_deviation, current_mid + max_deviation)
        
        return fair_price
    
    def calculate_optimal_spread(self, product: str) -> float:
        """Calculate optimal bid-ask spread with volatility adjustment"""
        if product not in self.market_data:
            return self.base_spread[product]
        
        current_spread = self.market_data[product]['spread']
        history = self.price_history[product]
        
        if len(history) < 10:
            return max(self.base_spread[product], current_spread)
        
        # Calculate volatility safely
        if len(history) > 1 and all(h > 0 for h in history):
            returns = np.diff(history) / history[:-1]
            if len(returns) > 0 and not np.isnan(returns).all():
                volatility = np.std(returns[~np.isnan(returns)]) * np.sqrt(len(history))
            else:
                volatility = 0
        else:
            volatility = 0
        
        # Base spread with volatility adjustment
        base_spread = self.base_spread[product]
        volatility_adjustment = volatility * self.market_data[product]['mid_price'] * 0.3
        
        # Inventory adjustment - widen spread when at limits
        position_ratio = abs(self.positions[product].quantity) / self.position_limits[product]
        inventory_multiplier = 1 + position_ratio * 0.3
        
        optimal_spread = max(base_spread, volatility_adjustment) * inventory_multiplier
        
        # Cap spread to reasonable maximum
        max_spread = self.market_data[product]['mid_price'] * 0.005  # 0.5% max spread
        optimal_spread = min(optimal_spread, max_spread)
        
        return optimal_spread
    
    def should_place_orders(self, product: str) -> bool:
        """Determine if we should place orders for this product"""
        position = self.positions[product]
        
        # Don't trade if at position limits
        if abs(position.quantity) >= self.position_limits[product]:
            return False
        
        # Check stop loss
        if position.quantity != 0:
            current_mid = self.market_data.get(product, {}).get('mid_price', 0)
            if current_mid > 0:
                pnl_per_unit = (current_mid - position.avg_price) * np.sign(position.quantity)
                if pnl_per_unit < -position.avg_price * self.stop_loss_threshold:
                    return False  # Stop trading if losing too much
        
        return True
    
    def generate_orders(self, timestamp: int) -> List[Order]:
        """Generate market making orders with better risk management"""
        new_orders = []
        
        for product in self.products:
            if not self.should_place_orders(product) or product not in self.market_data:
                continue
            
            fair_price = self.calculate_fair_price(product)
            optimal_spread = self.calculate_optimal_spread(product)
            
            half_spread = optimal_spread / 2
            bid_price = fair_price - half_spread
            ask_price = fair_price + half_spread
            
            # Ensure our prices are competitive
            market_data = self.market_data[product]
            bid_price = min(bid_price, market_data['bid_price'] + 1)  # Be slightly aggressive
            ask_price = max(ask_price, market_data['ask_price'] - 1)
            
            # Calculate order sizes based on position limits and risk
            position = self.positions[product]
            
            # More conservative sizing
            max_buy = min(self.max_order_size, 
                         self.position_limits[product] - position.quantity,
                         max(1, self.position_limits[product] // 3))  # Max 1/3 of limit per order
            
            max_sell = min(self.max_order_size, 
                          self.position_limits[product] + position.quantity,
                          max(1, self.position_limits[product] // 3))
            
            # Only place orders if we have room
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
        """Execute an order and update positions with better PnL tracking"""
        position = self.positions[order.product]
        
        try:
            if order.side == OrderSide.BUY:
                # Calculate new average price
                if position.quantity == 0:
                    position.avg_price = execution_price
                    position.quantity = order.quantity
                else:
                    total_cost = position.quantity * position.avg_price + order.quantity * execution_price
                    position.quantity += order.quantity
                    position.avg_price = total_cost / position.quantity
            else:  # SELL
                # Calculate realized PnL
                if position.quantity < 0:  # We're short, covering
                    realized_pnl = order.quantity * (position.avg_price - execution_price)
                else:  # We're long, selling
                    realized_pnl = order.quantity * (execution_price - position.avg_price)
                
                position.realized_pnl += realized_pnl
                position.quantity -= order.quantity
                
                # Reset avg price if position is closed
                if position.quantity == 0:
                    position.avg_price = 0
            
            # Update unrealized PnL
            if order.product in self.market_data:
                current_mid = self.market_data[order.product]['mid_price']
                if position.quantity != 0:
                    if position.quantity > 0:
                        position.unrealized_pnl = position.quantity * (current_mid - position.avg_price)
                    else:
                        position.unrealized_pnl = abs(position.quantity) * (position.avg_price - current_mid)
                else:
                    position.unrealized_pnl = 0
            
            self.total_trades += 1
            if realized_pnl if 'realized_pnl' in locals() else 0 > 0:
                self.successful_trades += 1
            
            return True
        except Exception as e:
            print(f"Error executing order: {e}")
            return False
    
    def get_portfolio_status(self) -> Dict:
        """Get current portfolio status with detailed metrics"""
        total_realized_pnl = sum(pos.realized_pnl for pos in self.positions.values())
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        total_pnl = total_realized_pnl + total_unrealized_pnl
        
        status = {
            'total_pnl': total_pnl,
            'total_realized_pnl': total_realized_pnl,
            'total_unrealized_pnl': total_unrealized_pnl,
            'total_trades': self.total_trades,
            'success_rate': self.successful_trades / max(1, self.total_trades),
            'positions': {}
        }
        
        for product, position in self.positions.items():
            status['positions'][product] = {
                'quantity': position.quantity,
                'avg_price': position.avg_price,
                'realized_pnl': position.realized_pnl,
                'unrealized_pnl': position.unrealized_pnl,
                'total_pnl': position.realized_pnl + position.unrealized_pnl,
                'position_limit': self.position_limits[product],
                'utilization': abs(position.quantity) / self.position_limits[product]
            }
        
        return status
    
    def run_simulation(self, price_data_file: str, trades_data_file: str):
        """Run simulation on historical data with better execution logic"""
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
            
            # Generate orders every 5 timestamps to reduce overtrading
            if i % 5 == 0:
                new_orders = self.generate_orders(timestamp)
                
                # Simulate order execution with more realistic logic
                for order in new_orders:
                    market_data = self.market_data.get(order.product)
                    if market_data:
                        # More realistic execution probability
                        if order.side == OrderSide.BUY:
                            if order.price >= market_data['bid_price']:
                                execution_price = max(order.price, market_data['bid_price'])
                                self.execute_order(order, execution_price)
                        else:  # SELL
                            if order.price <= market_data['ask_price']:
                                execution_price = min(order.price, market_data['ask_price'])
                                self.execute_order(order, execution_price)
        
        # Print final results
        print("\n=== Simulation Results ===")
        portfolio_status = self.get_portfolio_status()
        
        print(f"Total PnL: {portfolio_status['total_pnl']:.2f}")
        print(f"Realized PnL: {portfolio_status['total_realized_pnl']:.2f}")
        print(f"Unrealized PnL: {portfolio_status['total_unrealized_pnl']:.2f}")
        print(f"Total Trades: {portfolio_status['total_trades']}")
        print(f"Success Rate: {portfolio_status['success_rate']:.2%}")
        
        for product, status in portfolio_status['positions'].items():
            print(f"\n{product}:")
            print(f"  Position: {status['quantity']} units")
            print(f"  Average Price: {status['avg_price']:.2f}")
            print(f"  Total PnL: {status['total_pnl']:.2f}")
            print(f"  Position Utilization: {status['utilization']:.2%}")

def main():
    """Main function to run the trading bot"""
    bot = ImprovedTradingBot()
    
    # Run simulation on day -2 data
    price_file = "Round1/prices_round_1_day_-2.csv"
    trade_file = "Round1/trades_round_1_day_-2.csv"
    
    bot.run_simulation(price_file, trade_file)

if __name__ == "__main__":
    main()
