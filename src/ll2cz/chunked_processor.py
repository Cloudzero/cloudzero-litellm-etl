# SPDX-FileCopyrightText: Copyright (c), CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Chunked processing for memory-efficient data transformation."""

from typing import Any, Callable, Dict, Iterator, List, Optional

import polars as pl
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .data_processor import DataProcessor


class ChunkedDataProcessor:
    """Process large datasets in chunks to avoid memory issues."""

    def __init__(self, chunk_size: int = 10000, show_progress: bool = True):
        """Initialize chunked processor.

        Args:
            chunk_size: Number of records to process per chunk
            show_progress: Whether to show progress during processing
        """
        self.chunk_size = chunk_size
        self.show_progress = show_progress
        self.console = Console()

    def process_dataframe_chunked(
        self,
        df: pl.DataFrame,
        processor: DataProcessor,
        callback: Optional[Callable[[List[Dict[str, Any]], Dict[str, Any]], None]] = None
    ) -> tuple[int, int, Dict[str, Any]]:
        """Process a DataFrame in chunks, yielding results progressively.

        Args:
            df: Input DataFrame to process
            processor: DataProcessor instance to use
            callback: Optional callback function for each chunk
                     Args: (cbf_records, error_summary)

        Returns:
            Tuple of (total_records, successful_records, overall_error_summary)
        """
        total_records = len(df)
        successful_records = 0

        if self.show_progress:
            progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
                transient=True
            )
            task = progress.add_task(f"Processing {total_records:,} records...", total=total_records)
            progress.start()

        try:
            # Process in chunks
            for chunk_start in range(0, total_records, self.chunk_size):
                chunk_end = min(chunk_start + self.chunk_size, total_records)
                chunk = df.slice(chunk_start, chunk_end - chunk_start)

                # Process the chunk
                czrns, cbf_records, error_summary = processor.process_dataframe(chunk)
                successful_records += len(cbf_records)

                # Call the callback if provided
                if callback:
                    callback(cbf_records, error_summary)

                # Update progress
                if self.show_progress:
                    progress.update(task, completed=chunk_end)

            # Get overall error summary
            overall_error_summary = processor.error_tracker.get_summary()

            return total_records, successful_records, overall_error_summary

        finally:
            if self.show_progress:
                progress.stop()

    def process_dataframe_as_generator(
        self,
        df: pl.DataFrame,
        processor: DataProcessor
    ) -> Iterator[tuple[List[str], List[Dict[str, Any]], Dict[str, Any]]]:
        """Process a DataFrame in chunks, yielding results as a generator.

        This is useful for streaming processing where you want to handle
        each chunk's results immediately without accumulating in memory.

        Args:
            df: Input DataFrame to process
            processor: DataProcessor instance to use

        Yields:
            Tuple of (czrns, cbf_records, error_summary) for each chunk
        """
        total_records = len(df)

        # Process in chunks
        for chunk_start in range(0, total_records, self.chunk_size):
            chunk_end = min(chunk_start + self.chunk_size, total_records)
            chunk = df.slice(chunk_start, chunk_end - chunk_start)

            # Process and yield the chunk results
            yield processor.process_dataframe(chunk)

    def process_with_memory_limit(
        self,
        df: pl.DataFrame,
        processor: DataProcessor,
        memory_limit_mb: int = 1000
    ) -> tuple[List[str], List[Dict[str, Any]], Dict[str, Any]]:
        """Process DataFrame with memory limit, using adaptive chunk sizing.

        Args:
            df: Input DataFrame to process
            processor: DataProcessor instance to use
            memory_limit_mb: Maximum memory to use in MB

        Returns:
            Tuple of (all_czrns, all_cbf_records, error_summary)
        """
        # Estimate memory per record (rough approximation)
        sample_size = min(100, len(df))
        sample = df.head(sample_size)
        _, sample_cbf, _ = processor.process_dataframe(sample)

        if sample_cbf:
            # Estimate bytes per record (assuming ~1KB per CBF record)
            bytes_per_record = 1024  # Conservative estimate
            records_per_mb = (1024 * 1024) / bytes_per_record
            adaptive_chunk_size = int(memory_limit_mb * records_per_mb * 0.5)  # Use 50% for safety

            # Ensure reasonable chunk size
            adaptive_chunk_size = max(1000, min(adaptive_chunk_size, 100000))
        else:
            adaptive_chunk_size = self.chunk_size

        # Process with adaptive chunk size
        all_czrns = []
        all_cbf_records = []

        chunked_processor = ChunkedDataProcessor(
            chunk_size=adaptive_chunk_size,
            show_progress=self.show_progress
        )

        def accumulate_results(cbf_records: List[Dict[str, Any]], error_summary: Dict[str, Any]):
            all_cbf_records.extend(cbf_records)

        _, _, error_summary = chunked_processor.process_dataframe_chunked(
            df, processor, callback=accumulate_results
        )

        # Get all CZRNs from CBF records
        for record in all_cbf_records:
            if 'resource/tag:czrn' in record:
                all_czrns.append(record['resource/tag:czrn'])

        return all_czrns, all_cbf_records, error_summary


def process_large_dataset(
    df: pl.DataFrame,
    source: str = "usertable",
    chunk_size: int = 10000,
    show_progress: bool = True
) -> Iterator[tuple[List[str], List[Dict[str, Any]], Dict[str, Any]]]:
    """Convenience function to process large datasets in chunks.

    Args:
        df: Input DataFrame to process
        source: Data source type ("usertable" or "logs")
        chunk_size: Number of records per chunk
        show_progress: Whether to show progress

    Yields:
        Tuple of (czrns, cbf_records, error_summary) for each chunk
    """
    processor = DataProcessor(source=source)
    chunked_processor = ChunkedDataProcessor(chunk_size=chunk_size, show_progress=show_progress)

    yield from chunked_processor.process_dataframe_as_generator(df, processor)
