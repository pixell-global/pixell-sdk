"""Intent validation command for pixell CLI."""

import click
from typing import List, Dict, Any


@click.command(name="validate-intents")
@click.option(
    "--file",
    "-f",
    type=click.Path(exists=True),
    multiple=True,
    help="JSON file(s) containing protocol envelopes to validate",
)
@click.option("--stdin", is_flag=True, help="Read a single JSON envelope from stdin")
@click.option("--strict", is_flag=True, help="Fail on first error")
@click.option(
    "--intent-schema",
    type=click.Path(exists=True),
    help="Optional path to a per-intent params schema JSON file",
)
def validate_intents_cmd(file, stdin, strict, intent_schema):
    """Validate protocol envelopes (ui.event, action.result, ui.patch) against JSON Schemas.

    Also validates per-intent params for `ui.event` when schemas are available.
    """
    import json
    import sys
    from jsonschema import ValidationError
    from pixell.protocol.validate import validate_envelope
    from pixell.intent.validate import validate_intent_params

    def _validate_payload(payload: Dict[str, Any]) -> List[str]:
        errs: List[str] = []
        try:
            validate_envelope(payload)
        except ValidationError as exc:
            errs.append(f"Schema validation error: {exc.message}")
        except Exception as exc:
            errs.append(f"Validation error: {exc}")
        # Per-intent params validation for ui.event
        if payload.get("type") == "ui.event":
            try:
                validate_intent_params(
                    payload.get("intent", ""), payload.get("params", {}), intent_schema
                )
            except FileNotFoundError as exc:
                # Only warn if schema not provided/found
                errs.append(f"Intent params schema not found: {exc}")
            except ValidationError as exc:
                errs.append(f"Intent params validation error: {exc.message}")
        return errs

    errors: List[str] = []

    if stdin:
        try:
            payload = json.load(sys.stdin)
            errors.extend(_validate_payload(payload))
        except Exception as exc:
            errors.append(f"Failed to read stdin JSON: {exc}")

    for path in file:
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            errors.extend(_validate_payload(payload))
        except Exception as exc:
            errors.append(f"{path}: {exc}")
            if strict:
                break

    if errors:
        click.secho("FAILED:", fg="red", bold=True)
        for e in errors:
            click.echo(f"  - {e}")
        ctx = click.get_current_context()
        ctx.exit(1)
    else:
        click.secho("SUCCESS: All envelopes valid", fg="green", bold=True)
        ctx = click.get_current_context()
        ctx.exit(0)
