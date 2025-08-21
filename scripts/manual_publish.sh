#!/bin/bash

# Manual PyPI publish script for pixell-kit
# Use this when GitHub Actions trusted publishing isn't configured

echo "Manual PyPI Publishing Script for pixell-kit"
echo "============================================"
echo ""
echo "Prerequisites:"
echo "1. Install twine: pip install twine"
echo "2. Configure PyPI credentials:"
echo "   - Create ~/.pypirc file or use PyPI API token"
echo ""
echo "Steps to publish:"
echo ""

# Clean previous builds
echo "Step 1: Cleaning previous build artifacts..."
rm -rf dist/ build/ *.egg-info/

# Build the package
echo "Step 2: Building the package..."
python setup.py sdist bdist_wheel

# Check the build
echo "Step 3: Checking the package..."
twine check dist/*

echo ""
echo "Step 4: Upload to PyPI"
echo "Run one of these commands:"
echo ""
echo "Option A - Using PyPI token (recommended):"
echo "  twine upload dist/* --username __token__ --password <your-pypi-token>"
echo ""
echo "Option B - Using username/password:"
echo "  twine upload dist/*"
echo ""
echo "Option C - Upload to TestPyPI first (for testing):"
echo "  twine upload --repository testpypi dist/*"
echo ""
echo "After uploading, users can upgrade with:"
echo "  pip install --upgrade pixell-kit"