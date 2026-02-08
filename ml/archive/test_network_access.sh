#!/bin/bash

# Network Accessibility Test Script
# Tests if the API is accessible from the network

echo "🌐 Network Accessibility Test"
echo "============================="

SERVER_IP=$(ip route get 1.1.1.1 | awk '{print $7; exit}')
PORT=8000
BASE_URL="http://${SERVER_IP}:${PORT}"

echo "📡 Server IP: ${SERVER_IP}"
echo "🔌 Port: ${PORT}"
echo "🌍 Network URL: ${BASE_URL}"
echo ""

# Check if server is running locally first
echo "🔍 Testing local access..."
if curl -s http://localhost:${PORT}/ping > /dev/null 2>&1; then
    echo "✅ Server responding locally"
else
    echo "❌ Server not running locally"
    echo "   Start server with: ./start_ml_api.sh"
    exit 1
fi

# Test network access from localhost (simulating remote access)
echo ""
echo "🔍 Testing network access..."
if curl -s "${BASE_URL}/ping" > /dev/null 2>&1; then
    echo "✅ Server accessible via network IP"
else
    echo "❌ Server not accessible via network IP"
    echo "   Check firewall or network configuration"
fi

# Test ML endpoints
echo ""
echo "🔍 Testing ML endpoints over network..."
response=$(curl -s "${BASE_URL}/ml/health" 2>/dev/null)
if [ $? -eq 0 ] && [ -n "$response" ]; then
    echo "✅ ML endpoints accessible over network"
    echo "Response: $response" | head -c 100
else
    echo "❌ ML endpoints not accessible over network"
fi

echo ""
echo "🚀 Network Access Information:"
echo "================================"
echo "Frontend/Other Servers can access:"
echo "  Base API: ${BASE_URL}"
echo "  ML Health: ${BASE_URL}/ml/health"
echo "  Get SKUs: ${BASE_URL}/ml/skus"
echo "  Predictions: ${BASE_URL}/ml/predict/inventory"
echo "  API Docs: ${BASE_URL}/docs"
echo ""
echo "📝 Example API call from another server:"
echo "curl ${BASE_URL}/ml/health"
echo ""
echo "curl -X POST ${BASE_URL}/ml/predict/inventory \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"sku_id\": \"1\", \"lookahead_days\": 7}'"