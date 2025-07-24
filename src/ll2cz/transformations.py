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
# CHANGELOG: 2025-01-24 - Extracted transformation functions for maximum clarity and reusability (erik.peterson)

"""Transformation functions for converting LiteLLM data to CZRN and CBF formats."""

import re
from datetime import datetime
from typing import Any, Optional, Union

import litellm
import polars as pl


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
    # Handle enum types
    if hasattr(provider, 'value'):
        provider_str = str(provider.value).lower()
    else:
        provider_str = str(provider).lower()

    # Define provider normalization mapping
    provider_mapping = {
        # OpenAI variants
        'openai': 'openai',
        'azure_openai': 'azure',
        'azure': 'azure',

        # Anthropic variants
        'anthropic': 'anthropic',
        'claude': 'anthropic',

        # AWS services
        'bedrock': 'aws',
        'aws_bedrock': 'aws',
        'sagemaker': 'aws',
        'aws_sagemaker': 'aws',
        'amazon_bedrock': 'aws',
        'amazon': 'aws',

        # Google/GCP services
        'vertex_ai': 'gcp',
        'gemini': 'gcp',
        'google': 'gcp',
        'gcp': 'gcp',
        'googleai': 'gcp',
        'google_vertex': 'gcp',
        'google_gemini': 'gcp',
        'palm': 'gcp',

        # Meta/Facebook
        'meta': 'meta',
        'facebook': 'meta',
        'llama': 'meta',

        # Microsoft
        'microsoft': 'microsoft',
        'bing': 'microsoft',

        # Other providers
        'cohere': 'cohere',
        'ai21': 'ai21',
        'huggingface': 'huggingface',
        'together_ai': 'together',
        'together': 'together',
        'fireworks_ai': 'fireworks',
        'fireworks': 'fireworks',
        'replicate': 'replicate',
        'mistral': 'mistral',
        'perplexity': 'perplexity',
        'groq': 'groq',
        'deepseek': 'deepseek',
        'deepinfra': 'deepinfra',
        'ollama': 'ollama',
        'openrouter': 'openrouter',
        'anyscale': 'anyscale',
        'vllm': 'vllm',
        'databricks': 'databricks',
        'watsonx': 'ibm',
        'ibm': 'ibm',
        'custom': 'custom',
        'local': 'local'
    }

    # Check if we have an exact mapping first
    if provider_str in provider_mapping:
        return provider_mapping[provider_str]

    # For unmapped providers, try dropping text after first "_" or "-"
    # e.g. "azure_ai" becomes "azure", "custom-llm" becomes "custom"
    base_provider = provider_str
    for separator in ['_', '-']:
        if separator in provider_str:
            base_provider = provider_str.split(separator)[0]
            break

    # Check if the base provider has a mapping
    if base_provider in provider_mapping:
        return provider_mapping[base_provider]

    # Return the base provider (after dropping suffix) or original if no separator found
    return base_provider


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
    component = re.sub(r'[^a-zA-Z0-9-]', '-', component)

    # Remove consecutive hyphens
    component = re.sub(r'-+', '-', component)

    # Strip leading/trailing hyphens
    component = component.strip('-')

    # Return 'unknown' if empty after normalization
    return component if component else 'unknown'


def extract_model_name(model: str) -> str:
    """Extract the core model name by removing version-related information.

    IMPORTANT: LLM model naming is subjective, inconsistent, and frankly insane across
    different providers. This algorithm attempts to extract the "core" model name by
    identifying and removing version-related components, but given the creative chaos
    of model naming conventions, this code will likely need periodic updates as new
    naming patterns emerge. The general intent is: preserve the model identity,
    discard the version/variant info.

    Key distinction:
    - Letter + number (e.g., "o1", "m7") = model name (preserve)
    - Number + letter (e.g., "4o", "3b") = version info (remove)

    Args:
        model: Full model identifier string

    Returns:
        Extracted core model name

    Examples:
        >>> extract_model_name("claude-3-5-haiku-20241022")
        'claude-haiku'
        >>> extract_model_name("claude-2.1")
        'claude'
        >>> extract_model_name("us.anthropic.claude-3-7-sonnet-20250219-v1:0")
        'claude-sonnet'
        >>> extract_model_name("gpt-4o")
        'gpt'
        >>> extract_model_name("o1-preview")
        'o1'
        >>> extract_model_name("text-moderation-stable")
        'text-moderation'
    """
    if not model:
        return 'unknown'

    original_model = model

    # Handle provider path prefixes (e.g., "fireworks_ai/accounts/fireworks/models/deepseek-v3")
    if '/' in model:
        model = model.split('/')[-1]

    # Handle AWS Bedrock format (e.g., "us.amazon.nova-lite-v1:0", "us.anthropic.claude-3-7-sonnet-20250219-v1:0")
    if ':' in model and '.' in model:
        # Extract the model part before the colon and after the provider
        parts = model.split(':')[0].split('.')
        if len(parts) >= 3:
            if parts[1] == 'amazon':
                model = '.'.join(parts[2:])  # e.g., "nova-lite-v1"
            elif parts[1] == 'anthropic':
                model = '.'.join(parts[2:])  # e.g., "claude-3-7-sonnet-20250219-v1"

    # Handle provider.model format (e.g., "amazon.titan-text-lite-v1")
    # Only apply this if the dot appears early in the string (likely a provider prefix)
    # and not if it's part of a version number (like "claude-2.1")
    if '.' in model and not model.startswith('gpt') and not model.startswith('text-'):
        parts = model.split('.')
        if len(parts) >= 2:
            # Only treat as provider.model if the first part looks like a provider
            # and the dot is not part of a version number at the end
            first_part = parts[0]
            # Check if first part is a known provider or looks like one (no hyphens, short)
            known_providers = {'amazon', 'google', 'microsoft', 'anthropic', 'openai', 'meta', 'cohere'}
            if (first_part in known_providers or
                (len(first_part) <= 10 and '-' not in first_part and not first_part.isdigit())):
                # Skip the provider part, keep the model part
                model = '.'.join(parts[1:])

    # Define version patterns that should be removed
    version_patterns = [
        r'^[0-9]+$',                    # Pure numbers: "4", "3", "2"
        r'^[0-9]+[a-z]$',               # Number+letter: "4o", "3b", "2t"
        r'^[0-9]+\.[0-9]+$',            # Semantic: "3.5", "2.1"
        r'^[0-9]+\.[0-9]+\.[0-9]+$',    # Full semantic: "1.2.3"
        r'^v[0-9]+$',                   # Version prefix: "v1", "v2"
        r'^v[0-9]+\.[0-9]+$',           # Version semantic: "v1.0", "v2.1"
        r'^[0-9]{4}\.[0-9]{2}\.[0-9]{2}$',  # Date format: "2024.01.15"
        r'^[0-9]{8}$',                  # Date format: "20240115", "20250219"
        r'^[0-9]{6}$',                  # Short date: "240115"
        r'^[0-9]+-[0-9]+-[0-9]+$',      # Hyphenated version: "3-7-sonnet" -> remove "3-7"
    ]

    # Version-related words that should be removed
    version_words = {
        'latest', 'stable', 'preview', 'beta', 'alpha',
        'rc', 'release', 'final', 'dev', 'nightly',
        'experimental', 'test', 'demo', 'trial', 'new',
        'updated', 'improved', 'enhanced', 'plus', 'pro',
        'hd', 'vision'  # Special modifiers that are versions, not model names
    }

    # Model variant words that should be PRESERVED (not considered versions)
    model_variants = {
        # Claude model variants
        'haiku', 'sonnet', 'opus', 'instant',
        # GPT model variants
        'turbo', 'instruct', 'vision', 'mini',
        # Common model variants
        'chat', 'text', 'base', 'small', 'medium', 'large',
        'xl', 'xxl', 'lite', 'light', 'fast', 'slow',
        # Nova model types
        'canvas', 'micro',
        # Other model indicators
        'embedding', 'ada', 'babbage', 'curie', 'davinci'
    }

    # Special handling for specific model families

    # Command-R models - always return 'command-r'
    if 'command' in model.lower() and 'r' in model.lower():
        return 'command-r'

    # Split model into parts
    parts = model.lower().split('-')
    if not parts:
        return model.lower()

    # Filter out version parts while preserving model variants
    filtered_parts = []

    for part in parts:
        # Skip empty parts
        if not part:
            continue

        # Check if part matches version patterns
        is_version = False
        for pattern in version_patterns:
            if re.match(pattern, part):
                is_version = True
                break

        # Skip if it's a version word (but not a model variant)
        if part in version_words:
            is_version = True

        # Preserve model variants even if they might look like versions
        if part in model_variants:
            is_version = False

        # Special case: preserve letter+number patterns (e.g., "o1", "m7")
        # but remove number+letter patterns (e.g., "4o", "3b")
        if re.match(r'^[a-z]+[0-9]+$', part):
            is_version = False  # This is a model name like "o1"
        elif re.match(r'^[0-9]+[a-z]+$', part):
            is_version = True   # This is a version like "4o"

        if not is_version:
            filtered_parts.append(part)

    # If we filtered everything out, fall back to the first part
    if not filtered_parts:
        filtered_parts = [parts[0]]

    result = '-'.join(filtered_parts)

    # Final cleanup - remove any trailing version-like suffixes
    result = re.sub(r'-+(latest|stable|preview|final|v[0-9]+)$', '', result)

    return result if result else original_model.lower()


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
    'spend': 'cost/cost',
    'prompt_tokens': 'usage/amount (partial)',
    'completion_tokens': 'usage/amount (partial)',
    'custom_llm_provider': 'resource/service (via normalize_service)',
    'key_alias': 'resource/account (via normalize_component, preferred)',
    'api_key': 'resource/account (via normalize_component, fallback)',
    'model': 'resource/usage_family (via extract_model_name)',
    # Resource tags - original fields (entity_id now used as resource tag since key_alias/api_key used for account)
    'entity_type': 'resource/tag:entity_type',
    'entity_id': 'resource/tag:entity_id',
    'api_requests': 'resource/tag:api_requests',
    'successful_requests': 'resource/tag:successful_requests',
    'failed_requests': 'resource/tag:failed_requests',
    'model_group': 'resource/tag:model_group',
    'cache_creation_input_tokens': 'resource/tag:cache_creation_tokens',
    'cache_read_input_tokens': 'resource/tag:cache_read_tokens',
    # Resource tags - enriched API key information
    'key_name': 'resource/tag:key_name',
    # Resource tags - enriched user information
    'user_alias': 'resource/tag:user_alias',
    'user_email': 'resource/tag:user_email',
    # Resource tags - enriched team information
    'team_alias': 'resource/tag:team_alias',
    'team_id': 'resource/tag:team_id',
    # Resource tags - enriched organization information
    'organization_alias': 'resource/tag:organization_alias',
    'organization_id': 'resource/tag:organization_id',
    # Note: resource/id comes from cloud-local-id, usage/units='tokens' (constant), lineitem/type='Usage' (constant), resource/tag:czrn contains full CZRN
}

# Additional CBF fields that are constants or derived (for display purposes)
CBF_CONSTANT_MAPPINGS = {
    '__resource_id__': 'resource/id (cloud-local-id)',
    '__usage_units__': 'usage/units (constant: "tokens")',
    '__lineitem_type__': 'lineitem/type (constant: "Usage")',
}
