# Monarch CLI - Development Guide

## Project Overview

Monarch CLI is a terminal-based UI for power users to manage Monarch Money transactions efficiently. Built with Python using Textual for the UI and Polars for data processing.

## Development Setup

### Using uv (Required)

This project uses **uv** for package management and development. Do not use pip or other package managers.

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies in development mode
uv pip install -e ".[dev]"

# Run the TUI
uv run monarch-tui
# or
uv run python monarch_tui.py

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=monarch_tui --cov-report=html
```

### Project Structure

```
monarch-cli/
├── monarch_tui/              # Main package
│   ├── monarchmoney.py       # GraphQL client (keep separate for upstream diffs)
│   ├── app.py                # Main Textual application
│   ├── data_manager.py       # Data layer with Polars
│   ├── state.py              # App state with undo/redo
│   ├── credentials.py        # Encrypted credential storage
│   ├── keybindings.py        # Keyboard shortcuts
│   ├── widgets/              # Custom UI widgets
│   ├── views/                # View components
│   └── styles/               # Textual CSS
├── tests/                    # Test suite
│   ├── conftest.py           # Pytest fixtures
│   ├── mock_backend.py       # Mock MonarchMoney API
│   ├── test_state.py         # State management tests
│   ├── test_data_manager.py  # Data operations tests
│   └── test_workflows.py     # Edit workflow tests
├── monarchmoney/             # Copy of upstream library
├── pyproject.toml            # Project metadata and dependencies
├── README.md                 # User documentation
└── CLAUDE.md                 # This file - development guide
```

## Testing Strategy

**IMPORTANT**: All business logic must be tested before running against real data.

### Testing Architecture

1. **Mock Backend**: `tests/mock_backend.py` provides a `MockMonarchMoney` class that simulates the API without making real network calls.

2. **Test Fixtures**: `tests/conftest.py` provides reusable test data and fixtures.

3. **Separation of Concerns**:
   - `state.py`: Pure state management (no I/O) - easily testable
   - `data_manager.py`: Takes MonarchMoney instance via dependency injection - can use mock
   - UI layer: Testable with Textual pilot tests

### What We Test

- ✅ State management: undo/redo, change tracking
- ✅ Data operations: aggregation, filtering, search
- ✅ Edit workflows: merchant rename, category change, hide toggle
- ✅ Bulk operations: multi-select, bulk edit
- ✅ Duplicate detection: finding and handling duplicates
- ✅ Edge cases: empty datasets, invalid data, API failures

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_state.py

# Run with coverage report
uv run pytest --cov=monarch_tui --cov-report=html

# Run tests matching a pattern
uv run pytest -k "test_undo"

# Verbose output
uv run pytest -v
```

### Test-Driven Development Workflow

1. Write tests first for new features
2. Run tests to verify they fail
3. Implement the feature
4. Run tests to verify they pass
5. Refactor while keeping tests green

## Code Style

- Use type hints for all function signatures
- Document complex logic with comments
- Keep functions focused and single-purpose
- Use meaningful variable names

## Making Changes to monarchmoney.py

The `monarchmoney.py` file is kept separate to make it easy to generate diffs for upstream contributions:

```bash
# Generate a diff against the original
cd monarch_tui
diff monarchmoney.py /path/to/original/monarchmoney.py > my_changes.patch
```

## Security Notes

- Credentials are encrypted with Fernet (AES-128)
- Never commit `.mm/` directory (session data)
- Never commit test data with real credentials
- See SECURITY.md for full security documentation

## Common Tasks

### Adding a New Feature

1. Create tests in `tests/test_*.py`
2. Implement in appropriate module
3. Update keyboard shortcuts in `keybindings.py`
4. Update README.md with new functionality
5. Run full test suite

### Debugging

```bash
# Enable Textual dev tools
uv run textual console

# Then in another terminal
uv run python monarch_tui.py

# View logs in the console
```

### Updating Dependencies

```bash
# Add new dependency
uv pip install package-name

# Update pyproject.toml
# Then regenerate requirements
uv pip compile pyproject.toml -o requirements.txt
```

## Git Workflow

```bash
# Commit after each logical unit of work
git add -A
git commit -m "Descriptive commit message"

# Use conventional commit format
# feat: New feature
# fix: Bug fix
# test: Adding tests
# refactor: Code refactoring
# docs: Documentation updates
```

## Performance Considerations

- Bulk fetch transactions on startup (1000 per batch)
- All aggregations done locally with Polars
- Batch API updates to minimize round trips
- Cache data in AppState to avoid re-fetching

## Known Issues / TODOs

- [ ] Add transaction deletion with confirmation
- [ ] Implement time range picker UI
- [ ] Add CSV export functionality
- [ ] Improve duplicate detection algorithm
- [ ] Add split transaction support
- [ ] Implement transaction notes editing
