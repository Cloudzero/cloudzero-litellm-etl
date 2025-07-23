# LiteLLM to CloudZero ETL Tool

Transform LiteLLM database data into CloudZero AnyCost CBF format for cost tracking and analysis.

## Features

- Extract usage data from LiteLLM PostgreSQL database
- Transform data into CloudZero Billing Format (CBF)
- Analysis mode with beautiful terminal output using Rich
- Multiple output options: CSV files or direct CloudZero API streaming
- Built with modern Python tools: uv, ruff, pytest, polars, httpx

## Installation

### From PyPI (Recommended)

```bash
# Install with uv (recommended)
uv add litellm-cz-etl

# Or install with pip
pip install litellm-cz-etl
```

### From Source

```bash
git clone <repository-url>
cd litellm-cz-etl
uv sync
```

## Configuration

ll2cz supports configuration files to avoid repeating common settings. You can store your database connection, CloudZero API credentials, and other settings in `~/.ll2cz/config.yml`.

### Create Configuration File

```bash
# Create an example configuration file
ll2cz config example

# Check current configuration status
ll2cz config status
```

This creates `~/.ll2cz/config.yml` with the following structure:

```yaml
database_url: postgresql://user:password@host:5432/litellm_db
cz_api_key: your-cloudzero-api-key
cz_connection_id: your-connection-id
```

### Configuration Priority

CLI arguments always take priority over configuration file values:

1. **CLI arguments** (highest priority)
2. **Configuration file** (`~/.ll2cz/config.yml`)
3. **Default values** (lowest priority)

### CLI Commands

```bash
# Show version
ll2cz --version

# Show help
ll2cz --help

# Configuration management
ll2cz config example     # Create example config file
ll2cz config status      # Show current config status
ll2cz config edit        # Interactively edit configuration
```

## Usage

### Transform Mode

Transform LiteLLM data to CloudZero CBF format:

```bash
# Display data on screen (formatted table)
ll2cz transform --input "postgresql://user:pass@host:5432/litellm_db" --screen

# Export to CSV file
ll2cz transform --input "postgresql://user:pass@host:5432/litellm_db" --output data.csv

# Limit records for screen display
ll2cz transform --screen --limit 25
```

### Transmit Mode

Send data directly to CloudZero AnyCost API:

```bash
# Send today's data
ll2cz transmit day

# Send specific day's data (DD-MM-YYYY format)
ll2cz transmit day 15-01-2024

# Send current month's data
ll2cz transmit month

# Send specific month's data (MM-YYYY format)
ll2cz transmit month 01-2024

# Send all available data (batched by day)
ll2cz transmit all

# Test mode - show payloads without sending (5 records only)
ll2cz transmit day --test

# Use append mode (sum operation instead of replace_hourly)
ll2cz transmit day --append

# Specify timezone for date handling
ll2cz transmit day --timezone "US/Eastern"

# Limit number of records to process
ll2cz transmit month --limit 1000
```

### Analysis Mode

Analyze your LiteLLM database data:

```bash
# General data analysis
ll2cz analyze data --limit 10000

# Show raw table data
ll2cz analyze data --show-raw --table all

# Show specific table only
ll2cz analyze data --show-raw --table user

# CZRN (CloudZero Resource Name) analysis
ll2cz analyze czrn --limit 10000

# Spend analysis
ll2cz analyze spend --limit 10000

# Database schema analysis
ll2cz analyze schema --output schema_docs.md

# Force refresh cache
ll2cz analyze data --force-refresh

# Save analysis to JSON
ll2cz analyze data --json analysis.json
```

### Cache Management

Manage local data cache for offline operation:

```bash
# Check cache status (local only)
ll2cz cache status

# Check cache status with remote server verification
ll2cz cache status --remote-check

# Clear local cache
ll2cz cache clear

# Force refresh cache from server
ll2cz cache refresh
```

## Data Transformation

The tool transforms LiteLLM usage logs into CloudZero's CBF format with the following mappings:

- `spend` → `cost`
- `total_tokens` → `usage_quantity`
- `model`, `user_id`, `call_type` → `dimensions`
- `metadata` fields → additional `dimensions`
- Duration calculated from `startTime` and `endTime`

## Technology Stack

This project follows modern Python best practices:

- **Python 3.12** - Latest Python version
- **uv** - Fast Python package manager
- **Polars** - High-performance DataFrames (instead of pandas)
- **httpx** - Modern HTTP client (instead of requests)
- **Rich** - Beautiful terminal output and formatting
- **Typer** - Modern CLI framework with rich help formatting
- **PyYAML** - YAML configuration file support
- **Pathlib** - Modern filesystem path operations
- **pytest** - Testing framework
- **ruff** - Fast Python linter and formatter

## Development

```bash
# Setup development environment
uv sync --dev

# Run tests
uv run pytest

# Run linting
uv run ruff check src/ tests/

# Fix linting issues
uv run ruff check --fix src/ tests/

# Build package
uv build
```

## Requirements

- Python ≥ 3.12
- PostgreSQL database with LiteLLM data
- CloudZero API key and connection ID (for streaming mode)

## License

Apache 2.0 - see LICENSE file for details.