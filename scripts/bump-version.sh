#!/usr/bin/env bash
# Bump version in pyproject.toml and create git tag
#
# Usage:
#   ./scripts/bump-version.sh 0.2.0
#   ./scripts/bump-version.sh 0.1.1

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <new-version>"
    echo "Example: $0 0.2.0"
    exit 1
fi

NEW_VERSION="$1"

# Validate version format (basic check)
if ! [[ "$NEW_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: Version must be in format X.Y.Z (e.g., 0.2.0)"
    exit 1
fi

echo "Bumping version to $NEW_VERSION..."

# Get current version from pyproject.toml
CURRENT_VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
echo "Current version: $CURRENT_VERSION"
echo "New version: $NEW_VERSION"

# Update version in pyproject.toml
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s/^version = \".*\"/version = \"$NEW_VERSION\"/" pyproject.toml
else
    # Linux
    sed -i "s/^version = \".*\"/version = \"$NEW_VERSION\"/" pyproject.toml
fi

echo "✓ Updated pyproject.toml"

# Verify the change
NEW_VERSION_CHECK=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
if [ "$NEW_VERSION_CHECK" != "$NEW_VERSION" ]; then
    echo "Error: Version update failed!"
    exit 1
fi

# Update lock file
echo "Updating uv.lock..."
uv lock
echo "✓ Updated uv.lock"

# Stage and commit
git add pyproject.toml uv.lock
git commit -m "chore: Bump version to $NEW_VERSION"
echo "✓ Committed version bump"

# Create git tag
git tag "v$NEW_VERSION"
echo "✓ Created tag v$NEW_VERSION"

echo ""
echo "Version bump complete!"
echo ""
echo "Next steps:"
echo "  1. Review the commit: git show"
echo "  2. Push when ready: git push && git push --tags"
echo "  3. Publish to PyPI: ./scripts/publish-pypi.sh"
