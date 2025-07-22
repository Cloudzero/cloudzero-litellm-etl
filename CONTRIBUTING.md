# Contributing to LiteLLM CloudZero ETL

Thank you for your interest in contributing to the LiteLLM CloudZero ETL project! We welcome contributions from the community and appreciate your help in making this tool better.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contributing Process](#contributing-process)
- [Code Style and Standards](#code-style-and-standards)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Reporting Issues](#reporting-issues)
- [Code Review Process](#code-review-process)
- [Community Guidelines](#community-guidelines)

## Getting Started

Before contributing, please:

1. Read this document completely
2. Review our [Code of Conduct](CODE-OF-CONDUCT.md)
3. Check existing [issues](https://github.com/Cloudzero/litellm-cz-etl/issues) and [pull requests](https://github.com/Cloudzero/litellm-cz-etl/pulls)
4. Join our community discussions if available

## Development Setup

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) for dependency management
- Git for version control
- Access to a LiteLLM PostgreSQL database for testing (optional)

### Local Development Environment

1. **Fork and Clone the Repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/litellm-cz-etl.git
   cd litellm-cz-etl
   ```

2. **Set Up Python Environment**
   ```bash
   # Install dependencies using uv
   uv sync
   
   # Activate virtual environment
   source .venv/bin/activate
   ```

3. **Install in Development Mode**
   ```bash
   uv pip install -e .
   ```

4. **Verify Installation**
   ```bash
   ll2cz --help
   ```

5. **Set Up Configuration (Optional)**
   ```bash
   # Create example config
   ll2cz config example
   
   # Edit with your database credentials
   ll2cz config edit
   ```

### Project Structure

```
src/ll2cz/
├── __init__.py          # Package initialization and version
├── cli.py              # Command-line interface
├── database.py         # PostgreSQL database connection
├── cached_database.py  # SQLite caching layer
├── cache.py            # Cache management
├── analysis.py         # Data analysis and reporting
├── transform.py        # CBF data transformation
├── czrn.py            # CloudZero Resource Names
├── output.py          # CSV and API output
└── config.py          # Configuration management

tests/
├── test_czrn.py       # CZRN generation tests
├── test_transform.py  # Data transformation tests
└── test_output.py     # Output format tests
```

## Contributing Process

### 1. Choose What to Work On

- Check [open issues](https://github.com/Cloudzero/litellm-cz-etl/issues) for tasks
- Look for issues labeled `good first issue` for beginners
- Propose new features by opening an issue first

### 2. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 3. Make Your Changes

- Write clean, readable code following our style guidelines
- Add tests for new functionality
- Update documentation as needed
- Follow commit message conventions

### 4. Test Your Changes

```bash
# Run tests
uv run pytest

# Run specific test files
uv run pytest tests/test_czrn.py

# Run with coverage (if configured)
uv run pytest --cov=ll2cz
```

## Code Style and Standards

### Python Code Style

- Follow [PEP 8](https://pep8.org/) Python style guide
- Use [Black](https://black.readthedocs.io/) for code formatting (if configured)
- Use type hints where appropriate
- Write docstrings for public functions and classes

### Code Quality Guidelines

1. **Functions should be focused and do one thing well**
2. **Use descriptive variable and function names**
3. **Keep functions reasonably short (prefer < 50 lines)**
4. **Add comments for complex logic**
5. **Handle errors gracefully with proper exception handling**

### Documentation

- Update README.md if you change installation or usage
- Add docstrings to new functions and classes
- Update type hints for new parameters
- Include examples in docstrings where helpful

### Import Organization

```python
# Standard library imports
import json
from pathlib import Path
from typing import Optional

# Third-party imports
import polars as pl
from rich.console import Console

# Local imports
from .database import LiteLLMDatabase
from .config import Config
```

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test
uv run pytest tests/test_czrn.py::test_czrn_generation
```

### Writing Tests

- Write tests for new features and bug fixes
- Use descriptive test names that explain what is being tested
- Include both positive and negative test cases
- Test edge cases and error conditions

Example test structure:
```python
def test_czrn_generation_with_valid_data():
    """Test CZRN generation with valid LiteLLM data."""
    # Arrange
    data = create_test_data()
    
    # Act
    result = generate_czrn(data)
    
    # Assert
    assert result.startswith('czrn:litellm:')
    assert 'gpt-4' in result
```

## Submitting Changes

### Pull Request Process

1. **Ensure your branch is up to date**
   ```bash
   git checkout main
   git pull upstream main
   git checkout your-branch
   git rebase main
   ```

2. **Push your changes**
   ```bash
   git push origin your-branch
   ```

3. **Create a Pull Request**
   - Use a clear, descriptive title
   - Reference any related issues
   - Provide a detailed description of changes
   - Include testing instructions if applicable

### Pull Request Template

When creating a PR, please include:

```markdown
## Description
Brief description of changes

## Related Issues
Fixes #issue_number

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring

## Testing
- [ ] Tests pass locally
- [ ] New tests added for new functionality
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or breaking changes documented)
```

## Reporting Issues

### Bug Reports

When reporting bugs, please include:

1. **Clear description** of the issue
2. **Steps to reproduce** the problem
3. **Expected behavior** vs actual behavior
4. **Environment information**:
   - Python version
   - Operating system
   - Package version
   - Database version (if applicable)
5. **Error messages** or logs
6. **Minimal code example** that reproduces the issue

### Feature Requests

For feature requests:

1. **Describe the problem** you're trying to solve
2. **Explain the proposed solution**
3. **Consider alternative solutions**
4. **Assess the impact** on existing functionality

## Code Review Process

### For Contributors

- Be open to feedback and suggestions
- Respond promptly to review comments
- Make requested changes in a timely manner
- Ask questions if review feedback is unclear

### Review Criteria

Code reviews will evaluate:

- **Functionality**: Does the code work as intended?
- **Code Quality**: Is the code clean, readable, and maintainable?
- **Testing**: Are there adequate tests for the changes?
- **Documentation**: Is documentation updated appropriately?
- **Performance**: Are there any performance implications?
- **Security**: Are there any security concerns?

## Community Guidelines

### Be Respectful

- Use welcoming and inclusive language
- Respect differing viewpoints and experiences
- Accept constructive criticism gracefully
- Focus on what is best for the community

### Be Collaborative

- Help others learn and grow
- Share knowledge and expertise
- Provide constructive feedback
- Celebrate others' contributions

### Be Professional

- Keep discussions focused and on-topic
- Avoid personal attacks or inflammatory language
- Report inappropriate behavior to maintainers
- Follow our [Code of Conduct](CODE-OF-CONDUCT.md)

## Getting Help

If you need help:

1. Check the [README.md](README.md) for basic usage
2. Review existing [issues](https://github.com/Cloudzero/litellm-cz-etl/issues)
3. Open a new issue with the `question` label
4. Reach out to maintainers if needed

## License

By contributing to this project, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).

## Acknowledgments

Thank you for taking the time to contribute to the LiteLLM CloudZero ETL project! Your contributions help make this tool better for everyone in the community.