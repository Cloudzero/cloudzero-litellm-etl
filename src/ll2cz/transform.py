# SPDX-FileCopyrightText: Copyright (c), CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Transform LiteLLM data to CloudZero AnyCost CBF format."""

from typing import Any

import polars as pl

from .czrn import CZRNGenerator
from .error_tracking import ConsolidatedErrorTracker
from .transformations import parse_date


class CBFTransformer:
    """Transform LiteLLM usage data to CloudZero Billing Format (CBF)."""

    def __init__(self):
        """Initialize transformer with CZRN generator."""
        self.czrn_generator = CZRNGenerator()
        self.error_tracker = ConsolidatedErrorTracker()

    def transform(self, data: pl.DataFrame, use_error_tracking: bool = False) -> pl.DataFrame:
        """Transform LiteLLM data to CBF format, dropping records with zero successful_requests or invalid CZRNs.

        Args:
            data: Input LiteLLM data
            use_error_tracking: Whether to use consolidated error tracking
        """
        if data.is_empty():
            return pl.DataFrame()

        # Reset error tracker for new transformation
        if use_error_tracking:
            self.error_tracker = ConsolidatedErrorTracker()

        # Filter out records with zero successful_requests first
        original_count = len(data)
        if 'successful_requests' in data.columns:
            filtered_data = data.filter(pl.col('successful_requests') > 0)
            zero_requests_dropped = original_count - len(filtered_data)
        else:
            filtered_data = data
            zero_requests_dropped = 0

        cbf_data = []
        czrn_dropped_count = 0
        filtered_count = len(filtered_data)

        for row in filtered_data.iter_rows(named=True):
            if use_error_tracking:
                self.error_tracker.increment_total()

            try:
                cbf_record = self._create_cbf_record(row, use_error_tracking=use_error_tracking)
                # Only include the record if CZRN generation was successful
                cbf_data.append(cbf_record)
                if use_error_tracking:
                    # Success is tracked within _create_cbf_record
                    pass
            except Exception as e:
                # Skip records that fail CZRN generation
                czrn_dropped_count += 1
                if use_error_tracking:
                    self.error_tracker.add_error('CBF_TRANSFORMATION_FAILED', str(e), row, 'CBF')
                continue

        # Print summary of dropped records if any
        from rich.console import Console
        console = Console()

        if zero_requests_dropped > 0:
            console.print(f"[yellow]⚠️  Dropped {zero_requests_dropped:,} of {original_count:,} records with zero successful_requests[/yellow]")

        if czrn_dropped_count > 0:
            console.print(f"[yellow]⚠️  Dropped {czrn_dropped_count:,} of {filtered_count:,} filtered records due to invalid CZRNs[/yellow]")

        if len(cbf_data) > 0:
            console.print(f"[green]✓ Successfully transformed {len(cbf_data):,} records[/green]")

        return pl.DataFrame(cbf_data)

    def _create_cbf_record(self, row: dict[str, Any], use_error_tracking: bool = False) -> dict[str, Any]:
        """Create a single CBF record from LiteLLM daily spend row.

        CZRN components are mapped to supported CBF fields where possible:
        CZRN format: czrn:<provider>:<service-type>:<region>:<owner-account-id>:<resource-type>:<cloud-local-id>

        - CZRN provider → resource/tag:czrn_provider (resource tag) ["litellm"]
        - CZRN service-type → resource/service (standard CBF field) [custom_llm_provider]
        - CZRN region → resource/region (standard CBF field) ["cross-region"]
        - CZRN owner-account-id → resource/account (standard CBF field) [key_alias or api_key]
        - CZRN resource-type → resource/usage_family (standard CBF field) [extracted model name]
        - CZRN cloud-local-id → resource/id (standard CBF field) + resource/tag:model (resource tag) [model identifier]
        - Full CZRN → resource/tag:czrn (resource tag) [complete CZRN string]
        """

        # Parse date (daily spend tables use date strings like '2025-04-19')
        usage_date = parse_date(row.get('date'))

        # Calculate total tokens
        prompt_tokens = int(row.get('prompt_tokens', 0))
        completion_tokens = int(row.get('completion_tokens', 0))
        total_tokens = prompt_tokens + completion_tokens

        # Create CloudZero Resource Name (CZRN)
        error_tracker = self.error_tracker if use_error_tracking else None
        full_czrn = self.czrn_generator.create_from_litellm_data(row, error_tracker)

        # Build dimensions for CloudZero
        entity_id = str(row.get('entity_id', ''))
        model = str(row.get('model', ''))
        api_key_full = str(row.get('api_key', ''))  # Full API key for identification

        dimensions = {
            # Original fields
            'entity_type': str(row.get('entity_type', '')),  # 'user' or 'team'
            'entity_id': entity_id,
            'model_original': model,  # Original model name (renamed to avoid conflict)
            'model_group': str(row.get('model_group', '')),
            'provider': str(row.get('custom_llm_provider', '')),
            'api_key': api_key_full,
            'api_requests': str(row.get('api_requests', 0)),
            'successful_requests': str(row.get('successful_requests', 0)),
            'failed_requests': str(row.get('failed_requests', 0)),
            'cache_creation_tokens': str(row.get('cache_creation_input_tokens', 0)),
            'cache_read_tokens': str(row.get('cache_read_input_tokens', 0)),
            # Enriched API key information
            'key_name': row.get('key_name', ''),
            'key_alias': row.get('key_alias', ''),
            # Enriched user information
            'user_alias': row.get('user_alias', ''),
            'user_email': row.get('user_email', ''),
            # Enriched team information
            'team_alias': row.get('team_alias', ''),
            'team_id': row.get('team_id', ''),
            # Enriched organization information
            'organization_alias': row.get('organization_alias', ''),
            'organization_id': row.get('organization_id', ''),
        }

        # Extract CZRN components to populate corresponding CBF columns
        try:
            czrn_components = self.czrn_generator.extract_components(full_czrn)
            provider, service_type, region, owner_account_id, resource_type, cloud_local_id = czrn_components
        except Exception as e:
            if use_error_tracking:
                self.error_tracker.add_error('CZRN_COMPONENT_EXTRACTION_FAILED', str(e), row, 'CBF')
            raise

        # CloudZero CBF format with proper column names
        cbf_record = {
            # Required CBF fields
            'time/usage_start': usage_date.isoformat() if usage_date else None,  # Required: ISO-formatted UTC datetime
            'cost/cost': float(row.get('spend', 0.0)),  # Required: billed cost
            'resource/id': cloud_local_id,  # Required when resource tags are present

            # Usage metrics for token consumption
            'usage/amount': total_tokens,  # Numeric value of tokens consumed
            'usage/units': 'tokens',  # Description of token units

            # Standard CBF fields for CZRN components
            'resource/service': service_type,  # Maps to CZRN service-type (custom_llm_provider)
            'resource/account': owner_account_id,  # Maps to CZRN owner-account-id (key_alias or api_key)
            'resource/region': region,  # Maps to CZRN region (cross-region)
            'resource/usage_family': resource_type,  # Maps to CZRN resource-type (extracted model name)

            # Line item details
            'lineitem/type': 'Usage',  # Standard usage line item
        }

        # Add CZRN components that don't have standard CBF field mappings as resource tags
        cbf_record['resource/tag:czrn_provider'] = provider  # CZRN provider component ("litellm")
        cbf_record['resource/tag:model'] = cloud_local_id  # CZRN cloud-local-id component
        cbf_record['resource/tag:czrn'] = full_czrn  # Full CZRN for reference

        # Add resource tags for all dimensions (using resource/tag:<key> format)
        for key, value in dimensions.items():
            if value is not None and value != '' and value != 'N/A':  # Only add non-empty, non-None tags
                cbf_record[f'resource/tag:{key}'] = str(value)

        # Add token breakdown as resource tags for analysis
        if prompt_tokens > 0:
            cbf_record['resource/tag:prompt_tokens'] = str(prompt_tokens)
        if completion_tokens > 0:
            cbf_record['resource/tag:completion_tokens'] = str(completion_tokens)
        if total_tokens > 0:
            cbf_record['resource/tag:total_tokens'] = str(total_tokens)

        return cbf_record



