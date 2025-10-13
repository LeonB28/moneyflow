# Publishing Scripts

Automation scripts for version management and PyPI publishing.

## Scripts

### `bump-version.sh <version>`

Bump version number and create git tag.

```bash
# Bump to 0.2.0
./scripts/bump-version.sh 0.2.0

# This will:
# 1. Update version in pyproject.toml
# 2. Commit the change
# 3. Create git tag v0.2.0
# 4. Print next steps (you push when ready)
```

### `test-build.sh`

Build the package and test it locally before publishing.

```bash
./scripts/test-build.sh

# This will:
# 1. Clean old builds
# 2. Build with uv
# 3. Test the wheel with uvx
# 4. Verify --help and --demo work
```

### `publish-testpypi.sh`

Publish to TestPyPI for testing.

```bash
./scripts/publish-testpypi.sh

# This will:
# 1. Run tests
# 2. Build package
# 3. Upload to TestPyPI
# 4. Print instructions for testing
```

### `publish-pypi.sh`

Publish to production PyPI (with safety checks).

```bash
./scripts/publish-pypi.sh

# This will:
# 1. Check for git tag
# 2. Check for uncommitted changes
# 3. Run tests
# 4. Build package
# 5. Ask for confirmation
# 6. Upload to PyPI
```

## Full Release Workflow

```bash
# 1. Bump version
./scripts/bump-version.sh 0.2.0

# 2. Test build locally
./scripts/test-build.sh

# 3. Publish to TestPyPI
./scripts/publish-testpypi.sh

# 4. Test from TestPyPI
uvx --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ moneyflow --demo

# 5. If good, publish to PyPI
./scripts/publish-pypi.sh

# 6. Test from PyPI
uvx moneyflow --demo

# 7. Push to GitHub
git push && git push --tags
```

## Prerequisites

- `~/.pypirc` configured with API tokens (see PUBLISHING.md)
- All tests passing
- Clean git state (no uncommitted changes)

## Safety Features

- All scripts run tests before building
- PyPI publish script requires typing "yes" to confirm
- Version tag check before publishing
- Uncommitted changes warning
- Test on TestPyPI before production
