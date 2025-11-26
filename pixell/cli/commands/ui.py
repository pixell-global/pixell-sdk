"""UI commands for pixell CLI."""

import click
from pathlib import Path


@click.group()
def ui():
    """UI-related commands."""
    pass


@ui.command(name="validate")
@click.option("--file", "file_path", required=True, help="Path to UI spec JSON file")
def ui_validate(file_path: str):
    """Validate a UI spec JSON file against the current schema and Pydantic models."""
    import json
    from pixell.ui import validate_spec

    with open(Path(file_path), "r") as f:
        data = json.load(f)
    try:
        validate_spec(data)
        click.secho("UI spec is valid", fg="green")
    except Exception as e:
        click.secho(f"Invalid UI spec: {e}", fg="red")
        ctx = click.get_current_context()
        ctx.exit(1)


@ui.command(name="schema")
@click.option("--print", "print_only", is_flag=True, help="Print current UI schema JSON to stdout")
@click.option("--out", "out_path", required=False, help="Write schema JSON to file")
def ui_schema(print_only: bool, out_path: str | None):
    """Print or write the current UISpec JSON Schema."""
    import json
    from pixell.ui.spec import UISpec

    schema = UISpec.model_json_schema()
    if print_only:
        click.echo(json.dumps(schema, indent=2))
    elif out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(json.dumps(schema, indent=2))
        click.secho(f"Wrote schema to {out_path}", fg="green")
    else:
        click.echo("Use --print to print schema or --out to write to a file.")
