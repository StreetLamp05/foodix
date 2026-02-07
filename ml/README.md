# 🏪 Restaurant Inventory Restock API

AI-powered restaurant inventory management and restock recommendation system built with FastAPI and XGBoost.

## 🚀 Features

- **AI-Powered Predictions**: XGBoost model with 99.5% accuracy for inventory forecasting
- **Restaurant Industry Focused**: Category-aware recommendations (Produce, Protein, Dairy, etc.)
- **Real-time API**: FastAPI-based REST endpoints with <50ms response times
- **Web Interface**: Interactive HTML/JavaScript dashboard for testing
- **Shelf Life Management**: Category-specific spoilage prevention and delivery scheduling
- **Priority Classification**: CRITICAL/HIGH/MEDIUM/LOW recommendations with uncertainty quantification
- **HTTPS Ready**: Cloudflare Tunnel integration for global access

## 📊 Model Performance

- **Accuracy**: R² = 0.9952 (99.52%)
- **Speed**: ~45ms single predictions, ~108ms bulk analysis
- **Reliability**: Handles heteroscedasticity with Log1p transformations and Poisson regression
- **Business Ready**: Category-specific ordering cycles and waste prevention

## 🛠️ Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the API Server
```bash
cd src/
python3 restaurant_api.py
```

### 3. Test the API
```bash
cd tests/
python3 test_api.py
```

### 4. Access Web Interface
- **Local**: http://localhost:8001/
- **API Docs**: http://localhost:8001/docs

## 📡 API Endpoints

### Core Endpoints
- `GET /ping` - Simple connectivity test
- `GET /health` - API status and model health
- `GET /categories` - Ingredient category information
- `POST /restock/predict-single` - Single ingredient prediction
- `POST /restock/recommendations` - Bulk inventory analysis

### Example Usage
```bash
curl -X POST "http://localhost:8001/restock/predict-single" \
     -H "Content-Type: application/json" \
     -d '{
       "ingredient_id": "CHICKEN_001",
       "ingredient_name": "Chicken Breast",
       "inventory_start": 50.0,
       "qty_used": 12.5,
       "covers": 150
     }'
```

## 🏗️ Project Structure

```
restaurant-inventory-api/
├── src/
│   ├── restaurant_api.py                    # FastAPI server
│   ├── restaurant_restock_system.py         # Production ML system  
│   ├── train_all_models.sh                  # Complete training pipeline
│   ├── models/                              # Model implementations
│   │   ├── enhanced_inventory.py            # Enhanced models
│   │   └── predict.py                       # Prediction utilities
│   ├── training/                            # Training scripts
│   │   ├── inventory_forecasting.py         # Original ensemble
│   │   ├── xgboost_only_forecasting.py      # XGBoost benchmark
│   │   ├── single_gpu_training.py           # GPU training
│   │   └── quick_train.py                   # Fast training
│   ├── data_processing/                     # Data utilities
│   │   └── data_fixer.py                    # Data cleaning
│   ├── data/                                # Training datasets
│   │   ├── restaurant_inventory.csv         # Main dataset (50k+ records)
│   │   ├── restaurant_daily_agg.csv         # Daily aggregates
│   │   └── top_ingredients.csv              # Common ingredients
│   └── static/
│       └── index.html                       # Web interface
├── tests/
│   └── test_api.py                          # API test suite
├── examples/
│   └── api_examples.sh                      # cURL examples
├── docs/
│   ├── ML_BACKEND.md                        # ML documentation
│   ├── CLOUDFLARE_SETUP.md                  # Deployment guide
│   └── GITHUB_INTEGRATION.md                # Repo integration
├── README.md                                # Main documentation
├── requirements.txt                         # Dependencies
└── setup.sh                                # One-click setup
```

## 🧠 ML Model Details

- **Algorithm**: XGBoost with Poisson regression objective
- **Features**: Inventory levels, usage patterns, seasonality, covers, lead times
- **Target**: Daily inventory consumption with Log1p transformation
- **Categories**: Produce (5d shelf life), Protein (4d), Dairy (10d), Non-perishable (90d), Alcohol/Dry (365d)

### Complete ML Backend Included

- **Production System**: `src/restaurant_restock_system.py` (main model)
- **Training Pipeline**: Multiple model variants for comparison
- **Data Processing**: Automated cleaning and feature engineering
- **Model Evolution**: From LSTM+XGBoost ensemble to optimized XGBoost-only
- **Experiment Tracking**: Performance monitoring and residual analysis

See [docs/ML_BACKEND.md](docs/ML_BACKEND.md) for detailed ML documentation.

## 🌐 Deployment

### Local Development
```bash
# Quick setup (trains production model and starts API)
./setup.sh

# Or train all model variants for comparison
cd src/
./train_all_models.sh
python3 restaurant_api.py
```

### Production (with Cloudflare Tunnel)
See [docs/CLOUDFLARE_SETUP.md](docs/CLOUDFLARE_SETUP.md) for HTTPS deployment guide.

## 🔧 Integration

The API can be integrated into:
- Restaurant POS Systems
- Inventory Management Dashboards
- Mobile Apps for Kitchen Staff
- Supply Chain Management Platforms
- Business Intelligence Tools

## 📈 Business Impact

- **Reduce Food Waste**: Prevent spoilage with predictive restocking
- **Optimize Inventory**: Right-sized orders based on demand patterns
- **Save Costs**: Automated ordering reduces over-purchasing
- **Improve Efficiency**: Staff focus on cooking, not inventory management

## 🧪 Testing

Run the comprehensive test suite:
```bash
cd tests/
python3 test_api.py
```

Or test with cURL:
```bash
cd examples/
./api_examples.sh
```

## 📝 License

Built for UGA Hacks 2026 - Open source for restaurant industry innovation.

---

**Built with ❤️ for restaurant operators who want to focus on great food, not inventory headaches.**