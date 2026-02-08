"""
Test script for ML endpoints
Tests the ensemble model serving functionality
"""

import requests
import json
from datetime import datetime, timedelta

# Test configuration
BASE_URL = "http://localhost:8000/ml"
TEST_SKU_ID = "1"  # Use a known SKU ID from your database

def test_ml_health():
    """Test ML service health"""
    print("🩺 Testing ML health endpoint...")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ ML Health: {result['status']}")
            print(f"   Models loaded: {result['model_status']['ensemble_loaded']}")
            print(f"   Database connected: {result['model_status']['database_connected']}")
            print(f"   GPU available: {result['model_status']['gpu_available']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_get_skus():
    """Test getting available SKUs"""
    print("📋 Testing available SKUs endpoint...")
    
    try:
        response = requests.get(f"{BASE_URL}/skus?limit=10")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Found {result['count']} available SKUs")
            print(f"   Sample SKUs: {result['skus'][:5]}")
            return result['skus'][0] if result['skus'] else None
        else:
            print(f"❌ SKUs request failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ SKUs request error: {e}")
        return None

def test_inventory_prediction(sku_id: str):
    """Test inventory prediction"""
    print(f"🔮 Testing inventory prediction for SKU {sku_id}...")
    
    payload = {
        "sku_id": sku_id,
        "lookahead_days": 7,
        "current_stock": 100.0
    }
    
    try:
        response = requests.post(f"{BASE_URL}/predict/inventory", json=payload)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Prediction successful for SKU {result['sku_id']}")
            print(f"   Predictions count: {len(result['predictions'])}")
            print(f"   Total predicted consumption: {result['summary']['total_predicted_consumption']:.2f}")
            print(f"   Average daily consumption: {result['summary']['avg_daily_consumption']:.2f}")
            
            # Show sample predictions
            print("   Sample predictions:")
            for i, pred in enumerate(result['predictions'][:3]):
                if pred['predicted'] is not None:
                    print(f"     {pred['date']}: {pred['predicted']:.2f}")
            
            return result
        else:
            print(f"❌ Prediction failed: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"   Error: {error_detail.get('detail', 'Unknown error')}")
            except:
                pass
            return None
    except Exception as e:
        print(f"❌ Prediction error: {e}")
        return None

def test_optimization_analytics(sku_id: str):
    """Test optimization analytics"""
    print(f"⚙️ Testing optimization analytics for SKU {sku_id}...")
    
    # Test optimization parameters
    params = {
        "current_stock": 50.0,
        "perish_date": (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d"),
        "safety_buffer_days": 3
    }
    
    try:
        response = requests.get(f"{BASE_URL}/analytics/optimization/{sku_id}", params=params)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Optimization analysis successful for SKU {result['sku_id']}")
            print(f"   Runout date: {result['runout_date']}")
            print(f"   Waste risk: {result['waste_risk']}")
            print(f"   Suggested action: {result['suggested_action']}")
            print(f"   Stock coverage: {result['details']['stock_coverage_days']} days")
            return result
        else:
            print(f"❌ Optimization failed: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"   Error: {error_detail.get('detail', 'Unknown error')}")
            except:
                pass
            return None
    except Exception as e:
        print(f"❌ Optimization error: {e}")
        return None

def main():
    """Run all ML endpoint tests"""
    print("🚀 Starting ML Endpoints Tests")
    print("=" * 50)
    
    # Test health
    if not test_ml_health():
        print("❌ ML services not healthy, skipping other tests")
        return
    
    print()
    
    # Get available SKUs
    test_sku = test_get_skus()
    if not test_sku:
        print("❌ No SKUs available, using default test SKU")
        test_sku = TEST_SKU_ID
    
    print()
    
    # Test prediction
    prediction_result = test_inventory_prediction(test_sku)
    
    print()
    
    # Test optimization if prediction worked
    if prediction_result:
        optimization_result = test_optimization_analytics(test_sku)
    
    print()
    print("🏁 ML Endpoints Tests Complete")

if __name__ == "__main__":
    main()