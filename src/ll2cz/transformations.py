# SPDX-FileCopyrightText: Copyright (c), CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Transformation functions for converting LiteLLM data to CZRN and CBF formats."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

import litellm
import polars as pl
import yaml

# Import the new model name extraction
from .model_name_strategies import extract_model_name


class ProviderNormalizer:
    """Handle provider normalization using configuration."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize with configuration from YAML file."""
        if config_path is None:
            config_path = Path(__file__).parent / 'config' / 'providers.yml'
        
        # Load configuration
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                self.provider_mapping = config.get('provider_mappings', {})
        else:
            # Fallback to minimal defaults if config file doesn't exist
            self.provider_mapping = {
                'openai': 'openai',
                'azure': 'azure',
                'anthropic': 'anthropic',
                'bedrock': 'aws',
                'google': 'gcp',
                'custom': 'custom'
            }
    
    def normalize(self, provider: Union[str, litellm.LlmProviders, Any]) -> str:
        """Normalize provider name."""
        # Handle enum types
        if hasattr(provider, 'value'):
            provider_str = str(provider.value).lower()
        else:
            provider_str = str(provider).lower()
        
        # Check if we have an exact mapping first
        if provider_str in self.provider_mapping:
            return self.provider_mapping[provider_str]
        
        # For unmapped providers, try dropping text after first "_" or "-"
        base_provider = provider_str
        for separator in ['_', '-']:
            if separator in provider_str:
                base_provider = provider_str.split(separator)[0]
                break
        
        # Check if the base provider has a mapping
        if base_provider in self.provider_mapping:
            return self.provider_mapping[base_provider]
        
        # Return the base provider or original if no separator found
        return base_provider


# Global instance for backward compatibility
_provider_normalizer = ProviderNormalizer()


def normalize_service(provider: Union[str, litellm.LlmProviders, Any]) -> str:
    """Normalize LiteLLM provider names to standard CZRN format.

    Maps various provider representations (enum values, strings, variations)
    to standardized provider names for consistent CZRN generation.

    Args:
        provider: Provider identifier (LiteLLM enum, string, or other type)

    Returns:
        Normalized provider name as lowercase string

    Examples:
        >>> normalize_service("openai")
        'openai'
        >>> normalize_service("azure_openai")
        'azure'
        >>> normalize_service("azure_ai")
        'azure'
        >>> normalize_service("bedrock")
        'aws'
        >>> normalize_service("custom_provider")
        'custom'
    """
    return _provider_normalizer.normalize(provider)


def normalize_component(component: str, allow_uppercase: bool = False) -> str:
    """Normalize CZRN components to meet format requirements.

    Ensures components contain only alphanumeric characters and hyphens,
    following CZRN naming conventions.

    Args:
        component: Raw component string to normalize
        allow_uppercase: Whether to preserve uppercase characters

    Returns:
        Normalized component string safe for CZRN usage

    Examples:
        >>> normalize_component("My Entity 123!")
        'my-entity-123'
        >>> normalize_component("test@domain.com")
        'test-domain-com'
        >>> normalize_component("")
        'unknown'
    """
    if not component:
        return 'unknown'

    # Convert to lowercase unless uppercase is allowed
    if not allow_uppercase:
        component = component.lower()

    # Replace invalid characters with hyphens
    # Valid: alphanumeric and hyphens
    import re
    component = re.sub(r'[^a-zA-Z0-9-]', '-', component)

    # Remove consecutive hyphens
    component = re.sub(r'-+', '-', component)

    # Strip leading/trailing hyphens
    component = component.strip('-')

    # Return 'unknown' if empty after normalization
    return component if component else 'unknown'


def generate_resource_id(model: str, provider: str = None) -> str:
    """Generate a consistent resource ID from model name for use as cloud-local-id in CZRN and resource/id in CBF.
    
    This function creates the unique identifier for a model resource by using the actual model name
    (e.g., model_group) with colons replaced by pipes for compatibility.
    
    Args:
        model: The model name/identifier from LiteLLM (e.g., "gpt-4", "us.anthropic.claude-3-haiku:0")
        provider: Optional provider name to prepend if not already in model string
        
    Returns:
        A consistent resource ID with colons replaced by pipes
        
    Examples:
        >>> generate_resource_id("gpt-4", "openai")
        'openai/gpt-4'
        >>> generate_resource_id("openai/gpt-4")
        'openai/gpt-4'
        >>> generate_resource_id("us.anthropic.claude-3-haiku:0", "bedrock")
        'bedrock/us.anthropic.claude-3-haiku|0'
        >>> generate_resource_id("bedrock/us.amazon.nova-lite-v1:0")
        'bedrock/us.amazon.nova-lite-v1|0'
    """
    if not model or model.strip() == '' or model == '*':
        return 'unknown/unknown'
    
    model = model.strip()
    
    # If provider is specified and not already in the model string, prepend it
    if provider and provider not in model and '/' not in model:
        resource_id = f"{provider}/{model}"
    else:
        resource_id = model
    
    # Replace colons with pipes for CZRN compatibility
    resource_id = resource_id.replace(':', '|')
    
    return resource_id


def parse_date(date_value: Union[str, datetime, None]) -> Optional[datetime]:
    """Parse date strings from LiteLLM daily spend tables into datetime objects.

    Handles various date formats commonly found in LiteLLM data,
    converting them to standardized datetime objects for CBF usage.

    Args:
        date_value: Date in string format, datetime object, or None

    Returns:
        Parsed datetime object or None if parsing fails

    Examples:
        >>> parse_date("2024-01-15")
        datetime.datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc)
        >>> parse_date("2024-01-15T10:30:00Z")
        datetime.datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
        >>> parse_date(None)
        None
    """
    if date_value is None:
        return None

    if isinstance(date_value, datetime):
        return date_value

    if not isinstance(date_value, str):
        return None

    try:
        # Try parsing as YYYY-MM-DD format (most common in daily spend tables)
        # Use Polars for consistent date parsing to midnight UTC
        date_series = pl.Series([date_value])
        parsed_series = date_series.str.to_datetime(format='%Y-%m-%d', time_zone='UTC')
        # Convert polars datetime to python datetime
        return parsed_series.to_list()[0]
    except Exception:
        try:
            # Fallback: try ISO format parsing
            date_series = pl.Series([date_value])
            parsed_series = date_series.str.to_datetime(time_zone='UTC')
            return parsed_series.to_list()[0]
        except Exception:
            # All parsing attempts failed
            return None


# Base field mappings (shared between user tables and logs)
_BASE_CBF_MAPPINGS = {
    'spend': 'cost/cost',
    'prompt_tokens': 'usage/amount (partial)',
    'completion_tokens': 'usage/amount (partial)',
    'custom_llm_provider': 'resource/service (via normalize_service)',
    'entity_type': 'resource/tag:entity_type',
    'entity_id': 'resource/tag:entity_id',
    'api_requests': 'resource/tag:api_requests',
    'successful_requests': 'resource/tag:successful_requests',
    'failed_requests': 'resource/tag:failed_requests',
    'model_group': 'resource/tag:model_group',
    # Enriched API key information
    # Note: key_name is NOT a sensitive value - it's already truncated/masked in the source database
    'key_name': 'resource/tag:key_name',
    # Enriched user information
    'user_alias': 'resource/tag:user_alias',
    'user_email': 'resource/tag:user_email',
    # Enriched team information
    'team_alias': 'resource/tag:team_alias',
    'team_id': 'resource/tag:team_id',
    # Enriched organization information
    'organization_alias': 'resource/tag:organization_alias',
    'organization_id': 'resource/tag:organization_id',
}

# Mapping dictionaries for field analysis and documentation
CZRN_FIELD_MAPPINGS = {
    'custom_llm_provider': 'service-type (via normalize_service)',
    'key_alias': 'owner-account-id (via normalize_component, preferred)',
    'api_key': 'owner-account-id (via normalize_component, fallback)',
    'model': 'resource-type (via extract_model_name)',
    # Note: provider='litellm' (constant), region='cross-region' (constant)
    # cloud-local-id is derived from custom_llm_provider + model
}

# Additional CZRN components that are constants or derived (for display purposes)
CZRN_CONSTANT_MAPPINGS = {
    '__provider__': 'provider (constant: "litellm")',
    '__region__': 'region (constant: "cross-region")',
    '__cloud_local_id__': 'cloud-local-id (derived from provider + model)',
}

CBF_FIELD_MAPPINGS = {
    # Standard CBF fields
    'date': 'time/usage_start (via parse_date)',
    'key_alias': 'resource/account (via normalize_component, preferred)',
    'api_key': 'resource/account (via normalize_component, fallback)',
    'model': 'resource/usage_family (via extract_model_name)',
    'cache_creation_input_tokens': 'resource/tag:cache_creation_tokens',
    'cache_read_input_tokens': 'resource/tag:cache_read_tokens',
    # Include all base mappings
    **_BASE_CBF_MAPPINGS,
    # Note: resource/id comes from cloud-local-id, usage/units='tokens' (constant), lineitem/type='Usage' (constant), resource/tag:czrn contains full CZRN
}

# Additional CBF fields that are constants or derived (for display purposes)
CBF_CONSTANT_MAPPINGS = {
    '__resource_id__': 'resource/id (cloud-local-id)',
    '__usage_units__': 'usage/units (constant: "tokens")',
    '__lineitem_type__': 'lineitem/type (constant: "Usage")',
    '__resource_tag_czrn__': 'resource/tag:czrn (full CZRN)',
}

# SpendLogs-specific field mappings (when --source logs is used)
SPENDLOGS_CZRN_FIELD_MAPPINGS = {
    'custom_llm_provider': 'service-type (via normalize_service)',
    'key_alias': 'owner-account-id (via normalize_component, preferred)',
    'api_key': 'owner-account-id (via normalize_component, fallback)',
    'call_type': 'resource-type (direct mapping)',  # KEY DIFFERENCE: use call_type instead of model
    # Note: provider='litellm' (constant), region='cross-region' (constant)
    # cloud-local-id is derived from custom_llm_provider + model
}

SPENDLOGS_CBF_FIELD_MAPPINGS = {
    # Standard CBF fields
    'start_time': 'time/usage_start (via parse_date)',
    'key_alias': 'resource/account (via normalize_component, preferred)',
    'api_key': 'resource/account (via normalize_component, fallback)',
    'call_type': 'resource/usage_family (direct mapping)',  # KEY DIFFERENCE: use call_type instead of model
    # SpendLogs-specific fields
    'request_id': 'resource/tag:request_id',
    'model': 'resource/tag:model',  # Model becomes a tag in SpendLogs
    'end_user': 'resource/tag:end_user',
    'enriched_team_id': 'resource/tag:enriched_team_id',
    # Include all base mappings
    **_BASE_CBF_MAPPINGS,
}


def get_field_mappings(source: str = 'usertable') -> Dict[str, Dict[str, Any]]:
    """Get field mappings based on data source.
    
    Args:
        source: Data source type ('usertable' or 'logs')
        
    Returns:
        Dictionary containing CZRN and CBF field mappings
    """
    if source == 'logs':
        return {
            'czrn': SPENDLOGS_CZRN_FIELD_MAPPINGS,
            'cbf': SPENDLOGS_CBF_FIELD_MAPPINGS,
            'czrn_constants': CZRN_CONSTANT_MAPPINGS,
            'cbf_constants': CBF_CONSTANT_MAPPINGS
        }
    else:
        return {
            'czrn': CZRN_FIELD_MAPPINGS,
            'cbf': CBF_FIELD_MAPPINGS,
            'czrn_constants': CZRN_CONSTANT_MAPPINGS,
            'cbf_constants': CBF_CONSTANT_MAPPINGS
        }