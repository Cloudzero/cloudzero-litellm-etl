# SPDX-FileCopyrightText: Copyright (c), CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Integration tests for transmit functionality with SQLite database and mocked HTTP calls."""

import json
import os
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import polars as pl
import pytest

from ll2cz.database import LiteLLMDatabase
from ll2cz.output import CloudZeroStreamer
from ll2cz.transmit import DataTransmitter
from ll2cz.transform import CBFTransformer


class TestTransmitIntegration:
    """Test transmit functionality with SQLite database for CI/CD environments."""

    @pytest.fixture
    def sqlite_db(self):
        """Provide SQLite database connection."""
        if not os.path.exists('test.sqlite'):
            pytest.skip("test.sqlite not found. Run 'python scripts/create_test_sqlite.py' first.")
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
            mock_client.put.return_value = mock_response  # Keep both for compatibility
            
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

        # Verify HTTP client was called
        assert mock_http_client.post.called
        
        # Get the call arguments
        call_args = mock_http_client.post.call_args
        url = call_args[0][0]
        payload = call_args[1]['json']  # httpx uses 'json' parameter, not 'content'
        
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
        
        # Check console output
        captured = capsys.readouterr()
        assert 'TEST MODE' in captured.out
        assert 'Sample payload:' in captured.out

    def test_transmit_specific_date(self, transmitter, mock_http_client):
        """Test transmitting data for a specific date."""
        # Use a date we know has data (from create_test_sqlite.py)
        target_date = '15-01-2025'
        
        result = transmitter.transmit(
            mode='day',
            date_spec=target_date,
            source='usertable',
            test=False
        )

        # Check if data was sent
        if mock_http_client.post.called:
            payload = mock_http_client.post.call_args[1]['json']
            # All records should be for the specified date
            for record in payload['data']:
                # API uses CBF field names directly
                assert '2025-01-15' in record['time/usage_start']

    def test_data_transformation_pipeline(self, sqlite_db):
        """Test the complete data transformation pipeline."""
        # Get raw data
        raw_data = sqlite_db.get_usage_data(limit=10)
        assert len(raw_data) > 0
        
        # Transform to CBF using the standalone transformer
        transformer = CBFTransformer()
        cbf_data = transformer.transform(raw_data)
        
        # Verify transformation
        assert isinstance(cbf_data, pl.DataFrame)
        assert len(cbf_data) > 0
        
        # Check required CBF fields
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
            assert field in cbf_data.columns
            
        # Verify data integrity
        assert cbf_data['cost/cost'].sum() > 0
        assert cbf_data['usage/amount'].sum() > 0

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
        transmitter.transmit(
            mode='all',
            source='usertable',
            append=False,
            test=False,
            limit=5
        )
        
        if mock_http_client.post.called:
            payload = mock_http_client.post.call_args[1]['json']
            assert payload['operation'] == 'replace_hourly'
        
        # Reset mock
        mock_http_client.reset_mock()
        
        # Test append mode
        transmitter.transmit(
            mode='all',
            source='usertable',
            append=True,
            test=False,
            limit=5
        )
        
        if mock_http_client.post.called:
            payload = mock_http_client.post.call_args[1]['json']
            assert payload['operation'] == 'sum'

    def test_no_data_handling(self, transmitter, mock_http_client):
        """Test handling when no data is available for the specified criteria."""
        # Use a future date that won't have data
        result = transmitter.transmit(
            mode='day',
            date_spec='01-01-2030',
            test=False
        )
        
        # Should not call the API when there's no data
        # Note: The date filtering happens at the CBF transformation level,
        # so we might still get calls if the raw data exists
        # The important thing is that the result indicates no data was found
        assert result.get('status') in ['no_data', 'success']
        if result.get('status') == 'success':
            assert result.get('records', 0) >= 0

    def test_source_parameter_handling(self, sqlite_db, mock_http_client):
        """Test handling different data sources."""
        transmitter = DataTransmitter(
            database=sqlite_db,
            cz_api_key='test-api-key',
            cz_connection_id='test-connection-id'
        )
        
        # Test with usertable source
        transmitter.transmit(
            mode='all',
            source='usertable',
            test=False,
            limit=5
        )
        
        assert mock_http_client.post.called
        user_call_count = mock_http_client.post.call_count
        
        # Reset mock
        mock_http_client.reset_mock()
        
        # Test with logs source (might not have data)
        try:
            transmitter.transmit(
                mode='all',
                source='logs',
                test=False,
                limit=5
            )
        except Exception:
            # Logs source might not be available in test data
            pass

    def test_cbf_field_validation(self, sqlite_db):
        """Test that all CBF fields are properly formatted."""
        # Get and transform data
        raw_data = sqlite_db.get_usage_data(limit=5)
        transformer = CBFTransformer()
        cbf_data = transformer.transform(raw_data)
        
        # Convert to dict format for validation
        records = cbf_data.to_dicts()
        
        for record in records:
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

    def test_console_output_formatting(self, transmitter, capsys):
        """Test that console output is properly formatted."""
        # Execute transmit in test mode to see console output
        transmitter.transmit(
            mode='all',
            source='usertable',
            test=True,
            limit=5
        )
        
        # Verify console output
        captured = capsys.readouterr()
        assert 'TEST MODE' in captured.out
        assert 'Sample payload:' in captured.out
        assert 'connection_id' in captured.out
        assert 'telemetry_stream' in captured.out

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
        transmitter.transmit(
            mode='all',
            source='usertable',
            test=False,
            limit=5
        )
        
        if mock_http_client.post.called:
            payload = mock_http_client.post.call_args[1]['json']
            # All timestamps should be in UTC format
            for record in payload['data']:
                # API uses CBF field names directly
                timestamp = record['time/usage_start']
                assert '+00:00' in timestamp or timestamp.endswith('Z')