import importlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = ROOT


def _run_copier(tmp_path: Path, data: dict[str, str]) -> Path:
    dest = tmp_path / "output"
    cmd = [
        sys.executable,
        "-m",
        "copier",
        "copy",
        str(TEMPLATE_ROOT),
        str(dest),
        "--force",
    ]
    for key, value in data.items():
        cmd.extend(["--data", f"{key}={value}"])

    subprocess.run(cmd, check=True, cwd=TEMPLATE_ROOT)
    return dest


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _project_root(dest: Path) -> Path:
    if (dest / "pyproject.toml").exists():
        return dest
    return dest / "template"


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
        for name in list(sys.modules):
            if name.startswith("io_cli"):
                sys.modules.pop(name, None)
