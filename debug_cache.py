#!/usr/bin/env python3

"""Debug script to test cache functionality."""

import tempfile
from pathlib import Path
import polars as pl

from src.ll2cz.cache import DataCache
from src.ll2cz.cached_database import CachedLiteLLMDatabase

def test_cache_basic():
    """Test basic cache functionality."""
    print("Testing basic cache functionality...")
    
    # Create temporary cache directory
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir)
        cache = DataCache(cache_dir)
        
        print(f"Cache file: {cache.cache_file}")
        print(f"Cache dir exists: {cache_dir.exists()}")
        print(f"Cache file exists: {cache.cache_file.exists()}")
        
        # Test with no database connection (offline mode)
        cached_db = CachedLiteLLMDatabase(None, cache_dir)
        print(f"Is offline mode: {cached_db.is_offline_mode()}")
        
        # Test cache status
        cache_info = cached_db.get_cache_status()
        print(f"Cache status: {cache_info}")

def test_empty_cache():
    """Test what happens with empty cache."""
    print("\nTesting empty cache...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir)
        
        # Create database with fake connection
        cached_db = CachedLiteLLMDatabase("postgresql://fake:fake@localhost/fake", cache_dir)
        print(f"Is offline mode: {cached_db.is_offline_mode()}")
        
        try:
            # This should fail gracefully and return empty data
            data = cached_db.get_usage_data(limit=10)
            print(f"Got data: {len(data)} records")
            print(f"Data columns: {data.columns if not data.is_empty() else 'No data'}")
        except Exception as e:
            print(f"Error getting data: {e}")
        
        # Test table info with empty cache
        try:
            table_info = cached_db.get_table_info()
            print(f"Table info: {table_info}")
        except Exception as e:
            print(f"Error getting table info: {e}")

if __name__ == "__main__":
    test_cache_basic()
    test_empty_cache()