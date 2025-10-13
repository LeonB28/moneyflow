# Publishing moneyflow to PyPI

## Prerequisites

1. **PyPI Account**: Create accounts on [PyPI](https://pypi.org/account/register/) and [TestPyPI](https://test.pypi.org/account/register/)
2. **API Tokens**: Generate API tokens for both (Account Settings → API tokens)
3. **Build Tools**: Install build tools with `uv pip install build twine`

## Build the Package

```bash
# Clean old builds
rm -rf dist/ build/ *.egg-info

# Build distribution packages
uv run python -m build

# This creates:
# - dist/moneyflow-0.1.0-py3-none-any.whl (wheel)
# - dist/moneyflow-0.1.0.tar.gz (source distribution)
```

## Test on TestPyPI First

```bash
# Upload to TestPyPI
uv run twine upload --repository testpypi dist/*

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ moneyflow

# Test that it works
moneyflow --demo

# Test with uvx
uvx --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ moneyflow --demo
```

## Publish to PyPI

Once tested on TestPyPI:

```bash
# Upload to real PyPI
uv run twine upload dist/*

# Test installation
pip install moneyflow

# Test command works
moneyflow --demo

# Test with uvx (no installation needed!)
uvx moneyflow --demo
```

## Version Bumping

Before each release, update version in `pyproject.toml`:

```toml
[project]
name = "moneyflow"
version = "0.2.0"  # Increment this
```

Then:
```bash
# Commit version bump
git add pyproject.toml
git commit -m "chore: Bump version to 0.2.0"
git tag v0.2.0
git push && git push --tags

# Build and publish
rm -rf dist/
uv run python -m build
uv run twine upload dist/*
```

## uvx Compatibility

The package is already configured for `uvx` usage! Users can run without installing:

```bash
# Run directly with uvx (downloads temporarily)
uvx moneyflow

# With options
uvx moneyflow --demo
uvx moneyflow --year 2025
```

This works because pyproject.toml defines:
- `[project.scripts]` entry point for `moneyflow` command
- All dependencies properly listed
- Python >=3.11 requirement

## Troubleshooting

### "Invalid distribution" error
- Make sure `README.md` and `LICENSE` files exist
- Check pyproject.toml syntax with `uv run python -m build --check`

### "Filename has already been used" error
- You can't re-upload the same version
- Bump the version number in pyproject.toml

### uvx can't find the command
- Make sure `[project.scripts]` is correct in pyproject.toml
- Verify entry point: `moneyflow = "moneyflow.app:main"`

## PyPI Package Page

After publishing, your package will be available at:
- https://pypi.org/project/moneyflow/
- Install with: `pip install moneyflow`
- Run with uvx: `uvx moneyflow`
