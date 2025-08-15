"""Server-driven UI runtime (agent_ui) models and helpers."""

from .version import SPEC_VERSION
from .spec import UISpec, Manifest, View, Component, UIPatch
from .actions import Action, OpenUrlAction, HttpAction, StateSetAction, EmitAction
from .theme import Theme
from .validate import validate_spec
from .patch import make_patch, validate_patch_scope
from .capabilities import ClientCapabilities, adapt_view_for_capabilities

__all__ = [
    "SPEC_VERSION",
    "UISpec",
    "Manifest",
    "View",
    "Component",
    "UIPatch",
    "Action",
    "OpenUrlAction",
    "HttpAction",
    "StateSetAction",
    "EmitAction",
    "Theme",
    "validate_spec",
    "make_patch",
    "validate_patch_scope",
    "ClientCapabilities",
    "adapt_view_for_capabilities",
] 