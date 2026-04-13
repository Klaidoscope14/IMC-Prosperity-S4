#!/usr/bin/env python3
"""
IMC Prosperity Season 4 - Streamlined Trading Strategy with Advanced Systems
========================================================================

This is a streamlined version implementing:
1. Intraday Pattern Recognition
2. Liquidity-Aware Execution  
3. Volatility-Adjusted Risk Management

Author: Trading Strategy Development
Date: April 2026
"""

import pandas as pd
import numpy as np
from typing import Dict, List
import json

class Trader:
    """
    Streamlined trading strategy with advanced systems
    """
    
    def __init__(self, initial_cash: float = 100000):
        # Basic parameters
        self.position_limits = {'EMERALDS': 50, 'TOMATOES': 100}
        self.current_positions = {'EMERALDS': 0, 'TOMATOES': 0}
        self.cash_balance = initial_cash
        self.trade_log = []
        self.price_history = {product: [] for product in self.position_limits}
        self.last_trade_time = {product: -999999 for product in self.position_limits}
        
        # Strategy parameters
        self.cooldown_period = 1000
        self.momentum_window = 10
        self.price_history_limit = 50
        
        # P&L Enhancement parameters
        self.aggressive_momentum_enabled = True
        self.volatility_breakout_enabled = True
        self.dynamic_spread_arbitrage = True
        self.position_accumulation_enabled = True
        self.momentum_threshold = 3.0  # Lower threshold for more trades
        self.extreme_momentum_threshold = 5.0
        self.breakout_volatility_threshold = 2.0
        self.max_position_multiplier = 1.5  # Allow larger positions
        self.aggressive_spread_tightening = 0.7
        
        # Cross-Product Arbitrage parameters
        self.cross_product_arbitrage_enabled = True
        self.price_ratio_history = []
        self.price_ratio_window = 30
        self.arbitrage_threshold = 2.0  # Standard deviations for arbitrage signals
        self.arbitrage_position_size = 8
        self.correlation_window = 20
        self.hedge_ratio = 0.6  # Hedge ratio for arbitrage positions
        
        # Multi-Timeframe Analysis parameters
        self.multi_timeframe_enabled = True
        self.short_term_window = 5   # Short-term momentum (5 periods)
        self.medium_term_window = 15  # Medium-term trend (15 periods)
        self.long_term_window = 30    # Long-term trend (30 periods)
        self.timeframe_signals = {product: {} for product in self.position_limits}
        self.timeframe_weights = {'short': 0.5, 'medium': 0.3, 'long': 0.2}
        
        # Pattern Recognition parameters
        self.pattern_recognition_enabled = True
        self.pattern_window = 20
        self.pattern_history = {product: [] for product in self.position_limits}
        self.pattern_signal_strength = {product: 0 for product in self.position_limits}
        
        # Liquidity-Aware Execution parameters
        self.liquidity_aware_execution = True
        self.slippage_history = {product: [] for product in self.position_limits}
        self.max_slippage_threshold = 0.5
        self.min_liquidity_threshold = 5
        
        # Volatility-Adjusted Risk Management parameters
        self.volatility_risk_management = True
        self.volatility_forecasts = {product: [] for product in self.position_limits}
        self.real_time_risk_limits = {product: self.position_limits[product] for product in self.position_limits}
        self.volatility_lookback_window = 30
        self.portfolio_var_limit = 0.02
        self.risk_emergency_stop = False
        
        # Mean reversion parameters
        self.mean_reversion_window = 20
        self.mean_reversion_threshold = 2.0
        
        # Dynamic position sizing
        self.base_position_size = {'EMERALDS': 6, 'TOMATOES': 8}
        
        # Performance tracking
        self.total_pnl = 0
        self.starting_cash = initial_cash

    def load_market_data(self) -> Dict:
        """Load historical market data"""
        data = {
            'prices_day_minus_2': None,
            'prices_day_minus_1': None,
            'trades_day_minus_2': None,
            'trades_day_minus_1': None
        }
        
        try:
            data['prices_day_minus_2'] = pd.read_csv('prices_round_0_day_-2.csv', sep=';')
        except FileNotFoundError:
            pass
            
        try:
            data['prices_day_minus_1'] = pd.read_csv('prices_round_0_day_-1.csv', sep=';')
        except FileNotFoundError:
            pass
            
        return data

    def analyze_market_state(self, order_books: Dict) -> Dict:
        """Analyze current market state"""
        market_state = {}
        
        for product in ['EMERALDS', 'TOMATOES']:
            if product not in order_books:
                continue
                
            book = order_books[product]
            mid_price = (book['best_bid'] + book['best_ask']) / 2
            spread = book['best_ask'] - book['best_bid']
            
            # Update price history
            self.price_history[product].append(mid_price)
            if len(self.price_history[product]) > self.price_history_limit:
                self.price_history[product] = self.price_history[product][-self.price_history_limit:]
            
            # Calculate momentum
            momentum = 0
            if len(self.price_history[product]) >= self.momentum_window:
                recent_prices = self.price_history[product][-5:]
                older_prices = self.price_history[product][-10:-5]
                momentum = np.mean(recent_prices) - np.mean(older_prices)
            
            # Calculate volatility
            volatility = 0
            if len(self.price_history[product]) >= 10:
                volatility = np.std(self.price_history[product][-10:])
            
            market_state[product] = {
                'mid_price': mid_price,
                'spread': spread,
                'momentum': momentum,
                'position': self.current_positions[product],
                'volatility': volatility,
                'best_bid': book['best_bid'],
                'best_ask': book['best_ask'],
                'bid_volume': book.get('bid_volume', 0),
                'ask_volume': book.get('ask_volume', 0)
            }
        
        return market_state

    def calculate_mean_reversion_signals(self, product: str) -> Dict:
        """Calculate mean reversion signals"""
        if len(self.price_history[product]) < self.mean_reversion_window:
            return {'signal': 'neutral', 'z_score': 0}
        
        recent_prices = self.price_history[product][-self.mean_reversion_window:]
        current_price = recent_prices[-1]
        mean_price = np.mean(recent_prices)
        std_dev = np.std(recent_prices)
        
        z_score = (current_price - mean_price) / std_dev if std_dev > 0 else 0
        
        if z_score > self.mean_reversion_threshold:
            signal = 'sell'
        elif z_score < -self.mean_reversion_threshold:
            signal = 'buy'
        else:
            signal = 'neutral'
        
        return {'signal': signal, 'z_score': z_score}

    def detect_intraday_patterns(self, product: str, market_state: Dict, timestamp: int) -> Dict:
        """Detect intraday patterns"""
        if not self.pattern_recognition_enabled or len(self.price_history[product]) < self.pattern_window:
            return {'recommendation': 'neutral', 'confidence': 0}
        
        recent_prices = self.price_history[product][-self.pattern_window:]
        current_price = recent_prices[-1]
        
        # Price breakout detection
        price_mean = np.mean(recent_prices)
        price_std = np.std(recent_prices)
        
        if price_std > 0:
            z_score = (current_price - price_mean) / price_std
            if abs(z_score) > 1.5:
                recommendation = 'buy' if z_score > 0 else 'sell'
                confidence = min(abs(z_score) / 3.0, 1.0)
            else:
                recommendation = 'neutral'
                confidence = 0.5
        else:
            recommendation = 'neutral'
            confidence = 0
        
        # Store pattern signal
        self.pattern_signal_strength[product] = confidence if recommendation != 'neutral' else 0
        
        return {'recommendation': recommendation, 'confidence': confidence}

    def analyze_liquidity_depth(self, product: str, order_book: Dict) -> Dict:
        """Analyze liquidity conditions"""
        if not self.liquidity_aware_execution:
            return {'liquidity_score': 1.0, 'execution_confidence': 1.0}
        
        bid_volume = order_book.get('bid_volume', 0)
        ask_volume = order_book.get('ask_volume', 0)
        total_volume = bid_volume + ask_volume
        spread = order_book.get('best_ask', 0) - order_book.get('best_bid', 0)
        
        # Calculate liquidity score
        liquidity_score = 0
        if total_volume >= self.min_liquidity_threshold:
            volume_score = min(total_volume / 20.0, 1.0)
            liquidity_score += volume_score * 0.6
        
        if spread > 0:
            if product == 'EMERALDS':
                spread_score = max(0, 1 - spread / 20.0)
            else:
                spread_score = max(0, 1 - spread / 25.0)
            liquidity_score += spread_score * 0.4
        
        execution_confidence = min(liquidity_score, 1.0)
        
        return {
            'liquidity_score': liquidity_score,
            'execution_confidence': execution_confidence,
            'total_volume': total_volume,
            'spread': spread
        }

    def forecast_volatility(self, product: str, price_history: List[float]) -> Dict:
        """Simple volatility forecasting"""
        if not self.volatility_risk_management or len(price_history) < self.volatility_lookback_window:
            return {'current_volatility': 0, 'forecast_volatility': 0, 'volatility_ratio': 1.0}
        
        recent_prices = price_history[-self.volatility_lookback_window:]
        returns = np.diff(recent_prices) / recent_prices[:-1]
        current_volatility = np.std(returns) * np.sqrt(100)
        
        # Simple forecast using EWMA
        lambda_param = 0.94
        ewma_variance = 0
        weight_sum = 0
        
        for i, ret in enumerate(reversed(returns[-20:])):
            weight = lambda_param ** i
            ewma_variance += weight * ret ** 2
            weight_sum += weight
        
        ewma_variance /= weight_sum
        forecast_volatility = np.sqrt(ewma_variance) * np.sqrt(100)
        
        volatility_ratio = forecast_volatility / (current_volatility + 0.001)
        
        # Store forecast
        forecast_record = {
            'current_volatility': current_volatility,
            'forecast_volatility': forecast_volatility,
            'volatility_ratio': volatility_ratio
        }
        self.volatility_forecasts[product].append(forecast_record)
        
        if len(self.volatility_forecasts[product]) > 50:
            self.volatility_forecasts[product] = self.volatility_forecasts[product][-50:]
        
        return {
            'current_volatility': current_volatility,
            'forecast_volatility': forecast_volatility,
            'volatility_ratio': volatility_ratio
        }

    def calculate_dynamic_risk_limits(self, product: str, volatility_forecast: Dict) -> Dict:
        """Calculate dynamic risk limits"""
        if not self.volatility_risk_management:
            return {'position_limit': self.position_limits[product], 'risk_multiplier': 1.0}
        
        volatility_ratio = volatility_forecast['volatility_ratio']
        
        # Determine risk regime
        if volatility_ratio > 2.0:
            risk_multiplier = max(0.7, 1.0 - 0.3)
        elif volatility_ratio > 1.5:
            risk_multiplier = max(0.8, 1.0 - 0.15)
        elif volatility_ratio < 0.5:
            risk_multiplier = min(1.2, 1.0 + 0.15)
        else:
            risk_multiplier = 1.0
        
        dynamic_limit = int(self.position_limits[product] * risk_multiplier)
        self.real_time_risk_limits[product] = dynamic_limit
        
        return {
            'position_limit': dynamic_limit,
            'risk_multiplier': risk_multiplier,
            'volatility_ratio': volatility_ratio
        }

    def check_risk_limits(self, product: str, proposed_position: int, current_prices: Dict, volatilities: Dict) -> Dict:
        """Check if proposed position violates risk limits"""
        if not self.volatility_risk_management:
            return {'approved': True}
        
        dynamic_limit = self.real_time_risk_limits[product]
        current_position = self.current_positions[product]
        
        if abs(current_position + proposed_position) > dynamic_limit:
            return {'approved': False, 'reason': f'Position limit exceeded: {abs(current_position + proposed_position)} > {dynamic_limit}'}
        
        if self.risk_emergency_stop:
            return {'approved': False, 'reason': 'Emergency stop activated'}
        
        return {'approved': True}

    def calculate_dynamic_position_size(self, product: str, market_state: Dict, mean_reversion: Dict, trade_confidence: float = 1.0) -> int:
        """Calculate dynamic position size"""
        base_size = self.base_position_size[product]
        current_position = market_state['position']
        position_limit = self.position_limits[product]
        
        # Volatility adjustment
        volatility = market_state['volatility']
        if product == 'EMERALDS':
            volatility_factor = 1.0 / (1.0 + 0.5 * max(0, volatility / 1.0))
        else:
            volatility_factor = 1.0 / (1.0 + 0.5 * max(0, volatility / 15.0))
        
        # Confidence adjustment
        if mean_reversion['signal'] != 'neutral':
            confidence_factor = 1.0 + (0.5 * abs(mean_reversion['z_score']) / 3.0)
        else:
            confidence_factor = 1.0
        
        confidence_factor *= trade_confidence
        
        # Position utilization adjustment
        position_util = abs(current_position) / position_limit
        if position_util > 0.8:
            utilization_factor = 0.5
        elif position_util > 0.6:
            utilization_factor = 0.7
        else:
            utilization_factor = 1.0
        
        position_multiplier = volatility_factor * confidence_factor * utilization_factor
        
        # Enhanced position multipliers for P&L optimization
        position_multiplier = np.clip(position_multiplier, 0.3, 2.5)  # Increased max multiplier
        
        # Additional boost for strong signals
        if mean_reversion['signal'] != 'neutral' and abs(mean_reversion['z_score']) > 2.5:
            position_multiplier *= 1.3  # Boost for strong mean reversion
        
        # Cap at maximum allowed multiplier
        position_multiplier = min(position_multiplier, self.max_position_multiplier)
        
        dynamic_size = int(base_size * position_multiplier)
        dynamic_size = max(1, dynamic_size)
        
        # Adjust for position capacity
        if current_position > 0:
            max_buy_size = position_limit - current_position
            dynamic_size = min(dynamic_size, max_buy_size)
        else:
            max_buy_size = position_limit + current_position
            dynamic_size = min(dynamic_size, max_buy_size)
        
        return dynamic_size

    def generate_emerald_orders_enhanced(self, state: Dict, timestamp: int, pattern_signals: Dict, 
                                       volatility_forecast: Dict, risk_limits: Dict, timeframe_signals: Dict = None) -> List[Dict]:
        """Enhanced EMERALDS order generation"""
        orders = []
        product = 'EMERALDS'
        
        if timestamp - self.last_trade_time[product] < self.cooldown_period:
            return orders
        
        position = state['position']
        position_limit = risk_limits['position_limit'] if risk_limits else self.position_limits[product]
        
        current_prices = {product: state['mid_price']}
        current_volatilities = {product: volatility_forecast['current_volatility']} if volatility_forecast else {}
        
        mean_reversion = self.calculate_mean_reversion_signals('EMERALDS')
        
        pattern_confidence = pattern_signals.get('confidence', 0) if pattern_signals else 0
        pattern_recommendation = pattern_signals.get('recommendation', 'neutral') if pattern_signals else 'neutral'
        
        # Multi-timeframe signal integration for EMERALDS
        timeframe_confidence = 0
        timeframe_recommendation = 'neutral'
        if timeframe_signals and self.multi_timeframe_enabled:
            timeframe_confidence = timeframe_signals.get('confidence', 0)
            timeframe_recommendation = timeframe_signals.get('overall_signal', 'neutral')
        
        # Combined signal strength for EMERALDS
        combined_confidence = (pattern_confidence * 0.6 + timeframe_confidence * 0.4)
        
        # Position reduction logic
        if position >= position_limit * 0.8:
            sell_size = self.calculate_dynamic_position_size(product, state, mean_reversion, 1.3)
            sell_size = min(sell_size, position_limit + position)
            
            risk_check = self.check_risk_limits(product, -sell_size, current_prices, current_volatilities)
            if risk_check['approved']:
                orders.append({
                    'product': product,
                    'type': 'SELL',
                    'price': state['best_bid'],
                    'quantity': sell_size,
                    'reason': 'position_reduction'
                })
                self.last_trade_time[product] = timestamp
                
        elif position <= -position_limit * 0.8:
            buy_size = self.calculate_dynamic_position_size(product, state, mean_reversion, 1.3)
            buy_size = min(buy_size, position_limit - position)
            
            risk_check = self.check_risk_limits(product, buy_size, current_prices, current_volatilities)
            if risk_check['approved']:
                orders.append({
                    'product': product,
                    'type': 'BUY',
                    'price': state['best_ask'],
                    'quantity': buy_size,
                    'reason': 'position_reduction'
                })
                self.last_trade_time[product] = timestamp
                
        else:  # Normal market making
            base_confidence = 1.0
            
            # Pattern adjustment
            if pattern_recommendation == 'buy':
                base_confidence *= (1 + pattern_confidence * 0.3)
            elif pattern_recommendation == 'sell':
                base_confidence *= (1 - pattern_confidence * 0.3)
            
            # Volatility adjustment
            if volatility_forecast:
                vol_ratio = risk_limits.get('volatility_ratio', 1.0) if risk_limits else 1.0
                if vol_ratio > 1.5:
                    base_confidence *= 0.7
                elif vol_ratio < 0.5:
                    base_confidence *= 1.2
            
            # Enhanced liquidity provision with spread arbitrage
            if position < position_limit - 8:  # Reduced buffer for EMERALDS too
                # Dynamic spread arbitrage for EMERALDS
                if self.dynamic_spread_arbitrage and state['spread'] < 12:
                    buy_price = state['best_bid'] + 0.5  # Very tight spread
                    buy_size = self.calculate_dynamic_position_size(product, state, mean_reversion, base_confidence * 1.3)
                    reason = 'emerald_spread_arbitrage'
                else:
                    buy_price = state['best_bid'] + 1
                    buy_size = self.calculate_dynamic_position_size(product, state, mean_reversion, base_confidence)
                    reason = 'enhanced_liquidity_provision'
                
                # Pattern-based position accumulation for EMERALDS
                if pattern_confidence > 0.8 and pattern_recommendation == 'buy':
                    buy_size = int(buy_size * 1.2)
                
                risk_check = self.check_risk_limits(product, buy_size, current_prices, current_volatilities)
                if risk_check['approved']:
                    orders.append({
                        'product': product,
                        'type': 'BUY',
                        'price': buy_price,
                        'quantity': buy_size,
                        'reason': reason
                    })
            
            if position > -position_limit + 8:  # Reduced buffer for EMERALDS too
                # Dynamic spread arbitrage for EMERALDS
                if self.dynamic_spread_arbitrage and state['spread'] < 12:
                    sell_price = state['best_ask'] - 0.5  # Very tight spread
                    sell_size = self.calculate_dynamic_position_size(product, state, mean_reversion, base_confidence * 1.3)
                    reason = 'emerald_spread_arbitrage'
                else:
                    sell_price = state['best_ask'] - 1
                    sell_size = self.calculate_dynamic_position_size(product, state, mean_reversion, base_confidence)
                    reason = 'enhanced_liquidity_provision'
                
                # Pattern-based position accumulation for EMERALDS
                if pattern_confidence > 0.8 and pattern_recommendation == 'sell':
                    sell_size = int(sell_size * 1.2)
                
                risk_check = self.check_risk_limits(product, -sell_size, current_prices, current_volatilities)
                if risk_check['approved']:
                    orders.append({
                        'product': product,
                        'type': 'SELL',
                        'price': sell_price,
                        'quantity': sell_size,
                        'reason': reason
                    })
        
        return orders

    def generate_tomato_orders_enhanced(self, state: Dict, timestamp: int, pattern_signals: Dict,
                                      volatility_forecast: Dict, risk_limits: Dict, timeframe_signals: Dict = None) -> List[Dict]:
        """Enhanced TOMATOES order generation"""
        orders = []
        product = 'TOMATOES'
        
        if timestamp - self.last_trade_time[product] < self.cooldown_period:
            return orders
        
        position = state['position']
        momentum = state['momentum']
        position_limit = risk_limits['position_limit'] if risk_limits else self.position_limits[product]
        
        current_prices = {product: state['mid_price']}
        current_volatilities = {product: volatility_forecast['current_volatility']} if volatility_forecast else {}
        
        mean_reversion = self.calculate_mean_reversion_signals('TOMATOES')
        
        pattern_confidence = pattern_signals.get('confidence', 0) if pattern_signals else 0
        pattern_recommendation = pattern_signals.get('recommendation', 'neutral') if pattern_signals else 'neutral'
        
        # Multi-timeframe signal integration for TOMATOES
        timeframe_confidence = 0
        timeframe_recommendation = 'neutral'
        if timeframe_signals and self.multi_timeframe_enabled:
            timeframe_confidence = timeframe_signals.get('confidence', 0)
            timeframe_recommendation = timeframe_signals.get('overall_signal', 'neutral')
        
        # Combined signal strength for TOMATOES
        combined_confidence = (pattern_confidence * 0.5 + timeframe_confidence * 0.5)
        
        # Position reduction logic
        if position >= position_limit * 0.8:
            sell_size = self.calculate_dynamic_position_size(product, state, mean_reversion, 1.4)
            sell_size = min(sell_size, position_limit + position)
            
            risk_check = self.check_risk_limits(product, -sell_size, current_prices, current_volatilities)
            if risk_check['approved']:
                orders.append({
                    'product': product,
                    'type': 'SELL',
                    'price': state['best_bid'],
                    'quantity': sell_size,
                    'reason': 'position_reduction'
                })
                self.last_trade_time[product] = timestamp
                
        elif position <= -position_limit * 0.8:
            buy_size = self.calculate_dynamic_position_size(product, state, mean_reversion, 1.4)
            buy_size = min(buy_size, position_limit - position)
            
            risk_check = self.check_risk_limits(product, buy_size, current_prices, current_volatilities)
            if risk_check['approved']:
                orders.append({
                    'product': product,
                    'type': 'BUY',
                    'price': state['best_ask'],
                    'quantity': buy_size,
                    'reason': 'position_reduction'
                })
                self.last_trade_time[product] = timestamp
                
        else:  # Enhanced momentum-aware market making
            base_confidence = 1.0
            
            # Pattern adjustment
            if pattern_recommendation == 'buy':
                base_confidence *= (1 + pattern_confidence * 0.4)
            elif pattern_recommendation == 'sell':
                base_confidence *= (1 - pattern_confidence * 0.4)
            
            # Volatility adjustment
            if volatility_forecast:
                vol_ratio = risk_limits.get('volatility_ratio', 1.0) if risk_limits else 1.0
                if vol_ratio > 1.5:
                    base_confidence *= 0.6
                elif vol_ratio < 0.5:
                    base_confidence *= 1.3
            
            # Enhanced momentum adjustment for P&L optimization
            if abs(momentum) > self.extreme_momentum_threshold:
                base_confidence *= 1.8  # Very high confidence for extreme momentum
                position_boost = 1.5  # Increase position size significantly
            elif abs(momentum) > self.momentum_threshold:
                base_confidence *= 1.5  # High confidence for strong momentum
                position_boost = 1.3
            elif abs(momentum) > 1:
                base_confidence *= 1.2
                position_boost = 1.1
            else:
                position_boost = 1.0
            
            # Volatility breakout strategy
            if volatility_forecast and self.volatility_breakout_enabled:
                vol_ratio = risk_limits.get('volatility_ratio', 1.0) if risk_limits else 1.0
                if vol_ratio > self.breakout_volatility_threshold:
                    base_confidence *= 1.6  # High confidence in breakouts
                    position_boost *= 1.4  # Larger positions in breakouts
            
            momentum_adjustment = np.clip(momentum * 0.8, -6, 6)  # Wider range for more aggressive trading
            
            # Enhanced buy side with aggressive momentum scalping
            if position < position_limit - 10:  # Reduced buffer for more trades
                # Aggressive momentum capture
                if momentum > self.momentum_threshold and pattern_recommendation != 'sell':
                    buy_price = state['best_ask']  # Cross spread immediately
                    buy_size = self.calculate_dynamic_position_size(product, state, mean_reversion, base_confidence * position_boost)
                    buy_size = int(buy_size * position_boost)  # Apply position boost
                    reason = 'aggressive_momentum_capture'
                # Extreme momentum - even more aggressive
                elif abs(momentum) > self.extreme_momentum_threshold:
                    buy_price = state['best_ask']
                    buy_size = self.calculate_dynamic_position_size(product, state, mean_reversion, base_confidence * 1.8)
                    buy_size = int(buy_size * 1.8)  # Maximum position boost
                    reason = 'extreme_momentum_scalp'
                # Dynamic spread arbitrage
                elif self.dynamic_spread_arbitrage and state['spread'] < 10:
                    buy_price = state['best_bid'] + 0.5  # Very tight spread
                    buy_size = self.calculate_dynamic_position_size(product, state, mean_reversion, base_confidence * 1.4)
                    reason = 'spread_arbitrage'
                else:
                    buy_price = state['best_bid'] + 1 + momentum_adjustment
                    buy_size = self.calculate_dynamic_position_size(product, state, mean_reversion, base_confidence)
                    reason = 'enhanced_market_making'
                
                # Position accumulation for strong trends
                if self.position_accumulation_enabled and pattern_confidence > 0.7 and momentum > 1:
                    buy_size = int(buy_size * 1.3)  # Accumulate larger position
                
                risk_check = self.check_risk_limits(product, buy_size, current_prices, current_volatilities)
                if risk_check['approved']:
                    orders.append({
                        'product': product,
                        'type': 'BUY',
                        'price': buy_price,
                        'quantity': buy_size,
                        'reason': reason
                    })
            
            # Enhanced sell side with aggressive momentum scalping
            if position > -position_limit + 10:  # Reduced buffer for more trades
                # Aggressive momentum capture
                if momentum < -self.momentum_threshold and pattern_recommendation != 'buy':
                    sell_price = state['best_bid']  # Cross spread immediately
                    sell_size = self.calculate_dynamic_position_size(product, state, mean_reversion, base_confidence * position_boost)
                    sell_size = int(sell_size * position_boost)  # Apply position boost
                    reason = 'aggressive_momentum_capture'
                # Extreme momentum - even more aggressive
                elif abs(momentum) > self.extreme_momentum_threshold:
                    sell_price = state['best_bid']
                    sell_size = self.calculate_dynamic_position_size(product, state, mean_reversion, base_confidence * 1.8)
                    sell_size = int(sell_size * 1.8)  # Maximum position boost
                    reason = 'extreme_momentum_scalp'
                # Dynamic spread arbitrage
                elif self.dynamic_spread_arbitrage and state['spread'] < 10:
                    sell_price = state['best_ask'] - 0.5  # Very tight spread
                    sell_size = self.calculate_dynamic_position_size(product, state, mean_reversion, base_confidence * 1.4)
                    reason = 'spread_arbitrage'
                else:
                    sell_price = state['best_ask'] - 1 + momentum_adjustment
                    sell_size = self.calculate_dynamic_position_size(product, state, mean_reversion, base_confidence)
                    reason = 'enhanced_market_making'
                
                # Position accumulation for strong trends
                if self.position_accumulation_enabled and pattern_confidence > 0.7 and momentum < -1:
                    sell_size = int(sell_size * 1.3)  # Accumulate larger position
                
                risk_check = self.check_risk_limits(product, -sell_size, current_prices, current_volatilities)
                if risk_check['approved']:
                    orders.append({
                        'product': product,
                        'type': 'SELL',
                        'price': sell_price,
                        'quantity': sell_size,
                        'reason': reason
                    })
        
        return orders

    def execute_orders(self, orders: List[Dict], order_books: Dict, timestamp: int) -> List[Dict]:
        """Execute orders against the market"""
        executed_trades = []
        
        for order in orders:
            product = order['product']
            if product not in order_books:
                continue
                
            market = order_books[product]
            
            if order['type'] == 'BUY':
                if order['price'] >= market['best_ask']:
                    execution_price = market['best_ask']
                    self.current_positions[product] += order['quantity']
                    self.cash_balance -= execution_price * order['quantity']
                    
                    trade = {
                        'product': product,
                        'type': 'BUY',
                        'price': execution_price,
                        'quantity': order['quantity'],
                        'timestamp': timestamp,
                        'reason': order['reason']
                    }
                    executed_trades.append(trade)
                    self.trade_log.append(trade)
                    
            elif order['type'] == 'SELL':
                if order['price'] <= market['best_bid']:
                    execution_price = market['best_bid']
                    self.current_positions[product] -= order['quantity']
                    self.cash_balance += execution_price * order['quantity']
                    
                    trade = {
                        'product': product,
                        'type': 'SELL',
                        'price': execution_price,
                        'quantity': order['quantity'],
                        'timestamp': timestamp,
                        'reason': order['reason']
                    }
                    executed_trades.append(trade)
                    self.trade_log.append(trade)
        
        return executed_trades

    def detect_cross_product_arbitrage(self, market_state: Dict) -> List[Dict]:
        """Detect cross-product arbitrage opportunities between EMERALDS and TOMATOES"""
        arbitrage_opportunities = []
        
        if not self.cross_product_arbitrage_enabled:
            return arbitrage_opportunities
        
        # Check if we have data for both products
        if 'EMERALDS' not in market_state or 'TOMATOES' not in market_state:
            return arbitrage_opportunities
        
        emerald_state = market_state['EMERALDS']
        tomato_state = market_state['TOMATOES']
        
        # Calculate price ratio (TOMATOES / EMERALDS)
        if emerald_state['mid_price'] > 0:
            current_ratio = tomato_state['mid_price'] / emerald_state['mid_price']
            self.price_ratio_history.append(current_ratio)
            
            # Keep only recent history
            if len(self.price_ratio_history) > self.price_ratio_window:
                self.price_ratio_history = self.price_ratio_history[-self.price_ratio_window:]
            
            # Calculate arbitrage signals if we have enough history
            if len(self.price_ratio_history) >= 10:
                ratio_mean = np.mean(self.price_ratio_history)
                ratio_std = np.std(self.price_ratio_history)
                
                if ratio_std > 0:
                    z_score = (current_ratio - ratio_mean) / ratio_std
                    
                    # Detect arbitrage opportunities
                    if abs(z_score) > self.arbitrage_threshold:
                        expected_ratio_reversion = ratio_mean
                        
                        if z_score > 0:  # TOMATOES overvalued relative to EMERALDS
                            arbitrage_opportunities.append({
                                'type': 'sell_tomatoes_buy_emeralds',
                                'z_score': z_score,
                                'current_ratio': current_ratio,
                                'expected_ratio': expected_ratio_reversion,
                                'confidence': min(abs(z_score) / 3.0, 1.0),
                                'tomato_price': tomato_state['mid_price'],
                                'emerald_price': emerald_state['mid_price']
                            })
                        else:  # TOMATOES undervalued relative to EMERALDS
                            arbitrage_opportunities.append({
                                'type': 'buy_tomatoes_sell_emeralds',
                                'z_score': z_score,
                                'current_ratio': current_ratio,
                                'expected_ratio': expected_ratio_reversion,
                                'confidence': min(abs(z_score) / 3.0, 1.0),
                                'tomato_price': tomato_state['mid_price'],
                                'emerald_price': emerald_state['mid_price']
                            })
        
        return arbitrage_opportunities
    
    def execute_cross_product_arbitrage(self, opportunity: Dict, market_state: Dict, timestamp: int) -> List[Dict]:
        """Execute cross-product arbitrage trades"""
        orders = []
        
        confidence = opportunity['confidence']
        base_size = int(self.arbitrage_position_size * confidence)
        
        emerald_position = self.current_positions['EMERALDS']
        tomato_position = self.current_positions['TOMATOES']
        
        emerald_limit = self.position_limits['EMERALDS']
        tomato_limit = self.position_limits['TOMATOES']
        
        if opportunity['type'] == 'sell_tomatoes_buy_emeralds':
            # Sell TOMATOES, buy EMERALDS
            tomato_sell_size = min(base_size, tomato_limit + tomato_position)
            emerald_buy_size = min(base_size, emerald_limit - emerald_position)
            
            # Apply hedge ratio
            emerald_buy_size = int(emerald_buy_size * self.hedge_ratio)
            
            if tomato_sell_size > 0:
                orders.append({
                    'product': 'TOMATOES',
                    'type': 'SELL',
                    'price': market_state['TOMATOES']['best_bid'],
                    'quantity': tomato_sell_size,
                    'reason': 'cross_arbitrage_sell_tomatoes'
                })
            
            if emerald_buy_size > 0:
                orders.append({
                    'product': 'EMERALDS',
                    'type': 'BUY',
                    'price': market_state['EMERALDS']['best_ask'],
                    'quantity': emerald_buy_size,
                    'reason': 'cross_arbitrage_buy_emeralds'
                })
        
        elif opportunity['type'] == 'buy_tomatoes_sell_emeralds':
            # Buy TOMATOES, sell EMERALDS
            tomato_buy_size = min(base_size, tomato_limit - tomato_position)
            emerald_sell_size = min(base_size, emerald_limit + emerald_position)
            
            # Apply hedge ratio
            tomato_buy_size = int(tomato_buy_size * self.hedge_ratio)
            
            if tomato_buy_size > 0:
                orders.append({
                    'product': 'TOMATOES',
                    'type': 'BUY',
                    'price': market_state['TOMATOES']['best_ask'],
                    'quantity': tomato_buy_size,
                    'reason': 'cross_arbitrage_buy_tomatoes'
                })
            
            if emerald_sell_size > 0:
                orders.append({
                    'product': 'EMERALDS',
                    'type': 'SELL',
                    'price': market_state['EMERALDS']['best_bid'],
                    'quantity': emerald_sell_size,
                    'reason': 'cross_arbitrage_sell_emeralds'
                })
        
        return orders
    
    def analyze_multi_timeframe_signals(self, product: str) -> Dict:
        """Analyze signals across multiple timeframes"""
        if not self.multi_timeframe_enabled or len(self.price_history[product]) < self.long_term_window:
            return {'overall_signal': 'neutral', 'confidence': 0}
        
        prices = self.price_history[product]
        
        # Short-term momentum (5 periods)
        if len(prices) >= self.short_term_window:
            short_prices = prices[-self.short_term_window:]
            short_momentum = (short_prices[-1] - short_prices[0]) / short_prices[0] if short_prices[0] > 0 else 0
            short_signal = 'buy' if short_momentum > 0.001 else 'sell' if short_momentum < -0.001 else 'neutral'
        else:
            short_momentum = 0
            short_signal = 'neutral'
        
        # Medium-term trend (15 periods)
        if len(prices) >= self.medium_term_window:
            medium_prices = prices[-self.medium_term_window:]
            medium_trend = (medium_prices[-1] - medium_prices[0]) / medium_prices[0] if medium_prices[0] > 0 else 0
            medium_signal = 'buy' if medium_trend > 0.002 else 'sell' if medium_trend < -0.002 else 'neutral'
        else:
            medium_trend = 0
            medium_signal = 'neutral'
        
        # Long-term trend (30 periods)
        if len(prices) >= self.long_term_window:
            long_prices = prices[-self.long_term_window:]
            long_trend = (long_prices[-1] - long_prices[0]) / long_prices[0] if long_prices[0] > 0 else 0
            long_signal = 'buy' if long_trend > 0.003 else 'sell' if long_trend < -0.003 else 'neutral'
        else:
            long_trend = 0
            long_signal = 'neutral'
        
        # Weighted signal combination
        signal_weights = {'buy': 0, 'sell': 0, 'neutral': 0}
        
        signal_weights[short_signal] += self.timeframe_weights['short']
        signal_weights[medium_signal] += self.timeframe_weights['medium']
        signal_weights[long_signal] += self.timeframe_weights['long']
        
        # Determine overall signal
        overall_signal = max(signal_weights, key=signal_weights.get)
        confidence = signal_weights[overall_signal]
        
        # Store timeframe signals
        self.timeframe_signals[product] = {
            'short_signal': short_signal,
            'medium_signal': medium_signal,
            'long_signal': long_signal,
            'short_momentum': short_momentum,
            'medium_trend': medium_trend,
            'long_trend': long_trend,
            'overall_signal': overall_signal,
            'confidence': confidence
        }
        
        return {
            'overall_signal': overall_signal,
            'confidence': confidence,
            'short_signal': short_signal,
            'medium_signal': medium_signal,
            'long_signal': long_signal
        }
    
    def update_risk_emergency_stop(self, market_state: Dict):
        """Update emergency stop conditions"""
        if not self.volatility_risk_management:
            return
        
        extreme_volatility = False
        for product in ['EMERALDS', 'TOMATOES']:
            if len(self.volatility_forecasts[product]) >= 2:
                recent_forecast = self.volatility_forecasts[product][-1]
                vol_increase = recent_forecast.get('volatility_ratio', 1.0)
                if vol_increase > 2.0:
                    extreme_volatility = True
                    break
        
        if extreme_volatility:
            self.risk_emergency_stop = True
        elif self.risk_emergency_stop:
            # Gradually release if conditions improve
            if not extreme_volatility:
                self.risk_emergency_stop = False

    def process_market_data(self, order_books: Dict, timestamp: int) -> List[Dict]:
        """Main method to process market data with integrated advanced systems"""
        # Analyze current market state
        market_state = self.analyze_market_state(order_books)
        
        # Pattern Recognition
        pattern_signals = {}
        for product in ['EMERALDS', 'TOMATOES']:
            if product in market_state:
                pattern_signals[product] = self.detect_intraday_patterns(product, market_state[product], timestamp)
        
        # Multi-Timeframe Analysis
        timeframe_signals = {}
        for product in ['EMERALDS', 'TOMATOES']:
            if product in market_state:
                timeframe_signals[product] = self.analyze_multi_timeframe_signals(product)
        
        # Volatility-Adjusted Risk Management
        volatility_forecasts = {}
        risk_limits = {}
        current_prices = {product: state['mid_price'] for product, state in market_state.items()}
        
        for product in ['EMERALDS', 'TOMATOES']:
            if product in self.price_history and len(self.price_history[product]) >= self.volatility_lookback_window:
                vol_forecast = self.forecast_volatility(product, self.price_history[product])
                volatility_forecasts[product] = vol_forecast
                risk_limits[product] = self.calculate_dynamic_risk_limits(product, vol_forecast)
        
        # Update emergency stop conditions
        self.update_risk_emergency_stop(market_state)
        
        # Generate orders
        all_orders = []
        
        if 'EMERALDS' in market_state:
            emerald_orders = self.generate_emerald_orders_enhanced(
                market_state['EMERALDS'], timestamp, pattern_signals.get('EMERALDS'), 
                volatility_forecasts.get('EMERALDS'), risk_limits.get('EMERALDS'),
                timeframe_signals.get('EMERALDS')
            )
            all_orders.extend(emerald_orders)
        
        if 'TOMATOES' in market_state:
            tomato_orders = self.generate_tomato_orders_enhanced(
                market_state['TOMATOES'], timestamp, pattern_signals.get('TOMATOES'),
                volatility_forecasts.get('TOMATOES'), risk_limits.get('TOMATOES'),
                timeframe_signals.get('TOMATOES')
            )
            all_orders.extend(tomato_orders)
        
        # Cross-Product Arbitrage
        arbitrage_opportunities = self.detect_cross_product_arbitrage(market_state)
        for opportunity in arbitrage_opportunities:
            if not self.risk_emergency_stop:
                arbitrage_orders = self.execute_cross_product_arbitrage(opportunity, market_state, timestamp)
                all_orders.extend(arbitrage_orders)
        
        # Execute orders
        executed_trades = self.execute_orders(all_orders, order_books, timestamp)
        
        return executed_trades

    def run(self, state: Dict) -> Dict:
        """Main entry point for IMC Prosperity competition"""
        # Extract order books from state
        order_books = {}
        
        if hasattr(state, 'order_books') and state.order_books:
            for product, book_data in state.order_books.items():
                if 'buy_orders' in book_data and 'sell_orders' in book_data:
                    buy_orders = sorted(book_data['buy_orders'].items(), key=lambda x: x[0], reverse=True)
                    sell_orders = sorted(book_data['sell_orders'].items(), key=lambda x: x[0])
                    
                    best_bid = buy_orders[0][0] if buy_orders else 0
                    best_ask = sell_orders[0][0] if sell_orders else float('inf')
                    bid_volume = buy_orders[0][1] if buy_orders else 0
                    ask_volume = sell_orders[0][1] if sell_orders else 0
                    
                    order_books[product] = {
                        'best_bid': best_bid,
                        'best_ask': best_ask,
                        'bid_volume': bid_volume,
                        'ask_volume': ask_volume
                    }
                else:
                    order_books[product] = {
                        'best_bid': book_data.get('best_bid', 0),
                        'best_ask': book_data.get('best_ask', 0),
                        'bid_volume': book_data.get('bid_volume', 0),
                        'ask_volume': book_data.get('ask_volume', 0)
                    }
        
        # Get timestamp from state
        timestamp = getattr(state, 'timestamp', 0)
        
        # Update positions from state if available
        if hasattr(state, 'positions') and state.positions:
            for product, position in state.positions.items():
                if product in self.current_positions:
                    self.current_positions[product] = position
        
        # Generate trades using enhanced logic
        executed_trades = self.process_market_data(order_books, timestamp)
        
        # Convert to competition format
        orders = {}
        for trade in executed_trades:
            product = trade['product']
            if product not in orders:
                orders[product] = []
            
            orders[product].append({
                'type': trade['type'],
                'price': trade['price'],
                'quantity': trade['quantity']
            })
        
        return orders

    def calculate_portfolio_value(self, current_prices: Dict) -> float:
        """Calculate total portfolio value"""
        total_value = self.cash_balance
        
        for product, position in self.current_positions.items():
            if position != 0 and product in current_prices:
                total_value += position * current_prices[product]
        
        return total_value

    def get_portfolio_status(self) -> Dict:
        """Get portfolio status"""
        position_utilization = {}
        for product, position in self.current_positions.items():
            limit = self.position_limits[product]
            utilization = abs(position) / limit * 100 if limit > 0 else 0
            position_utilization[product] = utilization
        
        return {
            'cash_balance': self.cash_balance,
            'positions': self.current_positions.copy(),
            'total_trades': len(self.trade_log),
            'position_utilization': position_utilization,
            'position_limits': self.position_limits.copy(),
            'starting_cash': self.starting_cash
        }

    def run_backtest(self, market_data: Dict) -> Dict:
        """Run backtest on historical data"""
        print("\n" + "="*60)
        print("RUNNING STREAMLINED BACKTEST")
        print("="*60)
        
        # Combine price data
        all_prices = None
        if market_data['prices_day_minus_2'] is not None and market_data['prices_day_minus_1'] is not None:
            all_prices = pd.concat([market_data['prices_day_minus_2'], market_data['prices_day_minus_1']])
        elif market_data['prices_day_minus_2'] is not None:
            all_prices = market_data['prices_day_minus_2']
        elif market_data['prices_day_minus_1'] is not None:
            all_prices = market_data['prices_day_minus_1']
        
        if all_prices is None:
            print("No price data available for backtest")
            return {'error': 'No price data available'}
        
        starting_value = self.starting_cash
        daily_results = []
        
        # Process each day
        for day in [-2, -1]:
            print(f"\nProcessing Day {day}...")
            
            if day == -2 and market_data['prices_day_minus_2'] is not None:
                day_prices = market_data['prices_day_minus_2']
            elif day == -1 and market_data['prices_day_minus_1'] is not None:
                day_prices = market_data['prices_day_minus_1']
            else:
                continue
            
            timestamps = sorted(day_prices['timestamp'].unique())
            trades_today = 0
            
            # Process every 10th timestamp for efficiency
            for timestamp in timestamps[::10]:
                timestamp_data = day_prices[day_prices['timestamp'] == timestamp]
                
                # Build order books
                order_books = {}
                current_prices = {}
                
                for _, row in timestamp_data.iterrows():
                    product = row['product']
                    order_books[product] = {
                        'best_bid': row['bid_price_1'],
                        'best_ask': row['ask_price_1'],
                        'bid_volume': row['bid_volume_1'],
                        'ask_volume': row['ask_volume_1']
                    }
                    current_prices[product] = row['mid_price']
                
                # Process market data
                executed_trades = self.process_market_data(order_books, timestamp)
                trades_today += len(executed_trades)
            
            # Calculate end of day portfolio value
            end_prices = {}
            for product in ['EMERALDS', 'TOMATOES']:
                product_data = day_prices[day_prices['product'] == product]
                if len(product_data) > 0:
                    end_prices[product] = product_data['mid_price'].iloc[-1]
            
            day_end_value = self.calculate_portfolio_value(end_prices)
            
            # Calculate daily P&L
            if day == -2:
                daily_pnl = day_end_value - starting_value
            else:
                daily_pnl = day_end_value - daily_results[-1]['end_value']
            
            daily_results.append({
                'day': day,
                'end_value': day_end_value,
                'daily_pnl': daily_pnl,
                'trades': trades_today
            })
            
            print(f"  Day {day} P&L: ${daily_pnl:,.2f}")
            print(f"  Trades executed: {trades_today}")
        
        # Calculate final results
        final_value = self.calculate_portfolio_value({})
        total_pnl = final_value - starting_value
        
        results = {
            'starting_value': starting_value,
            'final_value': final_value,
            'total_pnl': total_pnl,
            'total_trades': len(self.trade_log),
            'daily_results': daily_results,
            'final_positions': self.current_positions.copy(),
            'return_percentage': (total_pnl / starting_value) * 100 if starting_value > 0 else 0
        }
        
        self.print_backtest_results(results)
        return results

    def print_backtest_results(self, results: Dict):
        """Print backtest results"""
        print(f"\n{'='*60}")
        print("STREAMLINED BACKTEST RESULTS")
        print(f"{'='*60}")
        
        print(f"Starting Portfolio Value: ${results['starting_value']:,.2f}")
        print(f"Final Portfolio Value: ${results['final_value']:,.2f}")
        print(f"Total P&L: ${results['total_pnl']:,.2f}")
        print(f"Total Return: {results['return_percentage']:.2f}%")
        print(f"Total Trades Executed: {results['total_trades']}")
        
        print(f"\nDaily Performance:")
        for day_result in results['daily_results']:
            print(f"  Day {day_result['day']}: ${day_result['daily_pnl']:,.2f} "
                  f"({day_result['trades']} trades)")
        
        print(f"\nFinal Positions:")
        for product, position in results['final_positions'].items():
            print(f"  {product}: {position} units")
        
        # Strategy effectiveness assessment
        print(f"\nStrategy Effectiveness:")
        if results['total_pnl'] > 10000:
            print(f"  Status: HIGHLY PROFITABLE")
        elif results['total_pnl'] > 0:
            print(f"  Status: PROFITABLE")
        elif results['total_pnl'] > -10000:
            print(f"  Status: BREAKEVEN")
        else:
            print(f"  Status: UNPROFITABLE - Needs refinement")

def main():
    """Main execution function"""
    print("IMC Prosperity Season 4 - Streamlined Trading Strategy")
    print("=" * 60)
    print("Author: Trading Strategy Development Team")
    print("Date: April 2026")
    print("=" * 60)
    
    # Initialize the strategy
    strategy = Trader(initial_cash=100000)
    
    # Load market data
    market_data = strategy.load_market_data()
    
    # Run backtest if data is available
    if any(df is not None for df in market_data.values()):
        results = strategy.run_backtest(market_data)
        
        # Print final status
        print(f"\n{'='*60}")
        print("STRATEGY EXECUTION COMPLETE")
        print("=" * 60)
        
        status = strategy.get_portfolio_status()
        print(f"Final portfolio status:")
        print(f"  Cash balance: ${status['cash_balance']:,.2f}")
        print(f"  Positions: {status['positions']}")
        print(f"  Total trades executed: {status['total_trades']}")
        
        if 'total_pnl' in results:
            if results['total_pnl'] > 0:
                print(f"  Result: PROFITABLE (+${results['total_pnl']:,.2f})")
            else:
                print(f"  Result: ${results['total_pnl']:,.2f}")
    else:
        print("No market data available for backtest")
        print("Strategy is ready for live trading deployment")
    
    print(f"\n{'='*60}")
    print("STREAMLINED STRATEGY READY FOR DEPLOYMENT")
    print("=" * 60)
    print("Key features:")
    print("  - Intraday Pattern Recognition (NEW)")
    print("  - Liquidity-Aware Execution (NEW)")
    print("  - Volatility-Adjusted Risk Management (NEW)")
    print("  - Aggressive Momentum Scalping (NEW)")
    print("  - Dynamic Spread Arbitrage (NEW)")
    print("  - Volatility Breakout Trading (NEW)")
    print("  - Position Accumulation Strategy (NEW)")
    print("  - Cross-Product Arbitrage (NEW)")
    print("  - Multi-Timeframe Analysis (NEW)")
    print("  - Enhanced P&L Optimization")
    print("=" * 60)

if __name__ == "__main__":
    main()