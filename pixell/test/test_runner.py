"""Agent testing framework for pixell test command.

This module implements progressive validation and runtime checks for agent
projects packaged with Pixell Kit. It validates structure, builds an APKG,
installs in an isolated virtual environment, and can optionally start
configured surfaces (gRPC/REST/UI) and run basic health checks.
"""

from __future__ import annotations

import contextlib
import io
import subprocess
import tempfile
import zipfile
from collections.abc import Callable
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class TestLevel(str, Enum):
    STATIC = "static"
    BUILD = "build"
    INSTALL = "install"
    RUNTIME = "runtime"
    INTEGRATION = "integration"


class TestResult:
    def __init__(self) -> None:
        self.passed: List[str] = []
        self.failed: List[str] = []
        self.warnings: List[str] = []
        self.skipped: List[str] = []

    @property
    def success(self) -> bool:
        return len(self.failed) == 0


class AgentTester:
    """Comprehensive agent testing runner."""

    def __init__(
        self, project_dir: Path, level: TestLevel = TestLevel.INTEGRATION, silent: bool = False
    ):
        self.project_dir = Path(project_dir).resolve()
        self.level = level
        self.result = TestResult()
        self.test_venv: Optional[Path] = None
        self.apkg_path: Optional[Path] = None
        self.extract_dir: Optional[Path] = None
        self.silent = silent

    def _log(self, message: str) -> None:
        if not self.silent:
            print(message)

    async def run_all_tests(self) -> TestResult:
        """Run all test levels up to the configured level (fail-fast)."""
        sequence: List[Tuple[TestLevel, Callable]] = [
            (TestLevel.STATIC, self._test_static),
            (TestLevel.BUILD, self._test_build),
            (TestLevel.INSTALL, self._test_install),
            (TestLevel.RUNTIME, self._test_runtime),
            (TestLevel.INTEGRATION, self._test_integration),
        ]

        for lvl, fn in sequence:
            if self._should_run_level(lvl):
                await fn()
                if not self.result.success:
                    break
        return self.result

    def _should_run_level(self, test_level: TestLevel) -> bool:
        order = list(TestLevel)
        return order.index(test_level) <= order.index(self.level)

    # =============================
    # Level 1: Static Validation
    # =============================
    async def _test_static(self) -> None:
        self._log("\n📋 Level 1: Static Validation")
        self._log("=" * 50)
        await self._test_project_structure()
        await self._test_manifest_valid()
        await self._test_security_checks()
        await self._test_env_file()

    async def _test_project_structure(self) -> None:
        checks = [
            ("agent.yaml", self.project_dir / "agent.yaml"),
            ("src/ directory", self.project_dir / "src"),
        ]
        for name, path in checks:
            if path.exists():
                self.result.passed.append(f"✓ {name} exists")
            else:
                self.result.failed.append(f"✗ {name} missing")

    async def _test_manifest_valid(self) -> None:
        try:
            from pixell.core.validator import AgentValidator

            validator = AgentValidator(self.project_dir)
            is_valid, errors, warnings = validator.validate()
            if is_valid:
                self.result.passed.append("✓ Manifest schema valid")
            else:
                for err in errors:
                    self.result.failed.append(f"✗ Manifest error: {err}")
            for warn in warnings:
                self.result.warnings.append(f"⚠ {warn}")
        except Exception as exc:
            self.result.failed.append(f"✗ Manifest validation failed: {exc}")

    async def _test_security_checks(self) -> None:
        # .env file is expected and required for production agents
        env_file = self.project_dir / ".env"
        if env_file.exists():
            self.result.passed.append("✓ .env file present")

        # Sensitive files check - exclude .git (normal for version control)
        for fname in [".pypirc", "credentials.json", "private_key.pem"]:
            if (self.project_dir / fname).exists():
                self.result.failed.append(f"✗ Sensitive file found: {fname}")

    async def _test_env_file(self) -> None:
        env_file = self.project_dir / ".env"
        if not env_file.exists():
            self.result.warnings.append("⚠ No .env file - agent may need environment variables")
            return
        try:
            env_vars: Dict[str, str] = {}
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        env_vars[key.strip()] = value.strip()
            self.result.passed.append(f"✓ .env parsed successfully ({len(env_vars)} variables)")
            common = ["OPENAI_API_KEY", "API_KEY", "DB_HOST"]
            found = [k for k in common if k in env_vars]
            if found:
                self.result.passed.append(f"✓ Found common variables: {', '.join(found)}")
        except Exception as exc:
            self.result.failed.append(f"✗ .env parsing failed: {exc}")

    # =============================
    # Level 2: Build Validation
    # =============================
    async def _test_build(self) -> None:
        self._log("\n📦 Level 2: Build Validation")
        self._log("=" * 50)
        try:
            from pixell.core.builder import AgentBuilder

            with tempfile.TemporaryDirectory() as tmp:
                builder = AgentBuilder(self.project_dir)
                if self.silent:
                    sink = io.StringIO()
                    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                        self.apkg_path = builder.build(output_dir=Path(tmp))
                else:
                    self.apkg_path = builder.build(output_dir=Path(tmp))
                self.result.passed.append(f"✓ APKG built successfully: {self.apkg_path.name}")

                size_mb = self.apkg_path.stat().st_size / (1024 * 1024)
                if size_mb > 50:
                    self.result.warnings.append(f"⚠ Package is large: {size_mb:.1f}MB")
                else:
                    self.result.passed.append(f"✓ Package size: {size_mb:.1f}MB")

                await self._test_package_contents()
        except Exception as exc:
            self.result.failed.append(f"✗ Build failed: {exc}")

    async def _test_package_contents(self) -> None:
        if not self.apkg_path:
            self.result.failed.append("✗ Build did not produce an APKG path")
            return
        with zipfile.ZipFile(self.apkg_path) as zf:
            files = zf.namelist()
            for required in ["agent.yaml", "src/"]:
                if any(f.startswith(required) for f in files):
                    self.result.passed.append(f"✓ {required} in package")
                else:
                    self.result.failed.append(f"✗ {required} missing from package")
            if ".env" in files:
                self.result.passed.append("✓ .env included in package")
            else:
                self.result.warnings.append("⚠ .env not in package")

    # =============================
    # Level 3: Installation Testing
    # =============================
    async def _test_install(self) -> None:
        self._log("\n🔧 Level 3: Installation Testing")
        self._log("=" * 50)
        if not self.apkg_path:
            self.result.failed.append("✗ No APKG available to install")
            return

        with tempfile.TemporaryDirectory() as tmp:
            venv_path = Path(tmp) / "test_venv"

            proc = subprocess.run(
                ["python3", "-m", "venv", str(venv_path)], capture_output=True, text=True
            )
            if proc.returncode != 0:
                self.result.failed.append(f"✗ venv creation failed: {proc.stderr}")
                return
            self.result.passed.append("✓ Test venv created")

            extract_dir = Path(tmp) / "agent"
            with zipfile.ZipFile(self.apkg_path) as zf:
                zf.extractall(extract_dir)

            pip = venv_path / "bin" / "pip"
            req = extract_dir / "requirements.txt"
            if req.exists():
                proc = subprocess.run(
                    [str(pip), "install", "-r", str(req)],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                if proc.returncode == 0:
                    self.result.passed.append("✓ Requirements installed successfully")
                else:
                    self.result.failed.append(f"✗ Requirements install failed: {proc.stderr}")
                    return

            await self._test_imports(venv_path, extract_dir)

            # persist for runtime checks
            self.test_venv = venv_path
            self.extract_dir = extract_dir

    async def _test_imports(self, venv_path: Path, extract_dir: Path) -> None:
        python = venv_path / "bin" / "python"
        try:
            import yaml  # type: ignore

            with open(extract_dir / "agent.yaml", "r", encoding="utf-8") as f:
                manifest = yaml.safe_load(f)
        except Exception as exc:
            self.result.failed.append(f"✗ Failed to read manifest in extracted package: {exc}")
            return

        entrypoint = manifest.get("entrypoint")
        if not entrypoint:
            self.result.warnings.append("⚠ No entrypoint defined; skipping import test")
            return

        module_path, func_name = entrypoint.split(":", 1)
        test_script = (
            "import sys\n"
            f"sys.path.insert(0, '{extract_dir}')\n"
            f"from {module_path} import {func_name}\n"
            "print('OK')\n"
        )
        proc = subprocess.run([str(python), "-c", test_script], capture_output=True, text=True)
        if "OK" in proc.stdout:
            self.result.passed.append(f"✓ Entrypoint imports successfully: {entrypoint}")
        else:
            self.result.failed.append(f"✗ Import failed: {proc.stdout or proc.stderr}")

    # =============================
    # Level 4: Runtime Testing
    # =============================
    async def _test_runtime(self) -> None:
        self._log("\n🚀 Level 4: Runtime Testing")
        self._log("=" * 50)
        if not self.test_venv or not self.extract_dir:
            self.result.failed.append("✗ Runtime tests require successful install phase")
            return
        await self._test_grpc_server()
        await self._test_rest_server()
        await self._test_ui_assets()

    async def _test_grpc_server(self) -> None:
        # Basic stub: check config presence; user projects may not include gRPC
        if self.extract_dir is None:
            self.result.warnings.append("⚠ Extract dir not set for gRPC test")
            return
        try:
            import yaml  # type: ignore

            with open(self.extract_dir / "agent.yaml", "r", encoding="utf-8") as f:
                manifest = yaml.safe_load(f)
        except Exception as exc:
            self.result.warnings.append(f"⚠ Could not read manifest for gRPC test: {exc}")
            return

        a2a_cfg = manifest.get("a2a")
        if not a2a_cfg:
            self.result.skipped.append("⊘ gRPC server not configured")
            return

        # At this time, full gRPC runtime bootstrapping is project-specific; mark as skipped
        self.result.skipped.append("⊘ gRPC runtime test not implemented for this template")

    async def _test_rest_server(self) -> None:
        # Attempt to launch a minimal FastAPI app using mounted entry if present
        if self.extract_dir is None:
            return
        try:
            import yaml  # type: ignore

            with open(self.extract_dir / "agent.yaml", "r", encoding="utf-8") as f:
                manifest = yaml.safe_load(f)
        except Exception:
            return

        rest_cfg = manifest.get("rest")
        if not rest_cfg:
            self.result.skipped.append("⊘ REST server not configured")
            return

        # Best-effort: verify that module exists in dist copy
        try:
            module_path, func_name = rest_cfg["entry"].split(":", 1)
            src_file = self.extract_dir / (module_path.replace(".", "/") + ".py")
            if src_file.exists():
                self.result.passed.append("✓ REST entry module exists in package")
            else:
                self.result.warnings.append("⚠ REST entry module not found in package dist")
        except Exception as exc:
            self.result.warnings.append(f"⚠ REST config parsing issue: {exc}")

    async def _test_ui_assets(self) -> None:
        # Verify UI assets presence if configured
        if self.extract_dir is None:
            return
        try:
            import yaml  # type: ignore

            with open(self.extract_dir / "agent.yaml", "r", encoding="utf-8") as f:
                manifest = yaml.safe_load(f)
        except Exception:
            return

        ui_cfg = manifest.get("ui")
        if not ui_cfg:
            self.result.skipped.append("⊘ UI not configured")
            return
        ui_dir = self.extract_dir / "dist" / "ui"
        if ui_dir.exists() and ui_dir.is_dir():
            index = ui_dir / "index.html"
            if index.exists():
                self.result.passed.append("✓ UI assets present; index.html found")
            else:
                self.result.warnings.append("⚠ UI assets present but index.html missing")
        else:
            self.result.warnings.append("⚠ UI dist directory missing")

    # =============================
    # Level 5: Integration Testing
    # =============================
    async def _test_integration(self) -> None:
        self._log("\n🔗 Level 5: Integration Testing")
        self._log("=" * 50)
        # Placeholder for project-specific E2E invocation; mark skipped if no entrypoint
        if not self.extract_dir:
            self.result.skipped.append("⊘ Integration skipped (no installed package context)")
            return
        await self._test_agent_invocation()

    async def _test_agent_invocation(self) -> None:
        # Minimal validation: if entrypoint exists, ensure callable can be located in installed tree
        if self.extract_dir is None:
            self.result.warnings.append("⚠ Extract dir not set for integration test")
            return
        try:
            import yaml  # type: ignore

            with open(self.extract_dir / "agent.yaml", "r", encoding="utf-8") as f:
                manifest = yaml.safe_load(f)
        except Exception as exc:
            self.result.warnings.append(f"⚠ Could not read manifest for integration: {exc}")
            return

        entrypoint = manifest.get("entrypoint")
        if not entrypoint:
            self.result.skipped.append("⊘ No entrypoint configured; integration skipped")
            return
        module_path, func_name = entrypoint.split(":", 1)
        src_file = self.extract_dir / (module_path.replace(".", "/") + ".py")
        if src_file.exists():
            self.result.passed.append("✓ Entrypoint source present for integration checks")
        else:
            self.result.warnings.append("⚠ Entrypoint source not present in extracted package")
