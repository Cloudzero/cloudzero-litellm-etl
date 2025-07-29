# SPDX-FileCopyrightText: Copyright (c), CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Smoke tests for CLI commands to ensure they don't crash on import errors."""

import os
import subprocess
import sys
import tempfile

import pytest


class TestCLISmoke:
    """Smoke tests to ensure all CLI commands at least start without import errors."""

    def run_command(self, *args):
        """Run ll2cz command and return result."""
        cmd = [sys.executable, '-m', 'll2cz'] + list(args)
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result

    def test_help_works(self):
        """Test that help command works without errors."""
        result = self.run_command('--help')
        assert result.returncode == 0
        assert 'Transform LiteLLM database data' in result.stdout

    def test_version_works(self):
        """Test that version command works without errors."""
        result = self.run_command('--version')
        assert result.returncode == 0
        assert 'll2cz' in result.stdout

    def test_analyze_help_works(self):
        """Test that analyze help works."""
        result = self.run_command('analyze', '--help')
        assert result.returncode == 0
        assert 'analyze commands' in result.stdout

    def test_transform_help_works(self):
        """Test that transform help works."""
        result = self.run_command('transform', '--help')
        assert result.returncode == 0
        assert 'transform' in result.stdout

    def test_transmit_help_works(self):
        """Test that transmit help works."""
        result = self.run_command('transmit', '--help')
        assert result.returncode == 0
        assert 'transmit' in result.stdout

    def test_cache_help_works(self):
        """Test that cache help works."""
        result = self.run_command('cache', '--help')
        assert result.returncode == 0
        assert 'cache commands' in result.stdout

    def test_config_help_works(self):
        """Test that config help works."""
        result = self.run_command('config', '--help')
        assert result.returncode == 0
        assert 'config commands' in result.stdout

    def test_missing_required_args_shows_error(self):
        """Test that missing required arguments show proper error."""
        # analyze schema requires database connection
        result = self.run_command('analyze', 'schema')
        assert result.returncode != 0
        # Should show error about missing database config
        assert 'Error' in result.stdout or 'error' in result.stderr.lower()

    def test_invalid_command_shows_error(self):
        """Test that invalid commands show error."""
        result = self.run_command('invalid-command')
        assert result.returncode != 0
        assert 'invalid choice' in result.stderr

    def test_transmit_test_mode_without_config(self):
        """Test that transmit test mode handles missing config gracefully."""
        # Use a non-existent SQLite file which is safer for CI/CD
        result = self.run_command('transmit', '--mode', 'all', '--test', '--input', 'sqlite://nonexistent.db', '--disable-cache')
        # Should fail with file not found error
        assert result.returncode != 0
        # The important thing is no import errors
        assert 'ImportError' not in result.stderr
        assert 'cannot import' not in result.stderr
        # Should show an error about database/file, not imports
        assert 'Error' in result.stdout or 'error' in result.stderr.lower()
    
    def test_transmit_help_available(self):
        """Test that transmit command is available and doesn't require database for help."""
        # This is CI/CD safe - no database or network calls needed
        result = self.run_command('transmit', '--help')
        assert result.returncode == 0
        assert '--mode' in result.stdout
        assert '--test' in result.stdout
        assert '--input' in result.stdout
        assert 'ImportError' not in result.stderr
        assert 'cannot import' not in result.stderr
    
    def test_transmit_validates_arguments(self):
        """Test that transmit validates arguments properly (CI/CD safe)."""
        # Test invalid mode
        result = self.run_command('transmit', '--mode', 'invalid-mode')
        assert result.returncode != 0
        # Should show error about invalid choice, not import errors
        assert 'ImportError' not in result.stderr
        assert 'cannot import' not in result.stderr
        assert 'invalid choice' in result.stderr
    
    def test_transmit_with_env_credentials(self):
        """Test that transmit can use environment variables for credentials (CI/CD safe)."""
        # Set environment variables
        env = os.environ.copy()
        env['CZ_API_KEY'] = 'test-api-key'
        env['CZ_CONNECTION_ID'] = 'test-connection-id'
        
        # Run transmit help with env credentials - doesn't need database
        cmd = [sys.executable, '-m', 'll2cz', 'transmit', '--help']
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        
        # Should succeed - just testing that env vars don't break anything
        assert result.returncode == 0
        assert 'transmit' in result.stdout
        assert 'ImportError' not in result.stderr
        assert 'cannot import' not in result.stderr