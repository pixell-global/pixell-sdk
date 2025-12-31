"""CLI command modules for pixell."""

from pixell.cli.commands.agent import (
    init_cmd,
    build_cmd,
    run_dev_cmd,
    dev_cmd,
    validate_cmd,
    inspect_cmd,
)
from pixell.cli.commands.deploy import deploy_cmd, status_cmd
from pixell.cli.commands.config import config
from pixell.cli.commands.secrets import secrets
from pixell.cli.commands.ui import ui
from pixell.cli.commands.intent import validate_intents_cmd
from pixell.cli.commands.registry import list_cmd
from pixell.cli.commands.test import test_cmd
from pixell.cli.commands.guide import guide_cmd

__all__ = [
    "init_cmd",
    "build_cmd",
    "run_dev_cmd",
    "dev_cmd",
    "validate_cmd",
    "inspect_cmd",
    "deploy_cmd",
    "status_cmd",
    "config",
    "secrets",
    "ui",
    "validate_intents_cmd",
    "list_cmd",
    "test_cmd",
    "guide_cmd",
]
