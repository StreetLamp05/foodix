# Cleaned Restaurant ML Backend

This is the streamlined version of the restaurant ML backend that focuses only on the core workflow:

**Ingest → Normalize → Train XGBoost → Predict**

## Essential Files

### Core ML Pipeline
- **`train_simple_xgboost.py`** - XGBoost model training using database data
- **`ml_simple.py`** - Simple ML endpoints for predictions
- **`restaurant_api.py`** - Main FastAPI application with database connectivity
- **`data_processing/database_loader.py`** - Data ingestion and normalization from PostgreSQL

### Configuration & Data
- **`requirements.txt`** - Python dependencies 
- **`setup.sh`** - Environment setup script
- **`data/`** - CSV data files for backup/testing
- **`venv/`** - Python virtual environment (excluded from archive)

### Testing & Operations  
- **`start_ml_api.sh`** - Start the ML API server
- **`test_endpoints.sh`** - Test the API endpoints
- **`test_ml_api.py`** - Python-based API testing

## Usage

1. **Setup**: `./setup.sh`
2. **Train Model**: `python train_simple_xgboost.py`
3. **Start API**: `./start_ml_api.sh`
4. **Test**: `./test_endpoints.sh`

## Model Performance

- **XGBoost Model**: 81.7% R² accuracy on test data
- **Training Time**: ~1.46 seconds
- **Features**: Uses lag features and rolling averages for time series prediction

## API Endpoints

- `POST /predict/inventory` - Predict inventory levels
- `GET /health` - Health check
- `GET /available_skus` - List available SKUs

## Archived Components

All complex ensemble models, LSTM components, and non-essential files have been moved to the `archive/` directory:
- Complex ensemble training scripts
- LSTM model implementations  
- Alternative API implementations
- Documentation and examples
- Static files and backups

The archived components are preserved but not needed for the core ML pipeline.