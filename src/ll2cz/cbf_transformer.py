# SPDX-FileCopyrightText: Copyright (c), CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""CloudZero Billing Format (CBF) transformer with database integration."""

from typing import Any, Dict, List, Tuple, Union

import polars as pl
from rich.console import Console

from .cached_database import CachedLiteLLMDatabase
from .chunked_processor import ChunkedDataProcessor
from .data_processor import DataProcessor
from .data_source_strategy import DataSourceFactory
from .database import LiteLLMDatabase


class CBFTransformer:
    """Transform LiteLLM data to CloudZero Billing Format with database integration."""
    
    def __init__(self, database: Union[LiteLLMDatabase, CachedLiteLLMDatabase], timezone: str = 'UTC'):
        """Initialize transformer with database connection.
        
        Args:
            database: LiteLLM database connection
            timezone: Timezone for date operations
        """
        self.database = database
        self.timezone = timezone
        self.console = Console()
    
    def transform(self, limit: int = 10000, source: str = 'usertable') -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Transform data from database to CBF format.
        
        Args:
            limit: Maximum number of records to process
            source: Data source ('usertable' or 'logs')
            
        Returns:
            Tuple of (cbf_records, summary)
        """
        # Load data using strategy pattern
        strategy = DataSourceFactory.create_strategy(source)
        data = strategy.get_data(self.database, date_filter=None, limit=limit)
        
        if data.is_empty():
            return [], {
                'records_transformed': 0,
                'date_range': {'min': None, 'max': None},
                'total_spend': 0.0,
                'total_tokens': 0
            }
        
        # Process data to CBF format
        # Use chunked processing for large datasets
        if len(data) > 50000:
            self.console.print("[dim]Using chunked processing for large dataset...[/dim]")
            processor = DataProcessor(source=source)
            chunked_processor = ChunkedDataProcessor(chunk_size=10000, show_progress=True)
            
            all_cbf_records = []
            def collect_results(cbf_records, error_summary):
                all_cbf_records.extend(cbf_records)
            
            total_records, successful_records, error_summary = chunked_processor.process_dataframe_chunked(
                data, processor, callback=collect_results
            )
            cbf_records = all_cbf_records
        else:
            processor = DataProcessor(source=source)
            _, cbf_records, error_summary = processor.process_dataframe(data)
        
        # Calculate summary
        if cbf_records:
            cbf_df = pl.DataFrame(cbf_records)
            summary = {
                'records_transformed': len(cbf_records),
                'date_range': {
                    'min': cbf_df['time/usage_start'].min(),
                    'max': cbf_df['time/usage_start'].max()
                },
                'total_spend': cbf_df['cost/cost'].sum() if 'cost/cost' in cbf_df.columns else 0.0,
                'total_tokens': cbf_df['usage/amount'].sum() if 'usage/amount' in cbf_df.columns else 0
            }
        else:
            summary = {
                'records_transformed': 0,
                'date_range': {'min': None, 'max': None},
                'total_spend': 0.0,
                'total_tokens': 0
            }
        
        return cbf_records, summary