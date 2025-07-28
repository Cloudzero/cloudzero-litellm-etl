# SPDX-FileCopyrightText: Copyright (c), CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""SQLite caching layer for LiteLLM database data."""

import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import polars as pl
from rich.console import Console

from .database import LiteLLMDatabase


class DataCache:
    """SQLite-based cache for LiteLLM data with freshness checking."""

    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize cache with specified directory."""
        self.console = Console()

        if cache_dir is None:
            cache_dir = Path.home() / '.ll2cz' / 'cache'

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / 'litellm_data.db'

        self._init_cache_db()

    def _init_cache_db(self) -> None:
        """Initialize SQLite cache database with tables."""
        conn = sqlite3.connect(self.cache_file)
        try:
            # Cache metadata table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Consolidated data table (UNION of user, team, tag spend)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS consolidated_spend (
                    id TEXT NOT NULL,
                    date TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    api_key TEXT,
                    model TEXT,
                    model_group TEXT,
                    custom_llm_provider TEXT,
                    prompt_tokens INTEGER DEFAULT 0,
                    completion_tokens INTEGER DEFAULT 0,
                    spend REAL DEFAULT 0.0,
                    api_requests INTEGER DEFAULT 0,
                    successful_requests INTEGER DEFAULT 0,
                    failed_requests INTEGER DEFAULT 0,
                    cache_creation_input_tokens INTEGER DEFAULT 0,
                    cache_read_input_tokens INTEGER DEFAULT 0,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    PRIMARY KEY (id, entity_type)
                )
            """)

            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entity_type ON consolidated_spend(entity_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_date ON consolidated_spend(date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_model ON consolidated_spend(model)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_provider ON consolidated_spend(custom_llm_provider)")

            conn.commit()
        finally:
            conn.close()

    def _get_connection_hash(self, connection_string: str) -> str:
        """Generate a hash for the database connection for cache key."""
        return hashlib.sha256(connection_string.encode()).hexdigest()[:16]

    def _get_cache_metadata(self, key: str) -> Optional[str]:
        """Get cache metadata value."""
        conn = sqlite3.connect(self.cache_file)
        try:
            cursor = conn.execute("SELECT value FROM cache_metadata WHERE key = ?", (key,))
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            conn.close()

    def _set_cache_metadata(self, key: str, value: str) -> None:
        """Set cache metadata value."""
        conn = sqlite3.connect(self.cache_file)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO cache_metadata (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, value))
            conn.commit()
        finally:
            conn.close()

    def _is_cache_empty(self) -> bool:
        """Check if the cache has any data."""
        conn = sqlite3.connect(self.cache_file)
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM consolidated_spend")
            count = cursor.fetchone()[0]
            return count == 0
        finally:
            conn.close()

    def _check_server_freshness(self, database: LiteLLMDatabase) -> Dict[str, Any]:
        """Check if server data has changed since last cache update."""
        try:
            # Get current server table info
            server_info = database.get_table_info()

            # Get server record counts and max timestamps
            server_stats = {
                'total_records': server_info['row_count'],
                'table_breakdown': server_info['table_breakdown'],
                'check_time': datetime.now().isoformat()
            }

            # Try to get more detailed freshness info (latest timestamps)
            try:
                conn = database.connect()

                # Get latest created_at from each table
                latest_timestamps = {}
                for table_type in ['user', 'team', 'tag']:
                    table_name = f"LiteLLM_Daily{table_type.title()}Spend"
                    try:
                        cursor = conn.cursor()
                        cursor.execute(f'SELECT MAX(created_at) FROM "{table_name}"')
                        result = cursor.fetchone()
                        if result and result[0]:
                            latest_timestamps[table_type] = str(result[0])
                    except Exception:
                        # Table might be empty or not exist
                        latest_timestamps[table_type] = None

                server_stats['latest_timestamps'] = latest_timestamps
                conn.close()

            except Exception:
                # Fallback if detailed timestamp query fails
                server_stats['latest_timestamps'] = {}

            return server_stats

        except Exception as e:
            # Server unavailable
            return {
                'error': str(e),
                'check_time': datetime.now().isoformat(),
                'server_available': False
            }

    def _is_cache_fresh(self, connection_string: str, server_stats: Dict[str, Any]) -> bool:
        """Check if cached data is still fresh compared to server."""
        if server_stats.get('server_available', True) is False:
            # Server unavailable, consider cache fresh (offline mode)
            return True

        conn_hash = self._get_connection_hash(connection_string)
        cache_key = f"server_stats_{conn_hash}"

        # Get cached server stats
        cached_stats_str = self._get_cache_metadata(cache_key)
        if not cached_stats_str:
            return False

        try:
            import json
            cached_stats = json.loads(cached_stats_str)

            # Compare record counts
            if cached_stats.get('total_records') != server_stats.get('total_records'):
                return False

            # Compare table breakdown
            cached_breakdown = cached_stats.get('table_breakdown', {})
            server_breakdown = server_stats.get('table_breakdown', {})
            if cached_breakdown != server_breakdown:
                return False

            # Compare latest timestamps if available
            cached_timestamps = cached_stats.get('latest_timestamps', {})
            server_timestamps = server_stats.get('latest_timestamps', {})
            if cached_timestamps != server_timestamps:
                return False

            return True

        except (json.JSONDecodeError, KeyError):
            return False

    def _update_cache(self, database: LiteLLMDatabase, connection_string: str) -> None:
        """Update cache with fresh data from server."""
        self.console.print("[blue]Updating local cache with fresh data...[/blue]")

        # Get all data from server
        try:
            data = database.get_usage_data()
            self.console.print(f"[dim]Fetched {len(data):,} records from server[/dim]")
        except Exception as e:
            self.console.print(f"[red]Error fetching data from server: {e}[/red]")
            return

        if data.is_empty():
            self.console.print("[yellow]No data found on server[/yellow]")
            return

        # Clear existing cache data
        conn = sqlite3.connect(self.cache_file)
        try:
            conn.execute("DELETE FROM consolidated_spend")

            # Insert new data with dynamic column handling
            records = data.to_dicts()
            if records:
                # Get column names from actual data
                columns = list(records[0].keys())
                placeholders = ', '.join(['?' for _ in columns])
                column_names = ', '.join(columns)

                insert_sql = f"INSERT INTO consolidated_spend ({column_names}) VALUES ({placeholders})"

                for record in records:
                    values = [record.get(col) for col in columns]
                    conn.execute(insert_sql, values)

            conn.commit()

            # Update cache metadata
            server_stats = self._check_server_freshness(database)
            conn_hash = self._get_connection_hash(connection_string)
            cache_key = f"server_stats_{conn_hash}"

            import json
            self._set_cache_metadata(cache_key, json.dumps(server_stats))
            self._set_cache_metadata(f"last_update_{conn_hash}", datetime.now().isoformat())

            self.console.print(f"[green]Cache updated with {len(records):,} records[/green]")

        finally:
            conn.close()

    def _check_schema_mismatch(self, database: LiteLLMDatabase, connection_string: str) -> bool:
        """Check if the database schema has changed compared to cached schema."""
        try:
            # Get current database columns from fresh data sample
            fresh_data = database.get_usage_data()
            if fresh_data.is_empty():
                return False

            database_columns = set(fresh_data.columns)

            # Get cached table columns
            conn = sqlite3.connect(self.cache_file)
            try:
                cursor = conn.execute("PRAGMA table_info(consolidated_spend)")
                cache_columns = {row[1] for row in cursor.fetchall()}
            finally:
                conn.close()

            # Check if database has columns that cache doesn't have
            missing_columns = database_columns - cache_columns
            if missing_columns:
                self.console.print(f"[dim]Cache missing columns: {', '.join(sorted(missing_columns))}[/dim]")
                return True

            return False

        except Exception:
            # If we can't check schema, assume no mismatch
            return False

    def _recreate_cache_schema(self, database: LiteLLMDatabase) -> None:
        """Recreate cache table schema to match current database schema."""
        try:
            # Get fresh data to determine all columns and their types
            fresh_data = database.get_usage_data()
            if fresh_data.is_empty():
                return

            conn = sqlite3.connect(self.cache_file)
            try:
                # Drop existing table
                conn.execute("DROP TABLE IF EXISTS consolidated_spend")

                # Create new table with dynamic schema based on actual data
                # Use polars schema info to determine SQLite column types
                column_definitions = []

                for col_name, polars_dtype in fresh_data.schema.items():
                    # Map polars types to SQLite types
                    if polars_dtype in [pl.Int32, pl.Int64]:
                        sql_type = "INTEGER"
                    elif polars_dtype in [pl.Float32, pl.Float64]:
                        sql_type = "REAL"
                    elif polars_dtype == pl.Boolean:
                        sql_type = "INTEGER"  # SQLite stores booleans as integers
                    else:
                        sql_type = "TEXT"

                    # Handle special columns
                    if col_name in ['id', 'entity_type']:
                        column_definitions.append(f"{col_name} {sql_type} NOT NULL")
                    else:
                        column_definitions.append(f"{col_name} {sql_type}")

                # Create table with dynamic schema
                create_sql = f"""
                    CREATE TABLE consolidated_spend (
                        {', '.join(column_definitions)},
                        PRIMARY KEY (id, entity_type)
                    )
                """
                conn.execute(create_sql)

                # Recreate indexes for performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_entity_type ON consolidated_spend(entity_type)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_date ON consolidated_spend(date)")
                if 'model' in fresh_data.columns:
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_model ON consolidated_spend(model)")
                if 'custom_llm_provider' in fresh_data.columns:
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_provider ON consolidated_spend(custom_llm_provider)")

                conn.commit()
                self.console.print("[blue]Cache schema updated to match database[/blue]")

            finally:
                conn.close()

        except Exception as e:
            self.console.print(f"[red]Failed to recreate cache schema: {e}[/red]")

    def get_cached_data(self, database: Optional[LiteLLMDatabase], connection_string: str,
                       limit: Optional[int] = None, force_refresh: bool = False) -> pl.DataFrame:
        """Get data from cache, refreshing if necessary.

        Note: force_refresh is kept for internal use by the refresh_cache command.
        Users should use 'cache refresh' command to update cache."""

        # First check if cache is empty and force refresh if so
        cache_empty = self._is_cache_empty()
        if cache_empty and database is not None:
            self.console.print("[blue]Cache is empty - forcing initial refresh...[/blue]")
            force_refresh = True

        # Check if we should use server or cache
        if database is not None:
            # Check for schema mismatch and force refresh if needed
            schema_mismatch = self._check_schema_mismatch(database, connection_string)
            if schema_mismatch:
                self.console.print("[blue]Schema change detected - forcing cache refresh...[/blue]")
                force_refresh = True

            server_stats = self._check_server_freshness(database)
            server_available = server_stats.get('server_available', True)

            if server_available:
                if force_refresh or not self._is_cache_fresh(connection_string, server_stats):
                    if schema_mismatch:
                        self._recreate_cache_schema(database)
                    self._update_cache(database, connection_string)
                else:
                    self.console.print("[dim]Using cached data (fresh)[/dim]")
            else:
                self.console.print("[yellow]⚠️  Server unavailable - using cached data (may be out of date)[/yellow]")
        else:
            self.console.print("[yellow]⚠️  No server connection - using cached data (may be out of date)[/yellow]")

        # Load data from cache
        query = "SELECT * FROM consolidated_spend ORDER BY date DESC, created_at DESC"
        if limit:
            query += f" LIMIT {limit}"

        conn = sqlite3.connect(self.cache_file)
        try:
            # Use polars to read from SQLite
            result = pl.read_database(query, conn)
            if result.is_empty():
                self.console.print("[dim]Cache is empty - no data available[/dim]")
            return result
        finally:
            conn.close()

    def get_cache_info(self, connection_string: str) -> Dict[str, Any]:
        """Get information about cached data."""
        conn_hash = self._get_connection_hash(connection_string)

        # Get cache metadata
        last_update = self._get_cache_metadata(f"last_update_{conn_hash}")
        server_stats_str = self._get_cache_metadata(f"server_stats_{conn_hash}")

        # Get cache record count
        conn = sqlite3.connect(self.cache_file)
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM consolidated_spend")
            cache_count = cursor.fetchone()[0]

            # Get cache breakdown by entity type
            cursor = conn.execute("""
                SELECT entity_type, COUNT(*)
                FROM consolidated_spend
                GROUP BY entity_type
            """)
            breakdown = dict(cursor.fetchall())

        finally:
            conn.close()

        result = {
            'cache_file': str(self.cache_file),
            'record_count': cache_count,
            'breakdown': breakdown,
            'last_update': last_update
        }

        if server_stats_str:
            try:
                import json
                result['server_stats'] = json.loads(server_stats_str)
            except json.JSONDecodeError:
                pass

        return result

    def clear_cache(self, connection_string: Optional[str] = None) -> None:
        """Clear cached data."""
        conn = sqlite3.connect(self.cache_file)
        try:
            conn.execute("DELETE FROM consolidated_spend")

            if connection_string:
                # Clear specific connection metadata
                conn_hash = self._get_connection_hash(connection_string)
                conn.execute("DELETE FROM cache_metadata WHERE key LIKE ?", (f"%{conn_hash}%",))
            else:
                # Clear all metadata
                conn.execute("DELETE FROM cache_metadata")

            conn.commit()
            self.console.print("[green]Cache cleared[/green]")
        finally:
            conn.close()
