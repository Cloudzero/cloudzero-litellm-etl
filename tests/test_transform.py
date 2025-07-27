# SPDX-FileCopyrightText: Copyright (c), CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for CBF transformation logic."""


import polars as pl

from ll2cz.transform import CBFTransformer


class TestCBFTransformer:
    """Test CBF transformation functionality."""

    def test_empty_dataframe(self):
        """Test transformation of empty DataFrame."""
        transformer = CBFTransformer()
        result = transformer.transform(pl.DataFrame())
        assert result.is_empty()

    def test_basic_transformation(self):
        """Test basic transformation with daily spend data."""
        transformer = CBFTransformer()

        # Daily spend table structure
        data = pl.DataFrame([{
            'id': 'spend_123',
            'date': '2024-01-01',
            'entity_id': 'user_456',
            'entity_type': 'user',
            'api_key': 'sk-test123',
            'model': 'gpt-3.5-turbo',
            'model_group': 'openai/gpt-3.5-turbo',
            'custom_llm_provider': 'openai',
            'prompt_tokens': 100,
            'completion_tokens': 50,
            'spend': 0.002,
            'api_requests': 1,
            'successful_requests': 1,
            'failed_requests': 0,
            'cache_creation_input_tokens': 0,
            'cache_read_input_tokens': 0
        }])

        result = transformer.transform(data)

        assert len(result) == 1
        record = result.row(0, named=True)

        # Check CBF format fields with namespaced names
        assert record['resource/service'] == 'openai'  # service-type from custom_llm_provider
        assert record['resource/account'] == 'sk-test123'  # owner-account-id from api_key
        assert record['resource/id'] == 'openai/gpt-3.5-turbo'  # Now contains cloud-local-id
        assert record['resource/tag:czrn'] == 'czrn:litellm:openai:cross-region:sk-test123:gpt-turbo:openai/gpt-3.5-turbo'  # Full CZRN in tag
        assert record['cost/cost'] == 0.002
        assert record['usage/amount'] == 150  # prompt + completion tokens
        assert record['usage/units'] == 'tokens'
        assert record['resource/tag:prompt_tokens'] == '100'
        assert record['resource/tag:completion_tokens'] == '50'
        assert record['time/usage_start'] == '2024-01-01T00:00:00+00:00'  # ISO format with timezone
        assert record['lineitem/type'] == 'Usage'

        # Check resource tags (dimensions are now stored as resource/tag: fields)
        assert record['resource/tag:model'] == 'openai/gpt-3.5-turbo'  # cloud-local-id
        assert record['resource/tag:entity_id'] == 'user_456'
        assert record['resource/tag:entity_type'] == 'user'
        assert record['resource/tag:provider'] == 'openai'

    def test_team_transformation(self):
        """Test transformation with team entity type."""
        transformer = CBFTransformer()

        data = pl.DataFrame([{
            'id': 'team_spend_456',
            'date': '2024-01-02',
            'entity_id': 'team_engineering',
            'entity_type': 'team',
            'api_key': 'sk-team789',
            'model': 'gpt-4',
            'model_group': 'openai/gpt-4',
            'custom_llm_provider': 'openai',
            'prompt_tokens': 200,
            'completion_tokens': 100,
            'spend': 0.05,
            'api_requests': 5,
            'successful_requests': 4,
            'failed_requests': 1,
            'cache_creation_input_tokens': 0,
            'cache_read_input_tokens': 0
        }])

        result = transformer.transform(data)
        record = result.row(0, named=True)

        assert record['resource/id'] == 'openai/gpt-4'  # Now contains cloud-local-id
        assert record['resource/tag:czrn'] == 'czrn:litellm:openai:cross-region:sk-team789:gpt:openai/gpt-4'  # Full CZRN in tag
        assert record['usage/amount'] == 300  # 200 + 100 tokens
        assert record['cost/cost'] == 0.05

        # Check resource tags (dimensions are now stored as resource/tag: fields)
        assert record['resource/tag:entity_type'] == 'team'
        assert record['resource/tag:entity_id'] == 'team_engineering'
        assert record['resource/tag:api_requests'] == '5'
        assert record['resource/tag:successful_requests'] == '4'
        assert record['resource/tag:failed_requests'] == '1'

    def test_date_parsing(self):
        """Test date parsing for usage_start field."""
        transformer = CBFTransformer()

        data = pl.DataFrame([{
            'id': 'date_test_123',
            'date': '2024-12-25',  # Christmas day
            'entity_id': 'test_user',
            'entity_type': 'user',
            'api_key': 'sk-test',
            'model': 'gpt-3.5-turbo',
            'model_group': 'openai/gpt-3.5-turbo',
            'custom_llm_provider': 'openai',
            'prompt_tokens': 50,
            'completion_tokens': 25,
            'spend': 0.001,
            'api_requests': 1,
            'successful_requests': 1,
            'failed_requests': 0,
            'cache_creation_input_tokens': 0,
            'cache_read_input_tokens': 0
        }])

        result = transformer.transform(data)
        record = result.row(0, named=True)

        # Should parse to midnight UTC with timezone
        assert record['time/usage_start'] == '2024-12-25T00:00:00+00:00'

