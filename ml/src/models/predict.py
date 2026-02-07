"""
Restaurant Inventory Forecasting - Prediction Module
Use trained ensemble to make predictions on new data
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from inventory_forecasting import *
import matplotlib.pyplot as plt
import seaborn as sns

class InventoryPredictor:
    """Production-ready predictor using trained ensemble"""
    
    def __init__(self, model_dir: str = '/home/quentin/ugaHacks/models'):
        self.model_dir = model_dir
        self.ensemble = None
        self.is_loaded = False
        
    def load_ensemble(self):
        """Load trained ensemble models"""
        if not os.path.exists(self.model_dir):
            raise FileNotFoundError(f"Model directory not found: {self.model_dir}")
        
        # Initialize ensemble with dummy config (will be overridden by loaded models)
        config = ModelConfig(
            xgb_params={},
            lstm_params={'hidden_dim': 128, 'num_layers': 2, 'dropout': 0.2, 'output_dim': 1}
        )
        
        self.ensemble = StackedEnsemble(config)
        self.ensemble.load_models(self.model_dir)
        self.is_loaded = True
        
        logger.info("✅ Ensemble models loaded successfully!")
    
    def predict_inventory(self, data: pd.DataFrame, forecast_days: int = 7) -> Dict[str, np.ndarray]:
        """Predict future inventory levels"""
        if not self.is_loaded:
            self.load_ensemble()
        
        # Prepare features
        tabular_features, time_series_data, _ = self.ensemble.prepare_data(data)
        
        # Make predictions for available data
        predictions = []
        dates = []
        
        # Get predictions for existing sequences
        sequences, _ = self.ensemble.model_b.create_sequences(time_series_data)
        tabular_aligned = tabular_features[self.ensemble.config.sequence_length:]
        
        # Ensure alignment
        min_len = min(len(tabular_aligned), len(sequences))
        tabular_aligned = tabular_aligned[:min_len]
        sequences = sequences[:min_len]
        
        # Get ensemble predictions
        ensemble_pred = self.ensemble.predict(tabular_aligned, sequences)
        
        # Get individual model predictions for comparison
        xgb_pred = self.ensemble.model_a.predict(tabular_aligned)
        lstm_pred = self.ensemble.model_b.predict(sequences)
        
        return {
            'ensemble': ensemble_pred,
            'xgboost': xgb_pred,
            'lstm': lstm_pred,
            'dates': data['date'].iloc[self.ensemble.config.sequence_length:].values[:min_len]
        }
    
    def plot_predictions(self, data: pd.DataFrame, predictions: Dict[str, np.ndarray], 
                        save_path: str = None):
        """Plot actual vs predicted inventory levels"""
        
        plt.figure(figsize=(15, 10))
        
        # Get actual values
        actual = data['inventory_level'].iloc[self.ensemble.config.sequence_length:].values
        dates = predictions['dates']
        
        # Ensure same length
        min_len = min(len(actual), len(predictions['ensemble']))
        actual = actual[:min_len]
        
        # Main plot - Ensemble vs Actual
        plt.subplot(2, 2, 1)
        plt.plot(dates[:min_len], actual, 'b-', label='Actual', alpha=0.8, linewidth=2)
        plt.plot(dates[:min_len], predictions['ensemble'][:min_len], 'r-', label='Ensemble', alpha=0.8, linewidth=2)
        plt.title('Ensemble Predictions vs Actual', fontsize=14, fontweight='bold')
        plt.xlabel('Date')
        plt.ylabel('Inventory Level')
        plt.legend()
        plt.xticks(rotation=45)
        plt.grid(True, alpha=0.3)
        
        # Individual model comparisons
        plt.subplot(2, 2, 2)
        plt.plot(dates[:min_len], actual, 'b-', label='Actual', alpha=0.8)
        plt.plot(dates[:min_len], predictions['xgboost'][:min_len], 'g--', label='XGBoost', alpha=0.8)
        plt.plot(dates[:min_len], predictions['lstm'][:min_len], 'orange', linestyle=':', label='LSTM', alpha=0.8)
        plt.title('Individual Model Predictions', fontsize=14, fontweight='bold')
        plt.xlabel('Date')
        plt.ylabel('Inventory Level')
        plt.legend()
        plt.xticks(rotation=45)
        plt.grid(True, alpha=0.3)
        
        # Residuals plot
        plt.subplot(2, 2, 3)
        residuals = actual - predictions['ensemble'][:min_len]
        plt.scatter(predictions['ensemble'][:min_len], residuals, alpha=0.6, c='red')
        plt.axhline(y=0, color='black', linestyle='--')
        plt.title('Residuals Plot', fontsize=14, fontweight='bold')
        plt.xlabel('Predicted Values')
        plt.ylabel('Residuals')
        plt.grid(True, alpha=0.3)
        
        # Error distribution
        plt.subplot(2, 2, 4)
        plt.hist(residuals, bins=30, alpha=0.7, color='skyblue', edgecolor='black')
        plt.axvline(x=0, color='red', linestyle='--')
        plt.title('Residuals Distribution', fontsize=14, fontweight='bold')
        plt.xlabel('Residuals')
        plt.ylabel('Frequency')
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Plot saved to: {save_path}")
        
        plt.show()
    
    def evaluate_predictions(self, data: pd.DataFrame, predictions: Dict[str, np.ndarray]) -> Dict[str, Dict[str, float]]:
        """Evaluate prediction accuracy"""
        
        actual = data['inventory_level'].iloc[self.ensemble.config.sequence_length:].values
        min_len = min(len(actual), len(predictions['ensemble']))
        actual = actual[:min_len]
        
        results = {}
        
        for model_name, pred in predictions.items():
            if model_name == 'dates':
                continue
                
            pred_trimmed = pred[:min_len]
            
            results[model_name] = {
                'RMSE': np.sqrt(mean_squared_error(actual, pred_trimmed)),
                'MAE': mean_absolute_error(actual, pred_trimmed),
                'R²': r2_score(actual, pred_trimmed),
                'MAPE': np.mean(np.abs((actual - pred_trimmed) / actual)) * 100
            }
        
        return results

def demo_prediction():
    """Demo prediction on sample or real data"""
    logger.info("🔮 Restaurant Inventory Forecasting - Prediction Demo")
    logger.info("=" * 60)
    
    # Initialize predictor
    predictor = InventoryPredictor()
    
    try:
        predictor.load_ensemble()
    except FileNotFoundError:
        logger.error("❌ No trained models found! Please run training first.")
        logger.info("💡 Run: python quick_train.py")
        return
    
    # Load test data
    data_path = '/home/quentin/ugaHacks/data/restaurant_inventory.csv'
    if os.path.exists(data_path):
        data = pd.read_csv(data_path)
        logger.info(f"📁 Loaded data from: {data_path}")
    else:
        logger.info("📊 Creating sample data for demo...")
        data = create_sample_data(500)
    
    # Make predictions
    logger.info("🎯 Making predictions...")
    predictions = predictor.predict_inventory(data)
    
    # Evaluate
    logger.info("📊 Evaluating predictions...")
    evaluation = predictor.evaluate_predictions(data, predictions)
    
    # Print results
    logger.info("\n" + "=" * 60)
    logger.info("📈 PREDICTION EVALUATION")
    logger.info("=" * 60)
    
    for model, metrics in evaluation.items():
        logger.info(f"\n{model.upper()}:")
        for metric, value in metrics.items():
            logger.info(f"  {metric}: {value:.4f}")
    
    # Create visualization
    logger.info("\n📊 Creating visualization...")
    plot_path = '/home/quentin/ugaHacks/prediction_results.png'
    predictor.plot_predictions(data, predictions, save_path=plot_path)
    
    return predictor, predictions, evaluation

if __name__ == "__main__":
    demo_prediction()