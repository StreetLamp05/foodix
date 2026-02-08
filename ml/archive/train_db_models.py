"""
Database-based Training Script - Full Training Mode
Train models using real data from PostgreSQL database with full configuration
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from training.inventory_forecasting import *
from data_processing.database_loader import RestaurantDatabaseLoader
import pandas as pd
import numpy as np

def main():
    """Main training pipeline using database data"""
    logger.info("Starting Restaurant Inventory Forecasting - Full Database Training")
    
    # Full production configuration
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
    
    # Load real data from database
    logger.info("Loading data from PostgreSQL database...")
    with RestaurantDatabaseLoader() as db:
        # Get comprehensive training data (last year)
        data = db.load_training_data(days_back=365)
        
        if data.empty:
            logger.error("No training data available from database")
            return None, None
            
        logger.info(f"Loaded real database data with shape: {data.shape}")
        logger.info(f"Date range: {data['date'].min()} to {data['date'].max()}")
        logger.info(f"Restaurants: {data['restaurant_id'].nunique()}")
        logger.info(f"Ingredients: {data['ingredient_id'].nunique()}")
    
    # Initialize ensemble
    logger.info("Initializing Stacked Ensemble...")
    ensemble = StackedEnsemble(config)
    
    # Train models
    logger.info("Starting parallel multi-GPU training...")
    try:
        results = ensemble.train_models_parallel(data)
        
        logger.info("Training Results:")
        for key, value in results.items():
            if isinstance(value, (int, float)):
                logger.info(f"{key}: {value:.4f}")
            else:
                logger.info(f"{key}: {value}")
        
        # Save models
        save_dir = "/home/quentin/ugaHacks/models"
        logger.info(f"Saving trained models to {save_dir}...")
        ensemble.save_models(save_dir)
        logger.info("Models saved successfully.")
        
        # Test model loading
        logger.info("Testing model loading...")
        test_ensemble = StackedEnsemble(config)
        test_ensemble.load_models(save_dir)
        logger.info("Model loading test successful!")
        
    except Exception as e:
        logger.error(f"Training failed: {e}")
        import traceback
        traceback.print_exc()
        logger.error("Training failed. Models not saved.")
        return None, None
    
    return ensemble, results

if __name__ == "__main__":
    ensemble, results = main()