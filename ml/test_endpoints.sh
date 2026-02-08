#!/bin/bash

# ML Endpoints Test Script
# Tests all available ML endpoints with sample data

echo "🧪 Testing ML Endpoints"
echo "======================="

BASE_URL="http://localhost:8000"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to test an endpoint
test_endpoint() {
    local method=$1
    local endpoint=$2
    local data=$3
    local description=$4
    
    echo -e "\n${BLUE}🔍 Testing: ${description}${NC}"
    echo "Endpoint: ${method} ${BASE_URL}${endpoint}"
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\nHTTP_CODE:%{http_code}" "${BASE_URL}${endpoint}")
    else
        response=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X ${method} -H "Content-Type: application/json" -d "${data}" "${BASE_URL}${endpoint}")
    fi
    
    http_code=$(echo "$response" | tail -n1 | cut -d: -f2)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" -eq 200 ] || [ "$http_code" -eq 201 ]; then
        echo -e "${GREEN}✅ Success (HTTP ${http_code})${NC}"
        echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
    else
        echo -e "${RED}❌ Failed (HTTP ${http_code})${NC}"
        echo "$body"
    fi
}

# Test basic connectivity
echo -e "${YELLOW}📡 Testing Basic Connectivity...${NC}"
if curl -s "${BASE_URL}/ping" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Server is responding${NC}"
else
    echo -e "${RED}❌ Server is not responding at ${BASE_URL}${NC}"
    echo "Please make sure the server is running:"
    echo "cd /home/quentin/hacks11-voyix/ml && ./start_ml_api.sh"
    exit 1
fi

# Test ML health endpoint
test_endpoint "GET" "/ml/health" "" "ML Service Health Check"

# Test get available SKUs
test_endpoint "GET" "/ml/skus?limit=5" "" "Get Available SKUs (limit 5)"

# Get a sample SKU for testing predictions
echo -e "\n${YELLOW}🔍 Getting a sample SKU for testing...${NC}"
sample_sku=$(curl -s "${BASE_URL}/ml/skus?limit=1" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['skus'][0] if data.get('skus') else 'test_sku')" 2>/dev/null || echo "test_sku")
echo "Using SKU: ${sample_sku}"

# Test inventory prediction
prediction_request="{
  \"sku_id\": \"${sample_sku}\",
  \"lookahead_days\": 7
}"

test_endpoint "POST" "/ml/predict/inventory" "$prediction_request" "Inventory Prediction (7 days)"

# Test with different lookahead period
prediction_request_14="{
  \"sku_id\": \"${sample_sku}\",
  \"lookahead_days\": 14
}"

test_endpoint "POST" "/ml/predict/inventory" "$prediction_request_14" "Inventory Prediction (14 days)"

# Test optimization analytics (if available)
echo -e "\n${YELLOW}🔍 Testing optimization endpoints...${NC}"
optimization_params="current_stock=100&safety_buffer_days=3"
test_endpoint "GET" "/analytics/optimization/${sample_sku}?${optimization_params}" "" "Optimization Analytics"

# Test with expiry date
expiry_date=$(date -d "+10 days" +%Y-%m-%d)
optimization_params_expiry="current_stock=50&perish_date=${expiry_date}&safety_buffer_days=2"
test_endpoint "GET" "/analytics/optimization/${sample_sku}?${optimization_params_expiry}" "" "Optimization with Expiry Date"

# Test API documentation endpoints
echo -e "\n${YELLOW}📚 API Documentation Endpoints:${NC}"
echo "- Interactive Docs: ${BASE_URL}/docs"
echo "- ReDoc: ${BASE_URL}/redoc"
echo "- OpenAPI Schema: ${BASE_URL}/openapi.json"

echo -e "\n${GREEN}🎉 Testing completed!${NC}"
echo -e "\n${BLUE}💡 Pro Tips:${NC}"
echo "1. Open ${BASE_URL}/docs in your browser for interactive API testing"
echo "2. Use the /ml/health endpoint to check if models are loaded"
echo "3. Use /ml/skus to see which ingredient IDs are available for prediction"
echo "4. The prediction responses are formatted for Recharts (frontend graphing)"

echo -e "\n${YELLOW}🚀 Quick Manual Tests:${NC}"
echo "# Health check"
echo "curl ${BASE_URL}/ml/health"
echo ""
echo "# Get SKUs"
echo "curl ${BASE_URL}/ml/skus"
echo ""
echo "# Make prediction"
echo "curl -X POST ${BASE_URL}/ml/predict/inventory \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"sku_id\": \"${sample_sku}\", \"lookahead_days\": 7}'"