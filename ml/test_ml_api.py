"""
ML Endpoints Test Suite
Python script for testing ML endpoints with detailed output
"""

import requests
import json
from datetime import datetime, timedelta
import time

BASE_URL = "http://localhost:8000"

def test_endpoint(method, endpoint, data=None, description=""):
    """Test an endpoint and return results"""
    url = f"{BASE_URL}{endpoint}"
    print(f"\n🔍 {description}")
    print(f"   {method} {url}")
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, timeout=10)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, timeout=10)
        else:
            print(f"❌ Unsupported method: {method}")
            return None
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Success!")
            
            # Pretty print key information
            if endpoint.endswith("/health"):
                print(f"   Status: {result.get('status', 'unknown')}")
                if 'model_status' in result:
                    print(f"   Model Loaded: {result['model_status'].get('xgboost_loaded', 'unknown')}")
                    print(f"   Database: {result['model_status'].get('database_connected', 'unknown')}")
            
            elif endpoint.endswith("/skus"):
                skus = result.get('skus', [])
                print(f"   Found {len(skus)} SKUs: {skus[:5]}{'...' if len(skus) > 5 else ''}")
                
            elif "/predict/inventory" in endpoint:
                predictions = result.get('predictions', [])
                summary = result.get('summary', {})
                print(f"   Predictions: {len(predictions)} data points")
                print(f"   Total consumption: {summary.get('total_predicted_consumption', 0):.2f}")
                print(f"   Avg daily: {summary.get('avg_daily_consumption', 0):.2f}")
                
                # Show sample predictions
                future_preds = [p for p in predictions if p.get('predicted') is not None]
                if future_preds:
                    print("   Sample predictions:")
                    for pred in future_preds[:3]:
                        print(f"     {pred['date']}: {pred['predicted']:.2f}")
            
            return result
        else:
            print(f"❌ Failed: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def main():
    """Main test function"""
    print("🧪 ML Endpoints Test Suite")
    print("=" * 40)
    
    # Check basic connectivity
    print("📡 Checking server connectivity...")
    try:
        response = requests.get(f"{BASE_URL}/ping", timeout=5)
        if response.status_code == 200:
            print("✅ Server is responding")
        else:
            print("❌ Server responded with error")
            return
    except:
        print("❌ Server is not responding")
        print(f"   Make sure server is running on {BASE_URL}")
        print("   Run: cd /home/quentin/hacks11-voyix/ml && ./start_ml_api.sh")
        return
    
    # Test ML health
    health_result = test_endpoint("GET", "/ml/health", description="ML Health Check")
    
    # Test get SKUs
    skus_result = test_endpoint("GET", "/ml/skus?limit=10", description="Get Available SKUs")
    
    # Get a sample SKU for predictions
    sample_sku = None
    if skus_result and skus_result.get('skus'):
        sample_sku = skus_result['skus'][0]
        print(f"\n📋 Using sample SKU: {sample_sku}")
    else:
        sample_sku = "1"  # Fallback
        print(f"\n📋 Using fallback SKU: {sample_sku}")
    
    # Test inventory predictions
    prediction_data = {
        "sku_id": sample_sku,
        "lookahead_days": 7
    }
    
    prediction_result = test_endpoint(
        "POST", "/ml/predict/inventory", 
        data=prediction_data,
        description=f"Inventory Prediction for SKU {sample_sku}"
    )
    
    # Test longer prediction
    prediction_data_long = {
        "sku_id": sample_sku,
        "lookahead_days": 30
    }
    
    test_endpoint(
        "POST", "/ml/predict/inventory",
        data=prediction_data_long,
        description=f"Long-term Prediction (30 days)"
    )
    
    # Test error handling with invalid SKU
    invalid_data = {
        "sku_id": "invalid_sku_12345",
        "lookahead_days": 7
    }
    
    test_endpoint(
        "POST", "/ml/predict/inventory",
        data=invalid_data,
        description="Error Handling Test (Invalid SKU)"
    )
    
    print("\n" + "="*50)
    print("🎉 Test Suite Completed!")
    print("\n💡 Additional Testing Options:")
    print(f"1. Interactive docs: {BASE_URL}/docs")
    print(f"2. API schema: {BASE_URL}/openapi.json")
    print("3. Run the bash test script: ./test_endpoints.sh")
    
    print("\n🚀 Quick Manual Commands:")
    print(f"curl {BASE_URL}/ml/health")
    print(f"curl {BASE_URL}/ml/skus")
    print(f"""curl -X POST {BASE_URL}/ml/predict/inventory \\
  -H 'Content-Type: application/json' \\
  -d '{{"sku_id": "{sample_sku}", "lookahead_days": 7}}'""")

if __name__ == "__main__":
    main()