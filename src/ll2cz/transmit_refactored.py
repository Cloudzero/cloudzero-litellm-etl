# SPDX-FileCopyrightText: Copyright (c), CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Refactored data transmission module with improved separation of concerns.

This refactoring addresses the following issues:
1. Single Responsibility: Each class now has one clear purpose
2. Testability: All components can be tested in isolation with dependency injection
3. Separation of Concerns: Business logic, I/O, and presentation are clearly separated
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol, Union

import polars as pl

from .cached_database import CachedLiteLLMDatabase
from .chunked_processor import ChunkedDataProcessor
from .data_processor import DataProcessor
from .data_source_strategy import DataSourceFactory, DataSourceStrategy
from .database import LiteLLMDatabase
from .date_utils import DateParser

# ==============================================================================
# DATA MODELS - Pure data structures with validation
# ==============================================================================

@dataclass
class TransmitRequest:
    """Encapsulates all parameters for a transmission request.
    
    This is a pure data class - no business logic, just validation.
    """
    mode: str
    source: str = 'usertable'
    date_spec: Optional[str] = None
    append: bool = False
    test: bool = False
    limit: Optional[int] = None

    def validate(self) -> None:
        """Validate request parameters."""
        if self.mode not in ['day', 'month', 'all']:
            raise ValueError("Mode must be 'day', 'month', or 'all'")
        if self.source not in ['usertable', 'logs']:
            raise ValueError("Source must be 'usertable' or 'logs'")


@dataclass
class TransmitResult:
    """Result of a transmission operation.
    
    Immutable result object that encapsulates all possible outcomes.
    """
    status: str  # 'success', 'no_data', 'test', 'error'
    records: int = 0
    batches: int = 0
    operation: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_successful(self) -> bool:
        """Check if the transmission was successful."""
        return self.status in ('success', 'test')

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for legacy compatibility."""
        result = {
            'status': self.status,
            'records': self.records,
        }
        if self.operation:
            result['operation'] = self.operation
        if self.error:
            result['error'] = self.error
        result.update(self.metadata)
        return result


# ==============================================================================
# BUSINESS LOGIC COMPONENTS - Each with single responsibility
# ==============================================================================

class RequestValidator:
    """Validates transmission requests."""

    VALID_MODES = {'day', 'month', 'all'}
    VALID_SOURCES = {'usertable', 'logs'}

    def validate(self, request: TransmitRequest) -> None:
        """Validate a transmission request.
        
        Raises:
            ValueError: If the request is invalid
        """
        if request.mode not in self.VALID_MODES:
            raise ValueError(f"Mode must be one of {self.VALID_MODES}")
        if request.source not in self.VALID_SOURCES:
            raise ValueError(f"Source must be one of {self.VALID_SOURCES}")
        if request.limit is not None and request.limit <= 0:
            raise ValueError("Limit must be positive")


class DataLoader:
    """Responsible for loading data from the database.
    
    This class only knows how to load data - it doesn't know about
    validation, transformation, or transmission.
    """

    DEFAULT_TEST_LIMIT = 5

    def __init__(self,
                 database: Union[LiteLLMDatabase, CachedLiteLLMDatabase],
                 date_parser: DateParser,
                 source_factory: Optional[Callable[[str], DataSourceStrategy]] = None):
        self.database = database
        self.date_parser = date_parser
        self.source_factory = source_factory or DataSourceFactory.create_strategy

    def load_data(self, request: TransmitRequest) -> pl.DataFrame:
        """Load data based on the request parameters."""
        # Parse date specification
        date_filter = self.date_parser.parse_date_spec(request.mode, request.date_spec)

        # Load data using strategy pattern
        strategy = self.source_factory(request.source)

        # Determine limit
        limit = self._determine_limit(request)

        # In test mode, ignore date filter to ensure we get some data
        if request.test:
            return strategy.get_data(self.database, date_filter=None, limit=limit)
        else:
            return strategy.get_data(self.database, date_filter, limit)

    def _determine_limit(self, request: TransmitRequest) -> Optional[int]:
        """Determine the limit to use for data loading."""
        if request.test and request.limit is None:
            return self.DEFAULT_TEST_LIMIT
        return request.limit

    def get_date_description(self, request: TransmitRequest) -> Optional[str]:
        """Get human-readable date description."""
        date_filter = self.date_parser.parse_date_spec(request.mode, request.date_spec)
        return date_filter.get('description') if date_filter else None


class DataTransformer:
    """Responsible for transforming data to CBF format.
    
    This class only knows about data transformation - it doesn't know
    about loading, validation, or transmission.
    """

    DEFAULT_CHUNK_THRESHOLD = 50000
    DEFAULT_CHUNK_SIZE = 10000

    def __init__(self,
                 chunk_threshold: int = DEFAULT_CHUNK_THRESHOLD,
                 chunk_size: int = DEFAULT_CHUNK_SIZE,
                 processor_factory: Optional[Callable[[str], DataProcessor]] = None):
        self.chunk_threshold = chunk_threshold
        self.chunk_size = chunk_size
        self.processor_factory = processor_factory or (lambda source: DataProcessor(source=source))

    def transform(self, data: pl.DataFrame, source: str) -> pl.DataFrame:
        """Transform data to CBF format."""
        if data.is_empty():
            return data

        processor = self.processor_factory(source)

        # Use chunked processing for large datasets
        if self._should_use_chunking(data):
            return self._transform_chunked(data, processor)
        else:
            return self._transform_direct(data, processor)

    def _should_use_chunking(self, data: pl.DataFrame) -> bool:
        """Determine if chunked processing should be used."""
        return len(data) > self.chunk_threshold

    def _transform_direct(self, data: pl.DataFrame, processor: DataProcessor) -> pl.DataFrame:
        """Direct transformation for smaller datasets."""
        _, cbf_records, _ = processor.process_dataframe(data)
        return pl.DataFrame(cbf_records)

    def _transform_chunked(self, data: pl.DataFrame, processor: DataProcessor) -> pl.DataFrame:
        """Chunked transformation for large datasets."""
        chunked_processor = ChunkedDataProcessor(
            chunk_size=self.chunk_size,
            show_progress=False  # No UI concerns in business logic
        )

        all_cbf_records = []
        def collect_results(cbf_records, error_summary):
            all_cbf_records.extend(cbf_records)

        chunked_processor.process_dataframe_chunked(
            data, processor, callback=collect_results
        )
        return pl.DataFrame(all_cbf_records)


class BatchAnalyzer:
    """Analyzes data for batching information."""

    def analyze_batches(self, data: pl.DataFrame) -> Dict[str, Any]:
        """Analyze data to determine batch information."""
        if data.is_empty() or 'time/usage_start' not in data.columns:
            return {'batches': 0, 'dates': []}

        # Extract date from timestamp and group by date
        data_with_date = data.with_columns(
            pl.col('time/usage_start').str.slice(0, 10).alias('date')
        )

        date_groups = data_with_date.group_by('date').agg(
            pl.len().alias('record_count')
        ).sort('date')

        return {
            'batches': len(date_groups),
            'dates': [
                {
                    'date': row['date'],
                    'count': row['record_count']
                }
                for row in date_groups.iter_rows(named=True)
            ]
        }


# ==============================================================================
# INTERFACES - Protocols and abstractions for loose coupling
# ==============================================================================

class OutputHandler(Protocol):
    """Protocol for output handlers - separates presentation from logic."""

    def show_loading(self, mode: str, source: str, date_desc: Optional[str]) -> None:
        """Show loading information."""
        ...

    def show_no_data(self) -> None:
        """Show no data message."""
        ...

    def show_processing(self, record_count: int) -> None:
        """Show processing information."""
        ...

    def show_test_payload(self, batch_info: Dict[str, Any], payload_data: List[Dict],
                         operation: str, mode: str) -> None:
        """Show test payload information."""
        ...

    def show_transmitting(self, operation: str) -> None:
        """Show transmission start."""
        ...

    def show_success(self, record_count: int) -> None:
        """Show success message."""
        ...

    def show_error(self, error: str) -> None:
        """Show error message."""
        ...


class Transmitter(Protocol):
    """Protocol for data transmitters - abstracts the actual transmission."""

    def transmit(self, data: pl.DataFrame, operation: str) -> None:
        """Transmit data."""
        ...


class ConsoleOutput:
    """Console output implementation."""

    def __init__(self):
        from rich.console import Console
        from rich.table import Table
        self.console = Console()
        self.Table = Table

    def show_loading(self, mode: str, source: str, date_desc: Optional[str]) -> None:
        """Show loading information."""
        source_desc = "SpendLogs table" if source == "logs" else "user tables"
        self.console.print(f"[blue]Loading {mode} data from LiteLLM {source_desc}...[/blue]")
        if date_desc:
            self.console.print(f"[dim]Date filter: {date_desc}[/dim]")

    def show_no_data(self) -> None:
        """Show no data message."""
        self.console.print("[yellow]No data found for the specified criteria[/yellow]")

    def show_processing(self, record_count: int) -> None:
        """Show processing information."""
        self.console.print(f"[blue]Processing {record_count} records...[/blue]")

    def show_test_payload(self, batch_info: Dict[str, Any], payload_data: List[Dict],
                         operation: str, mode: str) -> None:
        """Show test payload information."""
        import json

        self.console.print("\n[yellow]TEST MODE - Showing sample payloads[/yellow]")

        # Show batch summary
        self.console.print(f"\n[blue]Would send {batch_info['batches']} batches:[/blue]")

        if batch_info['dates']:
            # Show summary table
            table = self.Table(title="Batch Summary")
            table.add_column("Date", style="cyan")
            table.add_column("Records", style="green")

            for date_info in batch_info['dates']:
                table.add_row(date_info['date'], str(date_info['count']))

            self.console.print(table)

        # Show sample payload
        sample_payload = {
            "connection_id": "<CZ_CONNECTION_ID>",
            "telemetry_stream": payload_data
        }

        self.console.print("\n[blue]Sample payload:[/blue]")
        self.console.print(json.dumps(sample_payload, indent=2))

        self.console.print(f"\n[dim]Operation: {operation}[/dim]")
        self.console.print(f"[dim]Mode: {mode}[/dim]")
        self.console.print("\n[dim]💡 Remove --test flag to actually transmit these batches to CloudZero AnyCost API[/dim]")

    def show_transmitting(self, operation: str) -> None:
        """Show transmission start."""
        self.console.print(f"[blue]Transmitting to CloudZero AnyCost API using operation: '{operation}'[/blue]")

    def show_success(self, record_count: int) -> None:
        """Show success message."""
        self.console.print(f"[green]✓ Successfully transmitted {record_count} records to CloudZero AnyCost API[/green]")

    def show_error(self, error: str) -> None:
        """Show error message."""
        self.console.print(f"[red]Error: {error}[/red]")


# ==============================================================================
# OUTPUT IMPLEMENTATIONS - Presentation layer, separated from business logic
# ==============================================================================

class NullOutput:
    """Null output implementation for testing - no side effects."""

    def show_loading(self, mode: str, source: str, date_desc: Optional[str]) -> None:
        pass

    def show_no_data(self) -> None:
        pass

    def show_processing(self, record_count: int) -> None:
        pass

    def show_test_payload(self, batch_info: Dict[str, Any], payload_data: List[Dict],
                         operation: str, mode: str) -> None:
        pass

    def show_transmitting(self, operation: str) -> None:
        pass

    def show_success(self, record_count: int) -> None:
        pass

    def show_error(self, error: str) -> None:
        pass


class CollectingOutput:
    """Output handler that collects messages for testing."""

    def __init__(self):
        self.messages: List[str] = []

    def show_loading(self, mode: str, source: str, date_desc: Optional[str]) -> None:
        self.messages.append(f"Loading {mode} from {source}")
        if date_desc:
            self.messages.append(f"Date: {date_desc}")

    def show_no_data(self) -> None:
        self.messages.append("No data found")

    def show_processing(self, record_count: int) -> None:
        self.messages.append(f"Processing {record_count} records")

    def show_test_payload(self, batch_info: Dict[str, Any], payload_data: List[Dict],
                         operation: str, mode: str) -> None:
        self.messages.append(f"Test mode: {batch_info['batches']} batches")

    def show_transmitting(self, operation: str) -> None:
        self.messages.append(f"Transmitting with {operation}")

    def show_success(self, record_count: int) -> None:
        self.messages.append(f"Success: {record_count} records")

    def show_error(self, error: str) -> None:
        self.messages.append(f"Error: {error}")


# ==============================================================================
# TRANSMITTER IMPLEMENTATIONS - Actual data transmission, separated from logic
# ==============================================================================


class CloudZeroTransmitter:
    """CloudZero API transmitter."""

    def __init__(self, api_key: str, connection_id: str, timezone: str = 'UTC'):
        from .output import CloudZeroStreamer
        self.streamer = CloudZeroStreamer(api_key, connection_id, timezone)

    def transmit(self, data: pl.DataFrame, operation: str) -> None:
        """Transmit data to CloudZero."""
        self.streamer.send_batched(data, operation=operation)


class MockTransmitter:
    """Mock transmitter for testing - records transmissions without side effects."""

    def __init__(self):
        self.transmitted_data: List[pl.DataFrame] = []
        self.operations: List[str] = []
        self.call_count: int = 0

    def transmit(self, data: pl.DataFrame, operation: str) -> None:
        """Record transmission for testing."""
        self.transmitted_data.append(data.clone())  # Clone to avoid mutations
        self.operations.append(operation)
        self.call_count += 1

    def reset(self) -> None:
        """Reset the mock state."""
        self.transmitted_data.clear()
        self.operations.clear()
        self.call_count = 0


# ==============================================================================
# ORCHESTRATION - Coordinates components without containing business logic
# ==============================================================================

class TransmitOrchestrator:
    """Orchestrates the transmission process with proper separation of concerns.
    
    This class coordinates the workflow but contains no business logic itself.
    All logic is delegated to the appropriate components.
    """

    def __init__(self,
                 validator: RequestValidator,
                 data_loader: DataLoader,
                 data_transformer: DataTransformer,
                 batch_analyzer: BatchAnalyzer,
                 transmitter: Transmitter,
                 output: OutputHandler):
        self.validator = validator
        self.data_loader = data_loader
        self.data_transformer = data_transformer
        self.batch_analyzer = batch_analyzer
        self.transmitter = transmitter
        self.output = output

    def execute(self, request: TransmitRequest) -> TransmitResult:
        """Execute a transmission request.
        
        This method coordinates the workflow:
        1. Validation
        2. Data loading
        3. Data transformation
        4. Test mode or transmission
        5. Result reporting
        """
        try:
            # Step 1: Validate request
            self.validator.validate(request)

            # Step 2: Show loading info and load data
            date_desc = self.data_loader.get_date_description(request)
            self.output.show_loading(request.mode, request.source, date_desc)

            data = self.data_loader.load_data(request)

            if data.is_empty():
                self.output.show_no_data()
                return TransmitResult(status='no_data')

            # Step 3: Transform data
            self.output.show_processing(len(data))
            cbf_data = self.data_transformer.transform(data, request.source)

            # Step 4: Determine operation
            operation = self._determine_operation(request)

            # Step 5: Execute based on mode
            if request.test:
                return self._handle_test_mode(cbf_data, operation, request)
            else:
                return self._handle_production_mode(cbf_data, operation)

        except Exception as e:
            return self._handle_error(e)

    def _determine_operation(self, request: TransmitRequest) -> str:
        """Determine the operation type based on request."""
        return "sum" if request.append else "replace_hourly"

    def _handle_test_mode(self, data: pl.DataFrame, operation: str,
                          request: TransmitRequest) -> TransmitResult:
        """Handle test mode execution."""
        # Analyze batches
        batch_info = self.batch_analyzer.analyze_batches(data)

        # Show test payload
        payload_data = data.to_dicts()
        self.output.show_test_payload(batch_info, payload_data, operation, request.mode)

        return TransmitResult(
            status='test',
            records=len(data),
            batches=batch_info['batches'],
            operation=operation,
            metadata={'batch_info': batch_info}
        )

    def _handle_production_mode(self, data: pl.DataFrame, operation: str) -> TransmitResult:
        """Handle production mode execution."""
        self.output.show_transmitting(operation)
        self.transmitter.transmit(data, operation)
        self.output.show_success(len(data))

        return TransmitResult(
            status='success',
            records=len(data),
            operation=operation
        )

    def _handle_error(self, error: Exception) -> TransmitResult:
        """Handle errors during execution."""
        error_msg = str(error)
        self.output.show_error(error_msg)
        return TransmitResult(
            status='error',
            error=error_msg
        )


# ==============================================================================
# MAIN API - Facade that provides backward compatibility
# ==============================================================================

class DataTransmitterV2:
    """Refactored data transmitter with better separation of concerns.
    
    This is the main entry point that maintains backward compatibility
    while using the new component-based architecture internally.
    """

    def __init__(self,
                 database: Union[LiteLLMDatabase, CachedLiteLLMDatabase],
                 cz_api_key: str,
                 cz_connection_id: str,
                 timezone: str = 'UTC',
                 output: Optional[OutputHandler] = None,
                 transmitter: Optional[Transmitter] = None,
                 # Advanced customization options
                 validator: Optional[RequestValidator] = None,
                 data_transformer: Optional[DataTransformer] = None,
                 batch_analyzer: Optional[BatchAnalyzer] = None):
        """Initialize with dependency injection for better testability.
        
        Args:
            database: Database connection
            cz_api_key: CloudZero API key
            cz_connection_id: CloudZero connection ID
            timezone: Timezone for date operations
            output: Optional custom output handler
            transmitter: Optional custom transmitter
            validator: Optional custom validator
            data_transformer: Optional custom transformer
            batch_analyzer: Optional custom batch analyzer
        """
        # Core dependencies
        self.database = database
        self.timezone = timezone

        # Create components with defaults
        date_parser = DateParser(timezone)
        self.validator = validator or RequestValidator()
        self.data_loader = DataLoader(database, date_parser)
        self.data_transformer = data_transformer or DataTransformer()
        self.batch_analyzer = batch_analyzer or BatchAnalyzer()

        # Use provided or create default implementations
        self.output = output or ConsoleOutput()
        self.transmitter = transmitter or CloudZeroTransmitter(
            cz_api_key, cz_connection_id, timezone
        )

        # Create orchestrator
        self.orchestrator = TransmitOrchestrator(
            self.validator,
            self.data_loader,
            self.data_transformer,
            self.batch_analyzer,
            self.transmitter,
            self.output
        )

    def transmit(self, mode: str, date_spec: Optional[str] = None,
                 source: str = 'usertable', append: bool = False,
                 test: bool = False, limit: Optional[int] = None) -> Dict[str, Any]:
        """Transmit data to CloudZero AnyCost API.
        
        This method maintains the original API for backward compatibility.
        """
        # Create request
        request = TransmitRequest(
            mode=mode,
            source=source,
            date_spec=date_spec,
            append=append,
            test=test,
            limit=limit
        )

        # Execute
        result = self.orchestrator.execute(request)

        # Convert to legacy format for compatibility
        return result.to_dict()


# Alias for backward compatibility
DataTransmitter = DataTransmitterV2
