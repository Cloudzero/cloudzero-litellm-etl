# SPDX-FileCopyrightText: Copyright (c), CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for CLI commands to ensure all commands work correctly."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from ll2cz.cli import main


class TestCLICommands:
    """Test all CLI commands to prevent regressions."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration."""
        with patch('ll2cz.cli.Config') as mock:
            config_instance = MagicMock()
            config_instance.get.side_effect = lambda key, default=None: {
                'database_url': 'postgresql://test@localhost/test',
                'cz_api_key': 'test-api-key',
                'cz_connection_id': 'test-connection-id'
            }.get(key, default)
            mock.return_value = config_instance
            yield config_instance

    @pytest.fixture
    def mock_database(self):
        """Mock database with test data."""
        test_data = pl.DataFrame({
            'api_key': ['key1', 'key2'],
            'custom_llm_provider': ['openai', 'anthropic'],
            'model': ['gpt-4', 'claude-3'],
            'api_request': [1, 1],
            'cache_hits': [0, 0],
            'cache_read': [0, 0],
            'completion_tokens': [100, 200],
            'prompt_tokens': [50, 100],
            'response_cost_usd': [0.01, 0.02],
            'spend': [0.01, 0.02],
            'team_id': ['team1', 'team2'],
            'startTime': ['2025-01-01', '2025-01-02'],
            'request_id': ['req1', 'req2'],
            'user': ['user1', 'user2'],
            'team_alias': [None, None],
            'team': [None, None],
            'key_alias': [None, None],
            'user_email': [None, None],
            'user_alias': [None, None],
            'project_tag': [None, None],
            'org_tag': [None, None],
            'custom_tag_0': [None, None],
            'custom_tag_1': [None, None],
            'custom_tag_2': [None, None],
            'custom_tag_3': [None, None],
            'custom_tag_4': [None, None]
        })
        
        with patch('ll2cz.cli.CachedLiteLLMDatabase') as mock_db, \
             patch('ll2cz.analysis.CachedLiteLLMDatabase') as mock_db_analysis:
            db_instance = MagicMock()
            db_instance.get_usage_data.return_value = test_data
            db_instance.get_individual_table_data.return_value = test_data
            db_instance.get_spend_analysis_data.return_value = test_data
            db_instance.is_server_available.return_value = True
            db_instance.get_cache_info.return_value = {
                'total_records': 2,
                'user_records': 2,
                'team_records': 0,
                'tag_records': 0,
                'last_updated': '2025-01-01T00:00:00'
            }
            mock_db.return_value = db_instance
            mock_db_analysis.return_value = db_instance
            yield db_instance

    def test_help_command(self, capsys):
        """Test that help command works."""
        with patch('sys.argv', ['ll2cz', '--help']):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert 'Transform LiteLLM database data' in captured.out

    def test_version_command(self, capsys):
        """Test that version command works."""
        with patch('sys.argv', ['ll2cz', '--version']):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert 'll2cz' in captured.out

    def test_analyze_data_command(self, mock_config, mock_database, capsys):
        """Test analyze data command."""
        with patch('sys.argv', ['ll2cz', 'analyze', 'data', '--limit', '5']):
            main()
        
        captured = capsys.readouterr()
        assert 'Comprehensive Data Analysis' in captured.out
        assert 'Database Overview' in captured.out

    def test_analyze_spend_command(self, mock_config, mock_database, capsys):
        """Test analyze spend command."""
        with patch('sys.argv', ['ll2cz', 'analyze', 'spend']):
            main()
        
        captured = capsys.readouterr()
        assert 'Spend Analysis' in captured.out or 'Analysis' in captured.out

    def test_analyze_schema_command(self, mock_config, mock_database, capsys):
        """Test analyze schema command."""
        # Mock database schema
        mock_database.get_schema_info.return_value = {
            'test_table': [
                {'column_name': 'id', 'data_type': 'integer', 'is_nullable': 'NO', 'column_default': None}
            ]
        }
        
        with patch('sys.argv', ['ll2cz', 'analyze', 'schema']):
            main()
        
        captured = capsys.readouterr()
        assert 'Schema' in captured.out or 'test_table' in captured.out

    def test_transform_command(self, mock_config, mock_database):
        """Test transform command."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            output_file = f.name
        
        try:
            with patch('sys.argv', ['ll2cz', 'transform', '--output', output_file, '--limit', '5']):
                main()
            
            # Verify output file was created
            assert Path(output_file).exists()
            
            # Verify content
            content = Path(output_file).read_text()
            assert content  # Should not be empty
            
        finally:
            if Path(output_file).exists():
                os.unlink(output_file)

    def test_transmit_test_mode(self, mock_config, mock_database, capsys):
        """Test transmit command in test mode."""
        with patch('sys.argv', ['ll2cz', 'transmit', '--mode', 'all', '--test']):
            main()
        
        captured = capsys.readouterr()
        assert 'TEST MODE' in captured.out
        assert 'Sample payload' in captured.out

    def test_transmit_day_mode(self, mock_config, mock_database, capsys):
        """Test transmit command for specific day."""
        with patch('sys.argv', ['ll2cz', 'transmit', '--mode', 'day', '--date', '01-01-2025', '--test']):
            main()
        
        captured = capsys.readouterr()
        assert 'TEST MODE' in captured.out or 'Day: 2025-01-01' in captured.out

    def test_transmit_month_mode(self, mock_config, mock_database, capsys):
        """Test transmit command for specific month."""
        with patch('sys.argv', ['ll2cz', 'transmit', '--mode', 'month', '--date', '01-2025', '--test']):
            main()
        
        captured = capsys.readouterr()
        assert 'TEST MODE' in captured.out or 'Month: January 2025' in captured.out

    def test_cache_status_command(self, mock_config, mock_database, capsys):
        """Test cache status command."""
        with patch('sys.argv', ['ll2cz', 'cache', 'status']):
            main()
        
        captured = capsys.readouterr()
        assert 'Cache Status' in captured.out
        assert 'Records cached' in captured.out

    def test_cache_clear_command(self, mock_config, mock_database, capsys):
        """Test cache clear command."""
        mock_database.clear_cache.return_value = None
        
        with patch('sys.argv', ['ll2cz', 'cache', 'clear']):
            main()
        
        captured = capsys.readouterr()
        assert 'Cache cleared' in captured.out

    def test_cache_refresh_command(self, mock_config, mock_database, capsys):
        """Test cache refresh command."""
        mock_database.refresh_cache.return_value = {
            'user': {'added': 10, 'updated': 5, 'unchanged': 100},
            'team': {'added': 0, 'updated': 0, 'unchanged': 0},
            'tag': {'added': 0, 'updated': 0, 'unchanged': 0}
        }
        
        with patch('sys.argv', ['ll2cz', 'cache', 'refresh']):
            main()
        
        captured = capsys.readouterr()
        assert 'Refresh Results' in captured.out or 'Cache refreshed' in captured.out

    def test_config_show_command(self, mock_config, capsys):
        """Test config show command."""
        with patch('sys.argv', ['ll2cz', 'config', 'show']):
            main()
        
        captured = capsys.readouterr()
        assert 'Configuration' in captured.out or 'Configured' in captured.out

    def test_config_example_command(self, mock_config):
        """Test config example command."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / 'config.yml'
            
            with patch('ll2cz.cli.Path.home', return_value=Path(tmpdir)):
                with patch('sys.argv', ['ll2cz', 'config', 'example']):
                    main()
            
            # Verify config file was created
            expected_path = Path(tmpdir) / '.ll2cz' / 'config.yml'
            assert expected_path.exists()

    def test_invalid_command(self, capsys):
        """Test that invalid commands show error."""
        with patch('sys.argv', ['ll2cz', 'invalid-command']):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code != 0
        
        captured = capsys.readouterr()
        assert 'invalid choice' in captured.err or 'error' in captured.err.lower()

    def test_transform_with_source_logs(self, mock_config, mock_database):
        """Test transform command with logs source."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            output_file = f.name
        
        try:
            # Mock spend logs data
            mock_database.get_spend_logs_data.return_value = mock_database.get_usage_data()
            
            with patch('sys.argv', ['ll2cz', 'transform', '--source', 'logs', '--output', output_file]):
                main()
            
            assert Path(output_file).exists()
            
        finally:
            if Path(output_file).exists():
                os.unlink(output_file)

    def test_transmit_with_append_mode(self, mock_config, mock_database, capsys):
        """Test transmit command with append mode."""
        with patch('sys.argv', ['ll2cz', 'transmit', '--mode', 'all', '--append', '--test']):
            main()
        
        captured = capsys.readouterr()
        assert 'TEST MODE' in captured.out
        # In append mode, operation should be 'sum' instead of 'replace_hourly'
        assert 'sum' in captured.out or 'append' in captured.out.lower()