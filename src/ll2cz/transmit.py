# SPDX-FileCopyrightText: Copyright (c), CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Data transmission module for sending transformed data to CloudZero AnyCost API."""

import json
from typing import Any, Dict, Optional, Union

import polars as pl
from rich.console import Console
from rich.table import Table

from .cached_database import CachedLiteLLMDatabase
from .chunked_processor import ChunkedDataProcessor
from .data_processor import DataProcessor
from .data_source_strategy import DataSourceFactory
from .database import LiteLLMDatabase
from .date_utils import DateParser
from .output import CloudZeroStreamer


class DataTransmitter:
    """Handle data transmission to CloudZero AnyCost API."""

    def __init__(self, database: Union[LiteLLMDatabase, CachedLiteLLMDatabase],
                 cz_api_key: str, cz_connection_id: str, timezone: str = 'UTC'):
        """Initialize transmitter with database connection and CloudZero credentials.

        Args:
            database: LiteLLM database connection (cached or direct)
            cz_api_key: CloudZero API key
            cz_connection_id: CloudZero connection ID
            timezone: Timezone for date handling (default: UTC)
        """
        self.database = database
        self.cz_api_key = cz_api_key
        self.cz_connection_id = cz_connection_id
        self.timezone = timezone
        self.console = Console()
        self.date_parser = DateParser(timezone)

    def transmit(self, mode: str, date_spec: Optional[str] = None,
                 source: str = 'usertable', append: bool = False,
                 test: bool = False, limit: Optional[int] = None) -> Dict[str, Any]:
        """Transmit data to CloudZero AnyCost API.

        Args:
            mode: Transmission mode ('day', 'month', or 'all')
            date_spec: Date specification (DD-MM-YYYY for day, MM-YYYY for month)
            source: Data source ('usertable' or 'logs')
            append: Use 'sum' operation instead of 'replace_hourly'
            test: Test mode - show payloads without transmitting
            limit: Number of records to send or show (in test mode)

        Returns:
            Dictionary with transmission results
        """
        # Validate parameters
        if mode not in ['day', 'month', 'all']:
            raise ValueError("Mode must be 'day', 'month', or 'all'")
        if source not in ['usertable', 'logs']:
            raise ValueError("Source must be 'usertable' or 'logs'")

        # Parse date specification
        date_filter = self.date_parser.parse_date_spec(mode, date_spec)

        # Display loading info
        source_desc = "SpendLogs table" if source == "logs" else "user tables"
        self.console.print(f"[blue]Loading {mode} data from LiteLLM {source_desc}...[/blue]")
        if date_filter:
            self.console.print(f"[dim]Date filter: {date_filter.get('description', 'Unknown filter')}[/dim]")

        # Load data using strategy pattern
        strategy = DataSourceFactory.create_strategy(source)
        if test:
            # In test mode, use specified limit or default to 5 records
            test_limit = limit if limit else 5
            data = strategy.get_data(self.database, date_filter=None, limit=test_limit)
        else:
            data = strategy.get_data(self.database, date_filter, limit)

        if data.is_empty():
            self.console.print("[yellow]No data found for the specified criteria[/yellow]")
            return {'status': 'no_data', 'records': 0}

        self.console.print(f"[blue]Processing {len(data)} records...[/blue]")

        # Process data to CBF format
        # Use chunked processing for large datasets
        if len(data) > 50000:  # Threshold for chunked processing
            self.console.print("[dim]Using chunked processing for large dataset...[/dim]")
            processor = DataProcessor(source=source)
            chunked_processor = ChunkedDataProcessor(chunk_size=10000, show_progress=True)

            all_cbf_records = []
            def collect_results(cbf_records, error_summary):
                all_cbf_records.extend(cbf_records)

            _, _, error_summary = chunked_processor.process_dataframe_chunked(
                data, processor, callback=collect_results
            )
            cbf_data = pl.DataFrame(all_cbf_records)
        else:
            processor = DataProcessor(source=source)
            _, cbf_records, error_summary = processor.process_dataframe(data)
            cbf_data = pl.DataFrame(cbf_records)

        # Determine operation mode
        operation = "sum" if append else "replace_hourly"

        if test:
            return self._display_test_payloads(cbf_data, operation, mode)
        else:
            return self._transmit_data(cbf_data, operation)

    def _display_test_payloads(self, cbf_data: pl.DataFrame, operation: str, mode: str) -> Dict[str, Any]:
        """Display test payloads without transmitting.

        Returns:
            Dictionary with test results
        """
        self.console.print("\n[yellow]TEST MODE - Showing sample payloads[/yellow]")

        # Group by date for batching
        date_groups = cbf_data.group_by('time/usage_start').agg(
            pl.len().alias('record_count')
        ).sort('time/usage_start')

        self.console.print(f"\n[blue]Would send {len(date_groups)} batches:[/blue]")

        # Show summary table
        table = Table(title="Batch Summary")
        table.add_column("Date", style="cyan")
        table.add_column("Records", style="green")

        for row in date_groups.iter_rows(named=True):
            table.add_row(
                row['time/usage_start'].split('T')[0],
                str(row['record_count'])
            )

        self.console.print(table)

        # Show all records across all batches
        if len(date_groups) == 1:
            self.console.print("\n[blue]Sample payload:[/blue]")
        else:
            self.console.print(f"\n[blue]Sample payload (showing all {len(cbf_data)} records across {len(date_groups)} batches):[/blue]")

        all_records = cbf_data.to_dicts()

        sample_payload = {
            "connection_id": "<CZ_CONNECTION_ID>",
            "telemetry_stream": all_records  # Show all records from all batches
        }

        self.console.print(json.dumps(sample_payload, indent=2))

        self.console.print(f"\n[dim]Operation: {operation}[/dim]")
        self.console.print(f"[dim]Mode: {mode}[/dim]")
        self.console.print("\n[dim]💡 Remove --test flag to actually transmit these batches to CloudZero AnyCost API[/dim]")

        return {
            'status': 'test',
            'batches': len(date_groups),
            'total_records': len(cbf_data),
            'operation': operation
        }

    def _transmit_data(self, cbf_data: pl.DataFrame, operation: str) -> Dict[str, Any]:
        """Transmit data to CloudZero AnyCost API.

        Returns:
            Dictionary with transmission results
        """
        self.console.print(f"[blue]Transmitting to CloudZero AnyCost API using operation: '{operation}'[/blue]")

        streamer = CloudZeroStreamer(self.cz_api_key, self.cz_connection_id, self.timezone)
        streamer.send_batched(cbf_data, operation=operation)

        self.console.print(f"[green]✓ Successfully transmitted {len(cbf_data)} records to CloudZero AnyCost API[/green]")

        return {
            'status': 'success',
            'records': len(cbf_data),
            'operation': operation
        }

