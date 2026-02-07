"""
ML Endpoints for Restaurant Inventory System
FastAPI router for serving trained ensemble models

Author: Generated for UGA Hacks  
Date: February 7, 2026
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import xgboost as xgb
import joblib
import os
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

# Import existing modules
import sys
import os
sys.path.append(os.path.dirname(__file__))

try:
    from .data_processing.database_loader import RestaurantDatabaseLoader
    from .training.inventory_forecasting import (
        StackedEnsemble, 
        ModelConfig, 
        LSTMModel, 
        ModelA_XGBoost,  # Import the XGBoost class for pickle loading
        ModelB_LSTM      # Import the LSTM class for pickle loading
    )
    from .models.predict import InventoryPredictor
except ImportError:
    # Fallback to absolute imports
    from data_processing.database_loader import RestaurantDatabaseLoader
    from training.inventory_forecasting import (
        StackedEnsemble, 
        ModelConfig, 
        LSTMModel, 
        ModelA_XGBoost,  # Import the XGBoost class for pickle loading
        ModelB_LSTM      # Import the LSTM class for pickle loading
    )
    from models.predict import InventoryPredictor

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/ml", tags=["ML Predictions"])

# Global model instances
ensemble_predictor = None
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
    """Load ensemble models on startup"""
    global ensemble_predictor, db_loader
    
    try:
        # Import all model classes first to ensure they're available for pickle loading
        from training.inventory_forecasting import ModelA_XGBoost, ModelB_LSTM
        
        # Initialize database loader
        db_loader = RestaurantDatabaseLoader()
        logger.info("✅ Database loader initialized")
        
        # Initialize and load ensemble predictor
        ensemble_predictor = InventoryPredictor()
        ensemble_predictor.load_ensemble()
        logger.info("✅ Ensemble models loaded successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to load ML models: {e}")
        # Don't raise here - let the service start but with degraded functionality
        logger.warning("⚠️  ML services will be unavailable")

class EnsembleInference:
    """Handles ensemble model inference with VRAM optimization"""
    
    @staticmethod
    @torch.inference_mode()  # Optimize VRAM usage for RTX 3080
    def predict_with_ensemble(tabular_features: np.ndarray, 
                            time_series_data: np.ndarray,
                            ensemble: StackedEnsemble,
                            forecast_days: int = 7) -> np.ndarray:
        """Make predictions using loaded ensemble with VRAM optimization"""
        
        # XGBoost predictions (CPU/RTX 3060)
        xgb_pred = ensemble.xgb_model.model.predict(tabular_features)
        
        # LSTM predictions (RTX 3080 with inference mode)
        device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
        ensemble.lstm_model.model.to(device)
        ensemble.lstm_model.model.eval()
        
        # Convert to tensor and predict
        ts_tensor = torch.FloatTensor(time_series_data).to(device)
        
        # Handle batch dimension
        if len(ts_tensor.shape) == 2:
            ts_tensor = ts_tensor.unsqueeze(0)
            
        lstm_pred = ensemble.lstm_model.model(ts_tensor).cpu().numpy()
        
        # Meta-model combination
        expert_features = np.column_stack([xgb_pred.flatten(), lstm_pred.flatten()])
        final_pred = ensemble.meta_model.predict(expert_features)
        
        # Generate forecast sequence
        forecast = []
        current_pred = final_pred[0] if len(final_pred) > 0 else 0
        
        for i in range(forecast_days):
            # Simple linear decay for multi-step forecasting
            decay_factor = 1.0 - (i * 0.02)  # 2% decay per day
            forecast.append(max(0, current_pred * decay_factor))
            
        return np.array(forecast)

@router.post("/predict/inventory", response_model=InventoryPredictionResponse)
async def predict_inventory(request: InventoryPredictionRequest):
    """
    Predict inventory consumption for given SKU
    Fetches last 30 days of history and applies ensemble forecasting
    """
    if not ensemble_predictor or not db_loader:
        raise HTTPException(status_code=503, detail="Models not loaded")
    
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
        
        # Prepare data for ensemble prediction
        tabular_features, time_series_data, _ = ensemble_predictor.ensemble.prepare_data(
            historical_data
        )
        
        # Apply target scaling (log1p transformation as per training)
        target_values = historical_data['qty_consumed'].values
        scaled_targets = np.log1p(np.maximum(target_values, 0))
        
        # Make predictions using ensemble
        predictions = EnsembleInference.predict_with_ensemble(
            tabular_features=tabular_features,
            time_series_data=time_series_data,
            ensemble=ensemble_predictor.ensemble,
            forecast_days=request.lookahead_days
        )
        
        # Inverse transform predictions (expm1 to reverse log1p)
        predictions = np.expm1(predictions)
        predictions = np.maximum(predictions, 0)  # Ensure non-negative
        
        # Format response for Recharts
        prediction_data = []
        base_date = datetime.now().date()
        
        for i, pred_value in enumerate(predictions):
            prediction_date = base_date + timedelta(days=i+1)
            prediction_data.append(PredictionDataPoint(
                date=prediction_date.strftime("%Y-%m-%d"),
                predicted=float(pred_value),
                actual=None,  # Future dates have no actual values
                confidence_low=float(pred_value * 0.85),  # Simple confidence bands
                confidence_high=float(pred_value * 1.15)
            ))
        
        # Add recent historical data for context
        for i, (_, row) in enumerate(historical_data.tail(7).iterrows()):
            hist_date = pd.to_datetime(row['date']).date()
            prediction_data.insert(i, PredictionDataPoint(
                date=hist_date.strftime("%Y-%m-%d"),
                actual=float(row['qty_consumed']),
                predicted=None  # Historical dates have actual but no prediction
            ))
        
        # Sort by date
        prediction_data.sort(key=lambda x: x.date)
        
        # Calculate summary metrics
        total_predicted_consumption = float(np.sum(predictions))
        avg_daily_consumption = float(np.mean(predictions))
        peak_consumption_day = int(np.argmax(predictions) + 1)
        
        summary = {
            "total_predicted_consumption": total_predicted_consumption,
            "avg_daily_consumption": avg_daily_consumption,
            "peak_consumption_day": peak_consumption_day,
            "forecast_horizon_days": request.lookahead_days,
            "historical_avg": float(np.mean(target_values[-7:])) if len(target_values) >= 7 else 0.0
        }
        
        return InventoryPredictionResponse(
            sku_id=request.sku_id,
            predictions=prediction_data,
            summary=summary
        )
        
    except Exception as e:
        logger.error(f"Prediction error for SKU {request.sku_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@router.get("/analytics/optimization/{sku_id}")
async def get_optimization_analytics(
    sku_id: str,
    optimization: OptimizationRequest
):
    """
    Get optimization analytics including runout date, waste risk, and action suggestions
    """
    if not ensemble_predictor:
        raise HTTPException(status_code=503, detail="Models not loaded")
    
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
        current_stock = optimization.current_stock
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
        
        if optimization.perish_date:
            perish_datetime = datetime.strptime(optimization.perish_date, "%Y-%m-%d").date()
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
            safety_buffer=optimization.safety_buffer_days
        )
        
        # Additional details
        details = {
            "current_stock": current_stock,
            "predicted_30_day_consumption": total_predicted_consumption,
            "avg_daily_consumption": float(np.mean(predictions)),
            "days_until_runout": days_until_runout,
            "stock_coverage_days": int(current_stock / np.mean(predictions)) if np.mean(predictions) > 0 else 999,
            "perish_date": optimization.perish_date,
            "safety_buffer_days": optimization.safety_buffer_days
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

def _generate_action_suggestion(days_until_runout: Optional[int], 
                              waste_risk: bool,
                              current_stock: float,
                              avg_daily_consumption: float,
                              safety_buffer: int) -> str:
    """Generate action suggestions based on analysis"""
    
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
    """Health check for ML services"""
    
    model_status = {
        "ensemble_loaded": ensemble_predictor is not None and ensemble_predictor.is_loaded,
        "database_connected": db_loader is not None,
        "gpu_available": torch.cuda.is_available(),
        "gpu_count": torch.cuda.device_count() if torch.cuda.is_available() else 0
    }
    
    if torch.cuda.is_available():
        model_status["gpu_memory"] = {
            f"cuda:{i}": {
                "allocated_mb": torch.cuda.memory_allocated(i) / 1024**2,
                "reserved_mb": torch.cuda.memory_reserved(i) / 1024**2
            }
            for i in range(torch.cuda.device_count())
        }
    
    return {
        "status": "healthy" if all([model_status["ensemble_loaded"], model_status["database_connected"]]) else "degraded",
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