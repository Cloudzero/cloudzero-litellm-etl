# SPDX-FileCopyrightText: Copyright (c), CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for transmit functionality with SQLite database and mocked HTTP calls."""

import os
from unittest.mock import Mock, patch

import polars as pl
import pytest

from ll2cz.database import LiteLLMDatabase
from ll2cz.output import CloudZeroStreamer
from ll2cz.transmit import DataTransmitter


class TestTransmitWithSQLite:
    """Test transmit functionality with SQLite database and mocked HTTP."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Ensure test.sqlite exists before tests."""
        if not os.path.exists('test.sqlite'):
            pytest.skip("test.sqlite not found. Run 'python scripts/create_test_sqlite.py' first.")

    @pytest.fixture
    def sqlite_db(self):
        """Provide SQLite database connection."""
        return LiteLLMDatabase('sqlite://test.sqlite')

    @pytest.fixture
    def mock_http_client(self):
        """Mock httpx client to prevent actual HTTP calls."""
        with patch('ll2cz.output.httpx.Client') as mock_client_class:
            # Create mock client instance
            mock_client = Mock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "success"}
            mock_response.raise_for_status = Mock()
            mock_client.post.return_value = mock_response
            
            # Make the class return our mock instance
            mock_client_class.return_value.__enter__.return_value = mock_client
            
            yield mock_client

    @pytest.fixture
    def transmitter(self, sqlite_db):
        """Create DataTransmitter instance with test credentials."""
        return DataTransmitter(
            database=sqlite_db,
            cz_api_key='test-api-key',
            cz_connection_id='test-connection-id',
            timezone='UTC'
        )

    def test_transmit_all_mode(self, transmitter, mock_http_client):
        """Test transmitting all data from SQLite database."""
        # Execute transmit
        result = transmitter.transmit(
            mode='all',
            source='usertable',
            test=False,
            limit=10
        )

        # Verify result
        assert result['status'] in ['success', 'no_data']
        
        if result['status'] == 'success':
            # Verify HTTP client was called
            assert mock_http_client.post.called
            
            # Get the call arguments
            call_args = mock_http_client.post.call_args
            url = call_args[0][0]
            payload = call_args[1]['json']
            
            # Verify URL structure
            assert 'connections/billing/anycost/test-connection-id/billing_drops' in url
            
            # Verify payload structure
            assert 'month' in payload
            assert 'operation' in payload
            assert 'data' in payload
            assert isinstance(payload['data'], list)
            assert len(payload['data']) > 0

    def test_transmit_test_mode(self, transmitter, mock_http_client, capsys):
        """Test that test mode doesn't send data but shows preview."""
        # Execute in test mode
        result = transmitter.transmit(
            mode='all',
            source='usertable',
            test=True,
            limit=5
        )

        # Verify HTTP client was NOT called in test mode
        assert not mock_http_client.post.called
        
        # Check result
        assert result['status'] == 'test'
        
        # Check console output
        captured = capsys.readouterr()
        assert 'TEST MODE' in captured.out
        assert 'Sample payload:' in captured.out

    def test_transmit_with_date_filter(self, transmitter, mock_http_client):
        """Test transmitting data with date filtering."""
        # Execute transmit with date filter
        result = transmitter.transmit(
            mode='day',
            date_spec='15-01-2025',
            source='usertable',
            test=False
        )

        # Check result
        assert result['status'] in ['success', 'no_data']

    def test_data_transformation_pipeline(self, sqlite_db):
        """Test the complete data transformation pipeline."""
        # Get raw data
        raw_data = sqlite_db.get_usage_data(limit=10)
        assert len(raw_data) > 0
        
        # Import and use the data processor
        from ll2cz.data_processor import DataProcessor
        processor = DataProcessor(source='usertable')
        
        # Process data
        _, cbf_records, error_summary = processor.process_dataframe(raw_data)
        
        # Verify transformation
        assert len(cbf_records) > 0
        
        # Check required CBF fields in first record
        first_record = cbf_records[0]
        required_fields = [
            'time/usage_start',
            'cost/cost',
            'usage/amount',
            'usage/units',
            'resource/service',
            'resource/id',
            'lineitem/type'
        ]
        for field in required_fields:
            assert field in first_record

    def test_streamer_batching(self, mock_http_client):
        """Test that CloudZeroStreamer batches data by date."""
        streamer = CloudZeroStreamer(
            api_key='test-api-key',
            connection_id='test-connection-id'
        )
        
        # Create test data with multiple dates
        test_data = pl.DataFrame({
            'time/usage_start': [
                '2025-01-15T12:00:00+00:00',
                '2025-01-15T13:00:00+00:00',
                '2025-01-16T12:00:00+00:00',
            ],
            'cost/cost': [0.1, 0.2, 0.3],
            'usage/amount': [100, 200, 300],
            'usage/units': ['tokens', 'tokens', 'tokens'],
            'resource/service': ['openai', 'openai', 'anthropic'],
            'resource/id': ['gpt-4', 'gpt-4', 'claude-3'],
            'lineitem/type': ['Usage', 'Usage', 'Usage']
        })
        
        # Send batched data
        streamer.send_batched(test_data, 'replace_hourly')
        
        # Should have made 2 calls (one for each date)
        assert mock_http_client.post.call_count == 2

    def test_error_handling(self, transmitter):
        """Test error handling in transmission pipeline."""
        # Mock an error in data retrieval
        with patch.object(transmitter.database, 'get_usage_data') as mock_get:
            mock_get.side_effect = Exception("Database connection failed")
            
            with pytest.raises(Exception) as exc_info:
                transmitter.transmit(mode='all', test=False)
            
            assert "Database connection failed" in str(exc_info.value)

    def test_append_vs_replace_operation(self, sqlite_db, mock_http_client):
        """Test append vs replace operation modes."""
        transmitter = DataTransmitter(
            database=sqlite_db,
            cz_api_key='test-api-key',
            cz_connection_id='test-connection-id'
        )
        
        # Test replace mode (default)
        result = transmitter.transmit(
            mode='all',
            source='usertable',
            append=False,
            test=False,
            limit=5
        )
        
        if result['status'] == 'success' and mock_http_client.post.called:
            payload = mock_http_client.post.call_args[1]['json']
            assert payload['operation'] == 'replace_hourly'
        
        # Reset mock
        mock_http_client.reset_mock()
        
        # Test append mode
        result = transmitter.transmit(
            mode='all',
            source='usertable',
            append=True,
            test=False,
            limit=5
        )
        
        if result['status'] == 'success' and mock_http_client.post.called:
            payload = mock_http_client.post.call_args[1]['json']
            assert payload['operation'] == 'sum'

    def test_no_data_handling(self, transmitter, mock_http_client):
        """Test handling when no data is available."""
        # Mock empty data response
        with patch.object(transmitter.database, 'get_usage_data') as mock_get:
            mock_get.return_value = pl.DataFrame()
            
            result = transmitter.transmit(
                mode='all',
                test=False
            )
            
            # Should return no_data status
            assert result['status'] == 'no_data'
            # Should not call the API
            assert not mock_http_client.post.called

    def test_sqlite_specific_functionality(self, sqlite_db):
        """Test SQLite-specific database functionality."""
        # Test that SQLite connection works
        assert sqlite_db.db_type == 'sqlite'
        assert sqlite_db.sqlite_path == 'test.sqlite'
        
        # Test getting usage data
        data = sqlite_db.get_usage_data(limit=5)
        assert isinstance(data, pl.DataFrame)
        assert len(data) <= 5
        
        # Test getting table info
        table_info = sqlite_db.get_table_info()
        assert 'row_count' in table_info
        assert 'columns' in table_info
        assert len(table_info['columns']) > 0

    def test_cbf_field_validation(self, sqlite_db):
        """Test that all CBF fields are properly formatted."""
        # Get and transform data
        from ll2cz.data_processor import DataProcessor
        
        raw_data = sqlite_db.get_usage_data(limit=5)
        processor = DataProcessor(source='usertable')
        _, cbf_records, _ = processor.process_dataframe(raw_data)
        
        for record in cbf_records:
            # Verify time format
            assert 'time/usage_start' in record
            assert isinstance(record['time/usage_start'], str)
            assert 'T' in record['time/usage_start']  # ISO format
            
            # Verify numeric fields
            assert isinstance(record['cost/cost'], (int, float))
            assert isinstance(record['usage/amount'], (int, float))
            
            # Verify string fields
            assert isinstance(record['resource/service'], str)
            assert isinstance(record['resource/id'], str)
            
            # Verify optional resource tags
            for key, value in record.items():
                if key.startswith('resource/tag:'):
                    # Tags should not have None values
                    assert value is not None

    def test_timezone_handling(self, sqlite_db, mock_http_client):
        """Test timezone handling in transmitter."""
        # Create transmitter with specific timezone
        transmitter = DataTransmitter(
            database=sqlite_db,
            cz_api_key='test-api-key',
            cz_connection_id='test-connection-id',
            timezone='US/Eastern'
        )
        
        # Transmit data
        result = transmitter.transmit(
            mode='all',
            source='usertable',
            test=False,
            limit=5
        )
        
        if result['status'] == 'success' and mock_http_client.post.called:
            payload = mock_http_client.post.call_args[1]['json']
            # All timestamps should be in UTC format
            for record in payload['data']:
                timestamp = record['time/usage_start']
                assert '+00:00' in timestamp or timestamp.endswith('Z')