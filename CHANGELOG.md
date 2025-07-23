# Changelog

All notable changes to the LiteLLM CloudZero ETL project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- CONTRIBUTING.md with comprehensive development guidelines
- CHANGELOG.md for tracking project changes
- SECURITY.md for vulnerability reporting process

### Changed
- Enhanced transmission output to show API operation being used (`replace_hourly` or `sum`)
- Improved date filter display to show human-readable description instead of raw JSON

## [0.1.1] - 2025-01-23

### Changed
- Migrated from psycopg2-binary to psycopg[binary] (psycopg3) for improved performance and modern PostgreSQL features
- Updated database connection type annotations to use psycopg.Connection
- Updated all command default limits to 10,000 for consistent data loading behavior

## [0.1.0] - 2025-01-19

### Added
- Initial release of LiteLLM CloudZero ETL tool
- PostgreSQL database connection and data extraction from LiteLLM tables
- CloudZero Resource Name (CZRN) generation for cost attribution
- CloudZero Billing Format (CBF) data transformation
- CloudZero AnyCost API integration with batched transmission
- SQLite caching layer with offline support and automatic freshness detection
- Rich terminal output with formatted tables and progress indicators
- Configuration management via `~/.ll2cz/config.yml`
- Multiple CLI commands for analysis, transformation, and transmission

#### Core Features
- **Data Analysis**: Comprehensive spend analysis by teams, users, models, and providers
- **CZRN Analysis**: Resource name generation with error reporting and validation
- **Data Transformation**: LiteLLM to CloudZero CBF format conversion
- **Transmission Modes**: Day, month, and all-data transmission with timezone support
- **Caching System**: Intelligent SQLite cache with server freshness checking
- **Configuration**: Interactive config management with validation

#### CLI Commands
- `ll2cz transform` - Transform LiteLLM data to CBF format
- `ll2cz transmit` - Send data to CloudZero AnyCost API
- `ll2cz analyze data` - General data analysis and raw table viewing
- `ll2cz analyze czrn` - CZRN generation analysis with error reporting
- `ll2cz analyze spend` - Spending pattern analysis by entities and models
- `ll2cz analyze schema` - Database schema discovery and documentation
- `ll2cz config` - Configuration management (example, status, edit)
- `ll2cz cache` - Cache management (status, clear, refresh)

#### Technical Implementation
- Modern Python project structure with `src/` layout
- Type hints and comprehensive error handling
- Apache 2.0 license with proper headers in all source files
- Polars for high-performance data processing
- Rich library for enhanced terminal output
- Typer for modern CLI interface
- HTTPX for async HTTP requests
- Comprehensive test suite with pytest

#### Database Support
- PostgreSQL connection for LiteLLM database access
- Support for `LiteLLM_DailyUserSpend`, `LiteLLM_DailyTeamSpend`, and `LiteLLM_DailyTagSpend` tables
- Unified data querying with entity type differentiation
- Automatic schema discovery and documentation generation

#### CZRN Implementation
- Format: `czrn:litellm:{provider}:cross-region:{entity_id}:llm-usage:{model}`
- Entity-based ownership using team_id or user_id as owner-account-id
- Provider and service-type field mapping for accurate resource identification
- Comprehensive error reporting with full database record display

#### Caching Architecture
- SQLite-based local cache in `~/.ll2cz/cache/`
- Automatic server freshness detection and cache refresh
- Offline mode support with stale data warnings
- Record count and timestamp-based freshness validation

### Technical Details

#### Dependencies
- **Python**: 3.11+
- **Core Libraries**: polars, rich, typer, httpx, psycopg2-binary
- **Development**: pytest, build tools via uv package manager

#### Configuration
- YAML-based configuration file support
- CLI argument priority over config file values
- Interactive configuration editor with validation
- Secure handling of API keys and database credentials

#### Data Processing
- Filtering of records with zero successful requests
- Timezone-aware date handling and processing
- Numeric formatting optimized for CloudZero API requirements
- Comprehensive data validation and error reporting

### Documentation
- Comprehensive README with installation and usage instructions
- Technical documentation for CZRN implementation
- Complete database schema documentation
- API reference and configuration guides

### Security
- Sensitive data exclusion via comprehensive .gitignore
- API key masking in configuration display
- Secure credential handling and storage
- No hardcoded secrets or credentials

---

## Release Types

### Added
For new features.

### Changed
For changes in existing functionality.

### Deprecated
For soon-to-be removed features.

### Removed
For now removed features.

### Fixed
For any bug fixes.

### Security
In case of vulnerabilities.