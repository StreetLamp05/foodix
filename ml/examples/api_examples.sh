#!/bin/bash

# Restaurant Inventory Restock API - cURL Examples
# This script demonstrates how to interact with the API using curl
# 
# Author: Generated for UGA Hacks
# Date: February 7, 2026

API_URL="http://localhost:8001"

echo "🏪 Restaurant Inventory Restock API - cURL Examples"
echo "=================================================="

# 1. Health Check
echo -e "\n1. 🏥 Health Check"
echo "curl -X GET $API_URL/health"
curl -X GET "$API_URL/health" | python3 -m json.tool
sleep 1

# 2. Get Categories Information  
echo -e "\n\n2. 📋 Categories Information"
echo "curl -X GET $API_URL/categories"
curl -X GET "$API_URL/categories" | python3 -m json.tool
sleep 1

# 3. Single Ingredient Prediction
echo -e "\n\n3. 🥗 Single Ingredient Prediction"
echo "curl -X POST $API_URL/restock/predict-single"

SINGLE_INGREDIENT='{
  "ingredient_id": "TOMATO_001",
  "ingredient_name": "Roma Tomatoes", 
  "inventory_start": 30.0,
  "qty_used": 8.5,
  "covers": 180,
  "seasonality_factor": 1.2,
  "is_holiday": false
}'

curl -X POST "$API_URL/restock/predict-single" \
     -H "Content-Type: application/json" \
     -d "$SINGLE_INGREDIENT" | python3 -m json.tool
sleep 1

# 4. Bulk Restock Recommendations
echo -e "\n\n4. 📊 Bulk Restock Recommendations"  
echo "curl -X POST $API_URL/restock/recommendations"

BULK_REQUEST='{
  "ingredients": [
    {
      "ingredient_id": "BEEF_001",
      "ingredient_name": "Ground Beef",
      "inventory_start": 45.0,
      "qty_used": 18.0,
      "covers": 200,
      "seasonality_factor": 1.1
    },
    {
      "ingredient_id": "LETTUCE_002", 
      "ingredient_name": "Boston Lettuce",
      "inventory_start": 12.0,
      "qty_used": 7.5,
      "covers": 200
    },
    {
      "ingredient_id": "PASTA_001",
      "ingredient_name": "Penne Pasta", 
      "inventory_start": 150.0,
      "qty_used": 25.0,
      "covers": 200
    }
  ],
  "priority_filter": ["CRITICAL", "HIGH"],
  "limit": 5
}'

curl -X POST "$API_URL/restock/recommendations" \
     -H "Content-Type: application/json" \
     -d "$BULK_REQUEST" | python3 -m json.tool

echo -e "\n\n🎉 API Examples Complete!"
echo "🔗 View interactive documentation at: $API_URL/docs"
echo "🔗 View alternative docs at: $API_URL/redoc"