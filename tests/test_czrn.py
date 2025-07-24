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
# CHANGELOG: 2025-01-19 - Initial tests for CZRN module (erik.peterson)

"""Tests for CloudZero Resource Names (CZRN) generation."""

import pytest

from ll2cz.czrn import CZRNGenerator


class TestCZRNGenerator:
    """Test CZRN generation functionality."""

    def test_create_from_components(self):
        """Test basic CZRN creation from components."""
        generator = CZRNGenerator()

        czrn = generator.create_from_components(
            provider='litellm',
            service_type='openai',
            region='cross-region',
            owner_account_id='key-abc123def456',
            resource_type='gpt-turbo',
            cloud_local_id='user|test_user|gpt-3.5-turbo'
        )

        expected = 'czrn:litellm:openai:cross-region:key-abc123def456:gpt-turbo:user|test_user|gpt-3.5-turbo'
        assert czrn == expected

    def test_create_from_litellm_data(self):
        """Test CZRN creation from LiteLLM daily spend data."""
        generator = CZRNGenerator()

        litellm_data = {
            'entity_type': 'user',
            'entity_id': 'test_user_123',
            'model': 'gpt-3.5-turbo',
            'date': '2024-01-01',
            'custom_llm_provider': 'openai',
            'api_key': 'sk-test123456789'
        }

        czrn = generator.create_from_litellm_data(litellm_data)

        # Should use api_key as owner-account-id and extracted model name as resource-type
        assert czrn == 'czrn:litellm:openai:cross-region:sk-test123456789:gpt-turbo:openai/gpt-3.5-turbo'

    def test_provider_normalization(self):
        """Test provider name normalization."""
        generator = CZRNGenerator()

        test_cases = [
            ('openai', 'openai'),
            ('anthropic', 'anthropic'),
            ('azure_openai', 'azure'),
            ('azure', 'azure'),
            ('aws_bedrock', 'aws'),
            ('aws', 'aws'),
            ('together_ai', 'together'),
            ('unknown_provider', 'unknown_provider'),
        ]

        for input_provider, expected in test_cases:
            normalized = generator._normalize_provider(input_provider)
            assert normalized == expected

    def test_component_normalization(self):
        """Test component normalization."""
        generator = CZRNGenerator()

        test_cases = [
            ('Test_Component', 'test-component'),
            ('UPPERCASE', 'uppercase'),
            ('with spaces', 'with-spaces'),
            ('with@special!chars', 'with-special-chars'),
            ('multiple---hyphens', 'multiple-hyphens'),
            ('-leading-trailing-', 'leading-trailing'),
            ('', 'unknown'),
        ]

        for input_comp, expected in test_cases:
            normalized = generator._normalize_component(input_comp)
            assert normalized == expected

    def test_czrn_validation(self):
        """Test CZRN validation."""
        generator = CZRNGenerator()

        # Valid CZRNs
        valid_czrns = [
            'czrn:litellm:openai:cross-region:key-abc123:llm-usage:user|test|model',
            'czrn:ec2:aws:us-east-1:123456789012:instance:i-0abc123def456789',
            'czrn:compute:azure:eastus:subscription-abc123:virtualmachine:my-vm'
        ]

        for czrn in valid_czrns:
            assert generator.is_valid(czrn), f"Should be valid: {czrn}"

        # Invalid CZRNs
        invalid_czrns = [
            'not-a-czrn',
            'czrn:only:five:components:here',
            'czrn:invalid:components:with:UPPERCASE:Resource:id',
            ''
        ]

        for czrn in invalid_czrns:
            assert not generator.is_valid(czrn), f"Should be invalid: {czrn}"

    def test_component_extraction(self):
        """Test extracting components from CZRN."""
        generator = CZRNGenerator()

        czrn = 'czrn:litellm:openai:cross-region:key-abc123:gpt-turbo:user|test_user|gpt-3.5-turbo'

        components = generator.extract_components(czrn)
        expected = ('litellm', 'openai', 'cross-region', 'key-abc123', 'gpt-turbo', 'user|test_user|gpt-3.5-turbo')

        assert components == expected

    def test_extract_components_invalid_czrn(self):
        """Test extracting components from invalid CZRN raises error."""
        generator = CZRNGenerator()

        with pytest.raises(ValueError, match="Invalid CZRN format"):
            generator.extract_components('invalid-czrn')

    def test_team_entity_type(self):
        """Test CZRN generation for team entity type."""
        generator = CZRNGenerator()

        team_data = {
            'entity_type': 'team',
            'entity_id': 'engineering_team',
            'model': 'gpt-4',
            'date': '2024-01-02',
            'custom_llm_provider': 'openai',
            'api_key': 'sk-team123456'
        }

        czrn = generator.create_from_litellm_data(team_data)

        # Should use api_key as owner-account-id and extracted model name as resource-type
        assert czrn.endswith(':openai/gpt-4')
        assert czrn.startswith('czrn:litellm:openai:cross-region:sk-team123456:gpt:')

    def test_unknown_provider_handling(self):
        """Test handling of unknown/missing provider."""
        generator = CZRNGenerator()

        data_no_provider = {
            'entity_type': 'user',
            'entity_id': 'test_user',
            'model': 'custom-model',
            'date': '2024-01-01',
            'api_key': 'sk-test123'
            # No custom_llm_provider field
        }

        czrn = generator.create_from_litellm_data(data_no_provider)
        # Should use api_key as owner-account-id
        assert czrn.startswith('czrn:litellm:unknown:cross-region:sk-test123:')

    def test_create_from_components_invalid_generates_error(self):
        """Test that invalid component combinations raise errors."""
        generator = CZRNGenerator()

        # This should raise ValueError because the resulting CZRN would be invalid
        with pytest.raises(ValueError, match="Generated CZRN is invalid"):
            generator.create_from_components(
                service_type='',  # Empty service type
                provider='',  # Empty provider
                region='',  # Empty region
                owner_account_id='',  # Empty account
                resource_type='',  # Empty resource type
                cloud_local_id=''  # Empty cloud local id
            )

