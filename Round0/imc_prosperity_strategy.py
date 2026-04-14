#!/usr/bin/env python3
"""
IMC Prosperity Season 4 - Competition Trading Strategy
====================================================

Compliant trading strategy for IMC Prosperity competition.
Follows all rules and requirements from rules.md.

Author: Trading Strategy Development
Date: April 2026
"""

from typing import Dict, List, Tuple
import json

class Order:
    """Order class for competition compliance"""
    def __init__(self, symbol: str, price: int, quantity: int):
        self.symbol = symbol
        self.price = price
        self.quantity = quantity

class TradingState:
    """TradingState class for competition compliance"""
    def __init__(self):
        self.order_depths = {}
        self.own_trades = {}
        self.market_trades = {}
        self.position = {}
        self.observations = None
        self.traderData = ""
        self.timestamp = 0

class Trader:
    """
    Competition-compliant trading strategy
    """
    
    def __init__(self):
        # Position limits (example values - adjust based on actual competition limits)
        self.position_limits = {
            'EMERALDS': 50,
            'TOMATOES': 100
        }
        
        # Strategy parameters
        self.price_history = {product: [] for product in self.position_limits}
        self.max_history_length = 100
        self.momentum_window = 10
        self.mean_reversion_window = 20
        self.base_position_size = {'EMERALDS': 6, 'TOMATOES': 8}
        
        # Advanced strategy parameters
        self.momentum_threshold = 3.0
        self.extreme_momentum_threshold = 5.0
        self.pattern_window = 20
        self.volatility_window = 30
        
        # Multi-timeframe analysis
        self.short_term_window = 5
        self.medium_term_window = 15
        self.long_term_window = 30
        self.timeframe_weights = {'short': 0.5, 'medium': 0.3, 'long': 0.2}
        
        # Pattern recognition
        self.pattern_history = {product: [] for product in self.position_limits}
        self.pattern_signal_strength = {product: 0 for product in self.position_limits}
        
        # Cross-product arbitrage - Safer parameters
        self.price_ratio_history = []
        self.price_ratio_window = 30
        self.arbitrage_threshold = 2.5  # Stricter z-score threshold for safety
        self.arbitrage_position_size = 8
        self.hedge_ratio = 0.6
        self.max_arbitrage_spread = 4  # Maximum spread for arbitrage execution
        self.min_arbitrage_liquidity = 10  # Minimum liquidity for both legs
        self.arbitrage_execution_timeout = 3  # Periods to wait for both legs
        self.position_balance_tolerance = 2  # Tolerance for position balancing
        
        # Risk management
        self.max_position_per_trade = 10
        self.min_spread_threshold = 1
        self.volatility_forecasts = {product: [] for product in self.position_limits}
        
        # Edge threshold parameters
        self.edge_threshold_enabled = True
        self.min_liquidity_threshold = 5  # Minimum size at best levels
        self.edge_price_threshold = 3  # Maximum distance from mid price for edge detection
        self.liquidity_depth_levels = 3  # Number of levels to check for liquidity
        self.edge_fair_price_adjustment = 2  # Adjustment when near edges
        self.poor_liquidity_penalty = 0.7  # Position size multiplier for poor liquidity
        
        # Simplified signal parameters - only used when signals are enabled
        self.price_weighted_signals = False  # Start disabled
        self.price_signal_weight = 0.3  # Weight of price level in signal combination
        self.momentum_signal_weight = 0.4  # Weight of momentum signals
        self.pattern_signal_weight = 0.2  # Weight of pattern signals
        self.timeframe_signal_weight = 0.1  # Weight of timeframe signals
        self.min_signal_threshold = 0.6  # Minimum combined signal strength to trade
        self.signal_persistence_threshold = 0.4  # Minimum signal to maintain position
        
        # Trading frequency reduction parameters
        self.frequency_reduction_enabled = True
        self.trade_cooldown_period = 5  # Minimum periods between trades for same product
        self.signal_confirmation_periods = 3  # Periods to confirm signal before trading
        self.max_trades_per_session = 20  # Maximum trades per product per session
        self.volatility_based_filtering = True
        self.min_volatility_threshold = 2  # Minimum volatility for active trading
        self.max_volatility_threshold = 20  # Maximum volatility for safe trading
        
        # Trading frequency tracking
        self.last_trade_timestamp = {product: 0 for product in self.position_limits}
        self.trade_count_session = {product: 0 for product in self.position_limits}
        self.signal_history = {product: [] for product in self.position_limits}
        self.session_start_timestamp = 0
        
        # Safer arbitrage tracking
        self.pending_arbitrage_legs = {}  # Track incomplete arbitrage positions
        self.arbitrage_position_balances = {product: 0 for product in self.position_limits}
        self.last_arbitrage_timestamp = 0
        
        # Simplified strategy toggles - START WITH PURE MARKET MAKING
        self.pure_market_making_enabled = True  # ALWAYS ON - baseline strategy
        
        # Add signals ONE AT A TIME - start all disabled
        self.momentum_signal_enabled = False  # Add this first after testing pure MM
        self.pattern_signal_enabled = False   # Add this second
        self.arbitrage_signal_enabled = False # Add this third
        self.multi_timeframe_signal_enabled = False  # Add this last
        
        # Legacy toggles (kept for compatibility but disabled)
        self.aggressive_momentum_enabled = False
        self.pattern_recognition_enabled = False
        self.multi_timeframe_enabled = False
        self.cross_product_arbitrage_enabled = False
        self.volatility_risk_management = True
        
        # Signal hierarchy - only one active at a time
        self.active_signal_type = 'pure_market_making'  # Options: 'pure_market_making', 'momentum', 'pattern', 'arbitrage', 'multi_timeframe'
        self.signal_test_mode = True  # Only allow one signal type at a time

    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:
        """
        Main trading method called by competition system
        
        Args:
            state: Current trading state with market data
            
        Returns:
            Tuple of (orders, conversions, traderData)
        """
        # Initialize result dictionary
        result = {}
        
        # Calculate fair prices for all products
        fair_prices = {}
        for product in self.position_limits.keys():
            if product in state.order_depths:
                fair_price = self.calculate_fair_price(product, state.order_depths[product])
                if fair_price is not None:
                    fair_prices[product] = fair_price
        
        # SIMPLIFIED ARBITRAGE - only if arbitrage signal is enabled
        arbitrage_orders = {product: [] for product in self.position_limits}
        
        if self.arbitrage_signal_enabled and self.active_signal_type == 'arbitrage':
            arbitrage_opportunities = self.detect_cross_product_arbitrage(fair_prices, state)
            arbitrage_orders = self.execute_safer_arbitrage(arbitrage_opportunities, state)
        # Otherwise, no arbitrage to keep things simple
        
        # Process each product with enhanced strategies
        for product in self.position_limits.keys():
            if product in state.order_depths:
                # Generate individual product orders
                orders = self.generate_orders(product, state)
                
                # Add arbitrage orders only if arbitrage signal is active
                if self.arbitrage_signal_enabled and product in arbitrage_orders:
                    orders.extend(arbitrage_orders[product])
                
                if orders:
                    result[product] = orders
        
        # Return required format
        conversions = 0  # No conversions for this strategy
        traderData = self.serialize_state(state)
        
        # Update arbitrage tracking
        self.update_arbitrage_tracking(state)
        
        return result, conversions, traderData

    def generate_orders(self, product: str, state: TradingState) -> List[Order]:
        """Generate sophisticated trading orders for a product"""
        orders = []
        
        # Get market data
        order_depth = state.order_depths[product]
        current_position = state.position.get(product, 0)
        
        # Calculate fair price
        fair_price = self.calculate_fair_price(product, order_depth)
        if fair_price is None:
            return orders
        
        # Update price history
        self.price_history[product].append(fair_price)
        if len(self.price_history[product]) > self.max_history_length:
            self.price_history[product] = self.price_history[product][-self.max_history_length:]
        
        # SIMPLIFIED SIGNAL GENERATION - Only one signal type at a time
        signal_decision = self.get_simplified_signal_decision(product, fair_price, order_depth, state)
        
        # Update frequency tracking
        self.update_trading_frequency_tracking(product, signal_decision, state.timestamp)
        
        # Check trading frequency constraints
        can_trade = self.check_trading_frequency_constraints(product, state.timestamp, signal_decision)
        
        # Check volatility-based filtering
        volatility = self.calculate_volatility(product)
        if self.volatility_based_filtering:
            if volatility < self.min_volatility_threshold or volatility > self.max_volatility_threshold:
                can_trade = False  # Skip trading in extreme volatility conditions
        
        # Calculate position size - simplified
        base_size = self.base_position_size[product]
        position_multiplier = 1.0  # Start with base multiplier
        
        # Apply edge threshold penalty if needed
        edge_info = self.check_edge_conditions(product, order_depth, fair_price)
        if edge_info['should_reduce_position']:
            position_multiplier *= self.poor_liquidity_penalty
        
        # Apply signal confidence to position size (if signal is active)
        if signal_decision['confidence'] < 0.8 and signal_decision['confidence'] > 0:
            position_multiplier *= signal_decision['confidence']
        
        dynamic_size = int(base_size * position_multiplier)
        
        # Position limit check
        position_limit = self.position_limits[product]
        available_buy_capacity = position_limit - current_position
        available_sell_capacity = position_limit + current_position
        
        # SIMPLIFIED TRADING LOGIC
        if (signal_decision['action'] == 'buy' and 
            can_trade and available_buy_capacity > 0):
            
            buy_price = self.calculate_simplified_buy_price(product, order_depth, fair_price, edge_info)
            if buy_price is not None:
                buy_quantity = min(dynamic_size, available_buy_capacity)
                if buy_quantity > 0:
                    orders.append(Order(product, buy_price, buy_quantity))
                    # Update tracking for executed trade
                    self.update_trading_frequency_tracking(product, signal_decision, state.timestamp, True)
        
        elif (signal_decision['action'] == 'sell' and 
              can_trade and available_sell_capacity > 0):
            
            sell_price = self.calculate_simplified_sell_price(product, order_depth, fair_price, edge_info)
            if sell_price is not None:
                sell_quantity = min(dynamic_size, available_sell_capacity)
                if sell_quantity > 0:
                    orders.append(Order(product, sell_price, -sell_quantity))
                    # Update tracking for executed trade
                    self.update_trading_frequency_tracking(product, signal_decision, state.timestamp, True)
        
        return orders
    
    def get_simplified_signal_decision(self, product: str, fair_price: int, order_depth, state: TradingState) -> Dict:
        """
        Simplified signal decision - only one signal type at a time
        Returns: {'action': 'buy/sell/hold', 'confidence': 0.0-1.0, 'signal_type': str}
        """
        decision = {
            'action': 'hold',
            'confidence': 0.0,
            'signal_type': self.active_signal_type
        }
        
        # START WITH PURE MARKET MAKING - no signals, just basic market making
        if self.active_signal_type == 'pure_market_making':
            return self.get_pure_market_making_decision(product, fair_price, order_depth, state)
        
        # Add signals ONE AT A TIME - only enable one at a time
        elif self.active_signal_type == 'momentum' and self.momentum_signal_enabled:
            return self.get_momentum_signal_decision(product, fair_price, order_depth, state)
        
        elif self.active_signal_type == 'pattern' and self.pattern_signal_enabled:
            return self.get_pattern_signal_decision(product, fair_price, order_depth, state)
        
        elif self.active_signal_type == 'arbitrage' and self.arbitrage_signal_enabled:
            return self.get_arbitrage_signal_decision(product, fair_price, order_depth, state)
        
        elif self.active_signal_type == 'multi_timeframe' and self.multi_timeframe_signal_enabled:
            return self.get_multi_timeframe_signal_decision(product, fair_price, order_depth, state)
        
        # Default to pure market making if no valid signal type
        return self.get_pure_market_making_decision(product, fair_price, order_depth, state)
    
    def get_pure_market_making_decision(self, product: str, fair_price: int, order_depth, state: TradingState) -> Dict:
        """
        Pure market making - no complex signals, just basic bid/ask placement
        """
        decision = {
            'action': 'hold',
            'confidence': 0.0,
            'signal_type': 'pure_market_making'
        }
        
        # Simple market making logic - always place quotes on both sides
        best_bid = self.get_best_bid(order_depth)
        best_ask = self.get_best_ask(order_depth)
        
        if best_bid is None or best_ask is None or fair_price is None:
            return decision
        
        # Check if we have capacity to trade
        current_position = state.position.get(product, 0)
        position_limit = self.position_limits[product]
        
        # Simple decision: always provide liquidity if we have capacity
        if current_position < position_limit * 0.8:  # Can buy more
            decision['action'] = 'buy'
            decision['confidence'] = 0.5  # Moderate confidence for pure MM
        
        if current_position > -position_limit * 0.8:  # Can sell more
            if decision['action'] == 'buy':
                decision['action'] = 'both'  # Can do both sides
            else:
                decision['action'] = 'sell'
            decision['confidence'] = 0.5
        
        return decision
    
    def get_momentum_signal_decision(self, product: str, fair_price: int, order_depth, state: TradingState) -> Dict:
        """
        Momentum signal decision - only momentum, no other signals
        """
        decision = {
            'action': 'hold',
            'confidence': 0.0,
            'signal_type': 'momentum'
        }
        
        if not self.momentum_signal_enabled:
            return decision
        
        # Only analyze momentum, ignore other signals
        momentum_signals = self.analyze_momentum_signals(product, fair_price)
        
        # Simple momentum decision
        short_momentum = momentum_signals.get('short_momentum', 0)
        extreme_momentum = momentum_signals.get('extreme_momentum', False)
        
        if extreme_momentum and abs(short_momentum) > self.momentum_threshold * 2:
            decision['action'] = 'buy' if short_momentum > 0 else 'sell'
            decision['confidence'] = min(abs(short_momentum) / (self.momentum_threshold * 3), 1.0)
        elif abs(short_momentum) > self.momentum_threshold:
            decision['action'] = 'buy' if short_momentum > 0 else 'sell'
            decision['confidence'] = min(abs(short_momentum) / (self.momentum_threshold * 2), 0.8)
        
        return decision
    
    def get_pattern_signal_decision(self, product: str, fair_price: int, order_depth, state: TradingState) -> Dict:
        """
        Pattern signal decision - only patterns, no other signals
        """
        decision = {
            'action': 'hold',
            'confidence': 0.0,
            'signal_type': 'pattern'
        }
        
        if not self.pattern_signal_enabled:
            return decision
        
        # Only analyze patterns, ignore other signals
        pattern_signals = self.detect_patterns(product, fair_price)
        
        # Simple pattern decision
        breakout_signal = pattern_signals.get('breakout_signal', 'neutral')
        pattern_confidence = pattern_signals.get('pattern_confidence', 0)
        
        if breakout_signal in ['buy', 'sell'] and pattern_confidence > 0.6:
            decision['action'] = breakout_signal
            decision['confidence'] = pattern_confidence
        
        return decision
    
    def get_arbitrage_signal_decision(self, product: str, fair_price: int, order_depth, state: TradingState) -> Dict:
        """
        Arbitrage signal decision - only arbitrage, no other signals
        """
        decision = {
            'action': 'hold',
            'confidence': 0.0,
            'signal_type': 'arbitrage'
        }
        
        if not self.arbitrage_signal_enabled:
            return decision
        
        # Arbitrage is handled separately in main run method
        # Return hold for individual products
        return decision
    
    def get_multi_timeframe_signal_decision(self, product: str, fair_price: int, order_depth, state: TradingState) -> Dict:
        """
        Multi-timeframe signal decision - only timeframe analysis, no other signals
        """
        decision = {
            'action': 'hold',
            'confidence': 0.0,
            'signal_type': 'multi_timeframe'
        }
        
        if not self.multi_timeframe_signal_enabled:
            return decision
        
        # Only analyze timeframe, ignore other signals
        timeframe_signals = self.analyze_multi_timeframe(product)
        
        # Simple timeframe decision
        overall_signal = timeframe_signals.get('overall_signal', 'neutral')
        confidence = timeframe_signals.get('confidence', 0)
        
        if overall_signal in ['buy', 'sell'] and confidence > 0.7:
            decision['action'] = overall_signal
            decision['confidence'] = confidence
        
        return decision
    
    def calculate_simplified_buy_price(self, product: str, order_depth, fair_price: int, edge_info: Dict) -> int:
        """
        Simplified buy price calculation - no complex signal interference
        """
        best_bid = self.get_best_bid(order_depth)
        best_ask = self.get_best_ask(order_depth)
        
        if best_bid is None or best_ask is None or fair_price is None:
            return None
        
        spread = best_ask - best_bid
        
        # Simple logic: place between best bid and fair price, never cross spread
        if fair_price > best_bid:
            max_price = min(fair_price, best_bid + max(1, spread // 2))
            return min(max_price, best_ask - 1)
        else:
            return best_bid
    
    def calculate_simplified_sell_price(self, product: str, order_depth, fair_price: int, edge_info: Dict) -> int:
        """
        Simplified sell price calculation - no complex signal interference
        """
        best_bid = self.get_best_bid(order_depth)
        best_ask = self.get_best_ask(order_depth)
        
        if best_bid is None or best_ask is None or fair_price is None:
            return None
        
        spread = best_ask - best_bid
        
        # Simple logic: place between fair price and best ask, never cross spread
        if fair_price < best_ask:
            min_price = max(fair_price, best_ask - max(1, spread // 2))
            return max(min_price, best_bid + 1)
        else:
            return best_ask

    def calculate_fair_price(self, product: str, order_depth) -> int:
        """Calculate fair price from order book"""
        best_bid = self.get_best_bid(order_depth)
        best_ask = self.get_best_ask(order_depth)
        
        if best_bid is not None and best_ask is not None:
            return (best_bid + best_ask) // 2
        elif best_bid is not None:
            return best_bid
        elif best_ask is not None:
            return best_ask
        else:
            return None
    
    def get_best_bid(self, order_depth) -> int:
        """Get best bid price from order book"""
        if hasattr(order_depth, 'buy_orders') and order_depth.buy_orders:
            return max(order_depth.buy_orders.keys())
        return None
    
    def get_best_ask(self, order_depth) -> int:
        """Get best ask price from order book"""
        if hasattr(order_depth, 'sell_orders') and order_depth.sell_orders:
            return min(order_depth.sell_orders.keys())
        return None
    
    def get_liquidity_at_level(self, order_depth, price: int, is_buy: bool) -> int:
        """Get total liquidity available at a specific price level"""
        if is_buy:
            # Check buy side liquidity
            if hasattr(order_depth, 'buy_orders') and price in order_depth.buy_orders:
                return order_depth.buy_orders[price]
        else:
            # Check sell side liquidity
            if hasattr(order_depth, 'sell_orders') and price in order_depth.sell_orders:
                return order_depth.sell_orders[price]
        return 0
    
    def check_edge_conditions(self, product: str, order_depth, fair_price: int) -> Dict:
        """
        Check if current market conditions are at edge of order book
        Returns: edge_info dict with edge conditions and adjustments
        """
        edge_info = {
            'is_edge_buy': False,
            'is_edge_sell': False,
            'buy_liquidity_score': 1.0,
            'sell_liquidity_score': 1.0,
            'price_adjustment': 0,
            'should_reduce_position': False
        }
        
        if not self.edge_threshold_enabled:
            return edge_info
        
        best_bid = self.get_best_bid(order_depth)
        best_ask = self.get_best_ask(order_depth)
        
        if best_bid is None or best_ask is None or fair_price is None:
            return edge_info
        
        mid_price = (best_bid + best_ask) // 2
        spread = best_ask - best_bid
        
        # Check buy side edge conditions
        best_bid_liquidity = self.get_liquidity_at_level(order_depth, best_bid, True)
        if best_bid_liquidity < self.min_liquidity_threshold:
            edge_info['is_edge_buy'] = True
            edge_info['buy_liquidity_score'] = best_bid_liquidity / self.min_liquidity_threshold
        
        # Check if best bid is too far from fair price (edge condition)
        if fair_price - best_bid > self.edge_price_threshold:
            edge_info['is_edge_buy'] = True
            edge_info['buy_liquidity_score'] = min(edge_info['buy_liquidity_score'], 0.5)
        
        # Check sell side edge conditions
        best_ask_liquidity = self.get_liquidity_at_level(order_depth, best_ask, False)
        if best_ask_liquidity < self.min_liquidity_threshold:
            edge_info['is_edge_sell'] = True
            edge_info['sell_liquidity_score'] = best_ask_liquidity / self.min_liquidity_threshold
        
        # Check if best ask is too far from fair price (edge condition)
        if best_ask - fair_price > self.edge_price_threshold:
            edge_info['is_edge_sell'] = True
            edge_info['sell_liquidity_score'] = min(edge_info['sell_liquidity_score'], 0.5)
        
        # Calculate price adjustment for edge conditions
        if edge_info['is_edge_buy']:
            edge_info['price_adjustment'] = self.edge_fair_price_adjustment
        if edge_info['is_edge_sell']:
            edge_info['price_adjustment'] = -self.edge_fair_price_adjustment
        
        # Determine if position should be reduced due to poor liquidity
        overall_liquidity_score = min(edge_info['buy_liquidity_score'], edge_info['sell_liquidity_score'])
        if overall_liquidity_score < 0.5:
            edge_info['should_reduce_position'] = True
        
        return edge_info
    
    def get_safe_price_levels(self, order_depth, fair_price: int, num_levels: int = 3) -> Dict:
        """
        Get safe price levels with sufficient liquidity
        Returns: {'buy_levels': [(price, liquidity)], 'sell_levels': [(price, liquidity)]}
        """
        safe_levels = {'buy_levels': [], 'sell_levels': []}
        
        if not hasattr(order_depth, 'buy_orders') or not hasattr(order_depth, 'sell_orders'):
            return safe_levels
        
        # Get buy levels (sorted descending)
        buy_prices = sorted(order_depth.buy_orders.keys(), reverse=True)
        for price in buy_prices[:num_levels]:
            liquidity = order_depth.buy_orders[price]
            if liquidity >= self.min_liquidity_threshold:
                safe_levels['buy_levels'].append((price, liquidity))
        
        # Get sell levels (sorted ascending)
        sell_prices = sorted(order_depth.sell_orders.keys())
        for price in sell_prices[:num_levels]:
            liquidity = order_depth.sell_orders[price]
            if liquidity >= self.min_liquidity_threshold:
                safe_levels['sell_levels'].append((price, liquidity))
        
        return safe_levels
    
    def calculate_price_signal_strength(self, product: str, fair_price: int, best_bid: int, best_ask: int) -> float:
        """
        Calculate signal strength based on price levels and position relative to fair price
        Returns: signal strength between -1 and 1
        """
        if fair_price is None or best_bid is None or best_ask is None:
            return 0.0
        
        spread = best_ask - best_bid
        if spread <= 0:
            return 0.0
        
        # Calculate position of fair price within spread
        fair_price_position = (fair_price - best_bid) / spread
        
        # Normalize to -1 to 1 range (center = 0, buy side = positive, sell side = negative)
        signal_strength = (fair_price_position - 0.5) * 2
        
        # Apply edge condition penalties
        if fair_price - best_bid > self.edge_price_threshold:
            signal_strength *= 0.7  # Reduce signal if far from bid
        if best_ask - fair_price > self.edge_price_threshold:
            signal_strength *= 0.7  # Reduce signal if far from ask
        
        return max(-1.0, min(1.0, signal_strength))
    
    def combine_signals_with_price(self, product: str, momentum_signals: Dict, pattern_signals: Dict, 
                                  timeframe_signals: Dict, fair_price: int, best_bid: int, best_ask: int) -> Dict:
        """
        Combine all signals with price-aware weighting
        Returns: combined signal dict with buy/sell strengths and confidence
        """
        combined = {
            'buy_strength': 0.0,
            'sell_strength': 0.0,
            'overall_signal': 'neutral',
            'confidence': 0.0,
            'signal_components': {}
        }
        
        if not self.price_weighted_signals:
            # Fallback to simple scoring if price weighting disabled
            return self.simple_signal_combination(momentum_signals, pattern_signals, timeframe_signals)
        
        # Calculate price signal strength
        price_signal = self.calculate_price_signal_strength(product, fair_price, best_bid, best_ask)
        
        # Calculate normalized signal strengths for each component
        momentum_strength = self.normalize_momentum_signal(momentum_signals)
        pattern_strength = self.normalize_pattern_signal(pattern_signals)
        timeframe_strength = self.normalize_timeframe_signal(timeframe_signals)
        
        # Weighted combination
        combined['buy_strength'] = (
            max(0, price_signal) * self.price_signal_weight +
            max(0, momentum_strength) * self.momentum_signal_weight +
            max(0, pattern_strength) * self.pattern_signal_weight +
            max(0, timeframe_strength) * self.timeframe_signal_weight
        )
        
        combined['sell_strength'] = (
            max(0, -price_signal) * self.price_signal_weight +
            max(0, -momentum_strength) * self.momentum_signal_weight +
            max(0, -pattern_strength) * self.pattern_signal_weight +
            max(0, -timeframe_strength) * self.timeframe_signal_weight
        )
        
        # Determine overall signal and confidence
        net_strength = combined['buy_strength'] - combined['sell_strength']
        combined['confidence'] = abs(net_strength)
        
        if net_strength > self.min_signal_threshold:
            combined['overall_signal'] = 'buy'
        elif net_strength < -self.min_signal_threshold:
            combined['overall_signal'] = 'sell'
        else:
            combined['overall_signal'] = 'neutral'
        
        # Store components for analysis
        combined['signal_components'] = {
            'price_signal': price_signal,
            'momentum_signal': momentum_strength,
            'pattern_signal': pattern_strength,
            'timeframe_signal': timeframe_strength
        }
        
        return combined
    
    def normalize_momentum_signal(self, momentum_signals: Dict) -> float:
        """Normalize momentum signals to -1 to 1 range"""
        strength = 0.0
        
        # Short-term momentum (highest weight)
        short_momentum = momentum_signals.get('short_momentum', 0)
        strength += max(-1, min(1, short_momentum / self.momentum_threshold)) * 0.4
        
        # Medium-term momentum
        medium_momentum = momentum_signals.get('medium_momentum', 0)
        strength += max(-1, min(1, medium_momentum / self.momentum_threshold)) * 0.3
        
        # Extreme momentum bonus
        if momentum_signals.get('extreme_momentum', False):
            strength += 0.3
        
        return max(-1, min(1, strength))
    
    def normalize_pattern_signal(self, pattern_signals: Dict) -> float:
        """Normalize pattern signals to -1 to 1 range"""
        strength = 0.0
        
        # Breakout signal
        breakout = pattern_signals.get('breakout_signal', 'neutral')
        if breakout == 'buy':
            strength += pattern_signals.get('pattern_confidence', 0) * 0.6
        elif breakout == 'sell':
            strength -= pattern_signals.get('pattern_confidence', 0) * 0.6
        
        # Mean reversion signal (lower weight)
        mean_reversion = pattern_signals.get('mean_reversion_signal', 'neutral')
        if mean_reversion == 'buy':
            strength += 0.2
        elif mean_reversion == 'sell':
            strength -= 0.2
        
        return max(-1, min(1, strength))
    
    def normalize_timeframe_signal(self, timeframe_signals: Dict) -> float:
        """Normalize timeframe signals to -1 to 1 range"""
        signal = timeframe_signals.get('overall_signal', 'neutral')
        confidence = timeframe_signals.get('confidence', 0)
        
        if signal == 'buy':
            return confidence
        elif signal == 'sell':
            return -confidence
        else:
            return 0.0
    
    def check_trading_frequency_constraints(self, product: str, current_timestamp: int, 
                                          combined_signal: Dict) -> bool:
        """
        Check if trading should be restricted based on frequency constraints
        Returns: True if trading is allowed, False if restricted
        """
        if not self.frequency_reduction_enabled:
            return True
        
        # Check cooldown period
        time_since_last_trade = current_timestamp - self.last_trade_timestamp[product]
        if time_since_last_trade < self.trade_cooldown_period:
            return False
        
        # Check maximum trades per session
        if self.trade_count_session[product] >= self.max_trades_per_session:
            return False
        
        # Check signal confirmation (require persistent signal)
        if len(self.signal_history[product]) < self.signal_confirmation_periods:
            return False
        
        recent_signals = self.signal_history[product][-self.signal_confirmation_periods:]
        
        # Handle both old and new signal formats
        current_signal_value = combined_signal.get('action', 'hold')
        if 'overall_signal' in combined_signal:  # Fallback for old format
            current_signal_value = combined_signal['overall_signal']
        
        consistent_signals = sum(1 for s in recent_signals if s == current_signal_value)
        
        # Require consistent signals for confirmation
        if consistent_signals < self.signal_confirmation_periods - 1:
            return False
        
        return True
    
    def update_trading_frequency_tracking(self, product: str, signal: Dict, timestamp: int, 
                                        executed_trade: bool = False):
        """Update tracking variables for frequency reduction"""
        # Update signal history - handle both old and new signal formats
        signal_value = signal.get('action', 'hold')  # Use 'action' for simplified signals
        if 'overall_signal' in signal:  # Fallback for old format
            signal_value = signal['overall_signal']
        
        self.signal_history[product].append(signal_value)
        if len(self.signal_history[product]) > 20:  # Keep last 20 signals
            self.signal_history[product] = self.signal_history[product][-20:]
        
        # Update trade tracking if executed
        if executed_trade:
            self.last_trade_timestamp[product] = timestamp
            self.trade_count_session[product] += 1
        
        # Reset session if needed (based on timestamp)
        if self.session_start_timestamp == 0:
            self.session_start_timestamp = timestamp
        elif timestamp - self.session_start_timestamp > 10000:  # New session after 10000 periods
            self.trade_count_session = {p: 0 for p in self.position_limits}
            self.session_start_timestamp = timestamp
    
    def simple_signal_combination(self, momentum_signals: Dict, pattern_signals: Dict, 
                                 timeframe_signals: Dict) -> Dict:
        """Fallback simple signal combination method"""
        combined = {
            'buy_strength': 0.0,
            'sell_strength': 0.0,
            'overall_signal': 'neutral',
            'confidence': 0.0,
            'signal_components': {}
        }
        
        # Simple scoring based on original logic
        buy_score = 0
        sell_score = 0
        
        # Momentum signals
        if momentum_signals['short_momentum'] > self.momentum_threshold:
            buy_score += 2
        if momentum_signals['short_momentum'] < -self.momentum_threshold:
            sell_score += 2
        if momentum_signals['extreme_momentum']:
            if momentum_signals['short_momentum'] > 0:
                buy_score += 3
            else:
                sell_score += 3
        
        # Pattern signals
        if pattern_signals['breakout_signal'] == 'buy':
            buy_score += 2
        if pattern_signals['breakout_signal'] == 'sell':
            sell_score += 2
        
        # Timeframe signals
        if timeframe_signals.get('overall_signal') == 'buy':
            buy_score += timeframe_signals.get('confidence', 0) * 2
        if timeframe_signals.get('overall_signal') == 'sell':
            sell_score += timeframe_signals.get('confidence', 0) * 2
        
        # Normalize to 0-1 range
        max_score = max(buy_score, sell_score, 1)
        combined['buy_strength'] = buy_score / max_score
        combined['sell_strength'] = sell_score / max_score
        
        # Determine overall signal
        if buy_score > sell_score + 1:
            combined['overall_signal'] = 'buy'
            combined['confidence'] = (buy_score - sell_score) / max_score
        elif sell_score > buy_score + 1:
            combined['overall_signal'] = 'sell'
            combined['confidence'] = (sell_score - buy_score) / max_score
        else:
            combined['overall_signal'] = 'neutral'
            combined['confidence'] = 0.0
        
        return combined
    
    def should_cross_spread(self, product: str, fair_price: int, best_bid: int, best_ask: int, 
                           momentum_signals: Dict, spread: int) -> Tuple[bool, str]:
        """
        Determine if crossing the spread is justified
        Returns: (should_cross, reason)
        """
        # Never cross if spread is too wide (prevent overpaying)
        if spread > 5:  # Configurable max spread for crossing
            return False, "spread_too_wide"
        
        # Never cross if fair price is not favorable
        if fair_price <= best_bid or fair_price >= best_ask:
            return False, "unfavorable_fair_price"
        
        # Only cross for extreme momentum with strong signals
        if momentum_signals.get('extreme_momentum', False):
            momentum_strength = momentum_signals.get('momentum_strength', 0)
            if momentum_strength > self.extreme_momentum_threshold:
                return True, "extreme_momentum"
        
        # Consider crossing for very tight spreads with moderate momentum
        if spread <= 2 and momentum_signals.get('momentum_strength', 0) > self.momentum_threshold:
            return True, "tight_spread_moderate_momentum"
        
        return False, "no_justification"

    def analyze_momentum_signals(self, product: str, current_price: int) -> Dict:
        """Analyze momentum signals with multiple timeframes"""
        signals = {
            'short_momentum': 0,
            'medium_momentum': 0,
            'long_momentum': 0,
            'extreme_momentum': False,
            'momentum_strength': 0
        }
        
        price_history = self.price_history[product]
        if len(price_history) < self.momentum_window:
            return signals
        
        # Short-term momentum
        if len(price_history) >= self.short_term_window:
            recent = price_history[-self.short_term_window:]
            older = price_history[-2*self.short_term_window:-self.short_term_window]
            if len(recent) > 0 and len(older) > 0:
                signals['short_momentum'] = (sum(recent)/len(recent)) - (sum(older)/len(older))
        
        # Medium-term momentum
        if len(price_history) >= self.medium_term_window:
            recent = price_history[-self.medium_term_window:]
            older = price_history[-2*self.medium_term_window:-self.medium_term_window]
            if len(recent) > 0 and len(older) > 0:
                signals['medium_momentum'] = (sum(recent)/len(recent)) - (sum(older)/len(older))
        
        # Long-term momentum
        if len(price_history) >= self.long_term_window:
            recent = price_history[-self.long_term_window:]
            older = price_history[-2*self.long_term_window:-self.long_term_window]
            if len(recent) > 0 and len(older) > 0:
                signals['long_momentum'] = (sum(recent)/len(recent)) - (sum(older)/len(older))
        
        # Calculate overall momentum strength
        total_momentum = abs(signals['short_momentum']) + abs(signals['medium_momentum']) + abs(signals['long_momentum'])
        signals['momentum_strength'] = total_momentum / 3
        
        # Detect extreme momentum
        if abs(signals['short_momentum']) > self.extreme_momentum_threshold:
            signals['extreme_momentum'] = True
        
        return signals
    
    def detect_patterns(self, product: str, current_price: int) -> Dict:
        """Detect intraday patterns and price breakouts"""
        patterns = {
            'breakout_signal': 'neutral',
            'pattern_confidence': 0,
            'mean_reversion_signal': 'neutral',
            'trend_strength': 0
        }
        
        price_history = self.price_history[product]
        if len(price_history) < self.pattern_window:
            return patterns
        
        recent_prices = price_history[-self.pattern_window:]
        
        # Calculate pattern statistics
        mean_price = sum(recent_prices) / len(recent_prices)
        
        # Calculate standard deviation
        variance = sum((price - mean_price) ** 2 for price in recent_prices) / len(recent_prices)
        std_dev = variance ** 0.5 if variance > 0 else 1
        
        # Z-score for current price
        z_score = (current_price - mean_price) / std_dev if std_dev > 0 else 0
        
        # Breakout detection
        if abs(z_score) > 2.0:
            patterns['breakout_signal'] = 'buy' if z_score > 0 else 'sell'
            patterns['pattern_confidence'] = min(abs(z_score) / 3.0, 1.0)
        
        # Mean reversion signal
        if abs(z_score) > 1.5:
            patterns['mean_reversion_signal'] = 'sell' if z_score > 0 else 'buy'
        
        # Trend strength calculation
        if len(recent_prices) >= 5:
            first_half = recent_prices[:len(recent_prices)//2]
            second_half = recent_prices[len(recent_prices)//2:]
            first_avg = sum(first_half) / len(first_half)
            second_avg = sum(second_half) / len(second_half)
            patterns['trend_strength'] = (second_avg - first_avg) / first_avg if first_avg > 0 else 0
        
        # Store pattern signal strength
        self.pattern_signal_strength[product] = patterns['pattern_confidence']
        
        return patterns
    
    def analyze_multi_timeframe(self, product: str) -> Dict:
        """Analyze signals across multiple timeframes"""
        if not self.multi_timeframe_enabled:
            return {'overall_signal': 'neutral', 'confidence': 0}
        
        price_history = self.price_history[product]
        if len(price_history) < self.long_term_window:
            return {'overall_signal': 'neutral', 'confidence': 0}
        
        signals = {'short': 'neutral', 'medium': 'neutral', 'long': 'neutral'}
        
        # Short-term signal
        if len(price_history) >= self.short_term_window:
            short_prices = price_history[-self.short_term_window:]
            if len(short_prices) >= 3:
                short_trend = (short_prices[-1] - short_prices[0]) / short_prices[0] if short_prices[0] > 0 else 0
                signals['short'] = 'buy' if short_trend > 0.005 else 'sell' if short_trend < -0.005 else 'neutral'
        
        # Medium-term signal
        if len(price_history) >= self.medium_term_window:
            medium_prices = price_history[-self.medium_term_window:]
            if len(medium_prices) >= 5:
                medium_trend = (medium_prices[-1] - medium_prices[0]) / medium_prices[0] if medium_prices[0] > 0 else 0
                signals['medium'] = 'buy' if medium_trend > 0.008 else 'sell' if medium_trend < -0.008 else 'neutral'
        
        # Long-term signal
        if len(price_history) >= self.long_term_window:
            long_prices = price_history[-self.long_term_window:]
            if len(long_prices) >= 10:
                long_trend = (long_prices[-1] - long_prices[0]) / long_prices[0] if long_prices[0] > 0 else 0
                signals['long'] = 'buy' if long_trend > 0.012 else 'sell' if long_trend < -0.012 else 'neutral'
        
        # Weighted signal combination
        signal_weights = {'buy': 0, 'sell': 0, 'neutral': 0}
        signal_weights[signals['short']] += self.timeframe_weights['short']
        signal_weights[signals['medium']] += self.timeframe_weights['medium']
        signal_weights[signals['long']] += self.timeframe_weights['long']
        
        overall_signal = max(signal_weights, key=signal_weights.get)
        confidence = signal_weights[overall_signal]
        
        return {
            'overall_signal': overall_signal,
            'confidence': confidence,
            'signals': signals
        }
    
    def calculate_position_multiplier(self, product: str, momentum_signals: Dict, pattern_signals: Dict, timeframe_signals: Dict) -> float:
        """Calculate dynamic position size multiplier"""
        multiplier = 1.0
        
        # Momentum-based adjustment
        if self.aggressive_momentum_enabled:
            momentum_strength = momentum_signals.get('momentum_strength', 0)
            if momentum_signals.get('extreme_momentum', False):
                multiplier *= 2.0  # Double position for extreme momentum
            elif momentum_strength > self.momentum_threshold:
                multiplier *= 1.5  # Increase position for strong momentum
            elif momentum_strength > 1:
                multiplier *= 1.2  # Slight increase for moderate momentum
        
        # Pattern-based adjustment
        if self.pattern_recognition_enabled:
            pattern_confidence = pattern_signals.get('pattern_confidence', 0)
            if pattern_confidence > 0.8:
                multiplier *= 1.3  # Strong pattern confidence
            elif pattern_confidence > 0.5:
                multiplier *= 1.1  # Moderate pattern confidence
        
        # Timeframe-based adjustment
        if self.multi_timeframe_enabled:
            timeframe_confidence = timeframe_signals.get('confidence', 0)
            if timeframe_confidence > 0.7:
                multiplier *= 1.2  # Strong multi-timeframe signal
        
        # Volatility adjustment
        if self.volatility_risk_management:
            volatility = self.calculate_volatility(product)
            if volatility > 15:  # High volatility - reduce position
                multiplier *= 0.7
            elif volatility < 5:  # Low volatility - can increase position
                multiplier *= 1.2
        
        # Cap multiplier to reasonable bounds
        return min(max(multiplier, 0.5), 2.5)
    
    def calculate_volatility(self, product: str) -> float:
        """Calculate price volatility for a product"""
        price_history = self.price_history[product]
        if len(price_history) < self.volatility_window:
            return 0
        
        recent_prices = price_history[-self.volatility_window:]
        if len(recent_prices) < 2:
            return 0
        
        mean_price = sum(recent_prices) / len(recent_prices)
        variance = sum((price - mean_price) ** 2 for price in recent_prices) / len(recent_prices)
        return variance ** 0.5
    
    def should_buy(self, product: str, momentum_signals: Dict, pattern_signals: Dict, timeframe_signals: Dict) -> bool:
        """Determine if should place buy orders"""
        buy_score = 0
        
        # Momentum signals
        if momentum_signals['short_momentum'] > self.momentum_threshold:
            buy_score += 2
        if momentum_signals['medium_momentum'] > 1:
            buy_score += 1
        if momentum_signals['extreme_momentum']:
            buy_score += 3
        
        # Pattern signals
        if pattern_signals['breakout_signal'] == 'buy':
            buy_score += 2
        if pattern_signals['mean_reversion_signal'] == 'buy':
            buy_score += 1
        
        # Timeframe signals
        if timeframe_signals.get('overall_signal') == 'buy':
            buy_score += timeframe_signals.get('confidence', 0) * 2
        
        return buy_score >= 2
    
    def should_sell(self, product: str, momentum_signals: Dict, pattern_signals: Dict, timeframe_signals: Dict) -> bool:
        """Determine if should place sell orders"""
        sell_score = 0
        
        # Momentum signals
        if momentum_signals['short_momentum'] < -self.momentum_threshold:
            sell_score += 2
        if momentum_signals['medium_momentum'] < -1:
            sell_score += 1
        if momentum_signals['extreme_momentum']:
            sell_score += 3
        
        # Pattern signals
        if pattern_signals['breakout_signal'] == 'sell':
            sell_score += 2
        if pattern_signals['mean_reversion_signal'] == 'sell':
            sell_score += 1
        
        # Timeframe signals
        if timeframe_signals.get('overall_signal') == 'sell':
            sell_score += timeframe_signals.get('confidence', 0) * 2
        
        return sell_score >= 2
    
    def calculate_buy_price(self, product: str, order_depth, momentum_signals: Dict) -> int:
        """Calculate optimal buy price with edge threshold protection"""
        best_bid = self.get_best_bid(order_depth)
        best_ask = self.get_best_ask(order_depth)
        fair_price = self.calculate_fair_price(product, order_depth)
        
        if best_bid is None or best_ask is None or fair_price is None:
            return None
        
        spread = best_ask - best_bid
        
        # Check edge conditions
        edge_info = self.check_edge_conditions(product, order_depth, fair_price)
        
        # Adjust fair price for edge conditions
        adjusted_fair_price = fair_price + edge_info['price_adjustment']
        
        # Get safe price levels
        safe_levels = self.get_safe_price_levels(order_depth, fair_price)
        
        # If edge conditions detected, use safer pricing
        if edge_info['is_edge_buy']:
            # Edge condition on buy side - be more conservative
            if safe_levels['buy_levels']:
                # Use the best safe level instead of best bid
                safe_price, safe_liquidity = safe_levels['buy_levels'][0]
                max_price = min(adjusted_fair_price, safe_price + max(1, spread // 3))
                return min(max_price, best_ask - 1)
            else:
                # No safe levels - stay very conservative
                return best_bid
        
        # Check if spread crossing is justified (considering edge conditions)
        should_cross, reason = self.should_cross_spread(product, adjusted_fair_price, best_bid, best_ask, momentum_signals, spread)
        
        # Reduce crossing likelihood in edge conditions
        if edge_info['should_reduce_position'] and should_cross:
            should_cross = False
        
        # Only cross spread if justified and not in edge condition
        if should_cross and not edge_info['is_edge_buy']:
            # Cross spread but with limits
            if reason == "extreme_momentum":
                # Can go closer to fair price but not beyond
                return min(adjusted_fair_price, best_ask - 1)
            elif reason == "tight_spread_moderate_momentum":
                # Slight cross for tight spreads
                return min(best_bid + spread // 2, adjusted_fair_price)
        
        # Never cross spread - stay on bid side
        if adjusted_fair_price > best_bid:
            # Place between best bid and adjusted fair price, but never cross
            max_price = min(adjusted_fair_price, best_bid + max(1, spread // 2))
            return min(max_price, best_ask - 1)  # Ensure we don't cross
        else:
            # Adjusted fair price is at or below best bid - place at best bid
            return best_bid
    
    def calculate_sell_price(self, product: str, order_depth, momentum_signals: Dict) -> int:
        """Calculate optimal sell price with edge threshold protection"""
        best_bid = self.get_best_bid(order_depth)
        best_ask = self.get_best_ask(order_depth)
        fair_price = self.calculate_fair_price(product, order_depth)
        
        if best_bid is None or best_ask is None or fair_price is None:
            return None
        
        spread = best_ask - best_bid
        
        # Check edge conditions
        edge_info = self.check_edge_conditions(product, order_depth, fair_price)
        
        # Adjust fair price for edge conditions
        adjusted_fair_price = fair_price + edge_info['price_adjustment']
        
        # Get safe price levels
        safe_levels = self.get_safe_price_levels(order_depth, fair_price)
        
        # If edge conditions detected, use safer pricing
        if edge_info['is_edge_sell']:
            # Edge condition on sell side - be more conservative
            if safe_levels['sell_levels']:
                # Use the best safe level instead of best ask
                safe_price, safe_liquidity = safe_levels['sell_levels'][0]
                min_price = max(adjusted_fair_price, safe_price - max(1, spread // 3))
                return max(min_price, best_bid + 1)
            else:
                # No safe levels - stay very conservative
                return best_ask
        
        # Check if spread crossing is justified (considering edge conditions)
        should_cross, reason = self.should_cross_spread(product, adjusted_fair_price, best_bid, best_ask, momentum_signals, spread)
        
        # Reduce crossing likelihood in edge conditions
        if edge_info['should_reduce_position'] and should_cross:
            should_cross = False
        
        # Only cross spread if justified and not in edge condition
        if should_cross and not edge_info['is_edge_sell']:
            # Cross spread but with limits
            if reason == "extreme_momentum":
                # Can go closer to fair price but not beyond
                return max(adjusted_fair_price, best_bid + 1)
            elif reason == "tight_spread_moderate_momentum":
                # Slight cross for tight spreads
                return max(best_ask - spread // 2, adjusted_fair_price)
        
        # Never cross spread - stay on ask side
        if adjusted_fair_price < best_ask:
            # Place between adjusted fair price and best ask, but never cross
            min_price = max(adjusted_fair_price, best_ask - max(1, spread // 2))
            return max(min_price, best_bid + 1)  # Ensure we don't cross
        else:
            # Adjusted fair price is at or above best ask - place at best ask
            return best_ask
    
    def detect_cross_product_arbitrage(self, fair_prices: Dict, state: TradingState) -> List[Dict]:
        """Detect safer arbitrage opportunities between products"""
        if not self.cross_product_arbitrage_enabled:
            return []
        
        opportunities = []
        
        if 'EMERALDS' not in fair_prices or 'TOMATOES' not in fair_prices:
            return opportunities
        
        emerald_price = fair_prices['EMERALDS']
        tomato_price = fair_prices['TOMATOES']
        
        if emerald_price <= 0:
            return opportunities
        
        # Check spread sizes for both products
        emerald_spread_ok = self.check_arbitrage_spread_conditions('EMERALDS', state)
        tomato_spread_ok = self.check_arbitrage_spread_conditions('TOMATOES', state)
        
        if not emerald_spread_ok or not tomato_spread_ok:
            return opportunities  # Skip if spreads are too large
        
        # Calculate price ratio
        current_ratio = tomato_price / emerald_price
        self.price_ratio_history.append(current_ratio)
        
        # Keep only recent history
        if len(self.price_ratio_history) > self.price_ratio_window:
            self.price_ratio_history = self.price_ratio_history[-self.price_ratio_window:]
        
        # Calculate arbitrage signals with stricter criteria
        if len(self.price_ratio_history) >= 10:
            ratio_mean = sum(self.price_ratio_history) / len(self.price_ratio_history)
            ratio_variance = sum((r - ratio_mean) ** 2 for r in self.price_ratio_history) / len(self.price_ratio_history)
            ratio_std = ratio_variance ** 0.5 if ratio_variance > 0 else 1
            
            if ratio_std > 0:
                z_score = (current_ratio - ratio_mean) / ratio_std
                
                # Stricter threshold: abs(z_score) > 2.5
                if abs(z_score) > self.arbitrage_threshold:
                    confidence = min(abs(z_score) / 4.0, 1.0)  # More conservative confidence
                    
                    # Additional safety checks
                    if self.validate_arbitrage_opportunity(z_score, state):
                        if z_score > 0:  # TOMATOES overvalued
                            opportunities.append({
                                'type': 'sell_tomatoes_buy_emeralds',
                                'confidence': confidence,
                                'z_score': z_score,
                                'timestamp': state.timestamp
                            })
                        else:  # TOMATOES undervalued
                            opportunities.append({
                                'type': 'buy_tomatoes_sell_emeralds',
                                'confidence': confidence,
                                'z_score': z_score,
                                'timestamp': state.timestamp
                            })
        
        return opportunities
    
    def check_arbitrage_spread_conditions(self, product: str, state: TradingState) -> bool:
        """Check if spread conditions are suitable for arbitrage"""
        if product not in state.order_depths:
            return False
        
        order_depth = state.order_depths[product]
        best_bid = self.get_best_bid(order_depth)
        best_ask = self.get_best_ask(order_depth)
        
        if best_bid is None or best_ask is None:
            return False
        
        spread = best_ask - best_bid
        
        # Check if spread is small enough for arbitrage
        if spread > self.max_arbitrage_spread:
            return False
        
        # Check minimum liquidity
        bid_liquidity = self.get_liquidity_at_level(order_depth, best_bid, True)
        ask_liquidity = self.get_liquidity_at_level(order_depth, best_ask, False)
        
        if bid_liquidity < self.min_arbitrage_liquidity or ask_liquidity < self.min_arbitrage_liquidity:
            return False
        
        return True
    
    def validate_arbitrage_opportunity(self, z_score: float, state: TradingState) -> bool:
        """Additional validation for arbitrage opportunities"""
        # Check if we have enough time for both legs to execute
        if state.timestamp - self.last_arbitrage_timestamp < self.arbitrage_execution_timeout:
            return False
        
        # Check position balance constraints
        current_emerald_pos = state.position.get('EMERALDS', 0)
        current_tomato_pos = state.position.get('TOMATOES', 0)
        
        # Ensure we don't exceed position limits with arbitrage
        emerald_limit = self.position_limits['EMERALDS']
        tomato_limit = self.position_limits['TOMATOES']
        
        if abs(current_emerald_pos) > emerald_limit * 0.8 or abs(current_tomato_pos) > tomato_limit * 0.8:
            return False
        
        return True
    
    def execute_safer_arbitrage(self, opportunities: List[Dict], state: TradingState) -> Dict[str, List[Order]]:
        """Execute arbitrage with both legs execution guarantee and position balancing"""
        arbitrage_orders = {product: [] for product in self.position_limits}
        
        if not opportunities:
            return arbitrage_orders
        
        # Process each opportunity with safety checks
        for opportunity in opportunities:
            opportunity_type = opportunity['type']
            z_score = opportunity['z_score']
            confidence = opportunity['confidence']
            
            # Only execute if both legs can be executed safely
            if self.can_execute_both_legs(opportunity_type, state, confidence):
                # Generate balanced orders for both legs
                leg_orders = self.generate_balanced_arbitrage_legs(opportunity, state)
                
                # Add orders to result
                for product, orders in leg_orders.items():
                    if orders:  # Only add if we have valid orders
                        arbitrage_orders[product].extend(orders)
                        
                        # Track arbitrage execution
                        self.last_arbitrage_timestamp = state.timestamp
                        
                        # Update position balances
                        for order in orders:
                            self.arbitrage_position_balances[product] += order.quantity
        
        return arbitrage_orders
    
    def can_execute_both_legs(self, opportunity_type: str, state: TradingState, confidence: float) -> bool:
        """Check if both legs of arbitrage can be executed safely"""
        # Check position limits for both products
        emerald_position = state.position.get('EMERALDS', 0)
        tomato_position = state.position.get('TOMATOES', 0)
        
        emerald_limit = self.position_limits['EMERALDS']
        tomato_limit = self.position_limits['TOMATOES']
        
        # Calculate required position sizes
        base_size = int(self.arbitrage_position_size * confidence)
        emerald_size = int(base_size * self.hedge_ratio)
        tomato_size = base_size
        
        # Check if we have capacity for both legs
        if opportunity_type == 'sell_tomatoes_buy_emeralds':
            # Sell TOMATOES, buy EMERALDS
            if (abs(emerald_position + emerald_size) > emerald_limit or 
                abs(tomato_position - tomato_size) > tomato_limit):
                return False
        else:  # buy_tomatoes_sell_emeralds
            # Buy TOMATOES, sell EMERALDS
            if (abs(emerald_position - emerald_size) > emerald_limit or 
                abs(tomato_position + tomato_size) > tomato_limit):
                return False
        
        # Check liquidity for both legs
        emerald_liquidity_ok = self.check_arbitrage_spread_conditions('EMERALDS', state)
        tomato_liquidity_ok = self.check_arbitrage_spread_conditions('TOMATOES', state)
        
        return emerald_liquidity_ok and tomato_liquidity_ok
    
    def generate_balanced_arbitrage_legs(self, opportunity: Dict, state: TradingState) -> Dict[str, List[Order]]:
        """Generate balanced arbitrage orders for both legs"""
        leg_orders = {'EMERALDS': [], 'TOMATOES': []}
        
        opportunity_type = opportunity['type']
        confidence = opportunity['confidence']
        base_size = int(self.arbitrage_position_size * confidence)
        
        if opportunity_type == 'sell_tomatoes_buy_emeralds':
            # Generate TOMATOES sell orders
            tomato_orders = self.generate_single_arbitrage_leg('TOMATOES', 'sell', base_size, state)
            if tomato_orders:
                leg_orders['TOMATOES'] = tomato_orders
            
            # Generate EMERALDS buy orders
            emerald_size = int(base_size * self.hedge_ratio)
            emerald_orders = self.generate_single_arbitrage_leg('EMERALDS', 'buy', emerald_size, state)
            if emerald_orders:
                leg_orders['EMERALDS'] = emerald_orders
                
        elif opportunity_type == 'buy_tomatoes_sell_emeralds':
            # Generate TOMATOES buy orders
            tomato_size = int(base_size * self.hedge_ratio)
            tomato_orders = self.generate_single_arbitrage_leg('TOMATOES', 'buy', tomato_size, state)
            if tomato_orders:
                leg_orders['TOMATOES'] = tomato_orders
            
            # Generate EMERALDS sell orders
            emerald_orders = self.generate_single_arbitrage_leg('EMERALDS', 'sell', base_size, state)
            if emerald_orders:
                leg_orders['EMERALDS'] = emerald_orders
        
        return leg_orders
    
    def generate_single_arbitrage_leg(self, product: str, side: str, size: int, state: TradingState) -> List[Order]:
        """Generate orders for a single arbitrage leg with safety checks"""
        orders = []
        
        if product not in state.order_depths:
            return orders
        
        order_depth = state.order_depths[product]
        current_position = state.position.get(product, 0)
        position_limit = self.position_limits[product]
        
        # Check position capacity
        if side == 'buy':
            available_capacity = position_limit - current_position
            actual_size = min(size, available_capacity)
        else:  # sell
            available_capacity = position_limit + current_position
            actual_size = min(size, available_capacity)
        
        if actual_size <= 0:
            return orders
        
        # Calculate safe price
        fair_price = self.calculate_fair_price(product, order_depth)
        best_bid = self.get_best_bid(order_depth)
        best_ask = self.get_best_ask(order_depth)
        
        if fair_price is None or best_bid is None or best_ask is None:
            return orders
        
        # Check edge conditions
        edge_info = self.check_edge_conditions(product, order_depth, fair_price)
        
        # Skip if edge conditions are severe
        if edge_info['should_reduce_position'] and edge_info.get('buy_liquidity_score', 1.0) < 0.3:
            return orders
        
        # Generate order with safe pricing
        if side == 'buy':
            price = self.calculate_safe_arbitrage_buy_price(product, order_depth, fair_price, edge_info)
            if price is not None and price <= best_ask - 1:  # Ensure we don't cross spread
                orders.append(Order(product, price, actual_size))
        else:  # sell
            price = self.calculate_safe_arbitrage_sell_price(product, order_depth, fair_price, edge_info)
            if price is not None and price >= best_bid + 1:  # Ensure we don't cross spread
                orders.append(Order(product, price, -actual_size))
        
        return orders
    
    def calculate_safe_arbitrage_buy_price(self, product: str, order_depth, fair_price: int, edge_info: Dict) -> int:
        """Calculate safe buy price for arbitrage"""
        best_bid = self.get_best_bid(order_depth)
        best_ask = self.get_best_ask(order_depth)
        
        if best_bid is None or best_ask is None:
            return None
        
        spread = best_ask - best_bid
        adjusted_fair_price = fair_price + edge_info['price_adjustment']
        
        # Conservative pricing for arbitrage - stay on bid side
        if adjusted_fair_price > best_bid:
            max_price = min(adjusted_fair_price, best_bid + max(1, spread // 3))
            return min(max_price, best_ask - 1)
        else:
            return best_bid
    
    def calculate_safe_arbitrage_sell_price(self, product: str, order_depth, fair_price: int, edge_info: Dict) -> int:
        """Calculate safe sell price for arbitrage"""
        best_bid = self.get_best_bid(order_depth)
        best_ask = self.get_best_ask(order_depth)
        
        if best_bid is None or best_ask is None:
            return None
        
        spread = best_ask - best_bid
        adjusted_fair_price = fair_price + edge_info['price_adjustment']
        
        # Conservative pricing for arbitrage - stay on ask side
        if adjusted_fair_price < best_ask:
            min_price = max(adjusted_fair_price, best_ask - max(1, spread // 3))
            return max(min_price, best_bid + 1)
        else:
            return best_ask
    
    def update_arbitrage_tracking(self, state: TradingState):
        """Update arbitrage tracking variables"""
        # Clean up old pending arbitrage legs
        current_timestamp = state.timestamp
        expired_legs = []
        
        for leg_id, leg_info in self.pending_arbitrage_legs.items():
            if current_timestamp - leg_info['timestamp'] > self.arbitrage_execution_timeout * 2:
                expired_legs.append(leg_id)
        
        for leg_id in expired_legs:
            del self.pending_arbitrage_legs[leg_id]
        
        # Update position balances based on current positions
        for product in self.position_limits:
            current_pos = state.position.get(product, 0)
            self.arbitrage_position_balances[product] = current_pos
    
    def generate_arbitrage_orders(self, product: str, opportunity: Dict, state: TradingState) -> List[Order]:
        """Generate arbitrage orders for cross-product opportunities"""
        orders = []
        
        if not self.cross_product_arbitrage_enabled:
            return orders
        
        current_position = state.position.get(product, 0)
        position_limit = self.position_limits[product]
        
        opportunity_type = opportunity['type']
        confidence = opportunity['confidence']
        base_size = int(self.arbitrage_position_size * confidence)
        
        if opportunity_type == 'sell_tomatoes_buy_emeralds':
            if product == 'TOMATOES':
                # Sell TOMATOES - with edge threshold protection
                available_sell_capacity = position_limit + current_position
                sell_size = min(base_size, available_sell_capacity)
                if sell_size > 0:
                    order_depth = state.order_depths[product]
                    fair_price = self.calculate_fair_price(product, order_depth)
                    best_bid = self.get_best_bid(order_depth)
                    best_ask = self.get_best_ask(order_depth)
                    
                    if fair_price is not None and best_bid is not None and best_ask is not None:
                        # Check edge conditions
                        edge_info = self.check_edge_conditions(product, order_depth, fair_price)
                        
                        # Apply edge threshold penalty
                        if edge_info['should_reduce_position']:
                            sell_size = int(sell_size * self.poor_liquidity_penalty)
                        
                        # Skip if edge conditions are severe
                        if edge_info['is_edge_sell'] and edge_info['sell_liquidity_score'] < 0.3:
                            return orders
                        
                        spread = best_ask - best_bid
                        adjusted_fair_price = fair_price + edge_info['price_adjustment']
                        
                        # Get safe price levels
                        safe_levels = self.get_safe_price_levels(order_depth, fair_price)
                        
                        # Never cross spread in arbitrage - stay on ask side
                        if adjusted_fair_price < best_ask:
                            if edge_info['is_edge_sell'] and safe_levels['sell_levels']:
                                # Use safe level in edge conditions
                                safe_price, _ = safe_levels['sell_levels'][0]
                                min_price = max(adjusted_fair_price, safe_price - max(1, spread // 3))
                                sell_price = max(min_price, best_bid + 1)
                            else:
                                # Normal pricing
                                min_price = max(adjusted_fair_price, best_ask - max(1, spread // 2))
                                sell_price = max(min_price, best_bid + 1)
                        else:
                            # Adjusted fair price is at or above best ask - place at best ask
                            sell_price = best_ask
                        
                        orders.append(Order(product, sell_price, -sell_size))
            
            elif product == 'EMERALDS':
                # Buy EMERALDS with hedge ratio - with edge threshold protection
                available_buy_capacity = position_limit - current_position
                buy_size = min(int(base_size * self.hedge_ratio), available_buy_capacity)
                if buy_size > 0:
                    order_depth = state.order_depths[product]
                    fair_price = self.calculate_fair_price(product, order_depth)
                    best_bid = self.get_best_bid(order_depth)
                    best_ask = self.get_best_ask(order_depth)
                    
                    if fair_price is not None and best_bid is not None and best_ask is not None:
                        # Check edge conditions
                        edge_info = self.check_edge_conditions(product, order_depth, fair_price)
                        
                        # Apply edge threshold penalty
                        if edge_info['should_reduce_position']:
                            buy_size = int(buy_size * self.poor_liquidity_penalty)
                        
                        # Skip if edge conditions are severe
                        if edge_info['is_edge_buy'] and edge_info['buy_liquidity_score'] < 0.3:
                            return orders
                        
                        spread = best_ask - best_bid
                        adjusted_fair_price = fair_price + edge_info['price_adjustment']
                        
                        # Get safe price levels
                        safe_levels = self.get_safe_price_levels(order_depth, fair_price)
                        
                        # Never cross spread in arbitrage - stay on bid side
                        if adjusted_fair_price > best_bid:
                            if edge_info['is_edge_buy'] and safe_levels['buy_levels']:
                                # Use safe level in edge conditions
                                safe_price, _ = safe_levels['buy_levels'][0]
                                max_price = min(adjusted_fair_price, safe_price + max(1, spread // 3))
                                buy_price = min(max_price, best_ask - 1)
                            else:
                                # Normal pricing
                                max_price = min(adjusted_fair_price, best_bid + max(1, spread // 2))
                                buy_price = min(max_price, best_ask - 1)
                        else:
                            # Adjusted fair price is at or below best bid - place at best bid
                            buy_price = best_bid
                        
                        orders.append(Order(product, buy_price, buy_size))
        
        elif opportunity_type == 'buy_tomatoes_sell_emeralds':
            if product == 'TOMATOES':
                # Buy TOMATOES with hedge ratio - with edge threshold protection
                available_buy_capacity = position_limit - current_position
                buy_size = min(int(base_size * self.hedge_ratio), available_buy_capacity)
                if buy_size > 0:
                    order_depth = state.order_depths[product]
                    fair_price = self.calculate_fair_price(product, order_depth)
                    best_bid = self.get_best_bid(order_depth)
                    best_ask = self.get_best_ask(order_depth)
                    
                    if fair_price is not None and best_bid is not None and best_ask is not None:
                        # Check edge conditions
                        edge_info = self.check_edge_conditions(product, order_depth, fair_price)
                        
                        # Apply edge threshold penalty
                        if edge_info['should_reduce_position']:
                            buy_size = int(buy_size * self.poor_liquidity_penalty)
                        
                        # Skip if edge conditions are severe
                        if edge_info['is_edge_buy'] and edge_info['buy_liquidity_score'] < 0.3:
                            return orders
                        
                        spread = best_ask - best_bid
                        adjusted_fair_price = fair_price + edge_info['price_adjustment']
                        
                        # Get safe price levels
                        safe_levels = self.get_safe_price_levels(order_depth, fair_price)
                        
                        # Never cross spread in arbitrage - stay on bid side
                        if adjusted_fair_price > best_bid:
                            if edge_info['is_edge_buy'] and safe_levels['buy_levels']:
                                # Use safe level in edge conditions
                                safe_price, _ = safe_levels['buy_levels'][0]
                                max_price = min(adjusted_fair_price, safe_price + max(1, spread // 3))
                                buy_price = min(max_price, best_ask - 1)
                            else:
                                # Normal pricing
                                max_price = min(adjusted_fair_price, best_bid + max(1, spread // 2))
                                buy_price = min(max_price, best_ask - 1)
                        else:
                            # Adjusted fair price is at or below best bid - place at best bid
                            buy_price = best_bid
                        
                        orders.append(Order(product, buy_price, buy_size))
            
            elif product == 'EMERALDS':
                # Sell EMERALDS - with edge threshold protection
                available_sell_capacity = position_limit + current_position
                sell_size = min(base_size, available_sell_capacity)
                if sell_size > 0:
                    order_depth = state.order_depths[product]
                    fair_price = self.calculate_fair_price(product, order_depth)
                    best_bid = self.get_best_bid(order_depth)
                    best_ask = self.get_best_ask(order_depth)
                    
                    if fair_price is not None and best_bid is not None and best_ask is not None:
                        # Check edge conditions
                        edge_info = self.check_edge_conditions(product, order_depth, fair_price)
                        
                        # Apply edge threshold penalty
                        if edge_info['should_reduce_position']:
                            sell_size = int(sell_size * self.poor_liquidity_penalty)
                        
                        # Skip if edge conditions are severe
                        if edge_info['is_edge_sell'] and edge_info['sell_liquidity_score'] < 0.3:
                            return orders
                        
                        spread = best_ask - best_bid
                        adjusted_fair_price = fair_price + edge_info['price_adjustment']
                        
                        # Get safe price levels
                        safe_levels = self.get_safe_price_levels(order_depth, fair_price)
                        
                        # Never cross spread in arbitrage - stay on ask side
                        if adjusted_fair_price < best_ask:
                            if edge_info['is_edge_sell'] and safe_levels['sell_levels']:
                                # Use safe level in edge conditions
                                safe_price, _ = safe_levels['sell_levels'][0]
                                min_price = max(adjusted_fair_price, safe_price - max(1, spread // 3))
                                sell_price = max(min_price, best_bid + 1)
                            else:
                                # Normal pricing
                                min_price = max(adjusted_fair_price, best_ask - max(1, spread // 2))
                                sell_price = max(min_price, best_bid + 1)
                        else:
                            # Adjusted fair price is at or above best ask - place at best ask
                            sell_price = best_ask
                        
                        orders.append(Order(product, sell_price, -sell_size))
        
        return orders

    def serialize_state(self, state: TradingState) -> str:
        """Serialize trading state for persistence"""
        try:
            # Store only essential data to stay within 50,000 character limit
            essential_data = {
                'price_history': self.price_history,
                'last_timestamp': state.timestamp
            }
            return json.dumps(essential_data)
        except:
            return ""
    
    def deserialize_state(self, trader_data: str):
        """Deserialize trading state from persistence"""
        try:
            if trader_data:
                data = json.loads(trader_data)
                if 'price_history' in data:
                    self.price_history = data['price_history']
        except:
            pass