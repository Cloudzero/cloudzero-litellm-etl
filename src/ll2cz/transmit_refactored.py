# SPDX-FileCopyrightText: Copyright (c), CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Refactored transmit command functionality broken into smaller, focused functions."""

from typing import Optional, Tuple

import polars as pl
import typer
from rich.console import Console

from .cached_database import CachedLiteLLMDatabase
from .config import Config
from .data_processor import DataProcessor
from .data_source_strategy import DataSourceFactory
from .database import LiteLLMDatabase
from .date_utils import DateParser
from .output import CloudZeroStreamer

console = Console()


class TransmitCommand:
    """Encapsulates the transmit command functionality."""
    
    def __init__(self, config: Config):
        """Initialize with configuration."""
        self.config = config
        self.console = console
    
    def execute(self, mode: str, date_spec: Optional[str], db_connection: Optional[str],
                cz_api_key: Optional[str], cz_connection_id: Optional[str],
                append: bool, timezone: Optional[str], test: bool,
                limit: Optional[int], disable_cache: bool, source: str) -> None:
        """Execute the transmit command with all parameters."""
        try:
            # Step 1: Validate parameters
            self._validate_parameters(mode, source)
            
            # Step 2: Load configuration
            db_connection, cz_api_key, cz_connection_id = self._load_configuration(
                db_connection, cz_api_key, cz_connection_id
            )
            
            # Step 3: Setup database connection
            database = self._setup_database_connection(db_connection, disable_cache)
            
            # Step 4: Parse date specification
            date_parser = DateParser(timezone or 'UTC')
            date_filter = date_parser.parse_date_spec(mode, date_spec)
            
            # Step 5: Display operation info
            self._display_operation_info(mode, source, date_filter)
            
            # Step 6: Load and process data
            cbf_data = self._load_and_process_data(
                database, source, date_filter, limit, test
            )
            
            if cbf_data.is_empty():
                self.console.print("[yellow]No data found for the specified criteria[/yellow]")
                return
            
            # Step 7: Transmit or test
            operation = "sum" if append else "replace_hourly"
            
            if test:
                self._run_test_mode(cbf_data, operation, mode)
            else:
                self._transmit_data(cbf_data, operation, cz_api_key, cz_connection_id, timezone)
                
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)
    
    def _validate_parameters(self, mode: str, source: str) -> None:
        """Validate command parameters."""
        if mode not in ['day', 'month', 'all']:
            raise ValueError("Mode must be 'day', 'month', or 'all'")
            
        if source not in ['usertable', 'logs']:
            raise ValueError("Source must be either 'usertable' or 'logs'")
    
    def _load_configuration(self, db_connection: Optional[str],
                          cz_api_key: Optional[str],
                          cz_connection_id: Optional[str]) -> Tuple[str, str, str]:
        """Load and validate configuration."""
        # Database connection
        db_connection = self.config.get_database_connection(db_connection)
        if not db_connection:
            self.console.print("[red]Error: --input (database connection) is required[/red]")
            self.console.print("[blue]You can set it via CLI argument or in ~/.ll2cz/config.yml[/blue]")
            self.console.print("[blue]Run 'll2cz config-example' to create a sample config file[/blue]")
            raise typer.Exit(1)
        
        # CloudZero API credentials
        cz_api_key = self.config.get_cloudzero_api_key(cz_api_key)
        if not cz_api_key:
            self.console.print("[red]Error: --cz-api-key (CloudZero API key) is required[/red]")
            self.console.print("[blue]You can set it via CLI argument or in ~/.ll2cz/config.yml[/blue]")
            self.console.print("[blue]Run 'll2cz config-example' to create a sample config file[/blue]")
            raise typer.Exit(1)
            
        cz_connection_id = self.config.get_cloudzero_connection_id(cz_connection_id)
        if not cz_connection_id:
            self.console.print("[red]Error: --cz-connection-id (CloudZero connection ID) is required[/red]")
            self.console.print("[blue]You can set it via CLI argument or in ~/.ll2cz/config.yml[/blue]")
            self.console.print("[blue]Run 'll2cz config-example' to create a sample config file[/blue]")
            raise typer.Exit(1)
            
        return db_connection, cz_api_key, cz_connection_id
    
    def _setup_database_connection(self, db_connection: str, disable_cache: bool) -> LiteLLMDatabase:
        """Setup database connection with or without cache."""
        if disable_cache:
            database = LiteLLMDatabase(db_connection)
            self.console.print("[dim]Cache disabled - using direct database connection[/dim]")
        else:
            database = CachedLiteLLMDatabase(db_connection)
            if database.is_offline_mode():
                self.console.print("[yellow]⚠️  Operating in offline mode - using cached data[/yellow]")
                
        return database
    
    def _display_operation_info(self, mode: str, source: str, date_filter: Optional[dict]) -> None:
        """Display information about the operation."""
        source_desc = "SpendLogs table" if source == "logs" else "user tables"
        self.console.print(f"[blue]Loading {mode} data from LiteLLM {source_desc}...[/blue]")
        
        if date_filter:
            self.console.print(f"[dim]Date filter: {date_filter.get('description', 'Unknown filter')}[/dim]")
    
    def _load_and_process_data(self, database: LiteLLMDatabase, source: str,
                               date_filter: Optional[dict], limit: Optional[int],
                               test: bool) -> pl.DataFrame:
        """Load data from database and process it to CBF format."""
        # Use strategy pattern to load data
        strategy = DataSourceFactory.create_strategy(source)
        
        if test:
            # In test mode, always load just 5 records
            data = strategy.get_data(database, date_filter=None, limit=5)
        else:
            data = strategy.get_data(database, date_filter, limit)
        
        if data.is_empty():
            return pl.DataFrame()
        
        self.console.print(f"[blue]Processing {len(data)} records...[/blue]")
        
        # Process data to CBF format
        processor = DataProcessor(source=source)
        _, cbf_records, error_summary = processor.process_dataframe(data)
        
        # Convert to DataFrame
        return pl.DataFrame(cbf_records)
    
    def _run_test_mode(self, cbf_data: pl.DataFrame, operation: str, mode: str) -> None:
        """Run in test mode - display sample payloads without transmitting."""
        from .cli import _display_enhanced_test_payloads
        _display_enhanced_test_payloads(cbf_data, operation, mode)
    
    def _transmit_data(self, cbf_data: pl.DataFrame, operation: str,
                      cz_api_key: str, cz_connection_id: str,
                      timezone: Optional[str]) -> None:
        """Transmit data to CloudZero AnyCost API."""
        self.console.print(f"[blue]Transmitting to CloudZero AnyCost API using operation: '{operation}'[/blue]")
        
        streamer = CloudZeroStreamer(cz_api_key, cz_connection_id, timezone)
        streamer.send_batched(cbf_data, operation=operation)
        
        self.console.print(f"[green]✓ Successfully transmitted {len(cbf_data)} records to CloudZero AnyCost API[/green]")


def create_transmit_command(mode: str, date_spec: Optional[str], db_connection: Optional[str],
                          cz_api_key: Optional[str], cz_connection_id: Optional[str],
                          append: bool, timezone: Optional[str], test: bool,
                          limit: Optional[int], disable_cache: bool, source: str) -> None:
    """Factory function to create and execute transmit command."""
    config = Config()
    command = TransmitCommand(config)
    command.execute(
        mode=mode,
        date_spec=date_spec,
        db_connection=db_connection,
        cz_api_key=cz_api_key,
        cz_connection_id=cz_connection_id,
        append=append,
        timezone=timezone,
        test=test,
        limit=limit,
        disable_cache=disable_cache,
        source=source
    )