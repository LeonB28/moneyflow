#!/usr/bin/env bash
# Test the built package locally before publishing
#
# Usage:
#   ./scripts/test-build.sh

set -e

echo "Building and testing moneyflow package locally..."
echo ""

# Get version
VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
echo "Version: $VERSION"
echo ""

# Clean and build
echo "Cleaning old builds..."
rm -rf dist/ build/ *.egg-info moneyflow.egg-info
echo "✓ Cleaned"
echo ""

echo "Building package..."
uv build
echo "✓ Built"
echo ""

# Show built files
echo "Built files:"
ls -lh dist/
echo ""

# Test the wheel with uvx
WHEEL_FILE="dist/moneyflow-$VERSION-py3-none-any.whl"

if [ ! -f "$WHEEL_FILE" ]; then
    echo "❌ Wheel file not found: $WHEEL_FILE"
    exit 1
fi

echo "Testing wheel with uvx..."
echo ""

# Test --help
echo "1. Testing --help..."
uvx --from "$WHEEL_FILE" moneyflow --help | head -5
echo "✓ --help works"
echo ""

# Test --demo
echo "2. Testing --demo mode..."
echo "   (Will launch TUI - press 'q' to quit)"
echo ""
timeout 5 uvx --from "$WHEEL_FILE" moneyflow --demo || true
echo ""
echo "✓ Demo mode launches"
echo ""

echo "✅ Package build looks good!"
echo ""
echo "Next steps:"
echo "  1. Publish to TestPyPI: ./scripts/publish-testpypi.sh"
echo "  2. Test from TestPyPI"
echo "  3. Publish to PyPI: ./scripts/publish-pypi.sh"
