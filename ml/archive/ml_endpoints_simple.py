"""
Simplified ML Endpoints - XGBoost Only
FastAPI router for serving XGBoost-only predictions

Author: Generated for UGA Hacks  
Date: February 7, 2026
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
import os
from datetime import datetime, timedelta
import logging

# Import existing modules
import sys
sys.path.append(os.path.dirname(__file__))

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
    current_stock: Optional[float] = Field(None, description="Current stock level")

class OptimizationRequest(BaseModel):
    current_stock: float = Field(..., description="Current stock level")
    perish_date: Optional[str] = Field(None, description="Product expiry date (YYYY-MM-DD)")
    safety_buffer_days: int = Field(3, description="Safety buffer for reordering")

class PredictionDataPoint(BaseModel):
    date: str
    actual: Optional[float] = None
    predicted: float
    confidence_low: Optional[float] = None
    confidence_high: Optional[float] = None

class InventoryPredictionResponse(BaseModel):
    sku_id: str
    predictions: List[PredictionDataPoint]
    summary: Dict[str, Any]

class OptimizationResponse(BaseModel):
    sku_id: str
    runout_date: Optional[str]
    waste_risk: bool
    suggested_action: str
    details: Dict[str, Any]

@router.on_event("startup")
async def load_ml_models():
    """Load XGBoost model on startup"""
    global xgboost_model, db_loader
    
    try:
        # Initialize database loader
        db_loader = RestaurantDatabaseLoader()
        logger.info("✅ Database loader initialized")
        
        # Load XGBoost model
        model_path = "/home/quentin/ugaHacks/models/xgboost_simple.pkl"
        if os.path.exists(model_path):
            xgboost_model = joblib.load(model_path)
            logger.info("✅ Simple XGBoost model loaded successfully")
        else:
            logger.warning("⚠️  Simple XGBoost model not found, will use fallback")
            xgboost_model = None
        
    except Exception as e:
        logger.error(f"❌ Failed to load ML models: {e}")
        logger.warning("⚠️  ML services will be unavailable")

@router.post("/predict/inventory", response_model=InventoryPredictionResponse)
async def predict_inventory(request: InventoryPredictionRequest):
    """
    Predict inventory consumption for given SKU using XGBoost only
    """
    if not xgboost_model or not db_loader:
        raise HTTPException(status_code=503, detail="XGBoost model not loaded")
    
    try:
        # Fetch historical data for the SKU (last 30 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Get SKU history from database
        historical_data = db_loader.get_sku_history(
            sku_id=request.sku_id,
            start_date=start_date,
            end_date=end_date
        )
        
        if historical_data.empty:
            raise HTTPException(
                status_code=404, 
                detail=f"No historical data found for SKU: {request.sku_id}"
            )
        
        # Prepare features for XGBoost
        features = prepare_xgboost_features(historical_data)
        
        if features.empty:
            raise HTTPException(
                status_code=422, 
                detail=f"Could not prepare features for SKU: {request.sku_id}"
            )
        
        # Make predictions
        predictions = []
        base_date = datetime.now().date()
        
        # Use the latest features as base for predictions
        base_features = features.iloc[-1:].copy()
        
        for i in range(request.lookahead_days):
            prediction_date = base_date + timedelta(days=i+1)
            
            # Adjust time-based features for future prediction
            adjusted_features = base_features.copy()
            
            # Make prediction
            pred_value = float(xgboost_model.predict(adjusted_features)[0])
            pred_value = max(0, pred_value)  # Ensure non-negative
            
            predictions.append(PredictionDataPoint(
                date=prediction_date.strftime("%Y-%m-%d"),
                predicted=pred_value,
                actual=None,
                confidence_low=pred_value * 0.85,  # Simple confidence bands
                confidence_high=pred_value * 1.15
            ))
        
        # Add recent historical data for context
        for i, (_, row) in enumerate(historical_data.tail(7).iterrows()):
            hist_date = pd.to_datetime(row['date']).date()
            predictions.insert(i, PredictionDataPoint(
                date=hist_date.strftime("%Y-%m-%d"),
                actual=float(row['qty_consumed']) if pd.notna(row['qty_consumed']) else 0.0,
                predicted=None
            ))
        
        # Sort by date
        predictions.sort(key=lambda x: x.date)
        
        # Calculate summary metrics
        future_predictions = [p.predicted for p in predictions if p.predicted is not None]
        total_predicted_consumption = float(np.sum(future_predictions))
        avg_daily_consumption = float(np.mean(future_predictions))
        peak_consumption_day = int(np.argmax(future_predictions) + 1) if future_predictions else 0
        
        summary = {
            "total_predicted_consumption": total_predicted_consumption,
            "avg_daily_consumption": avg_daily_consumption,
            "peak_consumption_day": peak_consumption_day,
            "forecast_horizon_days": request.lookahead_days,
            "model_type": "XGBoost",
            "historical_avg": float(np.mean(historical_data['qty_consumed'].fillna(0).tail(7)))
        }
        
        return InventoryPredictionResponse(
            sku_id=request.sku_id,
            predictions=predictions,
            summary=summary
        )
        
    except Exception as e:
        logger.error(f"Prediction error for SKU {request.sku_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@router.get("/analytics/optimization/{sku_id}")
async def get_optimization_analytics(
    sku_id: str,
    current_stock: float,
    perish_date: Optional[str] = None,
    safety_buffer_days: int = 3
):
    """Get optimization analytics using XGBoost predictions"""
    
    if not xgboost_model:
        raise HTTPException(status_code=503, detail="XGBoost model not loaded")
    
    try:
        # Get predictions for the SKU
        prediction_request = InventoryPredictionRequest(
            sku_id=sku_id,
            lookahead_days=30  # Look ahead 30 days for optimization
        )
        
        prediction_response = await predict_inventory(prediction_request)
        predictions = [p.predicted for p in prediction_response.predictions if p.predicted is not None]
        
        if not predictions:
            raise HTTPException(status_code=404, detail="No predictions available")
        
        # Calculate runout date
        cumulative_consumption = 0
        runout_date = None
        
        for i, daily_consumption in enumerate(predictions):
            cumulative_consumption += daily_consumption
            if cumulative_consumption >= current_stock:
                runout_date = (datetime.now().date() + timedelta(days=i+1)).strftime("%Y-%m-%d")
                break
        
        # Calculate waste risk
        total_predicted_consumption = sum(predictions)
        waste_risk = False
        
        if perish_date:
            perish_datetime = datetime.strptime(perish_date, "%Y-%m-%d").date()
            days_to_perish = (perish_datetime - datetime.now().date()).days
            
            if days_to_perish > 0:
                consumption_until_perish = sum(predictions[:days_to_perish])
                waste_risk = consumption_until_perish < current_stock
        
        # Generate suggested action
        days_until_runout = None
        if runout_date:
            runout_datetime = datetime.strptime(runout_date, "%Y-%m-%d").date()
            days_until_runout = (runout_datetime - datetime.now().date()).days
        
        suggested_action = _generate_action_suggestion(
            days_until_runout=days_until_runout,
            waste_risk=waste_risk,
            current_stock=current_stock,
            avg_daily_consumption=np.mean(predictions),
            safety_buffer=safety_buffer_days
        )
        
        # Additional details
        details = {
            "current_stock": current_stock,
            "predicted_30_day_consumption": total_predicted_consumption,
            "avg_daily_consumption": float(np.mean(predictions)),
            "days_until_runout": days_until_runout,
            "stock_coverage_days": int(current_stock / np.mean(predictions)) if np.mean(predictions) > 0 else 999,
            "perish_date": perish_date,
            "safety_buffer_days": safety_buffer_days,
            "model_type": "XGBoost"
        }
        
        return OptimizationResponse(
            sku_id=sku_id,
            runout_date=runout_date,
            waste_risk=waste_risk,
            suggested_action=suggested_action,
            details=details
        )
        
    except Exception as e:
        logger.error(f"Optimization error for SKU {sku_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Optimization analysis failed: {str(e)}")

def prepare_xgboost_features(data: pd.DataFrame) -> pd.DataFrame:
    """Prepare features for XGBoost prediction"""
    
    if data.empty:
        return pd.DataFrame()
    
    # Sort by date
    data = data.sort_values('date').copy()
    
    # Basic features that should exist in our database
    feature_cols = [
        'covers', 'seasonality_factor', 'inventory_start', 'qty_used',
        'on_order_qty', 'avg_daily_usage_7d', 'avg_daily_usage_28d',
        'shelf_life_days', 'unit_cost', 'is_holiday', 'lead_time_days'
    ]
    
    # Add derived features
    data['day_of_week'] = pd.to_datetime(data['date']).dt.dayofweek
    data['month'] = pd.to_datetime(data['date']).dt.month
    data['day_of_month'] = pd.to_datetime(data['date']).dt.day
    
    # Add lag features
    for lag in [1, 7, 14]:
        data[f'qty_used_lag_{lag}'] = data['qty_used'].shift(lag)
    
    # Add rolling averages
    data['qty_used_roll_3d'] = data['qty_used'].rolling(3).mean()
    data['qty_used_roll_7d'] = data['qty_used'].rolling(7).mean()
    
    # Select available features
    available_cols = [col for col in feature_cols + ['day_of_week', 'month', 'day_of_month'] 
                     if col in data.columns]
    
    # Add lag and rolling features if they exist
    for col in data.columns:
        if col.startswith(('qty_used_lag_', 'qty_used_roll_')):
            available_cols.append(col)
    
    # Return feature matrix
    features = data[available_cols].fillna(0)
    return features

def _generate_action_suggestion(days_until_runout: Optional[int], 
                              waste_risk: bool,
                              current_stock: float,
                              avg_daily_consumption: float,
                              safety_buffer: int) -> str:
    """Generate action suggestions based on XGBoost predictions"""
    
    if waste_risk:
        return "Run a special - high waste risk detected before expiry"
    
    if days_until_runout is None:
        return "Stock appears sufficient - monitor regularly"
    
    if days_until_runout <= safety_buffer:
        return "Reorder now - critical stock level"
    elif days_until_runout <= safety_buffer + 3:
        return "Reorder soon - approaching reorder point"
    elif days_until_runout >= 30:
        return "Increase safety buffer - excess inventory detected"
    else:
        return "Monitor closely - stock levels normal"

# Health check endpoint for ML services
@router.get("/health")
async def ml_health_check():
    """Health check for XGBoost ML services"""
    
    model_status = {
        "xgboost_loaded": xgboost_model is not None,
        "database_connected": db_loader is not None,
        "model_type": "XGBoost Only"
    }
    
    return {
        "status": "healthy" if all([model_status["xgboost_loaded"], model_status["database_connected"]]) else "degraded",
        "timestamp": datetime.now().isoformat(),
        "model_status": model_status
    }

# Utility endpoint to get available SKUs
@router.get("/skus")
async def get_available_skus(limit: int = 100):
    """Get list of available SKUs for prediction"""
    if not db_loader:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    try:
        available_skus = db_loader.get_available_skus(limit=limit)
        return {"skus": available_skus, "count": len(available_skus)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch SKUs: {str(e)}")