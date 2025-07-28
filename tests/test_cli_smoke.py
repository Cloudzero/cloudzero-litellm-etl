# SPDX-FileCopyrightText: Copyright (c), CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Smoke tests for CLI commands to ensure they don't crash on import errors."""

import subprocess
import sys

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
        # transmit requires --mode
        result = self.run_command('transmit')
        assert result.returncode != 0
        assert 'Error' in result.stdout or 'required' in result.stderr

    def test_invalid_command_shows_error(self):
        """Test that invalid commands show error."""
        result = self.run_command('invalid-command')
        assert result.returncode != 0
        assert 'invalid choice' in result.stderr

    def test_transmit_test_mode_without_config(self):
        """Test that transmit test mode handles missing config gracefully."""
        result = self.run_command('transmit', '--mode', 'all', '--test', '--input', 'postgresql://fake/fake')
        # In test mode with cache, it might succeed (returncode 0)
        # The important thing is no import errors
        assert 'ImportError' not in result.stderr
        assert 'cannot import' not in result.stderr
        # If it runs, should show test mode
        if result.returncode == 0:
            assert 'TEST MODE' in result.stdout