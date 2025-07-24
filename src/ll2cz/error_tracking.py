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
# CHANGELOG: 2025-01-24 - Initial error tracking system for consolidated CZRN/CBF error reporting (erik.peterson)

"""Consolidated error tracking system for CZRN and CBF generation errors."""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List

import polars as pl
from rich.box import SIMPLE
from rich.console import Console
from rich.table import Table

from .transformations import (
    CBF_FIELD_MAPPINGS,
    CZRN_FIELD_MAPPINGS,
    extract_model_name,
    normalize_component,
    normalize_provider,
    parse_date,
)


@dataclass
class ErrorRecord:
    """Individual error record with context."""
    error_type: str
    error_message: str
    source_data: Dict[str, Any]
    operation: str  # 'CZRN' or 'CBF'
    field_name: str = None  # Specific field that caused the error


@dataclass
class SourceFieldAnalysis:
    """Analysis of source data fields and their mappings."""
    field_name: str
    unique_count: int
    null_count: int
    empty_count: int
    total_count: int
    sample_values: List[Any] = field(default_factory=list)
    czrn_mapping: str = None  # Which CZRN component this maps to
    cbf_mapping: str = None   # Which CBF field this maps to


class ConsolidatedErrorTracker:
    """Consolidated error tracking for CZRN and CBF generation operations."""

    def __init__(self):
        """Initialize error tracker."""
        self.errors: List[ErrorRecord] = []
        self.successful_operations = 0
        self.total_operations = 0
        self.console = Console()

    def add_error(self, error_type: str, error_message: str, source_data: Dict[str, Any],
                  operation: str, field_name: str = None) -> None:
        """Add an error to the tracking system."""
        self.errors.append(ErrorRecord(
            error_type=error_type,
            error_message=error_message,
            source_data=source_data.copy(),
            operation=operation,
            field_name=field_name
        ))

    def add_success(self) -> None:
        """Record a successful operation."""
        self.successful_operations += 1

    def increment_total(self) -> None:
        """Increment total operations counter."""
        self.total_operations += 1

    def analyze_source_fields(self, data: pl.DataFrame) -> Dict[str, SourceFieldAnalysis]:
        """Analyze source data fields and their mappings to CZRN/CBF components."""
        field_analysis = {}

        # Use centralized field mappings from transformations module
        czrn_mappings = CZRN_FIELD_MAPPINGS
        cbf_mappings = CBF_FIELD_MAPPINGS

        for column in data.columns:
            series = data[column]

            # Calculate statistics
            unique_count = series.n_unique()
            null_count = series.null_count()
            total_count = len(series)

            # Count empty strings for string columns
            empty_count = 0
            if series.dtype in [pl.String, pl.Utf8]:
                empty_count = len(series.filter(series == ""))

            # Get sample values (up to 10)
            sample_values = []
            if not series.is_empty():
                # Get unique values, limited to 10
                unique_values = series.unique().limit(10).to_list()
                sample_values = [v for v in unique_values if v is not None]

            field_analysis[column] = SourceFieldAnalysis(
                field_name=column,
                unique_count=unique_count,
                null_count=null_count,
                empty_count=empty_count,
                total_count=total_count,
                sample_values=sample_values,
                czrn_mapping=czrn_mappings.get(column),
                cbf_mapping=cbf_mappings.get(column)
            )

        return field_analysis

    def get_error_summary(self) -> Dict[str, Any]:
        """Get comprehensive error summary."""
        error_groups = defaultdict(list)
        error_types = defaultdict(int)
        error_operations = defaultdict(int)
        error_fields = defaultdict(int)

        for error in self.errors:
            # Group by error message for detailed analysis
            error_groups[error.error_message].append(error)

            # Count by error type
            error_types[error.error_type] += 1

            # Count by operation type
            error_operations[error.operation] += 1

            # Count by field if specified
            if error.field_name:
                error_fields[error.field_name] += 1

        return {
            'total_errors': len(self.errors),
            'successful_operations': self.successful_operations,
            'total_operations': self.total_operations,
            'error_rate': len(self.errors) / max(self.total_operations, 1),
            'error_groups': dict(error_groups),
            'error_types': dict(error_types),
            'error_operations': dict(error_operations),
            'error_fields': dict(error_fields)
        }

    def print_source_field_analysis(self, field_analysis: Dict[str, SourceFieldAnalysis]) -> None:
        """Print comprehensive source field analysis with mappings."""
        self.console.print("\n[bold blue]📊 Source Data Field Analysis & CZRN/CBF Mappings[/bold blue]")

        # Create comprehensive table
        field_table = Table(show_header=True, header_style="bold cyan", box=SIMPLE, padding=(0, 1))
        field_table.add_column("Field Name", style="bold blue", no_wrap=False)
        field_table.add_column("Unique", justify="right", style="green", no_wrap=False)
        field_table.add_column("Null", justify="right", style="red", no_wrap=False)
        field_table.add_column("Empty", justify="right", style="yellow", no_wrap=False)
        field_table.add_column("CZRN Mapping", style="bold magenta", no_wrap=False)  # CZRN color
        field_table.add_column("CBF Mapping", style="bold bright_blue", no_wrap=False)  # CBF color
        field_table.add_column("Sample Source Values", style="dim", no_wrap=False)
        field_table.add_column("Sample Mapped Values", style="bold white", no_wrap=False)

        # Sort fields: mapped fields first (both CZRN+CBF, then CZRN only, then CBF only), then unmapped
        def sort_key(item):
            field_name, analysis = item
            has_czrn = analysis.czrn_mapping is not None
            has_cbf = analysis.cbf_mapping is not None

            if has_czrn and has_cbf:
                return (0, field_name)  # Both mappings - highest priority
            elif has_czrn:
                return (1, field_name)  # CZRN only - second priority
            elif has_cbf:
                return (2, field_name)  # CBF only - third priority
            else:
                return (3, field_name)  # No mapping - lowest priority

        sorted_fields = sorted(field_analysis.items(), key=sort_key)

        for field_name, analysis in sorted_fields:
            # Format sample source values
            sample_source_str = ""
            if analysis.sample_values:
                # Show up to 3 sample values
                samples = analysis.sample_values[:3]
                sample_source_str = ", ".join([f"'{v}'" if isinstance(v, str) else str(v) for v in samples])
                if len(analysis.sample_values) > 3:
                    sample_source_str += f" (+{len(analysis.sample_values) - 3} more)"

            # Generate sample mapped values by applying transformations
            sample_mapped_str = "[dim]no mapping[/dim]"
            if analysis.sample_values:
                mapped_samples = []
                samples_to_transform = analysis.sample_values[:3]

                # Apply appropriate transformation based on field mapping
                for sample_value in samples_to_transform:
                    try:
                        if field_name == 'model':
                            transformed = extract_model_name(str(sample_value))
                            mapped_samples.append(f"'{transformed}'")
                        elif field_name == 'custom_llm_provider':
                            transformed = normalize_provider(str(sample_value))
                            mapped_samples.append(f"'{transformed}'")
                        elif field_name == 'entity_id':
                            transformed = normalize_component(str(sample_value))
                            mapped_samples.append(f"'{transformed}'")
                        elif field_name == 'date':
                            try:
                                transformed = parse_date(str(sample_value))
                                if transformed:
                                    mapped_samples.append(f"'{transformed.strftime('%Y-%m-%d %H:%M:%S UTC')}'")
                                else:
                                    # Show that it would be parsed as a date (even if parse_date fails)
                                    mapped_samples.append(f"'{sample_value} 00:00:00 UTC'")
                            except Exception:
                                mapped_samples.append(f"'{sample_value} 00:00:00 UTC'")
                        elif field_name in ['spend', 'prompt_tokens', 'completion_tokens']:
                            # These are used directly without transformation
                            mapped_samples.append(str(sample_value))
                        else:
                            # Other fields used directly (tags, etc.)
                            mapped_samples.append(f"'{sample_value}'" if isinstance(sample_value, str) else str(sample_value))
                    except Exception:
                        mapped_samples.append("'error'")

                if mapped_samples:
                    sample_mapped_str = ", ".join(mapped_samples)
                    if len(analysis.sample_values) > 3:
                        sample_mapped_str += f" (+{len(analysis.sample_values) - 3} more)"

            # Color-code field names based on mapping relationships
            has_czrn = analysis.czrn_mapping is not None
            has_cbf = analysis.cbf_mapping is not None

            if has_czrn and has_cbf:
                # Both CZRN and CBF mapping - green
                field_display = f"[bold green]{field_name}[/bold green]"
            elif has_czrn:
                # CZRN mapping only - magenta (matches CZRN column color)
                field_display = f"[bold magenta]{field_name}[/bold magenta]"
            elif has_cbf:
                # CBF mapping only - bright blue (matches CBF column color)
                field_display = f"[bold bright_blue]{field_name}[/bold bright_blue]"
            else:
                # No mapping - dim white for better distinction
                field_display = f"[dim white]{field_name}[/dim white]"

            # Override with red for problematic critical fields
            if analysis.null_count > 0 or analysis.empty_count > 0:
                if field_name in ['model', 'entity_id', 'custom_llm_provider']:
                    field_display = f"[bold red]{field_name}[/bold red]"

            field_table.add_row(
                field_display,
                f"{analysis.unique_count:,}",
                f"{analysis.null_count:,}" if analysis.null_count > 0 else "0",
                f"{analysis.empty_count:,}" if analysis.empty_count > 0 else "0",
                analysis.czrn_mapping or "[dim]not mapped[/dim]",
                analysis.cbf_mapping or "[dim]not mapped[/dim]",
                sample_source_str,
                sample_mapped_str
            )

        self.console.print(field_table)

        # Color legend
        self.console.print("\n[bold cyan]🎨 Field Color Legend:[/bold cyan]")
        self.console.print("  [bold green]Green[/bold green] = Mapped to both CZRN and CBF")
        self.console.print("  [bold magenta]Magenta[/bold magenta] = Mapped to CZRN only")
        self.console.print("  [bold bright_blue]Bright Blue[/bold bright_blue] = Mapped to CBF only")
        self.console.print("  [dim white]Dim White[/dim white] = Not mapped to CZRN or CBF")
        self.console.print("  [bold red]Red[/bold red] = Critical field with data quality issues")

        # Enhanced summary of mapping coverage
        both_mapped = sum(1 for a in field_analysis.values() if a.czrn_mapping and a.cbf_mapping)
        czrn_only = sum(1 for a in field_analysis.values() if a.czrn_mapping and not a.cbf_mapping)
        cbf_only = sum(1 for a in field_analysis.values() if not a.czrn_mapping and a.cbf_mapping)
        unmapped = sum(1 for a in field_analysis.values() if not a.czrn_mapping and not a.cbf_mapping)
        total_fields = len(field_analysis)

        self.console.print("\n[dim]📈 Mapping Coverage Summary:[/dim]")
        self.console.print(f"  [bold green]Both CZRN & CBF:[/bold green] {both_mapped} fields")
        self.console.print(f"  [bold magenta]CZRN only:[/bold magenta] {czrn_only} fields")
        self.console.print(f"  [bold bright_blue]CBF only:[/bold bright_blue] {cbf_only} fields")
        self.console.print(f"  [dim white]Unmapped:[/dim white] {unmapped} fields")
        self.console.print(f"  [cyan]Total fields:[/cyan] {total_fields}")

        # Ensure all CZRN and CBF fields are accounted for
        missing_czrn = {'provider', 'service-type', 'region', 'owner-account-id', 'resource-type', 'cloud-local-id'}
        missing_cbf = {'time/usage_start', 'cost/cost', 'usage/amount', 'usage/units', 'resource/id',
                      'resource/service', 'resource/account', 'resource/usage_family', 'lineitem/type'}

        # Check which CZRN components are covered
        czrn_components_covered = set()
        for analysis in field_analysis.values():
            if analysis.czrn_mapping:
                if 'service-type' in analysis.czrn_mapping:
                    czrn_components_covered.add('service-type')
                if 'owner-account-id' in analysis.czrn_mapping:
                    czrn_components_covered.add('owner-account-id')
                if 'resource-type' in analysis.czrn_mapping:
                    czrn_components_covered.add('resource-type')

        # Provider, region, and cloud-local-id are derived/constant
        czrn_components_covered.update(['provider', 'region', 'cloud-local-id'])
        missing_czrn -= czrn_components_covered

        # Check which CBF fields are covered
        cbf_fields_covered = set()
        for analysis in field_analysis.values():
            if analysis.cbf_mapping:
                if 'time/usage_start' in analysis.cbf_mapping:
                    cbf_fields_covered.add('time/usage_start')
                if 'cost/cost' in analysis.cbf_mapping:
                    cbf_fields_covered.add('cost/cost')
                if 'usage/amount' in analysis.cbf_mapping:
                    cbf_fields_covered.add('usage/amount')
                if 'resource/service' in analysis.cbf_mapping:
                    cbf_fields_covered.add('resource/service')
                if 'resource/account' in analysis.cbf_mapping:
                    cbf_fields_covered.add('resource/account')
                if 'resource/usage_family' in analysis.cbf_mapping:
                    cbf_fields_covered.add('resource/usage_family')

        # Constants and derived fields
        cbf_fields_covered.update(['usage/units', 'resource/id', 'lineitem/type'])
        missing_cbf -= cbf_fields_covered

        if missing_czrn or missing_cbf:
            self.console.print("\n[bold yellow]⚠️  Field Coverage Gaps:[/bold yellow]")
            if missing_czrn:
                self.console.print(f"  [magenta]Missing CZRN components:[/magenta] {', '.join(sorted(missing_czrn))}")
            if missing_cbf:
                self.console.print(f"  [bright_blue]Missing CBF fields:[/bright_blue] {', '.join(sorted(missing_cbf))}")

    def print_error_summary(self) -> None:
        """Print comprehensive error summary."""
        if not self.errors:
            self.console.print("\n[bold green]✅ No errors encountered in CZRN/CBF generation[/bold green]")
            return

        summary = self.get_error_summary()

        self.console.print("\n[bold red]❌ CZRN/CBF Generation Error Summary[/bold red]")
        self.console.print(f"[red]Total errors: {summary['total_errors']:,}[/red]")
        self.console.print(f"[green]Successful operations: {summary['successful_operations']:,}[/green]")
        self.console.print(f"[cyan]Total operations: {summary['total_operations']:,}[/cyan]")
        self.console.print(f"[yellow]Error rate: {summary['error_rate']:.2%}[/yellow]")

        # Error breakdown by operation
        if summary['error_operations']:
            self.console.print("\n[bold yellow]📊 Errors by Operation Type[/bold yellow]")
            for operation, count in sorted(summary['error_operations'].items()):
                self.console.print(f"  {operation}: {count:,} errors")

        # Error breakdown by type
        if summary['error_types']:
            self.console.print("\n[bold yellow]📋 Errors by Type[/bold yellow]")
            for error_type, count in sorted(summary['error_types'].items(), key=lambda x: x[1], reverse=True):
                self.console.print(f"  {error_type}: {count:,} errors")

        # Error breakdown by field
        if summary['error_fields']:
            self.console.print("\n[bold yellow]🎯 Errors by Field[/bold yellow]")
            for field, count in sorted(summary['error_fields'].items(), key=lambda x: x[1], reverse=True):
                self.console.print(f"  {field}: {count:,} errors")

    def print_detailed_errors(self, max_error_types: int = 10, max_samples_per_type: int = 3) -> None:
        """Print detailed error information with sample records."""
        if not self.errors:
            return

        self.console.print("\n[bold red]🔍 Detailed Error Analysis[/bold red]")

        # Group errors by message for detailed analysis
        summary = self.get_error_summary()
        error_groups = summary['error_groups']

        # Sort error groups by frequency
        sorted_error_groups = sorted(error_groups.items(), key=lambda x: len(x[1]), reverse=True)

        for i, (error_message, error_list) in enumerate(sorted_error_groups[:max_error_types], 1):
            self.console.print(f"\n[bold red]Error Type {i}:[/bold red] [white]{error_message}[/white]")
            self.console.print(f"[dim]Affects {len(error_list)} record(s). Operation breakdown:[/dim]")

            # Show operation breakdown for this error
            operations = defaultdict(int)
            for error in error_list:
                operations[error.operation] += 1

            for operation, count in operations.items():
                self.console.print(f"  {operation}: {count} records")

            # Show sample problematic records
            self.console.print(f"[dim]Sample problematic records (showing up to {max_samples_per_type}):[/dim]")

            sample_table = Table(show_header=True, header_style="bold yellow", box=SIMPLE, padding=(0, 1))
            sample_table.add_column("Operation", style="blue", no_wrap=False)
            sample_table.add_column("Field", style="cyan", no_wrap=False)
            sample_table.add_column("Entity ID", style="green", no_wrap=False)
            sample_table.add_column("Model", style="magenta", no_wrap=False)
            sample_table.add_column("Provider", style="yellow", no_wrap=False)
            sample_table.add_column("API Key", style="red", no_wrap=False)
            sample_table.add_column("Date", style="dim", no_wrap=False)

            for error in error_list[:max_samples_per_type]:
                source = error.source_data

                sample_table.add_row(
                    error.operation,
                    error.field_name or "N/A",
                    str(source.get('entity_id', 'N/A')),
                    str(source.get('model', 'N/A')),
                    str(source.get('custom_llm_provider', 'N/A')),
                    str(source.get('api_key', 'N/A')),
                    str(source.get('date', 'N/A'))
                )

            self.console.print(sample_table)

            if len(error_list) > max_samples_per_type:
                self.console.print(f"[dim]... and {len(error_list) - max_samples_per_type} more records with the same error[/dim]")
