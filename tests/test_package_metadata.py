import tempfile
import zipfile
from pathlib import Path
import yaml

from pixell.core.builder import AgentBuilder


def _write_manifest(project_dir: Path, name: str = "pkg-agent", desc: str = "desc"):
    manifest_data = {
        "version": "1.0",
        "name": name,
        "display_name": name,
        "description": desc,
        "author": "Test",
        "license": "MIT",
        "runtime": "python3.11",
        # Provide entrypoint to satisfy validation when no surfaces configured
        "entrypoint": "src.main:handler",
        "metadata": {"version": "0.1.0"},
    }
    with open(project_dir / "agent.yaml", "w") as f:
        yaml.dump(manifest_data, f)


class TestPackageDiscovery:
    def test_discover_packages_basic(self, tmp_path: Path):
        # Build directory layout
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("# main\n")
        (tmp_path / "core").mkdir()
        (tmp_path / "core" / "util.py").write_text("# util\n")
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / ".pixell").mkdir()

        builder = AgentBuilder(tmp_path)
        packages = builder._discover_packages(tmp_path)

        assert set(packages) == {"src", "core"}

    def test_discover_packages_nested(self, tmp_path: Path):
        (tmp_path / "app" / "v1" / "reddit").mkdir(parents=True)
        (tmp_path / "app" / "v1" / "reddit" / "commenter.py").write_text("# c\n")
        (tmp_path / "core" / "util").mkdir(parents=True)
        (tmp_path / "core" / "util" / "helpers.py").write_text("# h\n")

        builder = AgentBuilder(tmp_path)
        packages = builder._discover_packages(tmp_path)

        # Note: Only directories containing .py files are included
        assert "app.v1.reddit" in packages
        assert "core.util" in packages
        assert "app" not in packages  # no direct .py in app/

    def test_discover_packages_ignores_pycache(self, tmp_path: Path):
        (tmp_path / "pkg").mkdir()
        (tmp_path / "pkg" / "__pycache__").mkdir()
        (tmp_path / "pkg" / "module.py").write_text("# m\n")

        builder = AgentBuilder(tmp_path)
        packages = builder._discover_packages(tmp_path)
        assert packages == ["pkg"]


class TestSetupPyGeneration:
    def test_generate_setup_py_contents(self, tmp_path: Path):
        project_dir = tmp_path / "agent"
        project_dir.mkdir()
        _write_manifest(project_dir, name="vivid-commenter", desc="An agent")
        (project_dir / ".env").write_text("K=V\n")
        builder = AgentBuilder(project_dir)
        builder._load_manifest()

        packages = ["src", "core", "app.v1"]
        content = builder._generate_setup_py(packages)

        assert "name=\"vivid-commenter\"" in content
        assert "version=\"0.1.0\"" in content
        assert "packages=[" in content
        assert "'src'" in content and "'core'" in content and "'app.v1'" in content

    def test_create_package_metadata_writes_file(self, tmp_path: Path):
        project_dir = tmp_path / "agent"
        project_dir.mkdir()
        _write_manifest(project_dir, name="meta-agent")
        (project_dir / ".env").write_text("K=V\n")

        # Build-dir simulation with python files
        with tempfile.TemporaryDirectory() as build_dir:
            build_path = Path(build_dir)
            (build_path / "src").mkdir()
            (build_path / "src" / "main.py").write_text("# main\n")

            builder = AgentBuilder(project_dir)
            builder._load_manifest()
            builder._create_package_metadata(build_path)

            setup_path = build_path / "setup.py"
            assert setup_path.exists()
            content = setup_path.read_text()
            assert "name=\"meta-agent\"" in content
            assert "'src'" in content

    def test_skip_existing_setup_py(self, tmp_path: Path):
        project_dir = tmp_path / "agent"
        project_dir.mkdir()
        _write_manifest(project_dir, name="has-setup")
        (project_dir / ".env").write_text("K=V\n")

        with tempfile.TemporaryDirectory() as build_dir:
            build_path = Path(build_dir)
            (build_path / "pkg").mkdir()
            (build_path / "pkg" / "m.py").write_text("# m\n")
            # Pre-existing setup.py
            (build_path / "setup.py").write_text("# existing\n")

            builder = AgentBuilder(project_dir)
            builder._load_manifest()
            builder._create_package_metadata(build_path)

            assert (build_path / "setup.py").read_text().startswith("# existing")


class TestBuildIntegrationSetup:
    def test_build_generates_setup_py_in_apkg(self, tmp_path: Path):
        project_dir = tmp_path / "agent"
        project_dir.mkdir()
        _write_manifest(project_dir, name="vivid-commenter", desc="AI commenter")
        (project_dir / ".env").write_text("K=V\n")

        # Project content
        (project_dir / "src").mkdir()
        (project_dir / "src" / "main.py").write_text("# main\n")
        (project_dir / "core").mkdir()
        (project_dir / "core" / "util.py").write_text("# util\n")

        builder = AgentBuilder(project_dir)
        apkg_path = builder.build(tmp_path / "dist")

        assert apkg_path.exists()
        with zipfile.ZipFile(apkg_path, "r") as zf:
            names = zf.namelist()
            assert "setup.py" in names
            # Verify contents
            with zf.open("setup.py") as f:
                content = f.read().decode("utf-8")
                assert "'src'" in content
                assert "'core'" in content

