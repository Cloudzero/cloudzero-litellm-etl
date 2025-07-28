# SPDX-FileCopyrightText: Copyright (c), CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Database connection and data extraction for LiteLLM."""

from typing import Any, Dict, Optional

import polars as pl
import psycopg


class LiteLLMDatabase:
    """Handle LiteLLM PostgreSQL database connections and queries."""

    def __init__(self, connection_string: str):
        """Initialize database connection."""
        self.connection_string = connection_string
        self._connection: Optional[psycopg.Connection] = None

    def connect(self) -> psycopg.Connection:
        """Establish database connection."""
        if self._connection is None or self._connection.closed:
            self._connection = psycopg.connect(self.connection_string)
        return self._connection

    def get_usage_data(self, limit: Optional[int] = None) -> pl.DataFrame:
        """Retrieve enriched usage data from LiteLLM DailyUserSpend table with API key and user lookup information."""
        # Enhanced query with user lookup tables for API key enrichment
        query = """
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
            -- Enriched API key information
            vt.key_name,
            vt.key_alias,
            -- Enriched user information
            u.user_alias,
            u.user_email,
            -- Enriched team information
            t.team_alias,
            t.team_id,
            -- Enriched organization information
            o.organization_alias,
            o.organization_id
        FROM "LiteLLM_DailyUserSpend" s
        LEFT JOIN "LiteLLM_VerificationToken" vt ON s.api_key = vt.token
        LEFT JOIN "LiteLLM_UserTable" u ON vt.user_id = u.user_id
        LEFT JOIN "LiteLLM_TeamTable" t ON vt.team_id = t.team_id
        LEFT JOIN "LiteLLM_OrganizationTable" o ON vt.organization_id = o.organization_id
        ORDER BY s.date DESC, s.created_at DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        conn = self.connect()
        try:
            return pl.read_database(query, conn)
        finally:
            conn.close()

    def get_spend_analysis_data(self, limit: Optional[int] = None) -> pl.DataFrame:
        """Retrieve enriched consolidated usage data from both user and team spend tables with API key and user lookup information."""
        # Enhanced union query with user lookup tables for API key enrichment
        query = """
        WITH consolidated_spend AS (
            -- User spend data with enrichment
            SELECT
                s.id,
                s.date,
                s.user_id::text as entity_id,
                'user'::text as entity_type,
                s.api_key::text,
                s.model::text,
                s.model_group::text,
                s.custom_llm_provider::text,
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
                -- Enriched API key information
                vt.key_name::text,
                vt.key_alias::text,
                -- Enriched user information
                u.user_alias::text,
                u.user_email::text,
                -- Enriched team information
                t.team_alias::text,
                COALESCE(vt.team_id, t.team_id)::text as team_id,
                -- Enriched organization information
                o.organization_alias::text,
                COALESCE(vt.organization_id, o.organization_id)::text as organization_id
            FROM "LiteLLM_DailyUserSpend" s
            LEFT JOIN "LiteLLM_VerificationToken" vt ON s.api_key = vt.token
            LEFT JOIN "LiteLLM_UserTable" u ON vt.user_id = u.user_id
            LEFT JOIN "LiteLLM_TeamTable" t ON vt.team_id = t.team_id
            LEFT JOIN "LiteLLM_OrganizationTable" o ON vt.organization_id = o.organization_id

            UNION ALL

            -- Team spend data with enrichment
            SELECT
                s.id,
                s.date,
                s.team_id::text as entity_id,
                'team'::text as entity_type,
                s.api_key::text,
                s.model::text,
                s.model_group::text,
                s.custom_llm_provider::text,
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
                -- Enriched API key information
                vt.key_name::text,
                vt.key_alias::text,
                -- Enriched user information (may be null for team records)
                u.user_alias::text,
                u.user_email::text,
                -- Enriched team information
                COALESCE(t.team_alias, s.team_id)::text as team_alias,
                COALESCE(vt.team_id, t.team_id, s.team_id)::text as team_id,
                -- Enriched organization information
                o.organization_alias::text,
                COALESCE(vt.organization_id, o.organization_id)::text as organization_id
            FROM "LiteLLM_DailyTeamSpend" s
            LEFT JOIN "LiteLLM_VerificationToken" vt ON s.api_key = vt.token
            LEFT JOIN "LiteLLM_UserTable" u ON vt.user_id = u.user_id
            LEFT JOIN "LiteLLM_TeamTable" t ON vt.team_id = t.team_id
            LEFT JOIN "LiteLLM_OrganizationTable" o ON vt.organization_id = o.organization_id
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

    def get_table_info(self) -> Dict[str, Any]:
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

    def discover_all_tables(self) -> Dict[str, Any]:
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
        FROM "{table_name}"
        ORDER BY date DESC, created_at DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        conn = self.connect()
        try:
            return pl.read_database(query, conn)
        finally:
            conn.close()

    def get_spend_logs_data(self, limit: Optional[int] = None) -> pl.DataFrame:
        """Retrieve transaction-level data from LiteLLM_SpendLogs table with detailed request information."""
        conn = self.connect()
        try:
            # First, discover what columns exist in the SpendLogs table
            columns_query = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'LiteLLM_SpendLogs'
            AND table_schema = 'public'
            ORDER BY ordinal_position;
            """
            columns_df = pl.read_database(columns_query, conn)

            if columns_df.is_empty():
                raise ValueError("LiteLLM_SpendLogs table does not exist")

            available_columns = [row['column_name'] for row in columns_df.to_dicts()]

            # Build SELECT clause with only available columns
            select_parts = []
            for col in available_columns:
                if col in ['startTime', 'endTime', 'completionStartTime']:
                    select_parts.append(f'"{col}"::timestamp')
                elif col in ['spend']:
                    select_parts.append(f'{col}::decimal')
                elif col in ['total_tokens', 'prompt_tokens', 'completion_tokens']:
                    select_parts.append(f'{col}::integer')
                elif col in ['cache_hit']:
                    select_parts.append(f'{col}::boolean')
                else:
                    select_parts.append(f'{col}::text')

            query = f"""
            SELECT {', '.join(select_parts)}
            FROM "LiteLLM_SpendLogs"
            ORDER BY "startTime" DESC
            """

            if limit:
                query += f" LIMIT {limit}"

            return pl.read_database(query, conn)
        finally:
            conn.close()

    def get_spend_logs_for_analysis(self, limit: Optional[int] = None) -> pl.DataFrame:
        """Retrieve SpendLogs data enriched with org information for CZRN/CBF analysis."""
        conn = self.connect()
        try:
            # Enhanced query with organization lookup tables for analysis
            query = """
            SELECT
                s.request_id::text,
                s.call_type::text,
                s.api_key::text,
                s.spend::decimal,
                s.total_tokens::integer,
                s.prompt_tokens::integer,
                s.completion_tokens::integer,
                s."startTime"::timestamp as start_time,
                s.model::text,
                s.model_group::text,
                s.custom_llm_provider::text,
                s."user"::text as entity_id,
                'user'::text as entity_type,
                s.team_id::text,
                s.end_user::text,
                -- API request count (1 per log entry)
                1 as api_requests,
                1 as successful_requests,
                0 as failed_requests,
                -- Enriched API key information
                vt.key_name::text,
                vt.key_alias::text,
                -- Enriched user information
                u.user_alias::text,
                u.user_email::text,
                -- Enriched team information
                t.team_alias::text,
                COALESCE(vt.team_id, t.team_id, s.team_id)::text as enriched_team_id,
                -- Enriched organization information
                o.organization_alias::text,
                COALESCE(vt.organization_id, o.organization_id)::text as organization_id,
                -- Map start_time to date for compatibility
                s."startTime"::date as date
            FROM "LiteLLM_SpendLogs" s
            LEFT JOIN "LiteLLM_VerificationToken" vt ON s.api_key = vt.token
            LEFT JOIN "LiteLLM_UserTable" u ON s."user" = u.user_id
            LEFT JOIN "LiteLLM_TeamTable" t ON COALESCE(vt.team_id, s.team_id) = t.team_id
            LEFT JOIN "LiteLLM_OrganizationTable" o ON vt.organization_id = o.organization_id
            ORDER BY s."startTime" DESC
            """

            if limit:
                query += f" LIMIT {limit}"

            return pl.read_database(query, conn)
        finally:
            conn.close()

