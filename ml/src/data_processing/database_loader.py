"""
Database Data Loader for Restaurant ML System
Replaces CSV data loading with direct PostgreSQL integration
"""

import pandas as pd
import logging
from sqlalchemy import create_engine, text
from typing import Optional, Dict, List
import psycopg2
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RestaurantDatabaseLoader:
    """Load restaurant inventory data directly from PostgreSQL database"""
    
    def __init__(self, connection_string: str = 'postgresql://hacks11:hackers11@10.0.0.27:5432/inventory_health'):
        """Initialize database connection"""
        self.connection_string = connection_string
        self.engine = None
        self._connect()
    
    def _connect(self):
        """Establish database connection"""
        try:
            self.engine = create_engine(self.connection_string)
            logger.info("Connected to PostgreSQL database")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def get_available_tables(self) -> List[str]:
        """Get list of available tables in the database"""
        query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """
        df = pd.read_sql_query(query, self.engine)
        return df['table_name'].tolist()
    
    def load_daily_inventory_log(self, limit: Optional[int] = None) -> pd.DataFrame:
        """Load data from daily_inventory_log table"""
        logger.info("Loading daily inventory log data...")
        
        query = """
            SELECT 
                id,
                restaurant_id,
                ingredient_id,
                log_date as date,
                covers,
                seasonality_factor,
                inventory_start,
                qty_used,
                stockout_qty,
                inventory_end,
                on_order_qty,
                avg_daily_usage_7d,
                avg_daily_usage_28d,
                avg_daily_usage_56d,
                units_sold_items_using,
                revenue_items_using
            FROM daily_inventory_log
            ORDER BY restaurant_id, ingredient_id, log_date
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        df = pd.read_sql_query(query, self.engine)
        logger.info(f"Loaded {len(df)} records from daily_inventory_log")
        
        return df
    
    def load_ingredients_data(self) -> pd.DataFrame:
        """Load ingredients reference data"""
        logger.info("Loading ingredients data...")
        
        query = """
            SELECT 
                ingredient_id,
                ingredient_name,
                category,
                unit_cost,
                shelf_life_days,
                unit,
                is_active
            FROM ingredients
            WHERE is_active = true
            ORDER BY ingredient_id
        """
        
        try:
            df = pd.read_sql_query(query, self.engine)
            logger.info(f"Loaded {len(df)} ingredients")
            return df
        except Exception as e:
            logger.warning(f"Could not load ingredients table: {e}")
            return pd.DataFrame()
    
    def load_restaurants_data(self) -> pd.DataFrame:
        """Load restaurants reference data"""
        logger.info("Loading restaurants data...")
        
        query = """
            SELECT 
                restaurant_id,
                restaurant_name,
                timezone,
                is_active
            FROM restaurants
            WHERE is_active = true
            ORDER BY restaurant_id
        """
        
        try:
            df = pd.read_sql_query(query, self.engine)
            logger.info(f"Loaded {len(df)} restaurants")
            return df
        except Exception as e:
            logger.warning(f"Could not load restaurants table: {e}")
            return pd.DataFrame()
    
    def load_training_data(self, days_back: int = 365) -> pd.DataFrame:
        """
        Load comprehensive training data with proper joins to enhanced schema
        
        Args:
            days_back: Number of days of historical data to load
        """
        logger.info(f"Loading training data for last {days_back} days...")
        
        # Calculate date filter
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days_back)
        
        # Enhanced query with proper joins
        query = """
            SELECT 
                dil.id,
                dil.restaurant_id,
                dil.ingredient_id,
                dil.log_date as date,
                dil.covers,
                dil.seasonality_factor,
                dil.inventory_start,
                dil.qty_used,
                dil.stockout_qty,
                dil.inventory_end,
                dil.on_order_qty,
                dil.avg_daily_usage_7d,
                dil.avg_daily_usage_28d,
                dil.avg_daily_usage_56d,
                dil.units_sold_items_using,
                dil.revenue_items_using,
                -- Enhanced ingredient details
                i.ingredient_name,
                i.category as ingredient_category,
                i.unit_cost,
                i.shelf_life_days,
                i.unit,
                -- Restaurant details
                r.restaurant_name,
                r.timezone
            FROM daily_inventory_log dil
            LEFT JOIN ingredients i ON dil.ingredient_id = i.ingredient_id
            LEFT JOIN restaurants r ON dil.restaurant_id = r.restaurant_id  
            WHERE dil.log_date >= %(start_date)s AND dil.log_date <= %(end_date)s
            ORDER BY dil.restaurant_id, dil.ingredient_id, dil.log_date
        """
        
        df = pd.read_sql_query(query, self.engine, params={'start_date': start_date, 'end_date': end_date})
        
        # Add derived features that the ML system expects
        df = self._add_derived_features(df)
        
        logger.info(f"Loaded {len(df)} training records")
        if len(df) > 0:
            logger.info(f"Date range: {df['date'].min()} to {df['date'].max()}")
            logger.info(f"Restaurants: {df['restaurant_id'].nunique()}")
            logger.info(f"Ingredients: {df['ingredient_id'].nunique()}")
            logger.info(f"Categories: {df['ingredient_category'].value_counts().to_dict()}")
        
        return df
    
    def _add_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add derived features that the ML system expects"""
        logger.info("Adding derived features...")
        
        # Ensure date column is datetime
        df['date'] = pd.to_datetime(df['date'])
        
        # Use real ingredient names (no more generic names needed!)
        if 'ingredient_name' not in df.columns:
            df['ingredient_name'] = df['ingredient_id'].apply(lambda x: f"Ingredient_{x}")
        
        # Use real categories from database or set sensible defaults
        if 'ingredient_category' not in df.columns:
            df['ingredient_category'] = 'non_perishable'
        df['category'] = df['ingredient_category']
        
        # Add features the ML system expects
        if 'is_holiday' not in df.columns:
            df['is_holiday'] = 0  # Default to no holidays for now
        
        # Add default lead_time_days if not present
        if 'lead_time_days' not in df.columns:
            df['lead_time_days'] = 2  # Default 2 day lead time
        
        # Rename columns to match ML system expectations
        column_mapping = {
            'units_sold_items_using': 'units_sold_items_using_ing',
            'revenue_items_using': 'revenue_items_using_ing'
        }
        df = df.rename(columns=column_mapping)
        
        # Ensure all required numeric columns exist with reasonable defaults
        numeric_defaults = {
            'covers': 250,
            'seasonality_factor': 1.0,
            'inventory_start': 0,
            'qty_used': 0,
            'inventory_end': 0,
            'on_order_qty': 0,
            'avg_daily_usage_7d': 0,
            'avg_daily_usage_28d': 0,
            'avg_daily_usage_56d': 0,
            'units_sold_items_using_ing': 0,
            'revenue_items_using_ing': 0,
            'lead_time_days': 2,
            'is_holiday': 0,
            'shelf_life_days': 30,  # Will be overwritten by real data from ingredients table
            'unit_cost': 1.0        # Will be overwritten by real data from ingredients table
        }
        
        for col, default_val in numeric_defaults.items():
            if col not in df.columns:
                df[col] = default_val
            else:
                df[col] = df[col].fillna(default_val)
        
        logger.info("Added derived features")
        return df
    
    def get_latest_inventory_snapshot(self) -> pd.DataFrame:
        """Get the most recent inventory state for each ingredient/restaurant with enhanced data"""
        logger.info("Getting latest inventory snapshot...")
        
        query = """
            WITH latest_entries AS (
                SELECT 
                    restaurant_id,
                    ingredient_id,
                    MAX(log_date) as latest_date
                FROM daily_inventory_log
                GROUP BY restaurant_id, ingredient_id
            )
            SELECT 
                dil.id,
                dil.restaurant_id,
                dil.ingredient_id,
                dil.log_date as date,
                dil.covers,
                dil.seasonality_factor,
                dil.inventory_start,
                dil.qty_used,
                dil.stockout_qty,
                dil.inventory_end,
                dil.on_order_qty,
                dil.avg_daily_usage_7d,
                dil.avg_daily_usage_28d,
                dil.avg_daily_usage_56d,
                dil.units_sold_items_using,
                dil.revenue_items_using,
                -- Enhanced ingredient details
                i.ingredient_name,
                i.category as ingredient_category,
                i.unit_cost,
                i.shelf_life_days,
                i.unit,
                -- Restaurant details
                r.restaurant_name,
                r.timezone
            FROM daily_inventory_log dil
            INNER JOIN latest_entries le ON (
                dil.restaurant_id = le.restaurant_id 
                AND dil.ingredient_id = le.ingredient_id
                AND dil.log_date = le.latest_date
            )
            LEFT JOIN ingredients i ON dil.ingredient_id = i.ingredient_id
            LEFT JOIN restaurants r ON dil.restaurant_id = r.restaurant_id
            ORDER BY dil.restaurant_id, dil.ingredient_id
        """
        
        df = pd.read_sql_query(query, self.engine)
        df = self._add_derived_features(df)
        
        logger.info(f"Got latest snapshot: {len(df)} ingredient/restaurant combinations")
        return df
    
    def close(self):
        """Close database connection"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

def test_database_loader():
    """Test the database loader"""
    logger.info("🧪 Testing Restaurant Database Loader")
    logger.info("=" * 50)
    
    try:
        with RestaurantDatabaseLoader() as loader:
            # Test getting available tables
            tables = loader.get_available_tables()
            logger.info(f"📋 Available tables: {tables}")
            
            # Test loading daily inventory log (limited)
            daily_data = loader.load_daily_inventory_log(limit=10)
            logger.info(f"📊 Sample daily data shape: {daily_data.shape}")
            logger.info(f"📊 Sample columns: {daily_data.columns.tolist()}")
            
            # Test loading training data (last 30 days)
            training_data = loader.load_training_data(days_back=30)
            logger.info(f"🧠 Training data shape: {training_data.shape}")
            
            # Test latest snapshot
            snapshot = loader.get_latest_inventory_snapshot()
            logger.info(f"📸 Latest snapshot shape: {snapshot.shape}")
            
            logger.info("✅ Database loader tests completed successfully!")
            
    except Exception as e:
        logger.error(f"❌ Database loader test failed: {e}")
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_database_loader()