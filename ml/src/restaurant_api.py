"""
Restaurant Inventory Restock API
FastAPI-based REST API for the restaurant restock recommendation system

Author: Generated for UGA Hacks
Date: February 7, 2026
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
import joblib
import os
import logging
from datetime import datetime, timedelta
import uvicorn

# Import our restaurant system
from restaurant_restock_system import (
    RestockRecommendationEngine, 
    XGBoostInventoryModel, 
    RestockRecommendation,
    IngredientCategory,
    XGBoostConfig
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Restaurant Inventory Restock API",
    description="AI-powered restaurant inventory management and restock recommendations",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware for web browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Mount static files for web interface
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Global model variable
model_instance = None
restock_engine = None

# Pydantic models for API requests/responses
class IngredientData(BaseModel):
    ingredient_id: str
    ingredient_name: str
    inventory_start: float = Field(..., description="Current inventory level")
    qty_used: float = Field(default=0, description="Daily usage amount")
    on_order_qty: float = Field(default=0, description="Quantity already on order")
    lead_time_days: int = Field(default=3, description="Lead time for delivery")
    covers: int = Field(default=100, description="Daily covers/customers")
    seasonality_factor: float = Field(default=1.0, description="Seasonal demand multiplier")
    is_holiday: bool = Field(default=False, description="Is it a holiday period")
    avg_daily_usage_7d: Optional[float] = Field(None, description="7-day average usage")
    reorder_point: Optional[float] = Field(None, description="Custom reorder point")
    target_stock_level_S: Optional[float] = Field(None, description="Target stock level")

class BulkRestockRequest(BaseModel):
    ingredients: List[IngredientData] = Field(..., description="List of ingredients to analyze")
    priority_filter: Optional[List[str]] = Field(None, description="Filter by priority: CRITICAL, HIGH, MEDIUM, LOW")
    category_filter: Optional[List[str]] = Field(None, description="Filter by category")
    limit: int = Field(20, description="Maximum recommendations to return")

class RestockRecommendationResponse(BaseModel):
    ingredient_id: str
    ingredient_name: str
    category: str
    priority: str
    current_inventory: float
    predicted_inventory_end: float
    restock_needed: bool
    suggested_order_qty: float
    days_until_stockout: float
    shelf_life_days: int
    days_until_spoilage: float
    confidence_low: float
    confidence_high: float
    lead_time_days: int
    delivery_frequency_days: int
    next_delivery_window: str
    waste_risk: bool

class BulkRestockResponse(BaseModel):
    success: bool
    timestamp: str
    total_ingredients_analyzed: int
    recommendations_count: int
    summary: Dict[str, int]
    recommendations: List[RestockRecommendationResponse]
    processing_time_ms: float

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    model_loaded: bool
    model_accuracy: Optional[float] = None
    uptime_seconds: float

# Startup event to load model
@app.on_event("startup")
async def startup_event():
    """Load the trained model on startup"""
    global model_instance, restock_engine
    
    try:
        model_path = "/home/quentin/ugaHacks/models/restaurant_restock_model.pkl"
        if os.path.exists(model_path):
            model_instance = joblib.load(model_path)
            restock_engine = RestockRecommendationEngine(model_instance)
            logger.info("✅ Restaurant restock model loaded successfully")
        else:
            logger.warning("⚠️  Model file not found - training new model...")
            # Could trigger model training here
            
    except Exception as e:
        logger.error(f"❌ Failed to load model: {e}")

# Add a simple ping endpoint for basic connectivity testing
@app.get("/ping")
async def ping():
    """Simple ping endpoint for connectivity testing"""
    return {"message": "pong", "timestamp": datetime.now().isoformat()}

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    
    model_accuracy = None
    if model_instance and hasattr(model_instance, 'test_r2'):
        model_accuracy = getattr(model_instance, 'test_r2', None)
    
    return HealthResponse(
        status="healthy" if model_instance else "model_not_loaded",
        timestamp=datetime.now().isoformat(),
        model_loaded=model_instance is not None,
        model_accuracy=model_accuracy,
        uptime_seconds=0  # Could track actual uptime
    )

# Main restock recommendations endpoint
@app.post("/restock/recommendations", response_model=BulkRestockResponse)
async def get_restock_recommendations(request: BulkRestockRequest):
    """
    Get AI-powered restock recommendations for restaurant ingredients
    
    Analyzes current inventory levels and predicts optimal restocking needs
    based on usage patterns, shelf life, and category-specific ordering cycles.
    """
    
    if not model_instance or not restock_engine:
        raise HTTPException(status_code=503, detail="Model not loaded - service unavailable")
    
    start_time = datetime.now()
    
    try:
        # Convert request to DataFrame format expected by the model
        ingredient_data = []
        for ing in request.ingredients:
            # Create a data row similar to the training data format
            row = {
                'ingredient_id': ing.ingredient_id,
                'ingredient_name': ing.ingredient_name,
                'inventory_start': ing.inventory_start,
                'qty_used': ing.qty_used,
                'on_order_qty': ing.on_order_qty,
                'lead_time_days': ing.lead_time_days,
                'covers': ing.covers,
                'seasonality_factor': ing.seasonality_factor,
                'is_holiday': ing.is_holiday,
                'avg_daily_usage_7d': ing.avg_daily_usage_7d or ing.qty_used,
                'reorder_point': ing.reorder_point,
                'target_stock_level_S': ing.target_stock_level_S,
                # Add some default values for other expected columns
                'date': datetime.now().strftime('%Y-%m-%d'),
                'inventory_end': ing.inventory_start,  # Will be predicted
                'units_sold_items_using_ing': ing.covers * ing.seasonality_factor,
                'revenue_items_using_ing': ing.covers * ing.seasonality_factor * 15  # Assume $15 avg
            }
            ingredient_data.append(row)
        
        # Convert to DataFrame
        df = pd.DataFrame(ingredient_data)
        
        # Generate recommendations
        ingredient_ids = [ing.ingredient_id for ing in request.ingredients]
        recommendations = restock_engine.generate_restock_recommendations(
            df, 
            ingredient_filter=ingredient_ids
        )
        
        # Apply filters
        if request.priority_filter:
            recommendations = [r for r in recommendations if r.priority in request.priority_filter]
        
        if request.category_filter:
            recommendations = [r for r in recommendations if r.category.value in request.category_filter]
        
        # Limit results
        recommendations = recommendations[:request.limit]
        
        # Convert to response format
        response_recommendations = []
        for rec in recommendations:
            response_recommendations.append(RestockRecommendationResponse(
                ingredient_id=rec.ingredient_id,
                ingredient_name=rec.ingredient_name,
                category=rec.category.value,
                priority=rec.priority,
                current_inventory=rec.current_inventory,
                predicted_inventory_end=rec.predicted_inventory_end,
                restock_needed=rec.restock_needed,
                suggested_order_qty=rec.suggested_order_qty,
                days_until_stockout=rec.days_until_stockout,
                shelf_life_days=rec.shelf_life_days,
                days_until_spoilage=rec.days_until_spoilage,
                confidence_low=rec.confidence_low,
                confidence_high=rec.confidence_high,
                lead_time_days=rec.lead_time_days,
                delivery_frequency_days=rec.delivery_frequency_days,
                next_delivery_window=rec.next_delivery_window,
                waste_risk=rec.waste_risk
            ))
        
        # Generate summary statistics
        summary = {
            'critical': sum(1 for r in recommendations if r.priority == 'CRITICAL'),
            'high': sum(1 for r in recommendations if r.priority == 'HIGH'),
            'medium': sum(1 for r in recommendations if r.priority == 'MEDIUM'),
            'low': sum(1 for r in recommendations if r.priority == 'LOW'),
            'restock_needed': sum(1 for r in recommendations if r.restock_needed),
            'waste_risk': sum(1 for r in recommendations if r.waste_risk)
        }
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return BulkRestockResponse(
            success=True,
            timestamp=datetime.now().isoformat(),
            total_ingredients_analyzed=len(request.ingredients),
            recommendations_count=len(response_recommendations),
            summary=summary,
            recommendations=response_recommendations,
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Single ingredient prediction endpoint
@app.post("/restock/predict-single")
async def predict_single_ingredient(ingredient: IngredientData):
    """
    Get prediction for a single ingredient
    """
    
    if not model_instance:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    # Convert single ingredient to bulk format and process
    bulk_request = BulkRestockRequest(
        ingredients=[ingredient],
        limit=1
    )
    
    result = await get_restock_recommendations(bulk_request)
    
    if result.recommendations:
        return {
            "success": True,
            "recommendation": result.recommendations[0],
            "processing_time_ms": result.processing_time_ms
        }
    else:
        return {
            "success": False,
            "message": "No recommendations generated",
            "processing_time_ms": result.processing_time_ms
        }

# Categories information endpoint
@app.get("/categories")
async def get_categories():
    """
    Get information about ingredient categories and their properties
    """
    
    from restaurant_restock_system import CATEGORY_METADATA
    
    categories_info = {}
    for category, metadata in CATEGORY_METADATA.items():
        categories_info[category.value] = {
            "shelf_life_days": metadata.shelf_life_days,
            "delivery_frequency_days": metadata.delivery_frequency_days,
            "order_lead_time_days": metadata.order_lead_time_days,
            "waste_buffer_days": metadata.waste_buffer_days,
            "description": metadata.description
        }
    
    return {
        "categories": categories_info,
        "classification_keywords": {
            "produce": ["lettuce", "tomato", "onion", "pepper", "herbs", "basil"],
            "protein": ["chicken", "beef", "fish", "meat", "salmon"],
            "dairy": ["cheese", "milk", "cream", "butter", "mozzarella"],
            "non_perishable": ["rice", "pasta", "sauce", "oil", "dressing"],
            "alcohol_dry": ["wine", "beer", "spirits", "alcohol"]
        }
    }

# API documentation homepage
@app.get("/", response_class=HTMLResponse)
async def api_home():
    """
    API Homepage - serve the web interface
    """
    
    static_file = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(static_file):
        with open(static_file, 'r') as f:
            return f.read()
    
    # Fallback to simple HTML if static file not found
    html_content = """
    <html>
        <head>
            <title>Restaurant Inventory Restock API</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .header { color: #2c3e50; }
                .endpoint { background: #ecf0f1; padding: 15px; margin: 10px 0; border-radius: 5px; }
                .method { font-weight: bold; color: #27ae60; }
                code { background: #f8f9fa; padding: 2px 5px; border-radius: 3px; }
            </style>
        </head>
        <body>
            <h1 class="header">🏪 Restaurant Inventory Restock API</h1>
            <p>AI-powered restaurant inventory management and restock recommendations</p>
            
            <h2>🚀 Quick Start</h2>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/ping</code> - Simple connectivity test
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/health</code> - Check API status
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span> <code>/restock/recommendations</code> - Get bulk restock recommendations
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span> <code>/restock/predict-single</code> - Predict single ingredient
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/categories</code> - View ingredient categories
            </div>
            
            <h2>📖 Documentation</h2>
            <p>
                <a href="/docs">🔗 Interactive API Documentation (Swagger UI)</a><br>
                <a href="/redoc">🔗 Alternative Documentation (ReDoc)</a>
            </p>
            
            <h2>💡 Example Usage</h2>
            <pre><code>
curl -X POST "http://localhost:8000/restock/recommendations" \\
     -H "Content-Type: application/json" \\
     -d '{
       "ingredients": [
         {
           "ingredient_id": "CHICKEN_001",
           "ingredient_name": "Chicken Breast",
           "inventory_start": 100,
           "qty_used": 25,
           "covers": 150
         }
       ],
       "limit": 10
     }'
            </code></pre>
        </body>
    </html>
    """
    return html_content

# Run the API server
if __name__ == "__main__":
    uvicorn.run(
        "restaurant_api:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )