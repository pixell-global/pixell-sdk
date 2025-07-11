# Release Process for Pixell Kit

This document describes the release process for publishing pixell-kit to PyPI and Homebrew.

## Prerequisites

1. Ensure you have PyPI account and are added as a maintainer for `pixell-kit`
2. Set up PyPI trusted publishing for the GitHub repository
3. Have a Homebrew tap repository (e.g., `pixell/homebrew-tap`)

## Release Steps

### 1. Prepare the Release

1. Update version in:
   - `setup.py`
   - `pyproject.toml`
   - `pixell/cli/main.py` (if hardcoded)

2. Update CHANGELOG.md with release notes

3. Run tests locally:
   ```bash
   pytest tests/
   black pixell/
   ruff check pixell/
   ```

4. Build and test the package locally:
   ```bash
   python -m build
   pip install dist/pixell-kit-*.whl
   pixell --version
   ```

### 2. Create GitHub Release

1. Commit all changes:
   ```bash
   git add .
   git commit -m "Release v0.1.0"
   git push origin main
   ```

2. Create a new tag:
   ```bash
   git tag -a v0.1.0 -m "Release version 0.1.0"
   git push origin v0.1.0
   ```

3. Go to GitHub releases page and create a new release from the tag
4. Add release notes from CHANGELOG.md

### 3. PyPI Release (Automated)

The GitHub Actions workflow will automatically:
1. Run tests on Python 3.11 and 3.12
2. Build the package
3. Publish to PyPI using trusted publishing

Monitor the Actions tab to ensure successful deployment.

### 4. Update Homebrew Formula

After PyPI release succeeds:

1. Run the update script:
   ```bash
   python scripts/update_homebrew_formula.py 0.1.0
   ```

2. Copy the updated formula to your Homebrew tap:
   ```bash
   cp homebrew/pixell-kit.rb ../homebrew-tap/Formula/
   ```

3. Test the formula locally:
   ```bash
   brew install --build-from-source ../homebrew-tap/Formula/pixell-kit.rb
   brew test pixell-kit
   ```

4. Commit and push to Homebrew tap:
   ```bash
   cd ../homebrew-tap
   git add Formula/pixell-kit.rb
   git commit -m "pixell-kit 0.1.0"
   git push
   ```

### 5. Verify Installation

Test all installation methods:

```bash
# Test PyPI
pipx install pixell-kit
pixell --version

# Test Homebrew
brew update
brew install pixell-kit
pixell --version
```

## Troubleshooting

### PyPI Issues

- If PyPI upload fails, check GitHub Actions logs
- Ensure trusted publishing is configured in PyPI project settings
- Test with TestPyPI first using workflow_dispatch

### Homebrew Issues

- Run `brew audit --strict pixell-kit` to check formula
- Test on both Intel and Apple Silicon Macs if possible
- Check Python dependency versions match PyPI package

## Version Numbering

We follow semantic versioning:
- MAJOR.MINOR.PATCH (e.g., 0.1.0)
- Increment MAJOR for breaking changes
- Increment MINOR for new features
- Increment PATCH for bug fixes