#!/usr/bin/env python3
"""Test script to deploy an APKG file using pixell deploy command.

This script deploys an APKG file to Pixell Cloud.
Usage:
    python scripts/test_deploy.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import pixell
sys.path.insert(0, str(Path(__file__).parent.parent))

from pixell.core.deployment import (
    DeploymentClient,
    DeploymentError,
    AuthenticationError,
    InsufficientCreditsError,
    ValidationError,
    get_api_key,
    get_app_id,
)

# Hardcoded APKG file name
APKG_FILE_NAME = "paf-core-agent-1.0.3.apkg"


def main():
    # Get current directory (where APKG file should be)
    current_dir = Path.cwd()
    apkg_file = current_dir / APKG_FILE_NAME

    if not apkg_file.exists():
        print(f"❌ Error: APKG file not found: {apkg_file}")
        print(f"   Current directory: {current_dir}")
        sys.exit(1)

    # Get API key from environment or config
    api_key = get_api_key()
    if not api_key:
        print("❌ Error: No API key found.")
        print("   Set PIXELL_API_KEY environment variable or configure in ~/.pixell/config.json")
        sys.exit(1)

    # Get app ID from environment or config (default to prod)
    env = "local"
    app_id = get_app_id(env)
    if not app_id:
        print(f"❌ Error: No app ID found for environment '{env}'.")
        print("   Set PIXELL_APP_ID environment variable or configure in ~/.pixell/config.json")
        sys.exit(1)

    print(f"📦 Deploying {APKG_FILE_NAME}...")
    print(f"   Environment: {env}")
    print(f"   App ID: {app_id}")
    print(f"   Force overwrite: ENABLED")
    print()

    try:
        # Create deployment client
        client = DeploymentClient(environment=env, api_key=api_key)

        print(f"   Target: {client.base_url}")
        print()

        # Deploy with force overwrite
        response = client.deploy(
            app_id=app_id,
            apkg_file=apkg_file,
            force_overwrite=True,  # --force 옵션
        )

        deployment = response["deployment"]
        package = response["package"]
        tracking = response["tracking"]

        # Show deployment info
        print()
        print("✅ Deployment initiated successfully!")
        print(f"   Deployment ID: {deployment['id']}")
        print(f"   Package ID: {package['id']}")
        print(f"   Status: {deployment['status']}")
        print(f"   Version: {package['version']}")
        print(f"   Size: {package['size_bytes'] / (1024 * 1024):.1f} MB")
        print(f"   Queued at: {deployment['queued_at']}")

        if "estimated_duration_seconds" in deployment:
            print(f"   Estimated duration: {deployment['estimated_duration_seconds']} seconds")

        print()
        print(f"📊 Track deployment: {tracking['status_url']}")
        print()

        return 0

    except AuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
        sys.exit(1)
    except InsufficientCreditsError as e:
        print(f"❌ Insufficient credits: {e}")
        sys.exit(1)
    except ValidationError as e:
        print(f"❌ Validation failed: {e}")
        sys.exit(1)
    except DeploymentError as e:
        print(f"❌ Deployment failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())

