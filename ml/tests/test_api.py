"""
Test client for Restaurant Inventory Restock API
Demonstrates how to interact with the API endpoints

Author: Generated for UGA Hacks  
Date: February 7, 2026
"""

import requests
import json
import time
from datetime import datetime

# API base URL
BASE_URL = "http://localhost:8001"

def test_health_check():
    """Test the health check endpoint"""
    print("🏥 Testing health check...")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API Status: {data['status']}")
            print(f"📊 Model Loaded: {data['model_loaded']}")
            if data.get('model_accuracy'):
                print(f"🎯 Model Accuracy: {data['model_accuracy']:.4f}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except requests.ConnectionError:
        print("❌ Cannot connect to API - is the server running?")
        return False

def test_categories_endpoint():
    """Test the categories information endpoint"""
    print("\n📋 Testing categories endpoint...")
    
    try:
        response = requests.get(f"{BASE_URL}/categories")
        if response.status_code == 200:
            data = response.json()
            print("✅ Categories loaded:")
            for category, info in data['categories'].items():
                print(f"  • {category}: {info['shelf_life_days']} days shelf life, "
                      f"{info['delivery_frequency_days']} days delivery cycle")
            return True
        else:
            print(f"❌ Categories endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Categories test error: {e}")
        return False

def test_single_ingredient():
    """Test single ingredient prediction"""
    print("\n🥗 Testing single ingredient prediction...")
    
    # Sample ingredient data
    ingredient_data = {
        "ingredient_id": "CHICKEN_001",
        "ingredient_name": "Chicken Breast",
        "inventory_start": 50.0,
        "qty_used": 12.5,
        "on_order_qty": 0.0,
        "lead_time_days": 2,
        "covers": 120,
        "seasonality_factor": 1.1,
        "is_holiday": False
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/restock/predict-single",
            json=ingredient_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                rec = data['recommendation']
                print(f"✅ Prediction for {rec['ingredient_name']}:")
                print(f"  📊 Category: {rec['category']}")
                print(f"  ⚠️ Priority: {rec['priority']}")
                print(f"  📦 Current Stock: {rec['current_inventory']:.1f}")
                print(f"  🔮 Predicted End: {rec['predicted_inventory_end']:.1f}")
                print(f"  🛒 Restock Needed: {rec['restock_needed']}")
                if rec['restock_needed']:
                    print(f"  📋 Suggested Order: {rec['suggested_order_qty']:.1f}")
                    print(f"  📅 Days Until Stockout: {rec['days_until_stockout']:.1f}")
                print(f"  ⏱️ Processing Time: {data['processing_time_ms']:.1f}ms")
                return True
            else:
                print(f"❌ Prediction failed: {data.get('message', 'Unknown error')}")
                return False
        else:
            print(f"❌ Single ingredient test failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Single ingredient test error: {e}")
        return False

def test_bulk_recommendations():
    """Test bulk restock recommendations"""
    print("\n📊 Testing bulk restock recommendations...")
    
    # Sample restaurant inventory data
    ingredients_data = {
        "ingredients": [
            {
                "ingredient_id": "CHICKEN_001",
                "ingredient_name": "Chicken Breast",
                "inventory_start": 25.0,
                "qty_used": 15.0,
                "covers": 150
            },
            {
                "ingredient_id": "LETTUCE_001",
                "ingredient_name": "Iceberg Lettuce",
                "inventory_start": 8.0,
                "qty_used": 6.5,
                "covers": 150
            },
            {
                "ingredient_id": "CHEESE_001", 
                "ingredient_name": "Mozzarella Cheese",
                "inventory_start": 40.0,
                "qty_used": 8.0,
                "covers": 150
            },
            {
                "ingredient_id": "RICE_001",
                "ingredient_name": "Basmati Rice",
                "inventory_start": 200.0,
                "qty_used": 12.0,
                "covers": 150
            }
        ],
        "priority_filter": ["CRITICAL", "HIGH", "MEDIUM"],
        "limit": 10
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/restock/recommendations",
            json=ingredients_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Bulk analysis completed:")
            print(f"  📊 Analyzed: {data['total_ingredients_analyzed']} ingredients")
            print(f"  💡 Recommendations: {data['recommendations_count']}")
            print(f"  ⏱️ Processing Time: {data['processing_time_ms']:.1f}ms")
            
            # Print summary
            summary = data['summary']
            print(f"\n📋 Priority Breakdown:")
            print(f"  🔴 Critical: {summary['critical']}")
            print(f"  🟡 High: {summary['high']}") 
            print(f"  🟢 Medium: {summary['medium']}")
            print(f"  ⚪ Low: {summary['low']}")
            print(f"  🛒 Need Restock: {summary['restock_needed']}")
            print(f"  ⚠️ Waste Risk: {summary['waste_risk']}")
            
            # Show top recommendations
            print(f"\n🎯 Top Recommendations:")
            for i, rec in enumerate(data['recommendations'][:3], 1):
                print(f"  {i}. {rec['ingredient_name']} ({rec['category']})")
                print(f"     Priority: {rec['priority']}, Stock: {rec['current_inventory']:.1f}")
                if rec['restock_needed']:
                    print(f"     📦 Order: {rec['suggested_order_qty']:.1f}")
                
            return True
        else:
            print(f"❌ Bulk recommendations failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Bulk recommendations test error: {e}")
        return False

def run_all_tests():
    """Run all API tests"""
    print("🚀 Starting Restaurant Restock API Tests")
    print("=" * 50)
    
    # Track test results
    results = []
    
    # Test health check first
    results.append(("Health Check", test_health_check()))
    
    if not results[0][1]:  # If health check fails, skip other tests
        print("\n❌ Health check failed - skipping other tests")
        print("💡 Make sure to start the API server first:")
        print("   python restaurant_api.py")
        return
    
    # Run other tests
    time.sleep(1)  # Brief delay between tests
    results.append(("Categories", test_categories_endpoint()))
    
    time.sleep(1) 
    results.append(("Single Ingredient", test_single_ingredient()))
    
    time.sleep(1)
    results.append(("Bulk Recommendations", test_bulk_recommendations()))
    
    # Print final results
    print("\n" + "=" * 50)
    print("🏁 Test Results Summary:")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
    
    print(f"\n📊 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your API is ready to use.")
        print("\n🔗 Try the interactive docs at: http://localhost:8000/docs")
    else:
        print("⚠️  Some tests failed - check the API server logs")

if __name__ == "__main__":
    run_all_tests()