# Publishing pixell-kit to PyPI and Homebrew

This guide will walk you through publishing `pixell-kit` to PyPI and creating a Homebrew formula.

## Prerequisites

1. PyPI account at https://pypi.org
2. GitHub account with access to create repositories
3. The built packages in `dist/` directory

## Step 1: Set up PyPI Authentication

### Option A: Using PyPI Token (Recommended)

1. Log in to https://pypi.org
2. Go to Account Settings → API tokens
3. Create a new API token with scope "Entire account" or project-specific
4. Save the token securely

Create `~/.pypirc`:
```ini
[pypi]
username = __token__
password = pypi-YOUR_TOKEN_HERE
```

### Option B: Using GitHub Trusted Publishing (Best for CI/CD)

1. Go to your PyPI project settings
2. Add trusted publisher:
   - Publisher: GitHub
   - Repository: pixell-global/pixell-kit
   - Workflow: release.yml
   - Environment: (leave blank)

## Step 2: Publish to TestPyPI First (Optional but Recommended)

```bash
# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple pixell-kit
pixell --version
```

## Step 3: Publish to PyPI

```bash
# Upload to PyPI
twine upload dist/*

# The package will be available at https://pypi.org/project/pixell-kit/
```

## Step 4: Test PyPI Installation

```bash
# Test with pip
pip install pixell-kit
pixell --version

# Test with pipx (recommended for CLI tools)
pipx install pixell-kit
pixell --version
```

## Step 5: Create Homebrew Tap

1. Create a new GitHub repository named `homebrew-tap` in your organization:
   ```
   https://github.com/pixell-global/homebrew-tap
   ```

2. Create the directory structure:
   ```
   homebrew-tap/
   └── Formula/
       └── pixell-kit.rb
   ```

3. Update the formula with the actual SHA256:
   ```bash
   # Get the SHA256 of the source distribution
   shasum -a 256 dist/pixell_kit-0.1.0.tar.gz
   
   # Or use the update script after PyPI release
   python scripts/update_homebrew_formula.py 0.1.0
   ```

4. Copy the updated formula:
   ```bash
   cp homebrew/pixell-kit.rb PATH_TO_YOUR_TAP/Formula/
   ```

5. Commit and push to the tap repository

## Step 6: Test Homebrew Installation

```bash
# Add your tap
brew tap pixell-global/tap

# Install pixell-kit
brew install pixell-kit

# Test it works
pixell --version
```

## Step 7: Announce the Release

1. Create a GitHub Release:
   - Tag: v0.1.0
   - Title: pixell-kit v0.1.0
   - Add release notes from CHANGELOG.md

2. Update documentation to reflect availability

## Automated Releases (Future)

Once you've set up GitHub trusted publishing, future releases can be automated:

1. Update version in `pyproject.toml` and `setup.py`
2. Commit and tag: `git tag v0.1.1`
3. Push tag: `git push origin v0.1.1`
4. GitHub Actions will automatically publish to PyPI

## Troubleshooting

### PyPI Upload Issues
- Ensure your token has the correct permissions
- Check that the package name isn't already taken
- Verify your `.pypirc` file is correctly formatted

### Homebrew Issues
- Run `brew audit --strict pixell-kit` to check the formula
- Ensure all dependencies are correctly specified
- Test on both Intel and Apple Silicon Macs if possible

### Installation Issues
- For pipx: ensure Python 3.11+ is available
- For brew: ensure Homebrew is up to date with `brew update`

## Current Package Status

- Package Name: `pixell-kit`
- Version: 0.1.0
- Command: `pixell`
- Python Requirement: >=3.11
- License: Apache-2.0