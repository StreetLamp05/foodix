"""
Test script to verify trained models can be loaded and used for predictions
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from training.inventory_forecasting import *
from data_processing.database_loader import RestaurantDatabaseLoader
import pandas as pd
import numpy as np

def test_trained_models():
    """Test that our newly trained models work correctly"""
    
    print("🧪 Testing Newly Trained Models")
    print("=" * 40)
    
    # Configuration matching training
    config = ModelConfig(
        xgb_params={
            'n_estimators': 1000,
            'max_depth': 6,
            'learning_rate': 0.05,
            'tree_method': 'hist',
            'objective': 'count:poisson',
            'random_state': 42
        },
        lstm_params={
            'hidden_dim': 256,
            'num_layers': 3,
            'dropout': 0.3,
            'output_dim': 1
        },
        sequence_length=30,
        batch_size=128
    )
    
    try:
        print("🔄 Loading ensemble models...")
        ensemble = StackedEnsemble(config)
        ensemble.load_models("/home/quentin/ugaHacks/models")
        print("✅ Models loaded successfully!")
        
        # Test with some sample data
        print("📊 Loading test data from database...")
        with RestaurantDatabaseLoader() as db:
            data = db.load_training_data(days_back=30)
            if not data.empty:
                print(f"✅ Loaded {len(data)} test records")
                
                # Make a prediction
                print("🔮 Testing prediction...")
                test_sample = data.head(100)  # Small sample for testing
                
                # Prepare the data
                tabular_features, time_series_data, target = ensemble.prepare_data(test_sample)
                
                # Make predictions with each model
                print("🎯 XGBoost prediction...")
                xgb_pred = ensemble.model_a.model.predict(tabular_features)
                print(f"   XGBoost predictions shape: {xgb_pred.shape}")
                
                print("🎯 LSTM prediction...")
                device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
                ensemble.model_b.model.to(device)
                ensemble.model_b.model.eval()
                
                with torch.no_grad():
                    ts_tensor = torch.FloatTensor(time_series_data).to(device)
                    if len(ts_tensor.shape) == 2:
                        ts_tensor = ts_tensor.unsqueeze(0)
                    lstm_pred = ensemble.model_b.model(ts_tensor).cpu().numpy()
                    print(f"   LSTM predictions shape: {lstm_pred.shape}")
                
                print("🎯 Meta-model combination...")
                expert_features = np.column_stack([xgb_pred.flatten(), lstm_pred.flatten()])
                final_pred = ensemble.meta_model.predict(expert_features)
                print(f"   Final predictions shape: {final_pred.shape}")
                print(f"   Sample predictions: {final_pred[:5]}")
                
                print("✅ All predictions working correctly!")
                return True
            else:
                print("❌ No test data available")
                return False
                
    except Exception as e:
        print(f"❌ Model test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_trained_models()
    if success:
        print("\n🎉 Model testing completed successfully!")
        print("   Models are properly trained and can make predictions")
    else:
        print("\n❌ Model testing failed!")
        print("   There may be issues with model loading or prediction")