#!/usr/bin/env python3
"""Script to update Homebrew formula with new release information."""

import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

def get_package_info(package_name, version):
    """Fetch package information from PyPI."""
    url = f"https://pypi.org/pypi/{package_name}/{version}/json"
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read())

def get_sha256(url):
    """Download file and calculate SHA256."""
    with urllib.request.urlopen(url) as response:
        return hashlib.sha256(response.read()).hexdigest()

def update_formula(version):
    """Update the Homebrew formula with new version and SHA256."""
    formula_path = Path(__file__).parent.parent / "homebrew" / "pixell-kit.rb"
    
    # Get package info from PyPI
    package_info = get_package_info("pixell-kit", version)
    
    # Find the source distribution URL
    sdist_url = None
    for file_info in package_info["urls"]:
        if file_info["packagetype"] == "sdist":
            sdist_url = file_info["url"]
            break
    
    if not sdist_url:
        print("Error: Source distribution not found on PyPI")
        sys.exit(1)
    
    # Calculate SHA256
    sha256 = get_sha256(sdist_url)
    
    # Read the formula
    formula_content = formula_path.read_text()
    
    # Update version and SHA256
    formula_content = re.sub(
        r'url ".*pixell-kit-.*\.tar\.gz"',
        f'url "{sdist_url}"',
        formula_content
    )
    formula_content = re.sub(
        r'sha256 ".*"  # This will be updated',
        f'sha256 "{sha256}"',
        formula_content
    )
    
    # Write updated formula
    formula_path.write_text(formula_content)
    
    print(f"Updated Homebrew formula for version {version}")
    print(f"SHA256: {sha256}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python update_homebrew_formula.py <version>")
        sys.exit(1)
    
    version = sys.argv[1]
    update_formula(version)