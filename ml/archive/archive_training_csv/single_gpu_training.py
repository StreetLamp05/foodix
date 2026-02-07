"""
Single GPU Restaurant Inventory Forecasting
Optimized for RTX 3070 (8GB VRAM) - Sequential Training Strategy
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from inventory_forecasting import *

class SingleGPUEnsemble:
    """Optimized ensemble for single GPU training"""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.model_a = None  # XGBoost
        self.model_b = None  # LSTM
        self.meta_model = Ridge(alpha=10.0)  # High alpha to tame scale mismatch
        self.is_trained = False
        
        # Single GPU setup
        self.gpu_id = 0  # RTX 3070
        
    def train_xgboost_first(self, data: pd.DataFrame) -> Dict[str, float]:
        """Train XGBoost first, then clear GPU memory"""
        logger.info(f"🎯 Training XGBoost on GPU {self.gpu_id} (RTX 3070)...")
        
        # Prepare tabular features
        tabular_features, time_series_data, target = self.prepare_data(data)
        
        # Update XGBoost config - Use CPU since GPU support not available
        xgb_config = self.config.xgb_params.copy()
        xgb_config['tree_method'] = 'hist'  # CPU-based
        # Remove any GPU-related parameters
        if 'device' in xgb_config:
            del xgb_config['device']
        if 'gpu_id' in xgb_config:
            del xgb_config['gpu_id']
        
        self.model_a = ModelA_XGBoost(self.config)
        # Apply the updated config to the model
        self.model_a.config.xgb_params = xgb_config
        self.model_a.config.xgb_gpu_id = self.gpu_id
        
        # Train XGBoost
        xgb_results = self.model_a.train(tabular_features, target)
        
        logger.info(f"✅ XGBoost completed. RMSE: {xgb_results['test_rmse']:.4f}")
        return xgb_results
    
    def train_lstm_second(self, data: pd.DataFrame) -> Dict[str, float]:
        """Train LSTM after XGBoost, reusing GPU memory"""
        logger.info(f"🎯 Training LSTM on GPU {self.gpu_id} (RTX 3070)...")
        
        # Prepare data
        tabular_features, time_series_data, target = self.prepare_data(data)
        
        # Update LSTM config for single GPU
        lstm_config = self.config.lstm_params.copy()
        
        self.model_b = ModelB_LSTM(self.config)
        self.model_b.config.lstm_gpu_id = self.gpu_id
        self.model_b.device = torch.device(f'cuda:{self.gpu_id}' if torch.cuda.is_available() else 'cpu')
        
        # Train LSTM
        lstm_results = self.model_b.train(time_series_data)
        
        logger.info(f"✅ LSTM completed. RMSE: {lstm_results['test_rmse']:.4f}")
        return lstm_results
    
    def prepare_data(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Prepare data for both models"""
        # Ensure we have the right columns
        if 'inventory_level' not in data.columns:
            logger.error("Data must have 'inventory_level' column")
            raise ValueError("Missing required column: inventory_level")
        
        # Prepare features similar to original but adapted for normalized data
        tabular_features = self.prepare_tabular_features(data)
        
        # Time series data - use key columns
        ts_cols = ['inventory_level']
        if 'daily_cost' in data.columns:
            ts_cols.append('daily_cost')
        if 'covers' in data.columns:
            ts_cols.append('covers')
        if 'revenue_items_using_ing' in data.columns:
            ts_cols.append('revenue_items_using_ing')
            
        time_series_data = data[ts_cols].values
        target = data['inventory_level'].values
        
        return tabular_features, time_series_data, target
    
    def prepare_tabular_features(self, data: pd.DataFrame) -> np.ndarray:
        """Prepare tabular features for XGBoost"""
        features = []
        feature_names = []
        
        # Time-based features
        if 'date' in data.columns:
            data['date'] = pd.to_datetime(data['date'])
            data['day_of_week'] = data['date'].dt.dayofweek
            data['month'] = data['date'].dt.month
            data['quarter'] = data['date'].dt.quarter
            data['is_weekend'] = (data['day_of_week'] >= 5).astype(int)
            
            feature_names.extend(['day_of_week', 'month', 'quarter', 'is_weekend'])
        
        # Existing features from normalized data
        existing_features = []
        for col in ['covers', 'seasonality_factor', 'is_holiday', 'inventory_turnover', 
                   'cost_per_cover', 'revenue_per_cover', 'profit_margin']:
            if col in data.columns:
                existing_features.append(col)
                feature_names.append(col)
        
        # Rolling features for inventory_level
        if 'inventory_level' in data.columns:
            for window in [3, 7, 14]:
                col_name = f'rolling_mean_{window}'
                data[col_name] = data['inventory_level'].rolling(window, min_periods=1).mean()
                existing_features.append(col_name)
                feature_names.append(col_name)
                
                col_name = f'rolling_std_{window}'
                data[col_name] = data['inventory_level'].rolling(window, min_periods=1).std()
                existing_features.append(col_name)
                feature_names.append(col_name)
        
        # Lag features
        for lag in [1, 3, 7]:
            col_name = f'inventory_lag_{lag}'
            data[col_name] = data['inventory_level'].shift(lag)
            existing_features.append(col_name)
            feature_names.append(col_name)
        
        # Combine all features
        all_features = feature_names + existing_features
        available_features = [f for f in all_features if f in data.columns]
        
        logger.info(f"📊 Using {len(available_features)} tabular features: {', '.join(available_features[:5])}...")
        
        return data[available_features].fillna(0).values
    
    def train_sequential(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Train models sequentially on single GPU"""
        logger.info("🚀 Sequential Training on Single GPU (RTX 3070)")
        logger.info("=" * 60)
        
        results = {}
        
        # Step 1: Train XGBoost
        try:
            xgb_results = self.train_xgboost_first(data)
            results['xgboost'] = xgb_results
        except Exception as e:
            logger.error(f"❌ XGBoost training failed: {e}")
            results['xgboost'] = {'error': str(e)}
            
        # Clear any GPU memory if needed
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.info("🧹 Cleared GPU cache between models")
        
        # Step 2: Train LSTM
        try:
            lstm_results = self.train_lstm_second(data)  
            results['lstm'] = lstm_results
        except Exception as e:
            logger.error(f"❌ LSTM training failed: {e}")
            results['lstm'] = {'error': str(e)}
        
        # Step 3: Train meta-model if both succeeded
        if 'error' not in results.get('xgboost', {}) and 'error' not in results.get('lstm', {}):
            try:
                logger.info("🎯 Training meta-model...")
                self.train_meta_model(data)
                results['meta_model'] = {'status': 'trained'}
                self.is_trained = True
                logger.info("✅ Meta-model training completed!")
            except Exception as e:
                logger.error(f"❌ Meta-model training failed: {e}")
                results['meta_model'] = {'status': 'failed', 'error': str(e)}
        
        return results
    
    def train_meta_model(self, data: pd.DataFrame):
        """Train meta-model using predictions from both base models"""
        tabular_features, time_series_data, target = self.prepare_data(data)
        
        # Create sequences for LSTM
        sequences, seq_targets = self.model_b.create_sequences(time_series_data)
        
        # Align features
        min_len = min(len(tabular_features), len(sequences))
        tabular_aligned = tabular_features[:min_len]
        sequences_aligned = sequences[:min_len]
        target_aligned = seq_targets[:min_len]
        
        if len(target_aligned.shape) > 1:
            target_aligned = target_aligned[:, 0]
        
        # Get predictions
        xgb_pred = self.model_a.predict(tabular_aligned)
        lstm_pred = self.model_b.predict(sequences_aligned)
        
        # Ensure same length
        min_pred_len = min(len(xgb_pred), len(lstm_pred), len(target_aligned))
        xgb_pred = xgb_pred[:min_pred_len]
        lstm_pred = lstm_pred[:min_pred_len]
        target_aligned = target_aligned[:min_pred_len]
        
        # Stack predictions
        meta_features = np.column_stack([xgb_pred, lstm_pred])
        
        # Train meta-model
        self.meta_model.fit(meta_features, target_aligned)

def single_gpu_training():
    """Main training function for single GPU setup"""
    logger.info("🎮 Single GPU Restaurant Inventory Forecasting")
    logger.info("RTX 3070 (8GB) - Sequential Training Strategy")
    logger.info("=" * 70)
    
    # Optimized config for RTX 3070 with shared target scaler
    target_scaler = MinMaxScaler()  # Shared target scaler for consistency
    
    config = ModelConfig(
        xgb_params={
            'n_estimators': 1000,
            'max_depth': 6,
            'learning_rate': 0.05,
            'tree_method': 'gpu_hist',
            'gpu_id': 0,  # RTX 3070
            'random_state': 42,
            'subsample': 0.8,
            'colsample_bytree': 0.8
        },
        lstm_params={
            'hidden_dim': 256,     # Reduced for 8GB VRAM
            'num_layers': 3,
            'dropout': 0.3,
            'output_dim': 1
        },
        target_scaler=target_scaler,  # Shared target scaler
        sequence_length=30,       # 3 weeks
        batch_size=128,            # Conservative for 8GB
        test_size=0.2,
        val_size=0.1
    )
    
    # Load normalized data
    data_path = '/home/quentin/ugaHacks/data/restaurant_daily_agg.csv'
    if not os.path.exists(data_path):
        logger.error(f"❌ Normalized data not found: {data_path}")
        logger.info("💡 Run: python3 data_fixer.py")
        return
    
    data = pd.read_csv(data_path)
    logger.info(f"📊 Loaded data: {data.shape}")
    logger.info(f"📅 Date range: {data['date'].min()} to {data['date'].max()}")
    
    # Initialize single GPU ensemble
    ensemble = SingleGPUEnsemble(config)
    
    # Train sequentially
    start_time = time.time()
    results = ensemble.train_sequential(data)
    total_time = time.time() - start_time
    
    # Print results
    logger.info("=" * 70)
    logger.info("📊 SINGLE GPU TRAINING RESULTS")
    logger.info("=" * 70)
    
    for model_name, metrics in results.items():
        logger.info(f"\n{model_name.upper()}:")
        if 'error' in metrics:
            logger.error(f"  ❌ Error: {metrics['error']}")
        else:
            for metric, value in metrics.items():
                if isinstance(value, (int, float)) and metric != 'epochs_trained':
                    logger.info(f"  ✅ {metric}: {value:.4f}")
                else:
                    logger.info(f"  ✅ {metric}: {value}")
    
    logger.info(f"\n⏱️  Total Training Time: {total_time:.2f} seconds")
    logger.info(f"🎮 GPU: RTX 3070 (Sequential Training)")
    
    # Save models
    if ensemble.is_trained:
        save_dir = '/home/quentin/ugaHacks/models/single_gpu'
        os.makedirs(save_dir, exist_ok=True)
        
        # Save individual models
        if ensemble.model_a:
            joblib.dump(ensemble.model_a, f"{save_dir}/xgboost_model.pkl")
            joblib.dump(ensemble.model_a.feature_scaler, f"{save_dir}/xgb_feature_scaler.pkl")
            joblib.dump(ensemble.model_a.target_scaler, f"{save_dir}/xgb_target_scaler.pkl")
        if ensemble.model_b:
            torch.save(ensemble.model_b.model.state_dict(), f"{save_dir}/lstm_model.pth")
            joblib.dump(ensemble.model_b.feature_scaler, f"{save_dir}/lstm_feature_scaler.pkl")
            joblib.dump(ensemble.model_b.target_scaler, f"{save_dir}/lstm_target_scaler.pkl")
        if ensemble.meta_model:
            joblib.dump(ensemble.meta_model, f"{save_dir}/meta_model.pkl")
        
        logger.info(f"💾 Models saved to: {save_dir}")
        logger.info("🎯 Training completed successfully!")
    
    return ensemble, results

if __name__ == "__main__":
    ensemble, results = single_gpu_training()