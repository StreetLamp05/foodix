"""
Ultra Simple ML Endpoints - XGBoost Only
No complex imports, just basic XGBoost predictions

Author: Generated for UGA Hacks  
Date: February 7, 2026
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
import joblib
import os
from datetime import datetime, timedelta
import logging
import sys

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

# Simple database import
from data_processing.database_loader import RestaurantDatabaseLoader

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/ml", tags=["ML Predictions"])

# Global model instances
xgboost_model = None
db_loader = None

# Pydantic models for requests/responses
class InventoryPredictionRequest(BaseModel):
    sku_id: str = Field(..., description="SKU ID to predict")
    lookahead_days: int = Field(7, ge=1, le=90, description="Days to forecast ahead")

class PredictionDataPoint(BaseModel):
    date: str
    actual: Optional[float] = None
    predicted: float

class InventoryPredictionResponse(BaseModel):
    sku_id: str
    predictions: List[PredictionDataPoint]
    summary: Dict[str, Any]

@router.on_event("startup")
async def load_simple_models():
    """Load simple XGBoost model on startup"""
    global xgboost_model, db_loader
    
    try:
        # Initialize database loader
        db_loader = RestaurantDatabaseLoader()
        logger.info("✅ Database loader initialized")
        
        # Load simple XGBoost model
        model_path = "/home/quentin/ugaHacks/models/xgboost_simple.pkl"
        if os.path.exists(model_path):
            xgboost_model = joblib.load(model_path)
            logger.info("✅ Simple XGBoost model loaded successfully")
        else:
            logger.warning("⚠️  Simple XGBoost model not found")
            xgboost_model = None
        
    except Exception as e:
        logger.error(f"❌ Failed to load simple models: {e}")

@router.post("/predict/inventory", response_model=InventoryPredictionResponse)
async def predict_inventory_simple(request: InventoryPredictionRequest):
    """Simple inventory prediction using XGBoost only"""
    
    if not xgboost_model or not db_loader:
        raise HTTPException(status_code=503, detail="Model not available")
    
    try:
        # Get historical data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        historical_data = db_loader.get_sku_history(
            sku_id=request.sku_id,
            start_date=start_date,
            end_date=end_date
        )
        
        if historical_data.empty:
            raise HTTPException(status_code=404, detail=f"No data found for SKU: {request.sku_id}")
        
        # Simple feature preparation
        data = historical_data.copy()
        data['date'] = pd.to_datetime(data['date'])
        data = data.sort_values('date')
        
        # Basic features
        features = pd.DataFrame({
            'covers': data['covers'].fillna(250),
            'seasonality_factor': data['seasonality_factor'].fillna(1.0),
            'inventory_start': data['inventory_start'].fillna(0),
            'on_order_qty': data['on_order_qty'].fillna(0),
            'avg_daily_usage_7d': data['avg_daily_usage_7d'].fillna(0),
            'avg_daily_usage_28d': data['avg_daily_usage_28d'].fillna(0),
            'shelf_life_days': data['shelf_life_days'].fillna(30),
            'unit_cost': data['unit_cost'].fillna(1.0),
            'is_holiday': data['is_holiday'].fillna(0),
            'lead_time_days': data['lead_time_days'].fillna(2),
            'day_of_week': data['date'].dt.dayofweek,
            'month': data['date'].dt.month,
            'day_of_month': data['date'].dt.day,
            'is_weekend': (data['date'].dt.dayofweek >= 5).astype(int)
        })
        
        # Add lag features
        features['qty_used_lag_1'] = data['qty_used'].shift(1).fillna(0)
        features['qty_used_lag_7'] = data['qty_used'].shift(7).fillna(0)
        features['qty_used_lag_14'] = data['qty_used'].shift(14).fillna(0)
        
        # Add rolling features
        features['qty_used_roll_3d'] = data['qty_used'].rolling(3).mean().fillna(0)
        features['qty_used_roll_7d'] = data['qty_used'].rolling(7).mean().fillna(0)
        
        # Use latest features for prediction
        if len(features) > 0:
            latest_features = features.iloc[-1:].fillna(0)
            
            # Make predictions for future days
            predictions = []
            base_date = datetime.now().date()
            
            for i in range(request.lookahead_days):
                prediction_date = base_date + timedelta(days=i+1)
                
                # Simple prediction
                try:
                    pred_value = float(xgboost_model.predict(latest_features)[0])
                    pred_value = max(0, pred_value)  # Ensure non-negative
                except Exception as e:
                    logger.error(f"Prediction error: {e}")
                    pred_value = float(np.mean(data['qty_used'].fillna(0).tail(7)))  # Fallback to average
                
                predictions.append(PredictionDataPoint(
                    date=prediction_date.strftime("%Y-%m-%d"),
                    predicted=pred_value
                ))
            
            # Add historical data
            for _, row in data.tail(7).iterrows():
                hist_date = pd.to_datetime(row['date']).date()
                predictions.insert(0, PredictionDataPoint(
                    date=hist_date.strftime("%Y-%m-%d"),
                    actual=float(row['qty_used']) if pd.notna(row['qty_used']) else 0.0
                ))
            
            # Sort by date
            predictions.sort(key=lambda x: x.date)
            
            # Summary
            future_preds = [p.predicted for p in predictions if p.predicted is not None]
            summary = {
                "total_predicted_consumption": float(np.sum(future_preds)),
                "avg_daily_consumption": float(np.mean(future_preds)) if future_preds else 0.0,
                "forecast_horizon_days": request.lookahead_days,
                "model_type": "XGBoost Simple"
            }
            
            return InventoryPredictionResponse(
                sku_id=request.sku_id,
                predictions=predictions,
                summary=summary
            )
        else:
            raise HTTPException(status_code=422, detail="Could not prepare features")
            
    except Exception as e:
        logger.error(f"Prediction error for SKU {request.sku_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@router.get("/health")
async def simple_ml_health():
    """Simple health check"""
    return {
        "status": "healthy" if (xgboost_model is not None and db_loader is not None) else "degraded",
        "timestamp": datetime.now().isoformat(),
        "model_loaded": xgboost_model is not None,
        "database_connected": db_loader is not None,
        "model_type": "XGBoost Simple"
    }

@router.get("/skus")
async def get_simple_skus(limit: int = 10):
    """Get available SKUs"""
    if not db_loader:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    try:
        skus = db_loader.get_available_skus(limit=limit)
        return {"skus": skus, "count": len(skus)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch SKUs: {str(e)}")