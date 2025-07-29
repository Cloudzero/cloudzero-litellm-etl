# SPDX-FileCopyrightText: Copyright (c), CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for SQLite database support."""

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest
import polars as pl

from ll2cz.database import LiteLLMDatabase


class TestSQLiteSupport:
    """Test SQLite database functionality."""

    @pytest.fixture
    def temp_sqlite_db(self):
        """Create a temporary SQLite database with test data."""
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
            db_path = tmp.name
        
        # Create minimal test schema
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
        CREATE TABLE LiteLLM_OrganizationTable (
            organization_id TEXT PRIMARY KEY,
            organization_alias TEXT
        )
        """)
        
        cursor.execute("""
        CREATE TABLE LiteLLM_TeamTable (
            team_id TEXT PRIMARY KEY,
            team_alias TEXT,
            organization_id TEXT
        )
        """)
        
        cursor.execute("""
        CREATE TABLE LiteLLM_UserTable (
            user_id TEXT PRIMARY KEY,
            user_alias TEXT,
            user_email TEXT,
            team_id TEXT,
            organization_id TEXT
        )
        """)
        
        cursor.execute("""
        CREATE TABLE LiteLLM_VerificationToken (
            token TEXT PRIMARY KEY,
            key_name TEXT,
            key_alias TEXT,
            user_id TEXT,
            team_id TEXT,
            organization_id TEXT
        )
        """)
        
        cursor.execute("""
        CREATE TABLE LiteLLM_DailyUserSpend (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            user_id TEXT NOT NULL,
            api_key TEXT,
            model TEXT,
            model_group TEXT,
            custom_llm_provider TEXT,
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            spend DECIMAL(10, 6) DEFAULT 0,
            api_requests INTEGER DEFAULT 0,
            successful_requests INTEGER DEFAULT 0,
            failed_requests INTEGER DEFAULT 0,
            cache_creation_input_tokens INTEGER DEFAULT 0,
            cache_read_input_tokens INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        cursor.execute("""
        CREATE TABLE LiteLLM_DailyTeamSpend (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            team_id TEXT NOT NULL,
            api_key TEXT,
            model TEXT,
            model_group TEXT,
            custom_llm_provider TEXT,
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            spend DECIMAL(10, 6) DEFAULT 0,
            api_requests INTEGER DEFAULT 0,
            successful_requests INTEGER DEFAULT 0,
            failed_requests INTEGER DEFAULT 0,
            cache_creation_input_tokens INTEGER DEFAULT 0,
            cache_read_input_tokens INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        cursor.execute("""
        CREATE TABLE LiteLLM_DailyTagSpend (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            tag TEXT NOT NULL,
            api_key TEXT,
            model TEXT,
            model_group TEXT,
            custom_llm_provider TEXT,
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            spend DECIMAL(10, 6) DEFAULT 0,
            api_requests INTEGER DEFAULT 0,
            successful_requests INTEGER DEFAULT 0,
            failed_requests INTEGER DEFAULT 0,
            cache_creation_input_tokens INTEGER DEFAULT 0,
            cache_read_input_tokens INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Insert test data
        cursor.execute("INSERT INTO LiteLLM_OrganizationTable VALUES ('org-1', 'Test Org')")
        cursor.execute("INSERT INTO LiteLLM_TeamTable VALUES ('team-1', 'Test Team', 'org-1')")
        cursor.execute("INSERT INTO LiteLLM_UserTable VALUES ('user-1', 'test_user', 'test@example.com', 'team-1', 'org-1')")
        cursor.execute("INSERT INTO LiteLLM_VerificationToken VALUES ('sk-test', 'test-key', 'test', 'user-1', 'team-1', 'org-1')")
        
        cursor.execute("""
        INSERT INTO LiteLLM_DailyUserSpend 
        (date, user_id, api_key, model, model_group, custom_llm_provider, 
         prompt_tokens, completion_tokens, spend, api_requests, successful_requests, failed_requests)
        VALUES ('2025-01-15', 'user-1', 'sk-test', 'gpt-4', 'openai-gpt-4', 'openai', 
                1000, 500, 0.05, 10, 10, 0)
        """)
        
        conn.commit()
        conn.close()
        
        yield db_path
        
        # Cleanup
        os.unlink(db_path)

    def test_sqlite_connection_string_parsing(self):
        """Test various SQLite connection string formats."""
        # Test different formats
        formats = [
            ('sqlite:///path/to/db.sqlite', 'path/to/db.sqlite'),
            ('sqlite://path/to/db.sqlite', 'path/to/db.sqlite'),
            ('sqlite://./test.sqlite', './test.sqlite'),
            ('sqlite:///test.sqlite', 'test.sqlite'),
        ]
        
        for conn_str, expected_path in formats:
            db = LiteLLMDatabase(conn_str)
            assert db.db_type == 'sqlite'
            assert db.sqlite_path == expected_path

    def test_sqlite_database_connection(self, temp_sqlite_db):
        """Test connecting to SQLite database."""
        db = LiteLLMDatabase(f'sqlite:///{temp_sqlite_db}')
        conn = db.connect()
        assert conn is not None
        assert isinstance(conn, sqlite3.Connection)
        
        # Test foreign keys are enabled
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys")
        assert cursor.fetchone()[0] == 1  # Foreign keys should be ON

    def test_sqlite_get_usage_data(self, temp_sqlite_db):
        """Test retrieving usage data from SQLite."""
        db = LiteLLMDatabase(f'sqlite:///{temp_sqlite_db}')
        df = db.get_usage_data(limit=10)
        
        assert isinstance(df, pl.DataFrame)
        assert len(df) == 1
        assert df['entity_id'][0] == 'user-1'
        assert df['model'][0] == 'gpt-4'
        assert df['spend'][0] == 0.05

    def test_sqlite_get_table_info(self, temp_sqlite_db):
        """Test getting table info from SQLite."""
        db = LiteLLMDatabase(f'sqlite:///{temp_sqlite_db}')
        info = db.get_table_info()
        
        assert 'columns' in info
        assert 'row_count' in info
        assert 'table_breakdown' in info
        assert info['table_breakdown']['user_spend'] == 1
        assert info['table_breakdown']['team_spend'] == 0

    def test_sqlite_discover_all_tables(self, temp_sqlite_db):
        """Test discovering all tables in SQLite."""
        db = LiteLLMDatabase(f'sqlite:///{temp_sqlite_db}')
        schema = db.discover_all_tables()
        
        assert 'tables' in schema
        assert 'table_count' in schema
        assert schema['table_count'] >= 7  # At least the tables we created
        
        # Check specific table exists
        assert 'LiteLLM_DailyUserSpend' in schema['tables']
        user_spend_info = schema['tables']['LiteLLM_DailyUserSpend']
        assert user_spend_info['row_count'] == 1

    def test_sqlite_postgresql_compatibility(self, temp_sqlite_db):
        """Test that SQLite database works with same interface as PostgreSQL."""
        db = LiteLLMDatabase(f'sqlite:///{temp_sqlite_db}')
        
        # Test all major methods work
        methods = [
            (db.get_usage_data, {'limit': 10}),
            (db.get_table_info, {}),
            (db.discover_all_tables, {}),
            (db.get_individual_table_data, {'table_type': 'user', 'limit': 10}),
        ]
        
        for method, kwargs in methods:
            result = method(**kwargs)
            assert result is not None

    def test_existing_test_sqlite(self):
        """Test with the actual test.sqlite file if it exists."""
        if os.path.exists('test.sqlite'):
            db = LiteLLMDatabase('sqlite://test.sqlite')
            
            # Test we can read data
            df = db.get_usage_data(limit=5)
            assert isinstance(df, pl.DataFrame)
            assert len(df) > 0
            
            # Test schema discovery
            schema = db.discover_all_tables()
            assert len(schema['tables']) > 0