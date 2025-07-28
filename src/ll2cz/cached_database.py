# SPDX-FileCopyrightText: Copyright (c), CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Cached database wrapper that provides offline support and data freshness management."""

from typing import Any, Dict, Optional

import polars as pl
from rich.console import Console

from .cache import DataCache
from .database import LiteLLMDatabase


class CachedLiteLLMDatabase:
    """Cached wrapper for LiteLLM database with offline support."""

    def __init__(self, connection_string: Optional[str] = None, cache_dir: Optional[str] = None):
        """Initialize cached database wrapper."""
        self.connection_string = connection_string
        self.cache = DataCache(cache_dir)
        self.console = Console()

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

    def get_usage_data(self, limit: Optional[int] = None) -> pl.DataFrame:
        """Get usage data from cache."""
        if not self.connection_string:
            raise ValueError("No database connection string provided")

        return self.cache.get_cached_data(
            self.database,
            self.connection_string,
            limit=limit,
            force_refresh=False
        )

    def get_spend_analysis_data(self, limit: Optional[int] = None) -> pl.DataFrame:
        """Get spend analysis data from database directly (bypasses cache for fresh data)."""
        if not self.connection_string:
            raise ValueError("No database connection string provided")

        # For spend analysis, get fresh data directly from database to include both user and team data
        if not self.database:
            self.database = LiteLLMDatabase(self.connection_string)

        return self.database.get_spend_analysis_data(limit=limit)

    def get_table_info(self) -> Dict[str, Any]:
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

    def get_table_info_local_only(self) -> Dict[str, Any]:
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

        # Get columns from cache metadata or use default known columns (including enriched fields)
        columns = [
            'id', 'date', 'entity_id', 'entity_type', 'api_key', 'model', 'model_group',
            'custom_llm_provider', 'prompt_tokens', 'completion_tokens', 'spend',
            'api_requests', 'successful_requests', 'failed_requests',
            'cache_creation_input_tokens', 'cache_read_input_tokens', 'created_at', 'updated_at',
            # Enriched API key information
            'key_name', 'key_alias',
            # Enriched user information
            'user_alias', 'user_email',
            # Enriched team information
            'team_alias', 'team_id',
            # Enriched organization information
            'organization_alias', 'organization_id'
        ]

        return {
            'row_count': cache_info.get('record_count', 0),
            'table_breakdown': table_breakdown,
            'columns': columns,
            'cache_info': cache_info
        }

    def get_individual_table_data(self, table_type: str, limit: Optional[int] = None) -> pl.DataFrame:
        """Get data from a specific table type (user/team/tag/logs) directly from the raw table."""
        if not self.connection_string:
            raise ValueError("No database connection string provided")

        # For raw table access, we need to query the database directly if available
        # This ensures we get the actual raw table data, not the enriched/combined data
        if self.database:
            # Use the direct database query to get raw table data
            try:
                result = self.database.get_individual_table_data(table_type, limit=limit)
                return result
            except Exception as e:
                # If direct query fails, log the error and try fallback
                self.console.print(f"[yellow]Warning: Direct table query failed: {e}[/yellow]")
                self.console.print("[yellow]Falling back to cached data[/yellow]")

        # SpendLogs data is not cached, so if database is not available, raise error
        if table_type == 'logs':
            raise ConnectionError("SpendLogs data requires active server connection")

        # Fallback to filtering cached data if no database connection or if direct query failed
        # This is not ideal but allows offline mode to work
        data = self.cache.get_cached_data(self.database, self.connection_string)

        # Filter by entity type
        filtered_data = data.filter(pl.col('entity_type') == table_type)

        if limit:
            filtered_data = filtered_data.head(limit)

        return filtered_data

    def discover_all_tables(self) -> Dict[str, Any]:
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

    def get_cache_status(self) -> Dict[str, Any]:
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

    def get_spend_logs_data(self, limit: Optional[int] = None) -> pl.DataFrame:
        """Get SpendLogs data from database (no caching for transaction-level data)."""
        if not self.database:
            raise ConnectionError("SpendLogs data requires active server connection")

        return self.database.get_spend_logs_data(limit=limit)

    def get_spend_logs_for_analysis(self, limit: Optional[int] = None) -> pl.DataFrame:
        """Get enriched SpendLogs data for CZRN/CBF analysis (no caching for transaction-level data)."""
        if not self.database:
            raise ConnectionError("SpendLogs analysis data requires active server connection")

        return self.database.get_spend_logs_for_analysis(limit=limit)
