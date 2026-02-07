#!/bin/bash

# Restaurant Inventory API - Quick Setup Script
# Run this script to set up the API in any environment

echo "Setting up Restaurant Inventory API..."

# Create models directory if it doesn't exist
mkdir -p models

# Install Python dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Train the model (this will save it to models/ directory)
echo "Training ML model..."
cd src/
python3 restaurant_restock_system.py
cd ..

# Start the API server
echo "Starting API server..."
echo "Access the web interface at: http://localhost:8001/"
echo "API documentation at: http://localhost:8001/docs"
echo ""
echo "Press Ctrl+C to stop the server"

cd src/
python3 restaurant_api.py