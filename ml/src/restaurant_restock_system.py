"""
Restaurant Inventory Forecasting - Category-Aware Restock System
Enhanced with shelf life management and category-specific ordering patterns

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
from enum import Enum

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IngredientCategory(Enum):
    """Categories for different ingredient types with ordering patterns"""
    PRODUCE = "produce"
    PROTEIN = "protein" 
    DAIRY = "dairy"
    NON_PERISHABLE = "non_perishable"
    ALCOHOL_DRY = "alcohol_dry"

@dataclass
class CategoryMetadata:
    """Metadata for ingredient categories"""
    category: IngredientCategory
    shelf_life_days: int
    delivery_frequency_days: int  # How often deliveries happen
    order_lead_time_days: int     # How far ahead to order
    waste_buffer_days: int        # Extra days before spoilage to reorder
    description: str

# Category definitions based on restaurant industry standards
CATEGORY_METADATA = {
    IngredientCategory.PRODUCE: CategoryMetadata(
        category=IngredientCategory.PRODUCE,
        shelf_life_days=5,
        delivery_frequency_days=2,  # Every 2 days (3-6x/week)
        order_lead_time_days=1,
        waste_buffer_days=2,  # Reorder 2 days before spoilage
        description="Fresh produce - high perishability, frequent delivery"
    ),
    IngredientCategory.PROTEIN: CategoryMetadata(
        category=IngredientCategory.PROTEIN,
        shelf_life_days=4,
        delivery_frequency_days=2,  # Every 2-3 days
        order_lead_time_days=1,
        waste_buffer_days=2,  # Reorder 2 days before spoilage
        description="Meat/Fish - very perishable, frequent prep cycles"
    ),
    IngredientCategory.DAIRY: CategoryMetadata(
        category=IngredientCategory.DAIRY,
        shelf_life_days=10,
        delivery_frequency_days=7,  # Weekly
        order_lead_time_days=2,
        waste_buffer_days=3,  # Reorder 3 days before spoilage
        description="Dairy products - moderate shelf life, weekly delivery"
    ),
    IngredientCategory.NON_PERISHABLE: CategoryMetadata(
        category=IngredientCategory.NON_PERISHABLE,
        shelf_life_days=90,  # 3 months
        delivery_frequency_days=14,  # Bi-weekly
        order_lead_time_days=3,
        waste_buffer_days=0,  # No spoilage concern
        description="Staples - rice, pasta, canned goods"
    ),
    IngredientCategory.ALCOHOL_DRY: CategoryMetadata(
        category=IngredientCategory.ALCOHOL_DRY,
        shelf_life_days=365,  # 1 year
        delivery_frequency_days=30,  # Monthly
        order_lead_time_days=5,
        waste_buffer_days=0,  # No spoilage concern
        description="Alcohol and dry goods - long shelf life, bulk ordering"
    )
}

@dataclass
class XGBoostConfig:
    """Configuration for XGBoost model training"""
    xgb_params: dict
    test_size: float = 0.2
    val_size: float = 0.1

@dataclass
class RestockRecommendation:
    """Business recommendation for ingredient restocking with category awareness"""
    ingredient_id: str
    ingredient_name: str
    category: IngredientCategory
    current_inventory: float
    predicted_inventory_end: float
    shelf_life_days: int
    days_until_spoilage: float
    reorder_point: float
    target_stock_level: float
    restock_needed: bool
    suggested_order_qty: float
    days_until_stockout: float
    confidence_low: float
    confidence_high: float
    priority: str  # 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    lead_time_days: int
    delivery_frequency_days: int
    next_delivery_window: str
    waste_risk: bool  # Risk of spoilage

class XGBoostInventoryModel:
    """XGBoost Model for Inventory Forecasting"""
    
    def __init__(self, config: XGBoostConfig):
        self.config = config
        self.model = None
        self.feature_scaler = StandardScaler()
        self.use_log_transform = True
        self.bias_term = 0.0
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
        
        # Safe inventory features
        inventory_features = ['inventory_start', 'qty_used', 'on_order_qty', 
                            'lead_time_days', 'covers', 'seasonality_factor']
        for feat in inventory_features:
            if feat in data.columns:
                features.append(feat)
        
        # External features
        external_features = ['is_holiday', 'units_sold_items_using_ing', 'revenue_items_using_ing']
        for feat in external_features:
            if feat in data.columns:
                features.append(feat)
        
        return data[features].fillna(0).values
    
    def train(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """Train XGBoost model with Log1p transformation and Poisson objective"""
        logger.info("Training XGBoost model...")
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.config.test_size, random_state=42)
        
        X_train_scaled = self.feature_scaler.fit_transform(X_train)
        X_test_scaled = self.feature_scaler.transform(X_test)
        
        y_train_transformed = np.log1p(y_train)
        y_test_transformed = np.log1p(y_test)
        
        self.model = xgb.XGBRegressor(**self.config.xgb_params)
        
        start_time = time.time()
        self.model.fit(X_train_scaled, y_train_transformed)
        train_time = time.time() - start_time
        
        train_pred_transformed = self.model.predict(X_train_scaled)
        test_pred_transformed = self.model.predict(X_test_scaled)
        
        train_pred = np.expm1(train_pred_transformed)
        test_pred = np.expm1(test_pred_transformed)
        
        residuals = y_train - train_pred
        self.bias_term = np.mean(residuals)
        
        train_pred += self.bias_term
        test_pred += self.bias_term
        
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
        pred = np.expm1(pred_transformed)
        return pred + self.bias_term
    
    def _plot_residuals(self, y_train, train_pred, y_test, test_pred, model_name):
        """Plot residual analysis"""
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        train_residuals = y_train - train_pred
        axes[0].scatter(train_pred, train_residuals, alpha=0.5)
        axes[0].axhline(y=0, color='r', linestyle='--')
        axes[0].set_xlabel('Predicted Values')
        axes[0].set_ylabel('Residuals')
        axes[0].set_title(f'{model_name} - Training Residuals')
        
        test_residuals = y_test - test_pred
        axes[1].scatter(test_pred, test_residuals, alpha=0.5)
        axes[1].axhline(y=0, color='r', linestyle='--')
        axes[1].set_xlabel('Predicted Values')
        axes[1].set_ylabel('Residuals')
        axes[1].set_title(f'{model_name} - Test Residuals')
        
        plt.tight_layout()
        plt.savefig(f'/home/quentin/ugaHacks/residuals_restaurant_system.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Residual analysis saved: residuals_restaurant_system.png")

class RestockRecommendationEngine:
    """Engine that converts predictions into restaurant-industry recommendations"""
    
    def __init__(self, model: XGBoostInventoryModel):
        self.model = model
        self.safety_factor = 1.1  # 10% safety buffer
    
    def classify_ingredient(self, ingredient_name: str) -> IngredientCategory:
        """Classify ingredient into category based on name patterns"""
        name_lower = ingredient_name.lower()
        
        # Keyword mappings for ingredient classification
        produce_keywords = ['lettuce', 'tomato', 'onion', 'bell', 'pepper', 'cucumber', 'carrot', 
                          'spinach', 'arugula', 'romaine', 'basil', 'cilantro', 'parsley', 'herb',
                          'mushroom', 'avocado', 'lime', 'lemon', 'potato', 'celery']
        
        protein_keywords = ['chicken', 'beef', 'pork', 'fish', 'salmon', 'tuna', 'shrimp', 
                          'turkey', 'duck', 'lamb', 'bacon', 'sausage', 'ham', 'meat']
        
        dairy_keywords = ['cheese', 'milk', 'cream', 'butter', 'yogurt', 'mozzarella', 
                        'cheddar', 'parmesan', 'swiss', 'goat', 'feta', 'ricotta']
        
        non_perishable_keywords = ['rice', 'pasta', 'flour', 'sugar', 'salt', 'oil', 'vinegar',
                                 'sauce', 'dressing', 'spice', 'seasoning', 'bread', 'bun',
                                 'crouton', 'noodle', 'grain']
        
        alcohol_dry_keywords = ['wine', 'beer', 'vodka', 'whiskey', 'rum', 'gin', 'liquor',
                              'alcohol', 'spirit', 'cocktail', 'mix']
        
        if any(keyword in name_lower for keyword in produce_keywords):
            return IngredientCategory.PRODUCE
        elif any(keyword in name_lower for keyword in protein_keywords):
            return IngredientCategory.PROTEIN
        elif any(keyword in name_lower for keyword in dairy_keywords):
            return IngredientCategory.DAIRY
        elif any(keyword in name_lower for keyword in alcohol_dry_keywords):
            return IngredientCategory.ALCOHOL_DRY
        elif any(keyword in name_lower for keyword in non_perishable_keywords):
            return IngredientCategory.NON_PERISHABLE
        else:
            return IngredientCategory.NON_PERISHABLE
    
    def predict_with_uncertainty(self, X: np.ndarray) -> tuple:
        """Get prediction with confidence intervals"""
        if not self.model.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        pred_mean = self.model.predict(X)
        pred_std = pred_mean * 0.15  # 15% relative uncertainty
        
        confidence_low = pred_mean - 1.96 * pred_std
        confidence_high = pred_mean + 1.96 * pred_std
        
        return pred_mean, confidence_low, confidence_high
    
    def calculate_days_until_stockout(self, current_inventory: float, avg_daily_usage: float) -> float:
        """Calculate days until stockout"""
        if avg_daily_usage <= 0:
            return float('inf')
        return max(0, current_inventory / avg_daily_usage)
    
    def determine_priority(self, days_until_stockout: float, days_until_spoilage: float, 
                         restock_needed: bool, category: IngredientCategory) -> str:
        """Determine priority with category-specific logic"""
        if not restock_needed and days_until_spoilage > 3:
            return 'LOW'
        
        # Critical priority for spoilage risk or immediate stockout
        if days_until_spoilage < 1 or days_until_stockout < 1:
            return 'CRITICAL'
        
        # High priority based on category-specific thresholds
        if category in [IngredientCategory.PRODUCE, IngredientCategory.PROTEIN]:
            if days_until_stockout < 3 or days_until_spoilage < 2:
                return 'HIGH'
            elif days_until_stockout < 5 or restock_needed:
                return 'MEDIUM'
        elif category == IngredientCategory.DAIRY:
            if days_until_stockout < 5 or days_until_spoilage < 3:
                return 'HIGH'
            elif days_until_stockout < 7 or restock_needed:
                return 'MEDIUM'
        else:  # Non-perishables and alcohol
            if days_until_stockout < 7:
                return 'HIGH'
            elif days_until_stockout < 14 or restock_needed:
                return 'MEDIUM'
        
        return 'LOW'
    
    def generate_restock_recommendations(self, data: pd.DataFrame, 
                                       ingredient_filter: List[str] = None) -> List[RestockRecommendation]:
        """Generate category-aware restock recommendations"""
        logger.info("Generating restaurant-industry restock recommendations...")
        
        recommendations = []
        grouped = data.groupby(['ingredient_id', 'ingredient_name']).last().reset_index()
        
        if ingredient_filter:
            grouped = grouped[grouped['ingredient_id'].isin(ingredient_filter)]
        
        for _, row in grouped.iterrows():
            try:
                ingredient_data = data[data['ingredient_id'] == row['ingredient_id']].copy()
                features = self.model.prepare_tabular_features(ingredient_data)
                
                if len(features) == 0:
                    continue
                    
                pred_mean, pred_low, pred_high = self.predict_with_uncertainty(features[-1:])
                
                # Category-based business logic
                current_inventory = row.get('inventory_start', 0)
                avg_daily_usage = row.get('avg_daily_usage_7d', row.get('qty_used', 0))
                
                category = self.classify_ingredient(row['ingredient_name'])
                metadata = CATEGORY_METADATA[category]
                
                # Calculate reorder points based on category
                min_stock_days = metadata.delivery_frequency_days + metadata.order_lead_time_days + metadata.waste_buffer_days
                reorder_point = avg_daily_usage * min_stock_days if avg_daily_usage > 0 else current_inventory * 0.3
                
                target_stock_days = metadata.delivery_frequency_days * 2 + metadata.order_lead_time_days
                target_stock = avg_daily_usage * target_stock_days if avg_daily_usage > 0 else current_inventory * 1.5
                
                days_until_spoilage = metadata.shelf_life_days - metadata.waste_buffer_days
                
                predicted_end = pred_mean[0]
                restock_needed = predicted_end < reorder_point or days_until_spoilage < metadata.waste_buffer_days + 1
                
                # Category-specific ordering
                if restock_needed:
                    if category in [IngredientCategory.PRODUCE, IngredientCategory.PROTEIN]:
                        # Order for next delivery cycle only to minimize waste
                        order_period_days = metadata.delivery_frequency_days + metadata.order_lead_time_days
                        needed_inventory = avg_daily_usage * order_period_days if avg_daily_usage > 0 else target_stock * 0.5
                        shortfall = needed_inventory - predicted_end
                    else:
                        shortfall = target_stock - predicted_end
                    
                    suggested_qty = max(0, shortfall * self.safety_factor)
                else:
                    suggested_qty = 0
                
                days_until_stockout = self.calculate_days_until_stockout(predicted_end, avg_daily_usage)
                waste_risk = days_until_spoilage < 3 and current_inventory > avg_daily_usage * 2
                priority = self.determine_priority(days_until_stockout, days_until_spoilage, restock_needed, category)
                next_delivery = f"Next {metadata.description.split(' - ')[1].split(',')[0]} delivery in ~{metadata.delivery_frequency_days} days"
                
                recommendation = RestockRecommendation(
                    ingredient_id=row['ingredient_id'],
                    ingredient_name=row['ingredient_name'],
                    category=category,
                    current_inventory=current_inventory,
                    predicted_inventory_end=predicted_end,
                    shelf_life_days=metadata.shelf_life_days,
                    days_until_spoilage=days_until_spoilage,
                    reorder_point=reorder_point,
                    target_stock_level=target_stock,
                    restock_needed=restock_needed,
                    suggested_order_qty=suggested_qty,
                    days_until_stockout=days_until_stockout,
                    confidence_low=pred_low[0],
                    confidence_high=pred_high[0],
                    priority=priority,
                    lead_time_days=metadata.order_lead_time_days,
                    delivery_frequency_days=metadata.delivery_frequency_days,
                    next_delivery_window=next_delivery,
                    waste_risk=waste_risk
                )
                
                recommendations.append(recommendation)
                
            except Exception as e:
                logger.warning(f"Failed to generate recommendation for {row.get('ingredient_id', 'unknown')}: {e}")
                continue
        
        # Sort by priority, category importance, and urgency
        priority_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        category_importance = {
            IngredientCategory.PROTEIN: 0,
            IngredientCategory.PRODUCE: 1,
            IngredientCategory.DAIRY: 2,
            IngredientCategory.NON_PERISHABLE: 3,
            IngredientCategory.ALCOHOL_DRY: 4
        }
        
        recommendations.sort(key=lambda x: (
            priority_order[x.priority], 
            category_importance[x.category],
            x.days_until_stockout,
            -x.suggested_order_qty
        ))
        
        logger.info(f"Generated {len(recommendations)} restaurant-industry recommendations")
        return recommendations
    
    def print_recommendations(self, recommendations: List[RestockRecommendation], limit: int = 10):
        """Print restaurant-industry formatted recommendations"""
        print("\n" + "="*80)
        print("🏪 RESTAURANT INVENTORY RESTOCK SYSTEM")
        print("="*80)
        
        if not recommendations:
            print("✅ No restocking needed - all ingredients properly stocked!")
            return
        
        # Enhanced summary with category breakdown
        critical_priority = sum(1 for r in recommendations if r.priority == 'CRITICAL')
        high_priority = sum(1 for r in recommendations if r.priority == 'HIGH')
        medium_priority = sum(1 for r in recommendations if r.priority == 'MEDIUM')
        total_restock = sum(1 for r in recommendations if r.restock_needed)
        waste_risk_count = sum(1 for r in recommendations if r.waste_risk)
        
        print(f"📊 Summary: {total_restock} ingredients need restocking")
        if critical_priority > 0:
            print(f"🚨 CRITICAL: {critical_priority} (spoilage risk or <1 day stock)")
        print(f"🔴 High Priority: {high_priority}")
        print(f"🟡 Medium Priority: {medium_priority}")
        print(f"🟢 Low Priority: {len(recommendations) - critical_priority - high_priority - medium_priority}")
        if waste_risk_count > 0:
            print(f"⚠️  Waste Risk: {waste_risk_count} ingredients may spoil")
        print()
        
        # Category breakdown
        category_counts = {}
        for rec in recommendations[:limit]:
            cat = rec.category.value.title()
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        print("📦 Categories in top recommendations:")
        for cat, count in category_counts.items():
            emoji = {'Produce': '🥬', 'Protein': '🥩', 'Dairy': '🧀', 
                    'Non_Perishable': '📦', 'Alcohol_Dry': '🍷'}.get(cat, '📦')
            print(f"   {emoji} {cat}: {count}")
        print()
        
        # Individual recommendations
        for i, rec in enumerate(recommendations[:limit], 1):
            priority_emoji = {
                'CRITICAL': '🚨', 'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🟢'
            }[rec.priority]
            
            category_emoji = {
                IngredientCategory.PRODUCE: '🥬',
                IngredientCategory.PROTEIN: '🥩', 
                IngredientCategory.DAIRY: '🧀',
                IngredientCategory.NON_PERISHABLE: '📦',
                IngredientCategory.ALCOHOL_DRY: '🍷'
            }[rec.category]
            
            print(f"{i}. {priority_emoji} {category_emoji} {rec.ingredient_name} ({rec.ingredient_id})")
            print(f"   Category: {rec.category.value.title()} | Shelf Life: {rec.shelf_life_days} days")
            print(f"   Current: {rec.current_inventory:.1f} → Predicted: {rec.predicted_inventory_end:.1f}")
            print(f"   Reorder Point: {rec.reorder_point:.1f} | Target: {rec.target_stock_level:.1f}")
            
            if rec.waste_risk:
                print(f"   ⚠️  SPOILAGE RISK: {rec.days_until_spoilage:.1f} days until spoilage!")
            
            if rec.restock_needed:
                print(f"   📦 ORDER: {rec.suggested_order_qty:.1f} units")
                print(f"   ⏰ Stock runs out in: {rec.days_until_stockout:.1f} days")
            else:
                print(f"   ✅ Sufficient stock for {rec.days_until_stockout:.1f} days")
            
            print(f"   🚛 {rec.next_delivery_window}")
            print(f"   📈 95% CI: [{rec.confidence_low:.1f}, {rec.confidence_high:.1f}]")
            print()
        
        if len(recommendations) > limit:
            print(f"... and {len(recommendations) - limit} more recommendations")

def main():
    """Main restaurant restock system pipeline"""
    logger.info("Starting Restaurant Industry Restock System")
    
    config = XGBoostConfig(
        xgb_params={
            'n_estimators': 1000,
            'max_depth': 6,
            'learning_rate': 0.05,
            'tree_method': 'hist',
            'objective': 'count:poisson',
            'random_state': 42
        }
    )
    
    # Load data
    logger.info("Loading restaurant inventory data...")
    if os.path.exists('/home/quentin/ugaHacks/data/restaurant_inventory.csv'):
        data = pd.read_csv('/home/quentin/ugaHacks/data/restaurant_inventory.csv')
        logger.info(f"Loaded data with shape: {data.shape}")
    else:
        logger.error("Restaurant inventory data not found!")
        return None, None, None
    
    # Train model
    model = XGBoostInventoryModel(config)
    
    logger.info("Preparing data...")
    tabular_features = model.prepare_tabular_features(data.copy())
    target = data['inventory_end'].values
    
    logger.info("Training model...")
    start_time = time.time()
    results = model.train(tabular_features, target)
    total_time = time.time() - start_time
    
    logger.info("Model training completed!")
    for metric, value in results.items():
        logger.info(f"  {metric}: {value}")
    logger.info(f"Total training time: {total_time:.2f} seconds")
    
    # Generate restaurant-industry recommendations
    logger.info("\n" + "="*50)
    logger.info("GENERATING RESTAURANT RECOMMENDATIONS")
    logger.info("="*50)
    
    restock_engine = RestockRecommendationEngine(model)
    
    # Sample top ingredients for demo
    sample_ingredients = data['ingredient_id'].unique()[:25]
    recommendations = restock_engine.generate_restock_recommendations(
        data, 
        ingredient_filter=list(sample_ingredients)
    )
    
    # Display restaurant-ready recommendations
    restock_engine.print_recommendations(recommendations, limit=15)
    
    # Save model
    save_dir = '/home/quentin/ugaHacks/models'
    os.makedirs(save_dir, exist_ok=True)
    joblib.dump(model, f"{save_dir}/restaurant_restock_model.pkl")
    logger.info(f"Restaurant restock system saved to {save_dir}")
    
    return model, results, recommendations

if __name__ == "__main__":
    model, results, recommendations = main()