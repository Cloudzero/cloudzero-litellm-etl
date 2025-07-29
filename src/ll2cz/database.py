# SPDX-FileCopyrightText: Copyright (c), CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Database connection and data extraction for LiteLLM with SQLite support."""

import sqlite3
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse

import polars as pl
import psycopg


class LiteLLMDatabase:
    """Handle LiteLLM PostgreSQL and SQLite database connections and queries."""

    def __init__(self, connection_string: str):
        """Initialize database connection."""
        self.connection_string = connection_string
        self._connection: Optional[Union[psycopg.Connection, sqlite3.Connection]] = None

        # Parse connection string to determine database type
        parsed = urlparse(connection_string)
        self.db_type = 'sqlite' if parsed.scheme == 'sqlite' else 'postgresql'

        # For SQLite, extract the path
        if self.db_type == 'sqlite':
            # Handle various SQLite URL formats
            if connection_string.startswith('sqlite:///'):
                self.sqlite_path = connection_string[10:]  # Remove sqlite:///
            elif connection_string.startswith('sqlite://'):
                self.sqlite_path = connection_string[9:]   # Remove sqlite://
            else:
                self.sqlite_path = parsed.path.lstrip('/')

    def connect(self) -> Union[psycopg.Connection, sqlite3.Connection]:
        """Establish database connection."""
        if self.db_type == 'sqlite':
            if self._connection is None:
                self._connection = sqlite3.connect(self.sqlite_path)
                # Enable foreign keys in SQLite
                self._connection.execute("PRAGMA foreign_keys = ON")
            return self._connection
        else:
            if self._connection is None or self._connection.closed:
                self._connection = psycopg.connect(self.connection_string)
            return self._connection

    def _quote_table(self, table_name: str) -> str:
        """Quote table name based on database type."""
        if self.db_type == 'sqlite':
            return table_name  # SQLite doesn't require quotes
        else:
            return f'"{table_name}"'  # PostgreSQL uses double quotes

    def _close_connection(self, conn):
        """Close connection based on database type."""
        if self.db_type == 'postgresql':
            conn.close()

    def _adapt_query_for_db(self, query: str) -> str:
        """Adapt query syntax for specific database."""
        if self.db_type == 'sqlite':
            # Remove PostgreSQL-specific syntax
            query = query.replace('::text', '')
            query = query.replace('::integer', '')
            query = query.replace('::decimal', '')
            query = query.replace('::boolean', '')
            query = query.replace('::timestamp', '')
            query = query.replace('::date', '')
            # Remove double quotes around table names
            for table in ['LiteLLM_DailyUserSpend', 'LiteLLM_DailyTeamSpend', 'LiteLLM_DailyTagSpend',
                          'LiteLLM_SpendLogs', 'LiteLLM_VerificationToken', 'LiteLLM_UserTable',
                          'LiteLLM_TeamTable', 'LiteLLM_OrganizationTable']:
                query = query.replace(f'"{table}"', table)
        return query

    def get_usage_data(self, limit: Optional[int] = None) -> pl.DataFrame:
        """Retrieve enriched usage data from LiteLLM DailyUserSpend table."""
        query = f"""
        SELECT
            s.id,
            s.date,
            s.user_id as entity_id,
            'user' as entity_type,
            s.api_key,
            s.model,
            s.model_group,
            s.custom_llm_provider,
            s.prompt_tokens,
            s.completion_tokens,
            s.spend,
            s.api_requests,
            s.successful_requests,
            s.failed_requests,
            s.cache_creation_input_tokens,
            s.cache_read_input_tokens,
            s.created_at,
            s.updated_at,
            vt.key_name,
            vt.key_alias,
            u.user_alias,
            u.user_email,
            t.team_alias,
            t.team_id,
            o.organization_alias,
            o.organization_id
        FROM {self._quote_table('LiteLLM_DailyUserSpend')} s
        LEFT JOIN {self._quote_table('LiteLLM_VerificationToken')} vt ON s.api_key = vt.token
        LEFT JOIN {self._quote_table('LiteLLM_UserTable')} u ON vt.user_id = u.user_id
        LEFT JOIN {self._quote_table('LiteLLM_TeamTable')} t ON vt.team_id = t.team_id
        LEFT JOIN {self._quote_table('LiteLLM_OrganizationTable')} o ON vt.organization_id = o.organization_id
        ORDER BY s.date DESC, s.created_at DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        conn = self.connect()
        try:
            return pl.read_database(query, conn)
        finally:
            self._close_connection(conn)

    def get_spend_analysis_data(self, limit: Optional[int] = None) -> pl.DataFrame:
        """Retrieve consolidated spend data from user and team tables."""
        query = f"""
        WITH consolidated_spend AS (
            SELECT
                s.id,
                s.date,
                s.user_id{'::text' if self.db_type == 'postgresql' else ''} as entity_id,
                'user'{'::text' if self.db_type == 'postgresql' else ''} as entity_type,
                s.api_key{'::text' if self.db_type == 'postgresql' else ''},
                s.model{'::text' if self.db_type == 'postgresql' else ''},
                s.model_group{'::text' if self.db_type == 'postgresql' else ''},
                s.custom_llm_provider{'::text' if self.db_type == 'postgresql' else ''},
                s.prompt_tokens,
                s.completion_tokens,
                s.spend,
                s.api_requests,
                s.successful_requests,
                s.failed_requests,
                s.cache_creation_input_tokens,
                s.cache_read_input_tokens,
                s.created_at,
                s.updated_at,
                vt.key_name{'::text' if self.db_type == 'postgresql' else ''},
                vt.key_alias{'::text' if self.db_type == 'postgresql' else ''},
                u.user_alias{'::text' if self.db_type == 'postgresql' else ''},
                u.user_email{'::text' if self.db_type == 'postgresql' else ''},
                t.team_alias{'::text' if self.db_type == 'postgresql' else ''},
                COALESCE(vt.team_id, t.team_id){'::text' if self.db_type == 'postgresql' else ''} as team_id,
                o.organization_alias{'::text' if self.db_type == 'postgresql' else ''},
                COALESCE(vt.organization_id, o.organization_id){'::text' if self.db_type == 'postgresql' else ''} as organization_id
            FROM {self._quote_table('LiteLLM_DailyUserSpend')} s
            LEFT JOIN {self._quote_table('LiteLLM_VerificationToken')} vt ON s.api_key = vt.token
            LEFT JOIN {self._quote_table('LiteLLM_UserTable')} u ON vt.user_id = u.user_id
            LEFT JOIN {self._quote_table('LiteLLM_TeamTable')} t ON vt.team_id = t.team_id
            LEFT JOIN {self._quote_table('LiteLLM_OrganizationTable')} o ON vt.organization_id = o.organization_id

            UNION ALL

            SELECT
                s.id,
                s.date,
                s.team_id{'::text' if self.db_type == 'postgresql' else ''} as entity_id,
                'team'{'::text' if self.db_type == 'postgresql' else ''} as entity_type,
                s.api_key{'::text' if self.db_type == 'postgresql' else ''},
                s.model{'::text' if self.db_type == 'postgresql' else ''},
                s.model_group{'::text' if self.db_type == 'postgresql' else ''},
                s.custom_llm_provider{'::text' if self.db_type == 'postgresql' else ''},
                s.prompt_tokens,
                s.completion_tokens,
                s.spend,
                s.api_requests,
                s.successful_requests,
                s.failed_requests,
                s.cache_creation_input_tokens,
                s.cache_read_input_tokens,
                s.created_at,
                s.updated_at,
                vt.key_name{'::text' if self.db_type == 'postgresql' else ''},
                vt.key_alias{'::text' if self.db_type == 'postgresql' else ''},
                u.user_alias{'::text' if self.db_type == 'postgresql' else ''},
                u.user_email{'::text' if self.db_type == 'postgresql' else ''},
                COALESCE(t.team_alias, s.team_id){'::text' if self.db_type == 'postgresql' else ''} as team_alias,
                COALESCE(vt.team_id, t.team_id, s.team_id){'::text' if self.db_type == 'postgresql' else ''} as team_id,
                o.organization_alias{'::text' if self.db_type == 'postgresql' else ''},
                COALESCE(vt.organization_id, o.organization_id){'::text' if self.db_type == 'postgresql' else ''} as organization_id
            FROM {self._quote_table('LiteLLM_DailyTeamSpend')} s
            LEFT JOIN {self._quote_table('LiteLLM_VerificationToken')} vt ON s.api_key = vt.token
            LEFT JOIN {self._quote_table('LiteLLM_UserTable')} u ON vt.user_id = u.user_id
            LEFT JOIN {self._quote_table('LiteLLM_TeamTable')} t ON vt.team_id = t.team_id
            LEFT JOIN {self._quote_table('LiteLLM_OrganizationTable')} o ON vt.organization_id = o.organization_id
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
            self._close_connection(conn)

    def get_table_info(self) -> Dict[str, Any]:
        """Get information about the consolidated daily spend tables."""
        conn = self.connect()
        try:
            # Get combined row count from both tables
            user_count = self._get_table_row_count(conn, 'LiteLLM_DailyUserSpend')
            team_count = self._get_table_row_count(conn, 'LiteLLM_DailyTeamSpend')
            tag_count = self._get_table_row_count(conn, 'LiteLLM_DailyTagSpend')

            # Get column structure
            if self.db_type == 'sqlite':
                query = "PRAGMA table_info(LiteLLM_DailyUserSpend)"
                columns_df = pl.read_database(query, conn)
                columns = [{'column_name': row['name'], 'data_type': row['type'], 'is_nullable': not row['notnull']}
                          for row in columns_df.to_dicts()]
            else:
                query = """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'LiteLLM_DailyUserSpend'
                ORDER BY ordinal_position;
                """
                columns_df = pl.read_database(query, conn)
                columns = columns_df.to_dicts()

            return {
                'columns': columns,
                'row_count': user_count + team_count + tag_count,
                'table_breakdown': {
                    'user_spend': user_count,
                    'team_spend': team_count,
                    'tag_spend': tag_count
                }
            }
        finally:
            self._close_connection(conn)

    def _get_table_row_count(self, conn: Union[psycopg.Connection, sqlite3.Connection], table_name: str) -> int:
        """Get row count from specified table."""
        if self.db_type == 'sqlite':
            cursor = conn.cursor()
            cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
            return cursor.fetchone()[0]
        else:
            with conn.cursor() as cursor:
                cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                return cursor.fetchone()[0]

    def discover_all_tables(self) -> Dict[str, Any]:
        """Discover all tables in the LiteLLM database and their schemas."""
        conn = self.connect()
        try:
            if self.db_type == 'sqlite':
                # Get all tables
                tables_query = """
                SELECT name as table_name
                FROM sqlite_master
                WHERE type = 'table' AND name LIKE 'LiteLLM_%'
                ORDER BY name;
                """
            else:
                # Get all LiteLLM tables from PostgreSQL
                tables_query = """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name LIKE 'LiteLLM_%'
                ORDER BY table_name;
                """

            tables_df = pl.read_database(tables_query, conn)
            table_names = [row['table_name'] for row in tables_df.to_dicts()]

            # Get detailed schema for each table
            tables_info = {}
            for table_name in table_names:
                if self.db_type == 'sqlite':
                    # Get column information for SQLite
                    columns_query = f"PRAGMA table_info({table_name})"
                    columns_df = pl.read_database(columns_query, conn)
                    columns = [{
                        'column_name': row['name'],
                        'data_type': row['type'],
                        'is_nullable': not row['notnull'],
                        'column_default': row['dflt_value'],
                        'ordinal_position': row['cid'] + 1
                    } for row in columns_df.to_dicts()]

                    # Get primary keys
                    primary_keys = [col['column_name'] for col in columns if columns_df.filter(pl.col('name') == col['column_name'])['pk'][0] > 0]

                    # Foreign keys would require parsing sqlite_master, skip for now
                    foreign_keys = []

                    # Get indexes
                    indexes_query = f"PRAGMA index_list({table_name})"
                    indexes_df = pl.read_database(indexes_query, conn)
                    indexes = indexes_df.to_dicts() if not indexes_df.is_empty() else []
                else:
                    # PostgreSQL queries remain the same
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
                    columns = columns_df.to_dicts()

                    # Get primary key information
                    pk_query = """
                    SELECT a.attname
                    FROM pg_index i
                    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                    WHERE i.indrelid = %s::regclass AND i.indisprimary;
                    """
                    pk_df = pl.read_database(pk_query, conn, execute_options={"parameters": [f'"{table_name}"']})
                    primary_keys = [row['attname'] for row in pk_df.to_dicts()] if not pk_df.is_empty() else []

                    # Get foreign keys and indexes (simplified for now)
                    foreign_keys = []
                    indexes = []

                # Get row count
                try:
                    row_count = self._get_table_row_count(conn, table_name)
                except Exception:
                    row_count = 0

                tables_info[table_name] = {
                    'columns': columns,
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
            self._close_connection(conn)

    def get_individual_table_data(self, table_type: str, limit: Optional[int] = None, force_refresh: bool = False) -> pl.DataFrame:
        """Get data from a specific table type (user/team/tag/logs) directly from database."""
        # Map table type to actual table name
        table_mapping = {
            'user': 'LiteLLM_DailyUserSpend',
            'team': 'LiteLLM_DailyTeamSpend',
            'tag': 'LiteLLM_DailyTagSpend',
            'logs': 'LiteLLM_SpendLogs'
        }

        if table_type not in table_mapping:
            raise ValueError(f"Invalid table type: {table_type}. Must be one of: {', '.join(table_mapping.keys())}")

        table_name = table_mapping[table_type]

        # Special handling for SpendLogs table
        if table_type == 'logs':
            return self.get_spend_logs_data(limit=limit)

        # Build query based on table type
        if table_type == 'user':
            entity_field = 'user_id'
        elif table_type == 'team':
            entity_field = 'team_id'
        else:  # tag
            entity_field = 'tag'

        query = f"""
        SELECT
            id,
            date,
            {entity_field} as entity_id,
            '{table_type}' as entity_type,
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
        FROM {self._quote_table(table_name)}
        ORDER BY date DESC, created_at DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        conn = self.connect()
        try:
            return pl.read_database(query, conn)
        finally:
            self._close_connection(conn)

    def get_spend_logs_data(self, limit: Optional[int] = None) -> pl.DataFrame:
        """Retrieve transaction-level data from LiteLLM_SpendLogs table."""
        conn = self.connect()
        try:
            # First, discover what columns exist
            if self.db_type == 'sqlite':
                columns_query = "PRAGMA table_info(LiteLLM_SpendLogs)"
                columns_df = pl.read_database(columns_query, conn)
                available_columns = [row['name'] for row in columns_df.to_dicts()]
            else:
                columns_query = """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'LiteLLM_SpendLogs'
                AND table_schema = 'public'
                ORDER BY ordinal_position;
                """
                columns_df = pl.read_database(columns_query, conn)
                available_columns = [row['column_name'] for row in columns_df.to_dicts()]

            if not available_columns:
                raise ValueError("LiteLLM_SpendLogs table does not exist")

            # Build SELECT clause with available columns
            query = f"""
            SELECT *
            FROM {self._quote_table('LiteLLM_SpendLogs')}
            ORDER BY startTime DESC
            """

            if limit:
                query += f" LIMIT {limit}"

            return pl.read_database(query, conn)
        finally:
            self._close_connection(conn)

    def get_spend_logs_for_analysis(self, limit: Optional[int] = None) -> pl.DataFrame:
        """Retrieve SpendLogs data enriched with org information for CZRN/CBF analysis."""
        query = self._adapt_query_for_db(f"""
        SELECT
            s.request_id::text,
            s.call_type::text,
            s.api_key::text,
            s.spend::decimal,
            s.total_tokens::integer,
            s.prompt_tokens::integer,
            s.completion_tokens::integer,
            s.startTime::timestamp as start_time,
            s.model::text,
            s.model_group::text,
            s.custom_llm_provider::text,
            s.user::text as entity_id,
            'user'::text as entity_type,
            s.team_id::text,
            s.end_user::text,
            1 as api_requests,
            1 as successful_requests,
            0 as failed_requests,
            vt.key_name::text,
            vt.key_alias::text,
            u.user_alias::text,
            u.user_email::text,
            t.team_alias::text,
            COALESCE(vt.team_id, t.team_id, s.team_id)::text as enriched_team_id,
            o.organization_alias::text,
            COALESCE(vt.organization_id, o.organization_id)::text as organization_id,
            s.startTime::date as date
        FROM {self._quote_table('LiteLLM_SpendLogs')} s
        LEFT JOIN {self._quote_table('LiteLLM_VerificationToken')} vt ON s.api_key = vt.token
        LEFT JOIN {self._quote_table('LiteLLM_UserTable')} u ON s.user = u.user_id
        LEFT JOIN {self._quote_table('LiteLLM_TeamTable')} t ON COALESCE(vt.team_id, s.team_id) = t.team_id
        LEFT JOIN {self._quote_table('LiteLLM_OrganizationTable')} o ON vt.organization_id = o.organization_id
        ORDER BY s.startTime DESC
        """)

        if limit:
            query += f" LIMIT {limit}"

        conn = self.connect()
        try:
            return pl.read_database(query, conn)
        finally:
            self._close_connection(conn)
