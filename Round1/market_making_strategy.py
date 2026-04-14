import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt

class MarketMakingStrategy:
    def __init__(self):
        self.products = ['ASH_COATED_OSMIUM', 'INTARIAN_PEPPER_ROOT']
        self.price_data = {}
        self.trade_data = {}
        self.position_limits = {'ASH_COATED_OSMIUM': 20, 'INTARIAN_PEPPER_ROOT': 20}
        self.current_positions = {'ASH_COATED_OSMIUM': 0, 'INTARIAN_PEPPER_ROOT': 0}
        self.spread_target = 0.002  # 0.2% spread target
        self.inventory_skew_threshold = 0.5  # Position limit threshold for skew
        
    def load_data(self, days: List[int] = [-2, -1, 0]):
        """Load price and trade data for specified days"""
        for day in days:
            # Load price data
            price_file = f'Round1/prices_round_1_day_{day}.csv'
            try:
                df_prices = pd.read_csv(price_file, sep=';')
                self.price_data[day] = df_prices
                print(f"Loaded price data for day {day}: {len(df_prices)} rows")
            except FileNotFoundError:
                print(f"Price data file not found for day {day}")
            
            # Load trade data
            trade_file = f'Round1/trades_round_1_day_{day}.csv'
            try:
                df_trades = pd.read_csv(trade_file, sep=';')
                self.trade_data[day] = df_trades
                print(f"Loaded trade data for day {day}: {len(df_trades)} rows")
            except FileNotFoundError:
                print(f"Trade data file not found for day {day}")
    
    def analyze_market_data(self):
        """Analyze market characteristics for both products"""
        analysis = {}
        
        for product in self.products:
            product_analysis = {
                'avg_mid_price': [],
                'price_volatility': [],
                'avg_spread': [],
                'volume_profile': []
            }
            
            for day, df in self.price_data.items():
                product_df = df[df['product'] == product].copy()
                
                if len(product_df) > 0:
                    # Calculate mid price statistics
                    mid_prices = product_df['mid_price'].dropna()
                    product_analysis['avg_mid_price'].append(mid_prices.mean())
                    product_analysis['price_volatility'].append(mid_prices.std())
                    
                    # Calculate bid-ask spread
                    if 'bid_price_1' in product_df.columns and 'ask_price_1' in product_df:
                        spreads = (product_df['ask_price_1'] - product_df['bid_price_1']).dropna()
                        if len(spreads) > 0:
                            product_analysis['avg_spread'].append(spreads.mean())
                    
                    # Volume analysis
                    bid_volumes = product_df['bid_volume_1'].fillna(0)
                    ask_volumes = product_df['ask_volume_1'].fillna(0)
                    total_volume = (bid_volumes + ask_volumes).sum()
                    product_analysis['volume_profile'].append(total_volume)
            
            # Aggregate statistics across days
            analysis[product] = {
                'avg_mid_price': np.mean(product_analysis['avg_mid_price']),
                'avg_volatility': np.mean(product_analysis['price_volatility']),
                'avg_spread': np.mean(product_analysis['avg_spread']) if product_analysis['avg_spread'] else 0,
                'avg_daily_volume': np.mean(product_analysis['volume_profile'])
            }
        
        return analysis
    
    def calculate_optimal_spread(self, product: str, volatility: float, avg_spread: float) -> float:
        """Calculate optimal bid-ask spread based on volatility and market conditions"""
        # Base spread as percentage of price
        base_spread = max(avg_spread, volatility * 2)
        
        # Adjust for inventory skew
        position_ratio = abs(self.current_positions[product]) / self.position_limits[product]
        if position_ratio > self.inventory_skew_threshold:
            # Widen spread when carrying large inventory
            base_spread *= (1 + position_ratio)
        
        return base_spread
    
    def calculate_reference_price(self, product: str, current_mid: float, recent_prices: List[float]) -> float:
        """Calculate reference price for placing orders"""
        if len(recent_prices) < 2:
            return current_mid
        
        # Use weighted average of recent mid prices
        weights = np.exp(-np.arange(len(recent_prices)) * 0.1)  # Exponential decay
        weighted_avg = np.average(recent_prices, weights=weights)
        
        # Blend with current mid price
        reference_price = 0.7 * current_mid + 0.3 * weighted_avg
        
        # Apply inventory skew
        position_ratio = self.current_positions[product] / self.position_limits[product]
        skew_adjustment = position_ratio * current_mid * 0.001  # 0.1% skew per position unit
        reference_price -= skew_adjustment  # Lower price when long, higher when short
        
        return reference_price
    
    def generate_orders(self, product: str, current_data: Dict, analysis: Dict) -> List[Dict]:
        """Generate market making orders for a product"""
        orders = []
        
        current_mid = current_data['mid_price']
        volatility = analysis[product]['avg_volatility']
        avg_spread = analysis[product]['avg_spread']
        
        # Calculate optimal spread
        optimal_spread = self.calculate_optimal_spread(product, volatility, avg_spread)
        
        # Calculate reference price
        recent_mids = current_data.get('recent_mids', [current_mid])
        # Extract just the mid prices from the list of dictionaries
        recent_prices = [item['mid_price'] if isinstance(item, dict) else item for item in recent_mids]
        reference_price = self.calculate_reference_price(product, current_mid, recent_prices)
        
        # Generate bid and ask orders
        half_spread = optimal_spread / 2
        bid_price = reference_price - half_spread
        ask_price = reference_price + half_spread
        
        # Order sizing based on position limits and market conditions
        max_position = self.position_limits[product]
        current_position = self.current_positions[product]
        
        # Bid order size (buy more when short, less when long)
        if current_position < max_position:
            bid_size = min(10, max_position - current_position)
            orders.append({
                'product': product,
                'side': 'BUY',
                'price': bid_price,
                'quantity': bid_size,
                'timestamp': current_data['timestamp']
            })
        
        # Ask order size (sell more when long, less when short)
        if current_position > -max_position:
            ask_size = min(10, max_position + current_position)
            orders.append({
                'product': product,
                'side': 'SELL',
                'price': ask_price,
                'quantity': ask_size,
                'timestamp': current_data['timestamp']
            })
        
        return orders
    
    def backtest_strategy(self, day: int = -2) -> Dict:
        """Backtest the market making strategy on historical data"""
        if day not in self.price_data:
            return {}
        
        df = self.price_data[day].copy()
        results = {'ASH_COATED_OSMIUM': [], 'INTARIAN_PEPPER_ROOT': []}
        
        # Get market analysis
        analysis = self.analyze_market_data()
        
        # Process each timestamp
        for timestamp in sorted(df['timestamp'].unique()):
            timestamp_data = df[df['timestamp'] == timestamp]
            
            for product in self.products:
                product_data = timestamp_data[timestamp_data['product'] == product]
                if len(product_data) == 0:
                    continue
                
                current_row = product_data.iloc[0]
                current_data = {
                    'mid_price': current_row['mid_price'],
                    'timestamp': timestamp,
                    'recent_mids': results[product][-5:] if results[product] else [current_row['mid_price']]
                }
                
                # Generate orders
                orders = self.generate_orders(product, current_data, analysis)
                
                # Simulate order execution (simplified)
                for order in orders:
                    # Check if order would execute (simplified execution logic)
                    if order['side'] == 'BUY' and order['price'] >= current_row.get('bid_price_1', 0):
                        self.current_positions[product] += order['quantity']
                    elif order['side'] == 'SELL' and order['price'] <= current_row.get('ask_price_1', float('inf')):
                        self.current_positions[product] -= order['quantity']
                
                results[product].append({
                    'timestamp': timestamp,
                    'mid_price': current_row['mid_price'],
                    'position': self.current_positions[product],
                    'orders': orders
                })
        
        return results
    
    def plot_results(self, results: Dict, product: str):
        """Plot backtest results for a product"""
        if product not in results:
            return
        
        df_results = pd.DataFrame(results[product])
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # Plot mid price and positions
        ax1.plot(df_results['timestamp'], df_results['mid_price'], label='Mid Price', alpha=0.7)
        ax1.set_ylabel('Price')
        ax1.set_title(f'{product} - Market Making Strategy Results')
        ax1.legend()
        ax1.grid(True)
        
        # Plot positions
        ax2.plot(df_results['timestamp'], df_results['position'], label='Position', color='orange')
        ax2.axhline(y=self.position_limits[product], color='r', linestyle='--', label='Position Limit')
        ax2.axhline(y=-self.position_limits[product], color='r', linestyle='--')
        ax2.set_xlabel('Timestamp')
        ax2.set_ylabel('Position')
        ax2.legend()
        ax2.grid(True)
        
        plt.tight_layout()
        plt.show()
    
    def run_analysis(self):
        """Run complete analysis and backtesting"""
        print("Loading market data...")
        self.load_data()
        
        print("\nAnalyzing market characteristics...")
        analysis = self.analyze_market_data()
        
        for product in self.products:
            print(f"\n{product}:")
            print(f"  Average Mid Price: {analysis[product]['avg_mid_price']:.2f}")
            print(f"  Price Volatility: {analysis[product]['avg_volatility']:.2f}")
            print(f"  Average Spread: {analysis[product]['avg_spread']:.2f}")
            print(f"  Average Daily Volume: {analysis[product]['avg_daily_volume']:.0f}")
        
        print("\nRunning backtest on day -2...")
        results = self.backtest_strategy(-2)
        
        for product in self.products:
            if product in results and results[product]:
                final_position = results[product][-1]['position']
                print(f"\n{product} Final Position: {final_position}")
        
        return analysis, results

if __name__ == "__main__":
    strategy = MarketMakingStrategy()
    analysis, results = strategy.run_analysis()
    
    # Plot results for both products
    for product in strategy.products:
        strategy.plot_results(results, product)
