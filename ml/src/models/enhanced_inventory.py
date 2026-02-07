"""
Enhanced Restaurant Inventory Forecasting - Ingredient-Level Analysis
Adapted for detailed ingredient inventory data with rich features
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from inventory_forecasting import *

class IngredientInventoryProcessor:
    """Process ingredient-level inventory data for ensemble training"""
    
    def __init__(self):
        self.ingredient_encoders = {}
        self.restaurant_encoders = {}
        
    def load_and_preprocess_data(self, file_path: str) -> pd.DataFrame:
        """Load and preprocess the ingredient-level inventory data"""
        logger.info(f"Loading ingredient inventory data from: {file_path}")
        
        data = pd.read_csv(file_path)
        logger.info(f"Raw data shape: {data.shape}")
        logger.info(f"Date range: {data['date'].min()} to {data['date'].max()}")
        logger.info(f"Unique restaurants: {data['restaurant_id'].nunique()}")
        logger.info(f"Unique ingredients: {data['ingredient_id'].nunique()}")
        
        # Convert date
        data['date'] = pd.to_datetime(data['date'])
        
        # Sort by restaurant, ingredient, and date
        data = data.sort_values(['restaurant_id', 'ingredient_id', 'date']).reset_index(drop=True)
        
        return data
    
    def create_aggregated_data(self, data: pd.DataFrame, aggregate_by: str = 'restaurant') -> pd.DataFrame:
        """Create aggregated data for ensemble training"""
        logger.info(f"Creating aggregated data by {aggregate_by}...")
        
        if aggregate_by == 'restaurant':
            # Aggregate all ingredients per restaurant per day
            agg_data = data.groupby(['restaurant_id', 'date']).agg({
                'inventory_start': 'sum',
                'qty_used': 'sum', 
                'stockout_qty': 'sum',
                'inventory_end': 'sum',
                'on_order_qty': 'sum',
                'inventory_position': 'sum',
                'unit_cost': 'mean',
                'covers': 'first',
                'seasonality_factor': 'first',
                'is_weekend': 'first',
                'is_holiday': 'first',
                'day_of_week': 'first',
                'month': 'first',
                'year': 'first',
                'lead_time_days': 'mean',
                'avg_daily_usage_7d': 'sum',
                'avg_daily_usage_28d': 'sum',
                'avg_daily_usage_56d': 'sum',
                'revenue_items_using_ing': 'sum'
            }).reset_index()
            
        elif aggregate_by == 'ingredient':
            # Focus on a specific high-value ingredient
            high_value_ingredients = data.groupby('ingredient_id')['unit_cost'].mean().sort_values(ascending=False).head(5).index
            agg_data = data[data['ingredient_id'].isin(high_value_ingredients)].copy()
            
        else:  # 'both' - use individual ingredient records
            agg_data = data.copy()
        
        # Create inventory_level for compatibility with existing models
        agg_data['inventory_level'] = agg_data['inventory_end']
        
        # Add derived features
        agg_data['inventory_turnover'] = agg_data['qty_used'] / (agg_data['inventory_start'] + 1)
        agg_data['stockout_risk'] = (agg_data['stockout_qty'] > 0).astype(int)
        agg_data['reorder_urgency'] = (agg_data['inventory_position'] <= agg_data.get('reorder_point', 0)).astype(int)
        agg_data['cost_per_unit_used'] = agg_data['unit_cost'] * agg_data['qty_used']
        
        # Revenue-based features
        agg_data['revenue_per_cover'] = agg_data['revenue_items_using_ing'] / (agg_data['covers'] + 1)
        agg_data['usage_efficiency'] = agg_data['qty_used'] / (agg_data['covers'] + 1)
        
        logger.info(f"Aggregated data shape: {agg_data.shape}")
        return agg_data

    def prepare_training_data(self, data: pd.DataFrame, target_restaurant: str = None, 
                            target_ingredient: str = None) -> pd.DataFrame:
        """Prepare data for training - can focus on specific restaurant/ingredient"""
        
        if target_restaurant:
            data = data[data['restaurant_id'] == target_restaurant].copy()
            logger.info(f"Filtered to restaurant {target_restaurant}: {len(data)} records")
            
        if target_ingredient:
            data = data[data['ingredient_id'] == target_ingredient].copy()
            logger.info(f"Filtered to ingredient {target_ingredient}: {len(data)} records")
        
        # Ensure minimum data for training
        if len(data) < 100:
            logger.warning(f"Limited data ({len(data)} records). Consider aggregating or using more data.")
            
        return data.sort_values('date').reset_index(drop=True)

def enhanced_training_pipeline():
    """Enhanced training pipeline for ingredient inventory data"""
    logger.info("🍽️  Enhanced Restaurant Inventory Forecasting - Ingredient Level")
    logger.info("=" * 70)
    
    # Load and process data
    processor = IngredientInventoryProcessor()
    raw_data = processor.load_and_preprocess_data('/home/quentin/ugaHacks/data/restaurant_inventory.csv')
    
    # Show data insights
    logger.info("\n📊 Data Insights:")
    logger.info(f"Total records: {len(raw_data):,}")
    logger.info(f"Date range: {raw_data['date'].min()} to {raw_data['date'].max()}")
    logger.info(f"Restaurants: {raw_data['restaurant_id'].nunique()}")
    logger.info(f"Ingredients: {raw_data['ingredient_id'].nunique()}")
    
    # Top ingredients by value
    top_ingredients = raw_data.groupby('ingredient_name').agg({
        'unit_cost': 'mean',
        'qty_used': 'sum',
        'revenue_items_using_ing': 'sum'
    }).assign(
        total_value=lambda x: x['unit_cost'] * x['qty_used']
    ).sort_values('total_value', ascending=False).head(10)
    
    logger.info("\n💰 Top 10 Ingredients by Total Value:")
    for idx, (name, row) in enumerate(top_ingredients.iterrows(), 1):
        logger.info(f"{idx:2d}. {name:<15} ${row['total_value']:>8,.2f} (${row['unit_cost']:.3f}/unit)")
    
    # Create multiple training scenarios
    scenarios = [
        {
            'name': 'Restaurant Aggregate',
            'data': processor.create_aggregated_data(raw_data, 'restaurant'),
            'description': 'All ingredients aggregated per restaurant per day'
        },
        {
            'name': 'High-Value Ingredients',
            'data': processor.create_aggregated_data(raw_data, 'ingredient'),
            'description': 'Focus on top 5 highest-value ingredients'
        }
    ]
    
    results_summary = {}
    
    for scenario in scenarios:
        logger.info(f"\n🎯 Training Scenario: {scenario['name']}")
        logger.info(f"📝 {scenario['description']}")
        logger.info(f"📊 Data shape: {scenario['data'].shape}")
        
        # Enhanced configuration for this data
        config = ModelConfig(
            xgb_params={
                'n_estimators': 150,
                'max_depth': 8,
                'learning_rate': 0.08,
                'tree_method': 'gpu_hist',
                'gpu_id': 1,
                'random_state': 42,
                'subsample': 0.8,
                'colsample_bytree': 0.8
            },
            lstm_params={
                'hidden_dim': 128,
                'num_layers': 2,
                'dropout': 0.3,
                'output_dim': 1
            },
            sequence_length=14,  # 2 weeks of history
            batch_size=64,
            test_size=0.2,
            val_size=0.1
        )
        
        # Train ensemble
        ensemble = StackedEnsemble(config)
        
        try:
            start_time = time.time()
            training_results = ensemble.train_models_parallel(scenario['data'])
            training_time = time.time() - start_time
            
            # Store results
            results_summary[scenario['name']] = {
                'training_results': training_results,
                'training_time': training_time,
                'data_shape': scenario['data'].shape
            }
            
            # Save models with scenario name
            if ensemble.is_trained:
                save_dir = f"/home/quentin/ugaHacks/models/{scenario['name'].lower().replace(' ', '_')}"
                ensemble.save_models(save_dir)
                logger.info(f"💾 Models saved to: {save_dir}")
            
        except Exception as e:
            logger.error(f"❌ Training failed for {scenario['name']}: {e}")
            results_summary[scenario['name']] = {'error': str(e)}
    
    # Summary Report
    logger.info("\n" + "=" * 70)
    logger.info("📈 TRAINING SUMMARY REPORT")
    logger.info("=" * 70)
    
    for scenario_name, results in results_summary.items():
        logger.info(f"\n{scenario_name.upper()}:")
        
        if 'error' in results:
            logger.info(f"  ❌ Error: {results['error']}")
        else:
            logger.info(f"  ⏱️  Training time: {results['training_time']:.2f}s")
            logger.info(f"  📊 Data shape: {results['data_shape']}")
            
            # Show best model performance
            training_results = results['training_results']
            if 'xgboost' in training_results and 'test_rmse' in training_results['xgboost']:
                logger.info(f"  🎯 XGBoost RMSE: {training_results['xgboost']['test_rmse']:.4f}")
            if 'lstm' in training_results and 'test_rmse' in training_results['lstm']:
                logger.info(f"  🎯 LSTM RMSE: {training_results['lstm']['test_rmse']:.4f}")
    
    return results_summary

def quick_ingredient_analysis():
    """Quick analysis of the ingredient data"""
    logger.info("🔍 Quick Ingredient Data Analysis")
    logger.info("=" * 40)
    
    processor = IngredientInventoryProcessor()
    data = processor.load_and_preprocess_data('/home/quentin/ugaHacks/data/restaurant_inventory.csv')
    
    # Basic stats
    logger.info(f"\n📊 Basic Statistics:")
    logger.info(f"Average inventory level: ${data['inventory_end'].mean():.2f}")
    logger.info(f"Average daily usage: {data['qty_used'].mean():.2f} units")
    logger.info(f"Stockout frequency: {(data['stockout_qty'] > 0).mean()*100:.1f}%")
    logger.info(f"Weekend usage increase: {data.groupby('is_weekend')['qty_used'].mean().pct_change().iloc[-1]*100:.1f}%")
    
    # Seasonal patterns
    monthly_usage = data.groupby('month')['qty_used'].mean()
    logger.info(f"\n📅 Seasonal Patterns:")
    logger.info(f"Highest usage month: {monthly_usage.idxmax()} ({monthly_usage.max():.1f} units/day)")
    logger.info(f"Lowest usage month: {monthly_usage.idxmin()} ({monthly_usage.min():.1f} units/day)")
    
    return data

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced Restaurant Inventory Forecasting')
    parser.add_argument('--analysis', action='store_true', help='Run quick data analysis only')
    parser.add_argument('--train', action='store_true', help='Run enhanced training pipeline')
    
    args = parser.parse_args()
    
    if args.analysis:
        quick_ingredient_analysis()
    elif args.train:
        enhanced_training_pipeline()
    else:
        logger.info("Use --analysis for quick analysis or --train for full training")
        logger.info("Example: python enhanced_inventory.py --analysis")