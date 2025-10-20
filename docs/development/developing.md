# Developing moneyflow

This guide covers the essential development workflow for contributing to moneyflow.

## Quick Start

```bash
# Clone repository
git clone https://github.com/wesm/moneyflow.git
cd moneyflow

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies (creates .venv)
uv sync

# Run the app in demo mode
uv run moneyflow --demo

# Run tests
uv run pytest -v

# Run type checker
uv run pyright moneyflow/
```

## Development Environment

**Required:**
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) - Package manager

**Optional:**
- VS Code or PyCharm with Python extension

## Development Workflow

### Working on Documentation

To preview documentation changes locally with live reload:

```bash
# Serve docs with live reload (auto-refreshes on file changes)
uv run mkdocs serve --livereload

# Then open http://127.0.0.1:8000 in your browser
# Edit files in docs/ and see changes instantly
```

**Note:** The `--livereload` flag is important - without it, changes won't auto-refresh in the browser.

### Before Starting Work

```bash
git pull
uv sync
uv run pytest -v  # Ensure clean starting point
```

### Making Changes

```bash
# Make your changes

# Run tests
uv run pytest -v

# Check types (for new code)
uv run pyright moneyflow/

# Commit
git add -A
git commit -m "your message"
```

### Running Tests

```bash
# All tests
uv run pytest -v

# Specific file
uv run pytest tests/test_data_manager.py -v

# Stop on first failure
uv run pytest -x

# With coverage
uv run pytest --cov --cov-report=html
open htmlcov/index.html
```

## CI/CD

Tests run automatically on every push and pull request:
- Python 3.11, 3.12 compatibility
- Full test suite
- Type checking with pyright

See `.github/workflows/test.yml` for details.

## Release Process

```bash
# 1. Bump version in pyproject.toml

# 2. Test build
uv build

# 3. Publish to PyPI
uv publish

# 4. Push to GitHub
git push && git push --tags
```

## Troubleshooting

**Tests fail after `git pull`:**
```bash
uv sync
uv pip install -e .
```

**Import errors:**
```bash
find . -type d -name __pycache__ -exec rm -rf {} +
uv sync --reinstall
```

## Getting Help

- **Bugs**: [Open an issue](https://github.com/wesm/moneyflow/issues)
- **Questions**: [Start a discussion](https://github.com/wesm/moneyflow/discussions)
- **Contributing**: See [Contributing Guide](contributing.md)
