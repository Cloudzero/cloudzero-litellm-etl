# Changelog

All notable changes to the LiteLLM CloudZero ETL project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.6.2] - 2025-01-29

### Added
- **Transmit module refactoring** for improved maintainability and testability
  - Split monolithic `DataTransmitter` into focused components with single responsibilities
  - Introduced dependency injection for all components
  - Created protocol-based design with `OutputHandler` and `Transmitter` interfaces
  - Added test-friendly implementations: `NullOutput`, `MockTransmitter`, `CollectingOutput`
  - Comprehensive test suite with 27 new tests demonstrating improved testability
  - Full backward compatibility maintained
- **CI/CD safe smoke tests** for all CLI commands
  - Updated smoke tests to not require real database connections
  - All tests now safe for automated CI/CD pipelines
- **PII obfuscation in test data**
  - Anonymized all names, emails, and API keys in test.sqlite
  - Updated create_test_sqlite.py script to generate only anonymized test data
  - Reviewed entire codebase to ensure no PII is present

### Changed
- Updated CLI to use refactored transmit module (`transmit_refactored.py`)
- Fixed CLI error handling to properly exit with error code when transmit fails
- Improved BatchAnalyzer to correctly group data by date in refactored transmit module

### Fixed
- Fixed date filtering in SQLite implementation for data source strategies
- Fixed CLI mode mapping to correctly handle 'today', 'yesterday', 'date-range' modes

### Testing
- All 97 tests passing including new refactored transmit tests
- SQLite integration fully tested with transmit functionality
- All smoke tests are now CI/CD safe

## [0.6.1] - 2025-01-28

### Fixed
- Fixed import error in `data_processor.py` - `extract_model_name` now correctly imported from `model_name_strategies`
- Added `__main__.py` to enable running package as module: `python -m ll2cz`

### Added
- **SQLite database support** - All commands now accept `sqlite://` connection strings
- Comprehensive import tests (`test_imports.py`) to prevent future import errors
- CLI smoke tests (`test_cli_smoke.py`) to ensure all commands work without crashing
- Tests for all critical imports and circular dependency detection
- `scripts/create_test_sqlite.py` to generate test SQLite databases with sample data
- SQLite-specific tests (`test_sqlite.py`) for database functionality

### Testing
- Verified all CLI commands work correctly: `transmit`, `analyze`, `transform`, `cache`, `config`
- All 21 core tests passing
- All 24 new tests passing (import, smoke, and SQLite tests)
- SQLite support tested with both test databases and production-like schemas

## [0.6.0] - 2025-01-28

### Changed
- Expanded Python version support to include Python 3.9+
  - Updated type annotations to use typing module imports instead of Python 3.10+ syntax
  - Changed `dict[str, Any]` to `Dict[str, Any]`, `list[T]` to `List[T]`, etc.
  - Changed `T | None` to `Optional[T]` for compatibility
  - Updated pyproject.toml to require Python >=3.9
  - Added Python version classifiers for 3.9, 3.10, 3.11

## [0.5.1] - 2025-01-28

### Changed
- Renamed repository from `cloudzero-litellm-etl` to `cloudzero-litellm-toolkit`
  - Updated all GitHub URLs in pyproject.toml
  - Updated repository references in README.md
  - Updated Git remote URL to reflect new name

### Fixed
- Exclude None values from CBF line item tags to prevent invalid tag values
  - Updated `CBFBuilder.with_resource_tags()` to filter out None values
  - Enhanced `transform.py` to exclude None, empty strings, and 'N/A' values from resource tags
  - Added comprehensive test coverage for None value exclusion

## [0.5.0] - 2025-01-27

### Changed
- Major refactoring for improved maintainability and performance
- Reorganized code structure with dedicated modules for specific functionality
- Enhanced error handling and logging throughout the codebase
- Improved type hints and documentation

### Added
- Dedicated `cbf_builder.py` module with builder pattern for CBF record construction
- Specialized error tracking module for better debugging
- Enhanced transformation pipeline with clearer separation of concerns

## [0.4.0] - 2025-01-26

### Added
- Comprehensive cost comparison analysis features
- SpendLogs table support for detailed spend tracking
- Enhanced analysis commands with more detailed reporting options
- Cost trend analysis and anomaly detection capabilities

### Changed
- Improved data analysis output formatting
- Enhanced spend analysis with better grouping and aggregation
- Updated CLI commands for better user experience

## [0.3.0] - 2025-01-25

### Changed
- Updated CBF schema mappings for better CloudZero compatibility
- Enhanced model name extraction algorithm to handle more edge cases
- Improved CZRN generation with better normalization
- Updated resource field mappings to align with CloudZero's latest requirements

### Fixed
- Model name extraction now properly handles version suffixes
- CZRN generation correctly handles special characters
- Fixed edge cases in provider normalization

## [0.2.1] - 2025-01-24

### Fixed
- Fixed all tests and linting issues after CZRN/CBF mapping changes
- Corrected CZRN/CBF mapping to use key_alias or api_key for owner-account-id
- Fixed import issues and type annotations

### Changed
- Updated entity identification logic for better accuracy
- Improved error messages for configuration issues

## [0.2.0] - 2025-01-24

### Added
- CONTRIBUTING.md with comprehensive development guidelines
- CHANGELOG.md for tracking project changes
- SECURITY.md for vulnerability reporting process
- PyPI package publishing support
- Comprehensive CLI documentation

### Changed
- Enhanced transmission output to show API operation being used (`replace_hourly` or `sum`)
- Improved date filter display to show human-readable description instead of raw JSON
- Updated package structure for PyPI distribution
- Improved README with installation instructions from PyPI

### Fixed
- Configuration command syntax in documentation
- Various documentation inconsistencies

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