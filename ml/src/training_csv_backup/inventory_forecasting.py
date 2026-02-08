"""
Restaurant Inventory Forecasting - Stacked Ensemble
Multi-GPU Training System

Author: Generated for UGA Hacks
Date: February 7, 2026
"""

import os
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import xgboost as xgb
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import matplotlib.pyplot as plt
import seaborn as sns
import multiprocessing as mp
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import joblib
from typing import Tuple, Dict, Any, Optional
import logging
import time
from dataclasses import dataclass

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ModelConfig:
    """Configuration for model training"""
    # XGBoost Config
    xgb_params: dict
    
    # LSTM Config  
    lstm_params: dict
    
    # Data Config - Log1p transformation used instead of target_scaler
    xgb_gpu_id: int = 1  # RTX 3060
    lstm_gpu_id: int = 0  # RTX 3080
    sequence_length: int = 30
    batch_size: int = 32
    test_size: float = 0.2
    val_size: float = 0.1

class InventoryDataset(Dataset):
    """PyTorch Dataset for time series inventory data"""
    
    def __init__(self, sequences: np.ndarray, targets: np.ndarray):
        self.sequences = torch.FloatTensor(sequences)
        self.targets = torch.FloatTensor(targets)
    
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        return self.sequences[idx], self.targets[idx]

class LSTMModel(nn.Module):
    """LSTM Model for Time Series Forecasting"""
    
    def __init__(self, input_dim: int, hidden_dim: int = 128, num_layers: int = 2, 
                 dropout: float = 0.2, output_dim: int = 1):
        super(LSTMModel, self).__init__()
        
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, 
                           batch_first=True, dropout=dropout)
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_dim, output_dim)
        
    def forward(self, x):
        # Initialize hidden state with zeros
        batch_size = x.size(0)
        h0 = torch.zeros(self.num_layers, batch_size, self.hidden_dim).to(x.device)
        c0 = torch.zeros(self.num_layers, batch_size, self.hidden_dim).to(x.device)
        
        # Forward propagate LSTM
        lstm_out, _ = self.lstm(x, (h0, c0))
        
        # Get the last output
        output = self.dropout(lstm_out[:, -1, :])
        output = self.fc(output)
        
        return output

class ModelA_XGBoost:
    """XGBoost Model for Tabular Features (GPU 1 - RTX 3060)"""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.model = None
        self.feature_scaler = StandardScaler()
        self.use_log_transform = True  # Use Log1p transformation for target
        self.bias_term = 0.0  # For bias correction
        self.is_trained = False
        
        # GPU device is now set via device parameter in xgb_params
        
    def prepare_tabular_features(self, data: pd.DataFrame) -> np.ndarray:
        """Extract and prepare tabular features"""
        logger.info("Preparing tabular features for XGBoost...")
        
        features = []
        
        # Time-based features
        if 'date' in data.columns:
            data['date'] = pd.to_datetime(data['date'])
            data['day_of_week'] = data['date'].dt.dayofweek
            data['month'] = data['date'].dt.month
            data['quarter'] = data['date'].dt.quarter
            data['is_weekend'] = (data['day_of_week'] >= 5).astype(int)
            
            features.extend(['day_of_week', 'month', 'quarter', 'is_weekend'])
        
        # Statistical features (rolling windows) - use legitimate features only
        # Use inventory_start for rolling stats (available at prediction time)
        base_col = 'inventory_start'
        if base_col in data.columns:
            for window in [7, 14, 30]:
                data[f'rolling_mean_start_{window}'] = data[base_col].rolling(window).mean()
                data[f'rolling_std_start_{window}'] = data[base_col].rolling(window).std()
                features.extend([f'rolling_mean_start_{window}', f'rolling_std_start_{window}'])
        
        # Lag features - use inventory_end lags (past values only)
        target_col = 'inventory_end'
        for lag in [1, 3, 7, 14]:
            data[f'inventory_end_lag_{lag}'] = data[target_col].shift(lag)
            features.append(f'inventory_end_lag_{lag}')
        
        # Safe inventory features (available at prediction time)
        inventory_features = ['inventory_start', 'qty_used', 'on_order_qty', 
                            'lead_time_days', 'covers', 'seasonality_factor']
        for feat in inventory_features:
            if feat in data.columns:
                features.append(feat)
        
        # External features (if available)
        external_features = ['is_holiday', 'units_sold_items_using_ing', 'revenue_items_using_ing']
        for feat in external_features:
            if feat in data.columns:
                features.append(feat)
        
        return data[features].fillna(0).values
    
    def train(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """Train XGBoost model with Log1p transformation and Poisson objective"""
        logger.info(f"Training XGBoost on GPU {self.config.xgb_gpu_id} (RTX 3060)...")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.config.test_size, random_state=42)
        
        # Scale features
        X_train_scaled = self.feature_scaler.fit_transform(X_train)
        X_test_scaled = self.feature_scaler.transform(X_test)
        
        # Apply Log1p transformation to targets for heteroscedasticity
        y_train_transformed = np.log1p(y_train)  # Log1p handles values close to 0
        y_test_transformed = np.log1p(y_test)
        
        # Train XGBoost with Poisson objective on log-transformed targets
        self.model = xgb.XGBRegressor(**self.config.xgb_params)
        
        start_time = time.time()
        self.model.fit(X_train_scaled, y_train_transformed)
        train_time = time.time() - start_time
        
        # Get predictions in transformed space
        train_pred_transformed = self.model.predict(X_train_scaled)
        test_pred_transformed = self.model.predict(X_test_scaled)
        
        # Inverse transform predictions to original scale using expm1
        train_pred = np.expm1(train_pred_transformed)  # Inverse of log1p
        test_pred = np.expm1(test_pred_transformed)
        
        # Calculate bias correction
        residuals = y_train - train_pred
        self.bias_term = np.mean(residuals)
        
        # Apply bias correction
        train_pred += self.bias_term
        test_pred += self.bias_term
        
        # Plot residual analysis
        self._plot_residuals(y_train, train_pred, y_test, test_pred, 'XGBoost')
        
        metrics = {
            'train_rmse': np.sqrt(mean_squared_error(y_train, train_pred)),
            'test_rmse': np.sqrt(mean_squared_error(y_test, test_pred)),
            'train_mae': mean_absolute_error(y_train, train_pred),
            'test_mae': mean_absolute_error(y_test, test_pred),
            'train_r2': r2_score(y_train, train_pred),
            'test_r2': r2_score(y_test, test_pred),
            'train_time': train_time,
            'bias_term': self.bias_term
        }
        
        self.is_trained = True
        logger.info(f"XGBoost training completed. Test RMSE: {metrics['test_rmse']:.4f}")
        
        return metrics
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions with Log1p inverse transformation and bias correction"""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        X_scaled = self.feature_scaler.transform(X)
        pred_transformed = self.model.predict(X_scaled)
        # Inverse transform from log space to original scale
        pred = np.expm1(pred_transformed)
        return pred + self.bias_term
    
    def _plot_residuals(self, y_train, train_pred, y_test, test_pred, model_name):
        """Plot residual analysis"""
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        # Training residuals
        train_residuals = y_train - train_pred
        axes[0].scatter(train_pred, train_residuals, alpha=0.5)
        axes[0].axhline(y=0, color='r', linestyle='--')
        axes[0].set_xlabel('Predicted Values')
        axes[0].set_ylabel('Residuals')
        axes[0].set_title(f'{model_name} - Training Residuals')
        
        # Test residuals
        test_residuals = y_test - test_pred
        axes[1].scatter(test_pred, test_residuals, alpha=0.5)
        axes[1].axhline(y=0, color='r', linestyle='--')
        axes[1].set_xlabel('Predicted Values')
        axes[1].set_ylabel('Residuals')
        axes[1].set_title(f'{model_name} - Test Residuals')
        
        plt.tight_layout()
        plt.savefig(f'/home/quentin/ugaHacks/residuals_{model_name.lower()}.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Residual analysis saved: residuals_{model_name.lower()}.png")
        logger.info(f"{model_name} bias term: {self.bias_term:.6f}")

class ModelB_LSTM:
    """LSTM Model for Time Series (GPU 0 - RTX 3080)"""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.model = None
        self.feature_scaler = MinMaxScaler()  # Keep MinMax for LSTM features
        self.use_log_transform = True  # Use Log1p transformation for target consistency
        self.bias_term = 0.0  # For bias correction
        self.device = torch.device(f'cuda:{config.lstm_gpu_id}' if torch.cuda.is_available() else 'cpu')
        self.is_trained = False
        
        logger.info(f"LSTM will use device: {self.device}")
    
    def create_sequences(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Create sequences for LSTM training"""
        sequences, targets = [], []
        
        for i in range(self.config.sequence_length, len(data)):
            sequences.append(data[i-self.config.sequence_length:i])
            targets.append(data[i])
        
        return np.array(sequences), np.array(targets)
    
    def train(self, data: np.ndarray, target: np.ndarray) -> Dict[str, float]:
        """Train LSTM model with proper feature/target separation"""
        logger.info(f"Training LSTM on GPU {self.config.lstm_gpu_id} (RTX 3080)...")
        
        # Scale features only (no target in features)
        feature_data_scaled = self.feature_scaler.fit_transform(data)
        
        # Apply log1p transformation to target separately
        target_transformed = np.log1p(target)
        
        # Create sequences from features and targets separately
        X = []
        y = []
        
        for i in range(self.config.sequence_length, len(feature_data_scaled)):
            X.append(feature_data_scaled[i-self.config.sequence_length:i])
            y.append(target_transformed[i])
        
        X = np.array(X)
        y = np.array(y)
        
        # Split data
        train_size = int(len(X) * (1 - self.config.test_size - self.config.val_size))
        val_size = int(len(X) * self.config.val_size)
        
        X_train = X[:train_size]
        y_train = y[:train_size]
        X_val = X[train_size:train_size + val_size]
        y_val = y[train_size:train_size + val_size]
        X_test = X[train_size + val_size:]
        y_test = y[train_size + val_size:]
        
        # Create datasets and loaders
        train_dataset = InventoryDataset(X_train, y_train)
        val_dataset = InventoryDataset(X_val, y_val)
        test_dataset = InventoryDataset(X_test, y_test)
        
        train_loader = DataLoader(train_dataset, batch_size=self.config.batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=self.config.batch_size)
        test_loader = DataLoader(test_dataset, batch_size=self.config.batch_size)
        
        # Initialize model
        input_dim = X.shape[2]
        self.model = LSTMModel(input_dim, **self.config.lstm_params).to(self.device)
        
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=0.01, weight_decay=1e-4)  # Higher lr, add regularization
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=3, factor=0.7)
        
        # Training loop
        num_epochs = 150  # More epochs
        best_val_loss = float('inf')
        patience = 15  # More patience
        patience_counter = 0
        
        start_time = time.time()
        
        for epoch in range(num_epochs):
            # Training phase
            self.model.train()
            train_loss = 0.0
            
            for batch_X, batch_y in train_loader:
                batch_X, batch_y = batch_X.to(self.device), batch_y.to(self.device)
                
                optimizer.zero_grad()
                outputs = self.model(batch_X).squeeze()
                loss = criterion(outputs, batch_y)
                loss.backward()
                
                # Gradient clipping to prevent exploding gradients
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                optimizer.step()
                
                train_loss += loss.item()
            
            # Validation phase
            self.model.eval()
            val_loss = 0.0
            
            with torch.no_grad():
                for batch_X, batch_y in val_loader:
                    batch_X, batch_y = batch_X.to(self.device), batch_y.to(self.device)
                    outputs = self.model(batch_X).squeeze()
                    loss = criterion(outputs, batch_y)
                    val_loss += loss.item()
            
            train_loss /= len(train_loader)
            val_loss /= len(val_loader)
            
            scheduler.step(val_loss)
            
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
            else:
                patience_counter += 1
            
            if epoch % 10 == 0:
                logger.info(f'Epoch [{epoch}/{num_epochs}], Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}')
            
            if patience_counter >= patience:
                logger.info(f'Early stopping at epoch {epoch}')
                break
        
        train_time = time.time() - start_time
        
        # Final evaluation with bias correction
        self.model.eval()
        test_predictions = []
        test_targets = []
        train_predictions = []
        train_targets = []
        
        with torch.no_grad():
            # Get test predictions (scaled)
            for batch_X, batch_y in test_loader:
                batch_X, batch_y = batch_X.to(self.device), batch_y.to(self.device)
                outputs = self.model(batch_X).squeeze()
                test_predictions.extend(outputs.cpu().numpy())
                test_targets.extend(batch_y.cpu().numpy())
            
            # Get sample train predictions for bias calculation
            for i, (batch_X, batch_y) in enumerate(train_loader):
                if i >= 10:  # Only use first 10 batches for efficiency
                    break
                batch_X, batch_y = batch_X.to(self.device), batch_y.to(self.device)
                outputs = self.model(batch_X).squeeze()
                train_predictions.extend(outputs.cpu().numpy())
                train_targets.extend(batch_y.cpu().numpy())
        
        # Convert to numpy arrays and inverse transform from log space
        test_predictions = np.array(test_predictions)
        test_targets = np.array(test_targets)
        train_predictions = np.array(train_predictions)
        train_targets = np.array(train_targets)
        
        # Inverse transform from log space to original scale using expm1
        test_pred = np.expm1(test_predictions)  # Inverse of log1p
        test_true = np.expm1(test_targets)      # Inverse of log1p
        train_pred = np.expm1(train_predictions) # Inverse of log1p  
        train_true = np.expm1(train_targets)     # Inverse of log1p
        
        # Calculate bias correction
        residuals = train_true - train_pred
        self.bias_term = np.mean(residuals)
        
        # Apply bias correction
        train_pred += self.bias_term
        test_pred += self.bias_term
        
        # Plot residual analysis
        self._plot_residuals(train_true, train_pred, test_true, test_pred, 'LSTM')
        
        # Calculate metrics
        test_rmse = np.sqrt(mean_squared_error(test_true, test_pred))
        test_mae = mean_absolute_error(test_true, test_pred)
        test_r2 = r2_score(test_true, test_pred)
        
        metrics = {
            'best_val_loss': best_val_loss,
            'test_rmse': test_rmse,
            'test_mae': test_mae,
            'test_r2': test_r2,
            'train_time': train_time,
            'epochs_trained': epoch + 1,
            'bias_term': self.bias_term
        }
        
        self.is_trained = True
        logger.info(f"LSTM training completed. Test RMSE: {test_rmse:.4f}")
        
        return metrics
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions with proper scaling and bias correction"""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        self.model.eval()
        
        # Scale input data
        X_scaled = self.feature_scaler.transform(X.reshape(-1, X.shape[-1])).reshape(X.shape)
        
        dataset = InventoryDataset(X_scaled, np.zeros(len(X_scaled)))  # Dummy targets
        loader = DataLoader(dataset, batch_size=self.config.batch_size)
        
        predictions = []
        with torch.no_grad():
            for batch_X, _ in loader:
                batch_X = batch_X.to(self.device)
                outputs = self.model(batch_X).squeeze()
                predictions.extend(outputs.cpu().numpy())
        
        # Inverse transform from log space and apply bias correction
        predictions = np.array(predictions)
        predictions = np.expm1(predictions)  # Inverse of log1p
        return predictions + self.bias_term

    def _plot_residuals(self, y_train, train_pred, y_test, test_pred, model_name):
        """Plot residual analysis"""
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        # Training residuals
        train_residuals = y_train - train_pred
        axes[0].scatter(train_pred, train_residuals, alpha=0.5)
        axes[0].axhline(y=0, color='r', linestyle='--')
        axes[0].set_xlabel('Predicted Values')
        axes[0].set_ylabel('Residuals')
        axes[0].set_title(f'{model_name} - Training Residuals')
        
        # Test residuals
        test_residuals = y_test - test_pred
        axes[1].scatter(test_pred, test_residuals, alpha=0.5)
        axes[1].axhline(y=0, color='r', linestyle='--')
        axes[1].set_xlabel('Predicted Values')
        axes[1].set_ylabel('Residuals')
        axes[1].set_title(f'{model_name} - Test Residuals')
        
        plt.tight_layout()
        plt.savefig(f'/home/quentin/ugaHacks/residuals_{model_name.lower()}.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Residual analysis saved: residuals_{model_name.lower()}.png")
        logger.info(f"{model_name} bias term: {self.bias_term:.6f}")

class StackedEnsemble:
    """Stacked Ensemble combining XGBoost and LSTM with Linear Regression Meta-Model"""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.model_a = ModelA_XGBoost(config)
        self.model_b = ModelB_LSTM(config)
        self.meta_model = Ridge(alpha=10.0)  # High alpha to tame scale mismatch
        self.is_trained = False
        
    def prepare_data(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Prepare data for both models"""
        logger.info("Preparing data for ensemble training...")
        
        # Prepare tabular features for XGBoost
        tabular_features = self.model_a.prepare_tabular_features(data.copy())
        
        # Prepare time series data for LSTM - exclude target variable to avoid leakage
        time_series_cols = ['inventory_start', 'qty_used', 'on_order_qty']
        
        # Add additional time series features if available
        optional_cols = ['covers', 'seasonality_factor', 'lead_time_days']
        for col in optional_cols:
            if col in data.columns:
                time_series_cols.append(col)
        
        time_series_data = data[time_series_cols].values
        target = data['inventory_end'].values  # Use inventory_end as target
        
        return tabular_features, time_series_data, target
    
    def train_models_parallel(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Train both models in parallel using ThreadPoolExecutor"""
        logger.info("Starting parallel training of XGBoost and LSTM models...")
        
        # Prepare data
        tabular_features, time_series_data, target = self.prepare_data(data)
        
        # Results storage
        results = {}
        
        def train_xgboost():
            """Training function for XGBoost"""
            try:
                logger.info("Starting XGBoost training thread...")
                metrics = self.model_a.train(tabular_features, target)
                return ('xgboost', metrics)
            except Exception as e:
                logger.error(f"Error training XGBoost: {e}")
                return ('xgboost', {'error': str(e)})
        
        def train_lstm():
            """Training function for LSTM"""
            try:
                logger.info("Starting LSTM training thread...")
                metrics = self.model_b.train(time_series_data, target)
                return ('lstm', metrics)
            except Exception as e:
                logger.error(f"Error training LSTM: {e}")
                return ('lstm', {'error': str(e)})
        
        # Execute training in parallel
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(train_xgboost),
                executor.submit(train_lstm)
            ]
            
            for future in as_completed(futures):
                model_name, metrics = future.result()
                results[model_name] = metrics
                logger.info(f"{model_name.upper()} training completed!")
        
        # Train meta-model if both base models trained successfully
        if 'error' not in results.get('xgboost', {}) and 'error' not in results.get('lstm', {}):
            logger.info("Training meta-model...")
            self._train_meta_model(tabular_features, time_series_data, target)
            results['meta_model'] = {'status': 'trained'}
            self.is_trained = True
        else:
            logger.error("One or both base models failed to train. Cannot train meta-model.")
            results['meta_model'] = {'status': 'failed', 'reason': 'base_model_failure'}
        
        return results
    
    def _train_meta_model(self, tabular_features: np.ndarray, time_series_data: np.ndarray, target: np.ndarray):
        """Train the meta-model using base model predictions"""
        
        # Create sequences for LSTM prediction
        sequences, seq_targets = self.model_b.create_sequences(time_series_data)
        
        # Align tabular features with sequences
        tabular_aligned = tabular_features[self.config.sequence_length:]
        target_aligned = seq_targets[:, 0] if seq_targets.ndim > 1 else seq_targets
        
        # Ensure same length
        min_len = min(len(tabular_aligned), len(sequences), len(target_aligned))
        tabular_aligned = tabular_aligned[:min_len]
        sequences = sequences[:min_len]
        target_aligned = target_aligned[:min_len]
        
        # Get predictions from both models
        xgb_pred = self.model_a.predict(tabular_aligned)
        lstm_pred = self.model_b.predict(sequences)
        
        # Stack predictions as features for meta-model
        meta_features = np.column_stack([xgb_pred, lstm_pred])
        
        # Train meta-model
        self.meta_model.fit(meta_features, target_aligned)
        
        logger.info("Meta-model training completed!")
    
    def predict(self, tabular_features: np.ndarray, time_series_data: np.ndarray) -> np.ndarray:
        """Make ensemble predictions"""
        if not self.is_trained:
            raise ValueError("Ensemble must be trained before making predictions")
        
        # Get predictions from base models
        xgb_pred = self.model_a.predict(tabular_features)
        lstm_pred = self.model_b.predict(time_series_data)
        
        # Stack predictions
        meta_features = np.column_stack([xgb_pred, lstm_pred])
        
        # Get final prediction from meta-model
        return self.meta_model.predict(meta_features)
    
    def save_models(self, save_dir: str):
        """Save all models"""
        os.makedirs(save_dir, exist_ok=True)
        
        # Save XGBoost
        joblib.dump(self.model_a, f"{save_dir}/xgboost_model.pkl")
        
        # Save LSTM
        torch.save(self.model_b.model.state_dict(), f"{save_dir}/lstm_model.pth")
        joblib.dump(self.model_b.feature_scaler, f"{save_dir}/lstm_feature_scaler.pkl")
        
        # Save meta-model
        joblib.dump(self.meta_model, f"{save_dir}/meta_model.pkl")
        
        logger.info(f"All models saved to {save_dir}")
    
    def load_models(self, save_dir: str):
        """Load all models"""
        # Load XGBoost
        self.model_a = joblib.load(f"{save_dir}/xgboost_model.pkl")
        
        # Load LSTM
        self.model_b.feature_scaler = joblib.load(f"{save_dir}/lstm_feature_scaler.pkl")
        self.model_b.model.load_state_dict(torch.load(f"{save_dir}/lstm_model.pth"))
        
        # Load meta-model
        self.meta_model = joblib.load(f"{save_dir}/meta_model.pkl")
        
        self.is_trained = True
        logger.info(f"All models loaded from {save_dir}")

def create_sample_data(n_samples: int = 1000) -> pd.DataFrame:
    """Create sample restaurant inventory data for testing"""
    np.random.seed(42)
    
    dates = pd.date_range('2023-01-01', periods=n_samples, freq='D')
    
    # Base inventory level with trend and seasonality
    trend = np.linspace(100, 120, n_samples)
    seasonal = 10 * np.sin(2 * np.pi * np.arange(n_samples) / 365.25)  # Yearly
    weekly = 5 * np.sin(2 * np.pi * np.arange(n_samples) / 7)  # Weekly
    noise = np.random.normal(0, 3, n_samples)
    
    inventory_level = trend + seasonal + weekly + noise
    
    # Other features
    temperature = 20 + 10 * np.sin(2 * np.pi * np.arange(n_samples) / 365.25) + np.random.normal(0, 2, n_samples)
    precipitation = np.random.exponential(2, n_samples)
    holiday_flag = np.random.binomial(1, 0.05, n_samples)  # 5% chance of holiday
    promotion_flag = np.random.binomial(1, 0.1, n_samples)  # 10% chance of promotion
    special_event = np.random.binomial(1, 0.02, n_samples)  # 2% chance of special event
    
    # Sales data (correlated with inventory)
    sales = 0.8 * inventory_level + np.random.normal(0, 5, n_samples)
    
    df = pd.DataFrame({
        'date': dates,
        'inventory_level': inventory_level,
        'temperature': temperature,
        'precipitation': precipitation,
        'holiday_flag': holiday_flag,
        'promotion_flag': promotion_flag,
        'special_event': special_event,
        'sales': sales
    })
    
    return df

def main():
    """Main training pipeline"""
    logger.info("Starting Restaurant Inventory Forecasting - Stacked Ensemble Training")
    
    # Configuration - Log1p transformation replaces shared target scaler
    config = ModelConfig(
        xgb_params={
            'n_estimators': 1000,
            'max_depth': 6,
            'learning_rate': 0.05,
            'tree_method': 'hist',  # CPU-based tree method
            'objective': 'count:poisson',  # Poisson regression for count data
            'random_state': 42
        },
        lstm_params={
            'hidden_dim': 256,  # Bigger model
            'num_layers': 3,    # Deeper
            'dropout': 0.3,     # More dropout for regularization
            'output_dim': 1
        },
        sequence_length=30,
        batch_size=128
    )
    
    # Create or load data
    logger.info("Loading data...")
    if os.path.exists('/home/quentin/ugaHacks/data/restaurant_inventory.csv'):
        data = pd.read_csv('/home/quentin/ugaHacks/data/restaurant_inventory.csv')
        logger.info(f"Loaded real data with shape: {data.shape}")
    else:
        logger.info("Real data not found. Creating sample data...")
        data = create_sample_data(1500)
        os.makedirs('/home/quentin/ugaHacks/data', exist_ok=True)
        data.to_csv('/home/quentin/ugaHacks/data/restaurant_inventory.csv', index=False)
        logger.info(f"Created sample data with shape: {data.shape}")
    
    # Initialize ensemble
    ensemble = StackedEnsemble(config)
    
    # Train models in parallel
    logger.info("="*50)
    logger.info("STARTING PARALLEL TRAINING")
    logger.info("="*50)
    
    start_time = time.time()
    results = ensemble.train_models_parallel(data)
    total_time = time.time() - start_time
    
    # Print results
    logger.info("="*50)
    logger.info("TRAINING RESULTS")
    logger.info("="*50)
    
    for model_name, metrics in results.items():
        logger.info(f"\n{model_name.upper()} Results:")
        if 'error' in metrics:
            logger.error(f"  ERROR: {metrics['error']}")
        else:
            for metric, value in metrics.items():
                logger.info(f"  {metric}: {value}")
    
    logger.info(f"\nTotal Training Time: {total_time:.2f} seconds")
    
    # Save models if training successful
    if ensemble.is_trained:
        save_dir = '/home/quentin/ugaHacks/models'
        ensemble.save_models(save_dir)
        logger.info("Training completed successfully! Models saved.")
    else:
        logger.error("Training failed. Models not saved.")
    
    return ensemble, results

if __name__ == "__main__":
    ensemble, results = main()