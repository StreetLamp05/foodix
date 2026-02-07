#!/bin/bash

# Complete ML Backend Training Script
# Trains all model variants and saves them for comparison

echo "🧠 Restaurant Inventory ML Backend - Complete Training"
echo "===================================================="

# Create necessary directories
mkdir -p models logs plots

# Set up Python environment
echo "📦 Setting up environment..."
if [ ! -d "../../inventory_env" ]; then
    echo "Virtual environment not found. Please run from the restaurant-inventory-api folder."
    echo "Expected path: ../inventory_env"
fi

# Train all model variants
echo ""
echo "🔬 Training Model Variants..."

echo "1️⃣ Training Quick Model (Fast baseline)..."
python3 training/quick_train.py > logs/quick_train.log 2>&1

echo "2️⃣ Training XGBoost-only Model (Clean benchmark)..."  
python3 training/xgboost_only_forecasting.py > logs/xgboost_only.log 2>&1

echo "3️⃣ Training Production Restaurant System (Main model)..."
python3 restaurant_restock_system.py > logs/production_system.log 2>&1

echo "4️⃣ Training Original Ensemble (Research comparison)..."
python3 training/inventory_forecasting.py > logs/ensemble.log 2>&1

echo ""
echo "📊 Training Complete! Results:"
echo "=========================="

# Check if models were created
if [ -f "models/restaurant_restock_model.pkl" ]; then
    echo "✅ Production model: models/restaurant_restock_model.pkl"
else
    echo "❌ Production model failed to train"
fi

# Show log summaries
echo ""
echo "📈 Performance Summary:"
echo "----------------------"

# Extract R² scores from logs if available
if [ -f "logs/production_system.log" ]; then
    echo "🏭 Production System:"
    grep -E "(test_r2|Test RMSE)" logs/production_system.log | tail -2 || echo "   Logs not yet available"
fi

if [ -f "logs/xgboost_only.log" ]; then
    echo "📊 XGBoost Benchmark:"  
    grep -E "(test_r2|Test RMSE)" logs/xgboost_only.log | tail -2 || echo "   Logs not yet available"
fi

echo ""
echo "🎯 Next Steps:"
echo "============="
echo "1. Start the API server:"
echo "   python3 restaurant_api.py"
echo ""
echo "2. Test the API:"
echo "   cd ../tests && python3 test_api.py"
echo ""
echo "3. View logs for detailed results:"
echo "   cat logs/production_system.log"
echo ""
echo "4. Check generated plots:"
echo "   ls -la *.png"

echo ""
echo "🚀 Training pipeline complete!"