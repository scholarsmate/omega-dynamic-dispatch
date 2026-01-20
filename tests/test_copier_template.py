import importlib
import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = ROOT


def _run_copier(tmp_path: Path, data: dict[str, str]) -> Path:
    dest = tmp_path / "output"
    source = tmp_path / "source"

    shutil.copytree(
        TEMPLATE_ROOT,
        source,
        ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", ".pytest_cache"),
    )
    cmd = [
        sys.executable,
        "-m",
        "copier",
        "copy",
        str(source),
        str(dest),
        "--force",
        "--trust",
    ]
    for key, value in data.items():
        cmd.extend(["--data", f"{key}={value}"])

    subprocess.run(cmd, check=True, cwd=source)
    return dest


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _project_root(dest: Path) -> Path:
    if (dest / "pyproject.toml").exists():
        return dest
    return dest / "template"


def _purge_modules(prefix: str) -> None:
    for name in list(sys.modules):
        if name.startswith(prefix):
            sys.modules.pop(name, None)


def test_template_renders_with_entrypoints(tmp_path: Path) -> None:
    dest = _run_copier(
        tmp_path,
        {
            "project_name": "Sample CLI",
            "description": "Sample description",
            "author": "Test Author",
            "project_slug": "sample_cli",
            "python_min": "3.11",
            "use_entrypoints": "true",
            "license_year": "2026",
        },
    )

    project_root = _project_root(dest)
    pyproject = _read(project_root / "pyproject.toml")
    assert 'name = "sample_cli"' in pyproject
    assert '[project.entry-points."sample_cli.plugins"]' in pyproject

    cli = _read(project_root / "src" / "sample_cli" / "cli.py")
    assert "{{ project_slug }}" not in cli
    assert "load_plugins" in cli
    assert ".plugins" in cli
    assert "prog_name=pkg" in cli

    assert (project_root / "README.md").exists()
    assert (project_root / "LICENSE").exists()


def test_template_renders_without_entrypoints(tmp_path: Path) -> None:
    dest = _run_copier(
        tmp_path,
        {
            "project_name": "No Entry Points",
            "description": "No entrypoints",
            "author": "Test Author",
            "project_slug": "no_entry",
            "python_min": "3.11",
            "use_entrypoints": "false",
            "license_year": "2026",
        },
    )

    project_root = _project_root(dest)
    pyproject = _read(project_root / "pyproject.toml")
    assert '[project.entry-points."no_entry.plugins"]' not in pyproject


def test_ingest_handles_path_io(tmp_path: Path) -> None:
    dest = _run_copier(
        tmp_path,
        {
            "project_name": "IO CLI",
            "description": "IO test",
            "author": "Test Author",
            "project_slug": "io_cli",
            "python_min": "3.11",
            "use_entrypoints": "false",
            "license_year": "2026",
        },
    )

    project_root = _project_root(dest)
    package_root = project_root / "src"
    sys.path.insert(0, str(package_root))

    try:
        load_plugins = importlib.import_module("io_cli.core.plugins").load_plugins
        build_cli = importlib.import_module("io_cli.core.click_factory").build_cli
        from click.testing import CliRunner

        data_file = tmp_path / "data.txt"
        data_file.write_text("hello", encoding="utf-8")

        load_plugins("io_cli.plugins")
        cli = build_cli("io_cli")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--output",
                "json",
                "ingest",
                "users",
                str(data_file),
            ],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output.strip())
        assert payload.get("ok") is True
        events = payload.get("events", [])
        assert events
        assert events[0].get("kind") == "ingest"
        assert events[0].get("details", {}).get("bytes") == 5
    finally:
        sys.path.pop(0)
        _purge_modules("io_cli")


def test_main_propagates_exit_codes(tmp_path: Path) -> None:
    dest = _run_copier(
        tmp_path,
        {
            "project_name": "Exit Code CLI",
            "description": "Exit handling",
            "author": "Test Author",
            "project_slug": "exit_cli",
            "python_min": "3.11",
            "use_entrypoints": "false",
            "license_year": "2026",
        },
    )

    project_root = _project_root(dest)
    package_root = project_root / "src"
    data_file = tmp_path / "data.txt"
    data_file.write_text("hello", encoding="utf-8")

    sys.path.insert(0, str(package_root))
    try:
        cli_mod = importlib.import_module("exit_cli.cli")
        assert cli_mod.main(["check"]) == 1
        assert cli_mod.main(["ingest", "users", str(data_file)]) == 0
    finally:
        sys.path.pop(0)
        _purge_modules("exit_cli")


def test_optional_io_parameters_are_opened(tmp_path: Path) -> None:
    dest = _run_copier(
        tmp_path,
        {
            "project_name": "IO Optional CLI",
            "description": "IO optional test",
            "author": "Test Author",
            "project_slug": "io_optional_cli",
            "python_min": "3.11",
            "use_entrypoints": "false",
            "license_year": "2026",
        },
    )

    project_root = _project_root(dest)
    package_root = project_root / "src"
    plugin_path = package_root / "io_optional_cli" / "plugins" / "optional_file.py"
    plugin_path.write_text(
        textwrap.dedent(
            """
            from typing import IO

            from ..core.dispatch import command
            from ..core.errors import ErrorCode
            from ..core.results import ResultObject


            @command(positional=False)
            def optional_file(results: ResultObject, *, data_file: IO[str] | None = None) -> None:
                if data_file is None:
                    results.add_event("noop", code=ErrorCode.OK)
                    return

                text = data_file.read()
                results.add_event(
                    "got-file",
                    code=ErrorCode.OK,
                    details={"bytes": len(text.encode("utf-8"))},
                )
            """
        ).strip(),
        encoding="utf-8",
    )

    sys.path.insert(0, str(package_root))

    try:
        load_plugins = importlib.import_module("io_optional_cli.core.plugins").load_plugins
        build_cli = importlib.import_module("io_optional_cli.core.click_factory").build_cli
        from click.testing import CliRunner

        load_plugins("io_optional_cli.plugins")
        cli = build_cli("io_optional_cli")

        runner = CliRunner()

        result = runner.invoke(
            cli,
            [
                "--output",
                "json",
                "optional_file",
            ],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output.strip())
        assert payload.get("ok") is True
        events = payload.get("events", [])
        assert events and events[0].get("kind") == "noop"

        data_file = tmp_path / "optional-data.txt"
        data_file.write_text("abc", encoding="utf-8")
        result = runner.invoke(
            cli,
            [
                "--output",
                "json",
                "optional_file",
                "--data-file",
                str(data_file),
            ],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output.strip())
        events = payload.get("events", [])
        assert events and events[0].get("details", {}).get("bytes") == 3
    finally:
        sys.path.pop(0)
        _purge_modules("io_optional_cli")


def test_command_failure_returns_nonzero(tmp_path: Path) -> None:
    dest = _run_copier(
        tmp_path,
        {
            "project_name": "Error CLI",
            "description": "Error test",
            "author": "Test Author",
            "project_slug": "error_cli",
            "python_min": "3.11",
            "use_entrypoints": "false",
            "license_year": "2026",
        },
    )

    project_root = _project_root(dest)
    package_root = project_root / "src"
    plugin_path = package_root / "error_cli" / "plugins" / "fail.py"
    plugin_path.write_text(
        textwrap.dedent(
            """
            from ..core.dispatch import command
            from ..core.results import ResultObject


            @command()
            def fail(results: ResultObject) -> None:
                raise RuntimeError("boom")
            """
        ).strip(),
        encoding="utf-8",
    )

    sys.path.insert(0, str(package_root))

    try:
        load_plugins = importlib.import_module("error_cli.core.plugins").load_plugins
        build_cli = importlib.import_module("error_cli.core.click_factory").build_cli
        from click.testing import CliRunner

        load_plugins("error_cli.plugins")
        cli = build_cli("error_cli")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--output",
                "json",
                "fail",
            ],
        )

        assert result.exit_code == 70
        payload = json.loads(result.output.strip())
        assert payload.get("ok") is False
        events = payload.get("events", [])
        assert events and events[0].get("kind") == "error"
    finally:
        sys.path.pop(0)
        _purge_modules("error_cli")


def test_usage_error_returns_two(tmp_path: Path) -> None:
    dest = _run_copier(
        tmp_path,
        {
            "project_name": "Usage CLI",
            "description": "Usage test",
            "author": "Test Author",
            "project_slug": "usage_cli",
            "python_min": "3.11",
            "use_entrypoints": "false",
            "license_year": "2026",
        },
    )

    project_root = _project_root(dest)
    package_root = project_root / "src"

    sys.path.insert(0, str(package_root))

    try:
        load_plugins = importlib.import_module("usage_cli.core.plugins").load_plugins
        build_cli = importlib.import_module("usage_cli.core.click_factory").build_cli
        from click.testing import CliRunner

        load_plugins("usage_cli.plugins")
        cli = build_cli("usage_cli")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "ingest",
            ],
        )

        # Click usage errors should exit 2
        assert result.exit_code == 2
    finally:
        sys.path.pop(0)
        _purge_modules("usage_cli")
