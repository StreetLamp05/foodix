"""
Quick Training Script for Restaurant Inventory Forecasting
Simplified interface for rapid testing and experimentation
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from inventory_forecasting import *
import argparse

def quick_train(data_path: str = None, epochs: int = 50, save_models: bool = True):
    """Quick training function with simplified parameters"""
    
    # Quick config for faster training
    config = ModelConfig(
        xgb_params={
            'n_estimators': 50,  # Reduced for speed
            'max_depth': 4,
            'learning_rate': 0.15,
            'tree_method': 'gpu_hist',
            'gpu_id': 1,
            'random_state': 42
        },
        lstm_params={
            'hidden_dim': 64,  # Reduced for speed
            'num_layers': 1,
            'dropout': 0.1,
            'output_dim': 1
        },
        sequence_length=14,  # Shorter sequences
        batch_size=64
    )
    
    print("🚀 Quick Training Mode - Restaurant Inventory Forecasting")
    print("=" * 60)
    
    # Load data
    if data_path and os.path.exists(data_path):
        print(f"📁 Loading data from: {data_path}")
        data = pd.read_csv(data_path)
    else:
        print("📊 Creating sample data...")
        data = create_sample_data(800)  # Smaller dataset for speed
    
    print(f"📈 Data shape: {data.shape}")
    print(f"📅 Date range: {data['date'].min()} to {data['date'].max()}")
    
    # Initialize ensemble
    ensemble = StackedEnsemble(config)
    
    # Train
    print("\n🏃‍♂️ Starting parallel training...")
    print(f"🎯 XGBoost → GPU {config.xgb_gpu_id} (RTX 3060)")
    print(f"🎯 LSTM → GPU {config.lstm_gpu_id} (RTX 3080)")
    
    results = ensemble.train_models_parallel(data)
    
    # Results
    print("\n" + "=" * 60)
    print("📊 QUICK TRAINING RESULTS")
    print("=" * 60)
    
    for model_name, metrics in results.items():
        if 'error' not in metrics:
            print(f"\n{model_name.upper()}:")
            if 'test_rmse' in metrics:
                print(f"  ✅ Test RMSE: {metrics['test_rmse']:.4f}")
            if 'test_r2' in metrics:
                print(f"  ✅ Test R²: {metrics['test_r2']:.4f}")
            if 'train_time' in metrics:
                print(f"  ⏱️  Training time: {metrics['train_time']:.2f}s")
    
    # Save models
    if save_models and ensemble.is_trained:
        save_dir = '/home/quentin/ugaHacks/models'
        ensemble.save_models(save_dir)
        print(f"\n💾 Models saved to: {save_dir}")
    
    return ensemble, results

def test_gpu_setup():
    """Test GPU availability and setup"""
    print("🔍 Testing GPU Setup...")
    print("=" * 40)
    
    # Check CUDA
    import torch
    print(f"PyTorch CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA devices: {torch.cuda.device_count()}")
        for i in range(torch.cuda.device_count()):
            print(f"  GPU {i}: {torch.cuda.get_device_name(i)}")
    
    # Check XGBoost GPU
    try:
        import xgboost as xgb
        print("XGBoost GPU support: Available")
    except Exception as e:
        print(f"XGBoost GPU support: Error - {e}")
    
    print()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Quick Restaurant Inventory Forecasting')
    parser.add_argument('--data', type=str, help='Path to data CSV file')
    parser.add_argument('--epochs', type=int, default=50, help='Training epochs')
    parser.add_argument('--no-save', action='store_true', help='Don\'t save models')
    parser.add_argument('--test-gpu', action='store_true', help='Test GPU setup only')
    
    args = parser.parse_args()
    
    if args.test_gpu:
        test_gpu_setup()
    else:
        ensemble, results = quick_train(
            data_path=args.data,
            epochs=args.epochs,
            save_models=not args.no_save
        )