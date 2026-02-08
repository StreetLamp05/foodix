#!/bin/bash

echo "🚀 Starting Restaurant ML API Server"
echo "======================================"

# Set environment variables for optimal performance
export CUDA_VISIBLE_DEVICES=0,1  # Use both RTX 3080 and RTX 3060
export OMP_NUM_THREADS=4
export TORCH_HOME=/home/quentin/ugaHacks/models/torch_cache

# Create model directory if it doesn't exist
mkdir -p /home/quentin/ugaHacks/models/torch_cache

# Navigate to project root and activate venv
cd /home/quentin/hacks11-voyix/ml

echo "🔧 Environment configured:"
echo "   CUDA devices: $CUDA_VISIBLE_DEVICES"
echo "   OMP threads: $OMP_NUM_THREADS"
echo "   Torch cache: $TORCH_HOME"
echo "   Project root: $(pwd)"
echo ""

echo "🧠 Model directory: /home/quentin/ugaHacks/models"
echo ""

# Start the FastAPI server from project root, but target src/restaurant_api.py
echo "🌐 Starting FastAPI server on http://localhost:8000"
echo "📊 API docs available at: http://localhost:8000/docs"
echo "🔮 ML endpoints available at: http://localhost:8000/ml/"
echo ""

# Run with uvicorn using venv python, specifying the module path correctly
./venv/bin/uvicorn src.restaurant_api:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --workers 1 \
    --timeout-keep-alive 60 \
    --access-log \
    --log-level info