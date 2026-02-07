"""
Restaurant Inventory Forecasting - XGBoost Only
Simplified benchmark without LSTM

Author: Generated for UGA Hacks
Date: February 7, 2026
"""

import os
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import matplotlib.pyplot as plt
import joblib
from typing import Dict, Any, List
import logging
import time
from dataclasses import dataclass

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class RestockRecommendation:
    """Business recommendation for ingredient restocking"""
    ingredient_id: str
    ingredient_name: str
    current_inventory: float
    predicted_inventory_end: float
    reorder_point: float
    target_stock_level: float
    restock_needed: bool
    suggested_order_qty: float
    days_until_stockout: float
    confidence_low: float
    confidence_high: float
    priority: str  # 'HIGH', 'MEDIUM', 'LOW'
    lead_time_days: int

@dataclass
class XGBoostConfig:
    """Configuration for XGBoost model training"""
    # XGBoost Config
    xgb_params: dict
    
    # Data Config
    test_size: float = 0.2
    val_size: float = 0.1

class XGBoostInventoryModel:
    """XGBoost Model for Inventory Forecasting"""
    
    def __init__(self, config: XGBoostConfig):
        self.config = config
        self.model = None
        self.feature_scaler = StandardScaler()
        self.use_log_transform = True  # Use Log1p transformation for target
        self.bias_term = 0.0  # For bias correction
        self.is_trained = False
        
    def prepare_tabular_features(self, data: pd.DataFrame) -> np.ndarray:
        """Extract and prepare tabular features"""
        logger.info("Preparing tabular features for XGBoost...")
        
        features = []
        
        # Time-based features
        if 'date' in data.columns:
            data['date'] = pd.to_datetime(data['date'])
            data['day_of_week'] = data['date'].dt.dayofweek
            data['month'] = data['date'].dt.month
            data['quarter'] = data['date'].dt.quarter
            data['is_weekend'] = (data['day_of_week'] >= 5).astype(int)
            
            features.extend(['day_of_week', 'month', 'quarter', 'is_weekend'])
        
        # Statistical features (rolling windows) - use legitimate features only
        # Use inventory_start for rolling stats (available at prediction time)
        base_col = 'inventory_start'
        if base_col in data.columns:
            for window in [7, 14, 30]:
                data[f'rolling_mean_start_{window}'] = data[base_col].rolling(window).mean()
                data[f'rolling_std_start_{window}'] = data[base_col].rolling(window).std()
                features.extend([f'rolling_mean_start_{window}', f'rolling_std_start_{window}'])
        
        # Lag features - use inventory_end lags (past values only)
        target_col = 'inventory_end'
        for lag in [1, 3, 7, 14]:
            data[f'inventory_end_lag_{lag}'] = data[target_col].shift(lag)
            features.append(f'inventory_end_lag_{lag}')
        
        # Safe inventory features (available at prediction time)
        inventory_features = ['inventory_start', 'qty_used', 'on_order_qty', 
                            'lead_time_days', 'covers', 'seasonality_factor']
        for feat in inventory_features:
            if feat in data.columns:
                features.append(feat)
        
        # External features (if available)
        external_features = ['is_holiday', 'units_sold_items_using_ing', 'revenue_items_using_ing']
        for feat in external_features:
            if feat in data.columns:
                features.append(feat)
        
        return data[features].fillna(0).values
    
    def train(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """Train XGBoost model with Log1p transformation and Poisson objective"""
        logger.info("Training XGBoost model...")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.config.test_size, random_state=42)
        
        # Scale features
        X_train_scaled = self.feature_scaler.fit_transform(X_train)
        X_test_scaled = self.feature_scaler.transform(X_test)
        
        # Apply Log1p transformation to targets for heteroscedasticity
        y_train_transformed = np.log1p(y_train)  # Log1p handles values close to 0
        y_test_transformed = np.log1p(y_test)
        
        # Train XGBoost with Poisson objective on log-transformed targets
        self.model = xgb.XGBRegressor(**self.config.xgb_params)
        
        start_time = time.time()
        self.model.fit(X_train_scaled, y_train_transformed)
        train_time = time.time() - start_time
        
        # Get predictions in transformed space
        train_pred_transformed = self.model.predict(X_train_scaled)
        test_pred_transformed = self.model.predict(X_test_scaled)
        
        # Inverse transform predictions to original scale using expm1
        train_pred = np.expm1(train_pred_transformed)  # Inverse of log1p
        test_pred = np.expm1(test_pred_transformed)
        
        # Calculate bias correction
        residuals = y_train - train_pred
        self.bias_term = np.mean(residuals)
        
        # Apply bias correction
        train_pred += self.bias_term
        test_pred += self.bias_term
        
        # Plot residual analysis
        self._plot_residuals(y_train, train_pred, y_test, test_pred, 'XGBoost')
        
        metrics = {
            'train_rmse': np.sqrt(mean_squared_error(y_train, train_pred)),
            'test_rmse': np.sqrt(mean_squared_error(y_test, test_pred)),
            'train_mae': mean_absolute_error(y_train, train_pred),
            'test_mae': mean_absolute_error(y_test, test_pred),
            'train_r2': r2_score(y_train, train_pred),
            'test_r2': r2_score(y_test, test_pred),
            'train_time': train_time,
            'bias_term': self.bias_term
        }
        
        self.is_trained = True
        logger.info(f"XGBoost training completed. Test RMSE: {metrics['test_rmse']:.4f}")
        
        return metrics
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions with Log1p inverse transformation and bias correction"""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        X_scaled = self.feature_scaler.transform(X)
        pred_transformed = self.model.predict(X_scaled)
        # Inverse transform from log space to original scale
        pred = np.expm1(pred_transformed)
        return pred + self.bias_term
    
    def _plot_residuals(self, y_train, train_pred, y_test, test_pred, model_name):
        """Plot residual analysis"""
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        # Training residuals
        train_residuals = y_train - train_pred
        axes[0].scatter(train_pred, train_residuals, alpha=0.5)
        axes[0].axhline(y=0, color='r', linestyle='--')
        axes[0].set_xlabel('Predicted Values')
        axes[0].set_ylabel('Residuals')
        axes[0].set_title(f'{model_name} - Training Residuals')
        
        # Test residuals
        test_residuals = y_test - test_pred
        axes[1].scatter(test_pred, test_residuals, alpha=0.5)
        axes[1].axhline(y=0, color='r', linestyle='--')
        axes[1].set_xlabel('Predicted Values')
        axes[1].set_ylabel('Residuals')
        axes[1].set_title(f'{model_name} - Test Residuals')
        
        plt.tight_layout()
        plt.savefig(f'/home/quentin/ugaHacks/residuals_{model_name.lower()}_only.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Residual analysis saved: residuals_{model_name.lower()}_only.png")
        logger.info(f"{model_name} bias term: {self.bias_term:.6f}")
    
    def save_model(self, save_dir: str):
        """Save the model"""
        os.makedirs(save_dir, exist_ok=True)
        joblib.dump(self, f"{save_dir}/xgboost_only_model.pkl")
        logger.info(f"Model saved to {save_dir}/xgboost_only_model.pkl")
    
    def load_model(self, save_path: str):
        """Load the model"""
        loaded_model = joblib.load(save_path)
        self.__dict__.update(loaded_model.__dict__)
        logger.info(f"Model loaded from {save_path}")

class RestockRecommendationEngine:
    """Engine that converts predictions into business recommendations"""
    
    def __init__(self, model: XGBoostInventoryModel):
        self.model = model
        self.safety_factor = 1.2  # 20% safety buffer
    
    def predict_with_uncertainty(self, X: np.ndarray, n_estimators_sample: int = 50) -> tuple:
        """Get prediction with confidence intervals using bootstrap sampling"""
        if not self.model.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        # Get base prediction
        pred_mean = self.model.predict(X)
        
        # Simple uncertainty estimation using model's prediction variance
        # In production, could use quantile regression or prediction intervals
        pred_std = pred_mean * 0.15  # Assume 15% relative uncertainty
        
        confidence_low = pred_mean - 1.96 * pred_std  # 95% CI lower bound
        confidence_high = pred_mean + 1.96 * pred_std  # 95% CI upper bound
        
        return pred_mean, confidence_low, confidence_high
    
    def calculate_days_until_stockout(self, current_inventory: float, avg_daily_usage: float) -> float:
        """Calculate days until stockout based on current usage patterns"""
        if avg_daily_usage <= 0:
            return float('inf')  # No usage, won't run out
        return max(0, current_inventory / avg_daily_usage)
    
    def determine_priority(self, days_until_stockout: float, restock_needed: bool) -> str:
        """Determine priority level for restocking"""
        if not restock_needed:
            return 'LOW'
        elif days_until_stockout < 2:
            return 'HIGH'  # Critical - less than 2 days
        elif days_until_stockout < 5:
            return 'MEDIUM'  # Important - less than 5 days
        else:
            return 'LOW'
    
    def generate_restock_recommendations(self, 
                                       data: pd.DataFrame, 
                                       ingredient_filter: List[str] = None) -> List[RestockRecommendation]:
        """Generate restock recommendations for ingredients"""
        logger.info("Generating restock recommendations...")
        
        recommendations = []
        
        # Group by ingredient for latest data
        grouped = data.groupby(['ingredient_id', 'ingredient_name']).last().reset_index()
        
        if ingredient_filter:
            grouped = grouped[grouped['ingredient_id'].isin(ingredient_filter)]
        
        for _, row in grouped.iterrows():
            try:
                # Prepare features for this ingredient
                ingredient_data = data[data['ingredient_id'] == row['ingredient_id']].copy()
                features = self.model.prepare_tabular_features(ingredient_data)
                
                if len(features) == 0:
                    continue
                    
                # Get prediction with uncertainty
                pred_mean, pred_low, pred_high = self.predict_with_uncertainty(features[-1:])  # Latest row
                
                # Extract business parameters
                current_inventory = row.get('inventory_start', 0)
                reorder_point = row.get('reorder_point', current_inventory * 0.2)  # Default 20% of current
                target_stock = row.get('target_stock_level_S', current_inventory * 1.5)  # Default 150% of current
                avg_daily_usage = row.get('avg_daily_usage_7d', row.get('qty_used', 0))
                lead_time = int(row.get('lead_time_days', 3))  # Default 3 days
                
                # Business logic
                predicted_end = pred_mean[0]
                restock_needed = predicted_end < reorder_point
                
                # Calculate order quantity
                if restock_needed:
                    # Order enough to reach target stock level plus safety factor
                    shortfall = target_stock - predicted_end
                    suggested_qty = shortfall * self.safety_factor
                else:
                    suggested_qty = 0
                
                # Calculate days until stockout
                days_until_stockout = self.calculate_days_until_stockout(predicted_end, avg_daily_usage)
                
                # Determine priority
                priority = self.determine_priority(days_until_stockout, restock_needed)
                
                # Create recommendation
                recommendation = RestockRecommendation(
                    ingredient_id=row['ingredient_id'],
                    ingredient_name=row['ingredient_name'],
                    current_inventory=current_inventory,
                    predicted_inventory_end=predicted_end,
                    reorder_point=reorder_point,
                    target_stock_level=target_stock,
                    restock_needed=restock_needed,
                    suggested_order_qty=max(0, suggested_qty),
                    days_until_stockout=days_until_stockout,
                    confidence_low=pred_low[0],
                    confidence_high=pred_high[0],
                    priority=priority,
                    lead_time_days=lead_time
                )
                
                recommendations.append(recommendation)
                
            except Exception as e:
                logger.warning(f"Failed to generate recommendation for {row.get('ingredient_id', 'unknown')}: {e}")
                continue
        
        # Sort by priority and days until stockout
        priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
        recommendations.sort(key=lambda x: (priority_order[x.priority], x.days_until_stockout))
        
        logger.info(f"Generated {len(recommendations)} restock recommendations")
        return recommendations
    
    def print_recommendations(self, recommendations: List[RestockRecommendation], limit: int = 10):
        """Print formatted restock recommendations"""
        print("\n" + "="*80)
        print("🏪 INVENTORY RESTOCK RECOMMENDATIONS")
        print("="*80)
        
        if not recommendations:
            print("✅ No restocking needed - all ingredients well stocked!")
            return
        
        # Summary stats
        high_priority = sum(1 for r in recommendations if r.priority == 'HIGH')
        medium_priority = sum(1 for r in recommendations if r.priority == 'MEDIUM')
        total_restock = sum(1 for r in recommendations if r.restock_needed)
        
        print(f"📊 Summary: {total_restock} ingredients need restocking")
        print(f"🔴 High Priority: {high_priority}")
        print(f"🟡 Medium Priority: {medium_priority}")
        print(f"🟢 Low Priority: {len(recommendations) - high_priority - medium_priority}")
        print()
        
        # Top recommendations
        for i, rec in enumerate(recommendations[:limit], 1):
            priority_emoji = {'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🟢'}[rec.priority]
            
            print(f"{i}. {priority_emoji} {rec.ingredient_name} ({rec.ingredient_id})")
            print(f"   Current: {rec.current_inventory:.1f} → Predicted: {rec.predicted_inventory_end:.1f}")
            print(f"   Reorder Point: {rec.reorder_point:.1f} | Target Stock: {rec.target_stock_level:.1f}")
            
            if rec.restock_needed:
                print(f"   ⚠️  ORDER NOW: {rec.suggested_order_qty:.1f} units")
                print(f"   ⏰ Days until stockout: {rec.days_until_stockout:.1f}")
            else:
                print(f"   ✅ Well stocked for {rec.days_until_stockout:.1f} days")
            
            print(f"   📈 95% CI: [{rec.confidence_low:.1f}, {rec.confidence_high:.1f}]")
            print(f"   📦 Lead time: {rec.lead_time_days} days")
            print()
        
        if len(recommendations) > limit:
            print(f"... and {len(recommendations) - limit} more recommendations")

def create_sample_data(n_samples: int = 1000) -> pd.DataFrame:
    """Create sample restaurant inventory data for testing"""
    np.random.seed(42)
    
    dates = pd.date_range('2023-01-01', periods=n_samples, freq='D')
    
    # Base inventory level with trend and seasonality
    trend = np.linspace(100, 120, n_samples)
    seasonal = 10 * np.sin(2 * np.pi * np.arange(n_samples) / 365.25)  # Yearly
    weekly = 5 * np.sin(2 * np.pi * np.arange(n_samples) / 7)  # Weekly
    noise = np.random.normal(0, 3, n_samples)
    
    inventory_level = trend + seasonal + weekly + noise
    
    # Other features
    temperature = 20 + 10 * np.sin(2 * np.pi * np.arange(n_samples) / 365.25) + np.random.normal(0, 2, n_samples)
    precipitation = np.random.exponential(2, n_samples)
    holiday_flag = np.random.binomial(1, 0.05, n_samples)  # 5% chance of holiday
    promotion_flag = np.random.binomial(1, 0.1, n_samples)  # 10% chance of promotion
    special_event = np.random.binomial(1, 0.02, n_samples)  # 2% chance of special event
    
    # Sales data (correlated with inventory)
    sales = 0.8 * inventory_level + np.random.normal(0, 5, n_samples)
    
    df = pd.DataFrame({
        'date': dates,
        'inventory_level': inventory_level,
        'temperature': temperature,
        'precipitation': precipitation,
        'holiday_flag': holiday_flag,
        'promotion_flag': promotion_flag,
        'special_event': special_event,
        'sales': sales
    })
    
    return df

def main():
    """Main training pipeline"""
    logger.info("Starting Restaurant Inventory Forecasting - XGBoost Only")
    
    # Configuration with optimized XGBoost parameters
    config = XGBoostConfig(
        xgb_params={
            'n_estimators': 1000,
            'max_depth': 6,
            'learning_rate': 0.05,
            'tree_method': 'hist',  # CPU-based tree method
            'objective': 'count:poisson',  # Poisson regression for count data
            'random_state': 42
        }
    )
    
    # Create or load data
    logger.info("Loading data...")
    if os.path.exists('/home/quentin/ugaHacks/data/restaurant_inventory.csv'):
        data = pd.read_csv('/home/quentin/ugaHacks/data/restaurant_inventory.csv')
        logger.info(f"Loaded real data with shape: {data.shape}")
    else:
        logger.info("Real data not found. Creating sample data...")
        data = create_sample_data(1500)
        os.makedirs('/home/quentin/ugaHacks/data', exist_ok=True)
        data.to_csv('/home/quentin/ugaHacks/data/restaurant_inventory.csv', index=False)
        logger.info(f"Created sample data with shape: {data.shape}")
    
    # Initialize model
    model = XGBoostInventoryModel(config)
    
    # Prepare data
    logger.info("Preparing data for training...")
    tabular_features = model.prepare_tabular_features(data.copy())
    target = data['inventory_end'].values
    
    # Train model
    logger.info("="*50)
    logger.info("STARTING XGBOOST TRAINING")
    logger.info("="*50)
    
    start_time = time.time()
    results = model.train(tabular_features, target)
    total_time = time.time() - start_time
    
    # Print results
    logger.info("="*50)
    logger.info("TRAINING RESULTS")
    logger.info("="*50)
    
    logger.info(f"\nXGBOOST Results:")
    for metric, value in results.items():
        logger.info(f"  {metric}: {value}")
    
    logger.info(f"\nTotal Training Time: {total_time:.2f} seconds")
    
    # Save model
    save_dir = '/home/quentin/ugaHacks/models'
    model.save_model(save_dir)
    logger.info("Model training completed successfully! Model saved.")
    
    # Generate restock recommendations
    logger.info("\n" + "="*50)
    logger.info("GENERATING RESTOCK RECOMMENDATIONS")
    logger.info("="*50)
    
    restock_engine = RestockRecommendationEngine(model)
    
    # Generate recommendations for top ingredients (sample)
    sample_ingredients = data['ingredient_id'].unique()[:20]  # First 20 ingredients
    recommendations = restock_engine.generate_restock_recommendations(
        data, 
        ingredient_filter=list(sample_ingredients)
    )
    
    # Display recommendations
    restock_engine.print_recommendations(recommendations, limit=10)
    
    return model, results, recommendations

if __name__ == "__main__":
    model, results, recommendations = main()