"""
Simple XGBoost Training - Database Version
Train only XGBoost model using real database data
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib
import logging
from datetime import datetime, timedelta

from data_processing.database_loader import RestaurantDatabaseLoader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def prepare_features(data: pd.DataFrame) -> pd.DataFrame:
    """Prepare features for XGBoost"""
    
    if data.empty:
        return pd.DataFrame()
    
    # Sort by date
    data = data.sort_values('date').copy()
    
    # Add time-based features
    data['day_of_week'] = pd.to_datetime(data['date']).dt.dayofweek
    data['month'] = pd.to_datetime(data['date']).dt.month
    data['day_of_month'] = pd.to_datetime(data['date']).dt.day
    data['is_weekend'] = (data['day_of_week'] >= 5).astype(int)
    
    # Add lag features by ingredient
    for ingredient_id in data['ingredient_id'].unique():
        mask = data['ingredient_id'] == ingredient_id
        for lag in [1, 7, 14]:
            data.loc[mask, f'qty_used_lag_{lag}'] = data.loc[mask, 'qty_used'].shift(lag)
    
    # Add rolling averages by ingredient
    for ingredient_id in data['ingredient_id'].unique():
        mask = data['ingredient_id'] == ingredient_id
        data.loc[mask, 'qty_used_roll_3d'] = data.loc[mask, 'qty_used'].rolling(3).mean()
        data.loc[mask, 'qty_used_roll_7d'] = data.loc[mask, 'qty_used'].rolling(7).mean()
    
    # Basic feature columns
    feature_cols = [
        'covers', 'seasonality_factor', 'inventory_start', 
        'on_order_qty', 'avg_daily_usage_7d', 'avg_daily_usage_28d',
        'shelf_life_days', 'unit_cost', 'is_holiday', 'lead_time_days',
        'day_of_week', 'month', 'day_of_month', 'is_weekend'
    ]
    
    # Add lag and rolling features
    for col in data.columns:
        if col.startswith(('qty_used_lag_', 'qty_used_roll_')):
            feature_cols.append(col)
    
    # Select available features
    available_cols = [col for col in feature_cols if col in data.columns]
    
    return data[available_cols].fillna(0)

def train_simple_xgboost():
    """Train a simple XGBoost model using database data"""
    
    logger.info("🚀 Training Simple XGBoost Model")
    logger.info("=" * 40)
    
    # Load data from database
    logger.info("📊 Loading data from database...")
    with RestaurantDatabaseLoader() as db:
        data = db.load_training_data(days_back=365)
        
        if data.empty:
            logger.error("❌ No training data available")
            return None
            
        logger.info(f"✅ Loaded {len(data)} records")
        logger.info(f"📅 Date range: {data['date'].min()} to {data['date'].max()}")
        logger.info(f"🥘 Ingredients: {data['ingredient_id'].nunique()}")
    
    # Prepare features
    logger.info("🔧 Preparing features...")
    features = prepare_features(data)
    target = data['qty_used'].fillna(0)
    
    # Remove rows with insufficient data (too many NaNs from lags)
    valid_mask = ~features.isnull().any(axis=1)
    features = features[valid_mask]
    target = target[valid_mask]
    
    logger.info(f"📊 Feature matrix shape: {features.shape}")
    logger.info(f"📊 Target shape: {target.shape}")
    logger.info(f"📊 Features: {list(features.columns)}")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        features, target, test_size=0.2, random_state=42
    )
    
    logger.info(f"🔀 Train size: {len(X_train)}, Test size: {len(X_test)}")
    
    # Train XGBoost model
    logger.info("🎯 Training XGBoost...")
    
    model = xgb.XGBRegressor(
        n_estimators=500,
        max_depth=6,
        learning_rate=0.1,
        tree_method='hist',  # CPU-based
        objective='reg:squarederror',
        random_state=42,
        n_jobs=-1
    )
    
    start_time = datetime.now()
    model.fit(X_train, y_train)
    training_time = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"✅ Training completed in {training_time:.2f} seconds")
    
    # Evaluate model
    logger.info("📊 Evaluating model...")
    
    # Predictions
    y_train_pred = model.predict(X_train)
    y_test_pred = model.predict(X_test)
    
    # Metrics
    train_rmse = np.sqrt(mean_squared_error(y_train, y_train_pred))
    test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred))
    train_mae = mean_absolute_error(y_train, y_train_pred)
    test_mae = mean_absolute_error(y_test, y_test_pred)
    train_r2 = r2_score(y_train, y_train_pred)
    test_r2 = r2_score(y_test, y_test_pred)
    
    logger.info("📈 Training Results:")
    logger.info(f"   Train RMSE: {train_rmse:.4f}")
    logger.info(f"   Test RMSE:  {test_rmse:.4f}")
    logger.info(f"   Train MAE:  {train_mae:.4f}")
    logger.info(f"   Test MAE:   {test_mae:.4f}")
    logger.info(f"   Train R²:   {train_r2:.4f}")
    logger.info(f"   Test R²:    {test_r2:.4f}")
    
    # Feature importance
    logger.info("🔍 Top 10 Feature Importances:")
    feature_importance = pd.DataFrame({
        'feature': features.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    for i, row in feature_importance.head(10).iterrows():
        logger.info(f"   {row['feature']}: {row['importance']:.4f}")
    
    # Save model
    model_path = "/home/quentin/ugaHacks/models/xgboost_simple.pkl"
    logger.info(f"💾 Saving model to {model_path}")
    
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(model, model_path)
    
    logger.info("✅ Model saved successfully!")
    
    # Test loading
    logger.info("🧪 Testing model loading...")
    loaded_model = joblib.load(model_path)
    test_pred = loaded_model.predict(X_test[:5])
    logger.info(f"   Sample predictions: {test_pred}")
    logger.info("✅ Model loading test successful!")
    
    return model, {
        'train_rmse': train_rmse,
        'test_rmse': test_rmse,
        'train_r2': train_r2,
        'test_r2': test_r2,
        'training_time': training_time,
        'feature_importance': feature_importance
    }

if __name__ == "__main__":
    model, results = train_simple_xgboost()
    
    if model is not None:
        logger.info("\n🎉 XGBoost training completed successfully!")
    else:
        logger.error("\n❌ XGBoost training failed!")