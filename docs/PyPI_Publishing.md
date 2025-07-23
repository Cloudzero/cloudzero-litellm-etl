# PyPI Publishing Guide

This guide covers how to securely publish `ll2cz` to PyPI using modern best practices.

## 🔐 Secure PyPI Credential Storage

### 1. Create PyPI API Token (Recommended)

**Never use your PyPI password directly.** Instead, use API tokens:

1. Go to https://pypi.org/manage/account/token/
2. Click "Add API token"
3. Name: `ll2cz-package`
4. Scope: "Entire account" (initially, then scope to specific project after first upload)
5. Copy the token (starts with `pypi-`)

### 2. Store Credentials Securely

#### Option A: Environment Variables (Recommended for CI/CD)
```bash
# Add to your shell profile (~/.zshrc, ~/.bashrc, etc.)
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-AgEIcHlwaS5vcmcC... # Your actual token
```

#### Option B: Keyring (Recommended for Local Development)
```bash
# Install keyring support
uv add --dev keyring

# Store credentials securely in system keyring
uv run keyring set https://upload.pypi.org/legacy/ __token__
# Enter your API token when prompted
```

#### Option C: `.pypirc` File (Less Secure)
Create `~/.pypirc`:
```ini
[distutils]
index-servers = pypi

[pypi]
username = __token__
password = pypi-AgEIcHlwaS5vcmcC...  # Your actual token
```

**Important:** If using `.pypirc`, set secure permissions:
```bash
chmod 600 ~/.pypirc
```

### 3. Scoped API Tokens (After First Upload)

After your first successful upload:

1. Go to https://pypi.org/manage/project/ll2cz/settings/
2. Create a new API token scoped only to the `ll2cz` project
3. Replace your account-wide token with the project-scoped one
4. Delete the account-wide token

## 🚀 Publishing Process

### 1. Install Publishing Tools
```bash
# Add publishing dependencies
uv add --dev twine
```

### 2. Build the Package
```bash
# Clean previous builds
rm -rf dist/

# Build with uv
uv build
```

### 3. Check the Build
```bash
# Verify package contents
uv run twine check dist/*

# Test installation
uv run --with dist/ll2cz-0.1.0-py3-none-any.whl -- ll2cz --help
```

### 4. Upload to Test PyPI (Recommended First)
```bash
# Upload to Test PyPI first
uv run twine upload --repository testpypi dist/*

# Test installation from Test PyPI
uv run --with --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ ll2cz -- ll2cz --help
```

### 5. Upload to PyPI
```bash
# Upload to production PyPI
uv run twine upload dist/*
```

### 6. Verify Installation
```bash
# Test installation from PyPI
uv run --with ll2cz -- ll2cz --help
```

## 🔄 Automated Publishing (GitHub Actions)

Create `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    environment: publishing
    permissions:
      id-token: write  # For trusted publishing
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Install uv
      uses: astral-sh/setup-uv@v3
      with:
        version: "latest"
    
    - name: Set up Python
      run: uv python install 3.12
    
    - name: Build package
      run: uv build
    
    - name: Publish to PyPI
      uses: pypa/gh-action-pypi-publish@release/v1
      with:
        password: ${{ secrets.PYPI_API_TOKEN }}
```

**Store your API token in GitHub Secrets:**
1. Go to your repo → Settings → Secrets and variables → Actions
2. Add new secret: `PYPI_API_TOKEN`
3. Paste your PyPI API token

## 🎯 Version Management

### Semantic Versioning
Follow semantic versioning (semver.org):
- `MAJOR.MINOR.PATCH` (e.g., `1.2.3`)
- `MAJOR`: Breaking changes
- `MINOR`: New features (backward compatible)
- `PATCH`: Bug fixes (backward compatible)

### Update Version
Edit `pyproject.toml`:
```toml
[project]
version = "0.2.0"  # Update this
```

### Tag Releases
```bash
# Create and push version tag
git tag v0.2.0
git push origin v0.2.0
```

## 🛡️ Security Best Practices

### 1. API Token Security
- ✅ Use API tokens, not passwords
- ✅ Scope tokens to specific projects
- ✅ Rotate tokens regularly (every 6-12 months)
- ✅ Use different tokens for different environments
- ❌ Never commit tokens to version control
- ❌ Never share tokens in plain text

### 2. Build Security
```bash
# Always check builds before uploading
uv run twine check dist/*

# Use Test PyPI for testing
uv run twine upload --repository testpypi dist/*
```

### 3. 2FA and Account Security
- Enable 2FA on your PyPI account
- Use a strong, unique password
- Monitor your account for unauthorized uploads

## 🔍 Troubleshooting

### Common Issues

#### Authentication Failed
```bash
# Check your credentials
uv run twine check dist/*

# Test with verbose output
uv run twine upload --verbose dist/*
```

#### Package Already Exists
- You cannot overwrite existing versions on PyPI
- Increment version number in `pyproject.toml`
- Rebuild and upload

#### Build Failures
```bash
# Clean and rebuild
rm -rf dist/ build/
uv build
```

### Useful Commands
```bash
# Check package metadata
uv run twine check dist/*

# List package contents
tar -tzf dist/ll2cz-0.1.0.tar.gz

# Check wheel contents
unzip -l dist/ll2cz-0.1.0-py3-none-any.whl
```

## 📚 Additional Resources

- [PyPI Help](https://pypi.org/help/)
- [Twine Documentation](https://twine.readthedocs.io/)
- [Python Packaging Guide](https://packaging.python.org/)
- [uv Documentation](https://docs.astral.sh/uv/)