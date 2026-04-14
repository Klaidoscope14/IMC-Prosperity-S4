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
        'ASH_COATED_OSMIUM': 15,
        'INTARIAN_PEPPER_ROOT': 15,
    }

    # Minimum edge we want to capture over mid-price
    MIN_EDGE = 2
    
    def __init__(self):
        # Price history for fair value calculation
        self.price_history = defaultdict(list)
        self.max_history_length = 50
        
        # Dynamic spread parameters
        self.base_spreads = {
            'ASH_COATED_OSMIUM': 3,
            'INTARIAN_PEPPER_ROOT': 5
        }
        
        # Risk management parameters
        self.stop_loss_threshold = 0.20  # 5% stop loss
        self.max_drawdown = 0.10  # 10% max drawdown
        self.entry_prices = {}  # Track entry prices for stop loss
        self.max_position_utilization = 1.0  # Use 100% of position limit for aggressive trading
        
        # Trade clustering for support/resistance levels
        self.price_clusters = defaultdict(list)  # Track price levels with trade counts
        self.cluster_threshold = 5  # Minimum trades to consider a level significant
        
        # Avellaneda-Stoikov model parameters
        self.gamma = 0.1  # Risk aversion parameter
        self.sigma = 0.02  # Volatility estimate
        self.kappa = 1.0  # Order book depth parameter
        
        # Cross-product arbitrage tracking
        self.arbitrage_threshold = 2  # Minimum profit for arbitrage
        self.product_prices = {}  # Track prices for arbitrage detection 

    def run(self, state) -> Tuple[Dict[str, List[Order]], int, str]:
        # Load saved data
        if state.traderData:
            saved_data = json.loads(state.traderData)
            self.price_history = defaultdict(list, saved_data.get('price_history', {}))
            self.entry_prices = saved_data.get('entry_prices', {})
        
        result = {}
        
        # Cross-product arbitrage detection
        arbitrage_orders = self._detect_arbitrage(state)
        if arbitrage_orders:
            result.update(arbitrage_orders)
        
        for product in self.POSITION_LIMITS:
            if product not in state.order_depths:
                continue
            
            # Update product prices for arbitrage
            if state.order_depths[product].buy_orders and state.order_depths[product].sell_orders:
                best_bid = max(state.order_depths[product].buy_orders.keys())
                best_ask = min(state.order_depths[product].sell_orders.keys())
                self.product_prices[product] = (best_bid + best_ask) / 2
            
            # Check stop loss before trading
            current_position = state.position.get(product, 0)
            if self._should_stop_trading(product, current_position, state.order_depths[product]):
                continue  # Skip trading for this product if stop loss triggered
            
            orders = self._compute_orders(
                product,
                state.order_depths[product],
                current_position
            )
            if orders:
                result[product] = orders
                
        # Save data for next iteration
        traderData = json.dumps({
            'price_history': dict(self.price_history),
            'entry_prices': self.entry_prices
        })
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
        
        # Micro-price adjustment: Weighting mid-price by volume and order book imbalance
        bid_vol = depth.buy_orders[best_bid]
        ask_vol = abs(depth.sell_orders[best_ask])
        
        # Volume-weighted mid-price
        volume_weighted_mid = (best_bid * ask_vol + best_ask * bid_vol) / (bid_vol + ask_vol)
        
        # Order book imbalance signal
        if (bid_vol + ask_vol) > 0:
            imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol)
        else:
            imbalance = 0
        
        # Combine signals: 70% volume-weighted mid, 30% imbalance-adjusted
        mid_price = volume_weighted_mid + imbalance * 0.5
        
        # Update price history
        self.price_history[product].append(mid_price)
        if len(self.price_history[product]) > self.max_history_length:
            self.price_history[product].pop(0)
        
        # Enhanced fair value with historical context and advanced alpha
        if len(self.price_history[product]) > 20:
            # Advanced alpha: Micro mean reversion patterns
            short_mean = statistics.mean(self.price_history[product][-5:])  # Last 5 prices
            long_mean = statistics.mean(self.price_history[product][-20:])  # Last 20 prices
            
            # Alpha signal: Short-term vs long-term mean reversion
            signal = short_mean - long_mean
            
            # Apply alpha signal with reduced weight (more conservative)
            fair_value = mid_price - signal * 0.15
            
            # Trade clustering: Adjust for support/resistance levels
            # cluster_adjustment = self._get_cluster_adjustment(product, mid_price)
            # fair_value += cluster_adjustment
        elif len(self.price_history[product]) > 10:
            # Fallback to simple mean reversion
            historical_avg = statistics.mean(self.price_history[product][-10:])
            fair_value = 0.7 * mid_price + 0.3 * historical_avg
        else:
            fair_value = mid_price

        # 2. Inventory Skewing & Pressure Model
        # If we are long (+), we lower our "personal" fair value to encourage selling.
        # If we are short (-), we raise it to encourage buying.
        inventory_ratio = position / limit
        skew = -0.5 * inventory_ratio  # More conservative skew based on Round1 analysis
        fair_value = fair_value + skew
        
        # Inventory pressure model for faster clearing
        inventory_pressure = position * 0.1
        fair_value -= inventory_pressure
        
        # 3. Aggressive Market Taking
        # Buy from asks that are below our calculated fair value
        for ask, vol in sorted(depth.sell_orders.items()):
            if ask <= fair_value - 1 and position < limit:
                buy_qty = min(abs(vol), limit - position)
                orders.append(Order(product, ask, buy_qty))
                position += buy_qty

        # Sell to bids that are above our calculated fair value
        for bid, vol in sorted(depth.buy_orders.items(), reverse=True):
            if bid >= fair_value + 1 and position > -limit:
                sell_qty = min(abs(vol), limit + position)
                orders.append(Order(product, bid, -sell_qty))
                position -= sell_qty

        # 4. Avellaneda-Stoikov Optimal Quoting
        # Calculate optimal reservation price and spread
        reservation_price = mid_price - position * self.gamma * self.sigma**2 / self.kappa
        optimal_spread = self.gamma * self.sigma**2 / self.kappa + 2 * self.gamma * self.sigma**2 / self.kappa * (1 + 2 * position / limit)
        
        # Convert to integer prices
        half_spread = max(1, int(optimal_spread / 2))
        bid_price = int(reservation_price - half_spread)
        ask_price = int(reservation_price + half_spread)
        
        # Ensure we stay within market bounds
        bid_price = min(bid_price, best_bid + 1)
        ask_price = max(ask_price, best_ask - 1)
        
        # Inventory skew in quoting (enhanced)
        if position > 5:  # long
            ask_price = min(ask_price, best_ask - 2)   # sell more aggressively
        elif position < -5:  # short
            bid_price = max(bid_price, best_bid + 2)   # buy more aggressively
        
        # More aggressive order sizing with position-based logic and alpha multipliers
        if abs(position) < limit * 0.5:
            max_order_size = limit // 2  # Use up to 50% of position limit per order
        else:
            max_order_size = limit // 4  # Use up to 25% when position is large
        
        # Size-based alpha: Scale order size based on imbalance (symmetric)
        buy_multiplier = 1.0
        sell_multiplier = 1.0
        
        if imbalance > 0.3:
            buy_multiplier = 1.5  # Increase size when buying pressure
        elif imbalance < -0.3:
            sell_multiplier = 1.5  # Increase size when selling pressure
        
        # Apply alpha multipliers to respective order types
        adjusted_buy_size = int(max_order_size * buy_multiplier)
        adjusted_sell_size = int(max_order_size * sell_multiplier)
        
        if position < limit:
            buy_qty = min(adjusted_buy_size, limit - position)
            orders.append(Order(product, min(bid_price, best_bid + 1), buy_qty))
        if position > -limit:
            sell_qty = min(adjusted_sell_size, limit + position)
            orders.append(Order(product, max(ask_price, best_ask - 1), -sell_qty))

        return orders
    
    def _should_stop_trading(self, product: str, position: int, depth) -> bool:
        """Check if stop loss should trigger for this product"""
        if position == 0:
            return False
            
        # Get current market price
        if not depth.buy_orders or not depth.sell_orders:
            return False
            
        best_bid = max(depth.buy_orders.keys())
        best_ask = min(depth.sell_orders.keys())
        current_price = (best_bid + best_ask) / 2
        
        # Get entry price
        if product not in self.entry_prices:
            return False
            
        entry_price = self.entry_prices[product]
        
        # Calculate P&L percentage
        if position > 0:  # Long position
            pnl_pct = (current_price - entry_price) / entry_price
        else:  # Short position
            pnl_pct = (entry_price - current_price) / entry_price
            
        # Stop loss check
        if pnl_pct < -self.stop_loss_threshold:
            return True
            
        # Max drawdown check
        if pnl_pct < -self.max_drawdown:
            return True
            
        return False
    
    def _update_entry_price(self, product: str, position: int, execution_price: float):
        """Update entry price when opening new positions"""
        current_entry = self.entry_prices.get(product, 0)
        
        if position == 0:
            # Closed position, reset entry price
            self.entry_prices[product] = 0
        elif (current_entry == 0 and position != 0):
            # Opening new position
            self.entry_prices[product] = execution_price
            
    def _get_cluster_adjustment(self, product: str, current_price: float) -> float:
        """Calculate support/resistance adjustment based on trade clustering"""
        # Find price levels with significant trade activity
        adjustment = 0
        
        # Check if current price is near a clustered level
        for price_level, trade_count in self.price_clusters[product]:
            if trade_count >= self.cluster_threshold:
                # Significant level found
                price_diff = abs(current_price - price_level)
                if price_diff <= 2:  # Within 2 units of clustered level
                    # Adjust fair value away from support/resistance
                    if current_price > price_level:
                        # Near resistance - lower fair value
                        adjustment = -1.5
                    else:
                        # Near support - raise fair value
                        adjustment = 1.5
                    break
        
        return adjustment
    
    def _update_trade_clusters(self, product: str, trade_price: float):
        """Update trade clustering information"""
        # Round price to nearest integer for clustering
        rounded_price = round(trade_price)
        
        # Find existing cluster or create new one
        cluster_found = False
        for i, (price_level, trade_count) in enumerate(self.price_clusters[product]):
            if abs(price_level - rounded_price) <= 1:  # Same cluster within 1 unit
                self.price_clusters[product][i] = (price_level, trade_count + 1)
                cluster_found = True
                break
        
        if not cluster_found:
            # New price level cluster
            self.price_clusters[product].append((rounded_price, 1))
        
        # Keep only recent clusters (last 50 levels)
        if len(self.price_clusters[product]) > 50:
            self.price_clusters[product].pop(0)
    
    def _get_previous_position(self, product: str) -> int:
        """Helper to get previous position (simplified)"""
        # This would need proper state management in a real implementation
        return 0
    
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
        
        # Adaptive spread logic based on market conditions
        if market_spread > 10:
            my_spread = 3  # Exploit wide spreads
        else:
            my_spread = 1  # Stay competitive in tight markets
        
        # 3. Inventory component (widen spread when near limits)
        inventory_ratio = abs(position) / limit
        # Enhanced position-based spread widening
        if inventory_ratio > 0.5:
            inventory_multiplier = 1 + inventory_ratio * 1.0  # 100% wider at 50%+ utilization
        elif inventory_ratio > 0.3:
            inventory_multiplier = 1 + inventory_ratio * 0.7  # 70% wider at 30%+ utilization
        else:
            inventory_multiplier = 1 + inventory_ratio * 0.5  # 50% wider at max position
        
        # 4. Combine components
        dynamic_spread = max(
            base_spread,
            market_spread * 0.3,  # Be slightly tighter than market
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
    
    def _detect_arbitrage(self, state) -> Dict[str, List[Order]]:
        """Detect and execute cross-product arbitrage opportunities"""
        orders = {}
        
        # Check if we have price data for both products
        if len(self.product_prices) < 2:
            return orders
        
        # Get current positions
        positions = state.position
        
        # Calculate price spread between products
        products = list(self.POSITION_LIMITS.keys())
        if len(products) >= 2:
            product1, product2 = products[0], products[1]
            
            if product1 in self.product_prices and product2 in self.product_prices:
                price1 = self.product_prices[product1]
                price2 = self.product_prices[product2]
                
                # Simple arbitrage: buy low, sell high
                if price1 < price2 - self.arbitrage_threshold:
                    # Buy product1, sell product2
                    if positions.get(product1, 0) > -self.POSITION_LIMITS[product1]:
                        # Can still buy product1
                        buy_qty = min(5, self.POSITION_LIMITS[product1] + positions.get(product1, 0))
                        if product1 not in orders:
                            orders[product1] = []
                        orders[product1].append(Order(product1, int(price1), buy_qty))
                    
                    if positions.get(product2, 0) > -self.POSITION_LIMITS[product2]:
                        # Can sell product2
                        sell_qty = min(5, self.POSITION_LIMITS[product2] + positions.get(product2, 0))
                        if product2 not in orders:
                            orders[product2] = []
                        orders[product2].append(Order(product2, int(price2), -sell_qty))
                
                elif price2 < price1 - self.arbitrage_threshold:
                    # Buy product2, sell product1
                    if positions.get(product2, 0) > -self.POSITION_LIMITS[product2]:
                        buy_qty = min(5, self.POSITION_LIMITS[product2] + positions.get(product2, 0))
                        if product2 not in orders:
                            orders[product2] = []
                        orders[product2].append(Order(product2, int(price2), buy_qty))
                    
                    if positions.get(product1, 0) > -self.POSITION_LIMITS[product1]:
                        sell_qty = min(5, self.POSITION_LIMITS[product1] + positions.get(product1, 0))
                        if product1 not in orders:
                            orders[product1] = []
                        orders[product1].append(Order(product1, int(price1), -sell_qty))
        
        return orders