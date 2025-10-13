# Publishing moneyflow to PyPI

## Prerequisites

1. **PyPI Account**: Create accounts on [PyPI](https://pypi.org/account/register/) and [TestPyPI](https://test.pypi.org/account/register/)
2. **API Tokens**: Generate API tokens for both (Account Settings → API tokens)
3. **Configure PyPI credentials**:
   ```bash
   # Create/edit ~/.pypirc
   cat > ~/.pypirc << 'EOF'
   [distutils]
   index-servers =
       pypi
       testpypi

   [pypi]
   username = __token__
   password = pypi-YOUR_TOKEN_HERE

   [testpypi]
   repository = https://test.pypi.org/legacy/
   username = __token__
   password = pypi-YOUR_TESTPYPI_TOKEN_HERE
   EOF

   chmod 600 ~/.pypirc
   ```

## Build the Package

```bash
# Clean old builds
rm -rf dist/ build/ *.egg-info moneyflow.egg-info

# Build using uv (includes build tools automatically)
uv build

# Or use traditional build
uvx --from build pyproject-build --installer uv

# This creates:
# - dist/moneyflow-0.1.0-py3-none-any.whl (wheel)
# - dist/moneyflow-0.1.0.tar.gz (source distribution)
```

## Test on TestPyPI First

```bash
# Upload to TestPyPI using uvx (no permanent install needed)
uvx twine upload --repository testpypi dist/*
# Enter your TestPyPI token when prompted (or uses ~/.pypirc)

# Test installation from TestPyPI in a fresh environment
uvx --from moneyflow --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ moneyflow --demo

# Or install and test
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ moneyflow
moneyflow --demo
pip uninstall moneyflow  # Clean up
```

## Publish to PyPI

Once tested on TestPyPI:

```bash
# Upload to real PyPI
uvx twine upload dist/*
# Or if you have ~/.pypirc configured:
uvx twine upload --repository pypi dist/*

# Test installation (use a fresh terminal or different machine)
uvx moneyflow --demo

# Or install permanently
pip install moneyflow
moneyflow --demo
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
uv build
uvx twine upload dist/*
```

## Pre-Release Checklist

Before publishing a new version:

- [ ] All tests passing: `uv run pytest`
- [ ] Version bumped in `pyproject.toml`
- [ ] CHANGELOG updated (if you have one)
- [ ] README is current
- [ ] Works in demo mode: `uv run moneyflow --demo`
- [ ] Git tag created: `git tag v0.x.x`
- [ ] Committed and pushed to main

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

**Testing uvx before publishing:**
```bash
# After building, test the wheel directly
uvx --from ./dist/moneyflow-0.1.0-py3-none-any.whl moneyflow --demo
```

## Recommended Publishing Workflow

```bash
# 1. Bump version in pyproject.toml (e.g., 0.1.0 → 0.1.1)

# 2. Run tests
uv run pytest

# 3. Clean and build
rm -rf dist/ build/ *.egg-info
uv build

# 4. Test the built package locally with uvx
uvx --from ./dist/moneyflow-0.1.1-py3-none-any.whl moneyflow --demo

# 5. Upload to TestPyPI first
uvx twine upload --repository testpypi dist/*

# 6. Test from TestPyPI
uvx --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ moneyflow --demo

# 7. If all looks good, upload to PyPI
uvx twine upload dist/*

# 8. Test from real PyPI
uvx moneyflow --demo

# 9. Tag and push
git tag v0.1.1
git push && git push --tags
```

## Troubleshooting

### "Invalid distribution" error
- Make sure `README.md` and `LICENSE` files exist
- Check pyproject.toml syntax: `uv build --check`

### "Filename has already been used" error
- You can't re-upload the same version to PyPI
- Bump the version number in pyproject.toml
- TestPyPI allows re-uploads (for testing)

### uvx can't find the command
- Make sure `[project.scripts]` is correct in pyproject.toml
- Verify entry point: `moneyflow = "moneyflow.app:main"`
- Check the wheel was built correctly: `unzip -l dist/moneyflow-*.whl | grep __main__`

### Build fails
- Run `uv sync` to ensure all dependencies are installed
- Check for syntax errors in pyproject.toml
- Try: `uv build --verbose` for detailed error messages

## PyPI Package Page

After publishing, your package will be available at:
- https://pypi.org/project/moneyflow/
- Install with: `pip install moneyflow`
- Run with uvx: `uvx moneyflow`
