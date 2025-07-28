# SPDX-FileCopyrightText: Copyright (c), CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Centralized data processing layer for CZRN and CBF generation.

This module provides a unified interface for processing LiteLLM data into
CloudZero Resource Names (CZRNs) and CloudZero Bill Format (CBF) records,
eliminating duplication and ensuring consistent transformations across the codebase.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import polars as pl

from .error_tracking import ConsolidatedErrorTracker
from .transformations import (
    extract_model_name,
    generate_resource_id,
    get_field_mappings,
    normalize_component,
    normalize_service,
    parse_date,
)


class DataProcessor:
    """Centralized processor for CZRN and CBF generation from LiteLLM data.

    This class provides a single interface for all data transformation operations,
    eliminating duplication across CZRN generation, CBF transformation, and analysis.
    """

    def __init__(self, source: str = "usertable"):
        """Initialize data processor for specific data source.

        Args:
            source: Data source type ("usertable" or "logs")
        """
        if source not in ["usertable", "logs"]:
            raise ValueError(f"Invalid source: {source}. Must be 'usertable' or 'logs'")

        self.source = source
        self.error_tracker = ConsolidatedErrorTracker()

        # Get field mappings based on source
        mappings = get_field_mappings(source)
        self.czrn_mappings = mappings['czrn']
        self.cbf_mappings = mappings['cbf']
        self.czrn_constants = mappings['czrn_constants']
        self.cbf_constants = mappings['cbf_constants']
        
        # Set field names based on source
        if source == "logs":
            self.resource_type_field = "call_type"
            self.usage_family_field = "call_type"
        else:
            self.resource_type_field = "model"
            self.usage_family_field = "model"

    def create_czrn(self, record: Dict[str, Any]) -> Optional[str]:
        """Create a CloudZero Resource Name from a data record.

        Args:
            record: Dictionary containing record data

        Returns:
            Generated CZRN string or None if generation fails
        """
        try:
            # Extract and normalize service type
            service_type = self._extract_and_transform_field(
                record, "custom_llm_provider", normalize_service
            )

            # Extract and normalize owner account
            owner_account = self._get_owner_account(record)

            # Extract and normalize resource type
            resource_type = self._get_resource_type(record)

            # Validate required fields
            if not service_type or not owner_account or not resource_type:
                self._track_czrn_error(record, service_type, owner_account, resource_type)
                return None

            # Build CZRN components
            provider = "litellm"
            region = "cross-region"
            # Use consistent cloud-local-id construction (always use extracted model name)
            cloud_local_id = self._get_cloud_local_id(record)

            # Construct CZRN
            czrn = f"czrn:{provider}:{service_type}:{region}:{owner_account}:{resource_type}:{cloud_local_id}"

            return czrn

        except Exception as e:
            self.error_tracker.add_error("CZRN_GENERATION_FAILED", str(e), record, "CZRN")
            return None

    def create_cbf_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Create a CloudZero Bill Format record from a data record.

        Args:
            record: Dictionary containing record data

        Returns:
            CBF-formatted record dictionary
        """
        # Generate CZRN for this record
        czrn = self.create_czrn(record)

        # Extract core CBF fields
        cbf_record = {
            # Time and cost
            "time/usage_start": self._get_usage_start_time(record),
            "cost/cost": self._extract_field(record, "spend", 0.0),

            # Usage information
            "usage/amount": self._calculate_total_tokens(record),
            "usage/units": "tokens",

            # Resource information
            "resource/service": self._extract_and_transform_field(
                record, "custom_llm_provider", normalize_service
            ),
            "resource/account": self._get_owner_account(record),
            "resource/region": "cross-region",
            "resource/usage_family": self._get_usage_family(record),
            "resource/id": self._get_cloud_local_id(record),

            # Line item information
            "lineitem/type": "Usage",
        }

        # Add resource tags
        resource_tags = self._build_resource_tags(record, czrn)
        cbf_record.update(resource_tags)

        return cbf_record

    def process_dataframe(self, df: pl.DataFrame) -> Tuple[List[str], List[Dict[str, Any]], Dict[str, Any]]:
        """Process a polars DataFrame to generate CZRNs and CBF records.

        Args:
            df: Input DataFrame with LiteLLM data

        Returns:
            Tuple of (czrn_list, cbf_records_list, error_summary)
        """
        czrns = []
        cbf_records = []

        # Convert to list of dictionaries for processing
        records = df.to_dicts()

        for record in records:
            # Generate CZRN
            czrn = self.create_czrn(record)
            if czrn:
                czrns.append(czrn)

            # Generate CBF record
            cbf_record = self.create_cbf_record(record)
            cbf_records.append(cbf_record)

        # Get error summary
        error_summary = self.error_tracker.get_error_summary()

        return czrns, cbf_records, error_summary

    def get_field_mappings(self) -> Dict[str, Dict[str, str]]:
        """Get field mappings for current data source.

        Returns:
            Dictionary with 'czrn' and 'cbf' mapping dictionaries
        """
        return {
            "czrn": {**self.czrn_mappings, **self.czrn_constants},
            "cbf": {**self.cbf_mappings, **self.cbf_constants}
        }

    def analyze_field_mapping(self, df: pl.DataFrame) -> Dict[str, Any]:
        """Analyze field mapping coverage for the current data source.

        Args:
            df: Input DataFrame to analyze

        Returns:
            Field mapping analysis results
        """
        all_mappings = self.get_field_mappings()
        source_columns = set(df.columns)

        # Categorize fields
        both_mapped = set()
        czrn_only = set()
        cbf_only = set()
        unmapped = set()

        for field in source_columns:
            in_czrn = field in all_mappings["czrn"]
            in_cbf = field in all_mappings["cbf"]

            if in_czrn and in_cbf:
                both_mapped.add(field)
            elif in_czrn:
                czrn_only.add(field)
            elif in_cbf:
                cbf_only.add(field)
            else:
                unmapped.add(field)

        return {
            "source": self.source,
            "total_fields": len(source_columns),
            "both_mapped": len(both_mapped),
            "czrn_only": len(czrn_only),
            "cbf_only": len(cbf_only),
            "unmapped": len(unmapped),
            "both_mapped_fields": sorted(both_mapped),
            "czrn_only_fields": sorted(czrn_only),
            "cbf_only_fields": sorted(cbf_only),
            "unmapped_fields": sorted(unmapped),
            "mappings": all_mappings
        }

    # Private helper methods

    def _extract_field(self, record: Dict[str, Any], field: str, default: Any = None) -> Any:
        """Extract field value from record with fallback."""
        return record.get(field, default)

    def _extract_and_transform_field(
        self,
        record: Dict[str, Any],
        field: str,
        transform_func,
        default: Any = None
    ) -> Any:
        """Extract field value and apply transformation function."""
        value = self._extract_field(record, field, default)
        if value is None or value == "":
            return default
        return transform_func(value)

    def _get_owner_account(self, record: Dict[str, Any]) -> Optional[str]:
        """Get normalized owner account from record (prefers key_alias over api_key)."""
        # Prefer key_alias if available and not null/empty
        key_alias = self._extract_field(record, "key_alias")
        if key_alias and str(key_alias).strip():
            return normalize_component(str(key_alias))

        # Fallback to api_key
        api_key = self._extract_field(record, "api_key")
        if api_key and str(api_key).strip():
            return normalize_component(str(api_key))

        return None

    def _get_resource_type(self, record: Dict[str, Any]) -> Optional[str]:
        """Get resource type based on data source (model or call_type)."""
        field_value = self._extract_field(record, self.resource_type_field)

        if not field_value or str(field_value).strip() == "" or str(field_value) == "*":
            self._track_missing_field_error(record, self.resource_type_field)
            return None

        # For model field, extract model name; for call_type, use directly
        if self.resource_type_field == "model":
            return extract_model_name(str(field_value))
        else:
            return normalize_component(str(field_value))

    def _get_usage_family(self, record: Dict[str, Any]) -> str:
        """Get usage family based on data source (model or call_type)."""
        field_value = self._extract_field(record, self.usage_family_field)

        if not field_value or str(field_value).strip() == "" or str(field_value) == "*":
            return "unknown"

        # For model field, extract model name; for call_type, use directly
        if self.usage_family_field == "model":
            return extract_model_name(str(field_value))
        else:
            return normalize_component(str(field_value))

    def _get_cloud_local_id(self, record: Dict[str, Any]) -> str:
        """Generate cloud local ID from provider and full model name.

        Note: This should be constructed identically for both sources using the full model value,
        regardless of whether the source uses call_type or model for resource-type/usage_family.
        The full model name ensures different model versions are tracked as separate resources.
        """
        # Use the original provider name, not the normalized one
        original_provider = self._extract_field(record, "custom_llm_provider", "unknown")

        # Always use full model name for cloud-local-id, regardless of source
        model_value = self._extract_field(record, "model")
        if model_value and str(model_value).strip() and str(model_value) != "*":
            model = str(model_value)
        else:
            model = "unknown"

        return generate_resource_id(model, original_provider)

    def _get_usage_start_time(self, record: Dict[str, Any]) -> Optional[str]:
        """Get usage start time based on data source.

        Always returns ISO format string for CloudZero API compatibility.
        For SpendLogs, the start_time is already a datetime object from the database.
        For user tables, we parse the date string into a datetime object then convert to string.
        """
        if self.source == "logs":
            # SpendLogs uses start_time field (already a datetime object)
            start_time = self._extract_field(record, "start_time")
            if isinstance(start_time, datetime):
                # Convert datetime object to ISO format string for CloudZero API
                return start_time.isoformat() + 'Z' if start_time.tzinfo is None else start_time.isoformat()
            elif isinstance(start_time, str):
                return start_time
            return None
        else:
            # User tables use date field
            date_value = self._extract_field(record, "date")
            parsed_date = parse_date(date_value)
            if isinstance(parsed_date, datetime):
                return parsed_date.isoformat() + 'Z' if parsed_date.tzinfo is None else parsed_date.isoformat()
            return parsed_date

    def _calculate_total_tokens(self, record: Dict[str, Any]) -> int:
        """Calculate total tokens from prompt and completion tokens."""
        prompt_tokens = self._extract_field(record, "prompt_tokens", 0) or 0
        completion_tokens = self._extract_field(record, "completion_tokens", 0) or 0

        try:
            return int(prompt_tokens) + int(completion_tokens)
        except (ValueError, TypeError):
            return 0

    def _build_resource_tags(self, record: Dict[str, Any], czrn: Optional[str]) -> Dict[str, str]:
        """Build resource tags dictionary from record data."""
        tags = {}

        # Add CZRN as a resource tag if available
        if czrn:
            tags["resource/tag:czrn"] = czrn

        # Add extracted model family tag (always from model field regardless of source)
        model_value = self._extract_field(record, "model")
        if model_value and str(model_value).strip() and str(model_value) != "*":
            extracted_model = extract_model_name(str(model_value))
            tags["resource/tag:model_family"] = extracted_model

        # Add all CBF-mapped fields as resource tags
        for field, mapping in self.cbf_mappings.items():
            if mapping.startswith("resource/tag:"):
                tag_name = mapping
                field_value = self._extract_field(record, field)
                if field_value is not None:
                    tags[tag_name] = str(field_value)

        return tags

    def _track_czrn_error(
        self,
        record: Dict[str, Any],
        service_type: Optional[str],
        owner_account: Optional[str],
        resource_type: Optional[str]
    ):
        """Track CZRN generation errors with specific field information."""
        if not service_type:
            self.error_tracker.add_error(
                "MISSING_PROVIDER", "custom_llm_provider field is empty or null", record, "CZRN"
            )
        if not owner_account:
            self.error_tracker.add_error(
                "MISSING_ACCOUNT", "Neither key_alias nor api_key available", record, "CZRN"
            )
        if not resource_type:
            self.error_tracker.add_error(
                f"MISSING_{self.resource_type_field.upper()}",
                f"{self.resource_type_field} field is empty or null", record, "CZRN"
            )

    def _track_missing_field_error(self, record: Dict[str, Any], field: str):
        """Track missing field errors."""
        self.error_tracker.add_error(
            f"MISSING_{field.upper()}", f"{field} field is empty or null", record, "CZRN"
        )

