#!/usr/bin/env python3
"""Test script to build a test package using pixell build command.

This script builds the ./test_package directory into an APKG file.
Usage:
    python scripts/test_build.py
    python scripts/test_build.py --path ./test_package --output ./dist
    python scripts/test_build.py --path "B:\\Workspace\\Pixell Global\\vivid-commenter"
    python scripts/test_build.py -p "B:/Workspace/Pixell Global/ai-writer-agent" -o ./dist
"""

import sys
import os
import argparse
from pathlib import Path

# Add parent directory to path to import pixell
sys.path.insert(0, str(Path(__file__).parent.parent))

from pixell.core.builder import AgentBuilder, BuildError


def main():
    # Default path for debugging (F5 in VS Code)
    # Can be overridden via --path argument
    default_path = os.environ.get(
        "PIXELL_TEST_BUILD_PATH",
        r"B:\Workspace\Pixell Global\vivid-commenter"
    )
    
    parser = argparse.ArgumentParser(
        description="Test script to build a package using pixell build"
    )
    parser.add_argument(
        "--path",
        "-p",
        type=str,
        default=default_path,
        help=f"Path to agent project directory (default: {default_path}). Supports both relative and absolute paths.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output directory for APKG file (default: same as project directory)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    project_dir = Path(args.path).resolve()

    if not project_dir.exists():
        print(f"❌ Error: Project directory not found: {project_dir}")
        sys.exit(1)

    if not (project_dir / "agent.yaml").exists():
        print(f"❌ Error: agent.yaml not found in {project_dir}")
        sys.exit(1)

    print(f"📦 Building agent from {project_dir}...")
    if args.verbose:
        print(f"   Output directory: {args.output or project_dir}")

    try:
        builder = AgentBuilder(project_dir)
        output_dir = Path(args.output) if args.output else None
        output_path = builder.build(output_dir=output_dir)

        # Show build info
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print()
        print("✅ SUCCESS: Build successful!")
        print(f"   📄 Package: {output_path.name}")
        print(f"   📍 Location: {output_path.parent}")
        print(f"   📊 Size: {size_mb:.2f} MB")
        print()
        return 0

    except BuildError as e:
        print(f"❌ FAILED: Build failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
    except Exception as e:
        print(f"❌ ERROR: Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

