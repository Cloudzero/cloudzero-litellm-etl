# ll2cz CLI Reference

Complete command-line interface reference for the LiteLLM to CloudZero ETL tool.

## Global Options

```bash
ll2cz [OPTIONS] COMMAND [ARGS]...
```

### Global Options
- `--version` - Show version and exit
- `--help` - Show help message and exit

## Commands Overview

- [`transform`](#transform) - Transform LiteLLM data to CloudZero CBF format
- [`transmit`](#transmit) - Send data to CloudZero AnyCost API
- [`config`](#config) - Configuration management
- [`cache`](#cache) - Cache management
- [`analyze`](#analyze) - Data analysis and exploration

---

## transform

Transform LiteLLM database data into CloudZero AnyCost CBF format.

```bash
ll2cz transform [OPTIONS]
```

### Options
- `--input TEXT` - LiteLLM PostgreSQL database connection URL
- `--output TEXT` - Output CSV file name  
- `--screen` - Display transformed data on screen in formatted table
- `--limit INTEGER` - Limit number of records for screen output (default: 50)

### Examples
```bash
# Display data on screen (formatted table)
ll2cz transform --input "postgresql://user:pass@host:5432/litellm_db" --screen

# Export to CSV file
ll2cz transform --input "postgresql://user:pass@host:5432/litellm_db" --output data.csv

# Limit records for screen display
ll2cz transform --screen --limit 25

# Use config file for database connection
ll2cz transform --output data.csv
```

---

## transmit

Transform LiteLLM data and transmit to CloudZero AnyCost API.

```bash
ll2cz transmit [OPTIONS] MODE [DATE_SPEC]
```

### Arguments
- `MODE` - Transmission mode: `day`, `month`, or `all` (required)
- `DATE_SPEC` - Date specification (optional):
  - For `day` mode: DD-MM-YYYY format (e.g., 15-01-2024)
  - For `month` mode: MM-YYYY format (e.g., 01-2024)
  - For `all` mode: ignored

### Options
- `--input TEXT` - LiteLLM PostgreSQL database connection URL
- `--cz-api-key TEXT` - CloudZero API key
- `--cz-connection-id TEXT` - CloudZero connection ID
- `--append` - Use 'sum' operation instead of 'replace_hourly'
- `--timezone TEXT` - Timezone for date handling (default: UTC)
- `--test` - Test mode: show payloads without sending (5 records only)
- `--limit INTEGER` - Limit number of records to process

### Modes

#### Day Mode
Send data for a specific day.

```bash
# Send today's data
ll2cz transmit day

# Send specific day's data
ll2cz transmit day 15-01-2024

# Send today's data with timezone
ll2cz transmit day --timezone "US/Eastern"
```

#### Month Mode
Send data for a specific month.

```bash
# Send current month's data
ll2cz transmit month

# Send specific month's data
ll2cz transmit month 01-2024

# Send month data in append mode
ll2cz transmit month 01-2024 --append
```

#### All Mode
Send all available data, batched by day.

```bash
# Send all data
ll2cz transmit all

# Send all data with record limit
ll2cz transmit all --limit 10000
```

### Test Mode
Test mode processes only 5 records and shows JSON payloads without transmitting.

```bash
# Test today's transmission
ll2cz transmit day --test

# Test specific month with API keys still required
ll2cz transmit month 01-2024 --test --cz-api-key "key" --cz-connection-id "id"
```

---

## config

Configuration management commands.

```bash
ll2cz config [OPTIONS] COMMAND [ARGS]...
```

### Subcommands

#### example
Create an example configuration file at ~/.ll2cz/config.yml.

```bash
ll2cz config example
```

#### status  
Show current configuration status.

```bash
ll2cz config status
```

#### edit
Interactively edit configuration values.

```bash
ll2cz config edit
```

### Configuration File

Configuration is stored in `~/.ll2cz/config.yml`:

```yaml
database_url: postgresql://user:password@host:5432/litellm_db
cz_api_key: your-cloudzero-api-key
cz_connection_id: your-connection-id
```

### Priority Order
1. CLI arguments (highest priority)
2. Configuration file
3. Default values (lowest priority)

---

## cache

Cache management commands for offline operation.

```bash
ll2cz cache [OPTIONS] COMMAND [ARGS]...
```

### Subcommands

#### status
Show cache status and information.

```bash
ll2cz cache status [OPTIONS]
```

Options:
- `--input TEXT` - Database connection URL
- `--remote-check` - Perform remote server checks and show detailed status

```bash
# Check cache status (local only)
ll2cz cache status

# Check cache status with remote server verification
ll2cz cache status --remote-check
```

#### clear
Clear the local cache.

```bash
ll2cz cache clear [OPTIONS]
```

Options:
- `--input TEXT` - Database connection URL

```bash
ll2cz cache clear
```

#### refresh
Force refresh the cache from server.

```bash
ll2cz cache refresh [OPTIONS]
```

Options:
- `--input TEXT` - Database connection URL

```bash
ll2cz cache refresh
```

---

## analyze

Analysis and data exploration commands.

```bash
ll2cz analyze [OPTIONS] COMMAND [ARGS]...
```

### Subcommands

#### data
Analyze LiteLLM database data and show insights, or display raw data tables.

```bash
ll2cz analyze data [OPTIONS]
```

Options:
- `--input TEXT` - Database connection URL
- `--limit INTEGER` - Number of records to analyze (default: 10000)
- `--json TEXT` - JSON output file for analysis results
- `--show-raw` - Show raw data tables instead of analysis
- `--table TEXT` - Show specific table only (for --show-raw): 'user', 'team', 'tag', or 'all'

```bash
# General data analysis
ll2cz analyze data --limit 10000

# Show raw table data
ll2cz analyze data --show-raw --table all

# Show specific table only
ll2cz analyze data --show-raw --table user

# Use cache commands to refresh
ll2cz cache refresh

# Save analysis to JSON
ll2cz analyze data --json analysis.json
```

#### spend
Analyze spending patterns based on LiteLLM team and user data.

```bash
ll2cz analyze spend [OPTIONS]
```

Options:
- `--input TEXT` - Database connection URL
- `--limit INTEGER` - Number of records to analyze (default: 10000)

```bash
ll2cz analyze spend --limit 10000
```

#### schema
Discover and document all tables in the LiteLLM database.

```bash
ll2cz analyze schema [OPTIONS]
```

Options:
- `--input TEXT` - Database connection URL
- `--output TEXT` - Output file for schema documentation

```bash
# Display schema overview
ll2cz analyze schema

# Save complete schema documentation
ll2cz analyze schema --output schema_docs.md
```

---

## Common Workflows

### Initial Setup
```bash
# 1. Create configuration file
ll2cz config example

# 2. Edit configuration with your settings
ll2cz config edit

# 3. Verify configuration
ll2cz config status
```

### Data Exploration
```bash
# 1. Analyze your data
ll2cz analyze data --limit 1000

# 2. Check raw tables
ll2cz analyze data --show-raw --table all

# 3. Examine database schema
ll2cz analyze schema
```

### Data Transformation
```bash
# 1. Test transformation with screen output
ll2cz transform --screen --limit 10

# 2. Export to CSV for review
ll2cz transform --output sample.csv

# 3. Transmit test data
ll2cz transmit day --test
```

### Production Transmission
```bash
# 1. Send today's data
ll2cz transmit day

# 2. Send historical month
ll2cz transmit month 01-2024

# 3. Bulk send all data
ll2cz transmit all
```

---

## Error Handling

### Common Issues

#### Database Connection
```bash
# Error: --input (database connection) is required
# Solution: Set in config file or provide via CLI
ll2cz config example  # Create config file
# Or use CLI argument
ll2cz transform --input "postgresql://user:pass@host/db" --screen
```

#### Missing API Credentials
```bash
# Error: --cz-api-key and --cz-connection-id are required
# Solution: Set in config file or provide via CLI
ll2cz config edit  # Add credentials to config
# Or use CLI arguments
ll2cz transmit day --cz-api-key "key" --cz-connection-id "id"
```

#### Cache Issues
```bash
# Clear cache if corrupted
ll2cz cache clear

# Force refresh from server
ll2cz cache refresh

# Check cache status
ll2cz cache status --remote-check
```

### Offline Mode
When the database server is unavailable, ll2cz operates in offline mode using cached data:

```bash
# Check if in offline mode
ll2cz cache status

# Most commands work with cached data
ll2cz analyze data
ll2cz transform --screen
```

---

## Configuration Variables

### Environment Variables
You can also use environment variables instead of config file:

- `LL2CZ_DATABASE_URL` - Database connection URL
- `LL2CZ_CZ_API_KEY` - CloudZero API key  
- `LL2CZ_CZ_CONNECTION_ID` - CloudZero connection ID

### Priority Order
1. CLI arguments
2. Environment variables
3. Configuration file
4. Default values