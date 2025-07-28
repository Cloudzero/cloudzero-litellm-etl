# SPDX-FileCopyrightText: Copyright (c), CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for CBF Builder functionality."""

from datetime import datetime, timezone

from ll2cz.cbf_builder import CBFBuilder


class TestCBFBuilder:
    """Test CBF Builder functionality."""

    def test_with_resource_tags_excludes_none_values(self):
        """Test that None values are excluded from resource tags."""
        builder = CBFBuilder()

        # Add timestamp (required)
        builder.with_timestamp(datetime(2024, 1, 1, tzinfo=timezone.utc))

        # Add tags with some None values
        tags = {
            'model': 'gpt-3.5-turbo',
            'provider': 'openai',
            'key_name': None,  # Should be excluded
            'team': None,      # Should be excluded
            'environment': 'production'
        }

        builder.with_resource_tags(tags)
        record = builder.build()

        # Check that valid tags are included
        assert record.resource['tag:model'] == 'gpt-3.5-turbo'
        assert record.resource['tag:provider'] == 'openai'
        assert record.resource['tag:environment'] == 'production'

        # Check that None values are excluded
        assert 'tag:key_name' not in record.resource
        assert 'tag:team' not in record.resource

    def test_with_resource_tags_all_valid(self):
        """Test that all valid tags are included."""
        builder = CBFBuilder()

        # Add timestamp (required)
        builder.with_timestamp(datetime(2024, 1, 1, tzinfo=timezone.utc))

        # Add tags with all valid values
        tags = {
            'model': 'gpt-4',
            'provider': 'openai',
            'environment': 'production',
            'team': 'engineering'
        }

        builder.with_resource_tags(tags)
        record = builder.build()

        # Check that all tags are included
        assert record.resource['tag:model'] == 'gpt-4'
        assert record.resource['tag:provider'] == 'openai'
        assert record.resource['tag:environment'] == 'production'
        assert record.resource['tag:team'] == 'engineering'
