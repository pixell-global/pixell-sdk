"""Tests for required .env behavior and validations."""

import tempfile
import zipfile
from pathlib import Path
import pytest

from pixell.core.builder import AgentBuilder, BuildError
from pixell.core.validator import AgentValidator


def _write_minimal_project(project_dir: Path, with_entrypoint: bool = True) -> None:
    project_dir.mkdir(parents=True, exist_ok=True)
    # agent.yaml with entrypoint to satisfy validator when no surfaces
    manifest = {
        "version": "1.0",
        "name": "env-test-agent",
        "display_name": "Env Test Agent",
        "description": "Test agent",
        "author": "Tester",
        "license": "MIT",
        "runtime": "python3.11",
        "metadata": {"version": "1.0.0"},
    }
    if with_entrypoint:
        manifest["entrypoint"] = "src.main:handler"
    import yaml as _yaml

    (project_dir / "agent.yaml").write_text(_yaml.safe_dump(manifest, sort_keys=False))
    (project_dir / "src").mkdir(exist_ok=True)
    if with_entrypoint:
        (project_dir / "src" / "main.py").write_text(
            """
def handler(context):
    return {"ok": True}
""".lstrip()
        )


class TestEnvRequirements:
    def test_env_required_for_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "env-missing-agent"
            _write_minimal_project(project_dir)

            builder = AgentBuilder(project_dir)
            with pytest.raises(BuildError, match=r"Missing required .env file"):
                builder.build()

    def test_env_included_in_apkg(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "env-included-agent"
            _write_minimal_project(project_dir)

            env_content = "FOO='bar baz'\nAPI_HOST=0.0.0.0\n"
            (project_dir / ".env").write_text(env_content)

            builder = AgentBuilder(project_dir)
            apkg_path = builder.build()
            assert apkg_path.exists()

            with zipfile.ZipFile(apkg_path, "r") as zf:
                names = zf.namelist()
                assert ".env" in names
                with zf.open(".env") as f:
                    packaged = f.read().decode("utf-8")
                    # Normalize line endings for cross-platform compatibility
                    assert packaged.replace("\r\n", "\n") == env_content

    def test_env_security_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "env-security-agent"
            _write_minimal_project(project_dir)

            (project_dir / ".env").write_text(
                "OPENAI_API_KEY=sk-123456\nAWS_SECRET_ACCESS_KEY=placeholder\n"
            )

            validator = AgentValidator(project_dir)
            is_valid, errors, warnings = validator.validate()
            assert is_valid, f"Unexpected validation errors: {errors}"
            # Real secrets are now allowed - production agents need them for testing

    def test_env_path_hygiene(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "env-path-agent"
            _write_minimal_project(project_dir)

            (project_dir / ".env").write_text("MODEL_PATH=/Users/alice/models/model.bin\n")

            validator = AgentValidator(project_dir)
            is_valid, errors, warnings = validator.validate()
            assert is_valid, f"Unexpected validation errors: {errors}"
            joined = "\n".join(warnings)
            assert "absolute path" in joined
            assert "MODEL_PATH" in joined

    def test_parse_dotenv_and_merge_precedence(self):
        from pixell.utils import parse_dotenv, merge_envs

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text("A=1\nB='two'\n#C=skip\nD= spaced value \n")
            parsed = parse_dotenv(path)
            assert parsed["A"] == "1"
            assert parsed["B"] == "two"
            assert parsed["D"] == "spaced value"

            base = {"A": "0", "X": "x"}
            over = {"A": "1", "B": "2"}
            merged = merge_envs(base, over)
            assert merged["A"] == "1"
            assert merged["B"] == "2"
            assert merged["X"] == "x"

    def test_secrets_provider_selection_and_merge(self, monkeypatch):
        from pixell.secrets import get_provider_from_env
        from pixell.utils import merge_envs

        # Static provider via JSON
        monkeypatch.setenv("PIXELL_SECRETS_PROVIDER", "static")
        monkeypatch.setenv("PIXELL_SECRETS_JSON", '{"API_KEY":"runtime","DB_HOST":"db"}')
        provider = get_provider_from_env()
        assert provider is not None
        secrets = provider.fetch_secrets()
        assert secrets["API_KEY"] == "runtime"
        assert secrets["DB_HOST"] == "db"

        # Env provider
        monkeypatch.setenv("PIXELL_SECRETS_PROVIDER", "env")
        monkeypatch.setenv("FOO", "bar")
        provider = get_provider_from_env()
        assert provider is not None
        env_secrets = provider.fetch_secrets()
        assert env_secrets.get("FOO") == "bar"

        # Merge precedence example: provider > .env > base
        base = {"A": "base", "B": "base"}
        dotenv = {"B": "env", "C": "env"}
        provider_map = {"C": "prov", "D": "prov"}
        merged = merge_envs(base, dotenv)
        merged = merge_envs(merged, provider_map)
        assert merged == {"A": "base", "B": "env", "C": "prov", "D": "prov"}
