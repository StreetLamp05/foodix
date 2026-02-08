# ML Endpoints for Restaurant Inventory System

## Overview

The `ml_endpoints.py` module provides FastAPI endpoints for serving your trained ensemble model (XGBoost + LSTM + Meta-Model) with optimized inference and comprehensive analytics.

## Key Features

### 🤖 Ensemble Model Serving
- **GPU-Optimized Inference**: Uses `@torch.inference_mode()` for efficient VRAM usage on RTX 3080
- **Multi-GPU Support**: XGBoost on RTX 3060, LSTM on RTX 3080  
- **Automatic Model Loading**: Models loaded from `/home/quentin/ugaHacks/models` on startup

### 📊 Prediction Endpoints

#### `POST /ml/predict/inventory`
Predict inventory consumption for a specific SKU.

**Request:**
```json
{
  "sku_id": "ingredient_123",
  "lookahead_days": 7,
  "current_stock": 100.0
}
```

**Response:**
```json
{
  "sku_id": "ingredient_123",
  "predictions": [
    {
      "date": "2026-02-08",
      "actual": 12.5,
      "predicted": null
    },
    {
      "date": "2026-02-09", 
      "actual": null,
      "predicted": 11.8,
      "confidence_low": 10.0,
      "confidence_high": 13.6
    }
  ],
  "summary": {
    "total_predicted_consumption": 78.4,
    "avg_daily_consumption": 11.2,
    "peak_consumption_day": 3,
    "forecast_horizon_days": 7
  }
}
```

#### `GET /ml/analytics/optimization/{sku_id}`
Get optimization analytics and action recommendations.

**Query Parameters:**
- `current_stock`: Current inventory level
- `perish_date`: Product expiry date (YYYY-MM-DD)
- `safety_buffer_days`: Safety buffer for reordering

**Response:**
```json
{
  "sku_id": "ingredient_123",
  "runout_date": "2026-02-15",
  "waste_risk": false,
  "suggested_action": "Reorder soon - approaching reorder point",
  "details": {
    "current_stock": 50.0,
    "predicted_30_day_consumption": 180.5,
    "days_until_runout": 7,
    "stock_coverage_days": 4
  }
}
```

### 🔧 Utility Endpoints

#### `GET /ml/health`
Health check for ML services including GPU memory status.

#### `GET /ml/skus?limit=100`
Get list of available SKUs with recent activity.

## Data Integration

### Database Integration
- **PostgreSQL Connection**: Direct integration with inventory database
- **Historical Data**: Automatically fetches last 30 days for predictions
- **Real-time Data**: Uses latest inventory snapshots

### Data Preprocessing  
- **Target Scaling**: Applies log1p transformation as per training
- **Feature Engineering**: Adds derived features from database
- **Time Series Formatting**: Properly formats data for LSTM input

## Optimization Logic

### Runout Prediction
- Calculates when current stock will be depleted
- Accounts for predicted daily consumption patterns
- Provides early warning for stockouts

### Waste Risk Assessment
- Compares predicted consumption vs current stock
- Considers product perish dates
- Flags items at risk of spoilage

### Action Recommendations
- **"Run a special"**: High waste risk detected
- **"Reorder now"**: Critical stock level
- **"Reorder soon"**: Approaching reorder point  
- **"Increase safety buffer"**: Excess inventory detected
- **"Monitor closely"**: Normal stock levels

## Response Format

All prediction responses are formatted for **Recharts** compatibility:
- Array of objects with `{ date, actual, predicted }` structure
- Historical data includes `actual` values
- Future predictions include `predicted` values with confidence bands
- Dates in ISO format (YYYY-MM-DD)

## Performance Optimizations

### GPU Memory Management
- `@torch.inference_mode()` context for inference
- Automatic model device management
- Memory-efficient batch processing

### Database Efficiency  
- Optimized queries with proper indexing
- Configurable data fetch limits
- Connection pooling with SQLAlchemy

### Caching Strategy
- Model loaded once on startup
- Persistent database connections
- Efficient feature computation

## Quick Start

1. **Start the API Server:**
   ```bash
   ./start_ml_api.sh
   ```

2. **Test the Endpoints:**
   ```bash
   python test_ml_endpoints.py
   ```

3. **View API Documentation:**
   Visit `http://localhost:8000/docs` for interactive API docs

4. **Check ML Health:**
   ```bash
   curl http://localhost:8000/ml/health
   ```

## Example Usage

```python
import requests

# Get available SKUs
response = requests.get("http://localhost:8000/ml/skus?limit=10")
skus = response.json()["skus"]

# Predict inventory for first SKU
prediction_request = {
    "sku_id": skus[0],
    "lookahead_days": 14,
    "current_stock": 75.0
}

prediction = requests.post(
    "http://localhost:8000/ml/predict/inventory", 
    json=prediction_request
)

# Get optimization analytics  
optimization = requests.get(
    f"http://localhost:8000/ml/analytics/optimization/{skus[0]}",
    params={
        "current_stock": 75.0,
        "perish_date": "2026-02-20",
        "safety_buffer_days": 3
    }
)
```

## Error Handling

The API provides comprehensive error handling:
- **404**: SKU not found or no historical data
- **422**: Invalid request parameters  
- **500**: Model inference errors
- **503**: Models not loaded or database unavailable

All errors include detailed messages for debugging.

## Architecture Notes

### Model Loading
- Models loaded from `/home/quentin/ugaHacks/models`
- Automatic ensemble reconstruction
- Graceful fallback for missing models

### Multi-GPU Setup
- XGBoost: GPU 1 (RTX 3060) for tabular features
- LSTM: GPU 0 (RTX 3080) for time series  
- Meta-model: CPU for final combination

### Data Flow
1. **Request** → SKU ID + parameters
2. **Database** → Fetch 30-day history  
3. **Preprocessing** → Scale and format data
4. **Inference** → XGBoost + LSTM predictions
5. **Meta-model** → Combine expert outputs
6. **Response** → Recharts-formatted predictions

This architecture provides production-ready ML serving with optimal performance for your ensemble model setup.