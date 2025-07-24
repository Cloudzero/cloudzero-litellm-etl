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
# CHANGELOG: 2025-01-19 - Initial CZRN module for CloudZero Resource Names (erik.peterson)

"""CloudZero Resource Names (CZRN) generation and validation for LiteLLM resources."""

import re
from typing import Any

from .transformations import extract_model_name, normalize_component, normalize_service


class CZRNGenerator:
    """Generate CloudZero Resource Names (CZRNs) for LiteLLM resources."""

    CZRN_REGEX = re.compile(r'^czrn:([a-z0-9-]+):([a-zA-Z0-9-]+):([a-z0-9-]+):([a-z0-9-]+):([a-z0-9-]+):(.+)$')

    def __init__(self):
        """Initialize CZRN generator."""
        pass

    @staticmethod
    def extract_model_name(model: str) -> str:
        """Extract the core model name by removing version-related information.

        Delegates to the transformations.extract_model_name function for maximum
        reusability across the codebase.

        Args:
            model: Full model identifier string

        Returns:
            Extracted core model name
        """
        return extract_model_name(model)

    def create_from_litellm_data(self, row: dict[str, Any], error_tracker=None) -> str:
        """Create a CZRN from LiteLLM daily spend data.

        CZRN format: czrn:<provider>:<service-type>:<region>:<owner-account-id>:<resource-type>:<cloud-local-id>

        For LiteLLM resources, we map:
        - provider: 'litellm' (the service managing the LLM calls)
        - service-type: The custom_llm_provider (e.g., 'openai', 'anthropic', 'azure')
        - region: 'cross-region' (LiteLLM operates across regions)
        - owner-account-id: The key_alias (if available) or api_key as fallback
        - resource-type: Extracted model name (e.g., 'claude-haiku', 'gpt', 'gemini')
        - cloud-local-id: Full model identifier with optional provider prefix

        Args:
            row: LiteLLM data row
            error_tracker: Optional error tracker for consolidated error reporting
        """
        try:
            provider = 'litellm'
            custom_llm_provider = row.get('custom_llm_provider', 'unknown')
            service_type = self._normalize_service(custom_llm_provider)
            region = 'cross-region'

            # Use key_alias if available and not null, otherwise fallback to api_key for owner account
            key_alias = row.get('key_alias')
            api_key = row.get('api_key', 'unknown')

            if key_alias and key_alias.strip():
                owner_account_id = self._normalize_component(key_alias)
            else:
                owner_account_id = self._normalize_component(api_key)

            # Get the model for processing
            model = row.get('model', '').strip() if row.get('model') else ''

            # Validate model field is not empty, null, or asterisk
            if not model or model == '*':
                error_msg = "Cannot generate CZRN: model field is empty, null, or '*'"
                if error_tracker:
                    error_tracker.add_error('MISSING_MODEL', error_msg, row, 'CZRN', 'model')
                raise ValueError(error_msg)

            # Set cloud_local_id to custom_llm_provider/model if custom_llm_provider not in model
            if custom_llm_provider not in model:
                cloud_local_id = f"{custom_llm_provider}/{model}"
            else:
                cloud_local_id = model

            # Validate cloud_local_id is not invalid
            if not cloud_local_id or cloud_local_id.strip() == '' or cloud_local_id == '*':
                error_msg = f"Cannot generate CZRN: cloud_local_id is invalid (empty, null, or '*'): {cloud_local_id}"
                if error_tracker:
                    error_tracker.add_error('INVALID_CLOUD_LOCAL_ID', error_msg, row, 'CZRN', 'model')
                raise ValueError(error_msg)

            # Extract the core model name to use as the resource-type field
            resource_type = self.extract_model_name(model)

            czrn = self.create_from_components(
                provider=provider,
                service_type=service_type,
                region=region,
                owner_account_id=owner_account_id,
                resource_type=resource_type,
                cloud_local_id=cloud_local_id
            )

            if error_tracker:
                error_tracker.add_success()

            return czrn

        except Exception as e:
            if error_tracker:
                error_tracker.add_error('CZRN_GENERATION_FAILED', str(e), row, 'CZRN')
            raise

    def create_from_components(
        self,
        provider: str,
        service_type: str,
        region: str,
        owner_account_id: str,
        resource_type: str,
        cloud_local_id: str,
        error_tracker=None,
        source_data: dict = None
    ) -> str:
        """Create a CZRN from individual components.

        Args:
            provider: CZRN provider component
            service_type: CZRN service-type component
            region: CZRN region component
            owner_account_id: CZRN owner-account-id component
            resource_type: CZRN resource-type component
            cloud_local_id: CZRN cloud-local-id component
            error_tracker: Optional error tracker for consolidated error reporting
            source_data: Optional source data for error context
        """
        try:
            # Normalize components to ensure they meet CZRN requirements
            provider = self._normalize_component(provider, allow_uppercase=True)
            service_type = self._normalize_component(service_type)
            region = self._normalize_component(region)
            owner_account_id = self._normalize_component(owner_account_id)
            resource_type = self._normalize_component(resource_type)
            # cloud_local_id can contain pipes and other characters, so don't normalize it

            czrn = f"czrn:{provider}:{service_type}:{region}:{owner_account_id}:{resource_type}:{cloud_local_id}"

            if not self.is_valid(czrn):
                error_msg = f"Generated CZRN is invalid: {czrn}"
                if error_tracker and source_data:
                    error_tracker.add_error('INVALID_CZRN_FORMAT', error_msg, source_data, 'CZRN')
                raise ValueError(error_msg)

            return czrn

        except Exception as e:
            if error_tracker and source_data:
                error_tracker.add_error('CZRN_COMPONENT_ERROR', str(e), source_data, 'CZRN')
            raise

    def is_valid(self, czrn: str) -> bool:
        """Validate a CZRN string against the standard format."""
        return bool(self.CZRN_REGEX.match(czrn))

    def extract_components(self, czrn: str) -> tuple[str, str, str, str, str, str]:
        """Extract all components from a CZRN.

        Returns: (provider, service_type, region, owner_account_id, resource_type, cloud_local_id)
        """
        match = self.CZRN_REGEX.match(czrn)
        if not match:
            raise ValueError(f"Invalid CZRN format: {czrn}")

        return match.groups()

    def _normalize_service(self, provider: str) -> str:
        """Normalize provider names to standard CZRN format.

        Delegates to the transformations.normalize_service function for maximum
        reusability across the codebase.

        Args:
            provider: Provider identifier (LiteLLM enum, string, or other type)

        Returns:
            Normalized provider name as lowercase string
        """
        return normalize_service(provider)

    def _normalize_component(self, component: str, allow_uppercase: bool = False) -> str:
        """Normalize a CZRN component to meet format requirements.

        Delegates to the transformations.normalize_component function for maximum
        reusability across the codebase.

        Args:
            component: Raw component string to normalize
            allow_uppercase: Whether to preserve uppercase characters

        Returns:
            Normalized component string safe for CZRN usage
        """
        return normalize_component(component, allow_uppercase)

