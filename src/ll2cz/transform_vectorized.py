# SPDX-FileCopyrightText: Copyright (c), CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Vectorized transformation functions for converting LiteLLM data to CBF format."""

from typing import List, Dict, Any, Tuple
import polars as pl
from datetime import timezone

from .czrn import CZRNGenerator
from .transformations import parse_date, normalize_service, extract_model_name


class VectorizedTransformer:
    """Transformer that uses Polars vectorized operations for better performance."""
    
    def __init__(self, source: str = "usertable"):
        """Initialize with source type."""
        self.source = source
        self.czrn_generator = CZRNGenerator()
    
    def transform_to_cbf(self, data: pl.DataFrame) -> pl.DataFrame:
        """Transform LiteLLM data to CBF format using vectorized operations.
        
        Args:
            data: Input DataFrame with LiteLLM data
            
        Returns:
            DataFrame with CBF-formatted records
        """
        # Step 1: Filter out records with zero successful requests
        filtered_data = data.filter(pl.col('successful_requests') > 0)
        
        if filtered_data.is_empty():
            return pl.DataFrame()
        
        # Step 2: Add computed columns using vectorized operations
        transformed = filtered_data.with_columns([
            # Parse dates
            pl.col('date').map_elements(parse_date, return_dtype=pl.Datetime).alias('parsed_date'),
            
            # Calculate total tokens
            (pl.col('prompt_tokens').cast(pl.Int64) + 
             pl.col('completion_tokens').cast(pl.Int64)).alias('total_tokens'),
            
            # Normalize provider
            pl.col('custom_llm_provider').map_elements(
                normalize_service, return_dtype=pl.Utf8
            ).alias('normalized_provider'),
            
            # Extract model name
            pl.col('model').map_elements(
                extract_model_name, return_dtype=pl.Utf8
            ).alias('extracted_model_name'),
            
            # Generate CZRNs
            pl.struct(pl.all()).map_elements(
                self._generate_czrn_for_row, return_dtype=pl.Utf8
            ).alias('czrn'),
            
            # Prepare key_alias or fallback to api_key
            pl.when(pl.col('key_alias').is_not_null() & (pl.col('key_alias') != ''))
              .then(pl.col('key_alias'))
              .otherwise(pl.col('api_key'))
              .alias('account_id'),
        ])
        
        # Step 3: Filter out records with invalid CZRNs
        valid_czrn_data = transformed.filter(
            pl.col('czrn').is_not_null() & 
            (pl.col('czrn') != '') & 
            (pl.col('czrn') != 'INVALID_CZRN')
        )
        
        if valid_czrn_data.is_empty():
            return pl.DataFrame()
        
        # Step 4: Extract CZRN components
        czrn_components = valid_czrn_data.with_columns([
            pl.col('czrn').map_elements(
                self._extract_czrn_components, return_dtype=pl.Struct
            ).alias('czrn_parts')
        ])
        
        # Step 5: Build CBF records using vectorized operations
        cbf_data = czrn_components.with_columns([
            # Timestamp in ISO format
            pl.col('parsed_date').dt.strftime('%Y-%m-%dT%H:%M:%SZ').alias('timestamp'),
            
            # Build dimensions struct
            pl.struct([
                pl.col('entity_type').cast(pl.Utf8).alias('entity_type'),
                pl.col('entity_id').cast(pl.Utf8).alias('entity_id'),
                pl.col('model').cast(pl.Utf8).alias('model_original'),
                pl.col('model_group').cast(pl.Utf8).alias('model_group'),
                pl.col('custom_llm_provider').cast(pl.Utf8).alias('provider'),
                pl.col('api_key').cast(pl.Utf8).alias('api_key'),
                pl.col('api_requests').cast(pl.Utf8).alias('api_requests'),
                pl.col('successful_requests').cast(pl.Utf8).alias('successful_requests'),
                pl.col('failed_requests').cast(pl.Utf8).alias('failed_requests'),
                pl.col('cache_creation_input_tokens').cast(pl.Utf8).alias('cache_creation_tokens'),
                pl.col('cache_read_input_tokens').cast(pl.Utf8).alias('cache_read_tokens'),
                pl.col('key_name').cast(pl.Utf8).alias('key_name'),
                pl.col('key_alias').cast(pl.Utf8).alias('key_alias'),
                pl.col('user_alias').cast(pl.Utf8).alias('user_alias'),
                pl.col('user_email').cast(pl.Utf8).alias('user_email'),
                pl.col('team_alias').cast(pl.Utf8).alias('team_alias'),
                pl.col('team_id').cast(pl.Utf8).alias('team_id'),
                pl.col('organization_alias').cast(pl.Utf8).alias('organization_alias'),
                pl.col('organization_id').cast(pl.Utf8).alias('organization_id'),
            ]).alias('dimensions')
        ])
        
        # Step 6: Select and rename columns for final CBF format
        final_cbf = cbf_data.select([
            pl.col('timestamp'),
            pl.col('czrn_parts').struct.field('czrn_service').alias('resource/service'),
            pl.col('czrn_parts').struct.field('czrn_region').alias('resource/region'),
            pl.col('czrn_parts').struct.field('czrn_account').alias('resource/account'),
            pl.col('czrn_parts').struct.field('czrn_resource_type').alias('resource/usage_family'),
            pl.col('czrn_parts').struct.field('czrn_resource_id').alias('resource/id'),
            pl.col('czrn').alias('resource/tag:czrn'),
            pl.lit('litellm').alias('resource/tag:czrn_provider'),
            pl.col('extracted_model_name').alias('resource/tag:model'),
            pl.col('normalized_provider').alias('resource/tag:provider'),
            pl.col('total_tokens').cast(pl.Float64).alias('value'),
            pl.lit('count').alias('unit'),
            pl.col('cost').cast(pl.Float64).alias('cost'),
            pl.col('dimensions'),
            pl.col('prompt_tokens').alias('prompt_tokens'),
            pl.col('completion_tokens').alias('completion_tokens'),
        ])
        
        return final_cbf
    
    def _generate_czrn_for_row(self, row_struct: dict) -> str:
        """Generate CZRN for a single row."""
        try:
            return self.czrn_generator.create_from_litellm_data(row_struct)
        except Exception:
            return 'INVALID_CZRN'
    
    def _extract_czrn_components(self, czrn: str) -> dict:
        """Extract CZRN components into a dictionary."""
        try:
            components = self.czrn_generator.extract_components(czrn)
            return {
                'czrn_service': components.get('service-type', 'custom_llm_provider'),
                'czrn_region': components.get('region', 'cross-region'),
                'czrn_account': components.get('owner-account-id', 'unknown'),
                'czrn_resource_type': components.get('resource-type', 'unknown'),
                'czrn_resource_id': components.get('cloud-local-id', 'unknown'),
            }
        except Exception:
            return {
                'czrn_service': 'custom_llm_provider',
                'czrn_region': 'cross-region',
                'czrn_account': 'unknown',
                'czrn_resource_type': 'unknown',
                'czrn_resource_id': 'unknown',
            }
    
    def transform_batch(self, data: pl.DataFrame, batch_size: int = 10000) -> pl.DataFrame:
        """Transform data in batches for memory efficiency.
        
        Args:
            data: Input DataFrame
            batch_size: Number of records per batch
            
        Returns:
            Concatenated CBF DataFrame
        """
        if len(data) <= batch_size:
            return self.transform_to_cbf(data)
        
        # Process in batches
        batches = []
        for i in range(0, len(data), batch_size):
            batch = data.slice(i, min(batch_size, len(data) - i))
            cbf_batch = self.transform_to_cbf(batch)
            if not cbf_batch.is_empty():
                batches.append(cbf_batch)
        
        if not batches:
            return pl.DataFrame()
        
        return pl.concat(batches, how='vertical')