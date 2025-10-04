"""Tests for requirements parsing and setup.py install_requires generation."""

import tempfile
from pathlib import Path
import zipfile
import yaml

from pixell.core.builder import AgentBuilder


def _write_minimal_agent(project_dir: Path, name: str = "req-test-agent") -> None:
    manifest_data = {
        "version": "1.0",
        "name": name,
        "display_name": "Req Test Agent",
        "description": "Test agent for requirements parsing",
        "author": "Test",
        "license": "MIT",
        "runtime": "python3.11",
        "metadata": {"version": "1.0.0"},
        # Minimal entrypoint to pass validation
        "entrypoint": "src.main:handler",
    }
    (project_dir / "src").mkdir(parents=True, exist_ok=True)
    (project_dir / "src" / "main.py").write_text(
        """
def handler(context):
    return {"status": "ok"}
"""
    )
    (project_dir / ".env").write_text("API_KEY=test\n")
    with open(project_dir / "agent.yaml", "w") as f:
        yaml.dump(manifest_data, f)


class TestParseRequirements:
    def test_parse_requirements_basic(self, tmp_path: Path):
        req_file = tmp_path / "requirements.txt"
        req_file.write_text(
            """
langchain-openai==0.3.28
requests>=2.28.0
fastapi
"""
        )

        builder = AgentBuilder(tmp_path)
        reqs = builder._parse_requirements(req_file)

        assert len(reqs) == 3
        assert "langchain-openai==0.3.28" in reqs
        assert "requests>=2.28.0" in reqs
        assert "fastapi" in reqs

    def test_parse_requirements_with_comments(self, tmp_path: Path):
        req_file = tmp_path / "requirements.txt"
        req_file.write_text(
            """
# Core dependencies
langchain-openai==0.3.28

# HTTP client
requests>=2.28.0  # Used for API calls
"""
        )

        builder = AgentBuilder(tmp_path)
        reqs = builder._parse_requirements(req_file)

        assert len(reqs) == 2
        assert "langchain-openai==0.3.28" in reqs
        assert "requests>=2.28.0" in reqs

    def test_parse_requirements_skip_editable(self, tmp_path: Path):
        req_file = tmp_path / "requirements.txt"
        req_file.write_text(
            """
-e git+https://github.com/user/repo.git
requests
--editable .
numpy
"""
        )

        builder = AgentBuilder(tmp_path)
        reqs = builder._parse_requirements(req_file)

        assert len(reqs) == 2
        assert "requests" in reqs
        assert "numpy" in reqs

    def test_parse_requirements_skip_pip_options(self, tmp_path: Path):
        req_file = tmp_path / "requirements.txt"
        req_file.write_text(
            """
--index-url https://pypi.org/simple
requests
--extra-index-url https://custom.pypi.org
numpy
"""
        )

        builder = AgentBuilder(tmp_path)
        reqs = builder._parse_requirements(req_file)

        assert len(reqs) == 2
        assert "requests" in reqs
        assert "numpy" in reqs

    def test_parse_requirements_environment_markers(self, tmp_path: Path):
        req_file = tmp_path / "requirements.txt"
        req_file.write_text(
            """
typing-extensions; python_version<'3.11'
dataclasses; python_version<'3.7'
"""
        )

        builder = AgentBuilder(tmp_path)
        reqs = builder._parse_requirements(req_file)

        assert len(reqs) == 2
        assert "typing-extensions; python_version<'3.11'" in reqs
        assert "dataclasses; python_version<'3.7'" in reqs

    def test_parse_requirements_empty_file(self, tmp_path: Path):
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("")

        builder = AgentBuilder(tmp_path)
        reqs = builder._parse_requirements(req_file)

        assert len(reqs) == 0

    def test_parse_requirements_no_file(self, tmp_path: Path):
        req_file = tmp_path / "requirements.txt"

        builder = AgentBuilder(tmp_path)
        reqs = builder._parse_requirements(req_file)

        assert len(reqs) == 0


class TestSetupPyGeneration:
    def test_generate_setup_py_with_install_requires(self, tmp_path: Path):
        # Create minimal manifest
        manifest = {
            "version": "1.0",
            "name": "test-agent",
            "display_name": "Test Agent",
            "description": "Test agent",
            "author": "Tester",
            "license": "MIT",
            "runtime": "python3.11",
            "metadata": {"version": "1.0.0"},
            "entrypoint": "src.main:handler",
        }

        (tmp_path / "src").mkdir(parents=True, exist_ok=True)
        (tmp_path / "src" / "main.py").write_text(
            """
def handler(context):
    return {"status": "ok"}
"""
        )
        (tmp_path / ".env").write_text("API_KEY=test\n")
        with open(tmp_path / "agent.yaml", "w") as f:
            yaml.dump(manifest, f)

        builder = AgentBuilder(tmp_path)
        builder._load_manifest()

        packages = ["src", "core"]
        install_requires = ["requests>=2.28.0", "numpy"]

        setup_content = builder._generate_setup_py(packages, install_requires)

        assert 'name="test-agent"' in setup_content
        assert "'src'," in setup_content
        assert "install_requires=[" in setup_content
        assert "'requests>=2.28.0'," in setup_content
        assert "'numpy'," in setup_content

    def test_build_with_generate_install_requires(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "agent"
            project_dir.mkdir()

            _write_minimal_agent(project_dir, name="agent-with-reqs")

            # pak.yaml enabling feature
            (project_dir / "pak.yaml").write_text("generate_install_requires: true\n")

            # requirements.txt
            (project_dir / "requirements.txt").write_text("requests>=2.28.0\nnumpy\n")

            builder = AgentBuilder(project_dir)
            apkg_path = builder.build()

            extract_dir = Path(temp_dir) / "extracted"
            extract_dir.mkdir()
            with zipfile.ZipFile(apkg_path, "r") as zf:
                zf.extractall(extract_dir)

            setup_path = extract_dir / "setup.py"
            assert setup_path.exists()
            content = setup_path.read_text()
            assert "'requests>=2.28.0'," in content
            assert "'numpy'," in content

    def test_build_without_generate_install_requires(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "agent-no-optin"
            project_dir.mkdir()

            _write_minimal_agent(project_dir, name="agent-no-optin")

            builder = AgentBuilder(project_dir)
            apkg_path = builder.build()

            extract_dir = Path(temp_dir) / "extracted2"
            extract_dir.mkdir()
            with zipfile.ZipFile(apkg_path, "r") as zf:
                zf.extractall(extract_dir)

            setup_path = extract_dir / "setup.py"
            content = setup_path.read_text()
            assert "install_requires=[]" in content
