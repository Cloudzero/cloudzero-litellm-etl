# SPDX-FileCopyrightText: Copyright (c), CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Data analysis module for LiteLLM database inspection."""

from typing import Any, Dict, List, Optional, Tuple, Union

import polars as pl
from rich.console import Console
from rich.table import Table

from .cached_database import CachedLiteLLMDatabase
from .czrn import CZRNGenerator
from .data_processor import DataProcessor
from .database import LiteLLMDatabase
from .error_tracking import ConsolidatedErrorTracker


class DataAnalyzer:
    """Analyze LiteLLM database data for inspection and validation."""

    def __init__(self, database: Union[LiteLLMDatabase, CachedLiteLLMDatabase]):
        """Initialize analyzer with database connection."""
        self.database = database
        self.console = Console()

    def analyze(self, limit: int = 10000, source: str = "usertable", cbf_example_limit: int = 5) -> Dict[str, Any]:
        """Perform comprehensive analysis of LiteLLM data including source data summary, CZRN generation, and CBF transformation.

        Args:
            limit: Number of records to analyze
            source: Data source - 'usertable' for user/team/tag tables or 'logs' for SpendLogs table
            cbf_example_limit: Number of CBF transformation examples to generate
        """
        # Load data based on the specified source
        if source == "logs":
            # Use SpendLogs data with enriched organization information
            if isinstance(self.database, CachedLiteLLMDatabase):
                raw_data = self.database.get_spend_logs_for_analysis(limit=limit)
            else:
                raw_data = self.database.get_spend_logs_for_analysis(limit=limit)
        else:
            # Use traditional user/team/tag aggregated data
            if isinstance(self.database, CachedLiteLLMDatabase):
                raw_data = self.database.get_usage_data(limit=limit)
            else:
                raw_data = self.database.get_usage_data(limit=limit)
        table_info = self.database.get_table_info()

        # Filter data and show filtering summary
        data, filter_summary = self._filter_successful_requests(raw_data)

        # Generate CBF transformation examples using centralized processor
        cbf_examples = []
        if not data.is_empty():
            processor = DataProcessor(source=source)
            sample_data = data.head(cbf_example_limit)  # Transform specified number of records as examples
            _, cbf_records, _ = processor.process_dataframe(sample_data)
            cbf_examples = cbf_records

        # CZRN analysis data
        czrn_analysis_data = None
        if not data.is_empty():
            czrn_analysis_data = self._perform_czrn_analysis(data, source)

        return {
            'table_info': table_info,
            'data_summary': self._analyze_data_summary(data),
            'column_analysis': self._analyze_columns(data),
            'sample_records': data.head(5).to_dicts() if not data.is_empty() else [],
            'cbf_examples': cbf_examples,
            'filter_summary': filter_summary,
            'czrn_analysis': czrn_analysis_data
        }

    def _analyze_data_summary(self, data: pl.DataFrame) -> Dict[str, Any]:
        """Analyze basic data summary statistics for daily spend data."""
        if data.is_empty():
            return {'message': 'No data available'}

        columns = data.columns

        # Calculate total tokens from prompt + completion tokens
        total_tokens = 0
        if 'prompt_tokens' in columns and 'completion_tokens' in columns:
            total_tokens = int(data['prompt_tokens'].sum() + data['completion_tokens'].sum())

        # Get date range
        date_range = {}
        if 'date' in columns:
            date_range = {
                'start': str(data['date'].min()),
                'end': str(data['date'].max())
            }

        # Entity type breakdown
        entity_breakdown = {}
        if 'entity_type' in columns:
            entity_counts = data['entity_type'].value_counts()
            entity_breakdown = {
                row['entity_type']: row['count']
                for row in entity_counts.to_dicts()
            }

        return {
            'total_records_analyzed': len(data),
            'date_range': date_range,
            'total_spend': (
                float(data['spend'].sum())
                if 'spend' in columns else None
            ),
            'total_tokens': total_tokens,
            'total_api_requests': (
                int(data['api_requests'].sum())
                if 'api_requests' in columns else None
            ),
            'entity_breakdown': entity_breakdown,
            'data_types': {
                col: str(dtype)
                for col, dtype in zip(columns, data.dtypes, strict=False)
            }
        }

    def _analyze_columns(self, data: pl.DataFrame) -> Dict[str, Dict[str, Any]]:
        """Analyze each column for unique values and statistics."""
        column_analysis = {}

        for column in data.columns:
            series = data[column]
            dtype = series.dtype

            analysis = {
                'unique_count': series.n_unique(),
                'null_count': series.null_count(),
                'data_type': str(dtype)
            }

            if dtype in [pl.String, pl.Utf8]:
                value_counts = series.value_counts().limit(10)
                if not value_counts.is_empty():
                    analysis['top_values'] = {
                        row[column]: row['count']
                        for row in value_counts.to_dicts()
                    }
            elif dtype.is_numeric():
                if not data.is_empty():
                    analysis['stats'] = {
                        'min': (
                            float(series.min())
                            if series.min() is not None else None
                        ),
                        'max': (
                            float(series.max())
                            if series.max() is not None else None
                        ),
                        'mean': (
                            float(series.mean())
                            if series.mean() is not None else None
                        ),
                        'median': (
                            float(series.median())
                            if series.median() is not None else None
                        ),
                    }

            column_analysis[column] = analysis

        return column_analysis

    def _filter_successful_requests(self, data: pl.DataFrame) -> Tuple[pl.DataFrame, Dict[str, Any]]:
        """Filter data to only include records with successful_requests > 0."""
        if data.is_empty():
            return data, {'original_count': 0, 'filtered_count': 0, 'removed_count': 0}

        original_count = len(data)

        # Filter for successful requests only
        if 'successful_requests' in data.columns:
            filtered_data = data.filter(pl.col('successful_requests') > 0)
        else:
            # If column doesn't exist, assume all records are valid
            filtered_data = data

        filtered_count = len(filtered_data)
        removed_count = original_count - filtered_count

        filter_summary = {
            'original_count': original_count,
            'filtered_count': filtered_count,
            'removed_count': removed_count
        }

        return filtered_data, filter_summary

    def print_results(self, analysis: Dict[str, Any], source: str = "usertable") -> None:
        """Print analysis results to console using rich formatting."""
        table_info = analysis['table_info']
        data_summary = analysis['data_summary']

        # Table Structure - compact format
        self.console.print("\n[bold blue]📊 Database Overview[/bold blue]")
        rows = f"{table_info['row_count']:,}"
        cols = str(len(table_info['columns']))

        if 'table_breakdown' in table_info:
            breakdown = table_info['table_breakdown']
            self.console.print(f"  Rows: {rows} ({breakdown['user_spend']:,} user, {breakdown['team_spend']:,} team, {breakdown['tag_spend']:,} tag)")
        else:
            self.console.print(f"  Rows: {rows}")
        self.console.print(f"  Columns: {cols}")

        # Filter Summary
        if 'filter_summary' in analysis:
            filter_info = analysis['filter_summary']
            if filter_info['removed_count'] > 0:
                self.console.print(f"  Filtered: {filter_info['filtered_count']:,} records (removed {filter_info['removed_count']:,} with 0 successful requests)")
            else:
                self.console.print(f"  Filtered: {filter_info['filtered_count']:,} records (no filtering needed)")

        # Data Summary - compact format
        if 'message' in data_summary:
            self.console.print(f"\n[yellow]⚠️  {data_summary['message']}[/yellow]")
        else:
            self.console.print("\n[bold green]📈 Analysis Results[/bold green]")

            # Create compact summary lines
            summary_parts = []
            summary_parts.append(f"Records: {data_summary['total_records_analyzed']:,}")

            if data_summary['date_range']['start']:
                date_range = f"{data_summary['date_range']['start']} to {data_summary['date_range']['end']}"
                summary_parts.append(f"Dates: {date_range}")

            if data_summary['total_spend']:
                summary_parts.append(f"Spend: ${data_summary['total_spend']:.2f}")

            if data_summary['total_tokens']:
                summary_parts.append(f"Tokens: {data_summary['total_tokens']:,}")

            if data_summary['total_api_requests']:
                summary_parts.append(f"API calls: {data_summary['total_api_requests']:,}")

            # Print summary in compact format
            for part in summary_parts:
                self.console.print(f"  {part}")

            # Entity breakdown if available
            if data_summary['entity_breakdown']:
                entity_parts = []
                for entity_type, count in data_summary['entity_breakdown'].items():
                    entity_parts.append(f"{entity_type}: {count:,}")
                self.console.print(f"  Entities: {', '.join(entity_parts)}")

        # 3. SOURCE DATA FIELD ANALYSIS WITH CZRN/CBF MAPPINGS
        if analysis.get('czrn_analysis'):
            czrn_data = analysis['czrn_analysis']
            if czrn_data.get('field_analysis'):
                czrn_data['error_tracker'].print_source_field_analysis(czrn_data['field_analysis'], source)

        # 4. CZRN GENERATION ANALYSIS
        if analysis.get('czrn_analysis'):
            czrn_data = analysis['czrn_analysis']
            self.console.print("\n[bold yellow]🔗 CZRN Generation Analysis[/bold yellow]")
            self.console.print(f"[green]✓ {len(czrn_data['successful_czrns']):,} unique CZRNs generated from {czrn_data['total_operations']:,} total records[/green]")

            # Error reporting
            czrn_data['error_tracker'].print_error_summary()
            czrn_data['error_tracker'].print_detailed_errors()

            # Show successful CZRNs
            if czrn_data['successful_czrns']:
                self._print_deduplicated_czrn_list(list(czrn_data['successful_czrns']))

        # 5. CBF TRANSFORMATION EXAMPLES
        if analysis.get('cbf_examples'):
            self._print_cbf_examples(analysis['cbf_examples'])

    def _print_cbf_examples(self, cbf_examples: List[Dict[str, Any]]) -> None:
        """Print CloudZero CBF transformation examples showing all standard CBF columns."""
        self.console.print("\n[bold yellow]💰 CBF Transformation Examples[/bold yellow]")

        if not cbf_examples:
            self.console.print("[dim]No CBF examples available[/dim]")
            return

        # Create table showing all standard CBF columns with wider console
        from rich.box import SIMPLE_HEAVY
        from rich.console import Console

        cbf_table = Table(
            show_header=True,
            header_style="bold cyan",
            box=SIMPLE_HEAVY,
            padding=(0, 1),
            expand=False,
            min_width=None,
            width=None
        )

        # Add columns for all standard CBF fields using actual CBF column names
        cbf_table.add_column("time/usage_start", style="blue", no_wrap=True, min_width=12)
        cbf_table.add_column("cost/cost", style="green", justify="right", no_wrap=True, min_width=10)
        cbf_table.add_column("resource/id", style="magenta", no_wrap=False, min_width=25)
        cbf_table.add_column("usage/amount", style="yellow", justify="right", no_wrap=True, min_width=12)
        cbf_table.add_column("usage/units", style="yellow", no_wrap=True, min_width=11)
        cbf_table.add_column("resource/service", style="cyan", no_wrap=True, min_width=15)
        cbf_table.add_column("resource/account", style="purple", no_wrap=True, min_width=15)
        cbf_table.add_column("resource/region", style="orange1", no_wrap=True, min_width=14)
        cbf_table.add_column("resource/usage_family", style="bright_blue", no_wrap=True, min_width=20)
        cbf_table.add_column("lineitem/type", style="dim", no_wrap=True, min_width=12)
        cbf_table.add_column("Tag Count", style="white", justify="right", no_wrap=True, min_width=9)

        for cbf_record in cbf_examples:
            # Extract all standard CBF fields
            date_full = str(cbf_record.get('time/usage_start', 'N/A'))
            date = date_full.split('T')[0] if 'T' in date_full else date_full

            cost = f"${cbf_record.get('cost/cost', 0):.6f}"
            resource_id = str(cbf_record.get('resource/id', 'N/A'))
            usage_amount = f"{cbf_record.get('usage/amount', 0):,}"
            usage_units = str(cbf_record.get('usage/units', 'N/A'))
            service = str(cbf_record.get('resource/service', 'N/A'))
            account = str(cbf_record.get('resource/account', 'N/A'))
            region = str(cbf_record.get('resource/region', 'N/A'))
            usage_family = str(cbf_record.get('resource/usage_family', 'N/A'))
            lineitem_type = str(cbf_record.get('lineitem/type', 'N/A'))

            # Count resource/tag columns
            tag_count = sum(1 for key in cbf_record.keys() if key.startswith('resource/tag:'))

            cbf_table.add_row(
                date,
                cost,
                resource_id,
                usage_amount,
                usage_units,
                service,
                account,
                region,
                usage_family,
                lineitem_type,
                str(tag_count)
            )

        # Print table with wider console to avoid truncation
        wider_console = Console(width=250, force_terminal=True)
        wider_console.print(cbf_table)

        # Summary message with tag information
        total_records = len(cbf_examples)
        if cbf_examples:
            sample_tag_count = sum(1 for key in cbf_examples[0].keys() if key.startswith('resource/tag:'))
            self.console.print(f"\n[dim]💡 Showing {total_records} CBF transformation example(s) with {sample_tag_count} resource tags each • Use --csv or --cz-api-key to export all data[/dim]")
        else:
            self.console.print(f"\n[dim]💡 {total_records} CBF transformation example(s) • Use --csv or --cz-api-key to export all data[/dim]")


    def _print_czrn_list(self, czrn_results: List[Dict[str, Any]]) -> None:
        """Print generated CZRNs as a deduplicated table with aligned components."""

        # Group results by CZRN for deduplication
        czrn_groups = {}
        for result in czrn_results:
            czrn = result['czrn']
            if czrn not in czrn_groups:
                czrn_groups[czrn] = []
            czrn_groups[czrn].append(result)

        # Separate successful CZRNs from errors
        successful_czrns = {}
        error_czrns = {}

        for czrn, group in czrn_groups.items():
            if czrn.startswith('ERROR:'):
                error_czrns[czrn] = group
            else:
                successful_czrns[czrn] = group

        # Display error CZRNs first
        if error_czrns:
            self.console.print("\n[bold red]❌ CZRN Generation Errors Summary[/bold red]")
            for i, (czrn, group) in enumerate(error_czrns.items(), 1):
                clean_error = czrn.replace('ERROR: ', '')
                self.console.print(f"[red]{i:3d}. {clean_error}[/red] [dim]({len(group)} records)[/dim]")

        # Display successful CZRNs in a formatted table
        if successful_czrns:
            from rich.box import SIMPLE
            from rich.table import Table

            # Create table with no width constraints to show all data
            czrn_table = Table(
                show_header=True,
                header_style="bold cyan",
                box=SIMPLE,
                padding=(0, 1),
                expand=False,
                min_width=None,
                width=None,
            )
            czrn_table.add_column("#", style="green", justify="right", no_wrap=True)
            czrn_table.add_column("Provider", style="blue", no_wrap=True)
            czrn_table.add_column("Service Type", style="yellow", no_wrap=True)
            czrn_table.add_column("Region", style="magenta", no_wrap=True)
            czrn_table.add_column("Owner Account", style="cyan", no_wrap=True)
            czrn_table.add_column("Resource Type", style="green", no_wrap=True)
            czrn_table.add_column("Local ID", style="white", no_wrap=True)
            czrn_table.add_column("Records", style="dim", justify="right", no_wrap=True)

            czrn_generator = CZRNGenerator()

            self.console.print("\n[bold green]📝 Generated CZRNs (Deduplicated)[/bold green]")
            for i, (czrn, group) in enumerate(sorted(successful_czrns.items()), 1):
                try:
                    # Parse CZRN components
                    provider, service_type, region, owner_account_id, resource_type, cloud_local_id = czrn_generator.extract_components(czrn)

                    # Display full components without truncation
                    czrn_table.add_row(
                        str(i),
                        provider,
                        service_type,
                        region,
                        owner_account_id,
                        resource_type,
                        cloud_local_id,
                        str(len(group))
                    )
                except Exception:
                    # Fallback for malformed CZRNs
                    czrn_table.add_row(
                        str(i),
                        "[red]MALFORMED[/red]",
                        "",
                        "",
                        "",
                        "",
                        czrn,
                        str(len(group))
                    )

            # Print table with wider console to avoid truncation
            from rich.console import Console
            wider_console = Console(width=200, force_terminal=True)
            wider_console.print(czrn_table)

        # Summary
        total_records = len(czrn_results)
        errors = len(error_czrns)
        successful_unique = len(successful_czrns)

        self.console.print(f"\n[dim]💡 {successful_unique:,} unique CZRNs from {total_records:,} total records[/dim]")
        if errors > 0:
            self.console.print(f"[dim]❌ {errors:,} error types affecting records[/dim]")

        # Show source records for unknown-account CZRNs
        self._show_unknown_account_details(czrn_groups)

    def _show_unknown_account_details(self, czrn_groups: Dict[str, List[Dict[str, Any]]]) -> None:
        """Show source records for CZRNs with unknown-account owner account IDs."""
        unknown_account_czrns = {}

        for czrn, group in czrn_groups.items():
            if not czrn.startswith('ERROR:') and 'unknown-account' in czrn:
                unknown_account_czrns[czrn] = group

        if not unknown_account_czrns:
            return

        self.console.print("\n[bold red]⚠️  Unknown Account Details[/bold red]")
        self.console.print(f"[yellow]Found {len(unknown_account_czrns)} CZRN(s) with unknown-account. Showing source records:[/yellow]\n")

        for czrn, group in unknown_account_czrns.items():
            self.console.print(f"[bold white]CZRN:[/bold white] [red]{czrn}[/red]")
            self.console.print(f"[dim]Affected records ({len(group)} total, showing up to 5):[/dim]")

            # Show up to 5 source records that contribute to this CZRN with ALL fields
            from rich.box import SIMPLE
            table = Table(show_header=True, header_style="bold yellow", box=SIMPLE, padding=(0, 1))
            table.add_column("ID", style="dim", no_wrap=False)
            table.add_column("Date", style="green", no_wrap=False)
            table.add_column("Entity Type", style="blue", no_wrap=False)
            table.add_column("Entity ID", style="cyan", no_wrap=False)
            table.add_column("API Key", style="red", no_wrap=False)
            table.add_column("Model", style="magenta", no_wrap=False)
            table.add_column("Model Group", style="purple", no_wrap=False)
            table.add_column("Provider", style="yellow", no_wrap=False)
            table.add_column("Prompt Tokens", style="blue", justify="right", no_wrap=False)
            table.add_column("Completion Tokens", style="blue", justify="right", no_wrap=False)
            table.add_column("Spend", style="green", justify="right", no_wrap=False)
            table.add_column("API Requests", style="cyan", justify="right", no_wrap=False)
            table.add_column("Success", style="green", justify="right", no_wrap=False)
            table.add_column("Failed", style="red", justify="right", no_wrap=False)
            table.add_column("Cache Create", style="orange1", justify="right", no_wrap=False)
            table.add_column("Cache Read", style="orange3", justify="right", no_wrap=False)
            table.add_column("Created At", style="dim", no_wrap=False)
            table.add_column("Updated At", style="dim", no_wrap=False)

            for record in group[:5]:  # Limit to 5 records
                source = record['source_data']

                # Show ALL fields from the source record
                record_id = str(source.get('id', 'N/A'))
                date = str(source.get('date', 'N/A'))
                entity_type = str(source.get('entity_type', 'N/A'))
                entity_id = str(source.get('entity_id', 'N/A'))

                api_key = str(source.get('api_key', 'N/A'))

                model = str(source.get('model', 'N/A'))
                model_group = str(source.get('model_group', 'N/A'))
                provider = str(source.get('custom_llm_provider', 'N/A'))

                prompt_tokens = str(source.get('prompt_tokens', 0))
                completion_tokens = str(source.get('completion_tokens', 0))
                spend = f"${source.get('spend', 0):.6f}"
                api_requests = str(source.get('api_requests', 0))
                successful_requests = str(source.get('successful_requests', 0))
                failed_requests = str(source.get('failed_requests', 0))
                cache_creation_tokens = str(source.get('cache_creation_input_tokens', 0))
                cache_read_tokens = str(source.get('cache_read_input_tokens', 0))

                created_at = str(source.get('created_at', 'N/A'))
                if 'T' in created_at:
                    created_at = created_at.split('T')[0]  # Show just date part for brevity

                updated_at = str(source.get('updated_at', 'N/A'))
                if 'T' in updated_at:
                    updated_at = updated_at.split('T')[0]  # Show just date part for brevity

                table.add_row(
                    record_id, date, entity_type, entity_id, api_key, model, model_group,
                    provider, prompt_tokens, completion_tokens, spend, api_requests,
                    successful_requests, failed_requests, cache_creation_tokens,
                    cache_read_tokens, created_at, updated_at
                )

            self.console.print(table)

            if len(group) > 5:
                self.console.print(f"[dim]... and {len(group) - 5} more records[/dim]")

            self.console.print()  # Add spacing between CZRNs

    def _perform_czrn_analysis(self, data: pl.DataFrame, source: str = "usertable") -> Dict[str, Any]:
        """Perform CZRN analysis on the provided data and return analysis results."""
        # Use centralized processor for consistent analysis
        processor = DataProcessor(source=source)

        # Initialize consolidated error tracker for field analysis
        error_tracker = ConsolidatedErrorTracker()

        # Source data field analysis
        field_analysis = error_tracker.analyze_source_fields(data, source)

        # Generate CZRNs and CBF records using centralized processor
        czrns, cbf_records, error_summary = processor.process_dataframe(data)
        successful_czrns = {czrn for czrn in czrns if czrn}

        return {
            'error_tracker': error_tracker,
            'field_analysis': field_analysis,
            'successful_czrns': successful_czrns,
            'total_operations': len(data),
            'processor_errors': error_summary
        }

    def get_error_tracker(self) -> ConsolidatedErrorTracker:
        """Get the current error tracker instance."""
        # Create processor to access its error tracker
        processor = DataProcessor()
        return processor.error_tracker

    def _print_czrn_component_analysis(self, czrn_results: List[Dict[str, Any]]) -> None:
        """Print analysis of CZRN components."""
        self.console.print("\n[bold yellow]🧩 CZRN Component Analysis[/bold yellow]")

        # Extract components from successful CZRNs
        czrn_generator = CZRNGenerator()
        component_stats = {
            'service_type': {},
            'provider': {},
            'region': {},
            'owner_account_id': {},
            'resource_type': {},
            'cloud_local_id_patterns': {},
            'entity_types': {},
            'models': {}
        }

        valid_czrns = [r for r in czrn_results if not r['czrn'].startswith('ERROR:')]

        for result in valid_czrns:
            try:
                components = czrn_generator.extract_components(result['czrn'])
                provider, service_type, region, owner_account_id, resource_type, cloud_local_id = components

                # Count component frequencies
                component_stats['provider'][provider] = component_stats['provider'].get(provider, 0) + 1
                component_stats['service_type'][service_type] = component_stats['service_type'].get(service_type, 0) + 1
                component_stats['region'][region] = component_stats['region'].get(region, 0) + 1
                component_stats['owner_account_id'][owner_account_id] = component_stats['owner_account_id'].get(owner_account_id, 0) + 1
                component_stats['resource_type'][resource_type] = component_stats['resource_type'].get(resource_type, 0) + 1

                # Analyze cloud_local_id patterns (now just the model)
                component_stats['cloud_local_id_patterns'][cloud_local_id] = component_stats['cloud_local_id_patterns'].get(cloud_local_id, 0) + 1

                # Extract model from cloud_local_id (now just the model itself)
                component_stats['models'][cloud_local_id] = component_stats['models'].get(cloud_local_id, 0) + 1

                # Get entity types from source data instead of cloud_local_id
                source_data = result['source_data']
                entity_type = source_data.get('entity_type', 'unknown')
                component_stats['entity_types'][entity_type] = component_stats['entity_types'].get(entity_type, 0) + 1

            except Exception:
                continue

        # Create component breakdown table - lightweight formatting, no width limits
        from rich.box import SIMPLE
        comp_table = Table(show_header=True, header_style="bold cyan", box=SIMPLE, padding=(0, 1))
        comp_table.add_column("Component", style="bold blue", no_wrap=False)
        comp_table.add_column("Values", style="white", no_wrap=False)
        comp_table.add_column("Count", style="green", justify="right", no_wrap=False)

        # Ensure ALL components are shown, even if empty
        for component_name, values in component_stats.items():
            if values:
                # Show all values for this component, sorted by frequency
                for value, count in sorted(values.items(), key=lambda x: x[1], reverse=True):
                    comp_table.add_row(component_name.replace('_', ' ').title(), value, str(count))
                    component_name = ""  # Only show component name for first row
            else:
                # Show empty components too
                comp_table.add_row(component_name.replace('_', ' ').title(), "[dim]No values found[/dim]", "0")

        self.console.print(comp_table)

        # Summary statistics - compact format
        total_records = len(czrn_results)
        successful_czrns = len(valid_czrns)
        error_count = total_records - successful_czrns

        self.console.print(f"\n[green]✓ {successful_czrns}/{total_records} CZRNs generated successfully[/green]")
        if error_count > 0:
            self.console.print(f"[red]✗ {error_count} generation errors[/red]")

        self.console.print("\n[dim]💡 CZRNs follow format: czrn:provider:service-type:region:owner-account-id:resource-type:cloud-local-id[/dim]")
        self.console.print("[dim]🔍 Use generated CZRNs as resource_id values in CloudZero CBF records[/dim]")

    def _print_czrn_errors(self, czrn_results: List[Dict[str, Any]]) -> None:
        """Print detailed error information for failed CZRN generations."""
        # Collect error results
        error_results = [result for result in czrn_results if result['czrn'].startswith('ERROR:')]

        if not error_results:
            return

        self.console.print(f"[yellow]Found {len(error_results)} record(s) with generation errors:[/yellow]\n")

        # Group errors by error message
        error_groups = {}
        for result in error_results:
            error_msg = result['czrn']  # Contains "ERROR: <message>"
            if error_msg not in error_groups:
                error_groups[error_msg] = []
            error_groups[error_msg].append(result)

        for i, (error_msg, group) in enumerate(error_groups.items(), 1):
            # Clean up the error message for display
            clean_error = error_msg.replace('ERROR: ', '')
            self.console.print(f"[bold red]Error {i}:[/bold red] [white]{clean_error}[/white]")
            self.console.print(f"[dim]Affects {len(group)} record(s). Sample problematic records:[/dim]")

            # Show up to 3 sample records per error in detailed format
            for j, record in enumerate(group[:3], 1):
                source = record['source_data']

                self.console.print(f"\n[bold]Record {j}:[/bold]")

                # Show all fields from the database record
                for field_name, field_value in source.items():
                    # Format field name and value for display
                    formatted_name = field_name.replace('_', ' ').title()

                    # Handle different field types
                    if field_value is None:
                        formatted_value = "[dim red]NULL[/dim red]"
                    elif field_value == "":
                        formatted_value = "[dim red]EMPTY[/dim red]"
                    elif isinstance(field_value, str):
                        # Truncate very long strings but show API keys in full
                        if len(str(field_value)) > 100:
                            formatted_value = f"[white]{str(field_value)[:97]}...[/white]"
                        else:
                            formatted_value = f"[white]{str(field_value)}[/white]"
                    elif isinstance(field_value, (int, float)):
                        formatted_value = f"[cyan]{field_value}[/cyan]"
                    else:
                        formatted_value = f"[white]{str(field_value)}[/white]"

                    # Color-code problematic fields
                    if field_value in [None, "", 0] and field_name in ['model', 'entity_id', 'entity_type', 'custom_llm_provider']:
                        formatted_name = f"[bold red]{formatted_name}[/bold red]"
                    else:
                        formatted_name = f"[bold blue]{formatted_name}:[/bold blue]"

                    self.console.print(f"  {formatted_name:25} {formatted_value}")

            if len(group) > 3:
                self.console.print(f"\n[dim]... and {len(group) - 3} more record(s) with the same error[/dim]")

            self.console.print()  # Add spacing between error groups

    def spend_analysis(self, limit: Optional[int] = 10000) -> None:
        """Perform comprehensive spend analysis based on teams and users."""
        if limit is None:
            self.console.print("\n[bold blue]💰 Spend Analysis - Processing all records[/bold blue]")
        else:
            self.console.print(f"\n[bold blue]💰 Spend Analysis - Processing {limit} records[/bold blue]")

        # Get data from cache/database - use spend analysis data to include both user and team data
        if isinstance(self.database, CachedLiteLLMDatabase):
            raw_data = self.database.get_spend_analysis_data(limit=limit)
        else:
            raw_data = self.database.get_spend_analysis_data(limit=limit)

        # Filter data and show filtering summary
        data, filter_summary = self._filter_successful_requests(raw_data)

        # Show filter summary
        if filter_summary['removed_count'] > 0:
            self.console.print(f"[dim]Filtered {filter_summary['filtered_count']:,} records (removed {filter_summary['removed_count']:,} with 0 successful requests)[/dim]")
        else:
            self.console.print(f"[dim]Processing {filter_summary['filtered_count']:,} records (no filtering needed)[/dim]")

        if data.is_empty():
            self.console.print("[yellow]No data available for spend analysis after filtering[/yellow]")
            return

        # Perform spend analysis
        self._analyze_spend_by_entity(data)
        self._analyze_spend_by_model(data)
        self._analyze_spend_by_provider(data)
        self._analyze_spend_trends(data)

        # Add SpendLogs field analysis
        self._analyze_spend_logs_fields(limit=limit)

        # Add cost comparison between SpendLogs and user tables
        self._analyze_cost_comparison(limit=limit)

    def _analyze_spend_by_entity(self, data: pl.DataFrame) -> None:
        """Analyze spending breakdown by entity type (teams vs users)."""
        self.console.print("\n[bold yellow]👥 Entity Spend Analysis[/bold yellow]")

        # Group by entity type and calculate totals
        entity_summary = data.group_by('entity_type').agg([
            pl.col('spend').sum().alias('total_spend'),
            pl.col('entity_id').n_unique().alias('unique_entities'),
            pl.col('api_requests').sum().alias('total_requests'),
            pl.col('prompt_tokens').sum().alias('total_prompt_tokens'),
            pl.col('completion_tokens').sum().alias('total_completion_tokens'),
            pl.len().alias('record_count')
        ]).sort('total_spend', descending=True)

        # Display entity type summary
        from rich.box import SIMPLE
        from rich.table import Table

        summary_table = Table(show_header=True, header_style="bold cyan", box=SIMPLE, padding=(0, 1))
        summary_table.add_column("Entity Type", style="bold green", no_wrap=False)
        summary_table.add_column("Total Spend", style="green", justify="right", no_wrap=False)
        summary_table.add_column("Entities", style="blue", justify="right", no_wrap=False)
        summary_table.add_column("API Requests", style="cyan", justify="right", no_wrap=False)
        summary_table.add_column("Total Tokens", style="yellow", justify="right", no_wrap=False)
        summary_table.add_column("Records", style="dim", justify="right", no_wrap=False)

        total_spend = 0
        for row in entity_summary.to_dicts():
            entity_type = row['entity_type']
            spend = row['total_spend']
            total_spend += spend
            unique_entities = row['unique_entities']
            total_requests = row['total_requests']
            total_tokens = row['total_prompt_tokens'] + row['total_completion_tokens']
            records = row['record_count']

            summary_table.add_row(
                entity_type.title(),
                f"${spend:.2f}",
                f"{unique_entities:,}",
                f"{total_requests:,}",
                f"{total_tokens:,}",
                f"{records:,}"
            )

        self.console.print(summary_table)
        self.console.print(f"[dim]💡 Total spend across all entities: ${total_spend:.2f}[/dim]")

        # Show top spenders within each entity type
        self._show_top_spenders_by_entity_type(data, 'team', 5)
        self._show_top_spenders_by_entity_type(data, 'user', 5)

    def _show_top_spenders_by_entity_type(self, data: pl.DataFrame, entity_type: str, top_n: int) -> None:
        """Show top spenders for a specific entity type."""
        # Filter by entity type
        entity_data = data.filter(pl.col('entity_type') == entity_type)

        if entity_data.is_empty():
            return

        # Group by entity_id and calculate spend
        top_spenders = entity_data.group_by('entity_id').agg([
            pl.col('spend').sum().alias('total_spend'),
            pl.col('api_requests').sum().alias('total_requests'),
            pl.col('prompt_tokens').sum().alias('total_prompt_tokens'),
            pl.col('completion_tokens').sum().alias('total_completion_tokens'),
            pl.col('model').n_unique().alias('unique_models'),
            pl.len().alias('record_count')
        ]).sort('total_spend', descending=True).head(top_n)

        self.console.print(f"\n[bold cyan]🏆 Top {top_n} {entity_type.title()} Spenders[/bold cyan]")

        from rich.box import SIMPLE
        from rich.table import Table

        spenders_table = Table(show_header=True, header_style="bold cyan", box=SIMPLE, padding=(0, 1))
        spenders_table.add_column(f"{entity_type.title()} ID", style="bold blue", no_wrap=False)
        spenders_table.add_column("Total Spend", style="green", justify="right", no_wrap=False)
        spenders_table.add_column("API Requests", style="cyan", justify="right", no_wrap=False)
        spenders_table.add_column("Total Tokens", style="yellow", justify="right", no_wrap=False)
        spenders_table.add_column("Models Used", style="magenta", justify="right", no_wrap=False)
        spenders_table.add_column("Records", style="dim", justify="right", no_wrap=False)

        for row in top_spenders.to_dicts():
            entity_id = row['entity_id']
            spend = row['total_spend']
            requests = row['total_requests']
            total_tokens = row['total_prompt_tokens'] + row['total_completion_tokens']
            unique_models = row['unique_models']
            records = row['record_count']

            spenders_table.add_row(
                entity_id,
                f"${spend:.2f}",
                f"{requests:,}",
                f"{total_tokens:,}",
                f"{unique_models}",
                f"{records:,}"
            )

        self.console.print(spenders_table)

    def _analyze_spend_by_model(self, data: pl.DataFrame) -> None:
        """Analyze spending breakdown by model."""
        self.console.print("\n[bold yellow]🤖 Model Spend Analysis[/bold yellow]")

        # Group by model and calculate totals
        model_summary = data.group_by('model').agg([
            pl.col('spend').sum().alias('total_spend'),
            pl.col('entity_id').n_unique().alias('unique_users'),
            pl.col('api_requests').sum().alias('total_requests'),
            pl.col('prompt_tokens').sum().alias('total_prompt_tokens'),
            pl.col('completion_tokens').sum().alias('total_completion_tokens'),
            pl.len().alias('record_count')
        ]).sort('total_spend', descending=True).head(10)  # Top 10 models

        from rich.box import SIMPLE
        from rich.table import Table

        model_table = Table(show_header=True, header_style="bold cyan", box=SIMPLE, padding=(0, 1))
        model_table.add_column("Model", style="bold magenta", no_wrap=False)
        model_table.add_column("Total Spend", style="green", justify="right", no_wrap=False)
        model_table.add_column("Users", style="blue", justify="right", no_wrap=False)
        model_table.add_column("API Requests", style="cyan", justify="right", no_wrap=False)
        model_table.add_column("Total Tokens", style="yellow", justify="right", no_wrap=False)
        model_table.add_column("Avg Cost/Token", style="red", justify="right", no_wrap=False)

        for row in model_summary.to_dicts():
            model = row['model']
            spend = row['total_spend']
            users = row['unique_users']
            requests = row['total_requests']
            total_tokens = row['total_prompt_tokens'] + row['total_completion_tokens']
            avg_cost_per_token = spend / total_tokens if total_tokens > 0 else 0

            model_table.add_row(
                model,
                f"${spend:.2f}",
                f"{users:,}",
                f"{requests:,}",
                f"{total_tokens:,}",
                f"${avg_cost_per_token:.6f}"
            )

        self.console.print(model_table)

    def _analyze_spend_by_provider(self, data: pl.DataFrame) -> None:
        """Analyze spending breakdown by provider."""
        self.console.print("\n[bold yellow]🏢 Provider Spend Analysis[/bold yellow]")

        # Group by provider and calculate totals
        provider_summary = data.group_by('custom_llm_provider').agg([
            pl.col('spend').sum().alias('total_spend'),
            pl.col('entity_id').n_unique().alias('unique_users'),
            pl.col('model').n_unique().alias('unique_models'),
            pl.col('api_requests').sum().alias('total_requests'),
            pl.col('prompt_tokens').sum().alias('total_prompt_tokens'),
            pl.col('completion_tokens').sum().alias('total_completion_tokens'),
            pl.len().alias('record_count')
        ]).sort('total_spend', descending=True)

        from rich.box import SIMPLE
        from rich.table import Table

        provider_table = Table(show_header=True, header_style="bold cyan", box=SIMPLE, padding=(0, 1))
        provider_table.add_column("Provider", style="bold yellow", no_wrap=False)
        provider_table.add_column("Total Spend", style="green", justify="right", no_wrap=False)
        provider_table.add_column("Users", style="blue", justify="right", no_wrap=False)
        provider_table.add_column("Models", style="magenta", justify="right", no_wrap=False)
        provider_table.add_column("API Requests", style="cyan", justify="right", no_wrap=False)
        provider_table.add_column("Total Tokens", style="yellow", justify="right", no_wrap=False)

        for row in provider_summary.to_dicts():
            provider = row['custom_llm_provider'] or 'Unknown'
            spend = row['total_spend']
            users = row['unique_users']
            models = row['unique_models']
            requests = row['total_requests']
            total_tokens = row['total_prompt_tokens'] + row['total_completion_tokens']

            provider_table.add_row(
                provider,
                f"${spend:.2f}",
                f"{users:,}",
                f"{models:,}",
                f"{requests:,}",
                f"{total_tokens:,}"
            )

        self.console.print(provider_table)

    def _analyze_spend_trends(self, data: pl.DataFrame) -> None:
        """Analyze spending trends over time."""
        self.console.print("\n[bold yellow]📈 Spend Trends Analysis[/bold yellow]")

        # Check if we have date information
        if 'date' not in data.columns:
            self.console.print("[dim]No date information available for trend analysis[/dim]")
            return

        # Group by date and calculate daily totals
        daily_trends = data.group_by('date').agg([
            pl.col('spend').sum().alias('total_spend'),
            pl.col('entity_id').n_unique().alias('unique_users'),
            pl.col('api_requests').sum().alias('total_requests'),
            pl.col('prompt_tokens').sum().alias('total_prompt_tokens'),
            pl.col('completion_tokens').sum().alias('total_completion_tokens'),
            pl.len().alias('record_count')
        ]).sort('date')

        if daily_trends.is_empty():
            self.console.print("[dim]No trend data available[/dim]")
            return

        # Show summary statistics
        total_days = len(daily_trends)
        avg_daily_spend = daily_trends['total_spend'].mean()
        max_daily_spend = daily_trends['total_spend'].max()
        min_daily_spend = daily_trends['total_spend'].min()

        self.console.print("[green]📊 Trend Summary[/green]")
        self.console.print(f"  Days analyzed: {total_days}")
        self.console.print(f"  Average daily spend: ${avg_daily_spend:.2f}")
        self.console.print(f"  Highest daily spend: ${max_daily_spend:.2f}")
        self.console.print(f"  Lowest daily spend: ${min_daily_spend:.2f}")

        # Show recent days (last 7 days)
        recent_days = daily_trends.tail(7)

        from rich.box import SIMPLE
        from rich.table import Table

        trend_table = Table(show_header=True, header_style="bold cyan", box=SIMPLE, padding=(0, 1))
        trend_table.add_column("Date", style="bold blue", no_wrap=False)
        trend_table.add_column("Daily Spend", style="green", justify="right", no_wrap=False)
        trend_table.add_column("Users", style="blue", justify="right", no_wrap=False)
        trend_table.add_column("API Requests", style="cyan", justify="right", no_wrap=False)
        trend_table.add_column("Total Tokens", style="yellow", justify="right", no_wrap=False)

        for row in recent_days.to_dicts():
            date = row['date']
            spend = row['total_spend']
            users = row['unique_users']
            requests = row['total_requests']
            total_tokens = row['total_prompt_tokens'] + row['total_completion_tokens']

            trend_table.add_row(
                str(date),
                f"${spend:.2f}",
                f"{users:,}",
                f"{requests:,}",
                f"{total_tokens:,}"
            )

        self.console.print(f"\n[bold cyan]📅 Recent Activity (Last {len(recent_days)} Days)[/bold cyan]")
        self.console.print(trend_table)

    def _analyze_spend_logs_fields(self, limit: Optional[int] = 1000) -> None:
        """Analyze SpendLogs table fields and their unique values."""
        self.console.print("\n[bold yellow]📋 SpendLogs Field Analysis[/bold yellow]")

        try:
            # Get SpendLogs data
            if isinstance(self.database, CachedLiteLLMDatabase):
                spend_logs_data = self.database.get_spend_logs_data(limit=limit)
            else:
                spend_logs_data = self.database.get_spend_logs_data(limit=limit)

            if spend_logs_data.is_empty():
                self.console.print("[yellow]No SpendLogs data available[/yellow]")
                return

            self.console.print(f"[dim]Analyzing {len(spend_logs_data):,} SpendLogs records[/dim]")

            # Use the existing field analysis infrastructure
            from .error_tracking import ConsolidatedErrorTracker
            error_tracker = ConsolidatedErrorTracker()
            field_analysis = error_tracker.analyze_source_fields(spend_logs_data, "logs")

            # Create a simplified analysis table for SpendLogs-specific fields
            from rich.box import SIMPLE
            from rich.table import Table

            logs_table = Table(show_header=True, header_style="bold cyan", box=SIMPLE, padding=(0, 1))
            logs_table.add_column("Field Name", style="bold blue", no_wrap=False)
            logs_table.add_column("Unique", justify="right", style="green", no_wrap=False)
            logs_table.add_column("Null", justify="right", style="red", no_wrap=False)
            logs_table.add_column("Sample Values", style="dim", no_wrap=False)

            # Focus on key SpendLogs fields
            key_fields = [
                'request_id', 'call_type', 'api_key', 'spend', 'total_tokens',
                'model', 'custom_llm_provider', 'user', 'team_id', 'end_user',
                'cache_hit', 'session_id', 'api_base', 'requester_ip_address'
            ]

            for field_name in key_fields:
                if field_name in field_analysis:
                    analysis = field_analysis[field_name]

                    # Format sample values
                    sample_str = ""
                    if analysis.sample_values:
                        samples = analysis.sample_values[:3]  # Show first 3
                        sample_str = ", ".join([f"'{v}'" if isinstance(v, str) else str(v) for v in samples])
                        if len(analysis.sample_values) > 3:
                            sample_str += f" (+{len(analysis.sample_values) - 3} more)"

                    logs_table.add_row(
                        field_name,
                        f"{analysis.unique_count:,}",
                        f"{analysis.null_count:,}" if analysis.null_count > 0 else "0",
                        sample_str
                    )

            self.console.print(logs_table)

            # Show JSONB field analysis
            self._analyze_jsonb_fields(spend_logs_data)

        except Exception as e:
            self.console.print(f"[red]Error analyzing SpendLogs: {e}[/red]")
            if "does not exist" in str(e) or "relation" in str(e):
                self.console.print("[dim]SpendLogs table may not exist in this database[/dim]")

    def _analyze_jsonb_fields(self, data: pl.DataFrame) -> None:
        """Analyze JSONB fields in SpendLogs data."""
        jsonb_fields = ['metadata', 'request_tags', 'messages', 'response']

        for field in jsonb_fields:
            if field in data.columns:
                self.console.print(f"\n[bold cyan]🔍 {field.title()} Field Analysis[/bold cyan]")

                series = data[field]
                non_null_count = len(series) - series.null_count()

                if non_null_count == 0:
                    self.console.print(f"[dim]All {field} values are null[/dim]")
                    continue

                # Get unique non-null values for analysis
                unique_values = series.filter(series.is_not_null()).unique().limit(5).to_list()

                self.console.print(f"  Non-null records: {non_null_count:,}")
                self.console.print(f"  Unique values: {series.n_unique():,}")

                if unique_values:
                    self.console.print("  Sample values:")
                    for i, value in enumerate(unique_values[:3], 1):
                        # Truncate long JSON strings for display
                        value_str = str(value)
                        if len(value_str) > 100:
                            value_str = value_str[:97] + "..."
                        self.console.print(f"    {i}. {value_str}")
                else:
                    self.console.print("  [dim]No sample values available[/dim]")

    def _print_deduplicated_czrn_list(self, czrns: List[str]) -> None:
        """Print a deduplicated list of CZRNs in a formatted table."""
        czrn_generator = CZRNGenerator()

        # Create table with no width constraints to show all data
        from rich.box import SIMPLE
        from rich.table import Table

        czrn_table = Table(
            show_header=True,
            header_style="bold cyan",
            box=SIMPLE,
            padding=(0, 1),
            expand=False,
            min_width=None,
            width=None,
        )
        czrn_table.add_column("#", style="green", justify="right", no_wrap=True)
        czrn_table.add_column("Provider", style="blue", no_wrap=True)
        czrn_table.add_column("Service Type", style="yellow", no_wrap=True)
        czrn_table.add_column("Region", style="magenta", no_wrap=True)
        czrn_table.add_column("Owner Account", style="cyan", no_wrap=True)
        czrn_table.add_column("Resource Type", style="green", no_wrap=True)
        czrn_table.add_column("Local ID", style="white", no_wrap=True)

        for i, czrn in enumerate(sorted(czrns), 1):
            try:
                # Parse CZRN components
                provider, service_type, region, owner_account_id, resource_type, cloud_local_id = czrn_generator.extract_components(czrn)

                # Display full components without truncation
                czrn_table.add_row(
                    str(i),
                    provider,
                    service_type,
                    region,
                    owner_account_id,
                    resource_type,
                    cloud_local_id
                )
            except Exception:
                # Fallback for malformed CZRNs
                czrn_table.add_row(
                    str(i),
                    "[red]MALFORMED[/red]",
                    "",
                    "",
                    "",
                    "",
                    czrn
                )

        # Print table with wider console to avoid truncation
        from rich.console import Console
        wider_console = Console(width=200, force_terminal=True)
        wider_console.print(czrn_table)

    def _analyze_cost_comparison(self, limit: Optional[int] = None) -> None:
        """Compare costs between SpendLogs and user tables to identify discrepancies."""
        self.console.print("\n[bold magenta]📊 Cost Comparison: SpendLogs vs User Tables[/bold magenta]")

        try:
            # Get data from both sources
            if isinstance(self.database, CachedLiteLLMDatabase):
                usertable_data = self.database.get_spend_analysis_data(limit=limit)
                spendlogs_data = self.database.get_spend_logs_for_analysis(limit=limit)
            else:
                usertable_data = self.database.get_spend_analysis_data(limit=limit)
                spendlogs_data = self.database.get_spend_logs_for_analysis(limit=limit)

            # Calculate key metrics for each source
            usertable_metrics = self._calculate_spend_metrics(usertable_data, "User Tables")
            spendlogs_metrics = self._calculate_spend_metrics(spendlogs_data, "SpendLogs")

            # Display comparison table
            self._display_cost_comparison_table(usertable_metrics, spendlogs_metrics)

            # Analyze date ranges and coverage
            self._analyze_date_coverage(usertable_data, spendlogs_data)

            # Analyze provider and model coverage
            self._analyze_provider_coverage(usertable_data, spendlogs_data)

            # Calculate potential discrepancies
            self._analyze_cost_discrepancies(usertable_metrics, spendlogs_metrics)

        except Exception as e:
            self.console.print(f"[red]Error during cost comparison: {e}[/red]")

    def _calculate_spend_metrics(self, data: pl.DataFrame, source_name: str) -> Dict[str, Any]:
        """Calculate key spending metrics from a data source."""
        if data.is_empty():
            return {
                'source': source_name,
                'total_records': 0,
                'total_spend': 0.0,
                'unique_providers': 0,
                'unique_models': 0,
                'total_requests': 0,
                'total_tokens': 0,
                'avg_cost_per_request': 0.0,
                'avg_cost_per_token': 0.0,
                'date_range': {'start': None, 'end': None}
            }

        # Calculate metrics
        total_records = len(data)
        total_spend = float(data.select(pl.col('spend').sum()).item())

        # Handle different column names between sources
        try:
            unique_providers = int(data.select(pl.col('custom_llm_provider').n_unique()).item())
        except Exception:
            unique_providers = 0

        try:
            unique_models = int(data.select(pl.col('model').n_unique()).item())
        except Exception:
            unique_models = 0

        # Calculate request totals
        try:
            total_requests = int(data.select(pl.col('api_requests').sum()).item())
        except Exception:
            # For SpendLogs, count number of records as requests
            total_requests = total_records

        # Calculate token totals
        try:
            prompt_tokens = int(data.select(pl.col('prompt_tokens').sum()).item() or 0)
            completion_tokens = int(data.select(pl.col('completion_tokens').sum()).item() or 0)
            total_tokens = prompt_tokens + completion_tokens
        except Exception:
            total_tokens = 0

        # Calculate averages
        avg_cost_per_request = total_spend / total_requests if total_requests > 0 else 0.0
        avg_cost_per_token = total_spend / total_tokens if total_tokens > 0 else 0.0

        # Get date range
        try:
            date_col = 'date' if 'date' in data.columns else 'start_time'
            date_stats = data.select([
                pl.col(date_col).min().alias('start_date'),
                pl.col(date_col).max().alias('end_date')
            ]).to_dicts()[0]
            date_range = {
                'start': date_stats['start_date'],
                'end': date_stats['end_date']
            }
        except Exception:
            date_range = {'start': None, 'end': None}

        return {
            'source': source_name,
            'total_records': total_records,
            'total_spend': total_spend,
            'unique_providers': unique_providers,
            'unique_models': unique_models,
            'total_requests': total_requests,
            'total_tokens': total_tokens,
            'avg_cost_per_request': avg_cost_per_request,
            'avg_cost_per_token': avg_cost_per_token,
            'date_range': date_range
        }

    def _display_cost_comparison_table(self, usertable_metrics: Dict[str, Any], spendlogs_metrics: Dict[str, Any]) -> None:
        """Display a comparison table of key metrics between sources."""
        from rich.box import SIMPLE
        from rich.table import Table

        # Create comparison table
        table = Table(show_header=True, header_style="bold cyan", box=SIMPLE, padding=(0, 1))
        table.add_column("Metric", style="bold green", no_wrap=False)
        table.add_column("User Tables", style="blue", justify="right", no_wrap=False)
        table.add_column("SpendLogs", style="yellow", justify="right", no_wrap=False)
        table.add_column("Difference", style="magenta", justify="right", no_wrap=False)
        table.add_column("% Diff", style="red", justify="right", no_wrap=False)

        # Helper function to calculate percentage difference
        def calc_percent_diff(val1, val2):
            if val1 == 0 and val2 == 0:
                return "0%"
            if val1 == 0:
                return "∞"
            return f"{((val2 - val1) / val1) * 100:.1f}%"

        # Add rows for each metric
        metrics_to_compare = [
            ('Total Records', 'total_records', lambda x: f"{x:,}"),
            ('Total Spend', 'total_spend', lambda x: f"${x:.2f}"),
            ('Unique Providers', 'unique_providers', lambda x: f"{x:,}"),
            ('Unique Models', 'unique_models', lambda x: f"{x:,}"),
            ('Total Requests', 'total_requests', lambda x: f"{x:,}"),
            ('Total Tokens', 'total_tokens', lambda x: f"{x:,}"),
            ('Avg Cost/Request', 'avg_cost_per_request', lambda x: f"${x:.4f}"),
            ('Avg Cost/Token', 'avg_cost_per_token', lambda x: f"${x:.6f}")
        ]

        for metric_name, metric_key, formatter in metrics_to_compare:
            ut_val = usertable_metrics[metric_key]
            sl_val = spendlogs_metrics[metric_key]
            diff = sl_val - ut_val
            percent_diff = calc_percent_diff(ut_val, sl_val)

            # Color code the difference
            if abs(diff) < 0.01 and metric_key in ['total_spend', 'avg_cost_per_request', 'avg_cost_per_token']:
                diff_color = "green"
            elif diff > 0:
                diff_color = "yellow"
            else:
                diff_color = "red"

            # Format difference based on metric type
            if metric_key == 'total_spend':
                diff_str = f"[{diff_color}]${diff:.2f}[/{diff_color}]"
            elif metric_key in ['avg_cost_per_request', 'avg_cost_per_token']:
                diff_str = f"[{diff_color}]${diff:.6f}[/{diff_color}]"
            else:
                diff_str = f"[{diff_color}]{diff:,}[/{diff_color}]"

            table.add_row(
                metric_name,
                formatter(ut_val),
                formatter(sl_val),
                diff_str,
                f"[{diff_color}]{percent_diff}[/{diff_color}]"
            )

        self.console.print(table)

    def _analyze_date_coverage(self, usertable_data: pl.DataFrame, spendlogs_data: pl.DataFrame) -> None:
        """Analyze date range coverage between sources."""
        self.console.print("\n[bold cyan]📅 Date Range Coverage Analysis[/bold cyan]")

        # Get date ranges for both sources
        ut_dates = self._get_date_range(usertable_data, 'date')
        sl_dates = self._get_date_range(spendlogs_data, 'start_time')

        from rich.box import SIMPLE
        from rich.table import Table

        date_table = Table(show_header=True, header_style="bold cyan", box=SIMPLE, padding=(0, 1))
        date_table.add_column("Source", style="bold green", no_wrap=False)
        date_table.add_column("Earliest Date", style="blue", no_wrap=False)
        date_table.add_column("Latest Date", style="yellow", no_wrap=False)
        date_table.add_column("Days Covered", style="magenta", justify="right", no_wrap=False)

        date_table.add_row(
            "User Tables",
            str(ut_dates['start']) if ut_dates['start'] else "N/A",
            str(ut_dates['end']) if ut_dates['end'] else "N/A",
            str(ut_dates['days']) if ut_dates['days'] else "N/A"
        )

        date_table.add_row(
            "SpendLogs",
            str(sl_dates['start']) if sl_dates['start'] else "N/A",
            str(sl_dates['end']) if sl_dates['end'] else "N/A",
            str(sl_dates['days']) if sl_dates['days'] else "N/A"
        )

        self.console.print(date_table)

        # Analyze overlaps and gaps
        if ut_dates['start'] and sl_dates['start']:
            self.console.print("\n[dim]💡 Coverage Analysis:[/dim]")
            if ut_dates['start'] < sl_dates['start']:
                gap_days = (sl_dates['start'] - ut_dates['start']).days
                self.console.print(f"[yellow]  • User Tables have {gap_days} days of data before SpendLogs start[/yellow]")
            elif sl_dates['start'] < ut_dates['start']:
                gap_days = (ut_dates['start'] - sl_dates['start']).days
                self.console.print(f"[yellow]  • SpendLogs have {gap_days} days of data before User Tables start[/yellow]")
            else:
                self.console.print("[green]  • Both sources start on the same date[/green]")

    def _analyze_provider_coverage(self, usertable_data: pl.DataFrame, spendlogs_data: pl.DataFrame) -> None:
        """Analyze provider and model coverage between sources."""
        self.console.print("\n[bold cyan]🔌 Provider & Model Coverage Analysis[/bold cyan]")

        # Get unique providers and models from both sources
        try:
            ut_providers = set(usertable_data.select('custom_llm_provider').to_series().unique().to_list())
        except Exception:
            ut_providers = set()

        try:
            ut_models = set(usertable_data.select('model').to_series().unique().to_list())
        except Exception:
            ut_models = set()

        try:
            sl_providers = set(spendlogs_data.select('custom_llm_provider').to_series().unique().to_list())
        except Exception:
            sl_providers = set()

        try:
            sl_models = set(spendlogs_data.select('model').to_series().unique().to_list())
        except Exception:
            sl_models = set()

        # Calculate overlaps and differences
        common_providers = ut_providers & sl_providers
        ut_only_providers = ut_providers - sl_providers
        sl_only_providers = sl_providers - ut_providers

        common_models = ut_models & sl_models
        ut_only_models = ut_models - sl_models
        sl_only_models = sl_models - ut_models

        self.console.print(f"[green]✓ Common Providers ({len(common_providers)}):[/green] {', '.join(sorted(common_providers))}")
        if ut_only_providers:
            self.console.print(f"[yellow]⚠ User Tables Only ({len(ut_only_providers)}):[/yellow] {', '.join(sorted(ut_only_providers))}")
        if sl_only_providers:
            self.console.print(f"[blue]ℹ SpendLogs Only ({len(sl_only_providers)}):[/blue] {', '.join(sorted(sl_only_providers))}")

        self.console.print(f"\n[green]✓ Common Models ({len(common_models)}):[/green]")
        if len(common_models) <= 10:
            self.console.print(f"  {', '.join(sorted(common_models))}")
        else:
            self.console.print(f"  {', '.join(sorted(list(common_models)[:10]))} ... and {len(common_models)-10} more")

        if ut_only_models:
            self.console.print(f"[yellow]⚠ User Tables Only Models ({len(ut_only_models)}):[/yellow]")
            if len(ut_only_models) <= 5:
                self.console.print(f"  {', '.join(sorted(ut_only_models))}")
            else:
                self.console.print(f"  {', '.join(sorted(list(ut_only_models)[:5]))} ... and {len(ut_only_models)-5} more")

        if sl_only_models:
            self.console.print(f"[blue]ℹ SpendLogs Only Models ({len(sl_only_models)}):[/blue]")
            if len(sl_only_models) <= 5:
                self.console.print(f"  {', '.join(sorted(sl_only_models))}")
            else:
                self.console.print(f"  {', '.join(sorted(list(sl_only_models)[:5]))} ... and {len(sl_only_models)-5} more")

    def _analyze_cost_discrepancies(self, usertable_metrics: Dict[str, Any], spendlogs_metrics: Dict[str, Any]) -> None:
        """Analyze and highlight significant cost discrepancies."""
        self.console.print("\n[bold red]🚨 Cost Discrepancy Analysis[/bold red]")

        ut_spend = usertable_metrics['total_spend']
        sl_spend = spendlogs_metrics['total_spend']

        if ut_spend == 0 and sl_spend == 0:
            self.console.print("[green]✓ Both sources report zero spend[/green]")
            return

        spend_diff = sl_spend - ut_spend
        spend_percent_diff = abs(spend_diff) / max(ut_spend, sl_spend) * 100 if max(ut_spend, sl_spend) > 0 else 0

        # Classify discrepancy severity
        if spend_percent_diff < 1:
            severity = "green"
            status = "✓ MINIMAL"
        elif spend_percent_diff < 5:
            severity = "yellow"
            status = "⚠ MINOR"
        elif spend_percent_diff < 20:
            severity = "yellow"
            status = "⚠ MODERATE"
        else:
            severity = "red"
            status = "🚨 MAJOR"

        self.console.print(f"[{severity}]{status} DISCREPANCY: {spend_percent_diff:.1f}% difference[/{severity}]")

        if spend_diff > 0:
            self.console.print(f"[blue]SpendLogs reports ${spend_diff:.2f} MORE than User Tables[/blue]")
        else:
            self.console.print(f"[yellow]User Tables report ${abs(spend_diff):.2f} MORE than SpendLogs[/yellow]")

        # Provide potential explanations
        self.console.print("\n[dim]💡 Potential Explanations:[/dim]")
        if spend_percent_diff > 5:
            self.console.print("[dim]  • Different aggregation periods (daily vs transaction-level)[/dim]")
            self.console.print("[dim]  • Data processing delays or timing differences[/dim]")
            self.console.print("[dim]  • Different filtering or inclusion criteria[/dim]")
            self.console.print("[dim]  • Failed requests included in one source but not the other[/dim]")
        else:
            self.console.print("[dim]  • Normal variance due to aggregation timing[/dim]")

    def _get_date_range(self, data: pl.DataFrame, date_col: str) -> Dict[str, Any]:
        """Get date range information from a DataFrame."""
        if data.is_empty() or date_col not in data.columns:
            return {'start': None, 'end': None, 'days': None}

        try:
            date_stats = data.select([
                pl.col(date_col).min().alias('start_date'),
                pl.col(date_col).max().alias('end_date')
            ]).to_dicts()[0]

            start_date = date_stats['start_date']
            end_date = date_stats['end_date']

            if start_date and end_date:
                # Convert to date objects if they're datetime
                if hasattr(start_date, 'date'):
                    start_date = start_date.date()
                if hasattr(end_date, 'date'):
                    end_date = end_date.date()

                days = (end_date - start_date).days + 1
            else:
                days = None

            return {
                'start': start_date,
                'end': end_date,
                'days': days
            }
        except Exception:
            return {'start': None, 'end': None, 'days': None}

