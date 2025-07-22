# Copyright 2025 CloudZero
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# CHANGELOG: 2025-01-20 - Initial cached database wrapper for offline support (erik.peterson)

"""Cached database wrapper that provides offline support and data freshness management."""

from typing import Any, Optional

import polars as pl

from .cache import DataCache
from .database import LiteLLMDatabase


class CachedLiteLLMDatabase:
    """Cached wrapper for LiteLLM database with offline support."""

    def __init__(self, connection_string: Optional[str] = None, cache_dir: Optional[str] = None):
        """Initialize cached database wrapper."""
        self.connection_string = connection_string
        self.cache = DataCache(cache_dir)
        
        # Only create database connection if connection string provided
        self.database: Optional[LiteLLMDatabase] = None
        if connection_string:
            try:
                self.database = LiteLLMDatabase(connection_string)
                # Test connection
                conn = self.database.connect()
                conn.close()
            except Exception:
                # Server unavailable, will use cache only
                self.database = None

    def get_usage_data(self, limit: Optional[int] = None, force_refresh: bool = False) -> pl.DataFrame:
        """Get usage data from cache, refreshing from server if needed."""
        if not self.connection_string:
            raise ValueError("No database connection string provided")
        
        return self.cache.get_cached_data(
            self.database, 
            self.connection_string, 
            limit=limit, 
            force_refresh=force_refresh
        )

    def get_table_info(self) -> dict[str, Any]:
        """Get table information from cache."""
        # Force a cache refresh if empty, then get fresh cache info
        if self.cache._is_cache_empty() and self.database:
            try:
                self.cache.get_cached_data(self.database, self.connection_string or "", limit=1)
            except Exception:
                pass  # Ignore errors, continue with empty cache
        
        cache_info = self.cache.get_cache_info(self.connection_string or "")
        
        # Convert cache info to match original table_info format
        breakdown = cache_info.get('breakdown', {})
        
        # Map cache breakdown to expected format
        table_breakdown = {
            'user_spend': breakdown.get('user', 0),
            'team_spend': breakdown.get('team', 0), 
            'tag_spend': breakdown.get('tag', 0)
        }
        
        # Get sample data to determine columns
        try:
            sample_data = self.cache.get_cached_data(self.database, self.connection_string or "", limit=1)
            columns = sample_data.columns if not sample_data.is_empty() else []
        except Exception:
            columns = []
        
        return {
            'row_count': cache_info.get('record_count', 0),
            'table_breakdown': table_breakdown,
            'columns': columns,
            'cache_info': cache_info
        }

    def get_table_info_local_only(self) -> dict[str, Any]:
        """Get table information from cache only (no remote calls)."""
        cache_info = self.cache.get_cache_info(self.connection_string or "")
        
        # Convert cache info to match original table_info format
        breakdown = cache_info.get('breakdown', {})
        
        # Map cache breakdown to expected format
        table_breakdown = {
            'user_spend': breakdown.get('user', 0),
            'team_spend': breakdown.get('team', 0), 
            'tag_spend': breakdown.get('tag', 0)
        }
        
        # Get columns from cache metadata or use default known columns
        columns = [
            'id', 'date', 'entity_id', 'entity_type', 'api_key', 'model', 'model_group',
            'custom_llm_provider', 'prompt_tokens', 'completion_tokens', 'spend',
            'api_requests', 'successful_requests', 'failed_requests', 
            'cache_creation_input_tokens', 'cache_read_input_tokens', 'created_at', 'updated_at'
        ]
        
        return {
            'row_count': cache_info.get('record_count', 0),
            'table_breakdown': table_breakdown,
            'columns': columns,
            'cache_info': cache_info
        }

    def get_individual_table_data(self, table_type: str, limit: Optional[int] = None, force_refresh: bool = False) -> pl.DataFrame:
        """Get data from a specific table type (user/team/tag)."""
        if not self.connection_string:
            raise ValueError("No database connection string provided")
        
        # Get cached data and filter by entity type
        data = self.cache.get_cached_data(self.database, self.connection_string, force_refresh=force_refresh)
        
        # Filter by entity type
        filtered_data = data.filter(pl.col('entity_type') == table_type)
        
        if limit:
            filtered_data = filtered_data.head(limit)
        
        return filtered_data

    def discover_all_tables(self) -> dict[str, Any]:
        """Discover all tables - requires live database connection."""
        if not self.database:
            raise ConnectionError("Database discovery requires active server connection")
        
        return self.database.discover_all_tables()

    def clear_cache(self) -> None:
        """Clear the local cache."""
        self.cache.clear_cache(self.connection_string)

    def refresh_cache(self) -> None:
        """Force refresh the cache from server."""
        if not self.database or not self.connection_string:
            raise ConnectionError("Cache refresh requires active server connection")
        
        self.cache.get_cached_data(self.database, self.connection_string, force_refresh=True)

    def get_cache_status(self) -> dict[str, Any]:
        """Get detailed cache status information (local cache only, no remote calls)."""
        if not self.connection_string:
            return {"error": "No connection string configured"}
        
        cache_info = self.cache.get_cache_info(self.connection_string)
        
        # Add server connectivity status (based on initialization, no remote call)
        cache_info['server_available'] = self.database is not None
        cache_info['connection_string_hash'] = self.cache._get_connection_hash(self.connection_string)
        
        return cache_info

    def is_offline_mode(self) -> bool:
        """Check if currently operating in offline mode."""
        return self.database is None