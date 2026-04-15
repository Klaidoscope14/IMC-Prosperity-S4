#!/usr/bin/env python3
"""
Data-Driven Parameter Optimization for IMC Prosperity ACO Strategy
=================================================================

This script analyzes Round1 historical price data to find mathematically optimal parameters:
- EMA alpha values (0.05 to 0.50)
- Anchor price (around 10,000)
- Anchor weight (around 0.50)

Instead of guessing parameters, we let the Round1 data speak for itself.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

class ACOParameterOptimizer:
    """Optimizes ACO strategy parameters using Round1 historical data."""
    
    def __init__(self):
        self.data_files = [
            "Round1/prices_round_1_day_-2.csv",
            "Round1/prices_round_1_day_-1.csv",
            "Round1/prices_round_1_day_0.csv"
        ]
        self.aco_data = []
        
    def load_data(self) -> None:
        """Load Round1 historical price data for ASH_COATED_OSMIUM."""
        base_path = Path("/Users/chaitanyasaagar/Desktop/IMC Prosperity")
        
        for file_path in self.data_files:
            full_path = base_path / file_path
            if full_path.exists():
                print(f"Loading: {file_path}")
                df = pd.read_csv(full_path, sep=';')
                
                # Filter for ASH_COATED_OSMIUM and clean data
                aco_df = df[df['product'] == 'ASH_COATED_OSMIUM'].copy()
                
                # Convert to numeric and handle missing values
                price_cols = ['mid_price', 'bid_price_1', 'ask_price_1']
                for col in price_cols:
                    if col in aco_df.columns:
                        aco_df[col] = pd.to_numeric(aco_df[col], errors='coerce')
                
                # Drop rows with missing mid_price
                aco_df = aco_df.dropna(subset=['mid_price'])
                
                # Sort by timestamp
                aco_df = aco_df.sort_values('timestamp').reset_index(drop=True)
                
                self.aco_data.append(aco_df)
                print(f"  Loaded {len(aco_df)} data points")
        
        print(f"\nTotal Round1 datasets: {len(self.aco_data)}")
        
    def calculate_ema(self, prices: np.ndarray, alpha: float) -> np.ndarray:
        """Calculate EMA with given alpha."""
        ema = np.zeros_like(prices)
        ema[0] = prices[0]  # Start with first price
        
        for i in range(1, len(prices)):
            ema[i] = alpha * prices[i] + (1 - alpha) * ema[i-1]
        
        return ema
    
    def calculate_fv(self, ema: np.ndarray, anchor: float, anchor_weight: float) -> np.ndarray:
        """Calculate fair value: FV = anchor_weight * anchor + (1-anchor_weight) * EMA."""
        return anchor_weight * anchor + (1 - anchor_weight) * ema
    
    def evaluate_parameters(self, alpha: float, anchor: float, anchor_weight: float, 
                           forward_ticks: int = 5) -> Dict[str, float]:
        """
        Evaluate parameter combination by measuring prediction accuracy.
        
        Returns metrics including RMSE, MAE, and directional accuracy.
        """
        all_errors = []
        all_directional_correct = 0
        all_directional_total = 0
        
        for dataset in self.aco_data:
            if len(dataset) < forward_ticks + 10:  # Need enough data
                continue
                
            prices = dataset['mid_price'].values
            
            # Calculate EMA and FV
            ema = self.calculate_ema(prices, alpha)
            fv = self.calculate_fv(ema, anchor, anchor_weight)
            
            # Calculate forward-looking errors
            for i in range(len(prices) - forward_ticks):
                current_fv = fv[i]
                future_price = prices[i + forward_ticks]
                
                error = current_fv - future_price
                all_errors.append(error)
                
                # Directional accuracy
                if i > 0:  # Need previous price for direction
                    prev_price = prices[i-1]
                    actual_direction = 1 if future_price > prev_price else -1
                    predicted_direction = 1 if current_fv > prev_price else -1
                    
                    if actual_direction == predicted_direction:
                        all_directional_correct += 1
                    all_directional_total += 1
        
        if not all_errors:
            return {'rmse': float('inf'), 'mae': float('inf'), 'directional_acc': 0}
        
        errors = np.array(all_errors)
        rmse = np.sqrt(np.mean(errors**2))
        mae = np.mean(np.abs(errors))
        directional_acc = all_directional_correct / all_directional_total if all_directional_total > 0 else 0
        
        return {
            'rmse': rmse,
            'mae': mae, 
            'directional_acc': directional_acc,
            'mean_error': np.mean(errors),
            'std_error': np.std(errors)
        }
    
    def optimize_ema_alpha(self, anchor: float = 10000, anchor_weight: float = 0.5) -> Dict:
        """Test EMA alphas from 0.05 to 0.50."""
        print("\n=== Optimizing EMA Alpha (Round1 Data) ===")
        alphas = np.arange(0.05, 0.51, 0.05)
        results = []
        
        for alpha in alphas:
            metrics = self.evaluate_parameters(alpha, anchor, anchor_weight)
            results.append({
                'alpha': alpha,
                'rmse': metrics['rmse'],
                'mae': metrics['mae'],
                'directional_acc': metrics['directional_acc']
            })
            print(f"Alpha {alpha:.2f}: RMSE={metrics['rmse']:.2f}, MAE={metrics['mae']:.2f}, Dir_Acc={metrics['directional_acc']:.3f}")
        
        # Find best alpha (lowest RMSE)
        best_result = min(results, key=lambda x: x['rmse'])
        
        return {
            'best_alpha': best_result['alpha'],
            'best_rmse': best_result['rmse'],
            'all_results': results
        }
    
    def optimize_anchor(self, alpha: float = 0.20, anchor_weight: float = 0.5) -> Dict:
        """Test anchor values around 10,000."""
        print("\n=== Optimizing Anchor Price (Round1 Data) ===")
        anchors = np.arange(9980, 10021, 2)  # 9980 to 10020 in steps of 2
        results = []
        
        for anchor in anchors:
            metrics = self.evaluate_parameters(alpha, anchor, anchor_weight)
            results.append({
                'anchor': anchor,
                'rmse': metrics['rmse'],
                'mae': metrics['mae'],
                'directional_acc': metrics['directional_acc']
            })
            if anchor % 10 == 0:  # Print every 10th value
                print(f"Anchor {anchor}: RMSE={metrics['rmse']:.2f}, MAE={metrics['mae']:.2f}")
        
        # Find best anchor
        best_result = min(results, key=lambda x: x['rmse'])
        
        return {
            'best_anchor': best_result['anchor'],
            'best_rmse': best_result['rmse'],
            'all_results': results
        }
    
    def optimize_anchor_weight(self, alpha: float = 0.20, anchor: float = 10000) -> Dict:
        """Test anchor weights from 0.1 to 0.9."""
        print("\n=== Optimizing Anchor Weight (Round1 Data) ===")
        weights = np.arange(0.1, 0.91, 0.1)
        results = []
        
        for weight in weights:
            metrics = self.evaluate_parameters(alpha, anchor, weight)
            results.append({
                'weight': weight,
                'rmse': metrics['rmse'],
                'mae': metrics['mae'],
                'directional_acc': metrics['directional_acc']
            })
            print(f"Weight {weight:.1f}: RMSE={metrics['rmse']:.2f}, MAE={metrics['mae']:.2f}, Dir_Acc={metrics['directional_acc']:.3f}")
        
        # Find best weight
        best_result = min(results, key=lambda x: x['rmse'])
        
        return {
            'best_weight': best_result['weight'],
            'best_rmse': best_result['rmse'],
            'all_results': results
        }
    
    def full_optimization(self) -> Dict:
        """Perform complete parameter optimization using Round1 data only."""
        print("Starting Full Parameter Optimization (Round1 Data Only)...")
        print("=" * 60)
        
        # Step 1: Optimize EMA alpha
        alpha_results = self.optimize_ema_alpha()
        best_alpha = alpha_results['best_alpha']
        
        # Step 2: Optimize anchor using best alpha
        anchor_results = self.optimize_anchor(best_alpha)
        best_anchor = anchor_results['best_anchor']
        
        # Step 3: Optimize anchor weight using best alpha and anchor
        weight_results = self.optimize_anchor_weight(best_alpha, best_anchor)
        best_weight = weight_results['best_weight']
        
        # Final evaluation with all optimal parameters
        final_metrics = self.evaluate_parameters(best_alpha, best_anchor, best_weight)
        
        print("\n" + "=" * 60)
        print("ROUND1 OPTIMIZATION RESULTS")
        print("=" * 60)
        print(f"Optimal EMA Alpha:     {best_alpha:.2f}")
        print(f"Optimal Anchor Price:  {best_anchor:.1f}")
        print(f"Optimal Anchor Weight: {best_weight:.1f}")
        print(f"Final RMSE:            {final_metrics['rmse']:.2f}")
        print(f"Final MAE:             {final_metrics['mae']:.2f}")
        print(f"Directional Accuracy:  {final_metrics['directional_acc']:.3f}")
        print(f"Mean Error:            {final_metrics['mean_error']:.2f}")
        print(f"Error Std Dev:         {final_metrics['std_error']:.2f}")
        
        return {
            'best_alpha': best_alpha,
            'best_anchor': best_anchor,
            'best_weight': best_weight,
            'final_metrics': final_metrics,
            'alpha_results': alpha_results,
            'anchor_results': anchor_results,
            'weight_results': weight_results
        }
    
    def generate_update_code(self, results: Dict) -> str:
        """Generate the exact code to update Zextros.py with optimal parameters."""
        alpha = results['best_alpha']
        anchor = results['best_anchor']
        weight = results['best_weight']
        
        code = f'''
# OPTIMIZED PARAMETERS (from Round1 data-driven analysis)
# Generated on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
# Dataset: {len(self.aco_data)} Round1 days of historical data
# Validation RMSE: {results['final_metrics']['rmse']:.2f}

ACO_ANCHOR     = {int(round(anchor))}  # Optimized from Round1 data
ACO_EMA_ALPHA  = {alpha:.2f}           # Optimized from Round1 data  
ACO_ANCHOR_WT  = {weight:.1f}          # Optimized from Round1 data

# Original parameters for comparison:
# ACO_ANCHOR     = 10_000  # Original guess
# ACO_EMA_ALPHA  = 0.20    # Original guess
# ACO_ANCHOR_WT  = 0.50    # Original guess
'''
        return code

def main():
    """Main optimization routine for Round1 data."""
    optimizer = ACOParameterOptimizer()
    
    # Load Round1 historical data
    optimizer.load_data()
    
    if not optimizer.aco_data:
        print("ERROR: No Round1 data loaded. Check file paths.")
        return
    
    # Run optimization
    results = optimizer.full_optimization()
    
    # Generate update code
    update_code = optimizer.generate_update_code(results)
    
    print("\n" + "=" * 60)
    print("CODE UPDATE FOR ZEXTROS.PY")
    print("=" * 60)
    print(update_code)
    
    # Save results to file
    with open('round1_optimization_results.txt', 'w') as f:
        f.write("ACO Parameter Optimization Results (Round1 Data Only)\n")
        f.write("=" * 50 + "\n")
        f.write(f"Best Alpha: {results['best_alpha']:.2f}\n")
        f.write(f"Best Anchor: {results['best_anchor']:.1f}\n")
        f.write(f"Best Weight: {results['best_weight']:.1f}\n")
        f.write(f"Final RMSE: {results['final_metrics']['rmse']:.2f}\n")
        f.write(f"Final MAE: {results['final_metrics']['mae']:.2f}\n")
        f.write(f"Directional Accuracy: {results['final_metrics']['directional_acc']:.3f}\n")
        f.write("\n" + update_code)
    
    print(f"\nResults saved to: round1_optimization_results.txt")
    print("Copy the parameter updates above into Zextros.py")

if __name__ == "__main__":
    main()
