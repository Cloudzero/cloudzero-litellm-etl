# LiteLLM to CloudZero ETL Tool

Transform LiteLLM database data into CloudZero AnyCost CBF format for cost tracking and analysis.

## Features

- Extract usage data from LiteLLM PostgreSQL database
- Transform data into CloudZero Billing Format (CBF)
- Analysis mode with beautiful terminal output using Rich
- Multiple output options: CSV files or direct CloudZero API streaming
- Built with modern Python tools: uv, ruff, pytest, polars, httpx

## Installation

```bash
# Install from PyPI (once published)
uv add litellm-cz-etl

# Or install from source
git clone <repository-url>
cd litellm-cz-etl
uv sync
```

## Configuration

ll2cz supports configuration files to avoid repeating common settings. You can store your database connection, CloudZero API credentials, and other settings in `~/.ll2cz/config.yml`.

### Create Configuration File

```bash
# Create an example configuration file
ll2cz config-example

# Check current configuration status
ll2cz config-status
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

# Show help (also shown when no options provided)
ll2cz --help

# Configuration management
ll2cz config-example    # Create example config file
ll2cz config-status     # Show current config status
```

## Usage

### Analysis Mode

Inspect your LiteLLM data with beautifully formatted terminal output:

```bash
# Analyze 100 recent records with rich formatting
ll2cz --analysis 100

# Or with explicit database connection (overrides config file)
ll2cz --input "postgresql://user:pass@host:5432/litellm_db" --analysis 100

# Save analysis results to JSON
ll2cz --analysis 100 --json analysis.json
```

The analysis mode provides:
- Color-coded tables showing data structure
- Column statistics and top values
- Data quality metrics
- Rich terminal formatting for better readability

### Export to CSV

```bash
# Export to CSV using config file database connection
ll2cz --csv output.csv

# Or with explicit database connection
ll2cz --input "postgresql://user:pass@host:5432/litellm_db" --csv output.csv
```

### Stream to CloudZero AnyCost API

```bash
# Stream to CloudZero using config file settings
ll2cz

# Or with explicit values (overrides config file)
ll2cz --input "postgresql://user:pass@host:5432/litellm_db" \
  --cz-api-key "your-cloudzero-api-key" \
  --cz-connection-id "your-connection-id"
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