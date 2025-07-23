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
# CHANGELOG: 2025-01-19 - Refactored to use daily spend tables for proper CBF mapping (erik.peterson)
# CHANGELOG: 2025-01-19 - Migrated from pandas to polars for database operations (erik.peterson)
# CHANGELOG: 2025-01-19 - Initial database module for LiteLLM data extraction (erik.peterson)

"""Database connection and data extraction for LiteLLM."""

import polars as pl
import psycopg


class LiteLLMDatabase:
    """Handle LiteLLM PostgreSQL database connections and queries."""

    def __init__(self, connection_string: str):
        """Initialize database connection."""
        self.connection_string = connection_string
        self._connection: psycopg.Connection | None = None

    def connect(self) -> psycopg.Connection:
        """Establish database connection."""
        if self._connection is None or self._connection.closed:
            self._connection = psycopg.connect(self.connection_string)
        return self._connection

    def get_usage_data(self, limit: int | None = None) -> pl.DataFrame:
        """Retrieve consolidated usage data from LiteLLM daily spend tables."""
        # Union query to combine user, team, and tag spend data
        query = """
        WITH consolidated_spend AS (
            -- User spend data
            SELECT
                id,
                date,
                user_id as entity_id,
                'user' as entity_type,
                api_key,
                model,
                model_group,
                custom_llm_provider,
                prompt_tokens,
                completion_tokens,
                spend,
                api_requests,
                successful_requests,
                failed_requests,
                cache_creation_input_tokens,
                cache_read_input_tokens,
                created_at,
                updated_at
            FROM "LiteLLM_DailyUserSpend"

            UNION ALL

            -- Team spend data
            SELECT
                id,
                date,
                team_id as entity_id,
                'team' as entity_type,
                api_key,
                model,
                model_group,
                custom_llm_provider,
                prompt_tokens,
                completion_tokens,
                spend,
                api_requests,
                successful_requests,
                failed_requests,
                cache_creation_input_tokens,
                cache_read_input_tokens,
                created_at,
                updated_at
            FROM "LiteLLM_DailyTeamSpend"

            UNION ALL

            -- Tag spend data
            SELECT
                id,
                date,
                tag as entity_id,
                'tag' as entity_type,
                api_key,
                model,
                model_group,
                custom_llm_provider,
                prompt_tokens,
                completion_tokens,
                spend,
                api_requests,
                successful_requests,
                failed_requests,
                cache_creation_input_tokens,
                cache_read_input_tokens,
                created_at,
                updated_at
            FROM "LiteLLM_DailyTagSpend"
        )
        SELECT * FROM consolidated_spend
        ORDER BY date DESC, created_at DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        conn = self.connect()
        try:
            return pl.read_database(query, conn)
        finally:
            conn.close()

    def get_table_info(self) -> dict:
        """Get information about the consolidated daily spend tables."""
        conn = self.connect()
        try:
            # Get combined row count from both tables
            user_count = self._get_table_row_count(conn, 'LiteLLM_DailyUserSpend')
            team_count = self._get_table_row_count(conn, 'LiteLLM_DailyTeamSpend')
            tag_count = self._get_table_row_count(conn, 'LiteLLM_DailyTagSpend')

            # Get column structure from user spend table (representative)
            query = """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'LiteLLM_DailyUserSpend'
            ORDER BY ordinal_position;
            """
            columns_df = pl.read_database(query, conn)

            return {
                'columns': columns_df.to_dicts(),
                'row_count': user_count + team_count + tag_count,
                'table_breakdown': {
                    'user_spend': user_count,
                    'team_spend': team_count,
                    'tag_spend': tag_count
                }
            }
        finally:
            conn.close()

    def _get_table_row_count(self, conn: psycopg.Connection, table_name: str) -> int:
        """Get row count from specified table."""
        with conn.cursor() as cursor:
            cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            return cursor.fetchone()[0]

    def discover_all_tables(self) -> dict:
        """Discover all tables in the LiteLLM database and their schemas."""
        conn = self.connect()
        try:
            # Get all LiteLLM tables
            litellm_tables_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE 'LiteLLM_%'
            ORDER BY table_name;
            """
            tables_df = pl.read_database(litellm_tables_query, conn)
            table_names = [row['table_name'] for row in tables_df.to_dicts()]

            # Get detailed schema for each table
            tables_info = {}
            for table_name in table_names:
                # Get column information
                columns_query = """
                SELECT 
                    column_name,
                    data_type,
                    is_nullable,
                    column_default,
                    character_maximum_length,
                    numeric_precision,
                    numeric_scale,
                    ordinal_position
                FROM information_schema.columns 
                WHERE table_name = %s
                AND table_schema = 'public'
                ORDER BY ordinal_position;
                """
                columns_df = pl.read_database(columns_query, conn, execute_options={"parameters": [table_name]})

                # Get primary key information
                pk_query = """
                SELECT a.attname
                FROM pg_index i
                JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                WHERE i.indrelid = %s::regclass AND i.indisprimary;
                """
                pk_df = pl.read_database(pk_query, conn, execute_options={"parameters": [f'"{table_name}"']})
                primary_keys = [row['attname'] for row in pk_df.to_dicts()] if not pk_df.is_empty() else []

                # Get foreign key information
                fk_query = """
                SELECT
                    tc.constraint_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = %s;
                """
                fk_df = pl.read_database(fk_query, conn, execute_options={"parameters": [table_name]})
                foreign_keys = fk_df.to_dicts() if not fk_df.is_empty() else []

                # Get indexes
                indexes_query = """
                SELECT
                    i.relname AS index_name,
                    array_agg(a.attname ORDER BY a.attnum) AS column_names,
                    ix.indisunique AS is_unique
                FROM pg_class t
                JOIN pg_index ix ON t.oid = ix.indrelid
                JOIN pg_class i ON i.oid = ix.indexrelid
                JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
                WHERE t.relname = %s
                AND t.relkind = 'r'
                GROUP BY i.relname, ix.indisunique
                ORDER BY i.relname;
                """
                indexes_df = pl.read_database(indexes_query, conn, execute_options={"parameters": [table_name]})
                indexes = indexes_df.to_dicts() if not indexes_df.is_empty() else []

                # Get row count
                try:
                    row_count = self._get_table_row_count(conn, table_name)
                except Exception:
                    row_count = 0

                tables_info[table_name] = {
                    'columns': columns_df.to_dicts(),
                    'primary_keys': primary_keys,
                    'foreign_keys': foreign_keys,
                    'indexes': indexes,
                    'row_count': row_count
                }

            return {
                'tables': tables_info,
                'table_count': len(table_names),
                'table_names': table_names
            }
        finally:
            conn.close()

