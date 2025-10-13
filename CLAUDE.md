# moneyflow - Development Guide

## Project Overview

moneyflow is a terminal-based UI for power users to manage personal finance transactions efficiently. Built with Python using Textual for the UI and Polars for data processing. Supports multiple backends including Monarch Money, with more platforms planned (YNAB, Lunch Money, etc.).

## Development Setup

### Using uv (REQUIRED)

**IMPORTANT**: This project uses **uv** exclusively for all development workflows. Always use `uv run` for executing scripts and `uv pip` for package management. Never use pip, pipenv, poetry, or other package managers.

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# FIRST TIME SETUP: Sync dependencies (includes dev dependencies for testing)
uv sync

# This creates a virtual environment and installs all dependencies
# You MUST run this before running tests or the TUI for the first time

# After sync, run the TUI
uv run moneyflow

# Run tests (ALWAYS before committing)
uv run pytest

# Run tests with coverage
uv run pytest --cov --cov-report=html

# View coverage report
open htmlcov/index.html
```

**If you get `ModuleNotFoundError`**: Run `uv sync` first!

### Test-Driven Development (CRITICAL)

**This project handles financial data. We cannot afford slip-ups.**

**MANDATORY WORKFLOW**:
1. **Write tests first** for any new feature or bug fix
2. **Run tests** - verify they fail as expected
3. **Implement** the feature/fix
4. **Run tests again** - verify all tests pass
5. **Check coverage** - ensure new code is tested
6. **Only commit when tests are green**

**Before EVERY commit**:
```bash
# Run full test suite
uv run pytest -v

# Run type checker
uv run pyright moneyflow/

# Check coverage
uv run pytest --cov --cov-report=term-missing
```

**All tests must pass and type checking must be clean before committing.** No exceptions.

### Project Structure

**IMPORTANT**: All Python source code must be in the `moneyflow/` package. No Python files should live at the top level.

```
moneyflow/
├── moneyflow/                   # Main package (ALL code goes here)
│   ├── app.py                   # Main Textual application (~1750 lines)
│   ├── monarchmoney.py          # GraphQL client (keep separate for upstream diffs)
│   ├── data_manager.py          # Data layer with Polars
│   ├── state.py                 # App state management
│   ├── credentials.py           # Encrypted credential storage
│   ├── duplicate_detector.py    # Duplicate detection
│   ├── view_presenter.py        # Presentation logic (NEW - fully typed & tested)
│   ├── time_navigator.py        # Time period calculations (NEW - 100% coverage)
│   ├── commit_orchestrator.py   # DataFrame update logic (NEW - critical, 100% tested)
│   ├── backends/                # Backend implementations
│   ├── screens/                 # UI screens and modals
│   ├── widgets/                 # Custom UI widgets
│   └── styles/                  # Textual CSS
├── tests/                       # Test suite (465+ tests)
│   ├── conftest.py              # Pytest fixtures
│   ├── mock_backend.py          # Mock MonarchMoney API
│   ├── test_state.py            # State management tests
│   ├── test_data_manager.py     # Data operations tests
│   ├── test_view_presenter.py   # Presentation logic tests (NEW - 48 tests)
│   ├── test_time_navigator.py   # Time navigation tests (NEW - 52 tests)
│   ├── test_commit_orchestrator.py  # DataFrame updates (NEW - 30 tests)
│   └── test_workflows.py        # Edit workflow tests
├── pyproject.toml               # Project metadata and dependencies
├── README.md                    # User documentation
└── CLAUDE.md                    # This file - development guide
```

**File Organization Rules**:
- ✅ All business logic in `moneyflow/` package
- ✅ All tests in `tests/` directory
- ✅ Entry point via `moneyflow` command (configured in pyproject.toml)
- ❌ No `.py` files at top level
- ❌ No duplicate files between top-level and package

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
- ✅ **Presentation logic**: View formatting, flag computation (100% coverage)
- ✅ **Time navigation**: Date calculations, leap years, boundaries (100% coverage)
- ✅ **DataFrame updates**: Critical commit logic (100% coverage)
- ✅ Edge cases: empty datasets, invalid data, API failures

### Running Tests

**ALWAYS use `uv run` for running tests:**

```bash
# Run all tests (run before EVERY commit)
uv run pytest -v

# Run with coverage report
uv run pytest --cov --cov-report=html --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_state.py -v

# Run tests matching a pattern
uv run pytest -k "test_undo" -v

# Run and stop on first failure
uv run pytest -x

# Run and show local variables on failure
uv run pytest -l
```

### Coverage Requirements

**Business Logic Coverage Target: >90%**

Core modules must maintain high coverage:
- `state.py`: State management (target: 90%+, current: 85%)
- `data_manager.py`: Data operations and API integration (target: 90%+, current: 97%)
- `duplicate_detector.py`: Duplicate detection (target: 95%+, current: 84%)
- `view_presenter.py`: Presentation logic (**100% - keep at 100%**)
- `time_navigator.py`: Time period calculations (**100% - keep at 100%**)
- `commit_orchestrator.py`: DataFrame updates (**100% - CRITICAL, keep at 100%**)

UI layer coverage is less critical but still valuable.

View coverage report:
```bash
uv run pytest --cov --cov-report=html
open htmlcov/index.html
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
cd moneyflow
diff monarchmoney.py /path/to/original/monarchmoney.py > my_changes.patch
```

## Security Notes

- Credentials are encrypted with Fernet (AES-128)
- Never commit `.mm/` directory (session data)
- Never commit `~/.moneyflow/` directory (encrypted credentials)
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
# Add new dependency to pyproject.toml manually, then:
uv sync

# Or add directly
uv add package-name

# Update all dependencies
uv lock --upgrade
uv sync
```

## Git Workflow

**CRITICAL**: Never commit without running tests first!

```bash
# MANDATORY: Run tests before committing
uv run pytest -v

# Only if all tests pass, then commit
git add -A
git commit -m "Descriptive commit message"

# Use conventional commit format
# feat: New feature
# fix: Bug fix
# test: Adding tests
# refactor: Code refactoring
# docs: Documentation updates
```

**Pre-commit Checklist**:
- [ ] All tests pass (`uv run pytest -v`)
- [ ] Type checking passes (`uv run pyright moneyflow/`)
- [ ] Coverage hasn't decreased
- [ ] No debug print statements left in code
- [ ] Updated tests for any changed behavior
- [ ] Ran with real test data if changing API logic

### Static Type Checking (NEW)

**Pyright** is integrated for static type analysis. Use comprehensive type hints for all new code.

```bash
# Type-check specific module
uv run pyright moneyflow/view_presenter.py

# Type-check all application code
uv run pyright moneyflow/

# Type checking is also run in CI on every push
```

**Type Hint Requirements**:
- All function signatures must have full type hints
- Use `TypedDict` for complex dictionaries
- Use `Literal` types for string enums
- Use `NamedTuple` for data transfer objects
- Prefer `Callable[[Args], Return]` for function types

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
