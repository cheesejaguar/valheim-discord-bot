# GitHub Actions Workflows

This directory contains GitHub Actions workflows for automated testing and CI/CD.

## Workflows

### 1. `test.yml` - Basic Test Workflow (Recommended)
- **Purpose**: Simple test workflow for basic validation
- **Triggers**: Push to main/master, Pull requests
- **Features**:
  - Multi-Python version testing (3.9, 3.10, 3.11, 3.12)
  - Pytest and unittest execution
  - Code coverage reporting
  - Cached dependencies

### 2. `ci.yml` - Comprehensive CI Workflow
- **Purpose**: Full CI pipeline with linting, security, and Docker testing
- **Triggers**: Push to main/master, Pull requests
- **Features**:
  - All features from `test.yml`
  - Code linting (flake8, black, isort, mypy)
  - Security scanning (bandit, safety)
  - Docker image building and testing
  - Coverage upload to Codecov

### 3. `tests.yml` - Legacy Test Workflow
- **Purpose**: Simple test workflow (alternative to `test.yml`)
- **Triggers**: Push to main/master, Pull requests
- **Features**:
  - Basic pytest execution
  - Coverage reporting

## Usage

### Status Badges

Add these badges to your README.md:

```markdown
![Tests](https://github.com/your-org/valheim-discord-bot/workflows/Test/badge.svg)
![CI](https://github.com/your-org/valheim-discord-bot/workflows/CI/badge.svg)
```

### Local Development

Before pushing, run the development checks locally:

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run all checks
python scripts/dev.py

# Or use the bash script
./scripts/dev.sh
```

## Configuration

The workflows use the following configuration files:
- `pytest.ini` - Pytest configuration
- `setup.cfg` - Linting tool configurations
- `pyproject.toml` - Modern Python tooling configuration
- `requirements-dev.txt` - Development dependencies

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure the `src/` directory structure is correct
2. **Coverage Failures**: Ensure tests cover all code paths (aim for 100%)
3. **Linting Errors**: Run `black src/ test/` and `isort src/ test/` to fix formatting
4. **Security Warnings**: Review bandit and safety reports for potential issues

### Workflow Selection

- **For Simple Projects**: Use `test.yml`
- **For Production Projects**: Use `ci.yml`
- **For Legacy Support**: Use `tests.yml` 