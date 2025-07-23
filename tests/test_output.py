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
# CHANGELOG: 2025-01-19 - Migrated tests from pandas to polars and requests to httpx (erik.peterson)
# CHANGELOG: 2025-01-19 - Initial output module tests (erik.peterson)

"""Tests for output modules."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import polars as pl

from ll2cz.output import CloudZeroStreamer, CSVWriter


class TestCSVWriter:
    """Test CSV output functionality."""

    def test_write_csv(self):
        """Test writing CBF data to CSV file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp:
            tmp_path = tmp.name

        try:
            data = pl.DataFrame([{
                'timestamp': '2024-01-01T10:00:00Z',
                'service': 'litellm',
                'resource_id': 'req_123',
                'cost': 0.002,
                'usage_quantity': 150,
                'usage_unit': 'tokens',
                'dimensions': {'model': 'gpt-3.5-turbo', 'user_id': 'user_456'}
            }])

            writer = CSVWriter(tmp_path)
            writer.write(data)

            result = pl.read_csv(tmp_path)
            assert len(result) == 1
            assert 'dim_model' in result.columns
            assert 'dim_user_id' in result.columns
            assert result.row(0, named=True)['dim_model'] == 'gpt-3.5-turbo'

        finally:
            tmp_file = Path(tmp_path)
            if tmp_file.exists():
                tmp_file.unlink()

    def test_empty_dataframe(self):
        """Test writing empty DataFrame to CSV."""
        with tempfile.NamedTemporaryFile(mode='w', delete=True, suffix='.csv') as tmp:
            tmp_path = tmp.name

        writer = CSVWriter(tmp_path)
        writer.write(pl.DataFrame())

        assert not Path(tmp_path).exists()


class TestCloudZeroStreamer:
    """Test CloudZero API streaming functionality."""

    def test_send_data(self):
        """Test sending data to CloudZero API."""
        with patch('ll2cz.output.httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_client.post.return_value = mock_response

            # Configure the context manager
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client_class.return_value.__exit__.return_value = None

            # Use current CBF format with namespaced fields
            data = pl.DataFrame([{
                'time/usage_start': '2024-01-01T10:00:00Z',
                'resource/service': 'litellm',
                'resource/id': 'req_123',
                'cost/cost': 0.002,
                'usage/amount': 150,
                'usage/units': 'tokens',
                'resource/tag:model': 'gpt-3.5-turbo'
            }])

            streamer = CloudZeroStreamer('test-api-key', 'test-connection-id')
            streamer.send_batched(data)

            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args

            assert 'Authorization' in call_args[1]['headers']
            assert call_args[1]['headers']['Authorization'] == 'Bearer test-api-key'
            assert 'test-connection-id' in call_args[0][0]

            payload = call_args[1]['json']
            # Check the data array in the payload
            data_records = payload['data']
            assert len(data_records) == 1
            record = data_records[0]
            assert record['resource/service'] == 'litellm'
            assert record['resource/id'] == 'req_123'
            assert record['cost/cost'] == '0.002'  # CloudZero expects strings

