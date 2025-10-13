# Developing moneyflow

This guide covers the development workflow, tools, and best practices for contributing to moneyflow.

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

### Required Tools

- **Python 3.11+**: Required runtime
- **uv**: Package manager and runner (replaces pip/poetry/pipenv)
- **pyright**: Static type checker
- **pytest**: Test framework

### IDE Setup

**Recommended**: VS Code or PyCharm with Python extension

**VS Code settings** (`.vscode/settings.json`):
```json
{
  "python.linting.pylintEnabled": false,
  "python.linting.enabled": true,
  "python.linting.pyright Enabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false
}
```

## Development Workflow

### Before Starting Work

```bash
# Always start with latest code
git pull

# Sync dependencies
uv sync

# Run tests to ensure starting point is clean
uv run pytest -v
```

### Test-Driven Development (TDD)

**This project handles financial data. We follow strict TDD:**

1. **Write test first** - What should the code do?
2. **Run test** - It should fail
3. **Write minimal code** - Make it pass
4. **Refactor** - Clean up while keeping tests green
5. **Commit** - Only when all tests pass

### Pre-Commit Checklist

**Before EVERY commit**:

```bash
# 1. Run full test suite
uv run pytest -v

# 2. Run type checker
uv run pyright moneyflow/

# 3. Check coverage hasn't decreased
uv run pytest --cov --cov-report=term-missing

# 4. All must pass!
```

**Checklist**:
- [ ] All tests passing
- [ ] Type checking clean (new code only)
- [ ] Coverage ≥ 68%
- [ ] No debug print statements
- [ ] Docstrings added for public APIs

### Running Tests

```bash
# All tests
uv run pytest -v

# Specific file
uv run pytest tests/test_data_manager.py -v

# Specific test
uv run pytest tests/test_data_manager.py::TestAggregation::test_aggregate_by_merchant -v

# Pattern matching
uv run pytest -k "test_merchant" -v

# Stop on first failure
uv run pytest -x

# Show local variables on failure
uv run pytest -l

# With coverage
uv run pytest --cov --cov-report=html
open htmlcov/index.html
```

### Type Checking

```bash
# Check specific module
uv run pyright moneyflow/view_presenter.py

# Check all application code
uv run pyright moneyflow/

# Check tests too
uv run pyright moneyflow/ tests/
```

**Type Hint Requirements**:
- All function signatures must have type hints
- Use `TypedDict` for complex dictionaries
- Use `Literal` for string enums
- Use `NamedTuple` for data transfer objects
- Use `Callable[[Args], Return]` for function parameters

## Project Architecture

### Module Organization

```
moneyflow/
├── app.py                   # Main TUI application (UI layer)
├── state.py                 # Application state container
├── data_manager.py          # Data operations (API, aggregations)
├── view_presenter.py        # Presentation logic (pure functions)
├── time_navigator.py        # Date calculations (pure functions)
├── commit_orchestrator.py   # DataFrame updates (pure functions)
├── backends/                # Backend implementations
│   ├── base.py             # Abstract interface
│   ├── monarch.py          # Monarch Money backend
│   └── demo.py             # Demo mode backend
├── screens/                 # Modal screens
└── widgets/                 # Custom widgets
```

### Design Principles

**Separation of Concerns**:
- **UI Layer** (app.py, screens/, widgets/): Rendering and user interaction only
- **Business Logic** (view_presenter, time_navigator, commit_orchestrator): Pure functions, fully tested
- **Data Layer** (data_manager, backends): API operations, DataFrame transformations
- **State Layer** (state.py): Hold state, minimal logic

**Testability**:
- Business logic extracted to pure functions (no UI dependencies)
- Dependency injection for backends (allows mocking)
- State is data, not operations

**Type Safety**:
- Comprehensive type hints on all new code
- Static checking with pyright
- CI enforces type checking

## Adding New Features

### Example: Add a New View Mode

1. **Add enum value** (state.py):
```python
class ViewMode(Enum):
    TAG = "tag"  # New!
```

2. **Add aggregation** (data_manager.py):
```python
def aggregate_by_tag(self, df: pl.DataFrame) -> pl.DataFrame:
    return self._aggregate_by_field(df, "tag")
```

3. **Add tests** (tests/test_data_manager.py):
```python
def test_aggregate_by_tag(self):
    # Test here
```

4. **Add UI method** (app.py):
```python
def show_tag_aggregation(self) -> None:
    self._show_aggregation("tag", self.data_manager.aggregate_by_tag)
```

5. **Add keyboard binding** (app.py BINDINGS):
```python
Binding("T", "view_tags", "Tags"),
```

6. **Run tests**:
```bash
uv run pytest -v
uv run pyright moneyflow/
```

## Code Style

### Formatting
- Line length: 100 characters
- Use ruff for linting (configured in pyproject.toml)
- Follow PEP 8

### Naming Conventions
- Functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_leading_underscore`

### Documentation
- Module docstrings: Explain purpose and responsibilities
- Class docstrings: Describe what it does, key attributes
- Method docstrings: Args, Returns, Examples
- Complex logic: Inline comments explaining "why", not "what"

## Common Tasks

### Adding a Backend

1. Create `backends/mybackend.py`:
```python
from .base import FinanceBackend

class MyBackend(FinanceBackend):
    async def login(self, ...): ...
    async def get_transactions(self, ...): ...
    # Implement other methods
```

2. Register in `backends/__init__.py`:
```python
BACKENDS = {
    "monarch": MonarchBackend,
    "mybackend": MyBackend,  # Add here
}
```

3. Add tests in `tests/test_mybackend.py`

### Adding a Category

Categories are defined in `data_manager.py::CATEGORY_GROUPS`:

```python
CATEGORY_GROUPS = {
    "My Group": [
        "Category 1",
        "Category 2",
    ],
}
```

Changes take effect immediately (dynamically applied to cached data).

### Debugging

```bash
# Run with dev mode for detailed errors
uv run moneyflow --dev

# In another terminal, run Textual console
uv run textual console

# View logs in the console window
```

### Performance Profiling

```bash
# Run with Python profiler
python -m cProfile -o profile.stats -m moneyflow.app --demo

# Analyze with snakeviz
pip install snakeviz
snakeviz profile.stats
```

## CI/CD

### GitHub Actions

Tests run automatically on:
- Every push to main
- Every pull request

**What CI tests**:
- Python 3.11, 3.12, 3.13 compatibility
- Full test suite (465 tests)
- Type checking with pyright
- Coverage reporting

**CI configuration**: `.github/workflows/test.yml`

### Local CI Simulation

```bash
# Test on different Python versions locally
uv run --python 3.11 pytest
uv run --python 3.12 pytest
uv run --python 3.13 pytest
```

## Release Process

See [PUBLISHING.md](../../PUBLISHING.md) for complete publishing workflow.

**Quick version**:
```bash
# 1. Bump version
./scripts/bump-version.sh 0.2.0

# 2. Test build
./scripts/test-build.sh

# 3. Publish to TestPyPI
./scripts/publish-testpypi.sh

# 4. Test installation
uvx --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ moneyflow --demo

# 5. Publish to PyPI
./scripts/publish-pypi.sh

# 6. Push to GitHub
git push && git push --tags
```

## Troubleshooting

### Tests Fail After `git pull`

```bash
# Resync dependencies
uv sync

# Reinstall in development mode
uv pip install -e .
```

### Type Checker Errors

```bash
# Update pyright
uv sync --upgrade

# Check specific file
uv run pyright moneyflow/your_file.py --verbose
```

### Import Errors

```bash
# Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
find . -name "*.pyc" -delete

# Reinstall
uv sync --reinstall
```

## Getting Help

- **Bugs**: Open an issue on GitHub
- **Questions**: Check existing issues or open a discussion
- **Development**: See [CLAUDE.md](../../CLAUDE.md) for detailed developer guide

## Best Practices

1. **Write tests first** - TDD is non-negotiable for financial software
2. **Use type hints** - Help catch bugs before runtime
3. **Keep functions small** - Single responsibility, easy to test
4. **Document public APIs** - Docstrings with examples
5. **Separate concerns** - Business logic out of UI
6. **Run tests often** - After every small change
7. **Commit frequently** - Small, focused commits with clear messages

## Resources

- [Textual Documentation](https://textual.textualize.io/)
- [Polars Documentation](https://pola.rs/)
- [Pyright Documentation](https://github.com/microsoft/pyright)
- [uv Documentation](https://docs.astral.sh/uv/)
