# SPDX-FileCopyrightText: Copyright (c), CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Builder pattern for constructing CloudZero Billing Format (CBF) records."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class CBFRecord:
    """Represents a CloudZero Billing Format record."""
    timestamp: str
    value: float
    unit: str
    cost: float
    resource: Dict[str, Any] = field(default_factory=dict)
    dimensions: Dict[str, str] = field(default_factory=dict)

    # Additional fields for tracking
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for API submission."""
        record = {
            'timestamp': self.timestamp,
            'value': self.value,
            'unit': self.unit,
            'cost': self.cost,
            'dimensions': self.dimensions
        }

        # Add resource fields
        for key, value in self.resource.items():
            record[f'resource/{key}'] = value

        # Add token fields if present
        if self.prompt_tokens is not None:
            record['prompt_tokens'] = self.prompt_tokens
        if self.completion_tokens is not None:
            record['completion_tokens'] = self.completion_tokens

        return record


class CBFBuilder:
    """Builder for constructing CBF records with fluent interface."""

    def __init__(self):
        """Initialize a new CBF builder."""
        self._reset()

    def _reset(self):
        """Reset builder to initial state."""
        self._timestamp = None
        self._value = 0.0
        self._unit = 'count'
        self._cost = 0.0
        self._resource = {}
        self._dimensions = {}
        self._prompt_tokens = None
        self._completion_tokens = None

    def with_timestamp(self, timestamp: datetime) -> 'CBFBuilder':
        """Set timestamp for the record.

        Args:
            timestamp: Datetime object (will be converted to UTC ISO format)
        """
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        self._timestamp = timestamp.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        return self

    def with_usage(self, value: float, unit: str = 'count') -> 'CBFBuilder':
        """Set usage value and unit.

        Args:
            value: Usage amount
            unit: Unit of measurement (default: 'count')
        """
        self._value = float(value)
        self._unit = unit
        return self

    def with_cost(self, cost: float) -> 'CBFBuilder':
        """Set cost for the record.

        Args:
            cost: Cost in USD
        """
        self._cost = float(cost)
        return self

    def with_resource(self, **kwargs) -> 'CBFBuilder':
        """Set resource attributes.

        Args:
            **kwargs: Resource attributes (e.g., service='custom_llm_provider')
        """
        self._resource.update(kwargs)
        return self

    def with_resource_tags(self, tags: Dict[str, str]) -> 'CBFBuilder':
        """Add resource tags.

        Args:
            tags: Dictionary of tag key-value pairs
        """
        for key, value in tags.items():
            if value is not None:
                self._resource[f'tag:{key}'] = value
        return self

    def with_czrn_components(self, czrn: str, components: Dict[str, str]) -> 'CBFBuilder':
        """Set CZRN and its components as resource attributes.

        Args:
            czrn: Full CZRN string
            components: CZRN components dictionary
        """
        self._resource['tag:czrn'] = czrn
        self._resource['tag:czrn_provider'] = 'litellm'

        # Map CZRN components to CBF fields
        if 'service-type' in components:
            self._resource['service'] = components['service-type']
        if 'region' in components:
            self._resource['region'] = components['region']
        if 'owner-account-id' in components:
            self._resource['account'] = components['owner-account-id']
        if 'resource-type' in components:
            self._resource['usage_family'] = components['resource-type']
        if 'cloud-local-id' in components:
            self._resource['id'] = components['cloud-local-id']

        return self

    def with_dimensions(self, **kwargs) -> 'CBFBuilder':
        """Set dimensions for the record.

        Args:
            **kwargs: Dimension key-value pairs
        """
        # Convert all values to strings as required by CBF
        for key, value in kwargs.items():
            self._dimensions[key] = str(value) if value is not None else ''
        return self

    def with_tokens(self, prompt_tokens: int, completion_tokens: int) -> 'CBFBuilder':
        """Set token counts.

        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
        """
        self._prompt_tokens = prompt_tokens
        self._completion_tokens = completion_tokens
        # Also set total tokens as value if not already set
        if self._value == 0.0:
            self._value = float(prompt_tokens + completion_tokens)
        return self

    def build(self) -> CBFRecord:
        """Build and return the CBF record.

        Returns:
            CBFRecord instance

        Raises:
            ValueError: If required fields are missing
        """
        if not self._timestamp:
            raise ValueError("Timestamp is required for CBF record")

        record = CBFRecord(
            timestamp=self._timestamp,
            value=self._value,
            unit=self._unit,
            cost=self._cost,
            resource=self._resource.copy(),
            dimensions=self._dimensions.copy(),
            prompt_tokens=self._prompt_tokens,
            completion_tokens=self._completion_tokens
        )

        # Reset builder for next use
        self._reset()

        return record

    @classmethod
    def from_litellm_row(cls, row: Dict[str, Any], czrn: str, czrn_components: Dict[str, str]) -> CBFRecord:
        """Convenience method to build CBF record from LiteLLM row data.

        Args:
            row: LiteLLM data row
            czrn: Generated CZRN string
            czrn_components: Extracted CZRN components

        Returns:
            CBFRecord instance
        """
        from .transformations import extract_model_name, normalize_service, parse_date

        builder = cls()

        # Parse and set timestamp
        usage_date = parse_date(row.get('date'))
        if usage_date:
            builder.with_timestamp(usage_date)

        # Set usage and cost
        prompt_tokens = int(row.get('prompt_tokens', 0))
        completion_tokens = int(row.get('completion_tokens', 0))
        builder.with_tokens(prompt_tokens, completion_tokens)
        builder.with_cost(float(row.get('cost', 0.0)))

        # Set CZRN components
        builder.with_czrn_components(czrn, czrn_components)

        # Add resource tags
        model = str(row.get('model', ''))
        provider = str(row.get('custom_llm_provider', ''))
        builder.with_resource_tags({
            'model': extract_model_name(model),
            'provider': normalize_service(provider)
        })

        # Set dimensions
        builder.with_dimensions(
            entity_type=row.get('entity_type', ''),
            entity_id=row.get('entity_id', ''),
            model_original=model,
            model_group=row.get('model_group', ''),
            provider=provider,
            api_key=row.get('api_key', ''),
            api_requests=row.get('api_requests', 0),
            successful_requests=row.get('successful_requests', 0),
            failed_requests=row.get('failed_requests', 0),
            cache_creation_tokens=row.get('cache_creation_input_tokens', 0),
            cache_read_tokens=row.get('cache_read_input_tokens', 0),
            key_name=row.get('key_name', ''),
            key_alias=row.get('key_alias', ''),
            user_alias=row.get('user_alias', ''),
            user_email=row.get('user_email', ''),
            team_alias=row.get('team_alias', ''),
            team_id=row.get('team_id', ''),
            organization_alias=row.get('organization_alias', ''),
            organization_id=row.get('organization_id', '')
        )

        return builder.build()
