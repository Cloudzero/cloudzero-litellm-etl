# SPDX-FileCopyrightText: Copyright (c), CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Command line interface for LiteLLM to CloudZero ETL tool using argparse."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console

from . import __version__
from .analysis import DataAnalyzer
from .cached_database import CachedLiteLLMDatabase
from .config import Config
from .database import LiteLLMDatabase
from .output import CSVWriter
from .cbf_transformer import CBFTransformer
from .transmit import DataTransmitter

console = Console()


class CustomHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Custom help formatter that provides better formatting."""
    def __init__(self, prog, indent_increment=2, max_help_position=30, width=None):
        super().__init__(prog, indent_increment, max_help_position, width)


def add_common_database_args(parser):
    """Add common database connection arguments to a parser."""
    parser.add_argument(
        '--input',
        dest='db_connection',
        help='LiteLLM PostgreSQL database connection URL'
    )


def add_cloudzero_auth_args(parser):
    """Add CloudZero authentication arguments to a parser."""
    parser.add_argument(
        '--cz-api-key',
        dest='cz_api_key',
        help='CloudZero API key for data transmission'
    )
    parser.add_argument(
        '--cz-connection-id',
        dest='cz_connection_id',
        help='CloudZero connection ID for this data source'
    )


def handle_database_config(args):
    """Handle database configuration loading."""
    config = Config()
    db_connection = config.get_database_connection(args.db_connection)

    if not db_connection:
        console.print("[red]Error: --input (database connection) is required[/red]")
        console.print("[blue]You can set it via CLI argument or in ~/.ll2cz/config.yml[/blue]")
        console.print("[blue]Run 'll2cz config-example' to create a sample config file[/blue]")
        sys.exit(1)

    return db_connection


def handle_cloudzero_auth(args):
    """Handle CloudZero authentication configuration."""
    config = Config()

    cz_api_key = config.get_cz_api_key(args.cz_api_key)
    if not cz_api_key:
        console.print("[red]Error: --cz-api-key (CloudZero API key) is required[/red]")
        console.print("[blue]You can set it via CLI argument or in ~/.ll2cz/config.yml[/blue]")
        console.print("[blue]Run 'll2cz config-example' to create a sample config file[/blue]")
        sys.exit(1)

    cz_connection_id = config.get_cz_connection_id(args.cz_connection_id)
    if not cz_connection_id:
        console.print("[red]Error: --cz-connection-id (CloudZero connection ID) is required[/red]")
        console.print("[blue]You can set it via CLI argument or in ~/.ll2cz/config.yml[/blue]")
        console.print("[blue]Run 'll2cz config-example' to create a sample config file[/blue]")
        sys.exit(1)

    return cz_api_key, cz_connection_id


# Config commands
def config_example(args):
    """Create an example configuration file."""
    config = Config()
    config.create_example_config()


def config_show(args):
    """Show current configuration."""
    config = Config()
    config.show_config_status()


# Analyze commands
def analyze_data(args):
    """Comprehensive analysis of LiteLLM data."""
    db_connection = handle_database_config(args)

    # Validate table option if show_raw is enabled
    if args.show_raw and args.table not in ["all", "user", "team", "tag", "logs"]:
        console.print("[red]Error: --table must be one of: all, user, team, tag, logs[/red]")
        sys.exit(1)

    if args.csv and not args.show_raw:
        console.print("[red]Error: --csv requires --show-raw to be enabled[/red]")
        sys.exit(1)

    # Choose database implementation based on cache setting
    if args.disable_cache:
        database = LiteLLMDatabase(db_connection)
        console.print("[dim]Cache disabled - using direct database connection[/dim]")
    else:
        database = CachedLiteLLMDatabase(db_connection)
        if database.is_offline_mode():
            console.print("[yellow]⚠️  Operating in offline mode - using cached data[/yellow]")

    if args.show_raw:
        # Show raw data tables
        raw_limit = 100 if args.limit == 10000 else args.limit

        if args.table == "all":
            if args.csv:
                console.print(f"[blue]Exporting {raw_limit:,} records from each LiteLLM table to CSV files...[/blue]")
            else:
                console.print(f"[blue]Showing {raw_limit:,} records from each LiteLLM table...[/blue]")
            _show_all_tables_data_cached(database, raw_limit, args.csv)
        else:
            if args.csv:
                console.print(f"[blue]Exporting {raw_limit:,} records from LiteLLM_{args.table.title()}Spend table to CSV file...[/blue]")
            else:
                console.print(f"[blue]Showing {raw_limit:,} records from LiteLLM_{args.table.title()}Spend table...[/blue]")
            _show_single_table_data_cached(database, args.table, raw_limit, args.csv)
    else:
        # Show comprehensive data analysis
        source_desc = "SpendLogs table" if args.source == "logs" else "user tables"
        console.print(f"[blue]Running comprehensive analysis on {args.limit:,} records from {source_desc}...[/blue]")
        analyzer = DataAnalyzer(database)
        results = analyzer.analyze(limit=args.limit, source=args.source, cbf_example_limit=args.records)

        console.print("\n[bold]Comprehensive Data Analysis:[/bold]")
        console.print("=" * 60)
        analyzer.print_results(results, args.source)

        if args.json:
            json_path = Path(args.json)
            json_path.write_text(json.dumps(results, indent=2, default=str))
            console.print(f"[green]Analysis results saved to {json_path}[/green]")


def analyze_spend(args):
    """Analyze spending patterns."""
    db_connection = handle_database_config(args)

    # Choose database implementation
    if args.disable_cache:
        database = LiteLLMDatabase(db_connection)
        console.print("[dim]Cache disabled - using direct database connection[/dim]")
    else:
        database = CachedLiteLLMDatabase(db_connection)
        if database.is_offline_mode():
            console.print("[yellow]⚠️  Operating in offline mode - using cached data[/yellow]")

    console.print(f"[blue]Analyzing spending patterns for {args.limit:,} records...[/blue]")

    try:
        analyzer = DataAnalyzer(database)
        analyzer.spend_analysis(limit=args.limit)
    except Exception as e:
        console.print(f"[red]Error during spend analysis: {e}[/red]")
        sys.exit(1)


def analyze_schema(args):
    """Discover and document database schema."""
    db_connection = handle_database_config(args)
    database = LiteLLMDatabase(db_connection)

    console.print("[blue]Discovering LiteLLM database schema...[/blue]")

    try:
        schema_info = database.discover_all_tables()

        # Display summary
        console.print("\n[bold]📊 Database Schema Summary[/bold]")
        console.print(f"Found {schema_info['table_count']} LiteLLM tables")

        # Display each table
        for table_name, table_info in sorted(schema_info['tables'].items()):
            console.print(f"\n[bold cyan]📋 {table_name}[/bold cyan]")
            console.print(f"  Rows: {table_info['row_count']:,}")
            console.print(f"  Columns: {len(table_info['columns'])}")

            if table_info['primary_keys']:
                console.print(f"  Primary Keys: {', '.join(table_info['primary_keys'])}")

        # Save to file if requested
        if args.output:
            output_path = Path(args.output)
            with output_path.open('w') as f:
                f.write("# LiteLLM Database Schema\n\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n\n")
                f.write("## Summary\n")
                f.write(f"- Total Tables: {schema_info['table_count']}\n")
                f.write(f"- Tables: {', '.join(sorted(schema_info['table_names']))}\n\n")

                for table_name, table_info in sorted(schema_info['tables'].items()):
                    f.write(f"## {table_name}\n\n")
                    f.write(f"- **Row Count**: {table_info['row_count']:,}\n")
                    f.write(f"- **Primary Keys**: {', '.join(table_info['primary_keys']) or 'None'}\n\n")

                    f.write("### Columns\n\n")
                    f.write("| Column | Type | Nullable | Default |\n")
                    f.write("|--------|------|----------|----------|\n")

                    for col in table_info['columns']:
                        nullable = "Yes" if col['is_nullable'] == 'YES' else "No"
                        default = col['column_default'] or '-'
                        f.write(f"| {col['column_name']} | {col['data_type']} | {nullable} | {default} |\n")

                    if table_info['foreign_keys']:
                        f.write("\n### Foreign Keys\n\n")
                        for fk in table_info['foreign_keys']:
                            f.write(f"- {fk['column_name']} → {fk['foreign_table_name']}.{fk['foreign_column_name']}\n")

                    if table_info['indexes']:
                        f.write("\n### Indexes\n\n")
                        for idx in table_info['indexes']:
                            unique = " (unique)" if idx['is_unique'] else ""
                            f.write(f"- {idx['index_name']}{unique}: {', '.join(idx['column_names'])}\n")

                    f.write("\n")

            console.print(f"[green]Schema documentation saved to {output_path}[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


# Transform command
def transform(args):
    """Transform LiteLLM data to CloudZero CBF format."""
    db_connection = handle_database_config(args)

    # Choose database implementation
    if args.disable_cache:
        database = LiteLLMDatabase(db_connection)
        console.print("[dim]Cache disabled - using direct database connection[/dim]")
    else:
        database = CachedLiteLLMDatabase(db_connection)
        if database.is_offline_mode():
            console.print("[yellow]⚠️  Operating in offline mode - using cached data[/yellow]")

    source_desc = "SpendLogs table" if args.source == "logs" else "user tables"
    console.print(f"[blue]Transforming {args.limit:,} records from {source_desc} to CBF format...[/blue]")

    try:
        transformer = CBFTransformer(database, timezone=args.timezone)
        cbf_data, summary = transformer.transform(
            limit=args.limit,
            source=args.source
        )

        # Display summary
        console.print(f"\n[green]✓ Transformed {summary['records_transformed']:,} records[/green]")
        console.print(f"[blue]Date range: {summary['date_range']['min']} to {summary['date_range']['max']}[/blue]")
        console.print(f"[blue]Total spend: ${summary['total_spend']:,.2f}[/blue]")
        console.print(f"[blue]Total tokens: {summary['total_tokens']:,}[/blue]")

        # Save output
        output_path = Path(args.output)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if args.format == 'csv':
            writer = CSVWriter()
            writer.write_cbf_records(cbf_data, output_path)
            console.print(f"[green]CBF data written to {output_path} (CSV format)[/green]")
        else:  # jsonl
            with output_path.open('w') as f:
                for record in cbf_data:
                    f.write(json.dumps(record, default=str) + '\n')
            console.print(f"[green]CBF data written to {output_path} (JSONL format)[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


# Transmit command
def transmit(args):
    """Transmit data to CloudZero."""
    db_connection = handle_database_config(args)
    cz_api_key, cz_connection_id = handle_cloudzero_auth(args)

    # Choose database implementation
    if args.disable_cache:
        database = LiteLLMDatabase(db_connection)
        console.print("[dim]Cache disabled - using direct database connection[/dim]")
    else:
        database = CachedLiteLLMDatabase(db_connection)
        if database.is_offline_mode():
            console.print("[yellow]⚠️  Operating in offline mode - using cached data[/yellow]")

    try:
        transmitter = DataTransmitter(
            database=database,
            cz_api_key=cz_api_key,
            cz_connection_id=cz_connection_id,
            timezone=args.timezone or 'UTC'
        )

        transmitter.transmit(
            mode=args.mode,
            date_spec=args.date,
            source=args.source,
            append=args.append,
            test=args.test,
            limit=args.records
        )

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


# Cache commands
def cache_status(args):
    """Show cache status."""
    db_connection = handle_database_config(args)

    try:
        database = CachedLiteLLMDatabase(db_connection)

        if args.remote_check:
            console.print("[blue]Checking cache status with remote server verification...[/blue]")

            # Test server connectivity
            if database.database:
                try:
                    conn = database.database.connect()
                    conn.close()
                    server_status = "[green]✓ Online[/green]"
                except Exception as e:
                    server_status = f"[red]✗ Offline ({str(e)})[/red]"
            else:
                server_status = "[red]✗ No connection configured[/red]"

            console.print("\n[bold]🌐 Server Status[/bold]")
            console.print(f"  Status: {server_status}")
            console.print(f"  Connection: {db_connection[:50]}..." if len(db_connection) > 50 else f"  Connection: {db_connection}")

            # Get table info if online
            if database.database:
                try:
                    table_info = database.get_table_info()
                    console.print("\n[bold]📊 Remote Database[/bold]")
                    console.print(f"  Total rows: {table_info['row_count']:,}")
                    console.print(f"  Columns: {len(table_info['columns'])}")

                    breakdown = table_info['table_breakdown']
                    console.print("\n[bold]📋 Table Breakdown[/bold]")
                    console.print(f"  User spend: {breakdown.get('user_spend', 0):,}")
                    console.print(f"  Team spend: {breakdown.get('team_spend', 0):,}")
                    console.print(f"  Tag spend: {breakdown.get('tag_spend', 0):,}")
                except Exception:
                    pass
        else:
            console.print("[blue]📦 Cache Status (Local Only)[/blue]")

        # Get cache status
        cache_status = database.get_cache_status()

        console.print(f"  Cache file: {cache_status.get('cache_file', 'Unknown')}")
        console.print(f"  Records cached: {cache_status.get('record_count', 0):,}")
        console.print(f"  Server available: {'Yes' if cache_status.get('server_available') else 'No'}")
        console.print(f"  Operating mode: {'Online' if cache_status.get('server_available') else 'Offline'}")

        if cache_status.get('last_update'):
            console.print(f"  Last updated: {cache_status['last_update']}")

        # Show breakdown
        breakdown = cache_status.get('breakdown', {})
        if breakdown:
            console.print("\n[bold]📊 Cache Breakdown[/bold]")
            console.print(f"  User records: {breakdown.get('user', 0):,}")
            console.print(f"  Team records: {breakdown.get('team', 0):,}")
            console.print(f"  Tag records: {breakdown.get('tag', 0):,}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def cache_clear(args):
    """Clear the cache."""
    db_connection = handle_database_config(args)

    try:
        database = CachedLiteLLMDatabase(db_connection)
        database.clear_cache()
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def cache_refresh(args):
    """Refresh the cache."""
    db_connection = handle_database_config(args)

    try:
        database = CachedLiteLLMDatabase(db_connection)

        console.print("[blue]Refreshing cache from server...[/blue]")
        database.refresh_cache()
        console.print("[green]✓ Cache refreshed successfully[/green]")

        # Show updated status
        cache_status = database.get_cache_status()
        console.print("\n[bold]Updated Cache Status[/bold]")
        console.print(f"  Records cached: {cache_status.get('record_count', 0):,}")

        breakdown = cache_status.get('breakdown', {})
        if breakdown:
            console.print(f"  User records: {breakdown.get('user', 0):,}")
            console.print(f"  Team records: {breakdown.get('team', 0):,}")
            console.print(f"  Tag records: {breakdown.get('tag', 0):,}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


# Helper functions (from original cli.py)
def _show_all_tables_data_cached(database, limit, csv_output=False):
    """Show data from all three LiteLLM tables individually using cache."""
    # Show table breakdown first (unless in CSV mode)
    table_info = database.get_table_info()
    breakdown = table_info['table_breakdown']
    if not csv_output:
        console.print("\n[bold blue]📊 Table Overview[/bold blue]")
        console.print(f"  User records: {breakdown['user_spend']:,}")
        console.print(f"  Team records: {breakdown['team_spend']:,}")
        console.print(f"  Tag records: {breakdown['tag_spend']:,}")
        console.print(f"  Total records: {sum(breakdown.values()):,}")

    # Show each table individually
    tables_to_show = [
        ("user", "LiteLLM_DailyUserSpend", "👤"),
        ("team", "LiteLLM_DailyTeamSpend", "👥"),
        ("tag", "LiteLLM_DailyTagSpend", "🏷️"),
        ("logs", "LiteLLM_SpendLogs", "📊")
    ]

    for table_type, table_name, emoji in tables_to_show:
        # For --show-raw, always try to query the table regardless of breakdown count
        if not csv_output:
            console.print(f"\n[bold green]{emoji} {table_name}[/bold green]")
        _show_single_table_data_cached(database, table_type, limit, csv_output)


def _show_single_table_data_cached(database, table_type, limit, csv_output=False):
    """Show data from a specific LiteLLM table using cache or export to CSV."""
    from pathlib import Path

    from rich.box import SIMPLE
    from rich.table import Table

    # Handle special case for logs table name
    if table_type == "logs":
        table_name = "LiteLLM_SpendLogs"
    else:
        table_name = f"LiteLLM_Daily{table_type.title()}Spend"

    if not csv_output:
        console.print(f"\n[bold green]📋 Raw Data from {table_name}[/bold green]")

    # Get data from cache filtered by entity type
    data = database.get_individual_table_data(table_type, limit=limit)

    if not data.is_empty():
        if csv_output:
            # Export to CSV
            csv_filename = f"{table_name}.csv"
            csv_path = Path(csv_filename)
            data.write_csv(csv_path)
            console.print(f"[green]✓ Exported {len(data):,} records from {table_name} to {csv_path}[/green]")
        else:
            # Show table in console
            table = Table(show_header=True, header_style="bold cyan", box=SIMPLE, padding=(0, 1))

            # For SpendLogs, show only key columns due to large number of fields
            if table_type == "logs":
                key_columns = [
                    'request_id', 'startTime', 'user', 'api_key', 'model',
                    'custom_llm_provider', 'total_tokens', 'spend', 'team_id'
                ]
                # Filter to only columns that exist in the data
                columns_to_show = [col for col in key_columns if col in data.columns]

                # Add columns
                for col in columns_to_show:
                    table.add_column(col, style="white", no_wrap=True if col == 'request_id' else False)

                # Add rows with selected columns
                for row in data.to_dicts():
                    table.add_row(*[str(row.get(col, ''))[:50] if col == 'request_id' else str(row.get(col, '')) for col in columns_to_show])
            else:
                # Add columns dynamically based on data
                for col in data.columns:
                    table.add_column(col, style="white", no_wrap=False)

                # Add rows
                for row in data.to_dicts():
                    table.add_row(*[str(row.get(col, '')) for col in data.columns])

            console.print(table)
            console.print(f"[dim]💡 Showing {len(data):,} records from {table_name}[/dim]")
    else:
        if not csv_output:
            console.print(f"[yellow]No data found in {table_name}[/yellow]")


def create_parser():
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog='ll2cz',
        description='Transform LiteLLM database data into CloudZero AnyCost CBF format',
        formatter_class=CustomHelpFormatter
    )

    # Global options
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )

    # Create subparsers
    subparsers = parser.add_subparsers(
        title='commands',
        dest='command',
        help='Available commands',
        required=True
    )

    # Config commands
    config_parser = subparsers.add_parser(
        'config',
        help='Configuration management commands',
        formatter_class=CustomHelpFormatter
    )
    config_subparsers = config_parser.add_subparsers(
        title='config commands',
        dest='config_command',
        required=True
    )

    config_example_parser = config_subparsers.add_parser(
        'example',
        help='Create an example configuration file at ~/.ll2cz/config.yml'
    )
    config_example_parser.set_defaults(func=config_example)

    config_show_parser = config_subparsers.add_parser(
        'show',
        help='Show current configuration with redacted sensitive values'
    )
    config_show_parser.set_defaults(func=config_show)

    # Analyze commands
    analyze_parser = subparsers.add_parser(
        'analyze',
        help='Analysis and data exploration commands',
        formatter_class=CustomHelpFormatter
    )
    analyze_subparsers = analyze_parser.add_subparsers(
        title='analyze commands',
        dest='analyze_command',
        required=True
    )

    # analyze data
    analyze_data_parser = analyze_subparsers.add_parser(
        'data',
        help='Comprehensive analysis of LiteLLM data including source data summary, CZRN generation, and CBF transformation'
    )
    add_common_database_args(analyze_data_parser)
    analyze_data_parser.add_argument(
        '--limit',
        type=int,
        default=10000,
        help='Number of records to analyze (default: 10000)'
    )
    analyze_data_parser.add_argument(
        '--json',
        help='JSON output file for analysis results'
    )
    analyze_data_parser.add_argument(
        '--show-raw',
        action='store_true',
        help='Show raw data tables instead of analysis'
    )
    analyze_data_parser.add_argument(
        '--table',
        default='all',
        choices=['all', 'user', 'team', 'tag', 'logs'],
        help="Show specific table only (for --show-raw): 'user', 'team', 'tag', 'logs', or 'all'"
    )
    analyze_data_parser.add_argument(
        '--csv',
        action='store_true',
        help='Export raw table data to CSV files (requires --show-raw)'
    )
    analyze_data_parser.add_argument(
        '--disable-cache',
        action='store_true',
        help='Disable cache and fetch data directly from database'
    )
    analyze_data_parser.add_argument(
        '--source',
        default='usertable',
        choices=['usertable', 'logs'],
        help="Data source: 'usertable' (default) or 'logs' (SpendLogs table)"
    )
    analyze_data_parser.add_argument(
        '--records',
        type=int,
        default=5,
        help='Number of CBF transformation examples to show (default: 5)'
    )
    analyze_data_parser.set_defaults(func=analyze_data)

    # analyze spend
    analyze_spend_parser = analyze_subparsers.add_parser(
        'spend',
        help='Analyze spending patterns based on LiteLLM team and user data'
    )
    add_common_database_args(analyze_spend_parser)
    analyze_spend_parser.add_argument(
        '--limit',
        type=int,
        default=10000,
        help='Number of records to analyze for spend analysis (default: 10000)'
    )
    analyze_spend_parser.add_argument(
        '--disable-cache',
        action='store_true',
        help='Disable cache and fetch data directly from database'
    )
    analyze_spend_parser.set_defaults(func=analyze_spend)

    # analyze schema
    analyze_schema_parser = analyze_subparsers.add_parser(
        'schema',
        help='Discover and document all tables in the LiteLLM database'
    )
    add_common_database_args(analyze_schema_parser)
    analyze_schema_parser.add_argument(
        '--output',
        help='Output file for schema documentation (Markdown format)'
    )
    analyze_schema_parser.set_defaults(func=analyze_schema)

    # Transform command
    transform_parser = subparsers.add_parser(
        'transform',
        help='Transform LiteLLM data to CloudZero AnyCost CBF format'
    )
    add_common_database_args(transform_parser)
    transform_parser.add_argument(
        '--output',
        default='cbf_output.jsonl',
        help='Output file path (default: cbf_output.jsonl)'
    )
    transform_parser.add_argument(
        '--format',
        choices=['jsonl', 'csv'],
        default='jsonl',
        help='Output format (default: jsonl)'
    )
    transform_parser.add_argument(
        '--limit',
        type=int,
        default=10000,
        help='Number of records to transform (default: 10000)'
    )
    transform_parser.add_argument(
        '--timezone',
        default='UTC',
        help='Timezone for date conversions (default: UTC)'
    )
    transform_parser.add_argument(
        '--disable-cache',
        action='store_true',
        help='Disable cache and fetch data directly from database'
    )
    transform_parser.add_argument(
        '--source',
        default='usertable',
        choices=['usertable', 'logs'],
        help="Data source: 'usertable' (default) or 'logs' (SpendLogs table)"
    )
    transform_parser.set_defaults(func=transform)

    # Transmit command
    transmit_parser = subparsers.add_parser(
        'transmit',
        help='Transmit transformed data to CloudZero'
    )
    add_common_database_args(transmit_parser)
    add_cloudzero_auth_args(transmit_parser)
    transmit_parser.add_argument(
        '--mode',
        choices=['today', 'yesterday', 'date-range', 'all'],
        default='yesterday',
        help='Transmission mode (default: yesterday)'
    )
    transmit_parser.add_argument(
        '--date',
        help='Date specification (YYYY-MM-DD for single date, or YYYY-MM-DD:YYYY-MM-DD for range)'
    )
    transmit_parser.add_argument(
        '--source',
        default='usertable',
        choices=['usertable', 'logs'],
        help="Data source: 'usertable' (default) or 'logs' (SpendLogs table)"
    )
    transmit_parser.add_argument(
        '--append',
        action='store_true',
        help='Append data to existing records in CloudZero'
    )
    transmit_parser.add_argument(
        '--test',
        action='store_true',
        help='Test mode - show what would be sent without transmitting'
    )
    transmit_parser.add_argument(
        '--records',
        type=int,
        help='Number of records to send or show (if using --test)'
    )
    transmit_parser.add_argument(
        '--timezone',
        help='Timezone for date operations (e.g., America/New_York)'
    )
    transmit_parser.add_argument(
        '--disable-cache',
        action='store_true',
        help='Disable cache and fetch data directly from database'
    )
    transmit_parser.set_defaults(func=transmit)

    # Cache commands
    cache_parser = subparsers.add_parser(
        'cache',
        help='Cache management commands',
        formatter_class=CustomHelpFormatter
    )
    cache_subparsers = cache_parser.add_subparsers(
        title='cache commands',
        dest='cache_command',
        required=True
    )

    # cache status
    cache_status_parser = cache_subparsers.add_parser(
        'status',
        help='Show cache status and information'
    )
    add_common_database_args(cache_status_parser)
    cache_status_parser.add_argument(
        '--remote-check',
        action='store_true',
        help='Perform remote server checks and show detailed server status'
    )
    cache_status_parser.set_defaults(func=cache_status)

    # cache clear
    cache_clear_parser = cache_subparsers.add_parser(
        'clear',
        help='Clear the local cache'
    )
    add_common_database_args(cache_clear_parser)
    cache_clear_parser.set_defaults(func=cache_clear)

    # cache refresh
    cache_refresh_parser = cache_subparsers.add_parser(
        'refresh',
        help='Force refresh the cache from server'
    )
    add_common_database_args(cache_refresh_parser)
    cache_refresh_parser.set_defaults(func=cache_refresh)

    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    try:
        # Call the appropriate function
        args.func(args)
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import os
        if os.environ.get('LL2CZ_DEBUG'):
            import traceback
            console.print("[dim]Full traceback:[/dim]")
            console.print(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()
