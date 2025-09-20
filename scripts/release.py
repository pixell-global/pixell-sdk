#!/usr/bin/env python3
"""
Release helper script for pixell-kit.
Updates version numbers and creates git tags.
"""

import re
import sys
import subprocess
from pathlib import Path


def update_version(file_path: Path, pattern: str, new_version: str):
    """Update version in a file."""
    content = file_path.read_text()
    updated = re.sub(pattern, f"\\g<1>{new_version}\\g<3>", content)
    if content != updated:
        file_path.write_text(updated)
        print(f"✓ Updated {file_path}")
    else:
        print(f"⚠ No changes in {file_path}")


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/release.py <version>")
        print("Example: python scripts/release.py 0.3.0")
        sys.exit(1)

    new_version = sys.argv[1]

    # Validate version format
    if not re.match(r"^\d+\.\d+\.\d+$", new_version):
        print(f"Error: Invalid version format '{new_version}'")
        print("Use semantic versioning: MAJOR.MINOR.PATCH")
        sys.exit(1)

    project_root = Path(__file__).parent.parent

    # Update version in files
    files_to_update = [
        (project_root / "setup.py", r'(version=")[^"]+(")', r'(version=")([^"]+)(")'),
        (project_root / "pyproject.toml", r'(version = ")[^"]+(")', r'(version = ")([^"]+)(")'),
    ]

    print(f"Updating version to {new_version}...")
    for file_path, _, pattern in files_to_update:
        update_version(file_path, pattern, new_version)

    # Update CHANGELOG.md
    changelog = project_root / "CHANGELOG.md"
    if changelog.exists():
        content = changelog.read_text()
        today = subprocess.run(["date", "+%Y-%m-%d"], capture_output=True, text=True).stdout.strip()

        # Update unreleased section
        updated = content.replace(
            "## [Unreleased]", f"## [Unreleased]\n\n## [{new_version}] - {today}"
        )

        if content != updated:
            changelog.write_text(updated)
            print(f"✓ Updated {changelog}")

    print("\n📋 Next steps:")
    print("1. Review the changes")
    print("2. Commit the changes:")
    print(f"   git add -A && git commit -m 'Release v{new_version}'")
    print("3. Create and push tag:")
    print(f"   git tag -a v{new_version} -m 'Release version {new_version}'")
    print("   git push origin main")
    print(f"   git push origin v{new_version}")
    print("4. Create a release on GitHub")


if __name__ == "__main__":
    main()
