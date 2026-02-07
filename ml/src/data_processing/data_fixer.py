"""
Data Normalizer for Restaurant Inventory
Fixes unit inconsistencies and scales data properly for ML training
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple

class InventoryDataNormalizer:
    """Normalize inventory data to handle mixed units and scales"""
    
    def __init__(self):
        # Standard conversion factors to normalize everything to "value units"
        self.unit_conversions = {
            # Convert discrete items to approximate gram equivalents for consistency
            'patty': 150,      # 1 beef patty ≈ 150g
            'breast': 200,     # 1 chicken breast ≈ 200g  
            'bun': 50,         # 1 bun ≈ 50g
            'bottle': 500,     # 1 bottle ≈ 500ml = 500g
            'egg': 50,         # 1 egg ≈ 50g
            'dough': 300,      # 1 pizza dough ≈ 300g
            'tortilla': 30,    # 1 tortilla ≈ 30g
            'cup': 240,        # 1 cup ≈ 240ml = 240g
            'ml': 1,           # 1ml ≈ 1g for liquids
            'l': 1000,         # 1L = 1000g
            'g': 1,            # baseline unit
            'kg': 1000,        # 1kg = 1000g
            'oz': 28.35,       # 1oz = 28.35g
            'lb': 453.59,      # 1lb = 453.59g
        }
        
        self.scaling_factors = {}
        self.is_fitted = False
    
    def normalize_units(self, data: pd.DataFrame) -> pd.DataFrame:
        """Convert all quantities to standardized gram-equivalent units"""
        print("🔧 Normalizing units to gram-equivalents...")
        
        data_norm = data.copy()
        
        # Convert quantities to grams
        data_norm['qty_in_grams'] = data_norm.apply(
            lambda row: row['qty_used'] * self.unit_conversions.get(row['unit'], 1), axis=1
        )
        
        data_norm['inventory_in_grams'] = data_norm.apply(
            lambda row: row['inventory_end'] * self.unit_conversions.get(row['unit'], 1), axis=1
        )
        
        data_norm['inventory_start_grams'] = data_norm.apply(
            lambda row: row['inventory_start'] * self.unit_conversions.get(row['unit'], 1), axis=1
        )
        
        # Convert unit costs to per-gram basis
        data_norm['cost_per_gram'] = data_norm.apply(
            lambda row: row['unit_cost'] / self.unit_conversions.get(row['unit'], 1), axis=1
        )
        
        # Create value-based metrics (more meaningful for business)
        data_norm['inventory_value'] = data_norm['inventory_in_grams'] * data_norm['cost_per_gram']
        data_norm['daily_cost'] = data_norm['qty_in_grams'] * data_norm['cost_per_gram']
        data_norm['waste_cost'] = data_norm['stockout_qty'] * data_norm['unit_cost']
        
        print(f"✅ Units normalized. Sample conversions:")
        sample_conversions = data_norm[['ingredient_name', 'unit', 'qty_used', 'qty_in_grams', 'unit_cost', 'cost_per_gram']].head(5)
        for _, row in sample_conversions.iterrows():
            print(f"  {row['ingredient_name']:<15}: {row['qty_used']:6.0f} {row['unit']} = {row['qty_in_grams']:6.0f}g, ${row['unit_cost']:.3f}/{row['unit']} = ${row['cost_per_gram']:.6f}/g")
        
        return data_norm
    
    def create_aggregated_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Create restaurant-level aggregated features for training"""
        print("🏢 Creating restaurant-level aggregated features...")
        
        # Aggregate by restaurant and date
        daily_agg = data.groupby(['restaurant_id', 'date']).agg({
            # Inventory metrics (in grams for consistency)
            'qty_in_grams': 'sum',
            'inventory_in_grams': 'sum', 
            'inventory_start_grams': 'sum',
            
            # Financial metrics  
            'inventory_value': 'sum',
            'daily_cost': 'sum',
            'revenue_items_using_ing': 'sum',
            'waste_cost': 'sum',
            
            # Business context
            'covers': 'first',
            'seasonality_factor': 'first', 
            'is_weekend': 'first',
            'is_holiday': 'first',
            'day_of_week': 'first',
            'month': 'first',
            'year': 'first',
            
            # Operational metrics
            'lead_time_days': 'mean',
            'stockout_qty': 'sum'
        }).reset_index()
        
        # Create derived features
        daily_agg['inventory_turnover'] = daily_agg['qty_in_grams'] / (daily_agg['inventory_start_grams'] + 1)
        daily_agg['cost_per_cover'] = daily_agg['daily_cost'] / (daily_agg['covers'] + 1)
        daily_agg['revenue_per_cover'] = daily_agg['revenue_items_using_ing'] / (daily_agg['covers'] + 1)
        daily_agg['profit_margin'] = (daily_agg['revenue_items_using_ing'] - daily_agg['daily_cost']) / (daily_agg['revenue_items_using_ing'] + 1)
        daily_agg['waste_ratio'] = daily_agg['waste_cost'] / (daily_agg['daily_cost'] + 1)
        
        # For ML compatibility, create 'inventory_level' as our main target
        daily_agg['inventory_level'] = daily_agg['inventory_in_grams']
        
        print(f"✅ Created aggregated features. Shape: {daily_agg.shape}")
        print(f"📊 Key metrics ranges:")
        print(f"  Inventory level: {daily_agg['inventory_level'].min():,.0f} - {daily_agg['inventory_level'].max():,.0f} grams")
        print(f"  Daily cost: ${daily_agg['daily_cost'].min():.2f} - ${daily_agg['daily_cost'].max():,.2f}")
        print(f"  Revenue per cover: ${daily_agg['revenue_per_cover'].min():.2f} - ${daily_agg['revenue_per_cover'].max():.2f}")
        
        return daily_agg
    
    def create_ingredient_features(self, data: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
        """Create features for top N ingredients by value"""
        print(f"🥘 Creating features for top {top_n} ingredients by total value...")
        
        # Calculate total value per ingredient
        ingredient_values = data.groupby('ingredient_id').agg({
            'inventory_value': 'mean',
            'daily_cost': 'mean', 
            'revenue_items_using_ing': 'mean',
            'ingredient_name': 'first'
        }).reset_index()
        
        ingredient_values['total_importance'] = (
            ingredient_values['inventory_value'] + 
            ingredient_values['daily_cost'] + 
            ingredient_values['revenue_items_using_ing']
        )
        
        # Get top ingredients
        top_ingredients = ingredient_values.nlargest(top_n, 'total_importance')
        print("🏆 Top ingredients by business importance:")
        for i, (_, row) in enumerate(top_ingredients.iterrows(), 1):
            print(f"  {i:2d}. {row['ingredient_name']:<20} (Value: ${row['total_importance']:,.0f})")
        
        # Filter data to top ingredients
        top_ingredient_data = data[data['ingredient_id'].isin(top_ingredients['ingredient_id'])].copy()
        
        # Add normalized features
        top_ingredient_data['inventory_level'] = top_ingredient_data['inventory_in_grams']
        
        print(f"✅ Top ingredient data shape: {top_ingredient_data.shape}")
        return top_ingredient_data

def fix_and_prepare_data():
    """Main function to fix the data and prepare for training"""
    print("🔧 Restaurant Inventory Data Fixer")
    print("=" * 50)
    
    # Load raw data
    raw_data = pd.read_csv('/home/quentin/ugaHacks/data/restaurant_inventory.csv')
    print(f"📥 Loaded raw data: {raw_data.shape}")
    
    # Initialize normalizer
    normalizer = InventoryDataNormalizer()
    
    # Normalize units
    normalized_data = normalizer.normalize_units(raw_data)
    
    # Create two training datasets
    print("\\n" + "=" * 50)
    print("Creating Training Datasets")
    print("=" * 50)
    
    # Dataset 1: Restaurant-level aggregation
    restaurant_data = normalizer.create_aggregated_features(normalized_data)
    restaurant_data.to_csv('/home/quentin/ugaHacks/data/restaurant_daily_agg.csv', index=False)
    print(f"💾 Saved restaurant-level data: restaurant_daily_agg.csv")
    
    # Dataset 2: Top ingredients 
    ingredient_data = normalizer.create_ingredient_features(normalized_data, top_n=10)
    ingredient_data.to_csv('/home/quentin/ugaHacks/data/top_ingredients.csv', index=False)
    print(f"💾 Saved top ingredients data: top_ingredients.csv")
    
    print("\\n🎯 FIXED DATA SUMMARY:")
    print("✅ Units normalized to gram-equivalents")
    print("✅ Value-based aggregation for business relevance") 
    print("✅ Two datasets ready for ensemble training:")
    print("   1. Restaurant daily aggregation (macro forecasting)")
    print("   2. Top ingredient tracking (micro forecasting)")
    print("\\n🚀 Ready for GPU training!")
    
    return restaurant_data, ingredient_data

if __name__ == "__main__":
    restaurant_data, ingredient_data = fix_and_prepare_data()